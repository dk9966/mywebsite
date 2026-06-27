// Bridges the abstract component footprints (the editable "mesh" boxes) to the
// real outline geometry from the GLB. The 2D editor drew labelled placeholder
// boxes; in 3D we render each component's actual `part-*` outline polylines and
// move/scale them with the same meshEdits that drive the boxes.

import {
  componentFootprintsDetailed,
  type ComponentFootprintDetailed,
} from "./circuitComponentFootprints";
import type { CircuitMesh, MeshBounds } from "./circuitMeshes";
import type { GridPath, Vec3 } from "./gridBuilder";

function partBaseId(segmentId: string): string | null {
  if (!segmentId.startsWith("part-")) return null;
  const segIdx = segmentId.indexOf("-seg-");
  return segIdx >= 0 ? segmentId.slice(0, segIdx) : segmentId;
}

export type OutlineModel = {
  footprints: ComponentFootprintDetailed[];
  /** Original (baseline) footprint bounds keyed by comp id. */
  origBounds: Map<string, MeshBounds>;
  /** Real outline segments grouped by the comp id they belong to. */
  segmentsByComp: Map<string, GridPath[]>;
  /** Y extent of all part outlines (used for box heights / side framing). */
  yMin: number;
  yMax: number;
};

/** One-time decomposition of raw paths into per-component outline geometry. */
export function buildOutlineModel(raw: GridPath[]): OutlineModel {
  const footprints = componentFootprintsDetailed(raw);

  const compOfBase = new Map<string, string>();
  const origBounds = new Map<string, MeshBounds>();
  for (const f of footprints) {
    origBounds.set(f.id, {
      minX: f.minX,
      maxX: f.maxX,
      minZ: f.minZ,
      maxZ: f.maxZ,
    });
    for (const base of f.members) compOfBase.set(base, f.id);
  }

  const segmentsByComp = new Map<string, GridPath[]>();
  let yMin = Infinity;
  let yMax = -Infinity;
  for (const p of raw) {
    const base = p.id ? partBaseId(p.id) : null;
    if (!base) continue;
    const comp = compOfBase.get(base);
    if (!comp) continue;
    for (const [, y] of p.waypoints) {
      if (y < yMin) yMin = y;
      if (y > yMax) yMax = y;
    }
    const list = segmentsByComp.get(comp);
    if (list) list.push(p);
    else segmentsByComp.set(comp, [p]);
  }

  if (!Number.isFinite(yMin)) {
    yMin = 0;
    yMax = 0;
  }

  return { footprints, origBounds, segmentsByComp, yMin, yMax };
}

function affineXZ(orig: MeshBounds, cur: MeshBounds) {
  const ow = Math.max(orig.maxX - orig.minX, 1e-6);
  const oh = Math.max(orig.maxZ - orig.minZ, 1e-6);
  const sx = (cur.maxX - cur.minX) / ow;
  const sz = (cur.maxZ - cur.minZ) / oh;
  return { sx, sz, ox: orig.minX, oz: orig.minZ, cx: cur.minX, cz: cur.minZ };
}

/**
 * Real outline segments transformed by the current mesh edits. A component
 * whose box was moved/scaled drags its outline along; a deleted component drops
 * out entirely. User-added meshes have no outline and are ignored here.
 */
export function transformedOutlinePaths(
  model: OutlineModel,
  resolved: CircuitMesh[],
): GridPath[] {
  const curById = new Map(resolved.map((m) => [m.id, m]));
  const out: GridPath[] = [];

  for (const [comp, segments] of model.segmentsByComp) {
    const cur = curById.get(comp);
    if (!cur) continue; // deleted component
    const orig = model.origBounds.get(comp)!;
    const t = affineXZ(orig, cur);
    const identity =
      Math.abs(t.sx - 1) < 1e-6 &&
      Math.abs(t.sz - 1) < 1e-6 &&
      Math.abs(t.cx - t.ox) < 1e-6 &&
      Math.abs(t.cz - t.oz) < 1e-6;

    for (const seg of segments) {
      if (identity) {
        out.push(seg);
        continue;
      }
      out.push({
        ...seg,
        waypoints: seg.waypoints.map(
          ([x, y, z]) =>
            [
              t.cx + (x - t.ox) * t.sx,
              y,
              t.cz + (z - t.oz) * t.sz,
            ] as Vec3,
        ),
      });
    }
  }

  return out;
}
