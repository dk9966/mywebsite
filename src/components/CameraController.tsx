import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useClock } from "../stores/clock";

const FLAT_DURATION = 4;
const TILT_DURATION = 10;

export default function CameraController() {
  const { camera } = useThree();

  useFrame(() => {
    const t = useClock.getState().time;

    if (t < FLAT_DURATION) {
      const p = easeInOut(Math.min(t / FLAT_DURATION, 1));
      const z = THREE.MathUtils.lerp(55, 45, p);
      camera.position.set(0, 0, z);
      camera.lookAt(0, 0, 0);
    } else {
      const dt = t - FLAT_DURATION;
      const p = Math.min(dt / TILT_DURATION, 1);
      const e = easeInOut(p);

      const z = THREE.MathUtils.lerp(45, 18, e);
      const y = THREE.MathUtils.lerp(0, -22, e);
      const lookY = THREE.MathUtils.lerp(0, 6, e);

      camera.position.set(0, y, z);
      camera.lookAt(0, lookY, 0);
    }
  });

  return null;
}

function easeInOut(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
