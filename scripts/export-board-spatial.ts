/**
 * Export a read-only spatial manifest of the Tron circuits board so an agent can
 * reason about where components sit, how traces run, where lines meet, and which
 * gaps are open for new routing.
 *
 * This reads the SAME inputs the editor uses (the outline GLB + a tuning JSON)
 * and writes a sidecar artifact. It never touches the editor state, the store,
 * or the committed tuning file.
 *
 *   pnpm tsx scripts/export-board-spatial.ts                 # uses circuits-tuning.json
 *   pnpm tsx scripts/export-board-spatial.ts --version 2     # uses circuit-versions/2.json
 *   pnpm tsx scripts/export-board-spatial.ts --in path.json  # explicit tuning file
 *   pnpm tsx scripts/export-board-spatial.ts --out path.json # explicit output
 *
 * Default output: src/data/board-spatial.json
 */
import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { buildOutlineModel } from "../src/lib/circuit3DMeshes";
import { MESH_LABELS } from "../src/lib/circuitMeshBoxes";
import {
  footprintsToMeshes,
  resolveMeshes,
  type CircuitMesh,
} from "../src/lib/circuitMeshes";
import { applyTopology } from "../src/lib/circuitTopology";
import type { GridPath, Vec3 } from "../src/lib/gridBuilder";
import { buildRawCircuitPaths } from "../src/lib/tronPathsFromCircuitsTraced";
import type { CircuitTuning } from "../src/stores/circuitTuning";

const GLB = fileURLToPath(
  new URL("../public/models/circuits-traced-outline.glb", import.meta.url),
);
const TUNING_DEFAULT = fileURLToPath(
  new URL("../src/data/circuits-tuning.json", import.meta.url),
);
const OUT_DEFAULT = fileURLToPath(
  new URL("../src/data/board-spatial.json", import.meta.url),
);

/** Max XZ distance to consider a trace endpoint "attached" to a component edge. */
const ATTACH_XZ = 0.35;
/** Endpoints within this distance are treated as the same junction vertex. */
const JUNCTION_EPS = 1e-3;
/** Two component bboxes closer than this (and overlapping on one axis) form a corridor. */
const CORRIDOR_MAX_GAP = 6;
/** Minimum overlap on the shared axis for a corridor to count as a real channel. */
const CORRIDOR_MIN_OVERLAP = 1;
/** Any coordinate past this magnitude is treated as corrupt board data, not geometry. */
const COORD_SANITY = 1e4;

type EdgeSide = "north" | "south" | "east" | "west";

function round(n: number, dp = 4): number {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
}

function isEditableLine(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
}

function parseArgs(argv: string[]): {
  inPath: string;
  outPath: string;
  label: string;
} {
  let inPath = TUNING_DEFAULT;
  let outPath = OUT_DEFAULT;
  let label = "circuits-tuning.json";

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--version") {
      const name = argv[++i];
      inPath = fileURLToPath(
        new URL(`../src/data/circuit-versions/${name}.json`, import.meta.url),
      );
      label = `version ${name}`;
    } else if (arg === "--in") {
      inPath = argv[++i];
      label = inPath;
    } else if (arg === "--out") {
      outPath = argv[++i];
    }
  }
  return { inPath, outPath, label };
}

function loadScene(): Promise<THREE.Object3D> {
  const buf = readFileSync(GLB);
  const arr = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.parse(arr as ArrayBuffer, "", (g) => resolve(g.scene), reject);
  });
}

function loadTuning(path: string): CircuitTuning {
  const raw = JSON.parse(readFileSync(path, "utf8")) as Partial<CircuitTuning>;
  return {
    ...raw,
    topology: raw.topology ?? { geometry: {}, deleted: [], added: [] },
    meshEdits: raw.meshEdits ?? { geometry: {}, deleted: [], added: [] },
  } as CircuitTuning;
}

type ComponentOut = {
  id: string;
  kind: string;
  label: string;
  variant?: string;
  bbox: { minX: number; maxX: number; minZ: number; maxZ: number };
  center: { x: number; z: number };
  size: { w: number; h: number };
  edges: Record<EdgeSide, number>;
};

function isSaneMesh(m: CircuitMesh): boolean {
  return [m.minX, m.maxX, m.minZ, m.maxZ].every(
    (n) => Number.isFinite(n) && Math.abs(n) <= COORD_SANITY,
  );
}

function componentsOut(meshes: CircuitMesh[]): ComponentOut[] {
  return meshes
    .filter(isSaneMesh)
    .map((m) => ({
      id: m.id,
      kind: m.kind,
      label: MESH_LABELS[m.kind] ?? m.kind,
      variant: m.variant,
      bbox: {
        minX: round(m.minX),
        maxX: round(m.maxX),
        minZ: round(m.minZ),
        maxZ: round(m.maxZ),
      },
      center: { x: round((m.minX + m.maxX) / 2), z: round((m.minZ + m.maxZ) / 2) },
      size: { w: round(m.maxX - m.minX), h: round(m.maxZ - m.minZ) },
      edges: {
        // +Z is "south" on screen in the editor's top view; +X is "east".
        north: round(m.minZ),
        south: round(m.maxZ),
        east: round(m.maxX),
        west: round(m.minX),
      },
    }))
    .sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
}

type TraceOut = {
  id: string;
  chain: string;
  start: Vec3;
  end: Vec3;
  angleDeg: number;
  length: number;
};

function chainOf(id: string): string {
  const m = /^(trace-\d+|user-\d+)/.exec(id);
  return m ? m[1] : id;
}

function tracesOut(paths: GridPath[]): TraceOut[] {
  const out: TraceOut[] = [];
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    const start = p.waypoints[0];
    const end = p.waypoints[p.waypoints.length - 1];
    const dx = end[0] - start[0];
    const dz = end[2] - start[2];
    const angle = ((Math.atan2(dz, dx) * 180) / Math.PI + 360) % 180;
    out.push({
      id: p.id,
      chain: chainOf(p.id),
      start: [round(start[0]), round(start[1]), round(start[2])],
      end: [round(end[0]), round(end[1]), round(end[2])],
      angleDeg: round(angle, 2),
      length: round(Math.hypot(dx, dz)),
    });
  }
  return out.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
}

type JunctionOut = { at: Vec3; segments: string[] };

function junctionsOut(paths: GridPath[]): JunctionOut[] {
  const q = (v: Vec3) =>
    `${Math.round(v[0] / JUNCTION_EPS)},${Math.round(v[2] / JUNCTION_EPS)}`;
  const map = new Map<string, { at: Vec3; ids: Set<string> }>();
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    for (const end of [p.waypoints[0], p.waypoints[p.waypoints.length - 1]]) {
      const k = q(end);
      const entry = map.get(k) ?? { at: end, ids: new Set<string>() };
      entry.ids.add(p.id);
      map.set(k, entry);
    }
  }
  const out: JunctionOut[] = [];
  for (const { at, ids } of map.values()) {
    if (ids.size < 2) continue;
    out.push({
      at: [round(at[0]), round(at[1]), round(at[2])],
      segments: [...ids].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
    });
  }
  return out;
}

type AttachmentOut = {
  traceId: string;
  endpoint: "start" | "end";
  componentId: string;
  edge: EdgeSide;
  distXZ: number;
};

/** Nearest edge of a bbox to a point, and its XZ distance. */
function nearestEdge(
  x: number,
  z: number,
  c: ComponentOut,
): { edge: EdgeSide; dist: number } | null {
  const { minX, maxX, minZ, maxZ } = c.bbox;
  const insideX = x >= minX - ATTACH_XZ && x <= maxX + ATTACH_XZ;
  const insideZ = z >= minZ - ATTACH_XZ && z <= maxZ + ATTACH_XZ;
  if (!insideX || !insideZ) return null;

  const cands: Array<{ edge: EdgeSide; dist: number }> = [
    { edge: "west", dist: Math.abs(x - minX) },
    { edge: "east", dist: Math.abs(x - maxX) },
    { edge: "north", dist: Math.abs(z - minZ) },
    { edge: "south", dist: Math.abs(z - maxZ) },
  ];
  cands.sort((a, b) => a.dist - b.dist);
  return cands[0].dist <= ATTACH_XZ ? cands[0] : null;
}

function attachmentsOut(
  paths: GridPath[],
  comps: ComponentOut[],
): AttachmentOut[] {
  const out: AttachmentOut[] = [];
  for (const p of paths) {
    if (!p.id || p.hidden || p.waypoints.length < 2) continue;
    const ends: Array<{ tag: "start" | "end"; pt: Vec3 }> = [
      { tag: "start", pt: p.waypoints[0] },
      { tag: "end", pt: p.waypoints[p.waypoints.length - 1] },
    ];
    for (const { tag, pt } of ends) {
      let best: { c: ComponentOut; edge: EdgeSide; dist: number } | null = null;
      for (const c of comps) {
        const hit = nearestEdge(pt[0], pt[2], c);
        if (hit && (!best || hit.dist < best.dist)) {
          best = { c, edge: hit.edge, dist: hit.dist };
        }
      }
      if (best) {
        out.push({
          traceId: p.id,
          endpoint: tag,
          componentId: best.c.id,
          edge: best.edge,
          distXZ: round(best.dist),
        });
      }
    }
  }
  return out;
}

type CorridorOut = {
  between: [string, string];
  axis: "x" | "z";
  gap: number;
  center: { x: number; z: number };
  span: number;
};

/**
 * Open channels between neighbouring components. For each near pair that overlaps
 * on one axis, report the gap width, its center, and how long the channel runs.
 */
function corridorsOut(comps: ComponentOut[]): CorridorOut[] {
  const out: CorridorOut[] = [];
  for (let i = 0; i < comps.length; i++) {
    for (let j = i + 1; j < comps.length; j++) {
      const a = comps[i].bbox;
      const b = comps[j].bbox;

      // Horizontal channel: components stacked on Z, gap runs along X.
      const zOverlap =
        Math.min(a.maxZ, b.maxZ) - Math.max(a.minZ, b.minZ);
      const xGap =
        Math.max(a.minX, b.minX) - Math.min(a.maxX, b.maxX);
      if (zOverlap >= CORRIDOR_MIN_OVERLAP && xGap > 0 && xGap <= CORRIDOR_MAX_GAP) {
        const lo = Math.min(a.maxX, b.maxX);
        const z0 = Math.max(a.minZ, b.minZ);
        const z1 = Math.min(a.maxZ, b.maxZ);
        out.push({
          between: [comps[i].id, comps[j].id],
          axis: "x",
          gap: round(xGap),
          center: { x: round(lo + xGap / 2), z: round((z0 + z1) / 2) },
          span: round(zOverlap),
        });
      }

      // Vertical channel: components side by side on X, gap runs along Z.
      const xOverlap =
        Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX);
      const zGap =
        Math.max(a.minZ, b.minZ) - Math.min(a.maxZ, b.maxZ);
      if (xOverlap >= CORRIDOR_MIN_OVERLAP && zGap > 0 && zGap <= CORRIDOR_MAX_GAP) {
        const lo = Math.min(a.maxZ, b.maxZ);
        const x0 = Math.max(a.minX, b.minX);
        const x1 = Math.min(a.maxX, b.maxX);
        out.push({
          between: [comps[i].id, comps[j].id],
          axis: "z",
          gap: round(zGap),
          center: { x: round((x0 + x1) / 2), z: round(lo + zGap / 2) },
          span: round(xOverlap),
        });
      }
    }
  }
  return out.sort((a, b) => a.gap - b.gap);
}

function boardBounds(comps: ComponentOut[], traces: TraceOut[]) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  let traceY = 0.003;
  for (const c of comps) {
    minX = Math.min(minX, c.bbox.minX);
    maxX = Math.max(maxX, c.bbox.maxX);
    minZ = Math.min(minZ, c.bbox.minZ);
    maxZ = Math.max(maxZ, c.bbox.maxZ);
  }
  for (const t of traces) {
    for (const pt of [t.start, t.end]) {
      minX = Math.min(minX, pt[0]);
      maxX = Math.max(maxX, pt[0]);
      minZ = Math.min(minZ, pt[2]);
      maxZ = Math.max(maxZ, pt[2]);
    }
    traceY = t.start[1];
  }
  if (!Number.isFinite(minX)) {
    minX = maxX = minZ = maxZ = 0;
  }
  return {
    minX: round(minX),
    maxX: round(maxX),
    minZ: round(minZ),
    maxZ: round(maxZ),
    traceY: round(traceY),
    axes: "XZ plane top view: +X = east/right, +Z = south/down, Y = height",
  };
}

async function main() {
  const { inPath, outPath, label } = parseArgs(process.argv.slice(2));
  const scene = await loadScene();
  const tuning = loadTuning(inPath);

  const raw = buildRawCircuitPaths(scene);
  const model = buildOutlineModel(raw);
  const baselineMeshes = footprintsToMeshes(model.footprints);
  const meshes = resolveMeshes(baselineMeshes, tuning.meshEdits);

  const editableBaseline = raw.filter((p) => isEditableLine(p.id));
  const editablePaths = applyTopology(editableBaseline, tuning.topology);

  const anomalies = meshes
    .filter((m) => !isSaneMesh(m))
    .map((m) => ({
      id: m.id,
      kind: m.kind,
      reason: "coordinate out of board range (likely corrupt meshEdits entry)",
      bbox: { minX: m.minX, maxX: m.maxX, minZ: m.minZ, maxZ: m.maxZ },
    }));

  const components = componentsOut(meshes);
  const traces = tracesOut(editablePaths);
  const junctions = junctionsOut(editablePaths);
  const attachments = attachmentsOut(editablePaths, components);
  const corridors = corridorsOut(components);
  const board = boardBounds(components, traces);

  const manifest = {
    source: label,
    generatedAt: new Date().toISOString(),
    note: "Read-only spatial map for editing circuits-tuning topology + meshEdits. Traces live in topology; components live in meshEdits.",
    counts: {
      components: components.length,
      traces: traces.length,
      junctions: junctions.length,
      attachments: attachments.length,
      corridors: corridors.length,
      anomalies: anomalies.length,
    },
    board,
    components,
    traces,
    junctions,
    attachments,
    corridors,
    anomalies,
  };

  writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

  console.log(`Board spatial manifest written to ${outPath}`);
  console.log(`  source: ${label}`);
  console.log(
    `  components=${components.length} traces=${traces.length} junctions=${junctions.length} attachments=${attachments.length} corridors=${corridors.length}`,
  );
  console.log(
    `  board XZ: x[${board.minX}, ${board.maxX}] z[${board.minZ}, ${board.maxZ}] traceY=${board.traceY}`,
  );
  if (anomalies.length > 0) {
    console.warn(
      `  WARNING: ${anomalies.length} component(s) with out-of-range coords excluded: ${anomalies.map((a) => a.id).join(", ")}`,
    );
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
