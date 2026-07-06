/**
 * PCB component outlines that terminate traces: wireframe IC bodies, two-pad
 * passives, and via rings. Traces are flat on y = 0; only component bodies
 * have height. Every builder returns exit points from which new traces may
 * continue, so nothing on the board ends dangling.
 */

import {
  type AreaGrid,
  DIRS,
  type RevealSegment,
  type Rng,
  type Vec3,
  emitLoop,
  emitPolyline,
  rangeInt,
  turn,
} from './core'

export interface Exit {
  x: number
  z: number
  dir: number
  arrival: number
}

const CHIP_HEIGHT = 1.5
const PASSIVE_HEIGHT = 0.7
const VIA_RADIUS = 0.7

/**
 * Terminates a trace at (x, z) heading `dir`. Prefers a chip for axis-aligned
 * approaches, then a small passive, then falls back to a via ring, which
 * always fits.
 */
export function placeTerminal(
  x: number,
  z: number,
  dir: number,
  arrival: number,
  rng: Rng,
  area: AreaGrid,
  out: RevealSegment[],
): Exit[] {
  if (dir % 2 === 0 && rng() < 0.5) {
    const exits = tryChip(x, z, dir, arrival, rng, area, out)
    if (exits) return exits
  }
  if (rng() < 0.6) {
    const exits = tryPassive(x, z, dir, arrival, rng, area, out)
    if (exits) return exits
  }
  emitVia(x, z, arrival, out)
  area.claimRect(x - 1, z - 1, x + 1, z + 1)
  return []
}

/** Octagonal via ring drawn around a trace endpoint. */
export function emitVia(
  cx: number,
  cz: number,
  arrival: number,
  out: RevealSegment[],
): void {
  const ring: Vec3[] = []
  for (let i = 0; i < 8; i++) {
    const angle = Math.PI / 8 + (i * Math.PI) / 4
    ring.push([cx + Math.cos(angle) * VIA_RADIUS, 0, cz + Math.sin(angle) * VIA_RADIUS])
  }
  emitLoop(ring, arrival, out)
}

/**
 * Wireframe IC: pin stub into a rectangular body (base outline, corner posts
 * rising together, top outline), with up to two exit pins on the far edge.
 * Axis-aligned approaches only.
 */
function tryChip(
  x: number,
  z: number,
  dir: number,
  arrival: number,
  rng: Rng,
  area: AreaGrid,
  out: RevealSegment[],
): Exit[] | null {
  const d = DIRS[dir]
  const p = DIRS[turn(dir, 2)]
  const halfWidth = rangeInt(rng, 2, 3)
  const depth = rangeInt(rng, 4, 7)
  const pinOffset = rangeInt(rng, -(halfWidth - 1), halfWidth - 1)
  const at = (along: number, perp: number, y = 0): Vec3 => [
    x + d[0] * along + p[0] * perp,
    y,
    z + d[1] * along + p[1] * perp,
  ]

  const base = [
    at(1, pinOffset - halfWidth),
    at(1, pinOffset + halfWidth),
    at(1 + depth, pinOffset + halfWidth),
    at(1 + depth, pinOffset - halfWidth),
  ]
  if (!claimFootprint(area, [at(0, 0), ...base], 1)) return null

  const pin = at(1, 0)
  let t = emitPolyline([at(0, 0), pin], arrival, out)
  t = emitLoop([pin, base[1], base[2], base[3], base[0]], t, out)

  let postsEnd = t
  for (const corner of base) {
    const top: Vec3 = [corner[0], CHIP_HEIGHT, corner[2]]
    postsEnd = Math.max(postsEnd, emitPolyline([corner, top], t, out))
  }
  const top = base.map((c): Vec3 => [c[0], CHIP_HEIGHT, c[2]])
  const outlineEnd = emitLoop(top, postsEnd, out)

  const exits: Exit[] = []
  const slots = shuffledPerpSlots(rng, pinOffset, halfWidth)
  for (const perp of slots.slice(0, rangeInt(rng, 0, 2))) {
    const edge = at(1 + depth, perp)
    exits.push({ x: edge[0], z: edge[2], dir, arrival: outlineEnd })
  }
  return exits
}

/**
 * Two-pad passive (resistor/capacitor): pad, small wireframe box, far pad
 * ending in a via. Works for diagonal approaches too; the total length is
 * chosen so the far end lands back on the routing lattice.
 */
function tryPassive(
  x: number,
  z: number,
  dir: number,
  arrival: number,
  rng: Rng,
  area: AreaGrid,
  out: RevealSegment[],
): Exit[] | null {
  const [dx, dz] = DIRS[dir]
  const scale = 1 / Math.hypot(dx, dz)
  const ux = dx * scale
  const uz = dz * scale
  const px = -uz
  const pz = ux

  const total = dir % 2 === 0 ? 4 : 3 * Math.SQRT2
  const pad = total * 0.1875
  const halfWidth = 0.8
  const at = (along: number, perp: number, y = 0): Vec3 => [
    x + ux * along + px * perp,
    y,
    z + uz * along + pz * perp,
  ]

  const base = [
    at(pad, -halfWidth),
    at(pad, halfWidth),
    at(total - pad, halfWidth),
    at(total - pad, -halfWidth),
  ]
  const end = at(total, 0)
  if (!claimFootprint(area, [at(0, 0), end, ...base], 1.2)) return null

  const nearPad = at(pad, 0)
  const farPad = at(total - pad, 0)
  let t = emitPolyline([at(0, 0), nearPad], arrival, out)
  t = emitLoop([nearPad, base[1], base[2], farPad, base[3], base[0]], t, out)

  let postsEnd = t
  for (const corner of base) {
    const top: Vec3 = [corner[0], PASSIVE_HEIGHT, corner[2]]
    postsEnd = Math.max(postsEnd, emitPolyline([corner, top], t, out))
  }
  const top = base.map((c): Vec3 => [c[0], PASSIVE_HEIGHT, c[2]])
  t = emitLoop(top, postsEnd, out)

  t = emitPolyline([farPad, end], t, out)
  emitVia(end[0], end[2], t, out)

  if (rng() < 0.5) return [{ x: end[0], z: end[2], dir, arrival: t }]
  return []
}

/** Checks a footprint's bounding rect (with margin) and claims it if free. */
function claimFootprint(area: AreaGrid, points: readonly Vec3[], margin: number): boolean {
  const xs = points.map((c) => c[0])
  const zs = points.map((c) => c[2])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minZ = Math.min(...zs)
  const maxZ = Math.max(...zs)
  if (!area.isRectFree(minX - margin, minZ - margin, maxX + margin, maxZ + margin)) {
    return false
  }
  area.claimRect(minX, minZ, maxX, maxZ)
  return true
}

function shuffledPerpSlots(rng: Rng, pinOffset: number, halfWidth: number): number[] {
  const slots: number[] = []
  for (let q = pinOffset - halfWidth + 1; q <= pinOffset + halfWidth - 1; q++) {
    slots.push(q)
  }
  for (let i = slots.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[slots[i], slots[j]] = [slots[j], slots[i]]
  }
  return slots
}
