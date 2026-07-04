import type { Object3D } from "three";
import traced from "../../plans/circuit design/circuits-traced.json";
import publishedTuning from "../data/circuits-tuning.json";
import type { CircuitTuning } from "../stores/circuitTuning";
import { applyTopology } from "./circuitTopology";
import {
  splitPathsIntoSegments,
  totalPathLength,
  type GridPath,
  type Vec3,
} from "./gridBuilder";
import { tronLinesFromGLB } from "./tronLinesFromGLB";

/** Committed tuning the site ships with; exported so the store can seed from it. */
export const PUBLISHED_TUNING = publishedTuning as unknown as CircuitTuning;

const PAD_CELLS = 6;
const CELL_PX = 9;
const BOARD_WORLD_W = 58.0;
const TRACE_Y = 0.022;
/** Max XZ gap (world units) to pull a trace endpoint onto a part outline edge. */
const TRACE_PART_SNAP_XZ = 0.35;

export const CIRCUITS_OUTLINE_CURSOR_SPEED = 6.0;
/** Horizontal pan speed for the scan camera (world units/sec). */
export const CIRCUITS_CAMERA_PAN_SPEED = 1.5;
export const CIRCUITS_SCAN_HEIGHT_FACTOR = 0.14;
/** Default lag behind the scan front so the draw tip sits near frame centre. */
export const CIRCUITS_SCAN_FRONT_LAG_SEC = 1.5;

/** Tunable scan-camera framing for the top-view reveal. */
export type TopViewCamera = {
  /** Camera height as a fraction of board span. */
  heightFactor: number;
  /** Seconds the camera trails behind the scan front (on top of startTime). */
  frontLagSec: number;
  /** World-space offset applied to camera position and look-at. */
  offset: Vec3;
};

export const DEFAULT_TOP_VIEW_CAMERA: TopViewCamera = {
  heightFactor: CIRCUITS_SCAN_HEIGHT_FACTOR,
  frontLagSec: CIRCUITS_SCAN_FRONT_LAG_SEC,
  offset: [0, 0, 0],
};

const SCAN_VIEW_FOV = 40;
const SCAN_VIEW_ASPECT = 16 / 9;
/** Fraction of the in-frame window used for drawing before the path exits view. */
const IN_FRAME_DRAW_FRACTION = 0.88;

export function scanViewHalfWidth(
  span: number,
  fovDeg = SCAN_VIEW_FOV,
): number {
  const height = span * CIRCUITS_SCAN_HEIGHT_FACTOR;
  const vFovRad = (fovDeg * Math.PI) / 180;
  const hFovRad = 2 * Math.atan(Math.tan(vFovRad / 2) * SCAN_VIEW_ASPECT);
  return height * Math.tan(hFovRad / 2);
}

export function scanPanDuration(spanX: number): number {
  return spanX > 0 ? spanX / CIRCUITS_CAMERA_PAN_SPEED : 0;
}

export function scanCameraX(
  time: number,
  minX: number,
  spanX: number,
  panDuration = scanPanDuration(spanX),
): number {
  const progress =
    panDuration > 0 ? Math.max(0, Math.min(time / panDuration, 1)) : 0;
  return minX + spanX * progress;
}

function pathBoundsX(waypoints: Vec3[]): { minX: number; maxX: number } {
  let minX = Infinity;
  let maxX = -Infinity;
  for (const [x] of waypoints) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
  }
  if (!Number.isFinite(minX)) return { minX: 0, maxX: 0 };
  return { minX, maxX };
}

type PxPoint = [number, number];
type TracedData = {
  lines: PxPoint[][];
  boxes: Record<
    string,
    Array<{
      x: number;
      y: number;
      w: number;
      h: number;
      cx?: number;
      cy?: number;
    }>
  >;
};

function contentBounds(data: TracedData, padPx: number) {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const line of data.lines) {
    for (const [x, y] of line) {
      xs.push(x);
      ys.push(y);
    }
  }
  for (const boxes of Object.values(data.boxes)) {
    for (const box of boxes) {
      xs.push(box.x, box.x + box.w);
      ys.push(box.y, box.y + box.h);
    }
  }
  return {
    minX: Math.min(...xs) - padPx,
    minY: Math.min(...ys) - padPx,
    maxX: Math.max(...xs) + padPx,
    maxY: Math.max(...ys) + padPx,
  };
}

function pxToWorld(
  px: number,
  py: number,
  offsetX: number,
  offsetY: number,
  scale: number,
): Vec3 {
  return [(px - offsetX) * scale, TRACE_Y, (py - offsetY) * scale];
}

export function boardBoundsX(paths: GridPath[]): {
  minX: number;
  maxX: number;
} {
  let minX = Infinity;
  let maxX = -Infinity;
  for (const path of paths) {
    for (const [x] of path.waypoints) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
    }
  }
  if (!Number.isFinite(minX)) return { minX: 0, maxX: 0 };
  return { minX, maxX };
}

function orientPathLeftToRight(path: GridPath): GridPath {
  const { waypoints } = path;
  if (waypoints.length < 2) return path;

  const firstX = waypoints[0][0];
  const lastX = waypoints[waypoints.length - 1][0];
  if (firstX <= lastX) return path;

  return { ...path, waypoints: [...waypoints].reverse() };
}

export type CircuitsTracedLayout = {
  paths: GridPath[];
  center: Vec3;
  span: number;
};

export function tracePathsFromCircuitsTraced(): GridPath[] {
  const data = traced as unknown as TracedData;
  const padPx = PAD_CELLS * CELL_PX;
  const bounds = contentBounds(data, padPx);
  const scale = BOARD_WORLD_W / (bounds.maxX - bounds.minX);

  return data.lines.map((line, i) => ({
    id: `trace-${i}`,
    waypoints: line.map(([px, py]) =>
      pxToWorld(px, py, bounds.minX, bounds.minY, scale),
    ),
    spawnTime: 0,
  }));
}

/** Accent-colored component boxes from circuits-traced.png / circuits-traced.json. */
export type TracedReferenceMesh = {
  accent: "green" | "pink";
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  cx: number;
  cz: number;
};

/** World-space mesh refs keyed by PNG accent (green = QFP, pink = heatsink). */
export function tracedReferenceMeshes(): TracedReferenceMesh[] {
  const data = traced as unknown as TracedData;
  const padPx = PAD_CELLS * CELL_PX;
  const bounds = contentBounds(data, padPx);
  const scale = BOARD_WORLD_W / (bounds.maxX - bounds.minX);
  const out: TracedReferenceMesh[] = [];

  for (const [accent, boxes] of Object.entries(data.boxes)) {
    if (accent !== "green" && accent !== "pink") continue;
    for (const b of boxes) {
      const minX = (b.x - bounds.minX) * scale;
      const minZ = (b.y - bounds.minY) * scale;
      const maxX = (b.x + b.w - bounds.minX) * scale;
      const maxZ = (b.y + b.h - bounds.minY) * scale;
      out.push({
        accent,
        minX,
        maxX,
        minZ,
        maxZ,
        cx: (minX + maxX) / 2,
        cz: (minZ + maxZ) / 2,
      });
    }
  }
  return out;
}

type OutlineSegment = readonly [Vec3, Vec3];

function partOutlineSegments(partPaths: GridPath[]): OutlineSegment[] {
  const segments: OutlineSegment[] = [];
  for (const path of partPaths) {
    const { waypoints } = path;
    for (let i = 0; i < waypoints.length - 1; i++) {
      segments.push([waypoints[i], waypoints[i + 1]]);
    }
  }
  return segments;
}

function nearestOnSegmentXZ(
  point: Vec3,
  a: Vec3,
  b: Vec3,
): { distXZ: number; point: Vec3 } {
  const px = point[0];
  const pz = point[2];
  const ax = a[0];
  const az = a[2];
  const bx = b[0];
  const bz = b[2];
  const dx = bx - ax;
  const dz = bz - az;
  const len2 = dx * dx + dz * dz;
  const t =
    len2 > 1e-12
      ? Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / len2))
      : 0;
  const qx = ax + t * dx;
  const qz = az + t * dz;
  const qy = a[1] + t * (b[1] - a[1]);
  return { distXZ: Math.hypot(px - qx, pz - qz), point: [qx, qy, qz] };
}

/** Pull trace endpoints onto nearby component outline edges so circuits meet meshes. */
export function snapTraceEndpointsToPartOutlines(
  tracePaths: GridPath[],
  partPaths: GridPath[],
  maxDistXZ = TRACE_PART_SNAP_XZ,
): GridPath[] {
  const segments = partOutlineSegments(partPaths);
  if (segments.length === 0) return tracePaths;

  return tracePaths.map((path) => {
    if (path.waypoints.length === 0) return path;

    const waypoints = path.waypoints.map((p) => [...p] as Vec3);
    const endpointIndices =
      waypoints.length === 1 ? [0] : [0, waypoints.length - 1];

    for (const idx of endpointIndices) {
      let bestDist = maxDistXZ;
      let bestYDelta = Infinity;
      let bestPoint: Vec3 | null = null;

      for (const [a, b] of segments) {
        const { distXZ, point } = nearestOnSegmentXZ(waypoints[idx], a, b);
        if (distXZ > maxDistXZ) continue;

        const yDelta = Math.abs(point[1] - waypoints[idx][1]);
        if (
          distXZ < bestDist - 1e-6 ||
          (Math.abs(distXZ - bestDist) <= 1e-6 && yDelta < bestYDelta)
        ) {
          bestDist = distXZ;
          bestYDelta = yDelta;
          bestPoint = point;
        }
      }

      if (bestPoint) waypoints[idx] = bestPoint;
    }

    return { ...path, waypoints };
  });
}

/** Vertices within this Y distance of the mesh bottom are pinned to that plane. */
const BASE_PLANE_EPS = 0.05;

/**
 * Source segment geometry shared by the 3D scene and the 2D editor.
 *
 * Component outlines come from the GLB (tag `part`); metal traces come from
 * circuits-traced.json. Part vertices near the mesh bottom are pinned to one
 * base plane, trace endpoints are snapped onto the outlines they approach and
 * flattened to that plane, and everything is split into two-point segments with
 * stable ids (`part-*`, `trace-*`). This is the untuned baseline that topology
 * edits and the scan schedule are layered on top of.
 */
export function buildRawCircuitPaths(scene: Object3D): GridPath[] {
  const partPaths = tronLinesFromGLB(scene, { tag: "part" }).map((p, i) => ({
    ...p,
    id: `part-${i}`,
    spawnTime: 0,
  }));

  let baseY = Infinity;
  for (const p of partPaths) {
    for (const [, y] of p.waypoints) baseY = Math.min(baseY, y);
  }
  if (!Number.isFinite(baseY)) baseY = 0;

  const alignedParts = partPaths.map((p) => ({
    ...p,
    waypoints: p.waypoints.map(
      ([x, y, z]) =>
        [x, Math.abs(y - baseY) <= BASE_PLANE_EPS ? baseY : y, z] as Vec3,
    ),
  }));

  const tracePaths = snapTraceEndpointsToPartOutlines(
    tracePathsFromCircuitsTraced(),
    alignedParts,
  ).map((p) => ({
    ...p,
    waypoints: p.waypoints.map(([x, , z]) => [x, baseY, z] as Vec3),
  }));

  return splitPathsIntoSegments([...alignedParts, ...tracePaths]);
}

/** Global scheduler knobs the tuner can adjust without touching per-line values. */
export type ScannerParams = {
  /** Horizontal pan speed for the scan camera (world units/sec). */
  panSpeed: number;
  /** Fraction of the in-frame window used for drawing before the path exits view. */
  drawFraction: number;
  /** Multiplies every derived draw speed (lower = slower, more dramatic). */
  speedScale: number;
  /** Seconds before the very first line is allowed to spawn. */
  startTime: number;
};

export const DEFAULT_SCANNER_PARAMS: ScannerParams = {
  panSpeed: CIRCUITS_CAMERA_PAN_SPEED,
  drawFraction: IN_FRAME_DRAW_FRACTION,
  speedScale: 1,
  startTime: 0,
};

type ScanSlot = {
  tEnter: number;
  tExit: number;
  pathLength: number;
};

function drawSpeedForWindow(
  pathLength: number,
  tStart: number,
  tExit: number,
  drawFraction: number,
  speedScale: number,
  fallbackSpeed: number,
): number {
  const inFrameSec = Math.max(0.1, (tExit - tStart) * drawFraction);
  const baseSpeed = pathLength > 0 ? pathLength / inFrameSec : fallbackSpeed;
  return speedScale > 0 ? baseSpeed * speedScale : baseSpeed;
}

/**
 * How close (world units) a drawing front must pass a junction before it
 * "touches" it and lights the lines meeting there. Tuned so a circuit passing a
 * component outline ignites it without igniting everything around it at once.
 */
const TOUCH_RADIUS = 1.0;
/** Brief pause after a front touches a junction before the touched line lights. */
const TOUCH_GAP_DELAY = 0.08;
/** Endpoints map to the same junction when within this distance (world units). */
const JUNCTION_QUANT = 1e-3;
/**
 * Endpoints this close are welded into one junction. Above the ~0.02 gaps that
 * endpoint snapping leaves inside a single trace, but far below real junction
 * spacing, so chains stay whole without merging genuinely distinct junctions.
 */
const JUNCTION_WELD_EPS = 0.05;
/** Draw speed is clamped to [min,max] × scan pan rate so wires draw evenly. */
const SPEED_BAND_MIN_FACTOR = 0.7;
const SPEED_BAND_MAX_FACTOR = 3.5;

/**
 * A junction the front passes near while drawing a segment, lighting the lines
 * that meet there. `along` is the distance along the segment of the nearest
 * point; `gapDelay` is extra travel time for bridge links that span open space.
 */
type ProximityHit = { key: string; along: number; gapDelay?: number };

function junctionKey(v: Vec3): string {
  return `${Math.round(v[0] / JUNCTION_QUANT)},${Math.round(
    v[1] / JUNCTION_QUANT,
  )},${Math.round(v[2] / JUNCTION_QUANT)}`;
}

/** Closest point on segment a→b to p; returns 3D distance and the param t∈[0,1]. */
function nearestParamOnSegment3D(
  p: Vec3,
  a: Vec3,
  b: Vec3,
): { dist: number; t: number } {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const dz = b[2] - a[2];
  const len2 = dx * dx + dy * dy + dz * dz;
  const t =
    len2 > 1e-12
      ? Math.max(
          0,
          Math.min(
            1,
            ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy + (p[2] - a[2]) * dz) /
              len2,
          ),
        )
      : 0;
  const qx = a[0] + t * dx;
  const qy = a[1] + t * dy;
  const qz = a[2] + t * dz;
  return { dist: Math.hypot(p[0] - qx, p[1] - qy, p[2] - qz), t };
}

type FloodEvent = {
  time: number;
  id: string;
  fromKey: string;
  /** Soft = an inter-component touch/bridge; only fires if its target component
   * has not already been lit by its own connectivity. */
  soft: boolean;
};

/** Binary min-heap over event time. */
class EventHeap {
  private data: FloodEvent[] = [];
  get size(): number {
    return this.data.length;
  }
  push(e: FloodEvent): void {
    const d = this.data;
    d.push(e);
    let i = d.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (d[parent].time <= d[i].time) break;
      [d[parent], d[i]] = [d[i], d[parent]];
      i = parent;
    }
  }
  pop(): FloodEvent {
    const d = this.data;
    const top = d[0];
    const last = d.pop()!;
    if (d.length > 0) {
      d[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let smallest = i;
        if (l < d.length && d[l].time < d[smallest].time) smallest = l;
        if (r < d.length && d[r].time < d[smallest].time) smallest = r;
        if (smallest === i) break;
        [d[smallest], d[i]] = [d[i], d[smallest]];
        i = smallest;
      }
    }
    return top;
  }
}

/** Disjoint-set over junction keys, used to give every cluster an origin. */
class UnionFind {
  private parent = new Map<string, string>();
  find(x: string): string {
    let root = this.parent.get(x);
    if (root === undefined) {
      this.parent.set(x, x);
      return x;
    }
    while (root !== x) {
      x = root;
      root = this.parent.get(x)!;
    }
    return root;
  }
  union(a: string, b: string): void {
    const ra = this.find(a);
    const rb = this.find(b);
    if (ra !== rb) this.parent.set(ra, rb);
  }
}

type SegInfo = {
  startKey: string;
  endKey: string;
  start: Vec3;
  end: Vec3;
  length: number;
  tEnter: number;
  tExit: number;
};

/**
 * Flood-fill ignition that respects each line's own shape.
 *
 * Plain-English version: every trace is a chain of little segments
 * (`trace-7-seg-0`, `-seg-1`, ...). A chain only kicks off at a genuine open end
 * — a loose tip with nothing feeding it — and from there it draws strictly in
 * order, each segment continuing exactly where the previous one finished. It
 * never lights a middle segment early, and never draws a segment backwards.
 *
 * How that's enforced: segments are grouped into "components" by real
 * connectivity (shared endpoints only). Inside a component the front travels
 * solely along those shared joints, so the draw direction always follows the
 * chain. A component that has an open end is driven only by that end. Shapes
 * with no open end (closed mesh loops) can't start themselves, so they wait
 * until another line's front physically passes them (a proximity touch) or, if
 * nothing ever does, until the nearest line bridges across the gap — at which
 * point they light at the contact point and branch outward. Crucially, those
 * touch/bridge ignitions only ever start a *different* component; they can never
 * reach into a chain and light it early or from the wrong side.
 *
 * If a front arrives late, the segment draws faster to catch the scan window
 * rather than starting early.
 */
function floodSchedule(
  paths: GridPath[],
  slots: Map<string, ScanSlot>,
  params: ScannerParams,
  fallbackSpeed: number,
  frameLeadTime: number,
): GridPath[] {
  const { drawFraction, speedScale } = params;
  const segs = paths.filter(
    (p) => p.id && slots.has(p.id) && p.waypoints.length >= 2,
  );

  const info = new Map<string, SegInfo>();
  const incident = new Map<string, string[]>();
  const junctionPos = new Map<string, Vec3>();
  const addIncident = (key: string, id: string, pos: Vec3) => {
    const list = incident.get(key);
    if (list) list.push(id);
    else incident.set(key, [id]);
    if (!junctionPos.has(key)) junctionPos.set(key, pos);
  };

  // Weld near-coincident endpoints to one junction. Quantizing alone splits a
  // shared point when the two copies straddle a grid boundary or sit a hair
  // apart (endpoint snapping can leave ~0.02 gaps within a single trace), which
  // would orphan a segment — making it self-start late (a visible pause) at a
  // wild catch-up speed. Welding within a tolerance well below real junction
  // spacing keeps every chain whole.
  const weldGrid = new Map<string, Array<{ key: string; pos: Vec3 }>>();
  const weldCell = (x: number, z: number) =>
    `${Math.floor(x / JUNCTION_WELD_EPS)},${Math.floor(z / JUNCTION_WELD_EPS)}`;
  const weld = (p: Vec3): string => {
    const cx = Math.floor(p[0] / JUNCTION_WELD_EPS);
    const cz = Math.floor(p[2] / JUNCTION_WELD_EPS);
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        for (const e of weldGrid.get(`${cx + dx},${cz + dz}`) ?? []) {
          if (
            Math.hypot(p[0] - e.pos[0], p[1] - e.pos[1], p[2] - e.pos[2]) <=
            JUNCTION_WELD_EPS
          ) {
            return e.key;
          }
        }
      }
    }
    const key = junctionKey(p);
    const cell = weldCell(p[0], p[2]);
    const bucket = weldGrid.get(cell);
    if (bucket) bucket.push({ key, pos: p });
    else weldGrid.set(cell, [{ key, pos: p }]);
    return key;
  };

  for (const p of segs) {
    const start = p.waypoints[0];
    const end = p.waypoints[p.waypoints.length - 1];
    const startKey = weld(start);
    const endKey = weld(end);
    const slot = slots.get(p.id!)!;
    info.set(p.id!, {
      startKey,
      endKey,
      start,
      end,
      length: slot.pathLength,
      tEnter: slot.tEnter,
      tExit: slot.tExit,
    });
    addIncident(startKey, p.id!, start);
    addIncident(endKey, p.id!, end);
  }

  // Components by real connectivity (shared endpoints only). Inside a component
  // the front can only travel along these joints, so a chain always draws in
  // order; nothing external can reach in and light a middle segment.
  const comp = new UnionFind();
  for (const i of info.values()) comp.union(i.startKey, i.endKey);
  const compOf = (id: string) => comp.find(info.get(id)!.startKey);

  // A component is a "circuit" (self-starting) if it has at least one open end —
  // a loose tip with nothing feeding it. Closed loops with no open end (mesh
  // outlines) are NOT self-starting; they wait until a circuit's front touches
  // them. This keeps meshes from popping in before a wire reaches them.
  const hasOpenEnd = new Set<string>();
  for (const [key, members] of incident) {
    if (members.length === 1) hasOpenEnd.add(comp.find(key));
  }

  // Each circuit component is lit from its LEFTMOST point, so the front always
  // enters from the left and flows rightward with the scan. Seeding from a tip
  // alone wasn't enough: a wire whose only open end is on the right (or that's
  // wholly interior to a network) would draw right-to-left. The leftmost point
  // has every neighbour to its right, so nothing is ever drawn backwards from it.
  const bestSourcePerComp = new Map<
    string,
    { key: string; tEnter: number; x: number }
  >();
  for (const [key, members] of incident) {
    const root = comp.find(key);
    if (!hasOpenEnd.has(root)) continue;
    const x = junctionPos.get(key)![0];
    let tEnter = Infinity;
    for (const m of members) tEnter = Math.min(tEnter, info.get(m)!.tEnter);
    const cur = bestSourcePerComp.get(root);
    if (!cur || x < cur.x) bestSourcePerComp.set(root, { key, tEnter, x });
  }
  const sourcedComps = new Set(bestSourcePerComp.keys());

  // Spatial hash of junctions on the board (XZ) plane for proximity queries.
  const cellOf = (x: number, z: number) =>
    `${Math.floor(x / TOUCH_RADIUS)},${Math.floor(z / TOUCH_RADIUS)}`;
  const grid = new Map<string, string[]>();
  for (const [key, pos] of junctionPos) {
    const ck = cellOf(pos[0], pos[2]);
    const list = grid.get(ck);
    if (list) list.push(key);
    else grid.set(ck, [key]);
  }

  // Inter-component touch contacts: a segment body passing near a junction that
  // belongs to a DIFFERENT component which isn't source-driven. Same-component
  // hits are skipped (those would light a chain early/backwards); source-driven
  // targets are skipped (they start from their own open end).
  const proximity = new Map<string, ProximityHit[]>();
  for (const p of segs) {
    const i = info.get(p.id!)!;
    const myComp = compOf(p.id!);
    const minX = Math.min(i.start[0], i.end[0]) - TOUCH_RADIUS;
    const maxX = Math.max(i.start[0], i.end[0]) + TOUCH_RADIUS;
    const minZ = Math.min(i.start[2], i.end[2]) - TOUCH_RADIUS;
    const maxZ = Math.max(i.start[2], i.end[2]) + TOUCH_RADIUS;
    const hits: ProximityHit[] = [];
    const seen = new Set<string>();
    for (let cx = Math.floor(minX / TOUCH_RADIUS); cx <= Math.floor(maxX / TOUCH_RADIUS); cx++) {
      for (let cz = Math.floor(minZ / TOUCH_RADIUS); cz <= Math.floor(maxZ / TOUCH_RADIUS); cz++) {
        for (const key of grid.get(`${cx},${cz}`) ?? []) {
          if (seen.has(key) || key === i.startKey || key === i.endKey) continue;
          seen.add(key);
          const targetComp = comp.find(key);
          if (targetComp === myComp || sourcedComps.has(targetComp)) continue;
          const pos = junctionPos.get(key)!;
          const { dist, t } = nearestParamOnSegment3D(pos, i.start, i.end);
          if (dist > TOUCH_RADIUS) continue;
          hits.push({ key, along: t * i.length });
        }
      }
    }
    if (hits.length) proximity.set(p.id!, hits);
  }

  const linkJunctionToSegment = (
    targetKey: string,
    hostSegId: string,
    gapDelay: number,
  ) => {
    const host = info.get(hostSegId)!;
    const pos = junctionPos.get(targetKey)!;
    const { t } = nearestParamOnSegment3D(pos, host.start, host.end);
    const entry: ProximityHit = {
      key: targetKey,
      along: t * host.length,
      gapDelay,
    };
    const list = proximity.get(hostSegId);
    if (list) list.push(entry);
    else proximity.set(hostSegId, [entry]);
  };

  // Reachability over components: source-driven plus anything a touch can lead
  // to. Whatever is left over is a mesh island no line passes near — bridge it
  // to the nearest reachable line so the front can still arrive across the gap.
  const reach = new UnionFind();
  const SOURCE = "__source__";
  for (const r of sourcedComps) reach.union(SOURCE, r);
  for (const [id, hits] of proximity) {
    const hc = compOf(id);
    for (const h of hits) reach.union(hc, comp.find(h.key));
  }

  // With no open end anywhere, kick off the single globally-leftmost junction.
  let fallbackSeed: { key: string; tEnter: number } | null = null;
  if (sourcedComps.size === 0) {
    let bestX = Infinity;
    for (const [key, pos] of junctionPos) {
      if (pos[0] < bestX) {
        bestX = pos[0];
        let earliest = Infinity;
        for (const m of incident.get(key) ?? [])
          earliest = Math.min(earliest, info.get(m)!.tEnter);
        fallbackSeed = { key, tEnter: earliest };
      }
    }
    if (fallbackSeed) reach.union(SOURCE, comp.find(fallbackSeed.key));
  }

  const junctionKeys = [...junctionPos.keys()];
  const isReachable = (compRoot: string) =>
    reach.find(compRoot) === reach.find(SOURCE);

  let guard = junctionKeys.length;
  for (;;) {
    let anyUnreachable = false;
    for (const k of junctionKeys) {
      if (!isReachable(comp.find(k))) {
        anyUnreachable = true;
        break;
      }
    }
    if (!anyUnreachable || guard-- <= 0) break;

    // Nearest reachable junction → unreachable junction; carry the front across.
    let best: { a: string; b: string; d: number } | null = null;
    for (const a of junctionKeys) {
      if (!isReachable(comp.find(a))) continue;
      const pa = junctionPos.get(a)!;
      for (const b of junctionKeys) {
        if (isReachable(comp.find(b))) continue;
        const pb = junctionPos.get(b)!;
        const d = Math.hypot(pa[0] - pb[0], pa[1] - pb[1], pa[2] - pb[2]);
        if (!best || d < best.d) best = { a, b, d };
      }
    }
    if (!best) break;
    const host = incident.get(best.a)?.[0];
    const gapDelay = fallbackSpeed > 0 ? best.d / fallbackSpeed : 0;
    if (host) linkJunctionToSegment(best.b, host, gapDelay);
    reach.union(comp.find(best.a), comp.find(best.b));
  }

  const spawn = new Map<string, number>();
  const fedFrom = new Map<string, string>();
  const speed = new Map<string, number>();
  const activated = new Set<string>();
  const heap = new EventHeap();

  // Draw speed, clamped to a band around the scan pan rate. The raw window-based
  // speed swings wildly (a segment reached after its scan window draws almost
  // instantly; one reached far ahead of it crawls), which reads as some wires
  // zipping while others freeze. Clamping keeps every wire drawing at a
  // comparable rate while still letting late arrivals speed up to catch up.
  const speedMin = params.panSpeed * SPEED_BAND_MIN_FACTOR;
  const speedMax = params.panSpeed * SPEED_BAND_MAX_FACTOR;
  const speedAt = (id: string, t0: number) => {
    const raw = drawSpeedForWindow(
      info.get(id)!.length,
      t0,
      info.get(id)!.tExit,
      drawFraction,
      speedScale,
      fallbackSpeed,
    );
    return Math.max(speedMin, Math.min(speedMax, raw));
  };

  const push = (key: string, time: number, soft: boolean) => {
    for (const id of incident.get(key) ?? []) {
      if (!spawn.has(id)) heap.push({ time, id, fromKey: key, soft });
    }
  };

  for (const { key, tEnter } of bestSourcePerComp.values()) {
    push(key, tEnter, false);
  }
  if (fallbackSeed) push(fallbackSeed.key, fallbackSeed.tEnter, false);

  while (heap.size > 0) {
    const { time, id, fromKey, soft } = heap.pop();
    if (spawn.has(id)) continue;
    const c = compOf(id);
    // A touch/bridge only lights a component that hasn't started drawing yet; it
    // can never override a chain that's already flowing along its own joints.
    if (soft && activated.has(c)) continue;

    const i = info.get(id)!;
    const sp = speedAt(id, time);
    spawn.set(id, time);
    fedFrom.set(id, fromKey);
    speed.set(id, sp);
    activated.add(c);

    // First touch into a fresh component lights every line meeting at the contact
    // point so the shape branches outward from there.
    if (soft) push(fromKey, time, false);

    const otherKey = fromKey === i.startKey ? i.endKey : i.startKey;
    const finish = time + (sp > 0 ? i.length / sp : 0);
    push(otherKey, finish, false);

    for (const hit of proximity.get(id) ?? []) {
      const alongFromFed =
        fromKey === i.startKey ? hit.along : i.length - hit.along;
      const tPass =
        time +
        (sp > 0 ? alongFromFed / sp : 0) +
        TOUCH_GAP_DELAY +
        (hit.gapDelay ?? 0);
      push(hit.key, tPass, true);
    }
  }

  return paths.map((p) => {
    if (!p.id || !info.has(p.id)) return p;
    const i = info.get(p.id)!;
    const tStart = spawn.get(p.id) ?? i.tEnter + frameLeadTime;
    const cursorSpeed = speed.get(p.id) ?? speedAt(p.id, tStart);
    const from = fedFrom.get(p.id) ?? i.startKey;

    // Draw direction. A horizontal run always draws left-to-right so no wire ever
    // travels backwards against the scan (segments arrive pre-oriented with
    // start.x <= end.x, so we just keep that). A (near-)vertical run has no
    // left/right, so it follows the side the front fed it from to stay continuous
    // with the segment that lit it.
    const isVertical = Math.abs(i.end[0] - i.start[0]) < 1e-3;
    const waypoints =
      isVertical && from === i.endKey
        ? [...p.waypoints].reverse()
        : p.waypoints;
    return { ...p, waypoints, spawnTime: tStart, cursorSpeed };
  });
}

/**
 * Left-to-right scan scheduling: the scanline seeds entry segments; every other
 * segment waits until a connected line finishes to the junction, then speeds up
 * to stay ahead of the scan frame.
 */
export function assignLeftToRightScanner(
  paths: GridPath[],
  params: Partial<ScannerParams> = {},
  fallbackSpeed = CIRCUITS_OUTLINE_CURSOR_SPEED,
): GridPath[] {
  if (paths.length === 0) return paths;

  const scannerParams = {
    ...DEFAULT_SCANNER_PARAMS,
    ...params,
  };
  const { panSpeed, drawFraction, speedScale, startTime } = scannerParams;

  const oriented = paths.map(orientPathLeftToRight);
  const { minX: boardMinX, maxX: boardMaxX } = boardBoundsX(oriented);
  const spanX = boardMaxX - boardMinX;
  if (spanX <= 0) return oriented;

  const viewHalfWidth = scanViewHalfWidth(spanX);
  const panDuration = panSpeed > 0 ? spanX / panSpeed : 0;
  // Time for the scan to travel from a line entering the frame's leading edge to
  // its centre passing that line; used to delay untouched lines off the edge.
  const frameLeadTime = spanX > 0 ? (viewHalfWidth / spanX) * panDuration : 0;
  const slots = new Map<string, ScanSlot>();

  const withScanSlots = oriented.map((path) => {
    const { minX: pathMinX, maxX: pathMaxX } = pathBoundsX(path.waypoints);
    const enterCamX = pathMinX - viewHalfWidth;
    const exitCamX = pathMaxX + viewHalfWidth;

    const tEnter = Math.max(
      startTime,
      startTime + ((enterCamX - boardMinX) / spanX) * panDuration,
    );
    const tExit = startTime + ((exitCamX - boardMinX) / spanX) * panDuration;
    const pathLength = totalPathLength(path.waypoints);

    if (path.id) {
      slots.set(path.id, { tEnter, tExit, pathLength });
    }

    const cursorSpeed = drawSpeedForWindow(
      pathLength,
      tEnter,
      tExit,
      drawFraction,
      speedScale,
      fallbackSpeed,
    );

    return { ...path, spawnTime: tEnter, cursorSpeed };
  });

  return floodSchedule(
    withScanSlots,
    slots,
    scannerParams,
    fallbackSpeed,
    frameLeadTime,
  );
}

function boardCenterXZ(paths: GridPath[]): Vec3 {
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (const path of paths) {
    for (const [x, , z] of path.waypoints) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;
    }
  }
  if (!Number.isFinite(minX)) return [0, 0, 0];
  return [(minX + maxX) * 0.5, 0, (minZ + maxZ) * 0.5];
}

/**
 * Whole-board transform (offset/rotationY/scale about the XZ center) plus an
 * optional per-line offset. Scale only affects the XZ footprint; height (Y) is
 * left to plain offset so components don't balloon off the board.
 */
function transformWaypoints(
  waypoints: Vec3[],
  transform: CircuitTuning["transform"],
  center: Vec3,
  perOffset?: Vec3,
): Vec3[] {
  const rad = (transform.rotationYDeg * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const ox = transform.offset[0] + (perOffset?.[0] ?? 0);
  const oy = transform.offset[1] + (perOffset?.[1] ?? 0);
  const oz = transform.offset[2] + (perOffset?.[2] ?? 0);

  return waypoints.map(([x, y, z]) => {
    const dx = (x - center[0]) * transform.scale;
    const dz = (z - center[2]) * transform.scale;
    const rx = dx * cos + dz * sin;
    const rz = -dx * sin + dz * cos;
    return [center[0] + rx + ox, y + oy, center[2] + rz + oz] as Vec3;
  });
}

/**
 * Waypoint transformer matching what `scheduledBaseline` applies to the visible
 * path set — for auxiliary geometry (e.g. mesh rise wireframes) that must land
 * in the same world space as the tuned board. Pass the SAME visible paths that
 * `applyTuning` will schedule so the rotation/scale pivot matches exactly.
 */
export function makeBoardTransform(
  visiblePaths: GridPath[],
  transform: CircuitTuning["transform"],
): (waypoints: Vec3[]) => Vec3[] {
  const center = boardCenterXZ(visiblePaths);
  return (waypoints) => transformWaypoints(waypoints, transform, center);
}

/**
 * Geometry + automatic schedule with NO per-line spawn/speed overrides applied.
 * Useful for showing the auto baseline in the tuner and for "bake" snapshots.
 */
export function scheduledBaseline(
  paths: GridPath[],
  tuning: CircuitTuning,
): GridPath[] {
  const center = boardCenterXZ(paths);
  const transformed = paths.map((p) => {
    const ov = p.id ? tuning.overrides[p.id] : undefined;
    return {
      ...p,
      hidden: ov?.hidden ?? false,
      waypoints: transformWaypoints(
        p.waypoints,
        tuning.transform,
        center,
        ov?.offset,
      ),
    };
  });
  const topologized = applyTopology(transformed, tuning.topology);
  return assignLeftToRightScanner(topologized, tuning.timing);
}

/** Full tuning: schedule, topology edits (display space), then per-line overrides. */
export function applyTuning(
  paths: GridPath[],
  tuning: CircuitTuning,
): GridPath[] {
  const deleted = new Set(tuning.topology.deleted);
  const visible = paths.filter((p) => p.id && !deleted.has(p.id));

  const scheduled = scheduledBaseline(visible, tuning);

  return scheduled.map((p) => {
    const ov = p.id ? tuning.overrides[p.id] : undefined;
    if (!ov) return p;

    let waypoints = p.waypoints;
    if (ov.reversed && waypoints.length >= 2) {
      waypoints = [...waypoints].reverse();
    }

    return {
      ...p,
      waypoints,
      spawnTime: ov.spawnTime ?? p.spawnTime,
      cursorSpeed: ov.cursorSpeed ?? p.cursorSpeed,
    };
  });
}

export function layoutFromPaths(paths: GridPath[]): CircuitsTracedLayout {
  const xs: number[] = [];
  const ys: number[] = [];
  const zs: number[] = [];

  for (const path of paths) {
    for (const [x, y, z] of path.waypoints) {
      xs.push(x);
      ys.push(y);
      zs.push(z);
    }
  }

  if (xs.length === 0) {
    return { paths, center: [0, 0, 0], span: 10 };
  }

  const center: Vec3 = [
    (Math.min(...xs) + Math.max(...xs)) * 0.5,
    (Math.min(...ys) + Math.max(...ys)) * 0.5,
    (Math.min(...zs) + Math.max(...zs)) * 0.5,
  ];
  const span = Math.max(
    Math.max(...xs) - Math.min(...xs),
    Math.max(...zs) - Math.min(...zs),
    Math.max(...ys) - Math.min(...ys),
  );

  return { paths, center, span };
}

export function tronPathsFromCircuitsTraced(): CircuitsTracedLayout {
  return layoutFromPaths(
    applyTuning(tracePathsFromCircuitsTraced(), PUBLISHED_TUNING),
  );
}
