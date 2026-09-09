import { Suspense, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { rebindMaterials } from "./materials";

// Lives inside secret-base/ and is bundled as a Vite asset.
export const WORLD_GLB_URL = new URL(
  "../../models/world.glb",
  import.meta.url,
).href;

/**
 * Loads the Blender-editable export of the world (islands + bridges,
 * everything except the cave background) and re-binds materials by name to
 * the live instances in materials.ts, so emissive/bloom stay code-driven.
 * Unknown materials (e.g. baked sign/screen canvas textures) are kept as-is.
 */
function Model() {
  const { scene } = useGLTF(WORLD_GLB_URL);

  useMemo(() => {
    rebindMaterials(scene);
  }, [scene]);

  return <primitive object={scene} />;
}

export function BakedWorld() {
  return (
    <Suspense fallback={null}>
      <Model />
    </Suspense>
  );
}

useGLTF.preload(WORLD_GLB_URL);
