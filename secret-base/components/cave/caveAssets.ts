import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

/** Written by `secret-base/cave-web/export_cave.py`; all positions are glTF (Y-up). */
export type Vec3 = [number, number, number];

export type CaveLight = {
  name: string;
  type: "SPOT" | "AREA" | "POINT" | "SUN";
  power: number;
  color: Vec3;
  position: Vec3;
  direction: Vec3;
  angle?: number;
  blend?: number;
  radius?: number;
  size?: [number, number];
  shape?: "SQUARE" | "RECTANGLE" | "DISK" | "ELLIPSE";
  /** Blender's per-light diffuse / specular factors. */
  diffuse?: number;
  specular?: number;
  /** Light-linked to specific surfaces; does not light the mist volumes. */
  linked?: boolean;
  /** Light-linked: the only collection it lights (see `CaveAtlas.receivers`). */
  receivers?: string;
};

/** One bake chunk: its material textures and its baked indirect light. */
export type CaveAtlas = {
  name: string;
  size: number;
  /** sRGB base colour; alpha = coverage (cut-outs). */
  albedo: string;
  /** Octahedral shading normal (glTF space) in RG, roughness in B, metallic / specular strength in A. */
  detail: string;
  /** Indirect diffuse light, log2(radiance / scale) over `stops` stops (0 = black). */
  light: string;
  lightSize: number;
  scale: number;
  stops: number;
  /** Light-linking collections the chunk's surfaces belong to. */
  receivers: string[];
};

export type CaveMist = {
  name: string;
  /** Column-major object matrix of a unit cube (-0.5..0.5), glTF space. */
  matrix: number[];
  density: number;
  radialStart: number;
  edge: number;
  color: Vec3;
  /** Principled Volume: constant density and an absorption term. */
  uniform?: boolean;
  absorption?: Vec3;
  anisotropy: number;
  noise: null | { scale: number; detail: number; roughness: number; from: [number, number]; to: [number, number] };
};

export type CaveManifest = {
  camera: { position: Vec3; direction: Vec3; up: Vec3; lens: number; sensor: number; shift?: [number, number]; resolution: [number, number] };
  view: { transform: string; look: string; exposure: number };
  world: { color: Vec3; strength: number };
  lights: CaveLight[];
  mists: CaveMist[];
  hole: { origin: Vec3; right: Vec3; up: Vec3; into: Vec3; width: number; height: number; depth: number; rim: Vec3[] };
  atlases: CaveAtlas[];
  emissive: Record<string, Vec3>;
  transparent: Record<string, { color: Vec3; alpha: number; roughness: number }>;
};

export type CaveMaps = { albedo: THREE.Texture; detail: THREE.Texture; light: THREE.Texture };

export type CaveAssets = {
  manifest: CaveManifest;
  scene: THREE.Group;
  /** Per chunk, in manifest order. */
  atlases: CaveMaps[];
  lut: Uint8Array;
};

const asset = (file: string) => new URL(`../../models/cave/${file}`, import.meta.url).href;

let pending: Promise<CaveAssets> | null = null;

/** Loads once per page; the cave never changes while it is open. */
export function loadCaveAssets(): Promise<CaveAssets> {
  pending ??= (async () => {
    // Nothing below the manifest depends on it except the atlas list: start the
    // geometry (and the Draco decoder's workers) and the LUT straight away.
    const draco = new DRACOLoader().setDecoderPath("/draco/");
    draco.preload();
    const model = new GLTFLoader().setDRACOLoader(draco).loadAsync(asset("cave.glb"));
    const lut = fetch(asset("view-lut.bin")).then((r) => r.arrayBuffer());
    const manifest: CaveManifest = await (await fetch(asset("manifest.json"))).json();
    // The atlases are 4K WebP; ImageBitmapLoader decodes them off the main
    // thread (an <img> decodes during the first upload and stalls it). Detail
    // and light hold data, not colour, and albedo's alpha is coverage: no
    // colour-space conversion or premultiplication, and glTF UVs are top-down
    // so no flip either. Albedo is sRGB-decoded by the sampler.
    const bitmaps = new THREE.ImageBitmapLoader().setOptions({
      imageOrientation: "none",
      premultiplyAlpha: "none",
      colorSpaceConversion: "none",
    });
    const load = async (file: string, colorSpace: THREE.ColorSpace) => {
      const texture = new THREE.Texture(await bitmaps.loadAsync(asset(file)));
      texture.colorSpace = colorSpace;
      texture.flipY = false;
      texture.premultiplyAlpha = false;
      texture.anisotropy = 8;
      texture.generateMipmaps = true;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.needsUpdate = true;
      return texture;
    };
    const atlases = await Promise.all(
      manifest.atlases.map(async (a) => {
        const [albedo, detail, light] = await Promise.all([
          load(a.albedo, THREE.SRGBColorSpace),
          load(a.detail, THREE.NoColorSpace),
          load(a.light, THREE.NoColorSpace),
        ]);
        return { albedo, detail, light };
      }),
    );
    const [gltf, lutData] = await Promise.all([model, lut]);
    draco.dispose();
    return { manifest, scene: gltf.scene, atlases, lut: new Uint8Array(lutData) };
  })();
  return pending;
}

export function linear([r, g, b]: Vec3 | number[]): THREE.Color {
  return new THREE.Color().setRGB(r, g, b, THREE.LinearSRGBColorSpace);
}
