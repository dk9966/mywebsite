/**
 * Report whether editable circuit lines are flat (constant Y), straight (2-point
 * segments), and on the 45° grid in XZ — same criteria Snap 45° uses.
 *
 *   pnpm tsx scripts/check-circuit-line-geometry.ts
 */
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { applyTopology } from "../src/lib/circuitTopology";
import type { GridPath, Vec3 } from "../src/lib/gridBuilder";
import {
  buildRawCircuitPaths,
} from "../src/lib/tronPathsFromCircuitsTraced";
import publishedTuning from "../src/data/circuits-tuning.json";
import type { CircuitTuning } from "../src/stores/circuitTuning";

const GLB = fileURLToPath(
  new URL("../public/models/circuits-traced-outline.glb", import.meta.url),
);

const QUARTER = Math.PI / 4;
const ANGLE_TOL_DEG = 0.25;
const ANGLE_TOL = (ANGLE_TOL_DEG * Math.PI) / 180;
const Y_FLAT_TOL = 1e-4;
const MIN_XZ_LEN = 1e-6;

function isEditable(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
}

function loadScene(): Promise<THREE.Object3D> {
  const buf = readFileSync(GLB);
  const arr = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.parse(arr as ArrayBuffer, "", (g) => resolve(g.scene), reject);
  });
}

type AngleKind = "horizontal" | "vertical" | "diag45" | "diag135" | "other";

function classifyAngleDeg(deg: number): AngleKind {
  const n = ((deg % 180) + 180) % 180;
  if (n <= ANGLE_TOL_DEG || n >= 180 - ANGLE_TOL_DEG) return "horizontal";
  if (Math.abs(n - 90) <= ANGLE_TOL_DEG) return "vertical";
  if (Math.abs(n - 45) <= ANGLE_TOL_DEG) return "diag45";
  if (Math.abs(n - 135) <= ANGLE_TOL_DEG) return "diag135";
  return "other";
}

type LineReport = {
  id: string;
  flat: boolean;
  straight: boolean;
  on45: boolean;
  angleDeg: number;
  snapDevDeg: number;
  yDelta: number;
  xzLen: number;
  kind: AngleKind;
  start: Vec3;
  end: Vec3;
};

function analyzeLine(p: GridPath): LineReport | null {
  if (!isEditable(p.id) || p.hidden || p.waypoints.length < 2) return null;

  const start = p.waypoints[0];
  const end = p.waypoints[p.waypoints.length - 1];
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const dz = end[2] - start[2];
  const xzLen = Math.hypot(dx, dz);
  if (xzLen < MIN_XZ_LEN) return null;

  const angle = Math.atan2(dz, dx);
  const snapped = Math.round(angle / QUARTER) * QUARTER;
  let deviation = Math.abs(angle - snapped);
  if (deviation > Math.PI) deviation = 2 * Math.PI - deviation;

  const angleDeg = (angle * 180) / Math.PI;
  const snapDevDeg = (deviation * 180) / Math.PI;

  let straight = p.waypoints.length === 2;
  if (!straight) {
    straight = p.waypoints.every((wp) => {
      const t =
        xzLen > 0
          ? ((wp[0] - start[0]) * dx + (wp[2] - start[2]) * dz) / (xzLen * xzLen)
          : 0;
      const px = start[0] + t * dx;
      const pz = start[2] + t * dz;
      return Math.hypot(wp[0] - px, wp[2] - pz) <= 1e-4;
    });
  }

  return {
    id: p.id!,
    flat: Math.abs(dy) <= Y_FLAT_TOL,
    straight,
    on45: deviation <= ANGLE_TOL,
    angleDeg,
    snapDevDeg,
    yDelta: dy,
    xzLen,
    kind: classifyAngleDeg(angleDeg),
    start,
    end,
  };
}

async function main() {
  const scene = await loadScene();
  const raw = buildRawCircuitPaths(scene);
  const tuning = publishedTuning as unknown as CircuitTuning;
  const paths = applyTopology(raw, tuning.topology);

  const reports = paths
    .map(analyzeLine)
    .filter((r): r is LineReport => r !== null);

  const flat = reports.filter((r) => r.flat);
  const notFlat = reports.filter((r) => !r.flat);
  const straight = reports.filter((r) => r.straight);
  const notStraight = reports.filter((r) => !r.straight);
  const on45 = reports.filter((r) => r.on45);
  const off45 = reports.filter((r) => !r.on45);

  const byKind = {
    horizontal: reports.filter((r) => r.kind === "horizontal").length,
    vertical: reports.filter((r) => r.kind === "vertical").length,
    diag45: reports.filter((r) => r.kind === "diag45").length,
    diag135: reports.filter((r) => r.kind === "diag135").length,
    other: reports.filter((r) => r.kind === "other").length,
  };

  console.log("Circuit line geometry check");
  console.log("Source: src/data/circuits-tuning.json + GLB baseline");
  console.log(
    "(Browser localStorage drafts are not visible from this script.)",
  );
  console.log("");
  console.log(`Editable segments analyzed: ${reports.length}`);
  console.log(
    `Flat (|ΔY| ≤ ${Y_FLAT_TOL}): ${flat.length} ok, ${notFlat.length} sloped`,
  );
  console.log(
    `Straight (2-point or collinear waypoints): ${straight.length} ok, ${notStraight.length} bent`,
  );
  console.log(
    `45° grid (±${ANGLE_TOL_DEG}° in XZ): ${on45.length} ok, ${off45.length} off-grid`,
  );
  console.log("");
  console.log("Angle buckets (on-grid only):");
  console.log(`  horizontal: ${byKind.horizontal}`);
  console.log(`  vertical:   ${byKind.vertical}`);
  console.log(`  45° diag:   ${byKind.diag45}`);
  console.log(`  135° diag:  ${byKind.diag135}`);
  console.log(`  off-grid:   ${byKind.other}`);

  const worstOff45 = [...off45].sort((a, b) => b.snapDevDeg - a.snapDevDeg);
  if (worstOff45.length > 0) {
    console.log("");
    console.log(`Worst off-grid lines (top ${Math.min(15, worstOff45.length)}):`);
    for (const r of worstOff45.slice(0, 15)) {
      console.log(
        `  ${r.id}: angle=${r.angleDeg.toFixed(2)}° dev=${r.snapDevDeg.toFixed(2)}° yΔ=${r.yDelta.toExponential(2)}`,
      );
    }
  }

  if (notFlat.length > 0) {
    console.log("");
    console.log(`Sloped lines (top ${Math.min(10, notFlat.length)} by |ΔY|):`);
    const sorted = [...notFlat].sort((a, b) => Math.abs(b.yDelta) - Math.abs(a.yDelta));
    for (const r of sorted.slice(0, 10)) {
      console.log(
        `  ${r.id}: yΔ=${r.yDelta.toExponential(3)} startY=${r.start[1].toFixed(4)} endY=${r.end[1].toFixed(4)}`,
      );
    }
  }

  if (notStraight.length > 0) {
    console.log("");
    console.log("Non-straight lines:");
    for (const r of notStraight.slice(0, 10)) {
      console.log(`  ${r.id}: ${paths.find((p) => p.id === r.id)!.waypoints.length} waypoints`);
    }
  }

  const allGood = notFlat.length === 0 && notStraight.length === 0 && off45.length === 0;
  console.log("");
  console.log(allGood ? "PASS: all lines flat, straight, and on 45° grid." : "FAIL: see issues above.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
