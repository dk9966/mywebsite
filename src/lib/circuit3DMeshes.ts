// Bridges the abstract component footprints (the editable "mesh" boxes) to the
// real outline geometry from the GLB. The 2D editor drew labelled placeholder
// boxes; in 3D we render each component's actual `part-*` outline polylines and
// move/scale them with the same meshEdits that drive the boxes.

import {
  componentFootprintsDetailed,
  type ComponentFootprintDetailed,
} from "./circuitComponentFootprints";
import type { MeshKind } from "./circuitMeshBoxes";
import type { CircuitMesh, MeshBounds } from "./circuitMeshes";
import {
  meshFootprintSize,
  normalizeMeshRotationYDeg,
} from "./circuitMeshes";
import type { GridPath, Vec3 } from "./gridBuilder";

function partBaseId(segmentId: string): string | null {
  if (!segmentId.startsWith("part-")) return null;
  const segIdx = segmentId.indexOf("-seg-");
  return segIdx >= 0 ? segmentId.slice(0, segIdx) : segmentId;
}

/** One outline color per mesh kind (traces keep the global cyan). */
const MESH_KIND_OUTLINE_COLORS: Record<MeshKind, string> = {
  qfp: "#66f0f0",
  soic: "#6eb4ff",
  capacitor: "#ffb86e",
  heatsink: "#ff6eb4",
  drum: "#b86eff",
  header: "#b4ff6e",
  connector: "#f0f066",
  smd: "#6effc8",
  pad: "#ff6e6e",
  via: "#a0ffa0",
  cpu: "#66f0f0",
  io: "#f0f066",
  dimm: "#b4ff6e",
  pcie: "#b86eff",
  vrm: "#ffb86e",
};

export function meshOutlineColorForKind(kind: MeshKind): string {
  return MESH_KIND_OUTLINE_COLORS[kind];
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

export type OutlineColorMode = "kind" | "global";

/**
 * Real outline segments transformed by the current mesh edits. A component
 * whose box was moved/scaled/rotated drags its outline along; a deleted
 * component drops out entirely. User-added meshes have no outline and are
 * ignored here.
 *
 * `colorMode: "kind"` (default) tints each component by mesh kind.
 * `colorMode: "global"` omits per-path color so TronGrid uses lineConfig.
 */
export function transformedOutlinePaths(
  model: OutlineModel,
  resolved: CircuitMesh[],
  colorMode: OutlineColorMode = "kind",
): GridPath[] {
  const curById = new Map(resolved.map((m) => [m.id, m]));
  const out: GridPath[] = [];

  for (const [comp, segments] of model.segmentsByComp) {
    const cur = curById.get(comp);
    if (!cur) continue; // deleted component
    const lineColor =
      colorMode === "kind" ? meshOutlineColorForKind(cur.kind) : undefined;
    const orig = model.origBounds.get(comp)!;
    const ow = Math.max(orig.maxX - orig.minX, 1e-6);
    const oh = Math.max(orig.maxZ - orig.minZ, 1e-6);
    const { w: fw, h: fd } = meshFootprintSize(cur);
    const sx = fw / ow;
    const sz = fd / oh;
    const ocx = (orig.minX + orig.maxX) / 2;
    const ocz = (orig.minZ + orig.maxZ) / 2;
    const ccx = (cur.minX + cur.maxX) / 2;
    const ccz = (cur.minZ + cur.maxZ) / 2;
    const rot = normalizeMeshRotationYDeg(cur.rotationYDeg ?? 0);
    const rad = (rot * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const identity =
      rot === 0 &&
      Math.abs(sx - 1) < 1e-6 &&
      Math.abs(sz - 1) < 1e-6 &&
      Math.abs(ccx - ocx) < 1e-6 &&
      Math.abs(ccz - ocz) < 1e-6;

    for (const seg of segments) {
      const colored = lineColor ? { ...seg, lineColor } : { ...seg };
      if (identity) {
        out.push(colored);
        continue;
      }
      out.push({
        ...colored,
        waypoints: seg.waypoints.map(([x, y, z]) => {
          const lx = (x - ocx) * sx;
          const lz = (z - ocz) * sz;
          return [
            ccx + lx * cos + lz * sin,
            y,
            ccz - lx * sin + lz * cos,
          ] as Vec3;
        }),
      });
    }
  }

  return out;
}
