import * as THREE from "three";

// Small shared material palette (Phase 1). Reuse instances everywhere.

export const graphite = new THREE.MeshStandardMaterial({
  color: "#3a465e",
  roughness: 0.45,
  metalness: 0.4,
  flatShading: true,
});

export const graphiteDark = new THREE.MeshStandardMaterial({
  color: "#242c42",
  roughness: 0.5,
  metalness: 0.35,
  flatShading: true,
});

export const rock = new THREE.MeshStandardMaterial({
  color: "#283452",
  roughness: 0.95,
  metalness: 0.05,
  flatShading: true,
});

export const rockDark = new THREE.MeshStandardMaterial({
  color: "#1d2a48",
  roughness: 1,
  metalness: 0,
  flatShading: true,
});

export const caveWall = new THREE.MeshStandardMaterial({
  color: "#264069",
  roughness: 1,
  metalness: 0,
  flatShading: true,
  side: THREE.BackSide,
});

export const neonCyan = new THREE.MeshStandardMaterial({
  color: "#04181d",
  emissive: "#2bd9f6",
  emissiveIntensity: 2.3,
  roughness: 0.4,
  metalness: 0,
});

export const neonCyanFaint = new THREE.MeshStandardMaterial({
  color: "#04181d",
  emissive: "#1fa8c9",
  emissiveIntensity: 0.9,
  roughness: 0.5,
  metalness: 0,
  transparent: true,
  opacity: 0.7,
});

/**
 * The deck's ground rings only. The weakest emitter here on purpose: they run
 * the full width of the floor, so at neonCyan strength they cut it to ribbons.
 */
export const runeGlow = new THREE.MeshStandardMaterial({
  color: "#04131c",
  emissive: "#0a3bff",
  emissiveIntensity: 4.2,
  roughness: 0.55,
  metalness: 0,
});

export const neonMagenta = new THREE.MeshStandardMaterial({
  color: "#2a0526",
  emissive: "#f04dd8",
  emissiveIntensity: 2.4,
  roughness: 0.4,
  metalness: 0,
});

export const lampWarm = new THREE.MeshStandardMaterial({
  color: "#3a2410",
  emissive: "#ffb254",
  emissiveIntensity: 3.2,
  roughness: 0.4,
  metalness: 0,
});

export const screenBlue = new THREE.MeshStandardMaterial({
  color: "#061430",
  emissive: "#2f7bdc",
  emissiveIntensity: 1.4,
  roughness: 0.35,
  metalness: 0,
});

export const purpleGlow = new THREE.MeshStandardMaterial({
  color: "#1a0a33",
  emissive: "#9a5cff",
  emissiveIntensity: 2.8,
  roughness: 0.4,
  metalness: 0,
});

export const crystal = new THREE.MeshStandardMaterial({
  color: "#4aa8ff",
  emissive: "#1d6fe8",
  emissiveIntensity: 1.15,
  roughness: 0.15,
  metalness: 0.1,
  flatShading: true,
  transparent: true,
  opacity: 0.95,
});

// Minecraft flat-color voxel materials
export const mcGrass = new THREE.MeshStandardMaterial({
  color: "#5ca83e",
  roughness: 0.9,
  metalness: 0,
  flatShading: true,
});

export const mcDirt = new THREE.MeshStandardMaterial({
  color: "#7a5230",
  roughness: 0.95,
  metalness: 0,
  flatShading: true,
});

export const mcStone = new THREE.MeshStandardMaterial({
  color: "#7d8792",
  roughness: 0.9,
  metalness: 0,
  flatShading: true,
});

export const mcWood = new THREE.MeshStandardMaterial({
  color: "#6b4a2f",
  roughness: 0.95,
  metalness: 0,
  flatShading: true,
});

export const mcLeaves = new THREE.MeshStandardMaterial({
  color: "#3f9440",
  roughness: 0.9,
  metalness: 0,
  flatShading: true,
});

export const mcWater = new THREE.MeshStandardMaterial({
  color: "#3aa0e8",
  emissive: "#2f8fe8",
  emissiveIntensity: 1.0,
  roughness: 0.3,
  metalness: 0,
  transparent: true,
  opacity: 0.85,
  flatShading: true,
});

/** Desk-wing HUD geometry from the Blender station. Hot enough to bloom. */
export const hudBlue = new THREE.MeshStandardMaterial({
  color: "#031528",
  emissive: "#0a6bff",
  emissiveIntensity: 2.2,
  roughness: 0.4,
  metalness: 0,
});

/** Front-edge LED strip on the station desk. */
export const ledBlue = new THREE.MeshStandardMaterial({
  color: "#03122e",
  emissive: "#0570ff",
  emissiveIntensity: 2.8,
  roughness: 0.35,
  metalness: 0,
});

export const glassPane = new THREE.MeshStandardMaterial({
  color: "#081018",
  roughness: 0.08,
  metalness: 0.12,
  transparent: true,
  opacity: 0.22,
  depthWrite: false,
});

export const metalDark = new THREE.MeshStandardMaterial({
  color: "#1a2230",
  roughness: 0.38,
  metalness: 0.72,
});

export const hologram = new THREE.MeshBasicMaterial({
  color: "#7fd0ff",
  transparent: true,
  opacity: 0.55,
  toneMapped: false,
  depthWrite: false,
});

export const hologramWire = new THREE.MeshBasicMaterial({
  color: "#cdeaff",
  wireframe: true,
  transparent: true,
  opacity: 0.28,
  toneMapped: false,
  depthWrite: false,
});

// Hot spots inside holograms (chest core, projector focus). Bright enough
// to cross the bloom threshold.
export const holoCore = new THREE.MeshStandardMaterial({
  color: "#06263f",
  emissive: "#6fd8ff",
  emissiveIntensity: 5,
  roughness: 0.4,
  metalness: 0,
});

export const paperWhite = new THREE.MeshStandardMaterial({
  color: "#d9e2f2",
  roughness: 0.9,
  metalness: 0,
  flatShading: true,
});

export const mcFlowerRed = new THREE.MeshStandardMaterial({
  color: "#d94040",
  roughness: 0.85,
  metalness: 0,
  flatShading: true,
});

export const mcFlowerYellow = new THREE.MeshStandardMaterial({
  color: "#e8c33a",
  roughness: 0.85,
  metalness: 0,
  flatShading: true,
});

export const crateOrange = new THREE.MeshStandardMaterial({
  color: "#c9702b",
  roughness: 0.7,
  metalness: 0.1,
  flatShading: true,
});

/**
 * Registry of every shared material, keyed by name. Names are written into
 * exported GLBs, which lets `BakedWorld` swap Blender-edited placeholder
 * materials back to these live instances (keeping emissive/bloom in code).
 */
export const MATERIALS: Record<string, THREE.Material> = {
  graphite,
  graphiteDark,
  rock,
  rockDark,
  caveWall,
  neonCyan,
  neonCyanFaint,
  runeGlow,
  neonMagenta,
  lampWarm,
  screenBlue,
  purpleGlow,
  crystal,
  mcGrass,
  mcDirt,
  mcStone,
  mcWood,
  mcLeaves,
  mcWater,
  hologram,
  hologramWire,
  holoCore,
  paperWhite,
  mcFlowerRed,
  mcFlowerYellow,
  crateOrange,
  hudBlue,
  ledBlue,
  glassPane,
  metalDark,
};

for (const [name, mat] of Object.entries(MATERIALS)) {
  mat.name = name;
}

/**
 * Replace GLB materials with the live instances above when the names match.
 * Unrecognised names (pillar LUT, baked canvases) pass through; unlit maps
 * skip tone mapping so they stay as authored.
 */
export function rebindMaterials(root: THREE.Object3D) {
  const swap = (m: THREE.Material): THREE.Material => {
    const shared = MATERIALS[m.name];
    if (shared) return shared;
    const basic = m as THREE.MeshBasicMaterial;
    if (basic.isMeshBasicMaterial && basic.map) basic.toneMapped = false;
    return m;
  };
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.material = Array.isArray(mesh.material)
      ? mesh.material.map(swap)
      : swap(mesh.material);
  });
}
