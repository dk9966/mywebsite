import * as THREE from "three";

// Small shared material palette (Phase 1). Reuse instances everywhere.

/**
 * Blender's Principled BSDF sockets hold *linear* values, so a colour copied
 * from a .blend has to be fed in as linear — writing it as a hex string would
 * put it through the sRGB decode a second time and come out far too dark.
 */
function lin(r: number, g: number, b: number): THREE.Color {
  return new THREE.Color().setRGB(r, g, b, THREE.LinearSRGBColorSpace);
}

export const graphite = new THREE.MeshStandardMaterial({
  color: lin(0.075, 0.093, 0.135),
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
  color: lin(0.055, 0.072, 0.115),
  roughness: 0.95,
  metalness: 0.05,
  flatShading: true,
});

export const rockDark = new THREE.MeshStandardMaterial({
  color: lin(0.028, 0.04, 0.078),
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
  color: lin(0.004, 0.055, 0.075),
  emissive: lin(0.06, 0.55, 1),
  emissiveIntensity: 1.9,
  roughness: 0.4,
  metalness: 0,
});

export const neonCyanFaint = new THREE.MeshStandardMaterial({
  color: lin(0.004, 0.055, 0.075),
  emissive: lin(0.05, 0.35, 0.72),
  emissiveIntensity: 1.2,
  roughness: 0.5,
  metalness: 0,
});

/**
 * The deck's ground rings only. Deep blue rather than cyan, and the strongest
 * emitter in the palette — that pairing is what makes them read as thin bright
 * strokes over the stone instead of washing it out.
 */
export const runeGlow = new THREE.MeshStandardMaterial({
  color: lin(0.006, 0.03, 0.055),
  emissive: lin(0.02, 0.13, 1),
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
  color: lin(0.12, 0.07, 0.03),
  emissive: lin(1, 0.62, 0.26),
  emissiveIntensity: 3,
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
  color: lin(0.055, 0.02, 0.11),
  emissive: lin(0.55, 0.16, 1),
  emissiveIntensity: 2.6,
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
  color: lin(0.052, 0.03, 0.016),
  roughness: 0.8,
  metalness: 0,
  flatShading: true,
});

export const mcLeaves = new THREE.MeshStandardMaterial({
  color: lin(0.035, 0.09, 0.045),
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
  color: lin(0.006, 0.04, 0.11),
  emissive: lin(0.06, 0.42, 1),
  emissiveIntensity: 1.25,
  roughness: 0.4,
  metalness: 0,
});

/** Front-edge LED strip on the station desk. */
export const ledBlue = new THREE.MeshStandardMaterial({
  color: lin(0.01, 0.07, 0.18),
  emissive: lin(0.02, 0.26, 1),
  emissiveIntensity: 2.6,
  roughness: 0.35,
  metalness: 0,
});

export const glassPane = new THREE.MeshStandardMaterial({
  color: lin(0.012, 0.016, 0.03),
  roughness: 0.08,
  metalness: 0,
  transparent: true,
  opacity: 0.2,
  depthWrite: false,
});

export const metalDark = new THREE.MeshStandardMaterial({
  color: lin(0.045, 0.05, 0.062),
  roughness: 0.3,
  metalness: 0.85,
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
 * Blender exports everything with backface culling off, so a fair number of
 * meshes (console greebles, rune strips, deck trim) rely on being drawn from
 * both sides. The shared instances are front-side, so keep a double-sided
 * twin of each and hand that out when the GLB asks for one.
 */
const doubleSided = new Map<string, THREE.Material>();

function asDoubleSided(shared: THREE.Material): THREE.Material {
  let twin = doubleSided.get(shared.name);
  if (!twin) {
    twin = shared.clone();
    twin.name = shared.name;
    twin.side = THREE.DoubleSide;
    doubleSided.set(shared.name, twin);
  }
  return twin;
}

/**
 * Replace GLB materials with the live instances above when the names match.
 * Unrecognised names (pillar LUT, baked canvases) pass through; unlit maps
 * skip tone mapping so they stay as authored.
 */
export function rebindMaterials(root: THREE.Object3D) {
  const swap = (m: THREE.Material): THREE.Material => {
    const shared = MATERIALS[m.name];
    if (shared) {
      return m.side === THREE.DoubleSide ? asDoubleSided(shared) : shared;
    }
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
