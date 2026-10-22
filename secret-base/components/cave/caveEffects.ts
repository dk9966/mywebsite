import * as THREE from "three";
import { BlendFunction, BloomEffect, Effect, EffectAttribute } from "postprocessing";
import type { CaveLight, CaveMist } from "./caveAssets";

/* ------------------------------------------------------------ view LUT --- */

export const LUT_SIZE = 48;
export const LUT_MIN_EV = -14;
export const LUT_MAX_EV = 10;

/**
 * Blender's view transform (AgX, "Medium High Contrast" look, exposure) baked
 * by `cave-web/gen_view_lut.py`. Input is scene-linear; output is the final
 * display-encoded sRGB, so the canvas must not encode again (`linear` Canvas).
 */
export class ViewLutEffect extends Effect {
  constructor(data: Uint8Array) {
    const rgba = new Uint8Array(LUT_SIZE ** 3 * 4);
    for (let i = 0; i < LUT_SIZE ** 3; i++) {
      rgba[i * 4] = data[i * 3];
      rgba[i * 4 + 1] = data[i * 3 + 1];
      rgba[i * 4 + 2] = data[i * 3 + 2];
      rgba[i * 4 + 3] = 255;
    }
    const lut = new THREE.Data3DTexture(rgba, LUT_SIZE, LUT_SIZE, LUT_SIZE);
    lut.format = THREE.RGBAFormat;
    lut.type = THREE.UnsignedByteType;
    lut.minFilter = lut.magFilter = THREE.LinearFilter;
    lut.wrapS = lut.wrapT = lut.wrapR = THREE.ClampToEdgeWrapping;
    lut.unpackAlignment = 1;
    lut.needsUpdate = true;
    super("ViewLutEffect", /* glsl */ `
      uniform lowp sampler3D lut;
      void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
        vec3 c = max(inputColor.rgb, vec3(0.0));
        vec3 coord = clamp((log2(max(c, vec3(1e-12))) - (${LUT_MIN_EV.toFixed(1)})) / ${(LUT_MAX_EV - LUT_MIN_EV).toFixed(1)}, 0.0, 1.0);
        // Index 0 of the LUT is exact black; everything darker clamps onto it.
        vec3 tc = (coord * ${(LUT_SIZE - 1).toFixed(1)} + 0.5) / ${LUT_SIZE.toFixed(1)};
        // Opaque: alpha-to-coverage leaves partial alpha in the frame.
        outputColor = vec4(texture(lut, tc).rgb, 1.0);
      }
    `, { uniforms: new Map([["lut", new THREE.Uniform(lut)]]) });
  }
}

/**
 * Debug output (`?logout`): scene-linear radiance as log2 over the LUT's range,
 * so captures can be compared numerically with Blender's linear EXRs.
 */
export class LogEncodeEffect extends Effect {
  constructor() {
    super("LogEncodeEffect", /* glsl */ `
      void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
        vec3 c = max(inputColor.rgb, vec3(1e-12));
        outputColor = vec4(clamp((log2(c) - (${LUT_MIN_EV.toFixed(1)})) / ${(LUT_MAX_EV - LUT_MIN_EV).toFixed(1)}, 0.0, 1.0), 1.0);
      }
    `);
  }
}

/* -------------------------------------------------------- pixel filter --- */

/**
 * Cycles reconstructs pixels with a 1.5 px Blackman-Harris filter, so a lamp
 * lens a pixel wide but 30x over white still lights a 3-4 px puck. WebGL draws
 * that single pixel. This spreads only the HDR excess (above 1.0) with a
 * matching kernel, energy-preserving, leaving everything else untouched.
 */
export class PixelFilterEffect extends Effect {
  constructor() {
    super("PixelFilterEffect", /* glsl */ `
      vec3 excess(vec2 uv) { return max(texture2D(inputBuffer, uv).rgb - 1.0, 0.0); }
      void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
        vec3 spread = vec3(0.0);
        float total = 0.0;
        for (int y = -2; y <= 2; y++) {
          for (int x = -2; x <= 2; x++) {
            float r2 = float(x * x + y * y);
            float w = exp(-r2 / (2.0 * 0.62 * 0.62));
            spread += excess(uv + vec2(float(x), float(y)) * texelSize) * w;
            total += w;
          }
        }
        vec3 base = inputColor.rgb - max(inputColor.rgb - 1.0, 0.0);
        outputColor = vec4(base + spread / total, inputColor.a);
      }
    `);
  }
}

/* ---------------------------------------------------------- amber bloom --- */

/**
 * The .blend compositor: Fog Glow only on pixels where R - B > 0.5 (the amber
 * practicals), threshold 0.7 with a 0.3 knee, added on top of the render.
 */
export function amberBloom(options: { intensity: number; radius: number; threshold: number; smoothing: number }) {
  const bloom = new BloomEffect({
    blendFunction: BlendFunction.ADD,
    mipmapBlur: true,
    luminanceThreshold: options.threshold,
    luminanceSmoothing: options.smoothing,
    intensity: options.intensity,
    radius: options.radius,
    levels: 8,
  });
  const material = bloom.luminanceMaterial;
  material.fragmentShader = material.fragmentShader
    .replace("float l=luminance(texel.rgb);", "float l=max(texel.r,max(texel.g,texel.b));")
    .replace("float mask=1.0;", "float mask=step(0.5,texel.r-texel.b);")
    .replace("mask=smoothstep(threshold,threshold+smoothing,l);", "mask*=smoothstep(threshold,threshold+smoothing,l);");
  material.needsUpdate = true;
  return bloom;
}

/* ------------------------------------------------------------------ haze --- */

/**
 * Lights that scatter in the mist: every spot, the larger area/point lights,
 * strongest first. Light-linked lights only reach their receiver surfaces.
 * Shadow slots follow this order, so the spot shadow maps use it too.
 */
function hazeLightList(lights: CaveLight[]) {
  return lights
    .filter((l) => !l.linked)
    .filter((l) => l.type === "SPOT" || (l.type === "AREA" && l.power >= 20) || (l.type === "POINT" && l.power >= 20))
    .sort((a, b) => b.power - a.power)
    .slice(0, MAX_HAZE_LIGHTS);
}

export const MAX_HAZE_LIGHTS = 48;
export const MAX_MISTS = 12;
export const MAX_SHADOWED_SPOTS = 12;
/** Area lights at least this strong get a shadow map too (the decks occlude them). */
const SHADOWED_AREA_POWER = 500;
const casts = (l: CaveLight) => l.type === "SPOT" || (l.type === "AREA" && l.power >= SHADOWED_AREA_POWER);
/** Texels along each side of the baked FBM volume. */
const NOISE_RES = 64;

/** One haze light, in the three texels the shader reads it from. */
type HazeLight = {
  position: THREE.Vector3;
  direction: THREE.Vector3;
  /** 0 point, 1 spot, 2 area. */
  type: number;
  cosHalf: number;
  /** Brightest channel of colour × intensity: the culling bound's numerator. */
  peak: number;
  clampRadius: number;
  texels: number[];
};

function packHazeLights(lights: CaveLight[], shadowed: boolean): HazeLight[] {
  let spotIndex = 0;
  return hazeLightList(lights).map((l) => {
    const type = l.type === "SPOT" ? 1 : l.type === "AREA" ? 2 : 0;
    const cosHalf = l.type === "SPOT" ? Math.cos((l.angle ?? 1) / 2) : 0;
    const smooth = l.type === "SPOT" ? (1 - cosHalf) * (l.blend ?? 0) : 0;
    const intensity = l.type === "AREA" ? l.power / Math.PI : l.power / (4 * Math.PI);
    const shadowIndex = casts(l) && shadowed && spotIndex < MAX_SHADOWED_SPOTS ? spotIndex++ : -1;
    const clampRadius = l.type === "AREA" ? Math.max(...(l.size ?? [1, 1])) * 0.5 : 0.25;
    const color = l.color.map((c) => c * intensity);
    return {
      position: new THREE.Vector3(...l.position),
      direction: new THREE.Vector3(...l.direction),
      type,
      cosHalf,
      peak: Math.max(...color),
      clampRadius,
      texels: [
        // Shadow slot and clamp radius ride along with the type in position.w.
        ...l.position, type + 4 * (shadowIndex + 1) + 64 * Math.round(clampRadius * 100),
        ...l.direction, cosHalf,
        ...color, smooth,
      ],
    };
  });
}

/**
 * The lights worth evaluating inside one mist. Spots whose cone misses the
 * volume and area lights facing away from it are dropped outright. The rest
 * are ranked by what they add along a view ray, which falls off as 1/d (the
 * path integral of 1/r²), d the light's distance to the volume; the weakest
 * are dropped while together they stay under `cull` of the mist's total.
 */
function lightsForMist(mist: CaveMist, lights: HazeLight[], cull: number): number[] {
  const toWorld = new THREE.Matrix4().fromArray(mist.matrix);
  const toLocal = toWorld.clone().invert();
  const center = new THREE.Vector3().setFromMatrixPosition(toWorld);
  const axis = new THREE.Vector3();
  const radius = 0.5 * Math.hypot(...[0, 1, 2].map((i) => axis.setFromMatrixColumn(toWorld, i).length()));
  const closest = new THREE.Vector3();
  const reach = lights.map((l) => {
    const toCenter = center.clone().sub(l.position);
    const distance = toCenter.length();
    if (l.type === 1 && distance > radius) {
      const offAxis = Math.acos(THREE.MathUtils.clamp(toCenter.dot(l.direction) / distance, -1, 1));
      if (offAxis - Math.asin(radius / distance) >= Math.acos(l.cosHalf)) return 0;
    }
    if (l.type === 2 && toCenter.dot(l.direction) <= -radius) return 0;
    closest.copy(l.position).applyMatrix4(toLocal).clampScalar(-0.5, 0.5).applyMatrix4(toWorld);
    return l.peak / Math.max(closest.distanceTo(l.position), l.clampRadius);
  });
  const total = reach.reduce((sum, r) => sum + r, 0);
  const dropped = new Set<number>();
  let budget = cull * total;
  for (const i of reach.map((_, i) => i).sort((a, b) => reach[a] - reach[b])) {
    if (reach[i] > budget) break;
    budget -= reach[i];
    dropped.add(i);
  }
  return reach.flatMap((r, i) => (r > 0 && !dropped.has(i) ? [i] : []));
}

export type HazeOptions = {
  /** Calibrated scattering gain (Cycles' volume bounce and light-tree sampling). */
  gain: number;
  /** Cave-wide bounce light in the uniform volume. */
  ambient: number;
  /** Ray-march resolution as a fraction of the frame. */
  scale: number;
  /** See `lightsForMist`. */
  cull: number;
};

/**
 * The Cycles mist volumes, ray-marched against the exported light list.
 *
 * Density follows the .blend node graphs exactly (radial smootherstep fade,
 * soft top/bottom edges, FBM noise for the under-platform mists). Light comes
 * from every spot (with a depth-map shadow, so beams stop at the decks) and the
 * larger area lights (unshadowed, cosine-weighted). Units are Cycles watts:
 * point/spot intensity P/4π, area intensity P·cosθ/π, and the scattering
 * coefficient is density·colour. `gain` is the one calibrated factor, absorbing
 * Cycles' single volume bounce and light-tree sampling.
 *
 * The march runs at `scale` × the frame into an in-scatter + transmittance
 * pair, which this effect then upsamples with depth-aware weights so the haze
 * stays put on silhouettes. Each mist only loops over the lights that reach it.
 */
export class HazeEffect extends Effect {
  camera: THREE.PerspectiveCamera;
  private readonly scale: number;
  /** [0] in-scattered light + the distance it was marched to, [1] transmittance. */
  private readonly march: THREE.WebGLRenderTarget;
  private readonly marchMaterial: THREE.ShaderMaterial;
  private readonly noise: THREE.WebGL3DRenderTarget;
  private readonly noiseMaterial: THREE.ShaderMaterial;
  private noiseBaked = false;
  private readonly quad: THREE.Mesh;
  private readonly quadScene = new THREE.Scene();
  private readonly quadCamera = new THREE.Camera();

  constructor(camera: THREE.PerspectiveCamera, mists: CaveMist[], lights: CaveLight[], shadow: SpotShadows | null, options: HazeOptions) {
    const used = mists.slice(0, MAX_MISTS);
    const mistMatrices = used.map((m) => new THREE.Matrix4().fromArray(m.matrix).invert());
    while (mistMatrices.length < MAX_MISTS) mistMatrices.push(new THREE.Matrix4());
    const mistA: THREE.Vector4[] = [];
    const mistB: THREE.Vector4[] = [];
    const mistC: THREE.Vector4[] = [];
    const mistD: THREE.Vector4[] = [];
    for (let i = 0; i < MAX_MISTS; i++) {
      const m = used[i];
      mistA.push(m ? new THREE.Vector4(m.density, m.radialStart, m.edge, m.anisotropy) : new THREE.Vector4());
      mistB.push(m ? new THREE.Vector4(...m.color, m.noise ? m.noise.scale : 0) : new THREE.Vector4());
      mistC.push(m?.noise ? new THREE.Vector4(m.noise.from[0], m.noise.from[1], m.noise.to[0], m.noise.to[1]) : new THREE.Vector4(0, 1, 1, 1));
      mistD.push(new THREE.Vector4(...(m?.absorption ?? [0, 0, 0]), m?.uniform ? 1 : 0));
    }

    // Per-mist light lists, flattened into rows of a float texture.
    const hazeLights = packHazeLights(lights, shadow !== null);
    const rows: number[] = [];
    const mistLights: THREE.Vector2[] = [];
    for (let i = 0; i < MAX_MISTS; i++) {
      const list = used[i] ? lightsForMist(used[i], hazeLights, options.cull) : [];
      mistLights.push(new THREE.Vector2(rows.length / 12, list.length));
      for (const index of list) rows.push(...hazeLights[index].texels);
    }
    if (!rows.length) rows.push(...new Array(12).fill(0));
    const lightData = new THREE.DataTexture(new Float32Array(rows), 3, rows.length / 12, THREE.RGBAFormat, THREE.FloatType);
    lightData.needsUpdate = true;

    // The FBM only ever sees generated coordinates times the noise scale.
    const noiseSpan = Math.max(1, ...used.map((m) => m.noise?.scale ?? 0));
    const noise = new THREE.WebGL3DRenderTarget(NOISE_RES, NOISE_RES, NOISE_RES, {
      type: THREE.HalfFloatType,
      format: THREE.RGBAFormat,
      depthBuffer: false,
    });
    noise.texture.minFilter = noise.texture.magFilter = THREE.LinearFilter;
    noise.texture.wrapS = noise.texture.wrapT = noise.texture.wrapR = THREE.ClampToEdgeWrapping;
    noise.texture.generateMipmaps = false;

    const march = new THREE.WebGLRenderTarget(1, 1, {
      count: 2,
      type: THREE.HalfFloatType,
      format: THREE.RGBAFormat,
      minFilter: THREE.NearestFilter,
      magFilter: THREE.NearestFilter,
      depthBuffer: false,
      generateMipmaps: false,
    });

    const marchMaterial = new THREE.ShaderMaterial({
      name: "HazeMarch",
      glslVersion: THREE.GLSL3,
      depthTest: false,
      depthWrite: false,
      vertexShader: QUAD_VERTEX,
      fragmentShader: HAZE_MARCH,
      defines: {
        MAX_MISTS: String(MAX_MISTS),
        MAX_SPOTS: String(MAX_SHADOWED_SPOTS),
        HAS_SHADOWS: shadow ? "1" : "0",
      },
      uniforms: {
        depthBuffer: { value: null },
        projectionInverse: { value: new THREE.Matrix4() },
        cameraWorld: { value: new THREE.Matrix4() },
        mistInverse: { value: mistMatrices },
        mistA: { value: mistA },
        mistB: { value: mistB },
        mistC: { value: mistC },
        mistD: { value: mistD },
        mistLights: { value: mistLights },
        mistCount: { value: used.length },
        lightData: { value: lightData },
        noiseVolume: { value: noise.texture },
        noiseSpan: { value: noiseSpan },
        shadowMap: { value: shadow?.target.texture ?? null },
        shadowMatrix: { value: shadow?.matrices ?? Array.from({ length: MAX_SHADOWED_SPOTS }, () => new THREE.Matrix4()) },
        shadowTiles: { value: shadow ? shadow.tiles : 1 },
        shadowFar: { value: SHADOW_FAR },
        gain: { value: options.gain },
        // Cycles' one volume bounce: light reflected off the lit rock and decks
        // scattering in the cave-wide haze. Cool, like the bounce light.
        ambient: { value: new THREE.Vector3(0.55, 0.75, 1).multiplyScalar(options.ambient) },
      },
    });

    const noiseMaterial = new THREE.ShaderMaterial({
      name: "HazeNoiseBake",
      depthTest: false,
      depthWrite: false,
      vertexShader: QUAD_VERTEX,
      fragmentShader: NOISE_BAKE,
      uniforms: { layer: { value: 0 }, span: { value: noiseSpan }, res: { value: NOISE_RES } },
    });

    super("HazeEffect", HAZE_COMPOSITE, {
      attributes: EffectAttribute.DEPTH,
      uniforms: new Map<string, THREE.Uniform>([
        ["hazeLight", new THREE.Uniform(march.textures[0])],
        ["hazeTransmit", new THREE.Uniform(march.textures[1])],
        ["hazeSize", new THREE.Uniform(new THREE.Vector4(1, 1, 1, 1))],
        ["projectionInverse", new THREE.Uniform(new THREE.Matrix4())],
      ]),
    });
    this.camera = camera;
    this.scale = options.scale;
    this.march = march;
    this.marchMaterial = marchMaterial;
    this.noise = noise;
    this.noiseMaterial = noiseMaterial;
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), marchMaterial);
    this.quad.frustumCulled = false;
    this.quadScene.add(this.quad);
  }

  /** Rows per mist, for debugging the culling (`__cave` in dev). */
  get lightRows() {
    return (this.marchMaterial.uniforms.mistLights.value as THREE.Vector2[]).map((v) => v.y);
  }

  setDepthTexture(depthTexture: THREE.Texture) {
    this.marchMaterial.uniforms.depthBuffer.value = depthTexture;
  }

  setSize(width: number, height: number) {
    const w = Math.max(1, Math.round(width * this.scale));
    const h = Math.max(1, Math.round(height * this.scale));
    this.march.setSize(w, h);
    this.uniforms.get("hazeSize")!.value.set(w, h, 1 / w, 1 / h);
  }

  update(renderer: THREE.WebGLRenderer) {
    const previous = renderer.getRenderTarget();
    if (!this.noiseBaked) {
      // The FBM is static: bake it once instead of 24 hashes per march step.
      this.quad.material = this.noiseMaterial;
      for (let layer = 0; layer < NOISE_RES; layer++) {
        this.noiseMaterial.uniforms.layer.value = layer;
        renderer.setRenderTarget(this.noise, layer);
        renderer.render(this.quadScene, this.quadCamera);
      }
      this.quad.material = this.marchMaterial;
      this.noiseBaked = true;
    }
    const projectionInverse = this.camera.projectionMatrixInverse;
    this.marchMaterial.uniforms.projectionInverse.value.copy(projectionInverse);
    this.marchMaterial.uniforms.cameraWorld.value.copy(this.camera.matrixWorld);
    this.uniforms.get("projectionInverse")!.value.copy(projectionInverse);
    renderer.setRenderTarget(this.march);
    renderer.render(this.quadScene, this.quadCamera);
    renderer.setRenderTarget(previous);
  }

  dispose() {
    super.dispose();
    this.quad.geometry.dispose();
    (this.marchMaterial.uniforms.lightData.value as THREE.DataTexture).dispose();
  }
}

const QUAD_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = position.xy * 0.5 + 0.5;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

// 3D gradient noise, remapped like Blender's Noise Texture (0..1, 0.5 mean).
const FBM = /* glsl */ `
vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}
float gnoise(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  vec3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  return mix(mix(mix(dot(hash3(i), f), dot(hash3(i + vec3(1, 0, 0)), f - vec3(1, 0, 0)), u.x),
                 mix(dot(hash3(i + vec3(0, 1, 0)), f - vec3(0, 1, 0)), dot(hash3(i + vec3(1, 1, 0)), f - vec3(1, 1, 0)), u.x), u.y),
             mix(mix(dot(hash3(i + vec3(0, 0, 1)), f - vec3(0, 0, 1)), dot(hash3(i + vec3(1, 0, 1)), f - vec3(1, 0, 1)), u.x),
                 mix(dot(hash3(i + vec3(0, 1, 1)), f - vec3(0, 1, 1)), dot(hash3(i + vec3(1, 1, 1)), f - vec3(1, 1, 1)), u.x), u.y), u.z);
}
float fbm(vec3 p) {
  // Detail 2, roughness 0.6, lacunarity 2, normalised.
  float sum = 0.0, amp = 1.0, norm = 0.0;
  for (int o = 0; o < 3; o++) {
    sum += amp * gnoise(p);
    norm += amp;
    amp *= 0.6;
    p *= 2.0;
  }
  return sum / norm * 0.75 + 0.5;
}
`;

/** One layer of the FBM volume; texel centres sit at (i + 0.5) / res × span. */
const NOISE_BAKE = /* glsl */ `
uniform float layer;
uniform float span;
uniform float res;
${FBM}
void main() {
  gl_FragColor = vec4(fbm(vec3(gl_FragCoord.xy, layer + 0.5) / res * span), 0.0, 0.0, 1.0);
}
`;

/**
 * The march itself, one low-res pixel per ray. Loop bounds are uniforms, not
 * array sizes, so the driver compiles loops instead of unrolling
 * mists × steps × lights.
 */
const HAZE_MARCH = /* glsl */ `
precision highp sampler3D;
uniform sampler2D depthBuffer;
uniform mat4 projectionInverse;
uniform mat4 cameraWorld;
uniform mat4 mistInverse[MAX_MISTS];
uniform vec4 mistA[MAX_MISTS];   // density, radialStart, edge, anisotropy
uniform vec4 mistB[MAX_MISTS];   // colour, noise scale (0 = none)
uniform vec4 mistC[MAX_MISTS];   // noise from.x, from.y, to.x, to.y
uniform vec4 mistD[MAX_MISTS];   // absorption colour, uniform flag
uniform vec2 mistLights[MAX_MISTS]; // first light row, row count
uniform int mistCount;
// Three texels per light: position + packed type / shadow slot / clamp radius,
// direction + cos(half spot angle), colour × intensity + spot smooth width.
uniform sampler2D lightData;
uniform sampler3D noiseVolume;
uniform float noiseSpan;
uniform sampler2D shadowMap;
uniform mat4 shadowMatrix[MAX_SPOTS];
uniform float shadowTiles;
uniform float shadowFar;
uniform float gain;
uniform vec3 ambient;

varying vec2 vUv;
layout(location = 0) out vec4 outLight;
layout(location = 1) out vec4 outTransmit;

const int STEPS = 18;
const int UNIFORM_STEPS = 32;

float smootherstep01(float x) {
  x = clamp(x, 0.0, 1.0);
  return x * x * x * (x * (x * 6.0 - 15.0) + 10.0);
}

// Mist density at a generated coordinate g in 0..1 (the node graph in the .blend).
float mistDensity(int i, vec3 g) {
  vec4 a = mistA[i];
  if (mistD[i].w > 0.5) return a.x;
  float radial = 1.0 - smootherstep01((length((g.xy - 0.5) * 2.0) - a.y) / (1.0 - a.y));
  float vertical = smootherstep01(min(g.z, 1.0 - g.z) / a.z);
  float d = a.x * radial * vertical;
  if (mistB[i].w > 0.0 && d > 0.0) {
    float n = texture(noiseVolume, g * (mistB[i].w / noiseSpan)).r;
    vec4 c = mistC[i];
    d *= mix(c.z, c.w, clamp((n - c.x) / (c.y - c.x), 0.0, 1.0));
  }
  return d;
}

float spotShadow(int slot, vec3 p, vec3 lp) {
#if HAS_SHADOWS
  vec4 clip = shadowMatrix[slot] * vec4(p, 1.0);
  if (clip.w <= 0.0) return 1.0;
  vec2 ndc = clip.xy / clip.w;
  if (abs(ndc.x) > 1.0 || abs(ndc.y) > 1.0) return 1.0;
  vec2 tileUv = ndc * 0.5 + 0.5;
  vec2 uv = vec2((float(slot) + tileUv.x) / shadowTiles, tileUv.y);
  float stored = texture(shadowMap, uv).r * shadowFar;
  return step(length(p - lp), stored + 0.15);
#else
  return 1.0;
#endif
}

vec3 inScatter(vec3 p, vec3 rayDir, float g, int first, int last) {
  vec3 total = vec3(0.0);
  for (int k = first; k < last; k++) {
    vec4 lp = texelFetch(lightData, ivec2(0, k), 0);
    vec4 ld = texelFetch(lightData, ivec2(1, k), 0);
    float packed = lp.w;
    float type = mod(packed, 4.0);
    float slot = mod(floor(packed / 4.0), 16.0) - 1.0;   // shadow-map tile, -1 = none
    float clampRadius = floor(packed / 64.0) / 100.0;
    vec3 toLight = lp.xyz - p;
    float dist2 = max(dot(toLight, toLight), clampRadius * clampRadius);
    vec3 L = toLight * inversesqrt(dist2);
    float cosE = dot(-L, ld.xyz);
    vec4 lc = texelFetch(lightData, ivec2(2, k), 0);
    float att = 1.0;
    if (type > 1.5) {
      att = max(cosE, 0.0);
    } else if (type > 0.5) {
      float t = cosE - ld.w;
      if (t <= 0.0) continue;
      if (lc.w > 0.0) att = smoothstep(0.0, lc.w, t);
    }
    if (att <= 0.0) continue;
    if (slot >= 0.0) att *= spotShadow(int(slot), p, lp.xyz);
    if (att <= 0.0) continue;
    float cosT = dot(L, -rayDir);
    float hg = (1.0 - g * g) / (12.566370614 * pow(max(1.0 + g * g + 2.0 * g * cosT, 1e-4), 1.5));
    total += lc.rgb * (att * hg / dist2);
  }
  return total;
}

float ign(vec2 px) {
  return fract(52.9829189 * fract(dot(px, vec2(0.06711056, 0.00583715))));
}

void main() {
  float depth = texture(depthBuffer, vUv).r;
  vec4 ndc = vec4(vUv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
  vec4 view = projectionInverse * ndc;
  view /= view.w;
  vec3 origin = cameraWorld[3].xyz;
  vec3 target = (cameraWorld * vec4(view.xyz, 1.0)).xyz;
  float sceneDist = depth >= 0.9999 ? 200.0 : length(target - origin);
  vec3 rayDir = normalize(target - origin);
  float jitter = ign(gl_FragCoord.xy);

  vec3 light = vec3(0.0);
  vec3 transmittance = vec3(1.0);
  for (int i = 0; i < mistCount; i++) {
    // Ray vs the volume's unit cube, in its local space.
    vec3 o = (mistInverse[i] * vec4(origin, 1.0)).xyz;
    vec3 d = (mistInverse[i] * vec4(rayDir, 0.0)).xyz;
    vec3 inv = 1.0 / d;
    vec3 t0 = (-0.5 - o) * inv;
    vec3 t1 = (0.5 - o) * inv;
    vec3 tmin = min(t0, t1);
    vec3 tmax = max(t0, t1);
    float enter = max(max(max(tmin.x, tmin.y), tmin.z), 0.0);
    float exit = min(min(min(tmax.x, tmax.y), tmax.z), sceneDist);
    if (exit <= enter) continue;
    bool uniformVolume = mistD[i].w > 0.5;
    int steps = uniformVolume ? UNIFORM_STEPS : STEPS;
    float dt = (exit - enter) / float(steps);
    vec3 color = mistB[i].rgb;
    vec3 extinction = color + mistD[i].rgb;
    float g = mistA[i].w;
    int first = int(mistLights[i].x);
    int last = first + int(mistLights[i].y);
    for (int s = 0; s < steps; s++) {
      float t = enter + (float(s) + jitter) * dt;
      vec3 local = o + d * t;
      float density = mistDensity(i, local + 0.5);
      if (density <= 0.0) continue;
      vec3 sigma = density * color;
      vec3 p = origin + rayDir * t;
      vec3 lit = inScatter(p, rayDir, g, first, last);
      if (uniformVolume) lit += ambient;
      light += transmittance * sigma * lit * dt * gain;
      transmittance *= exp(-density * extinction * dt);
    }
  }
  outLight = vec4(light, sceneDist);
  outTransmit = vec4(transmittance, 1.0);
}
`;

/**
 * Full-resolution composite: each pixel blends the four nearest march texels,
 * bilinearly, but only those that marched to about the same depth, so haze
 * from the far wall never bleeds onto a railing in front of it.
 */
const HAZE_COMPOSITE = /* glsl */ `
uniform sampler2D hazeLight;
uniform sampler2D hazeTransmit;
uniform vec4 hazeSize;   // march size, 1 / size
uniform mat4 projectionInverse;

void mainImage(const in vec4 inputColor, const in vec2 uv, const in float depth, out vec4 outputColor) {
  vec4 view = projectionInverse * vec4(vec3(uv, depth) * 2.0 - 1.0, 1.0);
  float dist = depth >= 0.9999 ? 200.0 : length(view.xyz / view.w);
  vec2 p = uv * hazeSize.xy - 0.5;
  vec2 f = fract(p);
  ivec2 base = ivec2(floor(p));
  ivec2 edge = ivec2(hazeSize.xy) - 1;
  vec3 light = vec3(0.0);
  vec3 transmit = vec3(0.0);
  float total = 0.0;
  float bestDiff = 1e9;
  vec3 bestLight = vec3(0.0);
  vec3 bestTransmit = vec3(1.0);
  for (int i = 0; i < 4; i++) {
    ivec2 offset = ivec2(i & 1, i >> 1);
    ivec2 texel = clamp(base + offset, ivec2(0), edge);
    vec4 l = texelFetch(hazeLight, texel, 0);
    vec3 t = texelFetch(hazeTransmit, texel, 0).rgb;
    float diff = abs(l.a - dist) / max(dist, 1e-3);
    vec2 bilinear = mix(1.0 - f, f, vec2(offset));
    float w = bilinear.x * bilinear.y * exp(-diff * diff * 400.0);
    light += l.rgb * w;
    transmit += t * w;
    total += w;
    if (diff < bestDiff) {
      bestDiff = diff;
      bestLight = l.rgb;
      bestTransmit = t;
    }
  }
  if (total > 1e-3) {
    light /= total;
    transmit /= total;
  } else {
    light = bestLight;
    transmit = bestTransmit;
  }
  outputColor = vec4(inputColor.rgb * transmit + light, inputColor.a);
}
`;

/* ------------------------------------------------------- spot shadows --- */

export const SHADOW_FAR = 60;
const SHADOW_TILE = 512;

/** Distance-to-light maps for the spots, rendered once (the cave is static). */
export type SpotShadows = { target: THREE.WebGLRenderTarget; matrices: THREE.Matrix4[]; tiles: number };

export function renderSpotShadows(renderer: THREE.WebGLRenderer, scene: THREE.Object3D, lights: CaveLight[]): SpotShadows | null {
  const spots = hazeLightList(lights)
    .filter(casts)
    .slice(0, MAX_SHADOWED_SPOTS);
  if (!spots.length) return null;
  const tiles = spots.length;
  const target = new THREE.WebGLRenderTarget(SHADOW_TILE * tiles, SHADOW_TILE, {
    type: THREE.HalfFloatType,
    format: THREE.RGBAFormat,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    depthBuffer: true,
  });
  const material = new THREE.ShaderMaterial({
    side: THREE.DoubleSide,
    uniforms: { lightPosition: { value: new THREE.Vector3() }, far: { value: SHADOW_FAR } },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 lightPosition;
      uniform float far;
      varying vec3 vWorld;
      void main() { gl_FragColor = vec4(length(vWorld - lightPosition) / far, 0.0, 0.0, 1.0); }`,
  });
  const holder = new THREE.Scene();
  const parent = scene.parent;
  holder.add(scene);
  holder.overrideMaterial = material;
  const previousTarget = renderer.getRenderTarget();
  const previousClear = renderer.getClearColor(new THREE.Color());
  const previousAlpha = renderer.getClearAlpha();
  renderer.setRenderTarget(target);
  renderer.setClearColor(0xffffff, 1);
  renderer.clear();
  const matrices: THREE.Matrix4[] = [];
  spots.forEach((spot, i) => {
    const fov = spot.type === "SPOT" ? THREE.MathUtils.radToDeg(spot.angle ?? 1) + 4 : 140;
    const cam = new THREE.PerspectiveCamera(fov, 1, 0.1, SHADOW_FAR);
    cam.position.set(...spot.position);
    const up = Math.abs(spot.direction[1]) > 0.99 ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(0, 1, 0);
    cam.up.copy(up);
    cam.lookAt(spot.position[0] + spot.direction[0], spot.position[1] + spot.direction[1], spot.position[2] + spot.direction[2]);
    cam.updateMatrixWorld(true);
    material.uniforms.lightPosition.value.set(...spot.position);
    target.viewport.set(i * SHADOW_TILE, 0, SHADOW_TILE, SHADOW_TILE);
    target.scissor.set(i * SHADOW_TILE, 0, SHADOW_TILE, SHADOW_TILE);
    target.scissorTest = true;
    renderer.setRenderTarget(target);
    renderer.render(holder, cam);
    matrices.push(new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
  });
  target.scissorTest = false;
  renderer.setRenderTarget(previousTarget);
  renderer.setClearColor(previousClear, previousAlpha);
  holder.overrideMaterial = null;
  if (parent) parent.add(scene);
  while (matrices.length < MAX_SHADOWED_SPOTS) matrices.push(new THREE.Matrix4());
  return { target, matrices, tiles };
}
