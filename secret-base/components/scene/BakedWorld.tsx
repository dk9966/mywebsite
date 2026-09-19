import { Suspense, useMemo } from "react";
import { useLiveBlenderModel } from "./useLiveBlenderModel";
import { rebindMaterials } from "./materials";

// Lives inside secret-base/ and is bundled as a Vite asset.
const WORLD_GLB_URL = new URL(
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
  const scene = useLiveBlenderModel(WORLD_GLB_URL, 'world');

  useMemo(() => {
    if (scene) rebindMaterials(scene);
  }, [scene]);

  return scene ? <primitive object={scene} /> : null;
}

export function BakedWorld() {
  return (
    <Suspense fallback={null}>
      <Model />
    </Suspense>
  );
}
