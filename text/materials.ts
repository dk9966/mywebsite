import * as THREE from "three";
import type { FillId, WordStyle } from "./store";

// Holographic fills. Every fill is unlit (shader-only), so the scene needs no
// lights or environment map. One ShaderMaterial serves both TextGeometry
// groups (caps + extruded sides); the shader tells them apart by object-space
// normal and blends the Face / Sides colors.

/** Palette applied when a fill is picked; the colour pickers can still override. */
export const FILL_PRESETS: Record<FillId, { faceColor: string; sideColor: string; accentColor: string }> = {
  tron: { faceColor: "#2fd8ff", sideColor: "#062a36", accentColor: "#ffffff" },
  scanline: { faceColor: "#7ff6ff", sideColor: "#1a6a78", accentColor: "#c9fdff" },
  rainbow: { faceColor: "#ffffff", sideColor: "#3a2a66", accentColor: "#ffffff" },
  prism: { faceColor: "#ffffff", sideColor: "#223355", accentColor: "#8fe8ff" },
  glitch: { faceColor: "#4ff0ff", sideColor: "#0b4a5a", accentColor: "#ff2bd6" },
  grid: { faceColor: "#66f0f0", sideColor: "#1a6a78", accentColor: "#bffcff" },
  ghost: { faceColor: "#bfeaff", sideColor: "#3a6a9a", accentColor: "#7fe0ff" },
  aurora: { faceColor: "#19ffb0", sideColor: "#5a2bff", accentColor: "#ff4fd8" },
  datastream: { faceColor: "#c8ffe0", sideColor: "#0f5a3a", accentColor: "#3dff8a" },
  neon: { faceColor: "#e8f6f8", sideColor: "#2a6f7a", accentColor: "#66f0f0" },
  wireframe: { faceColor: "#66f0f0", sideColor: "#1a6a78", accentColor: "#66f0f0" },
};

/** Which panel controls mean something for a fill. */
export const FILL_USES: Record<FillId, { accent: string | null; fx: boolean; tron?: boolean }> = {
  tron: { accent: null, fx: false, tron: true },
  scanline: { accent: "Rim", fx: true },
  rainbow: { accent: "Glint", fx: true },
  prism: { accent: "Rim", fx: true },
  glitch: { accent: "Glitch", fx: true },
  grid: { accent: "Rim", fx: true },
  ghost: { accent: "Rim / sweep", fx: true },
  aurora: { accent: "Aurora B", fx: true },
  datastream: { accent: "Stream", fx: true },
  neon: { accent: null, fx: false },
  wireframe: { accent: null, fx: false },
};

const VERTEX = /* glsl */ `
  uniform float time;
  uniform float uGlitch;
  uniform float uUnit;
  varying vec3 vNormalV;
  varying vec3 vNormalO;
  varying vec3 vViewPos;
  varying vec3 vPos;
  varying vec3 vWorld;
  float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
  }
  void main() {
    vec3 p = position;
    if (uGlitch > 0.5) {
      // Whole horizontal bands slip sideways in short bursts.
      float t = floor(time * 8.0);
      float band = floor(p.y * 6.0 / uUnit);
      float burst = step(0.78, hash11(t * 3.3));
      p.x += (hash11(band * 13.7 + t * 7.1) - 0.5) * 0.4 * uUnit * burst * step(0.4, hash11(band + t));
    }
    vPos = p;
    vNormalO = normal;
    vNormalV = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vViewPos = -mv.xyz;
    vWorld = (modelMatrix * vec4(p, 1.0)).xyz;
    gl_Position = projectionMatrix * mv;
  }
`;

const frag = (body: string) => /* glsl */ `
  uniform float time;
  uniform vec3 cFace;
  uniform vec3 cSide;
  uniform vec3 cAccent;
  uniform float uGlow;
  uniform float uScale;
  uniform float uSpeed;
  uniform float uUnit;
  uniform vec4 uBox; // minX, maxX, minY, maxY of the geometry
  varying vec3 vNormalV;
  varying vec3 vNormalO;
  varying vec3 vViewPos;
  varying vec3 vPos;
  varying vec3 vWorld;

  float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }
  vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
  }
  vec3 pal(float t) {
    return 0.5 + 0.5 * cos(6.28318 * (t + vec3(0.0, 0.33, 0.67)));
  }

  void main() {
    vec3 n = normalize(vNormalV);
    if (!gl_FrontFacing) n = -n;
    vec3 v = normalize(vViewPos);
    float ang = abs(dot(n, v));
    float fres = pow(1.0 - ang, 2.0);
    float T = time * uSpeed;
    // 0 on the flat front/back caps, 1 on the extruded walls.
    float sideness = 1.0 - abs(normalize(vNormalO).z);
    vec3 base = mix(cFace, cSide, smoothstep(0.3, 0.8, sideness));
    float xn = (vPos.x - uBox.x) / max(uBox.y - uBox.x, 1e-4);
    float yn = (vPos.y - uBox.z) / max(uBox.w - uBox.z, 1e-4);
    float k = uGlow * 0.5;
    vec3 c = vec3(0.0);
    float a = 1.0;
    ${body}
    gl_FragColor = vec4(c * k, a);
    #include <colorspace_fragment>
  }
`;

type Shaded = { fragment: string; additive: boolean; glitch?: boolean };

const SHADED: Partial<Record<FillId, Shaded>> = {
  // Classic projector hologram: rim glow, rolling scanlines, flicker.
  scanline: {
    additive: true,
    fragment: frag(`
      float scan = 0.65 + 0.35 * sin(vWorld.y * 40.0 * uScale - T * 4.0);
      float flicker = 0.93 + 0.07 * sin(T * 23.0);
      c = mix(base, cAccent, fres) * (0.3 + fres) * 2.0 * scan * flicker;
      a = clamp(0.2 + fres * 0.9, 0.0, 1.0) * scan;
    `),
  },
  // Holographic sticker foil: hue follows view angle and position.
  rainbow: {
    additive: false,
    fragment: frag(`
      float h = fract(ang * 1.2 + (xn * 0.9 + yn * 0.5) * uScale + T * 0.1);
      vec3 rain = hsv2rgb(vec3(h, 0.7, 1.0));
      float glint = pow(max(0.0, sin((xn * 5.0 + yn * 3.0) * uScale - T * 1.6)), 24.0);
      c = mix(rain, base, 0.18) * 0.9 + glint * cAccent * 1.6 + fres * rain * 0.5;
    `),
  },
  // Soft oil-slick thin film: smooth pastel interference bands.
  prism: {
    additive: false,
    fragment: frag(`
      float film = ang * 1.6 + (xn + yn) * 0.5 * uScale + sin(yn * 6.0 * uScale + T) * 0.12;
      vec3 f = 0.35 + 0.65 * pal(film);
      c = mix(f, base, 0.12) + pow(fres, 1.5) * cAccent;
    `),
  },
  // Slipping bands, dropped slices and colour flashes (vertex-displaced).
  glitch: {
    additive: false,
    glitch: true,
    fragment: frag(`
      float t = floor(T * 8.0);
      float band = floor(yn * 22.0 * uScale);
      float r = hash21(vec2(band, t));
      if (r < 0.05) discard;
      float scan = 0.85 + 0.15 * sin(vWorld.y * 90.0 * uScale);
      c = mix(base, cAccent, fres) * scan;
      if (r > 0.9) c = cAccent * 1.3;
    `),
  },
  // Glowing wire lattice drawn on the surface.
  grid: {
    additive: true,
    fragment: frag(`
      vec3 q = vPos / uUnit * 5.0 * uScale;
      vec3 g = abs(fract(q - 0.5) - 0.5) / max(fwidth(q), vec3(1e-4));
      float d = mix(min(g.x, g.y), min(min(g.x, g.y), g.z), step(0.5, sideness));
      float line = 1.0 - clamp(d / 1.3, 0.0, 1.0);
      float pulse = 0.75 + 0.25 * sin(yn * 8.0 - T * 2.0);
      c = mix(base, cAccent, fres) * (line * 2.2 * pulse + 0.12);
      a = clamp(line + 0.1 + fres * 0.4, 0.0, 1.0);
    `),
  },
  // Transparent glass ghost with a shine band sweeping across.
  ghost: {
    additive: true,
    fragment: frag(`
      float sweep = fract(T * 0.25) * 1.6 - 0.3;
      float band = smoothstep(0.1, 0.0, abs(xn * 0.7 + yn * 0.3 - sweep));
      c = base * 0.3 + cAccent * fres * 1.6 + cFace * band * 1.6;
      a = clamp(0.15 + fres * 0.85 + band, 0.0, 1.0);
    `),
  },
  // Slow flowing northern-lights gradient.
  aurora: {
    additive: false,
    fragment: frag(`
      float w = 0.5 + 0.5 * sin((xn * 3.0 * uScale + T * 0.2) * 2.0 + sin(yn * 4.0 * uScale + T * 0.7) * 1.5);
      float s = smoothstep(0.55, 0.95, 0.5 + 0.5 * sin(yn * 5.0 * uScale - T * 0.5 + xn * 2.0));
      c = mix(cFace, cAccent, w);
      c = mix(c, cSide, s * 0.8) + fres * 0.3 * cAccent;
    `),
  },
  // Falling columns of digital rain.
  datastream: {
    additive: true,
    fragment: frag(`
      float col = floor(xn * 18.0 * uScale);
      float rnd = hash21(vec2(col, 3.7));
      float head = 1.0 - fract(T * (0.15 + rnd * 0.35) + rnd * 10.0);
      float d = fract(yn - head);
      float trail = exp(-d * 4.5);
      float on = step(0.3, hash21(vec2(col, floor(yn * 30.0 * uScale) + floor(T * 6.0))));
      c = base * 0.2 + cAccent * trail * on * 1.6 + cFace * pow(trail, 8.0) * 1.5;
      a = clamp(0.14 + trail * on + fres * 0.3, 0.0, 1.0);
    `),
  },
};

const col = (hex: string, scale = 1) => new THREE.Color(hex).multiplyScalar(scale);

/**
 * Builds the [caps, sides] material pair for a word. TextGeometry puts the
 * front/back caps in group 0 and the extruded walls in group 1.
 */
export function makeMaterials(style: WordStyle, bounds: THREE.Box3): [THREE.Material, THREE.Material] {
  const { fill, faceColor, sideColor, accentColor, glow, fxScale, fxSpeed } = style;

  if (fill === "tron") {
    // The lines are drawn separately (TextScene); the body is the letter
    // interior (near-black by default, which hides the back lines) and sits
    // slightly behind them.
    const on = style.bodyFill;
    const opacity = on ? style.bodyOpacity : 1;
    const body = (scale: number) =>
      new THREE.MeshBasicMaterial({
        color: on ? col(style.bodyColor, glow * scale) : new THREE.Color(0x000000),
        transparent: opacity < 1,
        opacity,
        depthWrite: opacity > 0.5,
        polygonOffset: true,
        polygonOffsetFactor: 1,
        polygonOffsetUnits: 1,
        toneMapped: false,
      });
    // Sides a touch darker than the face so a thick extrusion still reads as 3D.
    return [body(1), body(0.6)];
  }
  if (fill === "neon") {
    return [
      new THREE.MeshBasicMaterial({ color: col(faceColor, glow), toneMapped: false }),
      new THREE.MeshBasicMaterial({ color: col(sideColor, Math.max(glow * 0.45, 0.3)), toneMapped: false }),
    ];
  }
  if (fill === "wireframe") {
    return [
      new THREE.MeshBasicMaterial({ color: col(faceColor, glow * 0.5), wireframe: true, toneMapped: false }),
      new THREE.MeshBasicMaterial({ color: col(sideColor, glow * 0.5), wireframe: true, toneMapped: false }),
    ];
  }

  const shaded = SHADED[fill]!;
  const m = new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      cFace: { value: col(faceColor) },
      cSide: { value: col(sideColor) },
      cAccent: { value: col(accentColor) },
      uGlow: { value: glow },
      uScale: { value: fxScale },
      uSpeed: { value: fxSpeed },
      uUnit: { value: style.size },
      uGlitch: { value: shaded.glitch ? 1 : 0 },
      uBox: { value: new THREE.Vector4(bounds.min.x, bounds.max.x, bounds.min.y, bounds.max.y) },
    },
    vertexShader: VERTEX,
    fragmentShader: shaded.fragment,
    transparent: shaded.additive,
    depthWrite: !shaded.additive,
    blending: shaded.additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    side: shaded.additive ? THREE.DoubleSide : THREE.FrontSide,
    toneMapped: false,
  });
  return [m, m];
}
