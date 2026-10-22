import * as THREE from "three";
import type { CaveAtlas, CaveLight } from "./caveAssets";
import { CAVE_FLAGS } from "./caveFlags";
import { groupLights, MIX_SOFTNESS, type LightGroups } from "./caveStartup";

/**
 * Live direct light for the cave surfaces. The exporter bakes only what the
 * browser cannot compute (multi-bounce GI, the surface textures); every one of
 * the 55 Blender lights is shaded here, per pixel, with shadow maps for all but
 * the faint ones. Nothing light- or view-dependent is frozen into a texture,
 * so shadows and highlights are right from every camera position.
 *
 * Units are Blender's, checked against Cycles bakes of a white plane: a point
 * or spot light of P watts has intensity P / 4π (a spot only masks its cone,
 * it does not concentrate), an area light P / π along its normal with a
 * cosine falloff, and irradiance is I / (d² + r²): exact for a sphere light of
 * radius r, and for a disc of radius r on its axis (r² = area / π otherwise).
 */

export const MAX_LIGHTS = 64;
export const MAX_SHADOWS = 32;
/** Lights at least this strong cast shadows (every spot does). */
const SHADOW_POWER = 40;
const SHADOW_TILE = 1024;
const SHADOW_COLUMNS = 8;
export const SHADOW_FAR = 60;

/**
 * The main shadow maps spread each light's 1024² over a 150° view, so a
 * texel is 3–10 cm at the platforms: fine from the main camera, but a
 * blocky stair-step edge once the camera zooms in. Each region the camera
 * can come close to (the four platforms) therefore gets finer maps for the
 * few lights that really light it: a narrow frustum round just that region,
 * used instead of the main map inside it and faded back out at its rim.
 * (glTF metres; `centre` is a point in the region, `radius` how far from it
 * the finer maps are used.)
 */
export const FOCUS_VOLUMES: { name: string; centre: [number, number, number]; radius: number }[] = [
  { name: "Projects", centre: [22.2, 7.5, -1.4], radius: 3.2 },
  { name: "About Me", centre: [26.48, 7.6, 7.05], radius: 2.6 },
  { name: "Contact", centre: [27.0, 12.4, 5.4], radius: 3.4 },
  { name: "Experiences", centre: [10.8, 3.6, -3.2], radius: 5.0 },
];
const FOCUS_TILE = 1024;
/** Lights per region that get a finer map (the strongest at its centre). */
const FOCUS_LIGHTS = 3;
export const MAX_FOCUS = FOCUS_VOLUMES.length * FOCUS_LIGHTS;
/** The finer map reaches this far past the region, so soft-shadow filters near its rim still find their blockers. */
const FOCUS_MARGIN = 1.0;
const FOCUS_BIAS_SCALE = 0.4;
/** A light is skipped for a chunk when it adds less radiance than this anywhere on it. */
const CULL_RADIANCE = 2e-4;

export const TEXELS_PER_LIGHT = 5;

export type PackedLights = {
  data: THREE.DataTexture;
  lights: CaveLight[];
  /** Shadow slot per light, -1 for none. */
  slots: number[];
  shadowed: CaveLight[];
  /** Which lights flicker together at power-on (caveStartup.ts). */
  groups: LightGroups;
};

const casts = (l: CaveLight) => l.type === "SPOT" || l.power >= SHADOW_POWER;

/** r² of the irradiance falloff and the radius that widens highlights. */
function extent(l: CaveLight) {
  if (l.type === "AREA") {
    const [sx, sy] = l.size ?? [1, 1];
    const area = l.shape === "DISK" || l.shape === "ELLIPSE" ? (Math.PI / 4) * sx * sy : sx * sy;
    return { r2: area / Math.PI, radius: Math.sqrt(area / Math.PI) };
  }
  const r = l.radius ?? 0;
  return { r2: r * r, radius: r };
}

function intensity(l: CaveLight) {
  if (l.type === "SUN") return l.power;
  return l.type === "AREA" ? l.power / Math.PI : l.power / (4 * Math.PI);
}

export function packLights(all: CaveLight[]): PackedLights {
  const lights = all.slice(0, MAX_LIGHTS);
  const order = lights.map((_, i) => i).filter((i) => casts(lights[i])).sort((a, b) => lights[b].power - lights[a].power);
  const slots = lights.map(() => -1);
  order.slice(0, MAX_SHADOWS).forEach((light, slot) => (slots[light] = slot));
  const values = new Float32Array(MAX_LIGHTS * TEXELS_PER_LIGHT * 4);
  lights.forEach((l, i) => {
    const type = { POINT: 0, SPOT: 1, AREA: 2, SUN: 3 }[l.type];
    const cosHalf = l.type === "SPOT" ? Math.cos((l.angle ?? 1) / 2) : 0;
    const smooth = l.type === "SPOT" ? (1 - cosHalf) * (l.blend ?? 0) : 0;
    const { r2, radius } = extent(l);
    const k = intensity(l);
    values.set(
      [
        ...l.position, type,
        ...l.direction, cosHalf,
        ...l.color.map((c) => c * k), smooth,
        r2, radius, slots[i], 0,
        l.diffuse ?? 1, l.specular ?? 1, 0, 0,
      ],
      i * TEXELS_PER_LIGHT * 4,
    );
  });
  const data = new THREE.DataTexture(values, TEXELS_PER_LIGHT, MAX_LIGHTS, THREE.RGBAFormat, THREE.FloatType);
  data.needsUpdate = true;
  return { data, lights, slots, shadowed: order.slice(0, MAX_SHADOWS).map((i) => lights[i]), groups: groupLights(lights) };
}

/**
 * The lights that can reach a chunk: light-linked lights only light their
 * receiver collections, spots whose cone misses the chunk's bounds and area
 * lights facing away from it are dropped, and so are lights too faint to show.
 */
export function lightsForChunk(packed: PackedLights, atlas: CaveAtlas, bounds: THREE.Box3): number[] {
  const closest = new THREE.Vector3();
  const corners = [0, 1, 2, 3, 4, 5, 6, 7].map(
    (i) =>
      new THREE.Vector3(
        i & 1 ? bounds.max.x : bounds.min.x,
        i & 2 ? bounds.max.y : bounds.min.y,
        i & 4 ? bounds.max.z : bounds.min.z,
      ),
  );
  const center = bounds.getCenter(new THREE.Vector3());
  const radius = bounds.getSize(new THREE.Vector3()).length() / 2;
  return packed.lights.flatMap((l, i) => {
    if (l.receivers && !atlas.receivers.includes(l.receivers)) return [];
    const position = new THREE.Vector3(...l.position);
    const direction = new THREE.Vector3(...l.direction);
    if (l.type === "AREA" && corners.every((c) => c.clone().sub(position).dot(direction) <= 0)) return [];
    if (l.type === "SPOT") {
      const toCenter = center.clone().sub(position);
      const distance = toCenter.length();
      if (distance > radius) {
        const offAxis = Math.acos(THREE.MathUtils.clamp(toCenter.dot(direction) / distance, -1, 1));
        if (offAxis - Math.asin(radius / distance) >= (l.angle ?? Math.PI) / 2) return [];
      }
    }
    const d = bounds.clampPoint(position, closest).distanceTo(position);
    const peak = Math.max(...l.color) * intensity(l);
    return peak / (d * d + extent(l).r2) / Math.PI < CULL_RADIANCE ? [] : [i];
  });
}

/* ------------------------------------------------------------- shadows --- */

export type SurfaceShadows = {
  target: THREE.WebGLRenderTarget;
  matrices: THREE.Matrix4[];
  /** Per slot: tan of half the field of view (texel size per metre of distance). */
  tanHalf: number[];
  columns: number;
  rows: number;
  /** Finer maps for the regions the camera comes close to (see FOCUS_VOLUMES). */
  focus: FocusShadows | null;
};

export type FocusShadows = {
  target: THREE.WebGLRenderTarget;
  /** 5 texels per map: view-projection (4), then tan of half the fov. */
  data: THREE.DataTexture;
  /** The main-map slot each finer map replaces, or -1. */
  slots: Float32Array;
  /** Region centre and radius per map. */
  spheres: THREE.Vector4[];
  columns: number;
  rows: number;
};

/**
 * Distance-to-light maps for every shadowing light, one tile each, rendered
 * once (the cave does not move; call again if it ever does). Spots get their
 * cone, area lights a 150° frustum along their normal (they emit little
 * beyond it), point lights the same downward. Cut-out surfaces (the deck
 * grates) cast through their holes; emitters and glass cast nothing.
 */
export function renderSurfaceShadows(renderer: THREE.WebGLRenderer, scene: THREE.Object3D, packed: PackedLights): SurfaceShadows | null {
  const count = packed.shadowed.length;
  if (!count) return null;
  const columns = Math.min(SHADOW_COLUMNS, count);
  const rows = Math.ceil(count / columns);
  const target = new THREE.WebGLRenderTarget(SHADOW_TILE * columns, SHADOW_TILE * rows, {
    type: THREE.HalfFloatType,
    format: THREE.RedFormat,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    depthBuffer: true,
  });
  const casters = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
  const hidden: THREE.Object3D[] = [];
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;
    const caster = mesh.userData.shadowCaster as THREE.ShaderMaterial | undefined;
    if (caster) {
      casters.set(mesh, mesh.material);
      mesh.material = caster;
    } else if (mesh.visible) {
      mesh.visible = false;
      hidden.push(mesh);
    }
  });
  const holder = new THREE.Scene();
  const parent = scene.parent;
  holder.add(scene);
  const previousTarget = renderer.getRenderTarget();
  const previousClear = renderer.getClearColor(new THREE.Color());
  const previousAlpha = renderer.getClearAlpha();
  renderer.setRenderTarget(target);
  renderer.setClearColor(0xffffff, 1);
  renderer.clear();
  const matrices: THREE.Matrix4[] = [];
  const tanHalf: number[] = [];
  const casterMaterials = new Set(Array.from(casters.keys(), (m) => m.userData.shadowCaster as THREE.ShaderMaterial));
  packed.shadowed.forEach((light, slot) => {
    const fov = light.type === "SPOT" ? THREE.MathUtils.radToDeg(light.angle ?? 1) + 4 : 150;
    const cam = new THREE.PerspectiveCamera(Math.min(fov, 160), 1, 0.05, SHADOW_FAR);
    cam.position.set(...light.position);
    const direction: [number, number, number] = light.type === "POINT" ? [0, -1, 0] : light.direction;
    if (Math.abs(direction[1]) > 0.99) cam.up.set(0, 0, 1);
    else cam.up.set(0, 1, 0);
    cam.lookAt(light.position[0] + direction[0], light.position[1] + direction[1], light.position[2] + direction[2]);
    cam.updateMatrixWorld(true);
    for (const material of casterMaterials) material.uniforms.lightPosition.value.set(...light.position);
    const x = (slot % columns) * SHADOW_TILE;
    const y = Math.floor(slot / columns) * SHADOW_TILE;
    target.viewport.set(x, y, SHADOW_TILE, SHADOW_TILE);
    target.scissor.set(x, y, SHADOW_TILE, SHADOW_TILE);
    target.scissorTest = true;
    renderer.setRenderTarget(target);
    renderer.render(holder, cam);
    matrices.push(new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
    tanHalf.push(Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2));
  });
  target.scissorTest = false;
  const focus = CAVE_FLAGS.focusShadows ? renderFocusShadows(renderer, holder, casterMaterials, packed) : null;
  renderer.setRenderTarget(previousTarget);
  renderer.setClearColor(previousClear, previousAlpha);
  if (parent) parent.add(scene);
  for (const [mesh, material] of casters) mesh.material = material;
  for (const object of hidden) object.visible = true;
  while (matrices.length < MAX_SHADOWS) matrices.push(new THREE.Matrix4());
  while (tanHalf.length < MAX_SHADOWS) tanHalf.push(1);
  return { target, matrices, tanHalf, columns, rows, focus };
}

/**
 * Finer maps for FOCUS_VOLUMES: per region, the lights that light its centre
 * most each get a narrow frustum round the region (see FOCUS_VOLUMES). Drawn
 * with the same caster materials as the main maps, in the same pass setup.
 */
function renderFocusShadows(
  renderer: THREE.WebGLRenderer,
  holder: THREE.Scene,
  casterMaterials: Set<THREE.ShaderMaterial>,
  packed: PackedLights,
): FocusShadows | null {
  type Entry = { slot: number; light: CaveLight; volume: (typeof FOCUS_VOLUMES)[number] };
  const entries: Entry[] = [];
  for (const volume of FOCUS_VOLUMES) {
    const centre = new THREE.Vector3(...volume.centre);
    const reach = volume.radius + FOCUS_MARGIN;
    const ranked = packed.shadowed
      .map((light, slot) => {
        const toCentre = centre.clone().sub(new THREE.Vector3(...light.position));
        const dist = toCentre.length();
        if (dist < reach * 1.05) return null; // inside the region's reach: no useful frustum, the main map keeps it
        const facing = toCentre.divideScalar(dist).dot(new THREE.Vector3(...light.direction));
        // Spots light a cone, areas a half space; a point light (reduced to a downward map) lights all.
        const lit = light.type === "SPOT" ? facing > Math.cos((light.angle ?? 1) / 2 + Math.atan(reach / dist)) : light.type === "AREA" ? facing > 0.1 : true;
        if (!lit) return null;
        return { slot, light, volume, value: (intensity(light) * Math.max(facing, 0.2)) / (dist * dist + extent(light).r2) };
      })
      .filter((e): e is Entry & { value: number } => e !== null)
      .sort((a, b) => b.value - a.value)
      .slice(0, FOCUS_LIGHTS);
    entries.push(...ranked);
  }
  if (!entries.length) return null;
  const columns = Math.min(4, entries.length);
  const rows = Math.ceil(entries.length / columns);
  const target = new THREE.WebGLRenderTarget(FOCUS_TILE * columns, FOCUS_TILE * rows, {
    type: THREE.HalfFloatType,
    format: THREE.RedFormat,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    depthBuffer: true,
  });
  renderer.setRenderTarget(target);
  renderer.setClearColor(0xffffff, 1);
  renderer.clear();
  const values = new Float32Array(MAX_FOCUS * 5 * 4);
  const slots = new Float32Array(MAX_FOCUS).fill(-1);
  const spheres = Array.from({ length: MAX_FOCUS }, () => new THREE.Vector4(0, 0, 0, 0));
  entries.forEach(({ slot, light, volume }, i) => {
    const centre = new THREE.Vector3(...volume.centre);
    const position = new THREE.Vector3(...light.position);
    const dist = position.distanceTo(centre);
    const half = Math.atan((volume.radius + FOCUS_MARGIN) / dist);
    const cam = new THREE.PerspectiveCamera(THREE.MathUtils.radToDeg(half) * 2, 1, 0.05, SHADOW_FAR);
    cam.position.copy(position);
    const direction = centre.clone().sub(position).normalize();
    if (Math.abs(direction.y) > 0.99) cam.up.set(0, 0, 1);
    else cam.up.set(0, 1, 0);
    cam.lookAt(centre);
    cam.updateMatrixWorld(true);
    for (const material of casterMaterials) material.uniforms.lightPosition.value.set(...light.position);
    const x = (i % columns) * FOCUS_TILE;
    const y = Math.floor(i / columns) * FOCUS_TILE;
    target.viewport.set(x, y, FOCUS_TILE, FOCUS_TILE);
    target.scissor.set(x, y, FOCUS_TILE, FOCUS_TILE);
    target.scissorTest = true;
    renderer.setRenderTarget(target);
    renderer.render(holder, cam);
    const matrix = new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
    values.set(matrix.elements, i * 20);
    values[i * 20 + 16] = Math.tan(half);
    slots[i] = slot;
    spheres[i].set(...volume.centre, volume.radius);
  });
  target.scissorTest = false;
  const data = new THREE.DataTexture(values, 5, MAX_FOCUS, THREE.RGBAFormat, THREE.FloatType);
  data.needsUpdate = true;
  return { target, data, slots, spheres, columns, rows };
}

/* ----------------------------------------------------------- materials --- */

const SHARED_GLSL = /* glsl */ `
  uniform sampler2D albedoMap;
  varying vec2 vUv;
  varying vec3 vWorld;

  // Interleaved gradient noise: a stable per-pixel threshold in [0, 1).
  float hash(vec2 p) { return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }

  // Albedo alpha is coverage (the deck grates' holes). Mipmaps average it, so
  // a distant grate is a fraction covered. The shadow pass draws that share of
  // its pixels (screen door, which PCF smooths into partial shadow); the lit
  // pass hands it to alpha-to-coverage on the 4x MSAA frame.
  bool cutOut(float coverage) { return coverage < 0.98 && coverage <= hash(gl_FragCoord.xy); }
`;

const VERTEX = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

/** Writes distance-to-light / far, through the cut-outs (dithered, so PCF turns a distant grate into partial shadow). */
export function shadowCasterMaterial(albedo: THREE.Texture) {
  return new THREE.ShaderMaterial({
    name: "cave-shadow-caster",
    side: THREE.DoubleSide,
    uniforms: { albedoMap: { value: albedo }, lightPosition: { value: new THREE.Vector3() }, far: { value: SHADOW_FAR } },
    vertexShader: VERTEX,
    fragmentShader: /* glsl */ `
      ${SHARED_GLSL}
      uniform vec3 lightPosition;
      uniform float far;
      void main() {
        if (cutOut(texture2D(albedoMap, vUv).a)) discard;
        gl_FragColor = vec4(length(vWorld - lightPosition) / far, 0.0, 0.0, 1.0);
      }
    `,
  });
}

const DEBUG_VIEWS = ["albedo", "coverage", "normal", "roughness", "metallic", "specular", "light"];

export type LitMaterialOptions = {
  atlas: CaveAtlas;
  maps: { albedo: THREE.Texture; detail: THREE.Texture; light: THREE.Texture };
  packed: PackedLights;
  lightList: number[];
};

/**
 * Blender's Principled BSDF, reduced to what the cave uses: Lambert diffuse
 * plus a GGX specular lobe (Schlick Fresnel, F0 = 0.04 or the base colour for
 * metals) scaled by the Specular IOR Level, lit by the baked indirect light
 * and every listed light.
 */
export function litMaterial({ atlas, maps, packed, lightList }: LitMaterialOptions) {
  const list = new Int32Array(MAX_LIGHTS);
  list.set(lightList.slice(0, MAX_LIGHTS));
  return new THREE.ShaderMaterial({
    name: "cave-lit",
    side: THREE.DoubleSide,
    // Partial coverage (a distant grate) keeps that share of the MSAA samples,
    // so it averages with the dark below it as Cycles' pixel filter does.
    alphaToCoverage: true,
    defines: { MAX_LIGHTS, MAX_SHADOWS, MAX_FOCUS, TEXELS_PER_LIGHT, LIGHT_ZONES: packed.groups.anchors.length, MIX_SOFTNESS: MIX_SOFTNESS.toFixed(1), SKIP_IRRADIANCE: "3e-5", SHADOW_MIN_RADIANCE: "1e-4", DEBUG_VIEW: DEBUG_VIEWS.indexOf(CAVE_FLAGS.debug ?? "") + 1 },
    uniforms: {
      albedoMap: { value: maps.albedo },
      detailMap: { value: maps.detail },
      lightMap: { value: maps.light },
      lightScale: { value: atlas.scale },
      lightStops: { value: atlas.stops },
      lights: { value: packed.data },
      lightList: { value: list },
      lightCount: { value: Math.min(lightList.length, MAX_LIGHTS) },
      shadowMap: { value: null as THREE.Texture | null },
      shadowMatrix: { value: Array.from({ length: MAX_SHADOWS }, () => new THREE.Matrix4()) },
      shadowTanHalf: { value: new Float32Array(MAX_SHADOWS).fill(1) },
      shadowGrid: { value: new THREE.Vector2(1, 1) },
      shadowFar: { value: SHADOW_FAR },
      useShadows: { value: false },
      focusMap: { value: null as THREE.Texture | null },
      focusData: { value: null as THREE.Texture | null },
      focusSlot: { value: new Float32Array(MAX_FOCUS).fill(-1) },
      focusSphere: { value: Array.from({ length: MAX_FOCUS }, () => new THREE.Vector4()) },
      focusGrid: { value: new THREE.Vector2(1, 1) },
      // Shared with every lit material; LightStartup changes the levels in place.
      zoneAnchor: { value: packed.groups.anchors },
      zoneLevel: { value: packed.groups.levels },
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
  });
}

/** Point every lit material at the shadow maps once they exist. */
export function attachShadows(scene: THREE.Object3D, shadows: SurfaceShadows | null) {
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    const material = mesh.isMesh ? (mesh.material as THREE.ShaderMaterial) : null;
    if (material?.name !== "cave-lit") return;
    const u = material.uniforms;
    u.useShadows.value = shadows !== null;
    if (!shadows) return;
    u.shadowMap.value = shadows.target.texture;
    u.shadowMatrix.value = shadows.matrices;
    u.shadowTanHalf.value = new Float32Array(shadows.tanHalf);
    u.shadowGrid.value.set(shadows.columns, shadows.rows);
    const focus = shadows.focus;
    u.focusMap.value = focus?.target.texture ?? null;
    u.focusData.value = focus?.data ?? null;
    u.focusSlot.value = focus?.slots ?? new Float32Array(MAX_FOCUS).fill(-1);
    u.focusSphere.value = focus?.spheres ?? Array.from({ length: MAX_FOCUS }, () => new THREE.Vector4());
    u.focusGrid.value.set(focus?.columns ?? 1, focus?.rows ?? 1);
  });
}

const FRAGMENT = /* glsl */ `
  ${SHARED_GLSL}
  uniform sampler2D detailMap;
  uniform sampler2D lightMap;
  uniform float lightScale;
  uniform float lightStops;
  uniform sampler2D lights;
  uniform int lightList[MAX_LIGHTS];
  uniform int lightCount;
  uniform sampler2D shadowMap;
  uniform mat4 shadowMatrix[MAX_SHADOWS];
  uniform float shadowTanHalf[MAX_SHADOWS];
  uniform vec2 shadowGrid;
  uniform float shadowFar;
  uniform bool useShadows;
  uniform sampler2D focusMap;
  uniform sampler2D focusData;
  uniform float focusSlot[MAX_FOCUS];
  uniform vec4 focusSphere[MAX_FOCUS];
  uniform vec2 focusGrid;
  uniform vec4 zoneAnchor[LIGHT_ZONES];
  uniform float zoneLevel[LIGHT_ZONES];

  const float PI = 3.14159265359;

  vec3 octahedralDecode(vec2 e) {
    e = e * 2.0 - 1.0;
    vec3 n = vec3(e, 1.0 - abs(e.x) - abs(e.y));
    float t = max(-n.z, 0.0);
    n.xy += vec2(n.x >= 0.0 ? -t : t, n.y >= 0.0 ? -t : t);
    return normalize(n);
  }

  // The baked bounce light is nearly all from the white zones (the amber
  // practicals are a few watts): it follows them at power-on, each zone
  // weighted by its power and distance (zoneShares in caveStartup.ts).
  float bounceLevel(vec3 p) {
    float total = 0.0, lit = 0.0;
    for (int i = 0; i < LIGHT_ZONES; i++) {
      vec3 d = p - zoneAnchor[i].xyz;
      float share = zoneAnchor[i].w / (dot(d, d) + MIX_SOFTNESS);
      total += share;
      lit += share * zoneLevel[i];
    }
    return lit / max(total, 1e-6);
  }

  vec3 bakedLight() {
    vec3 code = texture2D(lightMap, vUv).rgb * 255.0;
    return lightScale * exp2((code - 1.0) / 254.0 * lightStops - lightStops) * step(0.5, code);
  }

  // Split-sum environment term (Karis' analytic fit), for the baked light
  // treated as uniform incoming radiance.
  vec3 envBrdf(vec3 f0, float roughness, float nv) {
    const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
    const vec4 c1 = vec4(1.0, 0.0425, 1.04, -0.04);
    vec4 r = roughness * c0 + c1;
    float a004 = min(r.x * r.x, exp2(-9.28 * nv)) * r.x + r.y;
    vec2 ab = vec2(-1.04, 1.04) * a004 + r.zw;
    return f0 * ab.x + ab.y;
  }

  float ggx(float nh, float a) {
    float a2 = a * a;
    float d = nh * nh * (a2 - 1.0) + 1.0;
    return a2 / (PI * d * d);
  }

  float smithVisibility(float nl, float nv, float a) {
    float a2 = a * a;
    float gv = nl * sqrt(nv * nv * (1.0 - a2) + a2);
    float gl = nv * sqrt(nl * nl * (1.0 - a2) + a2);
    return 0.5 / max(gv + gl, 1e-5);
  }

  const vec2 DISK[12] = vec2[](
    vec2(-0.326, -0.406), vec2(-0.840, -0.074), vec2(-0.696, 0.457), vec2(-0.203, 0.621),
    vec2(0.962, -0.195), vec2(0.473, -0.480), vec2(0.519, 0.767), vec2(0.185, -0.893),
    vec2(0.507, 0.064), vec2(0.896, 0.412), vec2(-0.322, -0.933), vec2(-0.792, -0.598)
  );

  vec2 tileUv(vec2 grid, int tile, vec2 local) {
    vec2 at = vec2(mod(float(tile), grid.x), floor(float(tile) / grid.x));
    return (at + clamp(local, 0.0, 1.0)) / grid;
  }

  // Soft shadows (PCSS). The maps store distance to the light. A blocker b
  // metres from a light of radius R casts a penumbra R (d - b) / b wide on a
  // receiver d metres away: find the average blocker distance over the
  // light's footprint, then filter over that width. Rotated per pixel.
  // capUv / capWorld: how far the blocker search and the filter may
  // reach, as a share of the tile and in metres at the receiver (the smaller
  // wins). Outside the map the receiver counts as lit.
  float pcss(sampler2D map, vec2 grid, int tile, mat4 matrix, float tanHalf, float texel, float biasScale,
             vec2 capUv, vec2 capWorld, vec3 p, vec3 lightPosition, float lightRadius, float nl, mat2 spin) {
    vec4 clip = matrix * vec4(p, 1.0);
    if (clip.w <= 0.0) return 1.0;
    vec2 local = clip.xy / clip.w * 0.5 + 0.5;
    if (any(lessThan(local, vec2(0.0))) || any(greaterThan(local, vec2(1.0)))) return 1.0;
    float receiver = length(p - lightPosition);
    // Tile uv per metre across the light's view, at the receiver's depth.
    float metresToUv = 0.5 / (tanHalf * clip.w);
    float slope = min(sqrt(max(1.0 - nl * nl, 0.0)) / max(nl, 1e-3), 4.0);
    float baseBias = (0.03 + receiver * 0.003) * biasScale + slope * texel / metresToUv;

    float searchMax = max(min(capUv.x, capWorld.x * metresToUv), 2.0 * texel);
    float filterMax = max(min(capUv.y, capWorld.y * metresToUv), 1.5 * texel);
    float search = clamp(lightRadius * metresToUv, 2.0 * texel, searchMax);
    float blockers = 0.0;
    float found = 0.0;
    for (int s = 0; s < 6; s++) {
      float stored = texture2D(map, tileUv(grid, tile, local + spin * DISK[s * 2] * search)).r * shadowFar;
      if (stored < receiver - baseBias) { blockers += stored; found += 1.0; }
    }
    if (found == 0.0) return 1.0;
    float blocker = blockers / found;
    float penumbra = lightRadius * (receiver - blocker) / max(blocker, 0.05);
    float filterUv = clamp(penumbra * metresToUv, 1.5 * texel, filterMax);
    // Wide filters reach parts of the receiver nearer the light: bias by the slope across them.
    float bias = baseBias + slope * filterUv / metresToUv;
    float lit = 0.0;
    for (int s = 0; s < 12; s++) {
      float stored = texture2D(map, tileUv(grid, tile, local + spin * DISK[s] * filterUv)).r * shadowFar;
      lit += stored >= receiver - bias ? 1.0 : 0.0;
    }
    return lit / 12.0;
  }

  float shadow(int slot, vec3 p, vec3 lightPosition, float lightRadius, float nl, float rotation) {
    mat2 spin = mat2(cos(rotation), sin(rotation), -sin(rotation), cos(rotation));
    // Inside a focus region, the finer map for this light (if it has one).
    for (int i = 0; i < MAX_FOCUS; i++) {
      if (int(focusSlot[i] + 0.5) != slot) continue;
      vec4 sphere = focusSphere[i];
      float d = length(p - sphere.xyz);
      if (d >= sphere.w) continue;
      mat4 m = mat4(texelFetch(focusData, ivec2(0, i), 0), texelFetch(focusData, ivec2(1, i), 0),
                    texelFetch(focusData, ivec2(2, i), 0), texelFetch(focusData, ivec2(3, i), 0));
      float tanHalf = texelFetch(focusData, ivec2(4, i), 0).x;
      float fine = pcss(focusMap, focusGrid, i, m, tanHalf, 1.0 / ${FOCUS_TILE.toFixed(1)}, ${FOCUS_BIAS_SCALE.toFixed(2)},
                        vec2(1.0), vec2(${FOCUS_MARGIN.toFixed(2)}), p, lightPosition, lightRadius, nl, spin);
      // Fade back to the main map over the region's outer quarter.
      float edge = smoothstep(0.75 * sphere.w, sphere.w, d);
      if (edge <= 0.0) return fine;
      float coarse = pcss(shadowMap, shadowGrid, slot, shadowMatrix[slot], shadowTanHalf[slot], 1.0 / ${SHADOW_TILE.toFixed(1)}, 1.0,
                          vec2(0.06, 0.08), vec2(1e9), p, lightPosition, lightRadius, nl, spin);
      return mix(fine, coarse, edge);
    }
    return pcss(shadowMap, shadowGrid, slot, shadowMatrix[slot], shadowTanHalf[slot], 1.0 / ${SHADOW_TILE.toFixed(1)}, 1.0,
                vec2(0.06, 0.08), vec2(1e9), p, lightPosition, lightRadius, nl, spin);
  }

  void main() {
    vec4 base = texture2D(albedoMap, vUv);
    // Coverage from the mip of the pixel's widest footprint, one level up:
    // holes under ~2 pixels (the perforated plates) average out instead of
    // aliasing into speckle, as Cycles averages many samples per pixel.
    vec2 texels = vUv * vec2(textureSize(albedoMap, 0));
    vec2 du = dFdx(texels), dv = dFdy(texels);
    base.a = textureLod(albedoMap, vUv, 0.5 * log2(max(max(dot(du, du), dot(dv, dv)), 1e-8)) + 1.0).a;
    if (base.a < 0.02) discard;
    vec3 albedo = base.rgb;
    vec4 detail = texture2D(detailMap, vUv);
    // Detail alpha: metals 0.5 + 0.5 * metallic, other surfaces their
    // specular strength (Specular IOR Level x 2) as 0.02 + 0.47 * s.
    bool metal = detail.a > 0.6;
    float metallic = metal ? detail.a * 2.0 - 1.0 : 0.0;
    float specularStrength = metal ? 1.0 : clamp((detail.a - 0.02) / 0.47, 0.0, 1.0);
    vec3 n = octahedralDecode(detail.xy);
    n = gl_FrontFacing ? n : -n;
    float roughness = clamp(detail.z, 0.03, 1.0);
    vec3 v = normalize(cameraPosition - vWorld);
    float nv = max(dot(n, v), 1e-4);
    vec3 diffuseColor = albedo * (1.0 - metallic);
    vec3 f0 = mix(vec3(0.04), albedo, metallic);

    vec3 indirect = bakedLight();
    #if DEBUG_VIEW > 0
      vec3 views[7] = vec3[](albedo, vec3(base.a), n * 0.5 + 0.5, vec3(roughness), vec3(metallic), vec3(specularStrength), indirect * 4.0);
      gl_FragColor = vec4(views[DEBUG_VIEW - 1], 1.0);
      return;
    #endif
    indirect *= bounceLevel(vWorld);
    vec3 color = indirect * (diffuseColor + envBrdf(f0, roughness, nv) * specularStrength);

    // Shadow lookups offset along the geometric normal, a texel or so.
    vec3 faceNormal = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
    float rotation = hash(gl_FragCoord.xy) * 6.2831853;
    float alpha = roughness * roughness;
    for (int k = 0; k < MAX_LIGHTS; k++) {
      if (k >= lightCount) break;
      vec4 t0 = texelFetch(lights, ivec2(0, lightList[k]), 0);
      vec4 t1 = texelFetch(lights, ivec2(1, lightList[k]), 0);
      vec4 t2 = texelFetch(lights, ivec2(2, lightList[k]), 0);
      vec4 t3 = texelFetch(lights, ivec2(3, lightList[k]), 0);
      vec4 t4 = texelFetch(lights, ivec2(4, lightList[k]), 0);   // diffuse, specular factors
      int type = int(t0.w + 0.5);
      vec3 l;
      float irradiance;
      if (type == 3) {
        l = -t1.xyz;
        irradiance = 1.0;
      } else {
        vec3 toLight = t0.xyz - vWorld;
        float d2 = dot(toLight, toLight);
        l = toLight * inversesqrt(d2);
        irradiance = 1.0 / (d2 + t3.x);
        float facing = dot(-l, t1.xyz);
        if (type == 1) {
          // Blender: hard cone edge, smoothstep blend over (1 - cos) * blend inside it.
          float t = facing - t1.w;
          if (t <= 0.0) continue;
          if (t2.w > 0.0) irradiance *= smoothstep(0.0, 1.0, min(t / t2.w, 1.0));
        } else if (type == 2) {
          if (facing <= 0.0) continue;
          irradiance *= facing;
        }
      }
      float nl = dot(n, l);
      if (nl <= 0.0) continue;
      // Skip what cannot show: the light's diffuse share here is negligible
      // (radiance ~1e-5; a dark cave wall is ~5e-3) and it is too faint for a
      // highlight to matter either.
      float reach = max(max(t2.r, t2.g), t2.b) * irradiance * nl;
      if (reach < SKIP_IRRADIANCE) continue;
      vec3 h = normalize(l + v);
      float nh = max(dot(n, h), 0.0);
      float lh = max(dot(l, h), 0.0);
      // Widen the lobe by the light's angular radius so big soft lights give
      // broad highlights, not pinpoints (GGX stays normalised, so energy holds).
      float dist = type == 3 ? 1e6 : length(t0.xyz - vWorld);
      float a = min(alpha + t3.y / (2.0 * dist), 1.0);
      vec3 fresnel = f0 + (1.0 - f0) * pow(1.0 - lh, 5.0);
      vec3 specular = fresnel * ggx(nh, a) * smithVisibility(nl, nv, a);
      vec3 radiance = (diffuseColor / PI * t4.x + specular * (t4.y * specularStrength)) * t2.rgb * irradiance * nl;
      // Shadows only where the light adds a visible share (radiance units).
      if (useShadows && t3.z > -0.5 && max(max(radiance.r, radiance.g), radiance.b) > SHADOW_MIN_RADIANCE) {
        vec3 offset = faceNormal * (dot(faceNormal, l) < 0.0 ? -1.0 : 1.0);
        radiance *= shadow(int(t3.z + 0.5), vWorld + offset * (0.01 + dist * 0.002), t0.xyz, t3.y, nl, rotation);
      }
      color += radiance;
    }
    gl_FragColor = vec4(color, base.a);
  }
`;
