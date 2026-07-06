/**
 * Shared primitives for the circuit basement scene: the eight PCB routing
 * directions, a seeded RNG, and the reveal-segment representation every
 * visible line is built from.
 */

export type Rng = () => number

export function mulberry32(seed: number): Rng {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function rangeInt(rng: Rng, min: number, max: number): number {
  return min + Math.floor(rng() * (max - min + 1))
}

/**
 * The eight PCB routing directions as [dx, dz], counterclockwise from +X.
 * Even indices are axis-aligned, odd indices are 45-degree diagonals, so a
 * single index step is always a 45-degree turn.
 */
export const DIRS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [1, 1],
  [0, 1],
  [-1, 1],
  [-1, 0],
  [-1, -1],
  [0, -1],
  [1, -1],
]

export function turn(dir: number, steps: number): number {
  return (dir + steps + 8) % 8
}

export type Vec3 = readonly [number, number, number]

/** One short line piece with the network distance at which it lights up. */
export interface RevealSegment {
  a: Vec3
  b: Vec3
  arrival: number
}

/** Occupancy queries components use to reserve board area. */
export interface AreaGrid {
  isRectFree(minX: number, minZ: number, maxX: number, maxZ: number): boolean
  claimRect(minX: number, minZ: number, maxX: number, maxZ: number): void
}

const MAX_PIECE_LENGTH = 0.6

/**
 * Appends a polyline as short pieces whose arrivals increase with travelled
 * distance, so the reveal grows continuously along it rather than popping in
 * whole segments. Returns the arrival at the end of the polyline.
 */
export function emitPolyline(
  points: readonly Vec3[],
  startArrival: number,
  out: RevealSegment[],
): number {
  let arrival = startArrival
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]
    const b = points[i]
    const length = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2])
    const pieces = Math.max(1, Math.ceil(length / MAX_PIECE_LENGTH))
    for (let k = 0; k < pieces; k++) {
      out.push({
        a: lerp3(a, b, k / pieces),
        b: lerp3(a, b, (k + 1) / pieces),
        arrival: arrival + (length * k) / pieces,
      })
    }
    arrival += length
  }
  return arrival
}

/** Emits a closed loop starting and ending at the first point. */
export function emitLoop(
  points: readonly Vec3[],
  startArrival: number,
  out: RevealSegment[],
): number {
  return emitPolyline([...points, points[0]], startArrival, out)
}

function lerp3(a: Vec3, b: Vec3, t: number): Vec3 {
  return [
    a[0] + (b[0] - a[0]) * t,
    a[1] + (b[1] - a[1]) * t,
    a[2] + (b[2] - a[2]) * t,
  ]
}
