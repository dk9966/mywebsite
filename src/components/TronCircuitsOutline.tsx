import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import { buildOutlineModel, transformedOutlinePaths } from "../lib/circuit3DMeshes";
import { footprintsToMeshes, resolveMeshes } from "../lib/circuitMeshes";
import type { GridPath } from "../lib/gridBuilder";
import {
  useVariantCatalog,
  variantOutlinePaths,
} from "../lib/qfpVariantCatalog";
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
  const catalog = useVariantCatalog();

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
    // Match the editor's composition: mesh outlines are never run through
    // topology (that path is for two-point circuit segments and would shred
    // multi-point variant polylines). Traces get full applyTuning.
    const resolvedMeshes = resolveMeshes(baselineMeshes, meshEdits);
    // One shared color for the whole board (Controls → Line), not per-mesh tints.
    const baselineOutlines = transformedOutlinePaths(
      model,
      resolvedMeshes,
      "global",
    );
    const variantOutlines = catalog
      ? variantOutlinePaths(resolvedMeshes, catalog, model.yMin, "global")
      : [];
    const outlinePaths = [...baselineOutlines, ...variantOutlines];
    const editablePaths = rawPaths.filter((p) => isEditableLine(p.id));

    const tuning = {
      timing,
      transform,
      topViewCamera,
      overrides,
      topology,
      meshEdits,
      snapMergeEps,
    };
    // Outlines: board transform + scan schedule only (empty topology).
    const tunedOutlines = applyTuning(outlinePaths, {
      ...tuning,
      topology: { geometry: {}, deleted: [], added: [] },
    });
    const tunedTraces = applyTuning(editablePaths, tuning);
    return layoutFromPaths([...tunedOutlines, ...tunedTraces]);
  }, [
    rawPaths,
    model,
    baselineMeshes,
    meshEdits,
    catalog,
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
