import { useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { tronLinesFromGLB } from "../lib/tronLinesFromGLB";
import { layoutFromPaths } from "../lib/tronPathsFromCircuitsTraced";
import TronGrid from "./TronGrid";

const OUTLINE_GLB_URL = "/models/component-reference-outline.glb";

useGLTF.preload(OUTLINE_GLB_URL);

type ComponentReferenceOutlineProps = {
  onLayout?: (layout: ReturnType<typeof layoutFromPaths>) => void;
};

// Component catalog outlines from component_reference.glb (crease edges, pins omitted).
export default function ComponentReferenceOutline({ onLayout }: ComponentReferenceOutlineProps) {
  const { scene } = useGLTF(OUTLINE_GLB_URL);

  const layout = useMemo(() => {
    const paths = tronLinesFromGLB(scene, { tag: "part" });
    return layoutFromPaths(paths);
  }, [scene]);

  useEffect(() => {
    onLayout?.(layout);
  }, [layout, onLayout]);

  return (
    <TronGrid
      paths={layout.paths}
      showBackgroundGrid={false}
      animated={false}
    />
  );
}
