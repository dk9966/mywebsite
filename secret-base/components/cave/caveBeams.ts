import * as THREE from "three";
import { Effect, EffectAttribute } from "postprocessing";
import type { CaveMist } from "./caveAssets";
import { MAX_SHADOWS, SHADOW_FAR, type PackedLights, type SurfaceShadows } from "./caveLighting";

/**
 * Spotlight beams without the full haze march. Only two of the Cycles mists
 * are kept: the cave-wide uniform volume ("dry cave volume") and each spot's
 * own "soft local beam mist". Per pixel:
 *
 *   - the uniform volume's veil (extinction) and its ambient glow have a
 *     closed form along the ray, no march;
 *   - for each spot, the ray is clipped to the spot's cone analytically and
 *     only that stretch is marched, a few steps, through both mists, with the
 *     surface shadow maps so beams stop at the decks.
 *
 * Pixels outside every cone cost six ray-cone tests. Same units and `gain`
 * as `HazeEffect` (intensity P/4π, scattering density × colour, HG phase);
 * the dense chasm mists, lit mostly by the area fills, are what it leaves out.
 */

const MAX_BEAMS = 8;
const STEPS = 16;
const SHADOW_TILE = 1024;

export type BeamOptions = {
  /** Calibrated scattering gain, as for the haze. */
  gain: number;
  /** Cave-wide bounce light in the uniform volume. */
  ambient: number;
};

/** The beam mist that belongs to a spot: same "RL | Area |" prefix. */
function beamMistFor(spotName: string, mists: CaveMist[]) {
  const prefix = spotName.split(" | ").slice(0, 2).join(" | ");
  return mists.find((m) => !m.uniform && m.name.startsWith(prefix) && m.name.includes("beam mist"));
}

export class BeamEffect extends Effect {
  private readonly camera: THREE.PerspectiveCamera;
  /** Each beam's light (index into the packed lights) and full colour, and the full veil glow, for setLevels. */
  private readonly spotLights: number[];
  private readonly fullColor: THREE.Vector4[];
  private readonly fullAmbient: THREE.Vector3;

  constructor(camera: THREE.PerspectiveCamera, packed: PackedLights, shadows: SurfaceShadows | null, mists: CaveMist[], options: BeamOptions) {
    const fog = mists.find((m) => m.uniform);
    const spots = packed.lights
      .map((light, index) => ({ light, index }))
      .filter(({ light }) => light.type === "SPOT" && !light.receivers)
      .slice(0, MAX_BEAMS);

    const spotPosition = spots.map(({ light }) => new THREE.Vector3(...light.position));
    const spotAxis = spots.map(({ light }) => new THREE.Vector4(...light.direction, Math.cos((light.angle ?? 1) / 2)));
    const spotColor = spots.map(({ light }) => {
      const cosHalf = Math.cos((light.angle ?? 1) / 2);
      const k = light.power / (4 * Math.PI);
      return new THREE.Vector4(...light.color.map((c) => c * k), (1 - cosHalf) * (light.blend ?? 0));
    });
    // Shadow slot, beam-mist density, radial start, vertical edge.
    const spotMist = spots.map(({ light, index }) => {
      const m = beamMistFor(light.name, mists);
      return new THREE.Vector4(shadows ? packed.slots[index] : -1, m?.density ?? 0, m?.radialStart ?? 0, m?.edge ?? 1);
    });
    const spotMistInverse = spots.map(({ light }) => {
      const m = beamMistFor(light.name, mists);
      return m ? new THREE.Matrix4().fromArray(m.matrix).invert() : new THREE.Matrix4();
    });
    const pad = <T>(list: T[], make: () => T) => {
      while (list.length < MAX_BEAMS) list.push(make());
      return list;
    };
    const beamMist = mists.find((m) => m.name.includes("beam mist"));
    const beamColor = new THREE.Vector3(...(beamMist?.color ?? [0.62, 0.76, 0.9]));
    const scatter = new THREE.Vector3(...(fog?.color ?? [0, 0, 0])).multiplyScalar(fog?.density ?? 0);
    const extinction = scatter.clone().add(new THREE.Vector3(...(fog?.absorption ?? [0, 0, 0])).multiplyScalar(fog?.density ?? 0));

    super("BeamEffect", FRAGMENT, {
      attributes: EffectAttribute.DEPTH,
      defines: new Map([
        ["MAX_BEAMS", String(MAX_BEAMS)],
        ["MAX_SHADOWS", String(MAX_SHADOWS)],
        ["STEPS", String(STEPS)],
        ["SHADOW_TILE", SHADOW_TILE.toFixed(1)],
      ]),
      uniforms: new Map<string, THREE.Uniform>([
        ["projectionInverse", new THREE.Uniform(new THREE.Matrix4())],
        ["cameraWorld", new THREE.Uniform(new THREE.Matrix4())],
        ["spotCount", new THREE.Uniform(spots.length)],
        ["spotPosition", new THREE.Uniform(pad(spotPosition, () => new THREE.Vector3()))],
        ["spotAxis", new THREE.Uniform(pad(spotAxis, () => new THREE.Vector4()))],
        ["spotColor", new THREE.Uniform(pad(spotColor, () => new THREE.Vector4()))],
        ["spotMist", new THREE.Uniform(pad(spotMist, () => new THREE.Vector4(-1, 0, 0, 1)))],
        ["spotMistInverse", new THREE.Uniform(pad(spotMistInverse, () => new THREE.Matrix4()))],
        ["beamColor", new THREE.Uniform(beamColor)],
        ["beamAnisotropy", new THREE.Uniform(beamMist?.anisotropy ?? 0)],
        ["shadowMap", new THREE.Uniform(shadows?.target.texture ?? null)],
        ["shadowMatrix", new THREE.Uniform(shadows?.matrices ?? Array.from({ length: MAX_SHADOWS }, () => new THREE.Matrix4()))],
        ["shadowGrid", new THREE.Uniform(new THREE.Vector2(shadows?.columns ?? 1, shadows?.rows ?? 1))],
        ["shadowFar", new THREE.Uniform(SHADOW_FAR)],
        ["fogInverse", new THREE.Uniform(fog ? new THREE.Matrix4().fromArray(fog.matrix).invert() : new THREE.Matrix4())],
        ["fogScatter", new THREE.Uniform(scatter)],
        ["fogExtinction", new THREE.Uniform(extinction)],
        ["fogAnisotropy", new THREE.Uniform(fog?.anisotropy ?? 0)],
        // Same cool bounce tint as the haze's ambient term.
        ["fogAmbient", new THREE.Uniform(new THREE.Vector3(0.55, 0.75, 1).multiplyScalar(options.ambient))],
        ["gain", new THREE.Uniform(options.gain)],
      ]),
    });
    this.camera = camera;
    this.spotLights = spots.map(({ index }) => index);
    this.fullColor = spotColor.slice(0, spots.length).map((c) => c.clone());
    this.fullAmbient = this.uniforms.get("fogAmbient")!.value.clone();
  }

  /** Dims the beams with their lights (per packed light) and the veil's bounce glow with the cave's overall level. */
  setLevels(gains: Float32Array, overall: number) {
    const color = this.uniforms.get("spotColor")!.value as THREE.Vector4[];
    this.spotLights.forEach((light, k) => {
      const full = this.fullColor[k];
      color[k].set(full.x * gains[light], full.y * gains[light], full.z * gains[light], full.w);
    });
    this.uniforms.get("fogAmbient")!.value.copy(this.fullAmbient).multiplyScalar(overall);
  }

  update() {
    this.uniforms.get("projectionInverse")!.value.copy(this.camera.projectionMatrixInverse);
    this.uniforms.get("cameraWorld")!.value.copy(this.camera.matrixWorld);
  }
}

const FRAGMENT = /* glsl */ `
uniform mat4 projectionInverse;
uniform mat4 cameraWorld;
uniform int spotCount;
uniform vec3 spotPosition[MAX_BEAMS];
uniform vec4 spotAxis[MAX_BEAMS];     // direction, cos(half angle)
uniform vec4 spotColor[MAX_BEAMS];    // colour × P/4π, smooth width
uniform vec4 spotMist[MAX_BEAMS];     // shadow slot, beam-mist density, radial start, edge
uniform mat4 spotMistInverse[MAX_BEAMS];
uniform vec3 beamColor;
uniform float beamAnisotropy;
uniform sampler2D shadowMap;
uniform mat4 shadowMatrix[MAX_SHADOWS];
uniform vec2 shadowGrid;
uniform float shadowFar;
uniform mat4 fogInverse;
uniform vec3 fogScatter;
uniform vec3 fogExtinction;
uniform float fogAnisotropy;
uniform vec3 fogAmbient;
uniform float gain;

float smootherstep01(float x) {
  x = clamp(x, 0.0, 1.0);
  return x * x * x * (x * (x * 6.0 - 15.0) + 10.0);
}

// Ray vs a unit cube (-0.5..0.5) given its inverse matrix: [enter, exit].
vec2 boxSpan(mat4 inverseMatrix, vec3 origin, vec3 dir) {
  vec3 o = (inverseMatrix * vec4(origin, 1.0)).xyz;
  vec3 d = (inverseMatrix * vec4(dir, 0.0)).xyz;
  vec3 inv = 1.0 / d;
  vec3 t0 = (-0.5 - o) * inv;
  vec3 t1 = (0.5 - o) * inv;
  vec3 lo = min(t0, t1);
  vec3 hi = max(t0, t1);
  return vec2(max(max(max(lo.x, lo.y), lo.z), 0.0), min(min(hi.x, hi.y), hi.z));
}

// The beam mist's node graph: radial smootherstep fade, soft top/bottom.
float beamDensity(int k, vec3 p) {
  vec4 m = spotMist[k];
  if (m.y <= 0.0) return 0.0;
  vec3 g = (spotMistInverse[k] * vec4(p, 1.0)).xyz + 0.5;
  if (any(lessThan(g, vec3(0.0))) || any(greaterThan(g, vec3(1.0)))) return 0.0;
  float radial = 1.0 - smootherstep01((length((g.xy - 0.5) * 2.0) - m.z) / (1.0 - m.z));
  float vertical = smootherstep01(min(g.z, 1.0 - g.z) / m.w);
  return m.y * radial * vertical;
}

float beamShadow(int slot, vec3 p, vec3 lightPosition) {
  if (slot < 0) return 1.0;
  vec4 clip = shadowMatrix[slot] * vec4(p, 1.0);
  if (clip.w <= 0.0) return 1.0;
  vec2 local = clip.xy / clip.w * 0.5 + 0.5;
  if (any(lessThan(local, vec2(0.0))) || any(greaterThan(local, vec2(1.0)))) return 1.0;
  vec2 tile = vec2(mod(float(slot), shadowGrid.x), floor(float(slot) / shadowGrid.x));
  float stored = texture2D(shadowMap, (tile + local) / shadowGrid).r * shadowFar;
  return step(length(p - lightPosition), stored + 0.15);
}

float henyeyGreenstein(float g, float cosT) {
  return (1.0 - g * g) / (12.566370614 * pow(max(1.0 + g * g + 2.0 * g * cosT, 1e-4), 1.5));
}

bool insideCone(vec3 fromApex, vec3 axis, float cos2) {
  float h = dot(fromApex, axis);
  return h > 0.0 && h * h >= dot(fromApex, fromApex) * cos2;
}

float ign(vec2 px) {
  return fract(52.9829189 * fract(dot(px, vec2(0.06711056, 0.00583715))));
}

void mainImage(const in vec4 inputColor, const in vec2 uv, const in float depth, out vec4 outputColor) {
  vec4 view = projectionInverse * vec4(vec3(uv, depth) * 2.0 - 1.0, 1.0);
  view /= view.w;
  vec3 origin = cameraWorld[3].xyz;
  vec3 target = (cameraWorld * vec4(view.xyz, 1.0)).xyz;
  float sceneDist = depth >= 0.9999 ? 200.0 : length(target - origin);
  vec3 dir = normalize(target - origin);

  // Uniform volume: veil and ambient glow in closed form.
  vec2 fog = boxSpan(fogInverse, origin, dir);
  fog.y = min(fog.y, sceneDist);
  float fogLength = max(fog.y - fog.x, 0.0);
  vec3 transmit = exp(-fogExtinction * fogLength);
  vec3 light = fogScatter * fogAmbient * gain * (1.0 - transmit) / max(fogExtinction, vec3(1e-6));

  float jitter = ign(gl_FragCoord.xy);
  for (int k = 0; k < MAX_BEAMS; k++) {
    if (k >= spotCount) break;
    vec3 apex = spotPosition[k];
    vec3 axis = spotAxis[k].xyz;
    float cosHalf = spotAxis[k].w;
    float cos2 = cosHalf * cosHalf;
    // Ray vs the cone's forward nappe (convex: one span), clipped to the scene.
    vec3 co = origin - apex;
    float da = dot(dir, axis);
    float ca = dot(co, axis);
    float A = da * da - cos2;
    float B = 2.0 * (da * ca - dot(dir, co) * cos2);
    float C = ca * ca - dot(co, co) * cos2;
    float near = 0.0;
    float far = sceneDist;
    float r0 = far;
    float r1 = far;
    float disc = B * B - 4.0 * A * C;
    if (abs(A) > 1e-6 && disc >= 0.0) {
      float s = sqrt(disc);
      r0 = (-B - s) / (2.0 * A);
      r1 = (-B + s) / (2.0 * A);
      if (r0 > r1) { float tmp = r0; r0 = r1; r1 = tmp; }
    } else if (abs(A) <= 1e-6 && abs(B) > 1e-6) {
      r0 = r1 = -C / B;
    }
    float cuts[4] = float[](near, clamp(r0, near, far), clamp(r1, near, far), far);
    float lo = 1e9;
    float hi = -1e9;
    for (int c = 0; c < 3; c++) {
      if (cuts[c + 1] - cuts[c] < 1e-4) continue;
      if (insideCone(co + dir * (0.5 * (cuts[c] + cuts[c + 1])), axis, cos2)) {
        lo = min(lo, cuts[c]);
        hi = max(hi, cuts[c + 1]);
      }
    }
    if (hi <= lo) continue;

    int slot = int(spotMist[k].x + 0.5) - (spotMist[k].x < -0.5 ? 1 : 0);
    float dt = (hi - lo) / float(STEPS);
    vec3 beam = vec3(0.0);
    for (int s = 0; s < STEPS; s++) {
      float t = lo + (float(s) + jitter) * dt;
      vec3 p = origin + dir * t;
      vec3 toLight = apex - p;
      float d2 = max(dot(toLight, toLight), 0.0625);
      vec3 l = toLight * inversesqrt(d2);
      float edge = dot(-l, axis) - cosHalf;
      if (edge <= 0.0) continue;
      float att = spotColor[k].w > 0.0 ? smoothstep(0.0, spotColor[k].w, edge) : 1.0;
      att *= beamShadow(slot, p, apex);
      if (att <= 0.0) continue;
      float cosT = dot(l, -dir);
      float local = beamDensity(k, p);
      vec3 sigma = fogScatter * henyeyGreenstein(fogAnisotropy, cosT) + local * beamColor * henyeyGreenstein(beamAnisotropy, cosT);
      // Veil between the camera and this sample (uniform volume only).
      vec3 veil = exp(-fogExtinction * clamp(t - fog.x, 0.0, fogLength));
      beam += veil * sigma * (att / d2);
    }
    light += beam * spotColor[k].rgb * dt * gain;
  }
  outputColor = vec4(inputColor.rgb * transmit + light, inputColor.a);
}
`;
