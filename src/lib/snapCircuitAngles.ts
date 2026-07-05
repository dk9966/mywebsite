import type { CircuitMesh, MeshBounds } from "./circuitMeshes";
import type { GridPath, Vec3 } from "./gridBuilder";
import {
  deleteSegmentInTopology,
  mergeSegmentsInTopology,
  nearestOnSegmentXZ,
  resolveSegmentGeom,
  splitParentId,
  type CircuitTopology,
  type SegmentGeom,
} from "./circuitTopology";

/**
 * Snap every editable line to the nearest 45° step (horizontal, vertical, or
 * diagonal) without breaking junctions.
 *
 * Lines are connected when they share an endpoint. Rather than rotating each
 * line independently (which would tear shared corners apart), we treat each
 * shared junction as a single movable point and ask every line to align its
 * direction to the closest multiple of 45°. Connected lines reference the same
 * point, so connections survive by construction.
 *
 * Each line contributes one linear constraint: its perpendicular offset across
 * the snapped direction must be zero. Loops can make all constraints
 * impossible to satisfy at once, so we solve a weighted least-squares system —
 * align as closely as possible while moving points as little as possible.
 *
 * After snapping, nearby endpoints are welded together (and endpoints near a
 * segment body are pulled onto it) so almost-touching junctions become real joins.
 * Collinear pairs that meet at a degree-2 junction are then collapsed back into
 * one segment so split lines fully rejoin. Endpoints near component mesh boxes
 * are finally snapped to the nearest box edge.
 */

const QUARTER = Math.PI / 4;
const MIN_SEGMENT_LEN = 1e-4;
const JOIN_EPS = 1e-6;
export const DEFAULT_MERGE_EPS = 0.28;
const MAX_MERGE_PASSES = 8;

/** Editable circuit lines are the traced and user-drawn segments. */
function isEditable(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
}

type Endpoint = { seg: number; end: 0 | 1 };

type Vertex = {
  x: number;
  z: number;
  /** Y is preserved per-vertex; only the board plane (XZ) is solved. */
  y: number;
  endpoints: Endpoint[];
};

type SnapSegment = {
  id: string;
  vStart: number;
  vEnd: number;
  /** Unit normal of the snapped direction, in (x, z). */
  nx: number;
  nz: number;
  /** True when the line already sat on a 45° step within tolerance. */
  aligned: boolean;
};

type EndpointRef = { segId: string; end: 0 | 1; x: number; z: number; y: number };

export interface SnapAnglesOptions {
  /** Junctions within this XZ distance are one shared point during the angle solve. Defaults to mergeEps. */
  clusterEps?: number;
  /** Lines whose angle is within this many degrees of a step count as aligned. */
  angleTolDeg?: number;
  /** Endpoints closer than this (XZ) are welded into one vertex after snapping. */
  mergeEps?: number;
  /** Component mesh boxes endpoints may snap to after angle/merge passes. */
  meshes?: CircuitMesh[];
}

export interface SnapAnglesResult {
  topology: CircuitTopology;
  /** How many lines were off a 45° step before snapping. */
  changed: number;
  /** How many endpoint joins were made (endpoint pairs + edge snaps). */
  merged: number;
  /** How many collinear segment pairs were collapsed into one line. */
  collapsed: number;
  /** How many endpoints were snapped to a mesh box edge. */
  meshSnapped: number;
}

export function snapAnglesToGrid(
  paths: GridPath[],
  topology: CircuitTopology,
  opts: SnapAnglesOptions = {},
): SnapAnglesResult {
  const angleTol = ((opts.angleTolDeg ?? 0.25) * Math.PI) / 180;
  const mergeEps = opts.mergeEps ?? DEFAULT_MERGE_EPS;
  const clusterEps = opts.clusterEps ?? mergeEps;

  const vertices: Vertex[] = [];
  const segments: SnapSegment[] = [];

  const findVertex = (p: Vec3): number => {
    for (let i = 0; i < vertices.length; i++) {
      const v = vertices[i];
      if (Math.hypot(v.x - p[0], v.z - p[2]) <= clusterEps) return i;
    }
    vertices.push({ x: p[0], z: p[2], y: p[1], endpoints: [] });
    return vertices.length - 1;
  };

  for (const p of paths) {
    if (!isEditable(p.id) || p.hidden || p.waypoints.length < 2) continue;
    const start = p.waypoints[0];
    const end = p.waypoints[p.waypoints.length - 1];
    const dx = end[0] - start[0];
    const dz = end[2] - start[2];
    if (Math.hypot(dx, dz) < 1e-6) continue;

    const seg = segments.length;
    const vStart = findVertex(start);
    const vEnd = findVertex(end);
    vertices[vStart].endpoints.push({ seg, end: 0 });
    vertices[vEnd].endpoints.push({ seg, end: 1 });

    const angle = Math.atan2(dz, dx);
    const snapped = Math.round(angle / QUARTER) * QUARTER;
    let deviation = Math.abs(angle - snapped);
    if (deviation > Math.PI) deviation = 2 * Math.PI - deviation;

    segments.push({
      id: p.id!,
      vStart,
      vEnd,
      nx: -Math.sin(snapped),
      nz: Math.cos(snapped),
      aligned: deviation <= angleTol,
    });
  }

  const changed = segments.filter((s) => !s.aligned).length;

  let resultTopology = topology;
  if (changed > 0) {
    const solved = solvePositions(vertices, segments);
    const geometry = { ...topology.geometry };
    for (const s of segments) {
      const a = solved[s.vStart];
      const b = solved[s.vEnd];
      geometry[s.id] = {
        start: [a.x, a.y, a.z],
        end: [b.x, b.y, b.z],
      };
    }
    resultTopology = { ...topology, geometry };
  }

  const { topology: mergedTopology, merged } = joinNearbyVertices(
    paths,
    resultTopology,
    mergeEps,
  );

  const { topology: collapsedTopology, collapsed } = collapseCollinearSegments(
    paths,
    mergedTopology,
  );

  const meshes = opts.meshes ?? [];
  let finalTopology = collapsedTopology;
  let meshSnapped = 0;

  if (meshes.length > 0) {
    const geoms = collectEditableGeoms(paths, collapsedTopology);
    if (geoms.size > 0) {
      meshSnapped = snapEndpointsToMeshes(geoms, meshes, mergeEps);
      if (meshSnapped > 0) {
        finalTopology = applyGeomEdits(collapsedTopology, geoms);
      }
    }
  }

  return { topology: finalTopology, changed, merged, collapsed, meshSnapped };
}

type SolvedVertex = { x: number; y: number; z: number };

function solvePositions(
  vertices: Vertex[],
  segments: SnapSegment[],
): SolvedVertex[] {
  const W_ALIGN = 1000;
  const W_ANCHOR = 1;
  const n = vertices.length;
  const dim = n * 2;
  const xi = (v: number) => v * 2;
  const zi = (v: number) => v * 2 + 1;

  const M: number[][] = Array.from({ length: dim }, () => new Array(dim).fill(0));
  const rhs = new Array(dim).fill(0);

  for (const s of segments) {
    const cols = [xi(s.vStart), zi(s.vStart), xi(s.vEnd), zi(s.vEnd)];
    const coef = [-s.nx, -s.nz, s.nx, s.nz];
    for (let a = 0; a < 4; a++) {
      for (let b = 0; b < 4; b++) {
        M[cols[a]][cols[b]] += W_ALIGN * coef[a] * coef[b];
      }
    }
  }

  for (let v = 0; v < n; v++) {
    M[xi(v)][xi(v)] += W_ANCHOR;
    rhs[xi(v)] += W_ANCHOR * vertices[v].x;
    M[zi(v)][zi(v)] += W_ANCHOR;
    rhs[zi(v)] += W_ANCHOR * vertices[v].z;
  }

  const p = solveSPD(M, rhs);
  return vertices.map((v, i) => ({ x: p[xi(i)], y: v.y, z: p[zi(i)] }));
}

function solveSPD(M: number[][], b: number[]): number[] {
  const n = b.length;
  const a = M.map((row, i) => [...row, b[i]]);

  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(a[r][col]) > Math.abs(a[pivot][col])) pivot = r;
    }
    if (pivot !== col) [a[col], a[pivot]] = [a[pivot], a[col]];

    const diag = a[col][col];
    if (Math.abs(diag) < 1e-12) continue;

    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const factor = a[r][col] / diag;
      if (factor === 0) continue;
      for (let c = col; c <= n; c++) a[r][c] -= factor * a[col][c];
    }
  }

  const x = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    const diag = a[i][i];
    x[i] = Math.abs(diag) < 1e-12 ? 0 : a[i][n] / diag;
  }
  return x;
}

function collectEditableGeoms(
  paths: GridPath[],
  topology: CircuitTopology,
): Map<string, SegmentGeom> {
  const deleted = new Set(topology.deleted);
  const geoms = new Map<string, SegmentGeom>();

  for (const p of paths) {
    if (!isEditable(p.id) || p.hidden || deleted.has(p.id!)) continue;
    const geom = resolveSegmentGeom(p, topology);
    if (!geom) continue;
    geoms.set(p.id!, {
      start: [...geom.start] as Vec3,
      end: [...geom.end] as Vec3,
    });
  }

  return geoms;
}

function endpointRefs(geoms: Map<string, SegmentGeom>): EndpointRef[] {
  const refs: EndpointRef[] = [];
  for (const [segId, geom] of geoms) {
    refs.push({
      segId,
      end: 0,
      x: geom.start[0],
      z: geom.start[2],
      y: geom.start[1],
    });
    refs.push({
      segId,
      end: 1,
      x: geom.end[0],
      z: geom.end[2],
      y: geom.end[1],
    });
  }
  return refs;
}

function setEndpoint(
  geoms: Map<string, SegmentGeom>,
  ref: EndpointRef,
  point: Vec3,
): void {
  const geom = geoms.get(ref.segId);
  if (!geom) return;
  if (ref.end === 0) geom.start = point;
  else geom.end = point;
}

/** Weld endpoint pairs within mergeEps to their shared centroid. */
function mergeEndpointClusters(
  geoms: Map<string, SegmentGeom>,
  mergeEps: number,
): number {
  const refs = endpointRefs(geoms);
  if (refs.length < 2) return 0;

  const parent = refs.map((_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const unite = (a: number, b: number) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[rb] = ra;
  };

  for (let i = 0; i < refs.length; i++) {
    for (let j = i + 1; j < refs.length; j++) {
      if (Math.hypot(refs[i].x - refs[j].x, refs[i].z - refs[j].z) <= mergeEps) {
        unite(i, j);
      }
    }
  }

  const groups = new Map<number, number[]>();
  for (let i = 0; i < refs.length; i++) {
    const root = find(i);
    const list = groups.get(root);
    if (list) list.push(i);
    else groups.set(root, [i]);
  }

  let merged = 0;
  for (const indices of groups.values()) {
    if (indices.length < 2) continue;

    let sx = 0;
    let sy = 0;
    let sz = 0;
    for (const i of indices) {
      sx += refs[i].x;
      sy += refs[i].y;
      sz += refs[i].z;
    }
    const n = indices.length;
    const point: Vec3 = [sx / n, sy / n, sz / n];

    const needsMove = indices.some(
      (i) => Math.hypot(refs[i].x - point[0], refs[i].z - point[2]) > JOIN_EPS,
    );
    if (!needsMove) continue;

    merged += indices.length - 1;

    for (const i of indices) {
      setEndpoint(geoms, refs[i], point);
    }
  }

  return merged;
}

/** Nearest point on an axis-aligned box perimeter in the board plane (XZ). */
function nearestOnBoxEdge(
  x: number,
  z: number,
  box: MeshBounds,
): { x: number; z: number; dist: number } {
  const { minX, maxX, minZ, maxZ } = box;
  const insideX = x > minX && x < maxX;
  const insideZ = z > minZ && z < maxZ;

  if (insideX && insideZ) {
    const dLeft = x - minX;
    const dRight = maxX - x;
    const dBottom = z - minZ;
    const dTop = maxZ - z;
    const dist = Math.min(dLeft, dRight, dBottom, dTop);
    if (dist === dLeft) return { x: minX, z, dist };
    if (dist === dRight) return { x: maxX, z, dist };
    if (dist === dBottom) return { x, z: minZ, dist };
    return { x, z: maxZ, dist };
  }

  const cx = Math.max(minX, Math.min(maxX, x));
  const cz = Math.max(minZ, Math.min(maxZ, z));
  return { x: cx, z: cz, dist: Math.hypot(x - cx, z - cz) };
}

/** Snap loose endpoints onto a nearby component mesh box edge. */
function snapEndpointsToMeshes(
  geoms: Map<string, SegmentGeom>,
  meshes: CircuitMesh[],
  snapEps: number,
): number {
  const refs = endpointRefs(geoms);
  let snapped = 0;

  for (const ref of refs) {
    let best: { x: number; z: number; dist: number } | null = null;

    for (const mesh of meshes) {
      const hit = nearestOnBoxEdge(ref.x, ref.z, mesh);
      if (hit.dist > snapEps) continue;
      if (!best || hit.dist < best.dist) {
        best = hit;
      }
    }

    if (
      best &&
      Math.hypot(ref.x - best.x, ref.z - best.z) > JOIN_EPS
    ) {
      setEndpoint(geoms, ref, [best.x, ref.y, best.z]);
      snapped += 1;
    }
  }

  return snapped;
}

/** Snap loose endpoints onto a nearby segment body (T-junction join). */
function joinEndpointsToSegments(
  geoms: Map<string, SegmentGeom>,
  mergeEps: number,
): number {
  const refs = endpointRefs(geoms);
  let joined = 0;

  for (const ref of refs) {
    const point: Vec3 = [ref.x, ref.y, ref.z];
    let best: { dist: number; point: Vec3 } | null = null;

    for (const [segId, geom] of geoms) {
      if (segId === ref.segId) continue;
      const hit = nearestOnSegmentXZ(point, geom.start, geom.end);
      if (hit.dist > mergeEps) continue;
      // Interior hits only — endpoints are handled by cluster merge.
      if (hit.t <= 0.02 || hit.t >= 0.98) continue;
      if (!best || hit.dist < best.dist) {
        best = { dist: hit.dist, point: hit.point };
      }
    }

    if (
      best &&
      Math.hypot(ref.x - best.point[0], ref.z - best.point[2]) > JOIN_EPS
    ) {
      setEndpoint(geoms, ref, best.point);
      joined += 1;
    }
  }

  return joined;
}

function applyGeomEdits(
  topology: CircuitTopology,
  geoms: Map<string, SegmentGeom>,
): CircuitTopology {
  const geometry = { ...topology.geometry };
  const toDelete: string[] = [];

  for (const [id, geom] of geoms) {
    const len = Math.hypot(
      geom.end[0] - geom.start[0],
      geom.end[2] - geom.start[2],
    );
    if (len < MIN_SEGMENT_LEN) {
      toDelete.push(id);
      continue;
    }
    geometry[id] = geom;
  }

  let nextTopology: CircuitTopology = { ...topology, geometry };
  for (const id of toDelete) {
    nextTopology = deleteSegmentInTopology(nextTopology, id);
  }
  return nextTopology;
}

/** Repeatedly merge close endpoints and snap to nearby segment bodies. */
function joinNearbyVertices(
  paths: GridPath[],
  topology: CircuitTopology,
  mergeEps: number,
): { topology: CircuitTopology; merged: number } {
  let totalMerged = 0;
  let current = topology;

  for (let pass = 0; pass < MAX_MERGE_PASSES; pass++) {
    const geoms = collectEditableGeoms(paths, current);
    if (geoms.size === 0) break;

    const clustered = mergeEndpointClusters(geoms, mergeEps);
    const edgeJoined = joinEndpointsToSegments(geoms, mergeEps);
    const passMerged = clustered + edgeJoined;
    if (passMerged === 0) break;

    totalMerged += passMerged;
    current = applyGeomEdits(current, geoms);
  }

  if (totalMerged === 0) return { topology, merged: 0 };
  return { topology: current, merged: totalMerged };
}

type XZDir = { x: number; z: number };

function xzDir(from: Vec3, to: Vec3): XZDir | null {
  const x = to[0] - from[0];
  const z = to[2] - from[2];
  const len = Math.hypot(x, z);
  if (len < MIN_SEGMENT_LEN) return null;
  return { x: x / len, z: z / len };
}

function parallelDirs(a: XZDir, b: XZDir): boolean {
  const cross = a.x * b.z - a.z * b.x;
  return Math.abs(cross) < 1e-3;
}

function pickMergedSegmentId(idA: string, idB: string): string {
  const parentA = splitParentId(idA);
  const parentB = splitParentId(idB);
  if (parentA && parentA === parentB) return parentA;
  if (!splitParentId(idA)) return idA;
  if (!splitParentId(idB)) return idB;
  return idA;
}

/** Merge two collinear segments that meet at one endpoint pair. */
function collinearMerge(
  a: SegmentGeom,
  endA: 0 | 1,
  b: SegmentGeom,
  endB: 0 | 1,
): SegmentGeom | null {
  const dirA = xzDir(a.start, a.end);
  const dirB = xzDir(b.start, b.end);
  if (!dirA || !dirB || !parallelDirs(dirA, dirB)) return null;

  const dot = dirA.x * dirB.x + dirA.z * dirB.z;

  if (endA === 1 && endB === 0) {
    if (dot <= 0.99) return null;
    return { start: [...a.start] as Vec3, end: [...b.end] as Vec3 };
  }
  if (endA === 1 && endB === 1) {
    if (dot >= -0.99) return null;
    return { start: [...a.start] as Vec3, end: [...b.start] as Vec3 };
  }
  if (endA === 0 && endB === 0) {
    if (dot <= 0.99) return null;
    return { start: [...a.end] as Vec3, end: [...b.end] as Vec3 };
  }
  if (endA === 0 && endB === 1) {
    if (dot >= -0.99) return null;
    return { start: [...a.end] as Vec3, end: [...b.start] as Vec3 };
  }
  return null;
}

function endpointClusters(
  refs: EndpointRef[],
  eps: number,
): EndpointRef[][] {
  if (refs.length < 2) return [];

  const parent = refs.map((_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const unite = (a: number, b: number) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[rb] = ra;
  };

  for (let i = 0; i < refs.length; i++) {
    for (let j = i + 1; j < refs.length; j++) {
      if (Math.hypot(refs[i].x - refs[j].x, refs[i].z - refs[j].z) <= eps) {
        unite(i, j);
      }
    }
  }

  const groups = new Map<number, EndpointRef[]>();
  for (let i = 0; i < refs.length; i++) {
    const root = find(i);
    const list = groups.get(root);
    if (list) list.push(refs[i]);
    else groups.set(root, [refs[i]]);
  }

  return [...groups.values()];
}

/** Collapse degree-2 collinear junctions back into single segments. */
function collapseCollinearSegments(
  paths: GridPath[],
  topology: CircuitTopology,
): { topology: CircuitTopology; collapsed: number } {
  let current = topology;
  let collapsed = 0;

  for (let pass = 0; pass < MAX_MERGE_PASSES; pass++) {
    const geoms = collectEditableGeoms(paths, current);
    if (geoms.size < 2) break;

    const groups = endpointClusters(endpointRefs(geoms), JOIN_EPS);
    let didCollapse = false;

    for (const group of groups) {
      if (group.length !== 2) continue;
      const [r0, r1] = group;
      if (r0.segId === r1.segId) continue;

      const g0 = geoms.get(r0.segId);
      const g1 = geoms.get(r1.segId);
      if (!g0 || !g1) continue;

      const combined = collinearMerge(g0, r0.end, g1, r1.end);
      if (!combined) continue;

      const mergedId = pickMergedSegmentId(r0.segId, r1.segId);
      current = mergeSegmentsInTopology(
        current,
        r0.segId,
        r1.segId,
        mergedId,
        combined,
      );
      collapsed += 1;
      didCollapse = true;
      break;
    }

    if (!didCollapse) break;
  }

  if (collapsed === 0) return { topology, collapsed: 0 };
  return { topology: current, collapsed };
}
