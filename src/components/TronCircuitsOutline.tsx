import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import type { GridPath } from "../lib/gridBuilder";
import {
  applyTuning,
  boardBoundsX,
  buildRawCircuitPaths,
  layoutFromPaths,
  scanPanDuration,
  type CircuitsTracedLayout,
} from "../lib/tronPathsFromCircuitsTraced";
import { useCircuitTuning } from "../stores/circuitTuning";
import TronGrid from "./TronGrid";

const OUTLINE_GLB_URL = "/models/circuits-traced-outline.glb";

useGLTF.preload(OUTLINE_GLB_URL);

type TronCircuitsOutlineProps = {
  onLayout?: (layout: CircuitsTracedLayout) => void;
};

// Component obstacle outlines from circuits-traced-outline.glb (mesh crease edges
// from component_reference.glb placements). Metal traces from circuits-traced.json,
// with endpoints snapped to the part outlines they approach.
export default function TronCircuitsOutline({
  onLayout,
}: TronCircuitsOutlineProps) {
  const { scene } = useGLTF(OUTLINE_GLB_URL);

  const timing = useCircuitTuning((s) => s.timing);
  const transform = useCircuitTuning((s) => s.transform);
  const overrides = useCircuitTuning((s) => s.overrides);
  const topology = useCircuitTuning((s) => s.topology);

  // Raw, untuned source geometry: part outlines (from GLB) + metal traces.
  // Stable ids let the tuner address each line; ordering is deterministic.
  const rawPaths = useMemo<GridPath[]>(() => buildRawCircuitPaths(scene), [
    scene,
  ]);

  const layout = useMemo(
    () =>
      layoutFromPaths(
        applyTuning(rawPaths, { timing, transform, overrides, topology }),
      ),
    [rawPaths, timing, transform, overrides, topology],
  );

  const playbackDuration = useMemo(() => {
    const { minX, maxX } = boardBoundsX(layout.paths);
    return scanPanDuration(maxX - minX) + 0.5;
  }, [layout.paths]);

  useEffect(() => {
    onLayout?.(layout);
  }, [layout, onLayout]);

  return (
    <TronGrid
      paths={layout.paths}
      showBackgroundGrid={false}
      playbackDuration={playbackDuration}
    />
  );
}
