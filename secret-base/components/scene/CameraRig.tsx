import { useEffect, useLayoutEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type * as THREE from "three";
import gsap from "gsap";
import { useViewStore } from "./viewStore";

type ControlsLike = {
  target: THREE.Vector3;
  enabled: boolean;
  minDistance: number;
  maxPolarAngle: number;
  update: () => void;
};

// Named camera framings. `projects` faces the holo panel head-on
// (panel sits at [0, 3.15, 0.25] with a 0.14 rad yaw).
const VIEWS = {
  overview: {
    position: [20.5, 17.5, 37] as const,
    target: [0.6, -0.2, 0.2] as const,
    minDistance: 14,
    maxPolarAngle: 1.35,
  },
  projects: {
    position: [1.25, 3.75, 7.4] as const,
    target: [0, 3.05, 0.3] as const,
    minDistance: 3.5,
    maxPolarAngle: 1.52,
  },
  // faces the About island's holo rig (island at [-10.85, 1.5, -4.65])
  about: {
    position: [-3.3, 4.7, -1.4] as const,
    target: [-10.85, 3.0, -4.65] as const,
    minDistance: 3.5,
    maxPolarAngle: 1.52,
  },
};

/**
 * Cinematic front three-quarter camera with click-drag orbit.
 * Clicking the Projects island flies to the holo panel; Escape (or
 * clicking the island again) flies back.
 */
export function CameraRig() {
  const camera = useThree((s) => s.camera);
  const controlsRef = useRef<ControlsLike | null>(null);
  const view = useViewStore((s) => s.view);
  const setView = useViewStore((s) => s.setView);

  useLayoutEffect(() => {
    const [x, y, z] = VIEWS.overview.position;
    camera.position.set(x, y, z);
  }, [camera]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setView("overview");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setView]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const v = VIEWS[view];

    // relax constraints for the flight, tighten to the view's own afterwards
    controls.enabled = false;
    controls.minDistance = Math.min(controls.minDistance, v.minDistance);
    controls.maxPolarAngle = Math.max(controls.maxPolarAngle, v.maxPolarAngle);

    let pending = 2;
    const finish = () => {
      pending -= 1;
      if (pending === 0) {
        controls.minDistance = v.minDistance;
        controls.maxPolarAngle = v.maxPolarAngle;
        controls.enabled = true;
      }
    };
    gsap.to(camera.position, {
      x: v.position[0],
      y: v.position[1],
      z: v.position[2],
      duration: 1.5,
      ease: "power2.inOut",
      onComplete: finish,
    });
    gsap.to(controls.target, {
      x: v.target[0],
      y: v.target[1],
      z: v.target[2],
      duration: 1.5,
      ease: "power2.inOut",
      onUpdate: () => controls.update(),
      onComplete: finish,
    });
  }, [view, camera]);

  return (
    <OrbitControls
      ref={controlsRef as never}
      target={[0.6, -0.2, 0.2]}
      enableDamping
      dampingFactor={0.08}
      enablePan={false}
      minDistance={14}
      maxDistance={55}
      minPolarAngle={0.25}
      maxPolarAngle={1.35}
      rotateSpeed={0.6}
      zoomSpeed={0.7}
    />
  );
}
