import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import {
  componentFootprints,
} from "../lib/circuitComponentFootprints";
import {
  drawMeshBox,
  MESH_LABELS,
  MESH_PALETTE,
  type MeshKind,
  type MeshStyle,
} from "../lib/circuitMeshBoxes";
import {
  footprintsToMeshes,
  meshContains,
  meshHandleWorld,
  moveMeshBounds,
  resizeMeshFromCorner,
  resolveMeshes,
  type CircuitMesh,
  type MeshBounds,
  type MeshHandle,
} from "../lib/circuitMeshes";
import {
  applyTopology,
  previewSnapPoint,
  resolveSegmentGeom,
  type CircuitTopology,
  type SegmentGeom,
} from "../lib/circuitTopology";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  BOX_SELECT_PAD,
  inflateScreenRect,
  segmentIntersectsRect as segmentHitsRect,
  screenRect as boxScreenRect,
} from "../lib/circuitBoxSelect";
import { buildRawCircuitPaths } from "../lib/tronPathsFromCircuitsTraced";
import { useCircuitTuning, setEditPathsGetter } from "../stores/circuitTuning";
import {
  SHORTCUT_BTN,
  useShortcutButtonFlash,
} from "../hooks/useShortcutButtonFlash";
import "./CircuitCanvasEditor.css";

const OUTLINE_GLB_URL = "/models/circuits-traced-outline.glb";

const BG = "#04090b";
const GRID = "rgba(120, 200, 210, 0.05)";
const MESH_STYLE: MeshStyle = { fg: "#1bbfac", bg: BG };
const TRACE = "#3ee8d2";
const SELECTED = "#ffffff";
const PREVIEW = "#7af7e6";
const SNAP = "#ffd54a";
const HANDLE_STROKE = "#ffffff";

/** Click tolerance (CSS px) for picking a line. */
const PICK_PX = 6;
/** Hit radius (CSS px) for grabbing an endpoint handle. */
const HANDLE_PX = 9;
/** Movement (CSS px) past which a press becomes a pan instead of a click. */
const DRAG_THRESHOLD = 4;

const MIN_SCALE = 2;
const MAX_SCALE = 600;

type View = { scale: number; offsetX: number; offsetY: number };

type ScreenPt = { sx: number; sy: number };

type ScreenRect = { l: number; t: number; r: number; b: number };

type Interaction =
  | { kind: "none" }
  | { kind: "pan"; startSx: number; startSy: number; startOX: number; startOY: number }
  | {
      kind: "maybe";
      startSx: number;
      startSy: number;
      startOX: number;
      startOY: number;
      panning: boolean;
    }
  | {
      kind: "boxSelect";
      startSx: number;
      startSy: number;
      endSx: number;
      endSy: number;
    }
  | {
      kind: "vertex";
      segmentId: string;
      end: 0 | 1;
      baseGeom: { start: Vec3; end: Vec3 };
    }
  | {
      kind: "meshCorner";
      meshId: string;
      handle: MeshHandle;
      startBounds: MeshBounds;
    }
  | {
      kind: "meshMove";
      meshId: string;
      startBounds: MeshBounds;
      startWorldX: number;
      startWorldZ: number;
      pushedUndo: boolean;
    }
  | {
      kind: "groupMove";
      startWorldX: number;
      startWorldZ: number;
      startLineGeoms: Record<string, SegmentGeom>;
      startMeshBounds: Record<string, MeshBounds>;
      pushedUndo: boolean;
    }
  | {
      kind: "groupScale";
      handle: MeshHandle;
      startGroupBounds: MeshBounds;
      startLineGeoms: Record<string, SegmentGeom>;
      startMeshBounds: Record<string, MeshBounds>;
    };

function isEditableLine(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
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
  const t =
    len2 > 1e-9
      ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2))
      : 0;
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function screenRect(x0: number, y0: number, x1: number, y1: number): ScreenRect {
  return {
    l: Math.min(x0, x1),
    r: Math.max(x0, x1),
    t: Math.min(y0, y1),
    b: Math.max(y0, y1),
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

function segmentIntersectsRect(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  rect: ScreenRect,
): boolean {
  if (pointInRect(ax, ay, rect) || pointInRect(bx, by, rect)) return true;
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

const MIN_GROUP_DIM = 0.8;

function isGroupSelection(lineIds: string[], meshIds: string[]): boolean {
  return lineIds.length + meshIds.length > 1;
}

function computeGroupBounds(
  paths: GridPath[],
  meshes: CircuitMesh[],
  lineIds: string[],
  meshIds: string[],
): MeshBounds | null {
  const lineSet = new Set(lineIds);
  const meshSet = new Set(meshIds);
  let minX = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxZ = -Infinity;
  for (const p of paths) {
    if (!p.id || !lineSet.has(p.id) || p.waypoints.length < 2) continue;
    for (const [x, , z] of p.waypoints) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minZ = Math.min(minZ, z);
      maxZ = Math.max(maxZ, z);
    }
  }
  for (const m of meshes) {
    if (!meshSet.has(m.id)) continue;
    minX = Math.min(minX, m.minX);
    maxX = Math.max(maxX, m.maxX);
    minZ = Math.min(minZ, m.minZ);
    maxZ = Math.max(maxZ, m.maxZ);
  }
  if (!Number.isFinite(minX)) return null;
  return { minX, maxX, minZ, maxZ };
}

type SelectionSnapshot = {
  groupBounds: MeshBounds;
  lineGeoms: Record<string, SegmentGeom>;
  meshBounds: Record<string, MeshBounds>;
};

function captureSelectionSnapshot(
  paths: GridPath[],
  meshes: CircuitMesh[],
  lineIds: string[],
  meshIds: string[],
  topology: CircuitTopology,
): SelectionSnapshot | null {
  const groupBounds = computeGroupBounds(paths, meshes, lineIds, meshIds);
  if (!groupBounds) return null;

  const lineSet = new Set(lineIds);
  const meshSet = new Set(meshIds);
  const lineGeoms: Record<string, SegmentGeom> = {};
  const meshBounds: Record<string, MeshBounds> = {};

  for (const p of paths) {
    if (!p.id || !lineSet.has(p.id)) continue;
    const geom = resolveSegmentGeom(p, topology);
    if (geom) lineGeoms[p.id] = geom;
  }
  for (const m of meshes) {
    if (!meshSet.has(m.id)) continue;
    meshBounds[m.id] = {
      minX: m.minX,
      maxX: m.maxX,
      minZ: m.minZ,
      maxZ: m.maxZ,
    };
  }

  return { groupBounds, lineGeoms, meshBounds };
}

function moveSegmentGeom(geom: SegmentGeom, dx: number, dz: number): SegmentGeom {
  return {
    start: [geom.start[0] + dx, geom.start[1], geom.start[2] + dz],
    end: [geom.end[0] + dx, geom.end[1], geom.end[2] + dz],
  };
}

function scaleXZ(
  x: number,
  z: number,
  anchorX: number,
  anchorZ: number,
  sx: number,
  sz: number,
): { x: number; z: number } {
  return {
    x: anchorX + (x - anchorX) * sx,
    z: anchorZ + (z - anchorZ) * sz,
  };
}

function scaleSegmentGeom(
  geom: SegmentGeom,
  anchorX: number,
  anchorZ: number,
  sx: number,
  sz: number,
): SegmentGeom {
  const a = scaleXZ(geom.start[0], geom.start[2], anchorX, anchorZ, sx, sz);
  const b = scaleXZ(geom.end[0], geom.end[2], anchorX, anchorZ, sx, sz);
  return {
    start: [a.x, geom.start[1], a.z],
    end: [b.x, geom.end[1], b.z],
  };
}

function scaleMeshBounds(
  bounds: MeshBounds,
  anchorX: number,
  anchorZ: number,
  sx: number,
  sz: number,
): MeshBounds {
  const nw = scaleXZ(bounds.minX, bounds.minZ, anchorX, anchorZ, sx, sz);
  const se = scaleXZ(bounds.maxX, bounds.maxZ, anchorX, anchorZ, sx, sz);
  return {
    minX: Math.min(nw.x, se.x),
    maxX: Math.max(nw.x, se.x),
    minZ: Math.min(nw.z, se.z),
    maxZ: Math.max(nw.z, se.z),
  };
}

function scaleFactorsFromHandle(
  handle: MeshHandle,
  start: MeshBounds,
  x: number,
  z: number,
): { anchorX: number; anchorZ: number; sx: number; sz: number } {
  const w = Math.max(start.maxX - start.minX, 1e-6);
  const h = Math.max(start.maxZ - start.minZ, 1e-6);
  const minSx = MIN_GROUP_DIM / w;
  const minSz = MIN_GROUP_DIM / h;

  switch (handle) {
    case "se": {
      const anchorX = start.minX;
      const anchorZ = start.minZ;
      return {
        anchorX,
        anchorZ,
        sx: Math.max(minSx, (x - anchorX) / w),
        sz: Math.max(minSz, (z - anchorZ) / h),
      };
    }
    case "nw": {
      const anchorX = start.maxX;
      const anchorZ = start.maxZ;
      return {
        anchorX,
        anchorZ,
        sx: Math.max(minSx, (anchorX - x) / w),
        sz: Math.max(minSz, (anchorZ - z) / h),
      };
    }
    case "ne": {
      const anchorX = start.minX;
      const anchorZ = start.maxZ;
      return {
        anchorX,
        anchorZ,
        sx: Math.max(minSx, (x - anchorX) / w),
        sz: Math.max(minSz, (anchorZ - z) / h),
      };
    }
    case "sw": {
      const anchorX = start.maxX;
      const anchorZ = start.minZ;
      return {
        anchorX,
        anchorZ,
        sx: Math.max(minSx, (anchorX - x) / w),
        sz: Math.max(minSz, (z - anchorZ) / h),
      };
    }
  }
}

function hasMovableSelection(lineIds: string[], meshIds: string[]): boolean {
  return lineIds.length + meshIds.length > 0;
}

function padGroupBounds(bounds: MeshBounds, minDim: number): MeshBounds {
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cz = (bounds.minZ + bounds.maxZ) / 2;
  const w = Math.max(bounds.maxX - bounds.minX, minDim);
  const h = Math.max(bounds.maxZ - bounds.minZ, minDim);
  return {
    minX: cx - w / 2,
    maxX: cx + w / 2,
    minZ: cz - h / 2,
    maxZ: cz + h / 2,
  };
}

function pointInGroupBounds(x: number, z: number, bounds: MeshBounds): boolean {
  return x >= bounds.minX && x <= bounds.maxX && z >= bounds.minZ && z <= bounds.maxZ;
}

function resolveLineMoveSelection(
  hitId: string,
  selectedLineIds: string[],
  selectedMeshIds: string[],
  additiveKey: boolean,
): { lineIds: string[]; meshIds: string[]; selectOnly: boolean } | null {
  if (additiveKey) {
    const next = selectedLineIds.includes(hitId)
      ? selectedLineIds.filter((id) => id !== hitId)
      : [...selectedLineIds, hitId];
    return { lineIds: next, meshIds: selectedMeshIds, selectOnly: true };
  }

  if (selectedLineIds.includes(hitId)) {
    return { lineIds: selectedLineIds, meshIds: selectedMeshIds };
  }

  return { lineIds: [hitId], meshIds: [] };
}

function beginSelectionMove(
  interaction: React.MutableRefObject<Interaction>,
  snap: SelectionSnapshot,
  sx: number,
  sy: number,
  screenToWorld: (sx: number, sy: number) => { x: number; z: number },
): void {
  const { x, z } = screenToWorld(sx, sy);
  interaction.current = {
    kind: "groupMove",
    startWorldX: x,
    startWorldZ: z,
    startLineGeoms: snap.lineGeoms,
    startMeshBounds: snap.meshBounds,
    pushedUndo: false,
  };
}

function drawHandle(
  ctx: CanvasRenderingContext2D,
  sx: number,
  sy: number,
): void {
  ctx.beginPath();
  ctx.rect(sx - 4, sy - 4, 8, 8);
  ctx.fillStyle = BG;
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = HANDLE_STROKE;
  ctx.stroke();
}

export default function CircuitCanvasEditor() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const rawPathsRef = useRef<GridPath[]>([]);
  const baselineMeshesRef = useRef<CircuitMesh[]>([]);
  const baseYRef = useRef(0);
  const viewRef = useRef<View>({ scale: 10, offsetX: 0, offsetY: 0 });
  const sizeRef = useRef({ w: 0, h: 0 });
  const interactionRef = useRef<Interaction>({ kind: "none" });
  const addPreviewRef = useRef<Vec3 | null>(null);
  const snapRef = useRef<Vec3 | null>(null);
  const spaceDownRef = useRef(false);
  const drawRef = useRef<() => void>(() => {});
  const pathsCacheRef = useRef<{ key: unknown; paths: GridPath[] }>({
    key: null,
    paths: [],
  });
  const meshesCacheRef = useRef<{ key: unknown; meshes: CircuitMesh[] }>({
    key: null,
    meshes: [],
  });

  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState("");
  const { flash: flashShortcutBtn, btnClass, btnTitle } = useShortcutButtonFlash();

  const editTool = useCircuitTuning((s) => s.editTool);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedMeshIds = useCircuitTuning((s) => s.selectedMeshIds);
  const clipboardLineCount = useCircuitTuning((s) => s.clipboardLineCount);
  const selectedLineSet = useMemo(
    () => new Set(selectedLineIds),
    [selectedLineIds],
  );
  const selectedMeshSet = useMemo(
    () => new Set(selectedMeshIds),
    [selectedMeshIds],
  );
  const addLineStart = useCircuitTuning((s) => s.addLineStart);
  const addMeshKind = useCircuitTuning((s) => s.addMeshKind);
  const meshEdits = useCircuitTuning((s) => s.meshEdits);

  // Live segment geometry from the current topology (board transform is identity
  // for circuits, so topology space == on-screen world space).
  const getPaths = useCallback((): GridPath[] => {
    const topology = useCircuitTuning.getState().topology;
    if (pathsCacheRef.current.key !== topology) {
      pathsCacheRef.current = {
        key: topology,
        paths: applyTopology(rawPathsRef.current, topology),
      };
    }
    return pathsCacheRef.current.paths;
  }, []);

  const getMeshes = useCallback((): CircuitMesh[] => {
    const edits = useCircuitTuning.getState().meshEdits;
    if (meshesCacheRef.current.key !== edits) {
      meshesCacheRef.current = {
        key: edits,
        meshes: resolveMeshes(baselineMeshesRef.current, edits),
      };
    }
    return meshesCacheRef.current.meshes;
  }, []);

  const worldToScreen = useCallback((x: number, z: number): ScreenPt => {
    const v = viewRef.current;
    return { sx: x * v.scale + v.offsetX, sy: z * v.scale + v.offsetY };
  }, []);

  const screenToWorld = useCallback((sx: number, sy: number) => {
    const v = viewRef.current;
    return { x: (sx - v.offsetX) / v.scale, z: (sy - v.offsetY) / v.scale };
  }, []);

  const localPos = useCallback((clientX: number, clientY: number): ScreenPt => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { sx: clientX - rect.left, sy: clientY - rect.top };
  }, []);

  const worldPointAt = useCallback(
    (sx: number, sy: number): Vec3 => {
      const { x, z } = screenToWorld(sx, sy);
      return [x, baseYRef.current, z];
    },
    [screenToWorld],
  );

  const fitView = useCallback(() => {
    const paths = getPaths();
    const meshes = getMeshes();
    let minX = Infinity;
    let minZ = Infinity;
    let maxX = -Infinity;
    let maxZ = -Infinity;
    const add = (x: number, z: number) => {
      minX = Math.min(minX, x);
      minZ = Math.min(minZ, z);
      maxX = Math.max(maxX, x);
      maxZ = Math.max(maxZ, z);
    };
    for (const p of paths) for (const [x, , z] of p.waypoints) add(x, z);
    for (const m of meshes) {
      add(m.minX, m.minZ);
      add(m.maxX, m.maxZ);
    }
    if (!Number.isFinite(minX)) return;

    const { w, h } = sizeRef.current;
    const worldW = maxX - minX || 1;
    const worldH = maxZ - minZ || 1;
    const scale = Math.max(
      MIN_SCALE,
      Math.min(MAX_SCALE, Math.min(w / worldW, h / worldH) * 0.9),
    );
    viewRef.current = {
      scale,
      offsetX: w / 2 - ((minX + maxX) / 2) * scale,
      offsetY: h / 2 - ((minZ + maxZ) / 2) * scale,
    };
  }, [getPaths, getMeshes]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const { w, h } = sizeRef.current;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);

    // Faint world grid for orientation; spacing kept roughly 24-80 px on screen.
    const v = viewRef.current;
    let step = 1;
    while (step * v.scale < 24) step *= 2;
    while (step * v.scale > 80) step /= 2;
    const left = -v.offsetX / v.scale;
    const right = (w - v.offsetX) / v.scale;
    const top = -v.offsetY / v.scale;
    const bottom = (h - v.offsetY) / v.scale;
    ctx.beginPath();
    for (let x = Math.floor(left / step) * step; x <= right; x += step) {
      const sx = x * v.scale + v.offsetX;
      ctx.moveTo(sx, 0);
      ctx.lineTo(sx, h);
    }
    for (let z = Math.floor(top / step) * step; z <= bottom; z += step) {
      const sy = z * v.scale + v.offsetY;
      ctx.moveTo(0, sy);
      ctx.lineTo(w, sy);
    }
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Component meshes: plain labeled boxes (edges meet traces, no pin tabs).
    const meshes = getMeshes();
    for (const m of meshes) {
      const a = worldToScreen(m.minX, m.minZ);
      const b = worldToScreen(m.maxX, m.maxZ);
      drawMeshBox(
        ctx,
        { x: a.sx, y: a.sy, w: b.sx - a.sx, h: b.sy - a.sy },
        m.kind,
        MESH_STYLE,
      );
    }

    for (const m of meshes) {
      if (!selectedMeshSet.has(m.id)) continue;
      const a = worldToScreen(m.minX, m.minZ);
      const b = worldToScreen(m.maxX, m.maxZ);
      ctx.strokeStyle = SELECTED;
      ctx.lineWidth = 2;
      ctx.strokeRect(a.sx, a.sy, b.sx - a.sx, b.sy - a.sy);
    }

    const soleMesh =
      selectedMeshIds.length === 1 && selectedLineIds.length === 0
        ? meshes.find((m) => m.id === selectedMeshIds[0])
        : undefined;
    if (soleMesh) {
      for (const handle of ["nw", "ne", "sw", "se"] as const) {
        const p = meshHandleWorld(soleMesh, handle);
        const s = worldToScreen(p.x, p.z);
        drawHandle(ctx, s.sx, s.sy);
      }
    }

    const paths = getPaths();

    const groupSel = isGroupSelection(selectedLineIds, selectedMeshIds);
    const groupBounds = groupSel
      ? computeGroupBounds(paths, meshes, selectedLineIds, selectedMeshIds)
      : null;
    if (groupBounds) {
      const a = worldToScreen(groupBounds.minX, groupBounds.minZ);
      const b = worldToScreen(groupBounds.maxX, groupBounds.maxZ);
      ctx.strokeStyle = SELECTED;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);
      ctx.strokeRect(a.sx, a.sy, b.sx - a.sx, b.sy - a.sy);
      ctx.setLineDash([]);
      for (const handle of ["nw", "ne", "sw", "se"] as const) {
        const p = meshHandleWorld(groupBounds, handle);
        const s = worldToScreen(p.x, p.z);
        drawHandle(ctx, s.sx, s.sy);
      }
    }
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.shadowColor = TRACE;
    for (const p of paths) {
      if (!isEditableLine(p.id) || p.hidden || p.waypoints.length < 2) continue;
      const a = worldToScreen(p.waypoints[0][0], p.waypoints[0][2]);
      const b = worldToScreen(p.waypoints[1][0], p.waypoints[1][2]);
      const isSel = selectedLineSet.has(p.id!);
      ctx.beginPath();
      ctx.moveTo(a.sx, a.sy);
      ctx.lineTo(b.sx, b.sy);
      ctx.strokeStyle = isSel ? SELECTED : TRACE;
      ctx.lineWidth = isSel ? 2.4 : 1.6;
      ctx.shadowBlur = isSel ? 0 : 5;
      ctx.stroke();
    }
    ctx.shadowBlur = 0;

    // Selected endpoint handles.
    const soleLine =
      selectedLineIds.length === 1 && selectedMeshIds.length === 0
        ? paths.find(
            (p) => p.id === selectedLineIds[0] && isEditableLine(p.id),
          )
        : undefined;
    if (soleLine && soleLine.waypoints.length >= 2) {
      for (const wp of [soleLine.waypoints[0], soleLine.waypoints[1]]) {
        const s = worldToScreen(wp[0], wp[2]);
        drawHandle(ctx, s.sx, s.sy);
      }
    }

    // Add-line rubber band.
    const start = useCircuitTuning.getState().addLineStart;
    const preview = addPreviewRef.current;
    if (editTool === "addLine" && start && preview) {
      const a = worldToScreen(start[0], start[2]);
      const b = worldToScreen(preview[0], preview[2]);
      ctx.beginPath();
      ctx.setLineDash([5, 4]);
      ctx.moveTo(a.sx, a.sy);
      ctx.lineTo(b.sx, b.sy);
      ctx.strokeStyle = PREVIEW;
      ctx.lineWidth = 1.6;
      ctx.stroke();
      ctx.setLineDash([]);
      dot(ctx, a.sx, a.sy, PREVIEW);
    }

    // Snap indicator.
    if (snapRef.current) {
      const s = worldToScreen(snapRef.current[0], snapRef.current[2]);
      ctx.beginPath();
      ctx.arc(s.sx, s.sy, 6, 0, Math.PI * 2);
      ctx.strokeStyle = SNAP;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    const it = interactionRef.current;
    if (it.kind === "boxSelect") {
      const x = Math.min(it.startSx, it.endSx);
      const y = Math.min(it.startSy, it.endSy);
      const bw = Math.abs(it.endSx - it.startSx);
      const bh = Math.abs(it.endSy - it.startSy);
      ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
      ctx.fillRect(x, y, bw, bh);
      ctx.strokeStyle = SELECTED;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x, y, bw, bh);
      ctx.setLineDash([]);
    }
  }, [
    editTool,
    getMeshes,
    getPaths,
    selectedLineIds,
    selectedLineSet,
    selectedMeshIds,
    selectedMeshSet,
    worldToScreen,
  ]);

  drawRef.current = draw;

  useEffect(() => {
    setEditPathsGetter(getPaths);
    return () => setEditPathsGetter(null);
  }, [getPaths]);

  // Load the GLB once, derive raw paths + footprints + base plane.
  useEffect(() => {
    let cancelled = false;
    new GLTFLoader().load(OUTLINE_GLB_URL, (gltf) => {
      if (cancelled) return;
      const raw = buildRawCircuitPaths(gltf.scene);
      rawPathsRef.current = raw;
      baselineMeshesRef.current = footprintsToMeshes(componentFootprints(raw));
      meshesCacheRef.current = { key: null, meshes: [] };
      let by = Infinity;
      for (const p of raw) for (const [, y] of p.waypoints) by = Math.min(by, y);
      baseYRef.current = Number.isFinite(by) ? by : 0;
      pathsCacheRef.current = { key: null, paths: [] };
      fitView();
      setLoaded(true);
      drawRef.current();
    });
    return () => {
      cancelled = true;
    };
  }, [fitView]);

  // Size tracking + redraw on resize.
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = container.clientWidth;
      const h = container.clientHeight;
      sizeRef.current = { w, h };
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      drawRef.current();
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Redraw on any store change (selection, tool, topology edits).
  useEffect(() => {
    const unsub = useCircuitTuning.subscribe(() => drawRef.current());
    return unsub;
  }, []);

  useEffect(() => {
    drawRef.current();
  }, [editTool, selectedLineIds, selectedMeshIds, addLineStart, addMeshKind, meshEdits, loaded]);

  // Space toggles temporary pan mode.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.code === "Space") spaceDownRef.current = true;
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") spaceDownRef.current = false;
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  // Wheel zoom (native listener so preventDefault works).
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const { sx, sy } = localPos(e.clientX, e.clientY);
      const before = screenToWorld(sx, sy);
      const v = viewRef.current;
      const factor = Math.exp(-e.deltaY * 0.0015);
      v.scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, v.scale * factor));
      v.offsetX = sx - before.x * v.scale;
      v.offsetY = sy - before.z * v.scale;
      drawRef.current();
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [localPos, screenToWorld]);

  // --- Hit testing -----------------------------------------------------------

  const meshHandleHitTest = useCallback(
    (sx: number, sy: number): MeshHandle | null => {
      const meshIds = useCircuitTuning.getState().selectedMeshIds;
      const lineIds = useCircuitTuning.getState().selectedLineIds;
      if (meshIds.length !== 1 || lineIds.length !== 0) return null;
      const mesh = getMeshes().find((m) => m.id === meshIds[0]);
      if (!mesh) return null;
      for (const handle of ["nw", "ne", "sw", "se"] as const) {
        const p = meshHandleWorld(mesh, handle);
        const s = worldToScreen(p.x, p.z);
        if (Math.hypot(sx - s.sx, sy - s.sy) <= HANDLE_PX) return handle;
      }
      return null;
    },
    [getMeshes, worldToScreen],
  );

  const groupHandleHitTest = useCallback(
    (sx: number, sy: number): MeshHandle | null => {
      const { selectedLineIds, selectedMeshIds } = useCircuitTuning.getState();
      if (!isGroupSelection(selectedLineIds, selectedMeshIds)) return null;
      const bounds = computeGroupBounds(
        getPaths(),
        getMeshes(),
        selectedLineIds,
        selectedMeshIds,
      );
      if (!bounds) return null;
      for (const handle of ["nw", "ne", "sw", "se"] as const) {
        const p = meshHandleWorld(bounds, handle);
        const s = worldToScreen(p.x, p.z);
        if (Math.hypot(sx - s.sx, sy - s.sy) <= HANDLE_PX) return handle;
      }
      return null;
    },
    [getMeshes, getPaths, worldToScreen],
  );

  const meshHitTest = useCallback(
    (sx: number, sy: number): string | null => {
      const { x, z } = screenToWorld(sx, sy);
      const meshes = getMeshes();
      for (let i = meshes.length - 1; i >= 0; i--) {
        const m = meshes[i];
        if (meshContains(m, x, z)) return m.id;
      }
      return null;
    },
    [getMeshes, screenToWorld],
  );

  const handleHitTest = useCallback(
    (sx: number, sy: number): 0 | 1 | null => {
      const lineIds = useCircuitTuning.getState().selectedLineIds;
      const meshIds = useCircuitTuning.getState().selectedMeshIds;
      if (lineIds.length !== 1 || meshIds.length !== 0) return null;
      const id = lineIds[0];
      const seg = getPaths().find((p) => p.id === id);
      if (!seg || seg.waypoints.length < 2) return null;
      for (const end of [0, 1] as const) {
        const wp = seg.waypoints[end];
        const s = worldToScreen(wp[0], wp[2]);
        if (Math.hypot(sx - s.sx, sy - s.sy) <= HANDLE_PX) return end;
      }
      return null;
    },
    [getPaths, worldToScreen],
  );

  const lineHitTest = useCallback(
    (sx: number, sy: number): string | null => {
      let bestId: string | null = null;
      let bestDist = PICK_PX;
      for (const p of getPaths()) {
        if (!isEditableLine(p.id) || p.hidden || p.waypoints.length < 2) continue;
        const a = worldToScreen(p.waypoints[0][0], p.waypoints[0][2]);
        const b = worldToScreen(p.waypoints[1][0], p.waypoints[1][2]);
        const d = distToSegmentPx(sx, sy, a.sx, a.sy, b.sx, b.sy);
        if (d <= bestDist) {
          bestDist = d;
          bestId = p.id!;
        }
      }
      return bestId;
    },
    [getPaths, worldToScreen],
  );

  const linesInBox = useCallback(
    (x0: number, y0: number, x1: number, y1: number): string[] => {
      const rect = inflateScreenRect(boxScreenRect(x0, y0, x1, y1), BOX_SELECT_PAD);
      const ids: string[] = [];
      for (const p of getPaths()) {
        if (!isEditableLine(p.id) || p.hidden || p.waypoints.length < 2) continue;
        let hit = false;
        for (let i = 0; i < p.waypoints.length - 1; i++) {
          const a = worldToScreen(p.waypoints[i][0], p.waypoints[i][2]);
          const b = worldToScreen(p.waypoints[i + 1][0], p.waypoints[i + 1][2]);
          if (segmentHitsRect(a.sx, a.sy, b.sx, b.sy, rect)) {
            hit = true;
            break;
          }
        }
        if (hit) ids.push(p.id!);
      }
      return ids;
    },
    [getPaths, worldToScreen],
  );

  const meshesInBox = useCallback(
    (x0: number, y0: number, x1: number, y1: number): string[] => {
      const rect = screenRect(x0, y0, x1, y1);
      const ids: string[] = [];
      for (const m of getMeshes()) {
        const a = worldToScreen(m.minX, m.minZ);
        const b = worldToScreen(m.maxX, m.maxZ);
        const meshRect = screenRect(a.sx, a.sy, b.sx, b.sy);
        if (rectsOverlap(rect, meshRect)) ids.push(m.id);
      }
      return ids;
    },
    [getMeshes, worldToScreen],
  );

  // --- Pointer interactions --------------------------------------------------

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const { sx, sy } = localPos(e.clientX, e.clientY);
      const store = useCircuitTuning.getState();
      canvasRef.current?.focus({ preventScroll: true });
      canvasRef.current?.setPointerCapture(e.pointerId);

      const wantsPan = e.button === 1 || spaceDownRef.current;
      const v = viewRef.current;
      if (wantsPan) {
        interactionRef.current = {
          kind: "pan",
          startSx: sx,
          startSy: sy,
          startOX: v.offsetX,
          startOY: v.offsetY,
        };
        return;
      }

      if (store.editTool === "addLine") {
        const point = snapNew(worldPointAt(sx, sy), getPaths());
        if (!store.addLineStart) {
          store.pushUndo();
          store.setAddLineStart(point);
        } else {
          store.addLineSegment(store.addLineStart, point);
        }
        addPreviewRef.current = point;
        drawRef.current();
        return;
      }

      if (store.editTool === "addMesh" && store.addMeshKind) {
        store.pushUndo();
        const { x, z } = screenToWorld(sx, sy);
        store.addMeshAt(store.addMeshKind, x, z);
        drawRef.current();
        return;
      }

      if (store.editTool === "split") {
        const hitId = lineHitTest(sx, sy);
        if (hitId && store.selectedLineIds.includes(hitId)) {
          store.splitSegmentAtPoint(getPaths(), hitId, worldPointAt(sx, sy));
          drawRef.current();
        }
        return;
      }

      if (e.shiftKey && store.editTool === "select") {
        interactionRef.current = {
          kind: "boxSelect",
          startSx: sx,
          startSy: sy,
          endSx: sx,
          endSy: sy,
        };
        return;
      }

      const groupSel = isGroupSelection(
        store.selectedLineIds,
        store.selectedMeshIds,
      );

      if (groupSel) {
        const groupHandle = groupHandleHitTest(sx, sy);
        if (groupHandle !== null) {
          const snap = captureSelectionSnapshot(
            getPaths(),
            getMeshes(),
            store.selectedLineIds,
            store.selectedMeshIds,
            store.topology,
          );
          if (snap) {
            store.pushUndo();
            interactionRef.current = {
              kind: "groupScale",
              handle: groupHandle,
              startGroupBounds: snap.groupBounds,
              startLineGeoms: snap.lineGeoms,
              startMeshBounds: snap.meshBounds,
            };
            return;
          }
        }
      }

      // Mesh corner handle (scale) — single mesh only.
      const meshHandle = meshHandleHitTest(sx, sy);
      if (meshHandle !== null) {
        const mesh = getMeshes().find(
          (m) => m.id === store.selectedMeshIds[0],
        );
        if (mesh) {
          store.pushUndo();
          interactionRef.current = {
            kind: "meshCorner",
            meshId: mesh.id,
            handle: meshHandle,
            startBounds: {
              minX: mesh.minX,
              maxX: mesh.maxX,
              minZ: mesh.minZ,
              maxZ: mesh.maxZ,
            },
          };
          return;
        }
      }

      // Select tool: line vertex (single line), mesh body move, line, mesh.
      const handleEnd = handleHitTest(sx, sy);
      if (handleEnd !== null) {
        const seg = getPaths().find((p) => p.id === store.selectedLineIds[0]);
        const baseGeom = seg
          ? resolveSegmentGeom(seg, store.topology)
          : null;
        if (baseGeom) {
          store.pushUndo();
          store.setDraggingVertex(true);
          interactionRef.current = {
            kind: "vertex",
            segmentId: store.selectedLineIds[0],
            end: handleEnd,
            baseGeom,
          };
          return;
        }
      }

      const hitId = lineHitTest(sx, sy);
      if (hitId) {
        const resolved = resolveLineMoveSelection(
          hitId,
          store.selectedLineIds,
          store.selectedMeshIds,
          e.metaKey,
        );
        if (!resolved) return;

        if (resolved.selectOnly) {
          store.setBoxSelection(resolved.lineIds, resolved.meshIds);
          return;
        }

        if (
          resolved.lineIds.length === 1 &&
          resolved.meshIds.length === 0 &&
          !store.selectedLineIds.includes(hitId)
        ) {
          store.select(hitId);
        }

        const snap = captureSelectionSnapshot(
          getPaths(),
          getMeshes(),
          resolved.lineIds,
          resolved.meshIds,
          store.topology,
        );
        if (snap) {
          beginSelectionMove(
            interactionRef,
            snap,
            sx,
            sy,
            screenToWorld,
          );
          return;
        }
      }

      const hitMeshId = meshHitTest(sx, sy);
      if (hitMeshId) {
        const mesh = getMeshes().find((m) => m.id === hitMeshId);
        if (mesh) {
          if (e.metaKey) {
            const nextMeshIds = store.selectedMeshIds.includes(hitMeshId)
              ? store.selectedMeshIds.filter((id) => id !== hitMeshId)
              : [...store.selectedMeshIds, hitMeshId];
            store.setBoxSelection(store.selectedLineIds, nextMeshIds);
            return;
          }
          if (
            hasMovableSelection(store.selectedLineIds, store.selectedMeshIds) &&
            store.selectedMeshIds.includes(hitMeshId)
          ) {
            const snap = captureSelectionSnapshot(
              getPaths(),
              getMeshes(),
              store.selectedLineIds,
              store.selectedMeshIds,
              store.topology,
            );
            if (snap) {
              beginSelectionMove(
                interactionRef,
                snap,
                sx,
                sy,
                screenToWorld,
              );
              return;
            }
          }
          store.selectMesh(hitMeshId);
          const { x, z } = screenToWorld(sx, sy);
          interactionRef.current = {
            kind: "meshMove",
            meshId: hitMeshId,
            startBounds: {
              minX: mesh.minX,
              maxX: mesh.maxX,
              minZ: mesh.minZ,
              maxZ: mesh.maxZ,
            },
            startWorldX: x,
            startWorldZ: z,
            pushedUndo: false,
          };
          return;
        }
      }

      if (hasMovableSelection(store.selectedLineIds, store.selectedMeshIds)) {
        const snap = captureSelectionSnapshot(
          getPaths(),
          getMeshes(),
          store.selectedLineIds,
          store.selectedMeshIds,
          store.topology,
        );
        if (snap) {
          const { x, z } = screenToWorld(sx, sy);
          const hitBounds = isGroupSelection(
            store.selectedLineIds,
            store.selectedMeshIds,
          )
            ? snap.groupBounds
            : padGroupBounds(snap.groupBounds, MIN_GROUP_DIM);
          if (pointInGroupBounds(x, z, hitBounds)) {
            beginSelectionMove(
              interactionRef,
              snap,
              sx,
              sy,
              screenToWorld,
            );
            return;
          }
        }
      }

      interactionRef.current = {
        kind: "maybe",
        startSx: sx,
        startSy: sy,
        startOX: v.offsetX,
        startOY: v.offsetY,
        panning: false,
      };
    },
    [
      getMeshes,
      getPaths,
      groupHandleHitTest,
      handleHitTest,
      lineHitTest,
      linesInBox,
      meshesInBox,
      localPos,
      meshHandleHitTest,
      meshHitTest,
      screenToWorld,
      worldPointAt,
    ],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const { sx, sy } = localPos(e.clientX, e.clientY);
      const it = interactionRef.current;
      const store = useCircuitTuning.getState();

      if (it.kind === "pan") {
        const v = viewRef.current;
        v.offsetX = it.startOX + (sx - it.startSx);
        v.offsetY = it.startOY + (sy - it.startSy);
        drawRef.current();
        return;
      }

      if (it.kind === "boxSelect") {
        it.endSx = sx;
        it.endSy = sy;
        drawRef.current();
        return;
      }

      if (it.kind === "maybe") {
        if (
          !it.panning &&
          Math.hypot(sx - it.startSx, sy - it.startSy) > DRAG_THRESHOLD
        ) {
          it.panning = true;
        }
        if (it.panning) {
          const v = viewRef.current;
          v.offsetX = it.startOX + (sx - it.startSx);
          v.offsetY = it.startOY + (sy - it.startSy);
          drawRef.current();
        }
        return;
      }

      if (it.kind === "vertex") {
        const point = worldPointAt(sx, sy);
        store.setVertices([
          { segmentId: it.segmentId, end: it.end, point, baseGeom: it.baseGeom },
        ]);
        snapRef.current = previewSnapPoint(point, getPaths(), it.segmentId);
        drawRef.current();
        return;
      }

      if (it.kind === "meshCorner") {
        const { x, z } = screenToWorld(sx, sy);
        const next = resizeMeshFromCorner(it.startBounds, it.handle, x, z);
        store.setMeshBounds(it.meshId, next);
        drawRef.current();
        return;
      }

      if (it.kind === "meshMove") {
        const { x, z } = screenToWorld(sx, sy);
        const dx = x - it.startWorldX;
        const dz = z - it.startWorldZ;
        if (
          !it.pushedUndo &&
          (Math.abs(dx) > 0.02 || Math.abs(dz) > 0.02)
        ) {
          store.pushUndo();
          it.pushedUndo = true;
        }
        if (it.pushedUndo) {
          store.setMeshBounds(
            it.meshId,
            moveMeshBounds(it.startBounds, dx, dz),
          );
        }
        drawRef.current();
        return;
      }

      if (it.kind === "groupMove") {
        const { x, z } = screenToWorld(sx, sy);
        const dx = x - it.startWorldX;
        const dz = z - it.startWorldZ;
        if (
          !it.pushedUndo &&
          (Math.abs(dx) > 0.02 || Math.abs(dz) > 0.02)
        ) {
          store.pushUndo();
          it.pushedUndo = true;
        }
        if (it.pushedUndo) {
          const lineGeoms: Record<string, SegmentGeom> = {};
          for (const [id, geom] of Object.entries(it.startLineGeoms)) {
            lineGeoms[id] = moveSegmentGeom(geom, dx, dz);
          }
          const meshBounds: Record<string, MeshBounds> = {};
          for (const [id, bounds] of Object.entries(it.startMeshBounds)) {
            meshBounds[id] = moveMeshBounds(bounds, dx, dz);
          }
          store.setLineGeometries(lineGeoms);
          store.setMeshBoundsMap(meshBounds);
        }
        drawRef.current();
        return;
      }

      if (it.kind === "groupScale") {
        const { x, z } = screenToWorld(sx, sy);
        const { anchorX, anchorZ, sx: scaleX, sz: scaleZ } =
          scaleFactorsFromHandle(it.handle, it.startGroupBounds, x, z);
        const lineGeoms: Record<string, SegmentGeom> = {};
        for (const [id, geom] of Object.entries(it.startLineGeoms)) {
          lineGeoms[id] = scaleSegmentGeom(
            geom,
            anchorX,
            anchorZ,
            scaleX,
            scaleZ,
          );
        }
        const meshBounds: Record<string, MeshBounds> = {};
        for (const [id, bounds] of Object.entries(it.startMeshBounds)) {
          meshBounds[id] = scaleMeshBounds(
            bounds,
            anchorX,
            anchorZ,
            scaleX,
            scaleZ,
          );
        }
        store.setLineGeometries(lineGeoms);
        store.setMeshBoundsMap(meshBounds);
        drawRef.current();
        return;
      }

      if (store.editTool === "addLine") {
        addPreviewRef.current = snapNew(worldPointAt(sx, sy), getPaths());
        drawRef.current();
      }
    },
    [getPaths, localPos, screenToWorld, worldPointAt],
  );

  const onPointerUp = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const { sx, sy } = localPos(e.clientX, e.clientY);
      const it = interactionRef.current;
      const store = useCircuitTuning.getState();
      canvasRef.current?.releasePointerCapture(e.pointerId);

      if (it.kind === "boxSelect") {
        const w = Math.abs(it.endSx - it.startSx);
        const h = Math.abs(it.endSy - it.startSy);
        if (w > DRAG_THRESHOLD || h > DRAG_THRESHOLD) {
          store.setBoxSelection(
            linesInBox(it.startSx, it.startSy, it.endSx, it.endSy),
            meshesInBox(it.startSx, it.startSy, it.endSx, it.endSy),
          );
        } else {
          store.clearSelection();
        }
        interactionRef.current = { kind: "none" };
        drawRef.current();
        return;
      }

      if (
        it.kind === "meshCorner" ||
        it.kind === "meshMove" ||
        it.kind === "groupMove" ||
        it.kind === "groupScale"
      ) {
        interactionRef.current = { kind: "none" };
        drawRef.current();
        return;
      }

      if (it.kind === "vertex") {
        const point = worldPointAt(sx, sy);
        store.moveVertex(
          it.segmentId,
          it.end,
          point,
          getPaths(),
          it.baseGeom,
          true,
        );
        store.setDraggingVertex(false);
        snapRef.current = null;
        interactionRef.current = { kind: "none" };
        drawRef.current();
        return;
      }

      if (it.kind === "maybe" && !it.panning) {
        store.clearSelection();
      }

      interactionRef.current = { kind: "none" };
    },
    [getPaths, linesInBox, localPos, meshesInBox, worldPointAt],
  );

  // --- Toolbar actions -------------------------------------------------------

  const setTool = useCircuitTuning((s) => s.setEditTool);
  const startAddMesh = useCircuitTuning((s) => s.startAddMesh);
  const snapAngles = useCircuitTuning((s) => s.snapAnglesToGrid);
  const snapMergeEps = useCircuitTuning((s) => s.snapMergeEps);
  const setSnapMergeEps = useCircuitTuning((s) => s.setSnapMergeEps);
  const deleteSelection = useCircuitTuning((s) => s.deleteSelection);
  const undo = useCircuitTuning((s) => s.undo);
  const redo = useCircuitTuning((s) => s.redo);
  const resetAll = useCircuitTuning((s) => s.resetAll);

  const flashStatus = useCallback((msg: string) => {
    setStatus(msg);
    window.setTimeout(() => setStatus(""), 2500);
  }, []);

  const onCopy = useCallback(() => {
    const count = useCircuitTuning.getState().selectedLineIds.filter(
      (id) => id.startsWith("trace-") || id.startsWith("user-"),
    ).length;
    if (count === 0) {
      flashStatus("Select one or more lines to copy");
      return;
    }
    if (useCircuitTuning.getState().copySelectedLines()) {
      flashStatus(`Copied ${count} line${count === 1 ? "" : "s"}`);
      drawRef.current();
    }
  }, [flashStatus]);

  const onPaste = useCallback(() => {
    if (!useCircuitTuning.getState().pasteLines()) {
      flashStatus("Nothing to paste — copy lines first");
      return;
    }
    const count = useCircuitTuning.getState().selectedLineIds.length;
    flashStatus(`Pasted ${count} line${count === 1 ? "" : "s"}`);
    drawRef.current();
  }, [flashStatus]);

  const onSnap45 = useCallback(() => {
    const { changed, merged, collapsed, meshSnapped } = snapAngles(getPaths(), getMeshes());
    drawRef.current();
    const parts: string[] = [];
    if (changed > 0) {
      parts.push(
        `Snapped ${changed} line${changed === 1 ? "" : "s"} to 45°`,
      );
    }
    if (merged > 0) {
      parts.push(
        `merged ${merged} vertex${merged === 1 ? "" : "es"}`,
      );
    }
    if (collapsed > 0) {
      parts.push(
        `rejoined ${collapsed} split line${collapsed === 1 ? "" : "s"}`,
      );
    }
    if (meshSnapped > 0) {
      parts.push(
        `connected ${meshSnapped} endpoint${meshSnapped === 1 ? "" : "s"} to mesh${meshSnapped === 1 ? "" : "es"}`,
      );
    }
    if (parts.length === 0) {
      flashStatus("Nothing to snap or merge");
    } else {
      flashStatus(parts.join(", "));
    }
  }, [flashStatus, getMeshes, getPaths, snapAngles]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        const store = useCircuitTuning.getState();
        const next = store.editTool === "addLine" ? "select" : "addLine";
        store.setEditTool(next);
        flashShortcutBtn(next === "addLine" ? SHORTCUT_BTN.addLine : SHORTCUT_BTN.select);
        return;
      }
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        flashShortcutBtn(SHORTCUT_BTN.snap45);
        onSnap45();
      }
    };
    canvas.addEventListener("keydown", onKeyDown);
    return () => canvas.removeEventListener("keydown", onKeyDown);
  }, [flashShortcutBtn, onSnap45]);

  const onSave = useCallback(async () => {
    const ok = await useCircuitTuning.getState().saveAsDefault();
    flashStatus(ok ? "Saved to circuits-tuning.json" : "Downloaded JSON (dev save unavailable)");
  }, [flashStatus]);

  const onExport = useCallback(() => {
    const text = useCircuitTuning.getState().exportJSON();
    const blob = new Blob([`${text}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "circuits-tuning.json";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const fileRef = useRef<HTMLInputElement | null>(null);
  const onImportFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      const text = await file.text();
      const ok = useCircuitTuning.getState().importJSON(text);
      flashStatus(ok ? "Imported tuning" : "Import failed: invalid JSON");
    },
    [flashStatus],
  );

  const cursorClass =
    editTool === "addLine" || editTool === "addMesh" || editTool === "split"
      ? "cce__canvas cce__canvas--add"
      : "cce__canvas";

  const hasSelection =
    selectedLineIds.length > 0 || selectedMeshIds.length > 0;

  const onDelete = useCallback(() => {
    deleteSelection();
  }, [deleteSelection]);

  return (
    <div className="cce" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className={cursorClass}
        tabIndex={0}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      />

      <div className="cce__toolbar">
        <div className="cce__group">
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.select,
              editTool === "select" ? "cce__btn cce__btn--active" : "cce__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.select)}
            onClick={() => setTool("select")}
          >
            Select
          </button>
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.addLine,
              editTool === "addLine" ? "cce__btn cce__btn--active" : "cce__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.addLine)}
            onClick={() => setTool("addLine")}
          >
            Add line
          </button>
        </div>

        <div className="cce__sep" />

        <div className="cce__group">
          <button
            type="button"
            className={
              editTool === "split" ? "cce__btn cce__btn--active" : "cce__btn"
            }
            disabled={selectedLineIds.length !== 1 && editTool !== "split"}
            onClick={() => setTool(editTool === "split" ? "select" : "split")}
          >
            Split
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.delete, "cce__btn cce__btn--danger")}
            disabled={!hasSelection}
            title={btnTitle(SHORTCUT_BTN.delete)}
            onClick={onDelete}
          >
            Delete
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.snap45, "cce__btn")}
            title={btnTitle(SHORTCUT_BTN.snap45)}
            onClick={onSnap45}
          >
            Snap 45°
          </button>
          <label className="cce__snap-merge">
            <span className="cce__snap-merge-label">Snap merge</span>
            <input
              className="cce__snap-merge-slider"
              type="range"
              min={0.05}
              max={1}
              step={0.01}
              value={snapMergeEps}
              onChange={(e) => setSnapMergeEps(Number(e.target.value))}
            />
            <span className="cce__snap-merge-value">
              {snapMergeEps.toFixed(2)}
            </span>
          </label>
        </div>

        <div className="cce__sep" />

        <div className="cce__group">
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.copy, "cce__btn")}
            disabled={selectedLineIds.length === 0}
            title={btnTitle(SHORTCUT_BTN.copy)}
            onClick={onCopy}
          >
            Copy
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.paste, "cce__btn")}
            disabled={clipboardLineCount === 0}
            title={btnTitle(SHORTCUT_BTN.paste)}
            onClick={onPaste}
          >
            Paste
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.undo, "cce__btn")}
            title={btnTitle(SHORTCUT_BTN.undo)}
            onClick={() => undo()}
          >
            Undo
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.redo, "cce__btn")}
            title={btnTitle(SHORTCUT_BTN.redo)}
            onClick={() => redo()}
          >
            Redo
          </button>
          <button
            type="button"
            className="cce__btn"
            onClick={() => {
              fitView();
              drawRef.current();
            }}
          >
            Fit
          </button>
        </div>

        <div className="cce__sep" />

        <div className="cce__group">
          <button type="button" className="cce__btn" onClick={onSave}>
            Save
          </button>
          <button type="button" className="cce__btn" onClick={onExport}>
            Export
          </button>
          <button
            type="button"
            className="cce__btn"
            onClick={() => fileRef.current?.click()}
          >
            Import
          </button>
          <button
            type="button"
            className="cce__btn"
            onClick={() => {
              resetAll();
              flashStatus("Reset to committed default");
            }}
          >
            Reset
          </button>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="application/json"
          hidden
          onChange={onImportFile}
        />
      </div>

      <aside className="cce__palette">
        <p className="cce__palette-title">Meshes</p>
        {MESH_PALETTE.map((kind) => (
          <button
            key={kind}
            type="button"
            className={
              editTool === "addMesh" && addMeshKind === kind
                ? "cce__palette-item cce__palette-item--active"
                : "cce__palette-item"
            }
            onClick={() => startAddMesh(kind)}
            title={`Place ${MESH_LABELS[kind]}`}
          >
            <span className="cce__palette-preview">{MESH_LABELS[kind]}</span>
            <span>{MESH_LABELS[kind]}</span>
          </button>
        ))}
      </aside>

      <div className="cce__status">
        {status && <span className="cce__status-line--accent">{status}</span>}
        <span>
          {loaded
            ? editTool === "split"
              ? "click on the selected line where you want to split it"
              : hasSelection
              ? [
                  selectedLineIds.length > 0
                    ? `${selectedLineIds.length} line${selectedLineIds.length === 1 ? "" : "s"}`
                    : null,
                  selectedMeshIds.length > 0
                    ? `${selectedMeshIds.length} mesh${selectedMeshIds.length === 1 ? "" : "es"}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(", ")
              : editTool === "addMesh" && addMeshKind
                  ? `click to place ${MESH_LABELS[addMeshKind]}`
                  : editTool === "addLine"
                    ? addLineStart
                      ? "click to place the line end"
                      : "click to place the line start"
                    : "click a line or mesh to select · ⌘-click to add to group · shift-drag to box select"
            : "loading board..."}
        </span>
        <span className="cce__hint">
          wheel: zoom · a: add line · r: snap 45° · space/middle-drag: pan ·
          ⌘-click: add to group · shift-drag: box select · drag line/body: move ·
          group corners: scale · ⌘C: copy · ⌘V: paste · del: delete · auto-saves
        </span>
      </div>
    </div>
  );
}

function dot(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
): void {
  ctx.beginPath();
  ctx.arc(x, y, 3, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

/** Snap a brand-new point onto nearby existing geometry (no segment to exclude). */
function snapNew(point: Vec3, paths: GridPath[]): Vec3 {
  return previewSnapPoint(point, paths, "__new__");
}
