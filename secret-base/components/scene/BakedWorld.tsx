import { Suspense, useMemo } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";
import { MATERIALS } from "./materials";

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
    const swap = (m: THREE.Material): THREE.Material => {
      const shared = MATERIALS[m.name];
      if (shared) return shared;
      // unlit texture panels (signs/screens) should ignore tone mapping,
      // matching how they were authored
      const basic = m as THREE.MeshBasicMaterial;
      if (basic.isMeshBasicMaterial && basic.map) basic.toneMapped = false;
      return m;
    };
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.material = Array.isArray(mesh.material)
        ? mesh.material.map(swap)
        : swap(mesh.material);
    });
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
