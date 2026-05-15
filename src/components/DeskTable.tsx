import { useMemo } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";

const TABLE_GLB_URL = "/models/table.glb";

useGLTF.preload(TABLE_GLB_URL);

// Polished gunmetal body shared across every desk part. Metalness is high
// so the scene's IBL + practicals show up as crisp highlights along the
// curved edges; roughness keeps reflections short of mirror-clear. Needs an
// <Environment> in the scene — without one a fully metallic surface falls
// back to near-black.
const TABLE_MATERIAL = new THREE.MeshStandardMaterial({
  color: new THREE.Color("#161e27"),
  metalness: 0.88,
  roughness: 0.3,
});

// The GLB packs the structural desk meshes (Top, Skirt, Leg_*, FootBrace)
// alongside `TronLine_*` edge-only meshes that were authored for the
// animated polyline effect. The desk setup no longer renders that effect,
// so we just hide the edge meshes and shade the rest with one material.
export default function DeskTable() {
  const { scene } = useGLTF(TABLE_GLB_URL);

  const prepared = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((obj) => {
      if (obj.name.startsWith("TronLine_")) {
        obj.visible = false;
        return;
      }
      if ((obj as THREE.Mesh).isMesh) {
        const mesh = obj as THREE.Mesh;
        mesh.material = TABLE_MATERIAL;
        mesh.castShadow = false;
        mesh.receiveShadow = false;
      }
    });
    return clone;
  }, [scene]);

  return <primitive object={prepared} />;
}
