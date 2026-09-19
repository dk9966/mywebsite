import { Suspense, useLayoutEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useLiveBlenderModel } from "./useLiveBlenderModel";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import { rebindMaterials } from "./materials";
import { StationLights } from "./stationLights";
import { StationPanels } from "./StationPanels";
import { StationIslandHeadings } from "./StationIslandHeadings";
import { stationLightColor, useStationLightColor } from "./stationLightColor";
import { batchStationMeshes } from "./batchStationMeshes";

// RectAreaLight needs this once per page; the station lamps use it.
RectAreaLightUniformsLib.init();

const PILLAR_GLB_URL = new URL(
  "../../models/pillar.glb",
  import.meta.url,
).href;

function worldPos(obj: THREE.Object3D): THREE.Vector3 {
  const p = new THREE.Vector3();
  obj.updateWorldMatrix(true, false);
  obj.getWorldPosition(p);
  return p;
}

function floorTop(scene: THREE.Object3D): number {
  const floor = scene.getObjectByName("deck_floor_b");
  if (!floor) return 0;
  const box = new THREE.Box3().setFromObject(floor);
  return box.max.y;
}

function Model() {
  const scene = useLiveBlenderModel(PILLAR_GLB_URL, 'pillar');
  const { hue, tint } = useStationLightColor();
  const invalidate = useThree((state) => state.invalidate);

  const hologramColor = useMemo(() => {
    // Match the exported desk/vein emission, including its HDR intensity.
    const color = new THREE.Color().setRGB(0.96, 1.8, 2.34, THREE.LinearSRGBColorSpace);
    scene?.traverse((object) => {
      const material = (object as THREE.Mesh).material;
      for (const candidate of Array.isArray(material) ? material : [material]) {
        if (candidate instanceof THREE.MeshStandardMaterial && candidate.name === "neonCyan_workshop_cyan") {
          color.copy(candidate.emissive).multiplyScalar(candidate.emissiveIntensity);
        }
      }
    });
    return color;
  }, [scene]);

  useLayoutEffect(() => {
    const originals = new Map<THREE.MeshStandardMaterial, THREE.Color>();
    scene?.traverse((object) => {
      const material = (object as THREE.Mesh).material;
      for (const candidate of Array.isArray(material) ? material : [material]) {
        if (!(candidate instanceof THREE.MeshStandardMaterial) || candidate.name === "lampWarm" || originals.has(candidate)) continue;
        if (candidate.emissive.r + candidate.emissive.g + candidate.emissive.b === 0) continue;
        originals.set(candidate, candidate.emissive.clone());
        candidate.emissive.copy(stationLightColor(candidate.emissive, hue, tint));
      }
    });
    invalidate();
    return () => { originals.forEach((color, material) => material.emissive.copy(color)); };
  }, [scene, hue, tint, invalidate]);

  const recenter = useMemo(() => {
    if (!scene) return [0, 0, 0] as [number, number, number];
    rebindMaterials(scene);
    scene.updateWorldMatrix(true, true);

    const pillar = scene.getObjectByName("island_pillar_project") ?? scene.getObjectByName("island_pillar_workshop");
    // Soften only the shaft. Traversing this parent also flattened the desk,
    // trim and every other child material, erasing their metallic highlights.
    const shaftMaterial = (pillar as THREE.Mesh | undefined)?.material;
    const shaftMaterials = Array.isArray(shaftMaterial) ? shaftMaterial : [shaftMaterial];
    for (const material of shaftMaterials) {
      if (material instanceof THREE.MeshStandardMaterial) material.roughness = 0.65;
    }

    const origin = pillar ? worldPos(pillar) : new THREE.Vector3();
    return [-origin.x, -floorTop(scene), -origin.z] as [number, number, number];
  }, [scene]);

  useLayoutEffect(() => {
    if (!scene) return;
    const batching = batchStationMeshes(scene);
    invalidate();
    return () => batching.dispose();
  }, [scene, invalidate]);

  if (!scene) return null;
  return (
    <group name="importedPillar" position={recenter}>
      <StationLights scene={scene} />
      <primitive object={scene} />
      <StationPanels lightColor={stationLightColor(hologramColor, hue, tint)} />
      <StationIslandHeadings scene={scene} lightColor={stationLightColor(hologramColor, hue, tint)} />
    </group>
  );
}

/** The workshop pillar and deck, exported from base.blend. */
export function ImportedPillar() {
  return (
    <Suspense fallback={null}>
      <Model />
    </Suspense>
  );
}
