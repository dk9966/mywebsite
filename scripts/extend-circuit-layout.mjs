// Extends the circuits-editor board layout: fills the sparse "beginning"
// (left of x≈3, where one hero line was already dragged out to x=-18) with an
// entrance network, and continues the board rightward past x=54 with new
// buses and components. Written in the board's PCB/Tron style: axis-aligned
// runs, 90° staircase jogs, twin parallel pairs with connector stubs, and
// component rectangles whose edges carry explicit connection vertices so
// feeder traces share real junctions (the flood scheduler then draws each
// component as a continuation of the wire that reaches it).
//
// Output goes into src/data/circuits-tuning.json:
//   - topology.added    ← user-ext-* two-point segments (editable in editor)
//   - meshEdits.added   ← mesh-user-ext-* component boxes (drive 3D rises)
//
// Re-runnable: previous user-ext-* / mesh-user-ext-* entries are replaced.
//
//   node scripts/extend-circuit-layout.mjs

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const TUNING_PATH = join(root, "src/data/circuits-tuning.json");
const TRACED_PATH = join(root, "plans/circuit design/circuits-traced.json");

/** Board plane Y (GLB part base; existing junctions sit here or within weld eps). */
const Y = 0.003000000026077032;
/** Endpoints this close weld into one junction (mirrors JUNCTION_WELD_EPS). */
const WELD_EPS = 0.05;

// --- Weld anchors: existing open trace tips the extension connects onto. ----
// Verified against the current data at runtime; the script aborts if one is
// missing so a future re-trace can't silently produce a disconnected board.
const ANCHORS = {
  heroTail: [-18.0806, 7.2726], // trace-2 end (the line you dragged out)
  trace7: [3.291, 7.5729], // trace-7 start
  trace19: [3.3843, 5.801], // trace-19 start
  trace26: [4.9189, 8.9884], // trace-26 start
  trace24: [53.9658, 10.6162], // trace-24 start (right side)
};

// --- Geometry helpers --------------------------------------------------------

let segCounter = 0;
const segments = [];

/** One axis-aligned (or explicit) two-point segment. */
function seg(x0, z0, x1, z1) {
  segCounter += 1;
  segments.push({
    id: `user-ext-${segCounter}`,
    start: [x0, Y, z0],
    end: [x1, Y, z1],
  });
}

/** Polyline as consecutive segments; every interior point is a real junction. */
function chain(pts) {
  for (let i = 0; i < pts.length - 1; i++) {
    seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
  }
}

/**
 * Component rectangle outline with connection vertices inserted on its edges.
 * Feeder traces that end exactly on a vertex share a junction with the box,
 * so the flood front flows from the wire into the outline and wraps it.
 * verts: { top?: x[], bottom?: x[], left?: z[], right?: z[] }
 */
function rect(minX, minZ, maxX, maxZ, verts = {}) {
  const asc = (a, b) => a - b;
  const top = [minX, ...(verts.top ?? []).slice().sort(asc), maxX];
  const bottom = [minX, ...(verts.bottom ?? []).slice().sort(asc), maxX];
  const left = [minZ, ...(verts.left ?? []).slice().sort(asc), maxZ];
  const right = [minZ, ...(verts.right ?? []).slice().sort(asc), maxZ];

  for (let i = 0; i < top.length - 1; i++) seg(top[i], minZ, top[i + 1], minZ);
  for (let i = 0; i < bottom.length - 1; i++)
    seg(bottom[i], maxZ, bottom[i + 1], maxZ);
  for (let i = 0; i < left.length - 1; i++)
    seg(minX, left[i], minX, left[i + 1]);
  for (let i = 0; i < right.length - 1; i++)
    seg(maxX, right[i], maxX, right[i + 1]);
}

let meshCounter = 0;
const meshes = [];

function mesh(kind, minX, minZ, maxX, maxZ, verts = {}) {
  meshCounter += 1;
  meshes.push({ id: `mesh-user-ext-${meshCounter}`, kind, minX, maxX, minZ, maxZ });
  rect(minX, minZ, maxX, maxZ, verts);
}

// --- Verify anchors still exist ----------------------------------------------

const traced = JSON.parse(readFileSync(TRACED_PATH, "utf8"));
const tuning = JSON.parse(readFileSync(TUNING_PATH, "utf8"));

function currentTraceTips() {
  const PAD = 54;
  const W = 58.0;
  const xs = [];
  const ys = [];
  for (const line of traced.lines)
    for (const [x, y] of line) {
      xs.push(x);
      ys.push(y);
    }
  for (const boxes of Object.values(traced.boxes))
    for (const b of boxes) {
      xs.push(b.x, b.x + b.w);
      ys.push(b.y, b.y + b.h);
    }
  const minx = Math.min(...xs) - PAD;
  const miny = Math.min(...ys) - PAD;
  const s = W / (Math.max(...xs) + PAD - minx);

  const geo = tuning.topology.geometry;
  const tips = [];
  for (let i = 0; i < traced.lines.length; i++) {
    const line = traced.lines[i];
    const ends = [
      { segId: `trace-${i}-seg-0`, key: "start", px: line[0] },
      {
        segId: `trace-${i}-seg-${line.length - 2}`,
        key: "end",
        px: line[line.length - 1],
      },
    ];
    for (const e of ends) {
      const ov = geo[e.segId]?.[e.key];
      tips.push(
        ov ? [ov[0], ov[2]] : [(e.px[0] - minx) * s, (e.px[1] - miny) * s],
      );
    }
  }
  return tips;
}

const tips = currentTraceTips();
for (const [name, [ax, az]] of Object.entries(ANCHORS)) {
  const hit = tips.some(
    ([tx, tz]) => Math.hypot(tx - ax, tz - az) <= WELD_EPS,
  );
  if (!hit) {
    console.error(
      `anchor "${name}" (${ax}, ${az}) no longer matches an open trace tip — ` +
        `re-derive ANCHORS before running.`,
    );
    process.exit(1);
  }
}

// =============================================================================
// LEFT — the entrance (x -20 … 9.5). Your hero line already runs out to
// x=-18.08 at z 7.27; everything here builds the runway around it.
// =============================================================================

// 1. Twin partner for the hero line: enters alongside it (0.7 below), then
//    staircases down and welds onto trace-26's open tip. Broken at x=-12.4
//    where the twin connector stub lands.
chain([
  [-20, 7.9727],
  [-12.4, 7.9727],
  [-8.6, 7.9727],
  [-8.6, ANCHORS.trace26[1]],
  ANCHORS.trace26,
]);
// Twin connector stub: reaches up toward the hero line's body. Its top end
// ignites by proximity as the hero front passes (a soft touch, like the clip's
// staircase links between parallel pairs).
seg(-12.4, 7.9727, -12.4, ANCHORS.heroTail[1]);

// 2. Upper bus pair. Main line staircases into trace-19's tip; its twin peels
//    off north and terminates on a via.
chain([
  [-20, 5.1],
  [-13, 5.1],
  [-13, ANCHORS.trace19[1]],
  ANCHORS.trace19,
]);
chain([
  [-20, 4.4],
  [-11.6, 4.4],
  [-11.6, 3.4],
  [-2, 3.4],
  [-2, 4.6],
  [2.6, 4.6],
]);
mesh("via", 2.6, 4.1, 3.6, 5.1, { left: [4.6] });

// 3. Long southern route into trace-7's tip, entering bottom-left. Broken at
//    x=-17.6 where the capacitor feeder drops off.
chain([
  [-20, 10.9],
  [-17.6, 10.9],
  [-15.2, 10.9],
  [-15.2, 9.9],
  [-9.8, 9.9],
  [-9.8, ANCHORS.trace7[1]],
  ANCHORS.trace7,
]);
// Capacitor near the scan start — an early 3D pop as the scan kicks off.
seg(-17.6, 10.9, -17.6, 11.5);
mesh("capacitor", -18.6, 11.5, -16.6, 13.5, { top: [-17.6] });

// 4. Isolated fragment (the clip's "second spawn" beat: a short piece that
//    pops in on its own), ending on a pad.
chain([
  [-4.8, 11.8],
  [-4.8, 10.4],
  [0.8, 10.4],
]);
mesh("pad", 0.8, 9.8, 2.0, 11.0, { left: [10.4] });

// =============================================================================
// RIGHT — the extension (x 54 … 82.6). New lanes route around the existing
// QFP at x 51.5–56.1, feed a new component cluster, and run off the edge.
// =============================================================================

// 5. Bottom lane pair (fresh open-left starts; they self-seed when the scan
//    front reaches them). L1 runs into the new SOIC; its twin L2 staircases up
//    into the new QFP's top edge. Connector stub at x=56.2.
chain([
  [54.6, 2.7],
  [56.2, 2.7],
  [60, 2.7],
  [60, 3.5],
  [71.2, 3.5],
]);
chain([
  [54.6, 3.4],
  [56.2, 3.4],
  [58.9, 3.4],
  [58.9, 4.2],
  [63.2, 4.2],
  [63.2, 4.9],
]);
seg(56.2, 2.7, 56.2, 3.4);

// 6. From trace-24's open tip: staircase into the new heatsink.
chain([
  ANCHORS.trace24,
  [56.6, ANCHORS.trace24[1]],
  [56.6, 9.9],
  [66.8, 9.9],
]);

// 7. Mid feeders into the QFP's left edge (short pair clearing the existing
//    component at x≤56.1).
chain([
  [56.5, 6.2],
  [61.4, 6.2],
]);
chain([
  [56.5, 6.9],
  [59.6, 6.9],
  [59.6, 7.6],
  [61.4, 7.6],
]);

// 8. The new component cluster.
mesh("qfp", 61.4, 4.9, 65.4, 8.9, {
  top: [63.2],
  left: [6.2, 7.6],
  right: [5.8, 7.0],
  bottom: [63.6],
});
mesh("soic", 71.2, 2.5, 75.2, 4.5, { left: [3.5], right: [3.5] });
mesh("heatsink", 66.8, 8.7, 71.4, 11.4, {
  left: [9.9],
  bottom: [68.3],
  right: [10.3],
});
mesh("header", 61.8, 10.0, 65.8, 11.5, { top: [63.6] });

// QFP bottom → header top.
seg(63.6, 8.9, 63.6, 10.0);

// 9. Outputs running off the right edge (staggered open ends, like the
//    existing board's ragged left edge).
chain([
  [65.4, 5.8],
  [69.8, 5.8],
  [69.8, 5.0],
  [77.6, 5.0],
  [77.6, 6.4],
  [81.5, 6.4],
]);
chain([
  [65.4, 7.0],
  [72.4, 7.0],
  [72.4, 7.8],
  [78.8, 7.8],
]);
chain([
  [75.2, 3.5],
  [78.4, 3.5],
  [78.4, 2.4],
  [82, 2.4],
]);
chain([
  [71.4, 10.3],
  [80.6, 10.3],
]);
mesh("capacitor", 80.6, 9.3, 82.6, 11.3, { left: [10.3] });

// 10. Southern sweep lane under the cluster, dipping to the heatsink's bottom
//     edge on the way past.
chain([
  [55.2, 12.1],
  [68.3, 12.1],
  [68.3, 11.4],
]);

// =============================================================================
// Write
// =============================================================================

const keepSeg = (a) => !a.id.startsWith("user-ext-");
const keepMesh = (m) => !m.id.startsWith("mesh-user-ext-");

tuning.topology.added = [...tuning.topology.added.filter(keepSeg), ...segments];
tuning.topology.deleted = tuning.topology.deleted.filter(
  (id) => !id.startsWith("user-ext-"),
);
for (const id of Object.keys(tuning.topology.geometry)) {
  if (id.startsWith("user-ext-")) delete tuning.topology.geometry[id];
}
tuning.meshEdits.added = [
  ...tuning.meshEdits.added.filter(keepMesh),
  ...meshes,
];
tuning.meshEdits.deleted = tuning.meshEdits.deleted.filter(
  (id) => !id.startsWith("mesh-user-ext-"),
);

writeFileSync(TUNING_PATH, `${JSON.stringify(tuning, null, 2)}\n`);
console.log(
  `wrote ${segments.length} segments + ${meshes.length} meshes → ${TUNING_PATH}`,
);
