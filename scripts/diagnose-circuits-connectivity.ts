/**
 * Diagnostic: reproduce the circuits-outline scheduled paths exactly as the app
 * builds them, then report trace<->part connectivity and spawn ordering so we
 * can see whether meshes (part loops) draw before a circuit touches them.
 *
 *   pnpm tsx scripts/diagnose-circuits-connectivity.ts
 */
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import {
  splitPathsIntoSegments,
  totalPathLength,
  type GridPath,
  type Vec3,
} from "../src/lib/gridBuilder";
import { tronLinesFromGLB } from "../src/lib/tronLinesFromGLB";
import {
  applyTuning,
  CIRCUITS_OUTLINE_CURSOR_SPEED,
  snapTraceEndpointsToPartOutlines,
  tracePathsFromCircuitsTraced,
} from "../src/lib/tronPathsFromCircuitsTraced";
import publishedTuning from "../src/data/circuits-tuning.json";
import type { CircuitTuning } from "../src/stores/circuitTuning";

const BASE_PLANE_EPS = 0.05;
const GLB = fileURLToPath(
  new URL("../public/models/circuits-traced-outline.glb", import.meta.url),
);

function loadScene(): Promise<THREE.Object3D> {
  const buf = readFileSync(GLB);
  const arr = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.parse(arr as ArrayBuffer, "", (g) => resolve(g.scene), reject);
  });
}

function buildRawPaths(scene: THREE.Object3D): GridPath[] {
  const partPaths = tronLinesFromGLB(scene, { tag: "part" }).map((p, i) => ({
    ...p,
    id: `part-${i}`,
    spawnTime: 0,
  }));

  let baseY = Infinity;
  for (const p of partPaths) for (const [, y] of p.waypoints) baseY = Math.min(baseY, y);
  if (!Number.isFinite(baseY)) baseY = 0;

  const alignedParts = partPaths.map((p) => ({
    ...p,
    waypoints: p.waypoints.map(
      ([x, y, z]) => [x, Math.abs(y - baseY) <= BASE_PLANE_EPS ? baseY : y, z] as Vec3,
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

const Q = 1e-3;
const key = (v: Vec3) =>
  `${Math.round(v[0] / Q)},${Math.round(v[1] / Q)},${Math.round(v[2] / Q)}`;

function kind(id: string): "part" | "trace" | "other" {
  if (id.startsWith("part-")) return "part";
  if (id.startsWith("trace-")) return "trace";
  return "other";
}

async function main() {
  const scene = await loadScene();
  const raw = buildRawPaths(scene);
  const tuning = publishedTuning as unknown as CircuitTuning;
  const paths = applyTuning(raw, tuning).filter(
    (p) => p.id && !p.hidden && p.waypoints.length >= 2,
  );

  const parts = paths.filter((p) => kind(p.id!) === "part");
  const traces = paths.filter((p) => kind(p.id!) === "trace");
  console.log(`segments: ${paths.length} total, ${parts.length} part, ${traces.length} trace`);

  // Spawn-time spread + how many finish drawing after the ~43.5s playback window.
  const PLAYBACK_END = 43.5;
  const spawns = paths.map((p) => p.spawnTime).sort((a, b) => a - b);
  const finishes = paths.map((p) => {
    const sp = p.cursorSpeed ?? CIRCUITS_OUTLINE_CURSOR_SPEED;
    return p.spawnTime + (sp > 0 ? totalPathLength(p.waypoints) / sp : 0);
  });
  const pct = (a: number[], q: number) => a[Math.floor((a.length - 1) * q)];
  console.log(
    `spawn times: min=${spawns[0].toFixed(1)} p50=${pct(spawns, 0.5).toFixed(1)} p90=${pct(spawns, 0.9).toFixed(1)} max=${spawns[spawns.length - 1].toFixed(1)}`,
  );
  console.log(
    `segments spawning after ${PLAYBACK_END}s: ${spawns.filter((s) => s > PLAYBACK_END).length}`,
  );
  console.log(
    `segments finishing after ${PLAYBACK_END}s: ${finishes.filter((f) => f > PLAYBACK_END).length}`,
  );
  const partSpawns = parts.map((p) => p.spawnTime).sort((a, b) => a - b);
  console.log(
    `part spawn times: min=${partSpawns[0].toFixed(1)} p50=${pct(partSpawns, 0.5).toFixed(1)} max=${partSpawns[partSpawns.length - 1].toFixed(1)}`,
  );

  // Draw-speed spread across trace segments.
  const tSpeeds = traces
    .map((p) => p.cursorSpeed ?? CIRCUITS_OUTLINE_CURSOR_SPEED)
    .sort((a, b) => a - b);
  console.log(
    `trace draw speeds: min=${tSpeeds[0].toFixed(1)} p50=${pct(tSpeeds, 0.5).toFixed(1)} p90=${pct(tSpeeds, 0.9).toFixed(1)} max=${tSpeeds[tSpeeds.length - 1].toFixed(1)}`,
  );

  // Largest gap between consecutive segments of the same trace (should be ~0 if
  // the chain is continuous; anything bigger is a weld candidate).
  {
    const ch = new Map<string, Array<(typeof paths)[number]>>();
    for (const p of paths) {
      const m = /^(trace-\d+)-seg-(\d+)$/.exec(p.id!);
      if (!m) continue;
      (ch.get(m[1]) ?? ch.set(m[1], []).get(m[1])!).push(p);
    }
    const gaps: Array<{ trace: string; gap: number }> = [];
    for (const [trace, ps] of ch) {
      ps.sort((a, b) => Number(/-seg-(\d+)$/.exec(a.id!)![1]) - Number(/-seg-(\d+)$/.exec(b.id!)![1]));
      for (let k = 1; k < ps.length; k++) {
        const A = ps[k - 1].waypoints;
        const B = ps[k].waypoints;
        let best = Infinity;
        for (const e1 of [A[0], A[A.length - 1]])
          for (const e2 of [B[0], B[B.length - 1]])
            best = Math.min(best, Math.hypot(e1[0] - e2[0], e1[1] - e2[1], e1[2] - e2[2]));
        gaps.push({ trace, gap: best });
      }
    }
    gaps.sort((a, b) => b.gap - a.gap);
    console.log(
      `largest same-trace consecutive gaps: ${gaps.slice(0, 8).map((g) => `${g.trace}=${g.gap.toExponential(2)}`).join(", ")}`,
    );
  }

  // Per-trace dump: spawn, finish, speed, and the gap to the next connected
  // segment in chain order (a positive gap = a visible pause between segments).
  const dumpTrace = process.env.DUMP_TRACE;
  if (dumpTrace) {
    const ids = paths
      .filter((p) => p.id!.startsWith(`${dumpTrace}-seg-`))
      .sort(
        (a, b) =>
          Number(/-seg-(\d+)$/.exec(a.id!)![1]) -
          Number(/-seg-(\d+)$/.exec(b.id!)![1]),
      );
    console.log(`\n${dumpTrace} segments (chain order):`);
    const fin = (p: (typeof ids)[number]) => {
      const sp = p.cursorSpeed ?? CIRCUITS_OUTLINE_CURSOR_SPEED;
      return p.spawnTime + (sp > 0 ? totalPathLength(p.waypoints) / sp : 0);
    };
    // Min endpoint-to-endpoint distance between consecutive (by index) segments.
    const byIdx = [...ids].sort(
      (a, b) =>
        Number(/-seg-(\d+)$/.exec(a.id!)![1]) -
        Number(/-seg-(\d+)$/.exec(b.id!)![1]),
    );
    for (let k = 1; k < byIdx.length; k++) {
      const prev = byIdx[k - 1].waypoints;
      const cur = byIdx[k].waypoints;
      let best = Infinity;
      for (const e1 of [prev[0], prev[prev.length - 1]])
        for (const e2 of [cur[0], cur[cur.length - 1]])
          best = Math.min(best, Math.hypot(e1[0] - e2[0], e1[1] - e2[1], e1[2] - e2[2]));
      console.log(`  ${byIdx[k - 1].id} <-> ${byIdx[k].id} min endpoint gap = ${best.toExponential(3)}`);
    }
    const bySpawn = [...ids].sort((a, b) => a.spawnTime - b.spawnTime);
    for (let k = 0; k < bySpawn.length; k++) {
      const p = bySpawn[k];
      const f = fin(p);
      const nextSpawn = k + 1 < bySpawn.length ? bySpawn[k + 1].spawnTime : null;
      const gap = nextSpawn === null ? 0 : nextSpawn - f;
      const a = p.waypoints[0];
      const b = p.waypoints[p.waypoints.length - 1];
      console.log(
        `  ${p.id}: spawn=${p.spawnTime.toFixed(2)} finish=${f.toFixed(2)} speed=${(p.cursorSpeed ?? 0).toFixed(1)} len=${totalPathLength(p.waypoints).toFixed(2)} gapToNext=${gap.toFixed(2)} start=[${a[0].toFixed(2)},${a[2].toFixed(2)}] end=[${b[0].toFixed(2)},${b[2].toFixed(2)}]`,
      );
    }
  }

  // Trace-chain ordering check: within each trace polyline, segments are numbered
  // seg-0,seg-1,... along the chain. A correct reveal draws them in sequence (in
  // one consistent direction), so spawn times must be monotonic. A non-monotonic
  // chain means a segment lit out of turn (early or backwards) — the exact bug.
  const segById = new Map(paths.map((p) => [p.id!, p] as const));
  const chains = new Map<string, string[]>();
  for (const p of paths) {
    const m = /^(trace-\d+)-seg-(\d+)$/.exec(p.id!);
    if (!m) continue;
    const arr = chains.get(m[1]) ?? chains.set(m[1], []).get(m[1])!;
    arr.push(p.id!);
  }
  const segIdx = (id: string) => Number(/-seg-(\d+)$/.exec(id)![1]);
  let badChains = 0;
  const offenders: string[] = [];
  for (const [trace, ids] of chains) {
    if (ids.length < 2) continue;
    ids.sort((a, b) => segIdx(a) - segIdx(b));
    const spawns = ids.map((id) => segById.get(id)!.spawnTime);
    const incCount = spawns.filter((s, k) => k > 0 && s < spawns[k - 1] - 1e-3).length;
    const decCount = spawns.filter((s, k) => k > 0 && s > spawns[k - 1] + 1e-3).length;
    // Monotonic in some direction => min(violations) is 0.
    const viol = Math.min(incCount, decCount);
    if (viol > 0) {
      badChains++;
      if (offenders.length < 12) offenders.push(`${trace}(${viol})`);
    }
  }
  console.log(
    `trace chains drawn OUT OF ORDER: ${badChains}/${chains.size}${offenders.length ? ` -> ${offenders.join(", ")}` : ""}`,
  );

  // Draw-direction check: where does each chain START drawing, and does any
  // segment's tip travel "backwards" relative to the chain's overall progression?
  // We define the chain's intended direction by its two extreme endpoints, then
  // flag segments whose drawn tip moves opposite to that.
  let chainsStartingFromRight = 0;
  let backwardSegs = 0;
  const startRightOffenders: string[] = [];
  for (const [trace, ids] of chains) {
    if (ids.length < 2) continue;
    ids.sort((a, b) => segById.get(a)!.spawnTime - segById.get(b)!.spawnTime);
    const first = segById.get(ids[0])!;
    const startPt = first.waypoints[0];
    // Chain extent across all its points.
    let minXk = Infinity;
    let maxXk = -Infinity;
    for (const id of ids)
      for (const [x] of segById.get(id)!.waypoints) {
        minXk = Math.min(minXk, x);
        maxXk = Math.max(maxXk, x);
      }
    const span = maxXk - minXk || 1;
    // How far (fraction) the start point sits from the left extreme.
    const startFrac = (startPt[0] - minXk) / span;
    if (startFrac > 0.5) {
      chainsStartingFromRight++;
      if (startRightOffenders.length < 12)
        startRightOffenders.push(`${trace}(${startFrac.toFixed(2)})`);
    }
    // Net leftward-drawing segments within this chain.
    for (const id of ids) {
      const wp = segById.get(id)!.waypoints;
      if (wp[wp.length - 1][0] < wp[0][0] - 1e-3) backwardSegs++;
    }
  }
  console.log(
    `chains whose drawing STARTS from the right half: ${chainsStartingFromRight}/${chains.size}${startRightOffenders.length ? ` -> ${startRightOffenders.join(", ")}` : ""}`,
  );
  console.log(`trace segments drawing net leftward: ${backwardSegs}`);


  // Junction graph by quantized endpoint.
  const junction = new Map<string, Array<{ id: string; end: 0 | 1 }>>();
  for (const p of paths) {
    const a = key(p.waypoints[0]);
    const b = key(p.waypoints[p.waypoints.length - 1]);
    (junction.get(a) ?? junction.set(a, []).get(a)!).push({ id: p.id!, end: 0 });
    (junction.get(b) ?? junction.set(b, []).get(b)!).push({ id: p.id!, end: 1 });
  }

  // How many part-segment endpoints coincide with a trace endpoint?
  let mixedJunctions = 0;
  const touchedPartSegs = new Set<string>();
  const fedTraceSegs = new Set<string>();
  for (const [, members] of junction) {
    const hasPart = members.some((m) => kind(m.id) === "part");
    const hasTrace = members.some((m) => kind(m.id) === "trace");
    if (hasPart && hasTrace) {
      mixedJunctions++;
      for (const m of members) {
        if (kind(m.id) === "part") touchedPartSegs.add(m.id);
        if (kind(m.id) === "trace") fedTraceSegs.add(m.id);
      }
    }
  }
  console.log(`mixed (part+trace) junctions: ${mixedJunctions}`);
  console.log(`part segments sharing a vertex with a trace: ${touchedPartSegs.size}`);

  // Connected components over shared endpoints; classify each.
  const adj = new Map<string, Set<string>>();
  for (const p of paths) adj.set(p.id!, new Set());
  for (const [, members] of junction) {
    for (let i = 0; i < members.length; i++)
      for (let j = i + 1; j < members.length; j++) {
        adj.get(members[i].id)!.add(members[j].id);
        adj.get(members[j].id)!.add(members[i].id);
      }
  }
  const seen = new Set<string>();
  const comps: string[][] = [];
  for (const p of paths) {
    if (seen.has(p.id!)) continue;
    const stack = [p.id!];
    seen.add(p.id!);
    const comp: string[] = [];
    while (stack.length) {
      const cur = stack.pop()!;
      comp.push(cur);
      for (const n of adj.get(cur) ?? []) if (!seen.has(n)) { seen.add(n); stack.push(n); }
    }
    comps.push(comp);
  }

  const partOnlyComps = comps.filter(
    (c) => c.every((id) => kind(id) === "part") && c.length > 0,
  );
  const mixedComps = comps.filter(
    (c) => c.some((id) => kind(id) === "part") && c.some((id) => kind(id) === "trace"),
  );
  console.log(`components: ${comps.length} total`);
  console.log(`  part-only components (loops with NO trace touching): ${partOnlyComps.length}`);
  console.log(`  mixed part+trace components: ${mixedComps.length}`);

  // For each part loop, earliest part spawn vs earliest trace spawn in its component.
  const byId = new Map(paths.map((p) => [p.id!, p] as const));
  const spawn = (id: string) => byId.get(id)!.spawnTime;
  const finish = (id: string) => {
    const p = byId.get(id)!;
    const sp = p.cursorSpeed ?? 6;
    return p.spawnTime + totalPathLength(p.waypoints) / sp;
  };

  let meshBeforeTouch = 0;
  for (const c of mixedComps) {
    const partSpawn = Math.min(...c.filter((id) => kind(id) === "part").map(spawn));
    // earliest moment any trace in this comp reaches a shared part vertex
    const feeders = c.filter((id) => kind(id) === "trace" && fedTraceSegs.has(id));
    const feedReach = feeders.length ? Math.min(...feeders.map(finish)) : Infinity;
    if (partSpawn < feedReach - 1e-3) meshBeforeTouch++;
  }
  console.log(`mixed components where a part segment spawns BEFORE its feeding trace arrives: ${meshBeforeTouch}`);

  // Global: earliest part spawn vs earliest trace spawn.
  const firstPart = Math.min(...parts.map((p) => p.spawnTime));
  const firstTrace = Math.min(...traces.map((p) => p.spawnTime));
  console.log(`earliest part spawn: ${firstPart.toFixed(3)}s, earliest trace spawn: ${firstTrace.toFixed(3)}s`);

  // How many trace endpoints lie ON a part segment body (T-junction, not vertex)?
  const partSegs = parts.map((p) => ({
    id: p.id!,
    a: p.waypoints[0],
    b: p.waypoints[p.waypoints.length - 1],
  }));
  const distToSeg = (pt: Vec3, a: Vec3, b: Vec3) => {
    const dx = b[0] - a[0];
    const dz = b[2] - a[2];
    const len2 = dx * dx + dz * dz;
    const t = len2 > 1e-12 ? Math.max(0, Math.min(1, ((pt[0] - a[0]) * dx + (pt[2] - a[2]) * dz) / len2)) : 0;
    return { d: Math.hypot(pt[0] - (a[0] + t * dx), pt[2] - (a[2] + t * dz)), t };
  };
  let endpointsOnBody = 0;
  let endpointsNearVertex = 0;
  const partLoopsTouchedByBody = new Set<string>();
  for (const tr of traces) {
    for (const pt of [tr.waypoints[0], tr.waypoints[tr.waypoints.length - 1]]) {
      let best = Infinity;
      let bestSeg = "";
      let bestT = 0;
      for (const s of partSegs) {
        const { d, t } = distToSeg(pt, s.a, s.b);
        if (d < best) { best = d; bestSeg = s.id; bestT = t; }
      }
      if (best <= 0.02) {
        if (bestT > 0.05 && bestT < 0.95) endpointsOnBody++;
        else endpointsNearVertex++;
        partLoopsTouchedByBody.add(bestSeg.replace(/-seg-.*$/, ""));
      }
    }
  }
  console.log(`trace endpoints lying ON a part edge (<=0.02): body=${endpointsOnBody}, nearVertex=${endpointsNearVertex}`);
  console.log(`distinct part loops touched by a trace endpoint (incl. mid-edge): ${partLoopsTouchedByBody.size}`);

  // Per part loop: nearest distance from any of its vertices to any trace segment body.
  const traceSegs = traces.map((p) => ({ a: p.waypoints[0], b: p.waypoints[p.waypoints.length - 1] }));
  const dist3ToSeg = (pt: Vec3, a: Vec3, b: Vec3) => {
    const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    const len2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    const t = len2 > 1e-12 ? Math.max(0, Math.min(1, ((pt[0] - a[0]) * d[0] + (pt[1] - a[1]) * d[1] + (pt[2] - a[2]) * d[2]) / len2)) : 0;
    return Math.hypot(pt[0] - (a[0] + t * d[0]), pt[1] - (a[1] + t * d[1]), pt[2] - (a[2] + t * d[2]));
  };
  const loopOf = (id: string) => id.replace(/-seg-.*$/, "");
  const partLoops = new Map<string, Vec3[]>();
  for (const p of parts) {
    const l = loopOf(p.id!);
    const arr = partLoops.get(l) ?? partLoops.set(l, []).get(l)!;
    arr.push(p.waypoints[0], p.waypoints[p.waypoints.length - 1]);
  }
  const nearests: number[] = [];
  for (const [, verts] of partLoops) {
    let best = Infinity;
    for (const v of verts) for (const s of traceSegs) best = Math.min(best, dist3ToSeg(v, s.a, s.b));
    nearests.push(best);
  }
  nearests.sort((a, b) => a - b);
  const buckets = [0.05, 0.2, 0.5, 1, 2, 4, 8, Infinity];
  const counts = buckets.map(() => 0);
  for (const n of nearests) counts[buckets.findIndex((b) => n <= b)]++;
  console.log(`part loops (${nearests.length}) nearest-vertex-to-any-trace-body distance buckets:`);
  let prev = 0;
  buckets.forEach((b, i) => { console.log(`  <=${b}: ${counts[i]}`); prev = b; });
  console.log(`  median nearest: ${nearests[Math.floor(nearests.length / 2)].toFixed(3)}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
