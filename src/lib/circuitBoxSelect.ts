import * as THREE from "three";
import type { CircuitMesh } from "./circuitMeshes";
import type { GridPath } from "./gridBuilder";

export type ScreenRect = { l: number; t: number; r: number; b: number };

export const BOX_SELECT_DRAG_THRESHOLD = 4;
/** Screen-pixel tolerance for clicking a trace. */
export const LINE_PICK_PX = 8;
/** Extra pixels around the marquee so on-screen stroke width is included. */
export const BOX_SELECT_PAD = 8;

const _v = new THREE.Vector3();

export function screenRect(x0: number, y0: number, x1: number, y1: number): ScreenRect {
  return {
    l: Math.min(x0, x1),
    r: Math.max(x0, x1),
    t: Math.min(y0, y1),
    b: Math.max(y0, y1),
  };
}

export function inflateScreenRect(rect: ScreenRect, pad: number): ScreenRect {
  return {
    l: rect.l - pad,
    r: rect.r + pad,
    t: rect.t - pad,
    b: rect.b + pad,
  };
}

export function canvasLocalPoint(
  clientX: number,
  clientY: number,
  canvas: HTMLCanvasElement,
): { sx: number; sy: number } {
  const rect = canvas.getBoundingClientRect();
  return { sx: clientX - rect.left, sy: clientY - rect.top };
}

function worldToCanvasLocal(
  x: number,
  y: number,
  z: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): { sx: number; sy: number } | null {
  const rect = canvas.getBoundingClientRect();
  _v.set(x, y, z);
  camera.updateMatrixWorld();
  _v.project(camera);
  if (!Number.isFinite(_v.x) || !Number.isFinite(_v.y)) return null;
  return {
    sx: ((_v.x + 1) / 2) * rect.width,
    sy: ((1 - _v.y) / 2) * rect.height,
  };
}

function pointInRect(px: number, py: number, rect: ScreenRect): boolean {
  return px >= rect.l && px <= rect.r && py >= rect.t && py <= rect.b;
}

function rectsOverlap(a: ScreenRect, b: ScreenRect): boolean {
  return a.l <= b.r && a.r >= b.l && a.t <= b.b && a.b >= b.t;
}

function segmentsCross(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
  dx: number,
  dy: number,
): boolean {
  const det = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx);
  if (Math.abs(det) < 1e-9) return false;
  const t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / det;
  const u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / det;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

/** Axis-aligned segment lying on or across a rect span (parallel overlap). */
function segmentCollinearOverlapsRect(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  rect: ScreenRect,
): boolean {
  if (Math.abs(ay - by) <= 1e-9) {
    if (ay < rect.t || ay > rect.b) return false;
    const segL = Math.min(ax, bx);
    const segR = Math.max(ax, bx);
    return segL <= rect.r && segR >= rect.l;
  }
  if (Math.abs(ax - bx) <= 1e-9) {
    if (ax < rect.l || ax > rect.r) return false;
    const segT = Math.min(ay, by);
    const segB = Math.max(ay, by);
    return segT <= rect.b && segB >= rect.t;
  }
  return false;
}

export function segmentIntersectsRect(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  rect: ScreenRect,
): boolean {
  if (pointInRect(ax, ay, rect) || pointInRect(bx, by, rect)) return true;
  if (segmentCollinearOverlapsRect(ax, ay, bx, by, rect)) return true;
  const edges: Array<[number, number, number, number]> = [
    [rect.l, rect.t, rect.r, rect.t],
    [rect.r, rect.t, rect.r, rect.b],
    [rect.r, rect.b, rect.l, rect.b],
    [rect.l, rect.b, rect.l, rect.t],
  ];
  for (const [x0, y0, x1, y1] of edges) {
    if (segmentsCross(ax, ay, bx, by, x0, y0, x1, y1)) return true;
  }
  return false;
}

function pathIntersectsScreenRect(
  waypoints: GridPath["waypoints"],
  project: (wp: GridPath["waypoints"][number]) => { sx: number; sy: number } | null,
  rect: ScreenRect,
): boolean {
  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = project(waypoints[i]);
    const b = project(waypoints[i + 1]);
    if (!a || !b) continue;
    if (segmentIntersectsRect(a.sx, a.sy, b.sx, b.sy, rect)) return true;
  }
  return false;
}

/**
 * Callers pass only the editable trace layer, so every path with an id is a
 * candidate — including split/join segments whose ids keep their source
 * prefix (e.g. "part-0-seg-0~a"). Do not re-filter by id prefix here.
 */
export function linesInScreenBox(
  paths: GridPath[],
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  pad = BOX_SELECT_PAD,
): string[] {
  const rect = inflateScreenRect(screenRect(x0, y0, x1, y1), pad);
  const ids: string[] = [];
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    const hit = pathIntersectsScreenRect(
      p.waypoints,
      (wp) => worldToCanvasLocal(wp[0], wp[1], wp[2], camera, canvas),
      rect,
    );
    if (hit) ids.push(p.id!);
  }
  return ids;
}

export function meshesInScreenBox(
  meshes: CircuitMesh[],
  boardY: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  pad = BOX_SELECT_PAD,
): string[] {
  const rect = inflateScreenRect(screenRect(x0, y0, x1, y1), pad);
  const ids: string[] = [];
  for (const m of meshes) {
    // Project all four footprint corners: under a rotated camera the screen
    // bounds of the box are not spanned by one diagonal alone.
    let l = Infinity;
    let r = -Infinity;
    let t = Infinity;
    let b = -Infinity;
    let ok = true;
    for (const [x, z] of [
      [m.minX, m.minZ],
      [m.maxX, m.minZ],
      [m.minX, m.maxZ],
      [m.maxX, m.maxZ],
    ]) {
      const p = worldToCanvasLocal(x, boardY, z, camera, canvas);
      if (!p) {
        ok = false;
        break;
      }
      l = Math.min(l, p.sx);
      r = Math.max(r, p.sx);
      t = Math.min(t, p.sy);
      b = Math.max(b, p.sy);
    }
    if (ok && rectsOverlap(rect, { l, r, t, b })) ids.push(m.id);
  }
  return ids;
}

function distToSegmentPx(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  if (len2 < 1e-12) return Math.hypot(px - ax, py - ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/** Nearest editable trace under a canvas-local point, if within pick tolerance. */
export function lineIdAtScreenPoint(
  paths: GridPath[],
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  sx: number,
  sy: number,
  pickPx = LINE_PICK_PX,
): string | null {
  let bestId: string | null = null;
  let bestDist = pickPx;
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    for (let i = 0; i < p.waypoints.length - 1; i++) {
      const a = worldToCanvasLocal(
        p.waypoints[i][0],
        p.waypoints[i][1],
        p.waypoints[i][2],
        camera,
        canvas,
      );
      const b = worldToCanvasLocal(
        p.waypoints[i + 1][0],
        p.waypoints[i + 1][1],
        p.waypoints[i + 1][2],
        camera,
        canvas,
      );
      if (!a || !b) continue;
      const d = distToSegmentPx(sx, sy, a.sx, a.sy, b.sx, b.sy);
      if (d <= bestDist) {
        bestDist = d;
        bestId = p.id;
      }
    }
  }
  return bestId;
}

function meshScreenRect(
  mesh: CircuitMesh,
  boardY: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenRect | null {
  let l = Infinity;
  let r = -Infinity;
  let t = Infinity;
  let b = -Infinity;
  for (const [x, z] of [
    [mesh.minX, mesh.minZ],
    [mesh.maxX, mesh.minZ],
    [mesh.minX, mesh.maxZ],
    [mesh.maxX, mesh.maxZ],
  ]) {
    const p = worldToCanvasLocal(x, boardY, z, camera, canvas);
    if (!p) return null;
    l = Math.min(l, p.sx);
    r = Math.max(r, p.sx);
    t = Math.min(t, p.sy);
    b = Math.max(b, p.sy);
  }
  return { l, r, t, b };
}

/** Component footprint under a canvas-local point, if any. */
export function meshIdAtScreenPoint(
  meshes: CircuitMesh[],
  boardY: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  sx: number,
  sy: number,
): string | null {
  for (const m of meshes) {
    const rect = meshScreenRect(m, boardY, camera, canvas);
    if (rect && pointInRect(sx, sy, rect)) return m.id;
  }
  return null;
}
