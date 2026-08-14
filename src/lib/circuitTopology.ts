import type { GridPath, Vec3 } from "./gridBuilder";

export type SegmentGeom = { start: Vec3; end: Vec3 };

export type AddedSegment = { id: string; start: Vec3; end: Vec3 };

export interface CircuitTopology {
  /** Absolute world-space endpoints overriding auto layout. */
  geometry: Record<string, SegmentGeom>;
  /** Auto or user segment ids removed from the layout. */
  deleted: string[];
  /** Segments created by splits, joins, or the user. */
  added: AddedSegment[];
}

export const EMPTY_TOPOLOGY: CircuitTopology = {
  geometry: {},
  deleted: [],
  added: [],
};

const SNAP_ENDPOINT = 0.28;
const SNAP_EDGE = 0.22;
/** Along-axis tolerance between the cursor and a snap target while dragging. */
const SNAP_AXIS_DISTANCE = 0.35;
/** Max Y gap for a snap target to count as sharing the dragged line's plane. */
const SNAP_PLANE_EPS = 0.05;

export function vecEq(a: Vec3, b: Vec3, eps = 1e-4): boolean {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) <= eps;
}

export function segmentGeom(path: GridPath): SegmentGeom | null {
  if (path.waypoints.length < 2) return null;
  return { start: path.waypoints[0], end: path.waypoints.at(-1)! };
}

export function resolveSegmentGeom(
  path: GridPath,
  topology: CircuitTopology,
): SegmentGeom | null {
  if (!path.id) return segmentGeom(path);
  const ov = topology.geometry[path.id];
  if (ov) return ov;
  return segmentGeom(path);
}

/** Resolve segment geometry by id from live paths and/or topology edits. */
export function resolveSegmentGeomById(
  id: string,
  paths: GridPath[],
  topology: CircuitTopology,
): SegmentGeom | null {
  if (topology.deleted.includes(id)) return null;
  const path = paths.find((p) => p.id === id);
  if (path) return resolveSegmentGeom(path, topology);
  const ov = topology.geometry[id];
  if (ov) return ov;
  const added = topology.added.find((a) => a.id === id);
  if (added) {
    return topology.geometry[id] ?? { start: added.start, end: added.end };
  }
  return null;
}

/** Merge topology edits onto baseline segment paths. */
export function applyTopology(
  paths: GridPath[],
  topology: CircuitTopology,
): GridPath[] {
  const deleted = new Set(topology.deleted);
  const out: GridPath[] = [];

  for (const p of paths) {
    if (!p.id || deleted.has(p.id)) continue;
    const ov = topology.geometry[p.id];
    if (ov) {
      // Explicit endpoint override — always a two-point circuit segment.
      out.push({ ...p, waypoints: [ov.start, ov.end] });
      continue;
    }
    // Variant mesh outlines (and any other multi-point polyline) keep their
    // full shape. Collapsing them to start→end was shredding palette meshes
    // on the outline page when they ran through applyTuning.
    if (p.waypoints.length !== 2) {
      if (p.waypoints.length < 2) continue;
      out.push(p);
      continue;
    }
    out.push({ ...p, waypoints: [p.waypoints[0], p.waypoints[1]] });
  }

  for (const added of topology.added) {
    if (deleted.has(added.id)) continue;
    const geom = topology.geometry[added.id] ?? { start: added.start, end: added.end };
    out.push({
      id: added.id,
      waypoints: [geom.start, geom.end],
      spawnTime: 0,
    });
  }

  return out;
}

type SnapEndpoint = {
  kind: "endpoint";
  segmentId: string;
  end: 0 | 1;
  point: Vec3;
  dist: number;
};

type SnapEdge = {
  kind: "edge";
  segment: GridPath;
  point: Vec3;
  dist: number;
};

export type SnapTarget = SnapEndpoint | SnapEdge;

function distXZ(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

export function nearestOnSegmentXZ(
  point: Vec3,
  a: Vec3,
  b: Vec3,
): { dist: number; point: Vec3; t: number } {
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
  return { dist: Math.hypot(px - qx, pz - qz), point: [qx, qy, qz], t };
}

export type SegmentAxis = { anchor: Vec3; dir: Vec3 };

/** Unit axis from the fixed anchor through the dragged endpoint. */
export function segmentDragAxis(geom: SegmentGeom, end: 0 | 1): SegmentAxis | null {
  const anchor = end === 0 ? geom.end : geom.start;
  const dragged = end === 0 ? geom.start : geom.end;
  const dx = dragged[0] - anchor[0];
  const dy = dragged[1] - anchor[1];
  const dz = dragged[2] - anchor[2];
  const len = Math.hypot(dx, dy, dz);
  if (len < 1e-12) return null;
  return { anchor, dir: [dx / len, dy / len, dz / len] };
}

export function paramOnAxis(point: Vec3, anchor: Vec3, dir: Vec3): number {
  return (
    (point[0] - anchor[0]) * dir[0] +
    (point[1] - anchor[1]) * dir[1] +
    (point[2] - anchor[2]) * dir[2]
  );
}

export function pointOnAxis(anchor: Vec3, dir: Vec3, t: number): Vec3 {
  return [
    anchor[0] + dir[0] * t,
    anchor[1] + dir[1] * t,
    anchor[2] + dir[2] * t,
  ];
}

/**
 * Crossing of the drag axis with a segment, solved on the board's XZ plane.
 * Returns the point on the SEGMENT (so a split there lands exactly on it, never
 * producing a kink) plus the axis parameter `s` of that crossing.
 */
function intersectAxisWithSegment(
  anchor: Vec3,
  dir: Vec3,
  a: Vec3,
  b: Vec3,
): { point: Vec3; s: number } | null {
  const dax = dir[0];
  const daz = dir[2];
  const ex = b[0] - a[0];
  const ez = b[2] - a[2];

  const det = -dax * ez + ex * daz;
  if (Math.abs(det) < 1e-9) return null; // parallel in the board plane

  const rx = a[0] - anchor[0];
  const rz = a[2] - anchor[2];
  const s = (-rx * ez + ex * rz) / det;
  const u = (dax * rz - daz * rx) / det;
  if (u < 0.02 || u > 0.98) return null;

  const point: Vec3 = [
    a[0] + u * ex,
    a[1] + u * (b[1] - a[1]),
    a[2] + u * ez,
  ];
  return { point, s };
}

/**
 * Snap a dragged vertex onto another segment.
 *
 * When dragging along a fixed axis, the snap target is where that axis crosses
 * the body of the nearest segment. That crossing always splits the segment,
 * creating a new vertex (a clean T-junction) rather than jumping to an existing
 * one. The point lands on the segment and on the axis, so the line stays
 * straight and the connection is real. Falls back to flat XZ proximity when no
 * axis is supplied.
 */
export function findSnapTarget(
  point: Vec3,
  paths: GridPath[],
  excludeSegmentId: string,
  axis?: SegmentAxis,
): SnapTarget | null {
  if (!axis) return findSnapTargetXZ(point, paths, excludeSegmentId);

  const tPoint = paramOnAxis(point, axis.anchor, axis.dir);
  const anchorY = axis.anchor[1];
  let best: SnapTarget | null = null;

  for (const p of paths) {
    if (!p.id || p.id === excludeSegmentId || p.hidden || p.waypoints.length < 2) continue;
    const [a, b] = [p.waypoints[0], p.waypoints[1]];

    // Only snap to segments sharing the dragged line's plane, so the junction
    // stays coplanar and the endpoints coincide exactly.
    if (Math.abs(a[1] - anchorY) > SNAP_PLANE_EPS) continue;
    if (Math.abs(b[1] - anchorY) > SNAP_PLANE_EPS) continue;

    const hit = intersectAxisWithSegment(axis.anchor, axis.dir, a, b);
    if (!hit) continue;

    const score = Math.abs(hit.s - tPoint);
    if (score > SNAP_AXIS_DISTANCE) continue;
    if (!best || score < best.dist) {
      best = { kind: "edge", segment: p, point: hit.point, dist: score };
    }
  }

  return best;
}

/** Flat-plane proximity snap used when there is no constrained drag axis. */
function findSnapTargetXZ(
  point: Vec3,
  paths: GridPath[],
  excludeSegmentId: string,
): SnapTarget | null {
  let best: SnapTarget | null = null;

  for (const p of paths) {
    if (!p.id || p.id === excludeSegmentId || p.hidden || p.waypoints.length < 2) continue;
    const [a, b] = [p.waypoints[0], p.waypoints[1]];

    for (const [end, vtx] of [[0, a], [1, b]] as const) {
      const dist = distXZ(point, vtx);
      if (dist > SNAP_ENDPOINT) continue;
      if (!best || dist < best.dist) {
        best = { kind: "endpoint", segmentId: p.id, end: end as 0 | 1, point: [...vtx] as Vec3, dist };
      }
    }

    const { dist, point: q, t } = nearestOnSegmentXZ(point, a, b);
    if (dist > SNAP_EDGE) continue;
    if (t <= 0.02 || t >= 0.98) continue;
    if (!best || dist < best.dist) {
      best = { kind: "edge", segment: p, point: q, dist };
    }
  }

  return best;
}

export function previewSnapPoint(
  point: Vec3,
  paths: GridPath[],
  excludeSegmentId: string,
  axis?: SegmentAxis,
): Vec3 {
  return findSnapTarget(point, paths, excludeSegmentId, axis)?.point ?? point;
}

/** Id before the first `~` split suffix, e.g. `trace-3-seg-1~a` → `trace-3-seg-1`. */
export function splitParentId(id: string): string | null {
  const i = id.indexOf("~");
  return i >= 0 ? id.slice(0, i) : null;
}

function splitId(baseId: string, topology: CircuitTopology): [string, string] {
  let n = 0;
  const exists = (id: string) =>
    topology.added.some((a) => a.id === id) || topology.geometry[id] !== undefined;
  let a = `${baseId}~a`;
  let b = `${baseId}~b`;
  while (exists(a) || exists(b)) {
    n++;
    a = `${baseId}~a${n}`;
    b = `${baseId}~b${n}`;
  }
  return [a, b];
}

/** Split a segment at a point on its edge; returns updated topology. */
export function splitSegmentInTopology(
  segment: GridPath,
  point: Vec3,
  topology: CircuitTopology,
): CircuitTopology {
  if (!segment.id || segment.waypoints.length < 2) return topology;

  const geom = resolveSegmentGeom(segment, topology)!;
  const [idA, idB] = splitId(segment.id, topology);
  const deleted = topology.deleted.includes(segment.id)
    ? topology.deleted
    : [...topology.deleted, segment.id];

  const addedBase = topology.added.filter((a) => a.id !== segment.id);
  const geometry = { ...topology.geometry };
  delete geometry[segment.id];

  geometry[idA] = { start: geom.start, end: point };
  geometry[idB] = { start: point, end: geom.end };

  return {
    deleted,
    geometry,
    added: [
      ...addedBase,
      { id: idA, start: geom.start, end: point },
      { id: idB, start: point, end: geom.end },
    ],
  };
}

export function setVertexInTopology(
  topology: CircuitTopology,
  segmentId: string,
  end: 0 | 1,
  point: Vec3,
  baseGeom: SegmentGeom,
): CircuitTopology {
  const prev = topology.geometry[segmentId] ?? baseGeom;
  const next: SegmentGeom =
    end === 0 ? { start: point, end: prev.end } : { start: prev.start, end: point };
  return {
    ...topology,
    geometry: { ...topology.geometry, [segmentId]: next },
  };
}

/** Snap a vertex to an endpoint or split+join onto another segment's edge. */
export function joinVertexInTopology(
  segmentId: string,
  end: 0 | 1,
  point: Vec3,
  paths: GridPath[],
  topology: CircuitTopology,
  axis?: SegmentAxis,
): CircuitTopology {
  const seg = paths.find((p) => p.id === segmentId);
  if (!seg) return topology;

  const baseGeom = resolveSegmentGeom(seg, topology)!;
  const target = findSnapTarget(point, paths, segmentId, axis);

  if (!target) {
    const finalPoint = axis
      ? pointOnAxis(
          axis.anchor,
          axis.dir,
          Math.max(0, paramOnAxis(point, axis.anchor, axis.dir)),
        )
      : point;
    return setVertexInTopology(topology, segmentId, end, finalPoint, baseGeom);
  }

  if (target.kind === "endpoint") {
    return setVertexInTopology(topology, segmentId, end, target.point, baseGeom);
  }

  let next = splitSegmentInTopology(target.segment, target.point, topology);
  next = setVertexInTopology(next, segmentId, end, target.point, baseGeom);
  return next;
}

/** Replace two segments with one; restores a split parent id when applicable. */
export function mergeSegmentsInTopology(
  topology: CircuitTopology,
  idA: string,
  idB: string,
  mergedId: string,
  geom: SegmentGeom,
): CircuitTopology {
  const geometry = { ...topology.geometry };
  delete geometry[idA];
  delete geometry[idB];
  geometry[mergedId] = geom;

  const deleted = new Set(topology.deleted);
  deleted.add(idA);
  deleted.add(idB);
  deleted.delete(mergedId);

  const idAWasAdded = topology.added.some((a) => a.id === idA);
  const idBWasAdded = topology.added.some((a) => a.id === idB);
  const parentA = splitParentId(idA);
  const parentB = splitParentId(idB);
  const splitParent =
    parentA !== null && parentA === parentB ? parentA : null;
  // Baseline trace segments live in raw paths; user-drawn ones only exist in added.
  const restoringBaselineSplit =
    splitParent === mergedId && !mergedId.startsWith("user-");
  const keepInAdded =
    !restoringBaselineSplit &&
    (idAWasAdded || idBWasAdded || mergedId.startsWith("user-"));

  let added = topology.added.filter((a) => a.id !== idA && a.id !== idB);
  if (keepInAdded) {
    const entry: AddedSegment = {
      id: mergedId,
      start: [...geom.start] as Vec3,
      end: [...geom.end] as Vec3,
    };
    const idx = added.findIndex((a) => a.id === mergedId);
    if (idx >= 0) added[idx] = entry;
    else added.push(entry);
  }

  return { geometry, deleted: [...deleted], added };
}

export function deleteSegmentInTopology(
  topology: CircuitTopology,
  segmentId: string,
): CircuitTopology {
  if (topology.deleted.includes(segmentId)) return topology;
  return { ...topology, deleted: [...topology.deleted, segmentId] };
}

export function coincidentVertices(
  point: Vec3,
  paths: GridPath[],
  eps = 0.02,
): Array<{ segmentId: string; end: 0 | 1 }> {
  const hits: Array<{ segmentId: string; end: 0 | 1 }> = [];
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    if (vecEq(p.waypoints[0], point, eps)) hits.push({ segmentId: p.id, end: 0 });
    if (vecEq(p.waypoints[1], point, eps)) hits.push({ segmentId: p.id, end: 1 });
  }
  return hits;
}

/** Slide a cursor position along the segment axis through the anchor vertex. */
export function slidePointOnSegment(
  cursor: Vec3,
  geom: SegmentGeom,
  end: 0 | 1,
  /** When true, the dragged end cannot cross the opposite (fixed) anchor. */
  preventCrossingAnchor = false,
): Vec3 {
  const axis = segmentDragAxis(geom, end);
  if (!axis) return [...cursor] as Vec3;
  let t = paramOnAxis(cursor, axis.anchor, axis.dir);
  if (preventCrossingAnchor) t = Math.max(0, t);
  return pointOnAxis(axis.anchor, axis.dir, t);
}

export function midpoint(a: Vec3, b: Vec3): Vec3 {
  return [(a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5];
}

let userSegmentCounter = 0;

export function nextUserSegmentId(topology: CircuitTopology): string {
  const exists = (id: string) =>
    topology.added.some((a) => a.id === id) || topology.geometry[id] !== undefined;
  do {
    userSegmentCounter += 1;
    const id = `user-${userSegmentCounter}`;
    if (!exists(id)) return id;
  } while (userSegmentCounter < 100000);
  return `user-${Date.now()}`;
}

export function addSegmentToTopology(
  topology: CircuitTopology,
  start: Vec3,
  end: Vec3,
): { topology: CircuitTopology; id: string } {
  const id = nextUserSegmentId(topology);
  const geom = { start, end };
  return {
    id,
    topology: {
      ...topology,
      geometry: { ...topology.geometry, [id]: geom },
      added: [...topology.added, { id, start, end }],
    },
  };
}
