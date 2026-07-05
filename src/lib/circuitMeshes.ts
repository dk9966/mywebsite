import type { ComponentFootprint } from "./circuitComponentFootprints";
import type { MeshKind } from "./circuitMeshBoxes";
import { MESH_LABELS } from "./circuitMeshBoxes";

export type CircuitMesh = {
  id: string;
  kind: MeshKind;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  /**
   * Catalog variant id (e.g. "q4-l-pins") for meshes placed from the
   * qfp-variants palette. When set, the mesh renders that variant's real
   * outline geometry instead of a placeholder box.
   */
  variant?: string;
};

export type MeshBounds = Pick<
  CircuitMesh,
  "minX" | "maxX" | "minZ" | "maxZ"
>;

/** Footprint size on the board plane (world units). */
export type MeshSize = { w: number; h: number };

export type MeshOverride = Partial<MeshBounds> & { kind?: MeshKind };

export interface CircuitMeshEdits {
  geometry: Record<string, MeshOverride>;
  deleted: string[];
  added: CircuitMesh[];
}

export const EMPTY_MESH_EDITS: CircuitMeshEdits = {
  geometry: {},
  deleted: [],
  added: [],
};

export type MeshHandle = "nw" | "ne" | "sw" | "se";

const MIN_MESH_DIM = 0.8;

/** Default world size when placing a new mesh from the palette. */
export const DEFAULT_MESH_SIZE: Record<MeshKind, MeshSize> = {
  qfp: { w: 3.5, h: 3.5 },
  soic: { w: 4, h: 2 },
  capacitor: { w: 2, h: 2 },
  heatsink: { w: 4.5, h: 2.5 },
  drum: { w: 3, h: 3 },
  header: { w: 4, h: 1.5 },
  connector: { w: 4, h: 1.8 },
  smd: { w: 2.5, h: 1.5 },
  pad: { w: 1.2, h: 1.2 },
  via: { w: 1, h: 1 },
  cpu: { w: 5, h: 5 },
  io: { w: 4.5, h: 2 },
  dimm: { w: 6, h: 1.6 },
  pcie: { w: 6.5, h: 1.6 },
  vrm: { w: 4.5, h: 2 },
};

export function footprintsToMeshes(
  footprints: ComponentFootprint[],
): CircuitMesh[] {
  return footprints.map((f) => ({
    id: f.id,
    kind: f.kind,
    minX: f.minX,
    maxX: f.maxX,
    minZ: f.minZ,
    maxZ: f.maxZ,
  }));
}

export function resolveMeshes(
  baseline: CircuitMesh[],
  edits: CircuitMeshEdits,
): CircuitMesh[] {
  const deleted = new Set(edits.deleted);
  const out: CircuitMesh[] = [];

  for (const m of baseline) {
    if (deleted.has(m.id)) continue;
    const ov = edits.geometry[m.id];
    out.push(
      ov
        ? {
            ...m,
            ...ov,
            id: m.id,
            kind: ov.kind ?? m.kind,
          }
        : m,
    );
  }

  for (const m of edits.added) {
    if (deleted.has(m.id)) continue;
    const ov = edits.geometry[m.id];
    out.push(
      ov
        ? {
            ...m,
            ...ov,
            id: m.id,
            kind: ov.kind ?? m.kind,
          }
        : m,
    );
  }

  return out;
}

export function meshCenter(m: MeshBounds): { cx: number; cz: number } {
  return {
    cx: (m.minX + m.maxX) / 2,
    cz: (m.minZ + m.maxZ) / 2,
  };
}

export function meshContains(m: MeshBounds, x: number, z: number): boolean {
  return x >= m.minX && x <= m.maxX && z >= m.minZ && z <= m.maxZ;
}

function meshExists(edits: CircuitMeshEdits, id: string): boolean {
  return (
    edits.added.some((m) => m.id === id) || edits.geometry[id] !== undefined
  );
}

let userMeshCounter = 0;

export function nextUserMeshId(edits: CircuitMeshEdits): string {
  do {
    userMeshCounter += 1;
    const id = `mesh-user-${userMeshCounter}`;
    if (!meshExists(edits, id)) return id;
  } while (userMeshCounter < 100000);
  return `mesh-user-${Date.now()}`;
}

export function addMeshToEdits(
  edits: CircuitMeshEdits,
  kind: MeshKind,
  cx: number,
  cz: number,
  size = DEFAULT_MESH_SIZE[kind],
  variant?: string,
): { edits: CircuitMeshEdits; mesh: CircuitMesh } {
  const { w, h } = size;
  const id = nextUserMeshId(edits);
  const mesh: CircuitMesh = {
    id,
    kind,
    minX: cx - w / 2,
    maxX: cx + w / 2,
    minZ: cz - h / 2,
    maxZ: cz + h / 2,
    ...(variant ? { variant } : {}),
  };
  return {
    mesh,
    edits: { ...edits, added: [...edits.added, mesh] },
  };
}

export function setMeshBoundsInEdits(
  edits: CircuitMeshEdits,
  id: string,
  bounds: MeshBounds,
): CircuitMeshEdits {
  return {
    ...edits,
    geometry: { ...edits.geometry, [id]: { ...edits.geometry[id], ...bounds } },
  };
}

export function deleteMeshInEdits(
  edits: CircuitMeshEdits,
  id: string,
): CircuitMeshEdits {
  return {
    deleted: edits.deleted.includes(id)
      ? edits.deleted
      : [...edits.deleted, id],
    geometry: { ...edits.geometry },
    added: edits.added.filter((m) => m.id !== id),
  };
}

function clampMinDim(
  anchorX: number,
  anchorZ: number,
  x: number,
  z: number,
  minDim: number,
): { x: number; z: number } {
  let nx = x;
  let nz = z;
  if (Math.abs(nx - anchorX) < minDim) {
    nx = anchorX + Math.sign(nx - anchorX || 1) * minDim;
  }
  if (Math.abs(nz - anchorZ) < minDim) {
    nz = anchorZ + Math.sign(nz - anchorZ || 1) * minDim;
  }
  return { x: nx, z: nz };
}

/** Keep aspect ratio: corner moves along the diagonal from anchor. */
function cornerOnUniformDiagonal(
  anchorX: number,
  anchorZ: number,
  armX: number,
  armZ: number,
  x: number,
  z: number,
  minDim: number,
): { x: number; z: number } {
  const w = Math.abs(armX);
  const h = Math.abs(armZ);
  const len2 = armX * armX + armZ * armZ;
  if (len2 < 1e-12) {
    return clampMinDim(anchorX, anchorZ, x, z, minDim);
  }

  const dx = x - anchorX;
  const dz = z - anchorZ;
  let t = (dx * armX + dz * armZ) / len2;
  const tMin = Math.max(minDim / w, minDim / h);
  if (t >= 0) {
    t = Math.max(t, tMin);
  } else {
    t = Math.min(t, -tMin);
  }

  return {
    x: anchorX + t * armX,
    z: anchorZ + t * armZ,
  };
}

/** Resize by dragging one corner; opposite corner stays fixed, aspect ratio locked. */
export function resizeMeshFromCorner(
  bounds: MeshBounds,
  handle: MeshHandle,
  x: number,
  z: number,
  minDim = MIN_MESH_DIM,
): MeshBounds {
  const w = bounds.maxX - bounds.minX;
  const h = bounds.maxZ - bounds.minZ;
  let { minX, maxX, minZ, maxZ } = bounds;

  switch (handle) {
    case "nw": {
      const p = cornerOnUniformDiagonal(maxX, maxZ, -w, -h, x, z, minDim);
      minX = p.x;
      minZ = p.z;
      break;
    }
    case "ne": {
      const p = cornerOnUniformDiagonal(minX, maxZ, w, -h, x, z, minDim);
      maxX = p.x;
      minZ = p.z;
      break;
    }
    case "sw": {
      const p = cornerOnUniformDiagonal(maxX, minZ, -w, h, x, z, minDim);
      minX = p.x;
      maxZ = p.z;
      break;
    }
    case "se": {
      const p = cornerOnUniformDiagonal(minX, minZ, w, h, x, z, minDim);
      maxX = p.x;
      maxZ = p.z;
      break;
    }
  }

  if (minX > maxX) [minX, maxX] = [maxX, minX];
  if (minZ > maxZ) [minZ, maxZ] = [maxZ, minZ];

  return { minX, maxX, minZ, maxZ };
}

export function moveMeshBounds(
  bounds: MeshBounds,
  dx: number,
  dz: number,
): MeshBounds {
  return {
    minX: bounds.minX + dx,
    maxX: bounds.maxX + dx,
    minZ: bounds.minZ + dz,
    maxZ: bounds.maxZ + dz,
  };
}

export function meshHandleWorld(
  bounds: MeshBounds,
  handle: MeshHandle,
): { x: number; z: number } {
  switch (handle) {
    case "nw":
      return { x: bounds.minX, z: bounds.minZ };
    case "ne":
      return { x: bounds.maxX, z: bounds.minZ };
    case "sw":
      return { x: bounds.minX, z: bounds.maxZ };
    case "se":
      return { x: bounds.maxX, z: bounds.maxZ };
  }
}

export function meshLabel(kind: MeshKind): string {
  return MESH_LABELS[kind];
}
