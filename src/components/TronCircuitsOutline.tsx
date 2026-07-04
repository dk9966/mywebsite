import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import { buildOutlineModel, transformedOutlinePaths } from "../lib/circuit3DMeshes";
import { footprintsToMeshes, resolveMeshes } from "../lib/circuitMeshes";
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

function isEditableLine(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
}

type TronCircuitsOutlineProps = {
  onLayout?: (layout: CircuitsTracedLayout) => void;
  /** Screen-pixel stroke width for free-camera mode; omit for cinematic playback. */
  screenLineWidth?: number;
};

// The editor-authored board, animated. Component outlines follow the editor's
// mesh edits (moved/scaled boxes drag their real GLB outlines along, deleted
// ones drop out); metal traces come from circuits-traced.json plus topology
// edits, played back with the flood-scheduled left-to-right scan.
export default function TronCircuitsOutline({
  onLayout,
  screenLineWidth,
}: TronCircuitsOutlineProps) {
  const { scene } = useGLTF(OUTLINE_GLB_URL);

  const timing = useCircuitTuning((s) => s.timing);
  const transform = useCircuitTuning((s) => s.transform);
  const topViewCamera = useCircuitTuning((s) => s.topViewCamera);
  const overrides = useCircuitTuning((s) => s.overrides);
  const topology = useCircuitTuning((s) => s.topology);
  const meshEdits = useCircuitTuning((s) => s.meshEdits);
  const snapMergeEps = useCircuitTuning((s) => s.snapMergeEps);

  // Raw, untuned source geometry: part outlines (from GLB) + metal traces.
  // Stable ids let the tuner address each line; ordering is deterministic.
  const rawPaths = useMemo<GridPath[]>(() => buildRawCircuitPaths(scene), [
    scene,
  ]);
  const model = useMemo(() => buildOutlineModel(rawPaths), [rawPaths]);
  const baselineMeshes = useMemo(
    () => footprintsToMeshes(model.footprints),
    [model],
  );

  const layout = useMemo(() => {
    // Same composition as the editor: outlines transformed by mesh edits,
    // plus the editable traces. What you arranged there is what plays here.
    const resolvedMeshes = resolveMeshes(baselineMeshes, meshEdits);
    const outlinePaths = transformedOutlinePaths(model, resolvedMeshes);
    const editablePaths = rawPaths.filter((p) => isEditableLine(p.id));
    const combined = [...outlinePaths, ...editablePaths];

    const tuning = {
      timing,
      transform,
      topViewCamera,
      overrides,
      topology,
      meshEdits,
      snapMergeEps,
    };
    return layoutFromPaths(applyTuning(combined, tuning));
  }, [
    rawPaths,
    model,
    baselineMeshes,
    meshEdits,
    timing,
    transform,
    topViewCamera,
    overrides,
    topology,
    snapMergeEps,
  ]);

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
      screenLineWidth={screenLineWidth}
    />
  );
}
