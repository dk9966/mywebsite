import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import {
  boardBoundsX,
  scanCameraX,
  scanPanDuration,
  type CircuitsTracedLayout,
  type TopViewCamera,
} from "../lib/tronPathsFromCircuitsTraced";
import { useClock } from "../stores/clock";
import { useCircuitTuning } from "../stores/circuitTuning";

const OVERVIEW_MARGIN = 1.12;

type CameraPose = {
  position: THREE.Vector3;
  target: THREE.Vector3;
  up: THREE.Vector3;
};

type CircuitsOutlineCameraProps = {
  layout: CircuitsTracedLayout;
  cinematicMode: boolean;
  fov: number;
};

function cinematicCameraPose(
  layout: CircuitsTracedLayout,
  time: number,
  topViewCamera: TopViewCamera,
  timingStart: number,
): CameraPose {
  const [, cy, cz] = layout.center;
  const { minX, maxX } = boardBoundsX(layout.paths);
  const spanX = maxX - minX;
  const panDuration = scanPanDuration(spanX);
  const { heightFactor, frontLagSec, offset } = topViewCamera;
  const camX = scanCameraX(
    time - timingStart - frontLagSec,
    minX,
    spanX,
    panDuration,
  );

  const height = layout.span * heightFactor;
  const px = camX + offset[0];
  const py = height + offset[1];
  const pz = cz + offset[2];
  const ty = cy + offset[1];

  return {
    position: new THREE.Vector3(px, py, pz),
    target: new THREE.Vector3(px, ty, pz),
    up: new THREE.Vector3(0, 1, 0),
  };
}

function overviewCameraPose(
  layout: CircuitsTracedLayout,
  fov: number,
): CameraPose {
  const [cx, cy, cz] = layout.center;
  const span = Math.max(layout.span, 1);
  const target = new THREE.Vector3(cx, cy, cz);
  const fovRad = (fov * Math.PI) / 180;
  const distance = ((span * 0.5) / Math.tan(fovRad / 2)) * OVERVIEW_MARGIN;

  return {
    position: new THREE.Vector3(cx, cy + distance, cz),
    target,
    up: new THREE.Vector3(0, 1, 0),
  };
}

function applyCameraPose(
  camera: THREE.Camera,
  controls: OrbitControlsImpl | null,
  pose: CameraPose,
) {
  camera.position.copy(pose.position);
  camera.up.copy(pose.up);
  camera.lookAt(pose.target);
  if (controls) {
    controls.target.copy(pose.target);
    controls.update();
  }
}

export default function CircuitsOutlineCamera({
  layout,
  cinematicMode,
  fov,
}: CircuitsOutlineCameraProps) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const prevCinematicRef = useRef(cinematicMode);

  useEffect(() => {
    if (prevCinematicRef.current === cinematicMode) return;
    prevCinematicRef.current = cinematicMode;

    if (cinematicMode) {
      const { time } = useClock.getState();
      const { timing, topViewCamera } = useCircuitTuning.getState();
      applyCameraPose(
        camera,
        controls,
        cinematicCameraPose(layout, time, topViewCamera, timing.startTime),
      );
      return;
    }

    applyCameraPose(camera, controls, overviewCameraPose(layout, fov));
  }, [cinematicMode, layout, fov, camera, controls]);

  useFrame(() => {
    const blockCamera =
      useCircuitTuning.getState().isDraggingVertex ||
      useCircuitTuning.getState().editTool === "addLine";

    if (!cinematicMode) {
      if (controls) {
        controls.enabled = !blockCamera;
        controls.enableRotate = !blockCamera;
        controls.enablePan = !blockCamera;
        controls.enableZoom = true;
      }
      return;
    }

    if (controls) {
      controls.enabled = false;
      controls.enableRotate = false;
      controls.enablePan = false;
    }

    const { time } = useClock.getState();
    const { timing, topViewCamera } = useCircuitTuning.getState();
    applyCameraPose(
      camera,
      controls,
      cinematicCameraPose(layout, time, topViewCamera, timing.startTime),
    );
  });

  return null;
}
