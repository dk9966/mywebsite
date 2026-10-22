import * as THREE from "three";
import { linear, type CaveAssets } from "./caveAssets";
import { lightsForChunk, litMaterial, packLights, shadowCasterMaterial, type PackedLights } from "./caveLighting";
import { splitFixture, WHITE_FIXTURES } from "./caveStartup";

/** The only emitters in the bake set: exact Blender emission colour x strength. */
function emissiveMaterial(name: string, rgb: number[]) {
  // Lamp lenses are single-sided planes that Cycles lights from both sides,
  // and several sit flush with their housings: pull them forward in depth.
  return new THREE.MeshBasicMaterial({
    name,
    color: linear(rgb),
    toneMapped: false,
    side: THREE.DoubleSide,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -8,
  });
}

/**
 * The holo table's misty glass is a layered Cycles shader (anisotropic sheen +
 * gradient emission + transparency). It is glowing glass from every angle that
 * matters here, so an additive pale-blue sheet stands in for it.
 */
function glassMaterial(name: string, spec: { color: number[]; alpha: number }) {
  if (name.startsWith("holoTable")) {
    return new THREE.MeshBasicMaterial({
      color: linear([HOLO_GLASS[0], HOLO_GLASS[1], HOLO_GLASS[2]]),
      transparent: true,
      opacity: HOLO_GLASS[3],
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      toneMapped: false,
    });
  }
  // Cycles' glass pane (alpha 0.2, roughness 0.08) mostly reflects the dim
  // cave; a dark tint at its full alpha darkened the console behind it.
  return new THREE.MeshBasicMaterial({
    color: linear(spec.color),
    transparent: true,
    opacity: spec.alpha * 0.3,
    depthWrite: false,
    toneMapped: false,
  });
}

/** Holo glass tint (linear rgb) and additive opacity, matched to the render. */
const HOLO_GLASS = [0.06, 0.2, 0.42, 0.5] as const;

/**
 * Swap every exported placeholder material for its web counterpart; returns
 * the packed light list the lit materials read.
 */
export function applyCaveMaterials({ manifest, scene, atlases }: CaveAssets): PackedLights {
  // Shared, cached assets: StrictMode and remounts must not swap twice.
  if (scene.userData.caveLights) return scene.userData.caveLights;
  const packed = packLights(manifest.lights);
  scene.userData.caveLights = packed;
  // Bake chunks: lit live, each with the lights that can reach it. Cycles
  // shades single-sided faces from both sides (the deck grates face down, the
  // cave shell faces in), so both sides are drawn and lit.
  const chunks = new Map(manifest.atlases.map((atlas, i) => [`bake_${atlas.name.split(" ").pop()}`, i]));
  scene.updateMatrixWorld(true);
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    const name = mesh.isMesh && !Array.isArray(mesh.material) ? mesh.material.name : "";
    const i = chunks.get(name);
    if (i === undefined) return;
    const bounds = new THREE.Box3().setFromObject(mesh);
    const atlas = manifest.atlases[i];
    (mesh.material as THREE.Material).dispose();
    mesh.material = litMaterial({ atlas, maps: atlases[i], packed, lightList: lightsForChunk(packed, atlas, bounds) });
    mesh.userData.shadowCaster = shadowCasterMaterial(atlases[i].albedo);
  });
  const byName = new Map<string, THREE.Material>();
  for (const [name, rgb] of Object.entries(manifest.emissive)) byName.set(name, emissiveMaterial(name, rgb));
  for (const [name, spec] of Object.entries(manifest.transparent)) {
    if (name === "glassPane" || name.startsWith("holoTable")) byName.set(name, glassMaterial(name, spec));
  }
  const fallback = new THREE.MeshBasicMaterial({ color: 0x000000 });
  const missing = new Set<string>();
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.matrixAutoUpdate = false;
    mesh.updateMatrix();
    const swap = (material: THREE.Material) => {
      if (material.name === "cave-lit") return material;
      const next = byName.get(material.name);
      if (!next) missing.add(`${material.name || "(unnamed)"} on ${mesh.name}`);
      material.dispose();
      return next ?? fallback;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
    const transparent = (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).some((m) => m.transparent);
    if (transparent) mesh.renderOrder = 2;
  });
  // The white lenses and strips power on zone by zone with the light they cast.
  const fixtures: THREE.Mesh[] = [];
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (mesh.isMesh && !Array.isArray(mesh.material) && WHITE_FIXTURES.has(mesh.material.name)) fixtures.push(mesh);
  });
  for (const mesh of fixtures) splitFixture(mesh, packed.groups);
  if (missing.size) console.warn("[cave] materials without a web counterpart:", [...missing]);
  return packed;
}
