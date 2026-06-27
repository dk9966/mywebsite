import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import type { ArcballControls as ArcballControlsImpl } from "three-stdlib";
import {
  boardBoundsX,
  scanCameraX,
  scanPanDuration,
  type CircuitsTracedLayout,
} from "../lib/tronPathsFromCircuitsTraced";
import { useClock } from "../stores/clock";
import { useCircuitTuning } from "../stores/circuitTuning";

type CircuitsOutlineCameraProps = {
  layout: CircuitsTracedLayout;
  topView: boolean;
};

export default function CircuitsOutlineCamera({
  layout,
  topView,
}: CircuitsOutlineCameraProps) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as ArcballControlsImpl | null;

  const [, cy, cz] = layout.center;
  const { span, paths } = layout;

  const { minX, maxX } = useMemo(() => boardBoundsX(paths), [paths]);
  const spanX = maxX - minX;
  const panDuration = useMemo(() => scanPanDuration(spanX), [spanX]);

  useFrame(() => {
    const blockCamera =
      useCircuitTuning.getState().isDraggingVertex ||
      useCircuitTuning.getState().editTool === "addLine";

    if (!topView) {
      if (controls) controls.enabled = !blockCamera;
      return;
    }

    if (controls) controls.enabled = false;

    const { time } = useClock.getState();
    const { timing, topViewCamera } = useCircuitTuning.getState();
    const { heightFactor, frontLagSec, offset } = topViewCamera;
    const camX = scanCameraX(
      time - timing.startTime - frontLagSec,
      minX,
      spanX,
      panDuration,
    );

    const height = span * heightFactor;
    const px = camX + offset[0];
    const py = height + offset[1];
    const pz = cz + offset[2];

    camera.position.set(px, py, pz);
    camera.up.set(0, 1, 0);
    camera.lookAt(px, cy + offset[1], pz);

    if (controls) controls.target.set(px, cy + offset[1], pz);
  });

  return null;
}
