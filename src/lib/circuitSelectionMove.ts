import type * as THREE from "three";
import {
  boardPickXZ,
  boardY,
  type BoardPickView,
} from "./circuitBoardPick";
import { lineIdAtScreenPoint, meshIdAtScreenPoint } from "./circuitBoxSelect";
import type { CircuitMesh, MeshBounds } from "./circuitMeshes";
import { moveMeshBounds } from "./circuitMeshes";
import {
  resolveSegmentGeom,
  type CircuitTopology,
  type SegmentGeom,
} from "./circuitTopology";
import type { GridPath } from "./gridBuilder";
import { useCircuitTuning } from "../stores/circuitTuning";

export const MIN_GROUP_DIM = 0.8;

export function isGroupSelection(lineIds: string[], meshIds: string[]): boolean {
  return lineIds.length + meshIds.length > 1;
}

export function hasMovableSelection(lineIds: string[], meshIds: string[]): boolean {
  return lineIds.length + meshIds.length > 0;
}

export function computeGroupBounds(
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

export type SelectionSnapshot = {
  groupBounds: MeshBounds;
  lineGeoms: Record<string, SegmentGeom>;
  meshBounds: Record<string, MeshBounds>;
};

export function captureSelectionSnapshot(
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

export function moveSegmentGeom(geom: SegmentGeom, dx: number, dz: number): SegmentGeom {
  return {
    start: [geom.start[0] + dx, geom.start[1], geom.start[2] + dz],
    end: [geom.end[0] + dx, geom.end[1], geom.end[2] + dz],
  };
}

export function padGroupBounds(bounds: MeshBounds, minDim: number): MeshBounds {
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

export function pointInGroupBounds(x: number, z: number, bounds: MeshBounds): boolean {
  return x >= bounds.minX && x <= bounds.maxX && z >= bounds.minZ && z <= bounds.maxZ;
}

export function resolveLineMoveSelection(
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
    return { lineIds: selectedLineIds, meshIds: selectedMeshIds, selectOnly: false };
  }

  return { lineIds: [hitId], meshIds: [], selectOnly: false };
}

export function resolveMeshMoveSelection(
  hitId: string,
  selectedLineIds: string[],
  selectedMeshIds: string[],
  additiveKey: boolean,
): { lineIds: string[]; meshIds: string[]; selectOnly: boolean } | null {
  if (additiveKey) {
    const next = selectedMeshIds.includes(hitId)
      ? selectedMeshIds.filter((id) => id !== hitId)
      : [...selectedMeshIds, hitId];
    return { lineIds: selectedLineIds, meshIds: next, selectOnly: true };
  }

  if (selectedMeshIds.includes(hitId)) {
    return { lineIds: selectedLineIds, meshIds: selectedMeshIds, selectOnly: false };
  }

  return { lineIds: [], meshIds: [hitId], selectOnly: false };
}

export function applySelectionMove(
  snapshot: Pick<SelectionSnapshot, "lineGeoms" | "meshBounds">,
  dx: number,
  dz: number,
): {
  lineGeoms: Record<string, SegmentGeom>;
  meshBounds: Record<string, MeshBounds>;
} {
  const lineGeoms: Record<string, SegmentGeom> = {};
  for (const [id, geom] of Object.entries(snapshot.lineGeoms)) {
    lineGeoms[id] = moveSegmentGeom(geom, dx, dz);
  }
  const meshBounds: Record<string, MeshBounds> = {};
  for (const [id, bounds] of Object.entries(snapshot.meshBounds)) {
    meshBounds[id] = moveMeshBounds(bounds, dx, dz);
  }
  return { lineGeoms, meshBounds };
}

export const SELECTION_MOVE_THRESHOLD = 0.02;

export type SelectionMoveDrag = {
  startHitX: number;
  startHitZ: number;
  baseSnapshot: Pick<SelectionSnapshot, "lineGeoms" | "meshBounds">;
  pushed: boolean;
};

export type ShiftPointerTarget =
  | { mode: "toggle"; lineIds: string[]; meshIds: string[] }
  | { mode: "move"; lineIds: string[]; meshIds: string[] }
  | { mode: "box" };

export function resolveShiftPointerTarget(
  sx: number,
  sy: number,
  clientX: number,
  clientY: number,
  paths: GridPath[],
  meshes: CircuitMesh[],
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  selectedLineIds: string[],
  selectedMeshIds: string[],
  topology: CircuitTopology,
  metaKey: boolean,
  view: BoardPickView = "top",
  centerZ = 0,
): ShiftPointerTarget {
  const hitLineId = lineIdAtScreenPoint(paths, camera, canvas, sx, sy);
  if (hitLineId) {
    const resolved = resolveLineMoveSelection(
      hitLineId,
      selectedLineIds,
      selectedMeshIds,
      metaKey,
    );
    if (!resolved) return { mode: "box" };
    if (resolved.selectOnly) {
      return {
        mode: "toggle",
        lineIds: resolved.lineIds,
        meshIds: resolved.meshIds,
      };
    }
    return {
      mode: "move",
      lineIds: resolved.lineIds,
      meshIds: resolved.meshIds,
    };
  }

  const y = boardY(paths);
  const hitMeshId = meshIdAtScreenPoint(meshes, y, camera, canvas, sx, sy);
  if (hitMeshId) {
    const resolved = resolveMeshMoveSelection(
      hitMeshId,
      selectedLineIds,
      selectedMeshIds,
      metaKey,
    );
    if (!resolved) return { mode: "box" };
    if (resolved.selectOnly) {
      return {
        mode: "toggle",
        lineIds: resolved.lineIds,
        meshIds: resolved.meshIds,
      };
    }
    return {
      mode: "move",
      lineIds: resolved.lineIds,
      meshIds: resolved.meshIds,
    };
  }

  if (hasMovableSelection(selectedLineIds, selectedMeshIds)) {
    const hit = boardPickXZ(
      clientX,
      clientY,
      camera,
      canvas,
      y,
      view,
      centerZ,
    );
    if (hit) {
      const snap = captureSelectionSnapshot(
        paths,
        meshes,
        selectedLineIds,
        selectedMeshIds,
        topology,
      );
      if (snap) {
        const hitBounds = isGroupSelection(selectedLineIds, selectedMeshIds)
          ? snap.groupBounds
          : padGroupBounds(snap.groupBounds, MIN_GROUP_DIM);
        if (pointInGroupBounds(hit.x, hit.z, hitBounds)) {
          return {
            mode: "move",
            lineIds: selectedLineIds,
            meshIds: selectedMeshIds,
          };
        }
      }
    }
  }

  return { mode: "box" };
}

export function beginSelectionMoveDrag(
  clientX: number,
  clientY: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  paths: GridPath[],
  meshes: CircuitMesh[],
  lineIds: string[],
  meshIds: string[],
  topology: CircuitTopology,
  view: BoardPickView = "top",
  centerZ = 0,
): SelectionMoveDrag | null {
  const y = boardY(paths);
  const hit = boardPickXZ(
    clientX,
    clientY,
    camera,
    canvas,
    y,
    view,
    centerZ,
  );
  if (!hit) return null;

  const snap = captureSelectionSnapshot(
    paths,
    meshes,
    lineIds,
    meshIds,
    topology,
  );
  if (!snap) return null;

  return {
    startHitX: hit.x,
    startHitZ: hit.z,
    baseSnapshot: {
      lineGeoms: snap.lineGeoms,
      meshBounds: snap.meshBounds,
    },
    pushed: false,
  };
}

export function stepSelectionMoveDrag(
  drag: SelectionMoveDrag,
  clientX: number,
  clientY: number,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
  paths: GridPath[],
  view: BoardPickView = "top",
  centerZ = 0,
): SelectionMoveDrag {
  const hit = boardPickXZ(
    clientX,
    clientY,
    camera,
    canvas,
    boardY(paths),
    view,
    centerZ,
  );
  if (!hit) return drag;

  const dx = hit.x - drag.startHitX;
  const dz = hit.z - drag.startHitZ;
  let pushed = drag.pushed;
  if (
    !pushed &&
    (Math.abs(dx) > SELECTION_MOVE_THRESHOLD ||
      Math.abs(dz) > SELECTION_MOVE_THRESHOLD)
  ) {
    useCircuitTuning.getState().pushUndo();
    pushed = true;
  }
  if (!pushed) return { ...drag, pushed };

  const { lineGeoms, meshBounds } = applySelectionMove(
    drag.baseSnapshot,
    dx,
    dz,
  );
  const store = useCircuitTuning.getState();
  store.setLineGeometries(lineGeoms);
  store.setMeshBoundsMap(meshBounds);
  return { ...drag, pushed: true };
}
