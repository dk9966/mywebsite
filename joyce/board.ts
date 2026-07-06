/**
 * Procedural PCB layout. Traces walk a unit lattice restricted to the eight
 * routing directions, so every bend is a 45-degree step. An occupancy grid
 * (nodes plus edge midpoints) keeps lines from overlapping or crossing, and
 * every trace terminates in a component, a via, or a T-junction with another
 * trace, so nothing dangles.
 *
 * Each visible piece carries an "arrival": its network distance from the
 * origin. Revealing pieces in arrival order plays the whole board back as a
 * wavefront spreading from the first dot.
 */

import { type Exit, placeTerminal } from './components'
import {
  type AreaGrid,
  DIRS,
  type RevealSegment,
  type Rng,
  type Vec3,
  emitPolyline,
  mulberry32,
  rangeInt,
  turn,
} from './core'

export interface Board {
  /** xyz pairs per segment, sorted by arrival. */
  positions: Float32Array
  /** Ascending arrival per segment. */
  arrivals: Float32Array
  /** frontX[i]: the largest x lit once segments 0..i are revealed. */
  frontX: Float32Array
  segmentCount: number
  maxArrival: number
  spineEndX: number
  bounds: typeof BOUNDS
}

const BOUNDS = { minX: 0, maxX: 220, minZ: -20, maxZ: 20 }
const MAX_PIECES = 26000
const SPINE_SOFT_Z = 7

/** Branch spawn probability per trace vertex; ramps up with x so the web gets denser to the right. */
function spawnProbability(x: number): number {
  if (x < 18) return 0
  return Math.min(0.12, ((x - 18) / 130) * 0.12)
}

interface WalkParams {
  maxSteps: number
  softZ: number
  forwardBias: number
  /** Chance per step of wanting a 45-degree wander turn. */
  turnChance: number
  /** No voluntary turns before this x (keeps the opening dead straight). */
  straightUntilX?: number
  /** Restricts usable directions (the spine never runs backwards). */
  allowed?: ReadonlySet<number>
}

interface WalkResult {
  points: Array<readonly [number, number]>
  /** Direction used to arrive at points[i + 1]. */
  dirs: number[]
  joined: boolean
  endDir: number
}

type TraceRequest = Exit

class Grid implements AreaGrid {
  private readonly nodes = new Set<string>()
  private readonly mids = new Set<string>()

  addNode(x: number, z: number): void {
    this.nodes.add(`${x},${z}`)
  }

  stepFree(x: number, z: number, dir: number): boolean {
    const [dx, dz] = DIRS[dir]
    return (
      !this.nodes.has(`${x + dx},${z + dz}`) &&
      !this.mids.has(`${2 * x + dx},${2 * z + dz}`)
    )
  }

  /** A step onto an occupied node whose edge is still free: a T-junction join. */
  canJoin(x: number, z: number, dir: number): boolean {
    const [dx, dz] = DIRS[dir]
    return (
      this.nodes.has(`${x + dx},${z + dz}`) &&
      !this.mids.has(`${2 * x + dx},${2 * z + dz}`)
    )
  }

  takeStep(x: number, z: number, dir: number): void {
    const [dx, dz] = DIRS[dir]
    this.mids.add(`${2 * x + dx},${2 * z + dz}`)
    this.nodes.add(`${x + dx},${z + dz}`)
  }

  isRectFree(minX: number, minZ: number, maxX: number, maxZ: number): boolean {
    if (
      minX < BOUNDS.minX ||
      maxX > BOUNDS.maxX ||
      minZ < BOUNDS.minZ ||
      maxZ > BOUNDS.maxZ
    ) {
      return false
    }
    for (let x = Math.floor(minX); x <= Math.ceil(maxX); x++) {
      for (let z = Math.floor(minZ); z <= Math.ceil(maxZ); z++) {
        if (this.nodes.has(`${x},${z}`)) return false
      }
    }
    return true
  }

  claimRect(minX: number, minZ: number, maxX: number, maxZ: number): void {
    for (let x = Math.floor(minX); x <= Math.ceil(maxX); x++) {
      for (let z = Math.floor(minZ); z <= Math.ceil(maxZ); z++) {
        this.nodes.add(`${x},${z}`)
      }
    }
  }
}

export function generateBoard(seed = 20260702): Board {
  const rng = mulberry32(seed)
  const grid = new Grid()
  const out: RevealSegment[] = []
  const queue: TraceRequest[] = []

  grid.addNode(0, 0)
  const spine = walk(grid, rng, 0, 0, 0, {
    maxSteps: 400,
    softZ: SPINE_SOFT_Z,
    forwardBias: 1.2,
    turnChance: 0.08,
    straightUntilX: 22,
    allowed: new Set([7, 0, 1]),
  })
  const spineArrivals = vertexArrivals(spine.points, 0)
  emitTrace(spine.points, 0, out)

  const spineEnd = spine.points[spine.points.length - 1]
  const spineEndArrival = spineArrivals[spineArrivals.length - 1]
  queue.push(
    ...placeTerminal(spineEnd[0], spineEnd[1], spine.endDir, spineEndArrival, rng, grid, out),
  )

  // Guaranteed early joins: the 2-3 lines that first meet the lone spine.
  for (const [targetX, side] of [
    [26, 1],
    [36, -1],
    [46, 1],
  ] as const) {
    const i = spine.points.findIndex(([px]) => px >= targetX)
    if (i > 0 && i < spine.points.length - 1) {
      queue.push({
        x: spine.points[i][0],
        z: spine.points[i][1],
        dir: turn(spine.dirs[i - 1], side),
        arrival: spineArrivals[i],
      })
    }
  }
  queueSpawns(spine, spineArrivals, rng, queue)

  while (queue.length > 0 && out.length < MAX_PIECES) {
    const req = queue.shift()!
    const branch = walk(grid, rng, req.x, req.z, req.dir, {
      maxSteps: rangeInt(rng, 20, 60),
      softZ: BOUNDS.maxZ - 4,
      forwardBias: 0.35,
      turnChance: 0.22,
    })
    if (branch.points.length < 4 && !branch.joined) continue

    const arrivals = vertexArrivals(branch.points, req.arrival)
    emitTrace(branch.points, req.arrival, out)
    queueSpawns(branch, arrivals, rng, queue)

    if (!branch.joined) {
      const end = branch.points[branch.points.length - 1]
      const endArrival = arrivals[arrivals.length - 1]
      queue.push(...placeTerminal(end[0], end[1], branch.endDir, endArrival, rng, grid, out))
    }
  }

  out.sort((a, b) => a.arrival - b.arrival)
  const positions = new Float32Array(out.length * 6)
  const arrivals = new Float32Array(out.length)
  const frontX = new Float32Array(out.length)
  let litX = 0
  out.forEach((s, i) => {
    positions.set([...s.a, ...s.b], i * 6)
    arrivals[i] = s.arrival
    litX = Math.max(litX, s.a[0], s.b[0])
    frontX[i] = litX
  })

  return {
    positions,
    arrivals,
    frontX,
    segmentCount: out.length,
    maxArrival: out.length > 0 ? arrivals[out.length - 1] : 0,
    spineEndX: spineEnd[0],
    bounds: BOUNDS,
  }
}

function walk(
  grid: Grid,
  rng: Rng,
  x0: number,
  z0: number,
  dir0: number,
  params: WalkParams,
): WalkResult {
  let x = x0
  let z = z0
  let dir = dir0
  let straightRun = 0
  let joined = false
  const points: Array<readonly [number, number]> = [[x0, z0]]
  const dirs: number[] = []
  // Staggered stop line so trace ends don't pile up in a wall at the edge.
  const stopX = BOUNDS.maxX - 2 - rangeInt(rng, 0, 12)

  for (let step = 0; step < params.maxSteps; step++) {
    if (x >= stopX) break
    const candidates = orderCandidates(dir, x, z, straightRun, rng, params)

    let took = -1
    for (const c of candidates) {
      if (!inBounds(x + DIRS[c][0], z + DIRS[c][1])) continue
      if (grid.stepFree(x, z, c)) {
        took = c
        break
      }
    }

    if (took === -1) {
      // Blocked mid-air: merge into the blocking trace as a T-junction.
      if (step >= 3) {
        for (const c of candidates) {
          if (!inBounds(x + DIRS[c][0], z + DIRS[c][1])) continue
          if (grid.canJoin(x, z, c)) {
            grid.takeStep(x, z, c)
            points.push([x + DIRS[c][0], z + DIRS[c][1]])
            dirs.push(c)
            joined = true
            break
          }
        }
      }
      break
    }

    grid.takeStep(x, z, took)
    straightRun = took === dir ? straightRun + 1 : 0
    dir = took
    x += DIRS[took][0]
    z += DIRS[took][1]
    points.push([x, z])
    dirs.push(took)
  }

  return { points, dirs, joined, endDir: dir }
}

/**
 * Ranks straight-ahead and the two 45-degree turns. Turning needs a couple of
 * straight cells first (clean PCB look), edges of the board steer traces back
 * toward the center, and a forward bias keeps the web drifting +X.
 */
function orderCandidates(
  dir: number,
  x: number,
  z: number,
  straightRun: number,
  rng: Rng,
  params: WalkParams,
): number[] {
  const canTurn = straightRun >= 2 && x >= (params.straightUntilX ?? 0)
  const wanderTurn = canTurn && rng() < params.turnChance ? (rng() < 0.5 ? 1 : -1) : 0
  const options = [dir, turn(dir, 1), turn(dir, -1)].filter(
    (c) => params.allowed === undefined || params.allowed.has(c),
  )

  const scored = options.map((c) => {
    const [dx, dz] = DIRS[c]
    let score = c === dir ? 1 : canTurn ? 0.55 : 0.1
    if (wanderTurn !== 0 && c === turn(dir, wanderTurn)) score += 0.8
    score += params.forwardBias * dx
    if (Math.abs(z) > params.softZ) score += 0.9 * (dz * -Math.sign(z))
    return { c, score: score + rng() * 0.25 }
  })
  scored.sort((a, b) => b.score - a.score)
  return scored.map((s) => s.c)
}

function inBounds(x: number, z: number): boolean {
  return x >= BOUNDS.minX && x <= BOUNDS.maxX && z >= BOUNDS.minZ && z <= BOUNDS.maxZ
}

function vertexArrivals(
  points: ReadonlyArray<readonly [number, number]>,
  startArrival: number,
): number[] {
  const arrivals = [startArrival]
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0]
    const dz = points[i][1] - points[i - 1][1]
    arrivals.push(arrivals[i - 1] + Math.hypot(dx, dz))
  }
  return arrivals
}

function emitTrace(
  points: ReadonlyArray<readonly [number, number]>,
  startArrival: number,
  out: RevealSegment[],
): void {
  const points3 = points.map(([px, pz]): Vec3 => [px, 0, pz])
  emitPolyline(points3, startArrival, out)
}

function queueSpawns(
  trace: WalkResult,
  arrivals: readonly number[],
  rng: Rng,
  queue: TraceRequest[],
): void {
  for (let i = 3; i < trace.points.length - 3; i++) {
    if (rng() >= spawnProbability(trace.points[i][0])) continue
    const side = rng() < 0.5 ? 1 : -1
    queue.push({
      x: trace.points[i][0],
      z: trace.points[i][1],
      dir: turn(trace.dirs[i - 1], side),
      arrival: arrivals[i],
    })
  }
}
