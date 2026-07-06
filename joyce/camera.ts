/**
 * Four-phase camera choreography:
 *  1. top-down over the origin while the dot becomes a line,
 *  2. top-down pan in +X tracking the reveal front (climbing a little as the
 *     web widens),
 *  3. a 90-degree tilt so the lit board settles at the bottom of the frame,
 *  4. a vertical rise from the basement to the ground floor, leaving black.
 */

import * as THREE from 'three'

export interface Timings {
  tiltStart: number
  tiltEnd: number
  riseStart: number
  riseEnd: number
}

const FOV = 50
const TOP_HEIGHT_NEAR = 26
const TOP_HEIGHT_FAR = 54
const FLOOR_EYE = 8
const FLOOR_DISTANCE = 42
/** How far below the eye the floor gaze aims; pitches the board into the lower frame. */
const FLOOR_GAZE_DROP = 8
const RISE_HEIGHT = 80

interface Pose {
  position: THREE.Vector3
  target: THREE.Vector3
  up: THREE.Vector3
}

export class CameraRig {
  readonly camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 600)
  private smoothedX: number | undefined

  constructor(
    private readonly timings: Timings,
    private readonly endX: number,
  ) {}

  update(t: number, dt: number, frontX: number): void {
    const clamped = THREE.MathUtils.clamp(frontX, 0, this.endX)
    // Snap on the first frame so ?t= seeks start framed on the front.
    this.smoothedX ??= clamped
    this.smoothedX += (clamped - this.smoothedX) * (1 - Math.exp(-dt * 2.5))
    const x = this.smoothedX

    const { tiltStart, tiltEnd, riseStart, riseEnd } = this.timings
    let pose: Pose
    if (t < tiltStart) {
      pose = this.topDownPose(x)
    } else if (t < tiltEnd) {
      const s = smootherstep((t - tiltStart) / (tiltEnd - tiltStart))
      pose = mixPose(this.topDownPose(x), this.floorPose(x), s)
    } else {
      pose = this.floorPose(x)
      const rise =
        RISE_HEIGHT *
        easeInOutCubic(THREE.MathUtils.clamp((t - riseStart) / (riseEnd - riseStart), 0, 1))
      pose.position.y += rise
      pose.target.y += rise
    }

    this.camera.position.copy(pose.position)
    this.camera.up.copy(pose.up).normalize()
    this.camera.lookAt(pose.target)
  }

  /** Straight down; screen shows the XZ plane with +X to the right. */
  private topDownPose(x: number): Pose {
    const height = THREE.MathUtils.lerp(TOP_HEIGHT_NEAR, TOP_HEIGHT_FAR, x / this.endX)
    return {
      position: new THREE.Vector3(x, height, 0),
      target: new THREE.Vector3(x, 0, 0),
      up: new THREE.Vector3(0, 0, -1),
    }
  }

  /** Near-horizontal gaze along -Z; the board glows along the bottom of the frame. */
  private floorPose(x: number): Pose {
    return {
      position: new THREE.Vector3(x, FLOOR_EYE, FLOOR_DISTANCE),
      target: new THREE.Vector3(x, FLOOR_EYE - FLOOR_GAZE_DROP, 0),
      up: new THREE.Vector3(0, 1, 0),
    }
  }
}

function mixPose(a: Pose, b: Pose, s: number): Pose {
  return {
    position: a.position.lerp(b.position, s),
    target: a.target.lerp(b.target, s),
    up: a.up.lerp(b.up, s),
  }
}

function smootherstep(x: number): number {
  const c = THREE.MathUtils.clamp(x, 0, 1)
  return c * c * c * (c * (c * 6 - 15) + 10)
}

function easeInOutCubic(x: number): number {
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2
}
