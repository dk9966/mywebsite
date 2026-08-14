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
};

for (const [name, mat] of Object.entries(MATERIALS)) {
  mat.name = name;
}
