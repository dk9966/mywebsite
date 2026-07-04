import * as THREE from "three";
import type { GridPath, Vec3 } from "./gridBuilder";

const _ray = new THREE.Raycaster();
const _ndc = new THREE.Vector2();
const _hit = new THREE.Vector3();
const _plane = new THREE.Plane();

export type BoardPickView = "top" | "side";

export function boardY(paths: GridPath[]): number {
  for (const p of paths) {
    if (p.waypoints.length > 0) return p.waypoints[0][1];
  }
  return 0.022;
}

export function boardCenterZ(paths: GridPath[]): number {
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (const p of paths) {
    for (const wp of p.waypoints) {
      minZ = Math.min(minZ, wp[2]);
      maxZ = Math.max(maxZ, wp[2]);
    }
  }
  return Number.isFinite(minZ) ? (minZ + maxZ) / 2 : 0;
}

export function pickBoardPoint(
  clientX: number,
  clientY: number,
  camera: THREE.Camera,
  domElement: HTMLCanvasElement,
  y: number,
  view: BoardPickView = "top",
  centerZ = 0,
): Vec3 | null {
  const rect = domElement.getBoundingClientRect();
  if (
    clientX < rect.left ||
    clientX > rect.right ||
    clientY < rect.top ||
    clientY > rect.bottom
  ) {
    return null;
  }

  _ndc.set(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  );
  _ray.setFromCamera(_ndc, camera);
  if (view === "side") {
    // Draw on the screen-facing plane (constant Z): X is horizontal, Y is
    // vertical. Keep the ray's Y so the line rises off the board — that Y
    // extent reads as "into/out of the page" back in top view.
    _plane.set(new THREE.Vector3(0, 0, 1), -centerZ);
    return _ray.ray.intersectPlane(_plane, _hit)
      ? ([_hit.x, _hit.y, centerZ] as Vec3)
      : null;
  }
  _plane.set(new THREE.Vector3(0, 1, 0), -y);
  return _ray.ray.intersectPlane(_plane, _hit)
    ? ([_hit.x, y, _hit.z] as Vec3)
    : null;
}

export type BoardPickXZ = (clientX: number, clientY: number) => {
  x: number;
  z: number;
} | null;

export function boardPickXZ(
  clientX: number,
  clientY: number,
  camera: THREE.Camera,
  domElement: HTMLCanvasElement,
  y: number,
  view: BoardPickView = "top",
  centerZ = 0,
): { x: number; z: number } | null {
  const pt = pickBoardPoint(
    clientX,
    clientY,
    camera,
    domElement,
    y,
    view,
    centerZ,
  );
  return pt ? { x: pt[0], z: pt[2] } : null;
}
