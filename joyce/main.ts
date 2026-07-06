/**
 * Circuit basement scene. The whole board is generated up front; every line
 * piece is packed into a single fat-line geometry sorted by network distance
 * from the origin, so raising `instanceCount` each frame plays the reveal
 * back as a wavefront spreading through the web. A master clock drives both
 * the reveal and the camera so they stay in sync.
 *
 * Append ?t=SECONDS to the URL to start partway through the timeline.
 */

import * as THREE from 'three'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { generateBoard } from './board'
import { CameraRig, type Timings } from './camera'

const NEON_BLUE = 0x35d6ff

// Neon glow built from layered copies of the same line geometry: a crisp
// core plus two wide translucent halos. Normal blending keeps overlapping
// segment joints from flaring into bright beads.
const GLOW_LAYERS = [
  { linewidth: 2, opacity: 1 },
  { linewidth: 7, opacity: 0.2 },
  { linewidth: 18, opacity: 0.07 },
]

// Timeline: reveal speed in board units per second, with a short velocity
// ramp so the first dot eases into motion.
const REVEAL_SPEED = 16
const REVEAL_ACCEL = 1.6
const REVEAL_START = 1.6
const DOT_START = 0.4
const DOT_DURATION = 0.8

const board = generateBoard()

const revealEnd = REVEAL_START + board.maxArrival / REVEAL_SPEED + REVEAL_ACCEL / 2
const timings: Timings = {
  tiltStart: revealEnd + 0.8,
  tiltEnd: revealEnd + 4.8,
  riseStart: revealEnd + 5.6,
  riseEnd: revealEnd + 11.6,
}

const scene = new THREE.Scene()
scene.background = new THREE.Color(0x000000)

const lineGeometry = new LineSegmentsGeometry()
lineGeometry.setPositions(board.positions)
lineGeometry.instanceCount = 0
const lineMaterials = GLOW_LAYERS.map(
  (layer) =>
    new LineMaterial({
      color: NEON_BLUE,
      linewidth: layer.linewidth,
      transparent: layer.opacity < 1,
      opacity: layer.opacity,
      depthWrite: layer.opacity === 1,
    }),
)
for (const material of lineMaterials) {
  const lines = new LineSegments2(lineGeometry, material)
  lines.frustumCulled = false
  scene.add(lines)
}

// The origin dot the whole board grows out of, with its own soft halo.
const dot = new THREE.Group()
for (const [radius, opacity] of [
  [0.55, 1],
  [1.1, 0.2],
  [1.9, 0.07],
] as const) {
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 32),
    new THREE.MeshBasicMaterial({
      color: NEON_BLUE,
      transparent: opacity < 1,
      opacity,
      depthWrite: opacity === 1,
    }),
  )
  disc.rotation.x = -Math.PI / 2
  dot.add(disc)
}
dot.scale.setScalar(0)
scene.add(dot)

// Stop the camera short of the board edge so the last frame stays filled.
const rig = new CameraRig(timings, board.spineEndX - 26)

const renderer = new THREE.WebGLRenderer({ antialias: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
document.body.appendChild(renderer.domElement)

function resize(): void {
  const w = window.innerWidth
  const h = window.innerHeight
  rig.camera.aspect = w / h
  rig.camera.updateProjectionMatrix()
  renderer.setSize(w, h)
  for (const material of lineMaterials) material.resolution.set(w, h)
}
window.addEventListener('resize', resize)
resize()

/** Network distance revealed at time t: short quadratic ramp, then linear. */
function revealDistance(t: number): number {
  const u = t - REVEAL_START
  if (u <= 0) return 0
  const ramped = u < REVEAL_ACCEL ? (u * u) / (2 * REVEAL_ACCEL) : u - REVEAL_ACCEL / 2
  return Math.min(ramped * REVEAL_SPEED, board.maxArrival)
}

/** Number of segments with arrival <= d (arrivals are sorted). */
function revealedCount(d: number): number {
  let lo = 0
  let hi = board.segmentCount
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (board.arrivals[mid] <= d) lo = mid + 1
    else hi = mid
  }
  return lo
}

// Dev helpers: ?t=SECONDS seeks into the timeline, ?freeze holds that frame.
const params = new URLSearchParams(location.search)
let t = Number(params.get('t') ?? '0')
const frozen = params.has('freeze')
let lastMs: number | undefined

function renderFrame(dt: number): void {
  if (!frozen) t += dt

  dot.scale.setScalar(smoothstep01((t - DOT_START) / DOT_DURATION))
  const count = revealedCount(revealDistance(t))
  lineGeometry.instanceCount = count
  rig.update(t, dt, count > 0 ? board.frontX[count - 1] : 0)

  renderer.render(scene, rig.camera)
}

// Paint one frame immediately so the canvas is never blank, even if the tab
// is occluded and requestAnimationFrame is throttled.
renderFrame(0)

renderer.setAnimationLoop((nowMs: number) => {
  const dt = Math.min((nowMs - (lastMs ?? nowMs)) / 1000, 0.05)
  lastMs = nowMs
  renderFrame(dt)
})

function smoothstep01(x: number): number {
  const c = THREE.MathUtils.clamp(x, 0, 1)
  return c * c * (3 - 2 * c)
}
