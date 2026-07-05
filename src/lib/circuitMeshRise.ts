// Occasional 3D pop-ups for the left-to-right scan, matching the reference
// clip (plans/clips/02 - Tron Lines): most of the board stays flat line-work,
// but as the scan front passes some components their wireframe volume grows
// straight up — corner risers shoot vertically, then a top "crown" wraps the
// perimeter and closes the box.
//
// The subset that rises is deterministic (FNV-1a hash of the mesh id), so the
// same components pop on every playback and survive editor round-trips. Flat
// kinds (smd/pad/via) never rise.

import type { MeshKind } from "./circuitMeshBoxes";
import type { CircuitMesh } from "./circuitMeshes";
import { totalPathLength, type GridPath, type Vec3 } from "./gridBuilder";

/** Rise height per kind, in multiples of the board's part-outline height. */
export const RISE_HEIGHT_FACTOR: Record<MeshKind, number> = {
  heatsink: 4.5,
  drum: 4.0,
  capacitor: 3.4,
  cpu: 3.0,
  dimm: 2.6,
  pcie: 2.6,
  qfp: 2.6,
  connector: 2.0,
  io: 2.0,
  vrm: 2.0,
  header: 1.8,
  soic: 1.6,
  smd: 0,
  pad: 0,
  via: 0,
};

/** Fraction of eligible meshes that rise ("occasional"). */
export const DEFAULT_RISE_PROBABILITY = 0.5;
/** Seconds for a corner riser to reach full height. */
const RISE_DURATION = 0.45;
/** Trailing (right-side) corners start this long after the leading pair. */
const TRAILING_STAGGER = 0.15;
/** Seconds for the top crown to wrap the perimeter after risers finish. */
const CROWN_DURATION = 0.5;

/** FNV-1a → [0,1). Stable per id so the "occasional" picks never reshuffle. */
function hash01(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return ((h >>> 0) % 100000) / 100000;
}

export type MeshRiseOptions = {
  /** Board plane (world Y) the risers grow from. */
  baseY: number;
  /** World height of the flat part outlines; rise heights scale off this. */
  unitHeight: number;
  /** Fraction of eligible meshes that rise. Default DEFAULT_RISE_PROBABILITY. */
  probability?: number;
  /**
   * Board transform applied to generated waypoints — pass the same transform
   * `applyTuning` uses (see makeBoardTransform) so rises land on the board.
   */
  transformWaypoints?: (waypoints: Vec3[]) => Vec3[];
};

export type MeshRiseSchedule = {
  /** Post-transform board min X the scan starts from. */
  boardMinX: number;
  /** Scan pan speed (world units/sec) — timing.panSpeed. */
  panSpeed: number;
  /** Seconds before the scan starts — timing.startTime. */
  startTime: number;
  /** Camera lag behind the scan front — topViewCamera.frontLagSec. */
  frontLagSec: number;
};

export function meshShouldRise(
  mesh: Pick<CircuitMesh, "id" | "kind">,
  probability = DEFAULT_RISE_PROBABILITY,
): boolean {
  return (
    (RISE_HEIGHT_FACTOR[mesh.kind] ?? 0) > 0 && hash01(mesh.id) < probability
  );
}

function pathMinX(waypoints: Vec3[]): number {
  let minX = Infinity;
  for (const [x] of waypoints) minX = Math.min(minX, x);
  return minX;
}

/**
 * Wireframe extrusion paths for the meshes that rise, scheduled against the
 * scan: a mesh starts growing the moment the camera centre reaches its left
 * edge. Returned paths carry final spawnTime/cursorSpeed — append them AFTER
 * `applyTuning` so the flood scheduler never rewrites them.
 */
export function meshRisePaths(
  meshes: CircuitMesh[],
  opts: MeshRiseOptions,
  schedule: MeshRiseSchedule,
): GridPath[] {
  const probability = opts.probability ?? DEFAULT_RISE_PROBABILITY;
  const xf = opts.transformWaypoints ?? ((w: Vec3[]) => w);
  const out: GridPath[] = [];

  for (const mesh of meshes) {
    if (!meshShouldRise(mesh, probability)) continue;

    const h = (RISE_HEIGHT_FACTOR[mesh.kind] ?? 0) * opts.unitHeight;
    if (h <= 0) continue;

    const { minX, maxX, minZ, maxZ } = mesh;
    const y0 = opts.baseY;
    const y1 = y0 + h;
    const midZ = (minZ + maxZ) / 2;

    // Corner risers: straight up from the board plane. Leading (left) pair
    // first, trailing pair a beat later, so the box "sweeps" with the scan.
    const corners: Array<{ x: number; z: number; leading: boolean }> = [
      { x: minX, z: minZ, leading: true },
      { x: minX, z: maxZ, leading: true },
      { x: maxX, z: minZ, leading: false },
      { x: maxX, z: maxZ, leading: false },
    ];
    const risers = corners.map((c) =>
      xf([
        [c.x, y0, c.z],
        [c.x, y1, c.z],
      ]),
    );

    // Top crown: both halves emerge from the same leading corner (minX,maxZ)
    // riser top and wrap opposite ways around the perimeter, meeting at the
    // middle of the trailing edge.
    const crownA = xf([
      [minX, y1, maxZ],
      [minX, y1, minZ],
      [maxX, y1, minZ],
      [maxX, y1, midZ],
    ]);
    const crownB = xf([
      [minX, y1, maxZ],
      [maxX, y1, maxZ],
      [maxX, y1, midZ],
    ]);

    // Spawn when the scan camera centre reaches the mesh's (transformed) left
    // edge: camX(t) = boardMinX + (t - startTime - frontLagSec) * panSpeed.
    const meshMinX = Math.min(...risers.map(pathMinX));
    const t0 = Math.max(
      schedule.startTime,
      schedule.startTime +
        schedule.frontLagSec +
        (schedule.panSpeed > 0
          ? (meshMinX - schedule.boardMinX) / schedule.panSpeed
          : 0),
    );

    const riserSpeed = h / RISE_DURATION;
    const crownStart = t0 + RISE_DURATION;

    risers.forEach((waypoints, i) => {
      out.push({
        id: `rise-${mesh.id}-r${i}`,
        waypoints,
        spawnTime: corners[i].leading ? t0 : t0 + TRAILING_STAGGER,
        cursorSpeed: riserSpeed,
      });
    });
    out.push({
      id: `rise-${mesh.id}-crown-a`,
      waypoints: crownA,
      spawnTime: crownStart,
      cursorSpeed: Math.max(totalPathLength(crownA), 1e-3) / CROWN_DURATION,
    });
    out.push({
      id: `rise-${mesh.id}-crown-b`,
      waypoints: crownB,
      spawnTime: crownStart,
      cursorSpeed: Math.max(totalPathLength(crownB), 1e-3) / CROWN_DURATION,
    });
  }

  return out;
}
