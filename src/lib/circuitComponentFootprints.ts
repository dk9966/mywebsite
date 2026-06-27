// Derives one component footprint per board part from the GLB outline segments,
// then labels each mesh from circuits-traced.json accent boxes (green = QFP,
// pink = heatsink), matching the reference PNG.

import type { GridPath } from "./gridBuilder";
import type { MeshKind } from "./circuitMeshBoxes";
import {
  tracedReferenceMeshes,
  type TracedReferenceMesh,
} from "./tronPathsFromCircuitsTraced";

export type ComponentFootprint = {
  id: string;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  cx: number;
  cz: number;
  kind: MeshKind;
};

/** A footprint plus the `part-*` polyline base ids whose outlines compose it. */
export type ComponentFootprintDetailed = ComponentFootprint & {
  members: string[];
};

type Box = { minX: number; maxX: number; minZ: number; maxZ: number };

/** Two part polylines within this XZ gap (world units) are one component. */
const CLUSTER_GAP = 0.12;

/** Accent colors in circuits-traced.png → circuit-painter mesh kind. */
const ACCENT_KIND: Record<TracedReferenceMesh["accent"], MeshKind> = {
  green: "qfp",
  pink: "heatsink",
};

function partBaseId(segmentId: string): string | null {
  if (!segmentId.startsWith("part-")) return null;
  const segIdx = segmentId.indexOf("-seg-");
  return segIdx >= 0 ? segmentId.slice(0, segIdx) : segmentId;
}

function boxesOverlap(a: Box, b: Box, gap: number): boolean {
  return (
    a.minX - gap <= b.maxX &&
    b.minX - gap <= a.maxX &&
    a.minZ - gap <= b.maxZ &&
    b.minZ - gap <= a.maxZ
  );
}

function mergeBox(a: Box, b: Box): Box {
  return {
    minX: Math.min(a.minX, b.minX),
    maxX: Math.max(a.maxX, b.maxX),
    minZ: Math.min(a.minZ, b.minZ),
    maxZ: Math.max(a.maxZ, b.maxZ),
  };
}

function boxIou(a: Box, b: Box): number {
  const ix0 = Math.max(a.minX, b.minX);
  const ix1 = Math.min(a.maxX, b.maxX);
  const iz0 = Math.max(a.minZ, b.minZ);
  const iz1 = Math.min(a.maxZ, b.maxZ);
  if (ix1 <= ix0 || iz1 <= iz0) return 0;
  const inter = (ix1 - ix0) * (iz1 - iz0);
  const areaA = (a.maxX - a.minX) * (a.maxZ - a.minZ);
  const areaB = (b.maxX - b.minX) * (b.maxZ - b.minZ);
  return inter / (areaA + areaB - inter);
}

/** Match a GLB footprint to the traced PNG reference box it corresponds to. */
function kindFromReference(box: Box, refs: TracedReferenceMesh[]): MeshKind {
  let best: TracedReferenceMesh | null = null;
  let bestIou = 0;
  for (const ref of refs) {
    const iou = boxIou(box, ref);
    if (iou > bestIou) {
      bestIou = iou;
      best = ref;
    }
  }
  if (best && bestIou >= 0.15) return ACCENT_KIND[best.accent];

  const cx = (box.minX + box.maxX) / 2;
  const cz = (box.minZ + box.maxZ) / 2;
  let nearest: TracedReferenceMesh | null = null;
  let nearDist = Infinity;
  for (const ref of refs) {
    const d = Math.hypot(cx - ref.cx, cz - ref.cz);
    if (d < nearDist) {
      nearDist = d;
      nearest = ref;
    }
  }
  if (nearest && nearDist < 1.5) return ACCENT_KIND[nearest.accent];

  return "qfp";
}

/**
 * Group `part-*` outline segments into per-component footprint boxes (top-down
 * XZ), assign mesh kinds from circuits-traced.json accent boxes, and keep the
 * member polyline base ids so callers can recover the real outline geometry.
 */
export function componentFootprintsDetailed(
  rawPaths: GridPath[],
): ComponentFootprintDetailed[] {
  const refs = tracedReferenceMeshes();
  const byPolyline = new Map<string, Box>();
  for (const path of rawPaths) {
    if (!path.id) continue;
    const base = partBaseId(path.id);
    if (!base) continue;
    let box = byPolyline.get(base);
    for (const [x, , z] of path.waypoints) {
      if (!box) {
        box = { minX: x, maxX: x, minZ: z, maxZ: z };
        byPolyline.set(base, box);
      } else {
        box.minX = Math.min(box.minX, x);
        box.maxX = Math.max(box.maxX, x);
        box.minZ = Math.min(box.minZ, z);
        box.maxZ = Math.max(box.maxZ, z);
      }
    }
  }

  const bases = [...byPolyline.keys()];
  const polylines = [...byPolyline.values()];
  const n = polylines.length;

  const parent = Array.from({ length: n }, (_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const union = (a: number, b: number) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  };

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (boxesOverlap(polylines[i], polylines[j], CLUSTER_GAP)) union(i, j);
    }
  }

  // Insertion order of `clusters` (first index reaching each root) fixes the
  // comp-N numbering, so persisted meshEdits keyed by these ids stay valid.
  const clusters = new Map<number, { box: Box; members: string[] }>();
  for (let i = 0; i < n; i++) {
    const root = find(i);
    const existing = clusters.get(root);
    if (existing) {
      existing.box = mergeBox(existing.box, polylines[i]);
      existing.members.push(bases[i]);
    } else {
      clusters.set(root, { box: polylines[i], members: [bases[i]] });
    }
  }

  const out: ComponentFootprintDetailed[] = [];
  let idx = 0;
  for (const { box, members } of clusters.values()) {
    out.push({
      id: `comp-${idx++}`,
      ...box,
      cx: (box.minX + box.maxX) / 2,
      cz: (box.minZ + box.maxZ) / 2,
      kind: kindFromReference(box, refs),
      members,
    });
  }
  return out;
}

/**
 * Group `part-*` outline segments into per-component footprint boxes (top-down
 * XZ) and assign mesh kinds from circuits-traced.json accent boxes.
 */
export function componentFootprints(rawPaths: GridPath[]): ComponentFootprint[] {
  return componentFootprintsDetailed(rawPaths).map(({ members: _, ...f }) => f);
}
