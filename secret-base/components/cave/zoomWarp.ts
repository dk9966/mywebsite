import * as THREE from "three";
import type { CaveManifest } from "./caveAssets";

/**
 * Re-projects finished cave frames to a nearby camera, for the orbiting
 * zooms (see caveZoom.ts). Each keyframe keeps its colour (the canvas, after
 * every post effect), its depth and the camera it was rendered from. Drawing
 * it from another camera lifts a grid, one vertex per 2×2 pixels, back into
 * the world and projects it again; triangles torn
 * across depth edges (disocclusions) stretch, and are marked unreliable so
 * the other keyframe fills them in.
 */

/** View distance written where nothing was drawn. */
const DEPTH_FAR = 500;
/** Unreliable below this many source texels per screen pixel (by area); a torn triangle covers far more pixels than texels. */
const STRETCH_LOW = 0.04;
const STRETCH_HIGH = 0.2;
/**
 * Titles claim their lettering and the glow band their distance field
 * stores round it (the field's value there falls toward 0), so the glow moves
 * with the letters while the wall between them keeps its own depth.
 */
const TITLE_FIELD_MIN = 0.02;
const MAX_TITLES = 8;

/** Red: view distance; green: which title (1-based, 0 = none) the pixel belongs to. */
export type DepthFrame = {
  target: THREE.WebGLRenderTarget;
  projection: THREE.Matrix4;
  projectionInverse: THREE.Matrix4;
  world: THREE.Matrix4;
  viewProjection: THREE.Matrix4;
};

/** A keyframe as the warp needs it. */
export type WarpSource = { texture: THREE.Texture | null; depth: DepthFrame | null };

const DEPTH_VERTEX = /* glsl */ `
  varying float vDepth;
  void main() {
    vec4 view = modelViewMatrix * vec4(position, 1.0);
    vDepth = -view.z;
    gl_Position = projectionMatrix * view;
  }
`;

const DEPTH_FRAGMENT = /* glsl */ `
  varying float vDepth;
  void main() {
    gl_FragColor = vec4(vDepth, 0.0, 0.0, 1.0);
  }
`;

/** CaveLabels' billboard (same vertex placement), tagged with its title. */
const TITLE_DEPTH_VERTEX = /* glsl */ `
  uniform vec2 uSize;
  varying vec2 vUv;
  varying float vDepth;
  void main() {
    vUv = uv;
    vec4 centre = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
    centre.xy += position.xy * uSize;
    vDepth = -centre.z;
    gl_Position = projectionMatrix * centre;
  }
`;

const TITLE_DEPTH_FRAGMENT = /* glsl */ `
  uniform sampler2D uField;
  uniform float uTitle;
  varying vec2 vUv;
  varying float vDepth;
  void main() {
    if (texture2D(uField, vUv).r < ${TITLE_FIELD_MIN}) discard;
    gl_FragColor = vec4(vDepth, uTitle, 0.0, 1.0);
  }
`;

/**
 * Keeps the nearest of each 2×2 block of the full-resolution depth (and which
 * title it is): a railing one pixel wide keeps its own depth instead of
 * taking the wall's behind it, and a keyframe stores a quarter of the pixels.
 */
const REDUCE_FRAGMENT = /* glsl */ `
  uniform sampler2D uDepth;
  vec2 nearer(vec2 a, vec2 b) { return b.r < a.r ? b : a; }
  void main() {
    ivec2 last = textureSize(uDepth, 0) - 1;
    ivec2 p = ivec2(gl_FragCoord.xy) * 2;
    gl_FragColor = vec4(nearer(
      nearer(texelFetch(uDepth, min(p, last), 0).rg, texelFetch(uDepth, min(p + ivec2(1, 0), last), 0).rg),
      nearer(texelFetch(uDepth, min(p + ivec2(0, 1), last), 0).rg, texelFetch(uDepth, min(p + ivec2(1, 1), last), 0).rg)
    ), 0.0, 1.0);
  }
`;

/**
 * One vertex per 2×2 source pixels, at that block's nearest depth.
 *
 * Titles are billboards: they always face the camera, so a title's pixels do
 * not move as the flat plane they were in the keyframe (which turns away as
 * the camera orbits) but stay flat on screen around the title's centre,
 * scaled with its distance and the lens.
 */
const WARP_VERTEX = /* glsl */ `
  uniform sampler2D uDepth;
  uniform mat4 uSourceProjectionInverse;
  uniform mat4 uSourceWorld;
  uniform mat4 uSourceViewProjection;
  uniform mat4 uViewProjection;
  uniform vec2 uFocalRatio;
  uniform vec3 uTitles[${MAX_TITLES}];
  varying vec2 vUv;
  void main() {
    vUv = position.xy;
    vec2 texel = texelFetch(uDepth, ivec2(vUv * vec2(textureSize(uDepth, 0) - 1) + 0.5), 0).rg;
    float depth = texel.r;
    int title = int(texel.g + 0.5);
    if (title > 0) {
      vec4 centre = vec4(uTitles[title - 1], 1.0);
      vec4 from = uSourceViewProjection * centre;
      vec4 to = uViewProjection * centre;
      vec2 offset = (vUv * 2.0 - 1.0 - from.xy / from.w) * uFocalRatio * (from.w / to.w);
      gl_Position = vec4((to.xy / to.w + offset) * to.w, to.z, to.w);
      return;
    }
    vec4 near = uSourceProjectionInverse * vec4(vUv * 2.0 - 1.0, -1.0, 1.0);
    vec3 ray = near.xyz / near.w;
    vec3 view = ray / -ray.z * depth;
    gl_Position = uViewProjection * uSourceWorld * vec4(view, 1.0);
  }
`;

const WARP_FRAGMENT = /* glsl */ `
  uniform sampler2D uColor;
  uniform vec2 uColorSize;
  varying vec2 vUv;
  void main() {
    vec2 p = vUv * uColorSize;
    vec2 dx = dFdx(p);
    vec2 dy = dFdy(p);
    float texels = abs(dx.x * dy.y - dx.y * dy.x);
    gl_FragColor = vec4(texture2D(uColor, vUv).rgb, smoothstep(${STRETCH_LOW}, ${STRETCH_HIGH}, texels));
  }
`;

const COMPOSITE_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

/** Each keyframe weighted by how far along the segment we are and how reliable its pixel is. */
const COMPOSITE_FRAGMENT = /* glsl */ `
  uniform sampler2D uA;
  uniform sampler2D uB;
  uniform float uMix;
  varying vec2 vUv;
  void main() {
    vec4 a = texture2D(uA, vUv);
    vec4 b = texture2D(uB, vUv);
    float wa = a.a * (1.0 - uMix);
    float wb = b.a * uMix;
    float w = wa + wb;
    vec3 colour = w > 1e-3 ? (a.rgb * wa + b.rgb * wb) / w : mix(a.rgb, b.rgb, uMix);
    gl_FragColor = vec4(colour, 1.0);
  }
`;

export class ZoomWarp {
  private readonly gl: THREE.WebGLRenderer;
  private readonly depthMaterial = new THREE.ShaderMaterial({ vertexShader: DEPTH_VERTEX, fragmentShader: DEPTH_FRAGMENT, side: THREE.DoubleSide });
  private readonly hole: THREE.Mesh;
  private readonly warpMaterial: THREE.ShaderMaterial;
  private readonly composite: THREE.ShaderMaterial;
  private readonly gridScene = new THREE.Scene();
  private readonly grid: THREE.Mesh;
  private readonly quadScene = new THREE.Scene();
  private readonly quadCamera = new THREE.OrthographicCamera();
  private readonly titleMaterials = new Map<THREE.Mesh, THREE.ShaderMaterial>();
  /** World centre of each title, by its id - 1 in the depth frames. */
  private readonly titleCentres = Array.from({ length: MAX_TITLES }, () => new THREE.Vector3());
  private targets: [THREE.WebGLRenderTarget, THREE.WebGLRenderTarget] | null = null;
  private composited = false;
  /** Full-resolution depth, rendered here and reduced into each keyframe's. */
  private scratch: THREE.WebGLRenderTarget | null = null;
  private readonly reduce = new THREE.ShaderMaterial({
    vertexShader: COMPOSITE_VERTEX,
    fragmentShader: REDUCE_FRAGMENT,
    uniforms: { uDepth: { value: null } },
    blending: THREE.NoBlending,
    depthTest: false,
    depthWrite: false,
  });
  private size = new THREE.Vector2();
  private readonly viewProjection = new THREE.Matrix4();
  private readonly clear = new THREE.Color();

  constructor(gl: THREE.WebGLRenderer, hole: CaveManifest["hole"]) {
    this.gl = gl;
    // The voxel box is not part of the cave model: stand a plane in for it,
    // halfway into the hole, so the room behind the rim moves at about its depth.
    this.hole = new THREE.Mesh(new THREE.PlaneGeometry(hole.width, hole.height), this.depthMaterial);
    const right = new THREE.Vector3(...hole.right);
    const up = new THREE.Vector3(...hole.up);
    const into = new THREE.Vector3(...hole.into);
    this.hole.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, into.clone().negate()));
    this.hole.position.set(...hole.origin).addScaledVector(into, hole.depth / 2);
    this.hole.updateMatrixWorld();

    this.warpMaterial = new THREE.ShaderMaterial({
      vertexShader: WARP_VERTEX,
      fragmentShader: WARP_FRAGMENT,
      uniforms: {
        uDepth: { value: null },
        uColor: { value: null },
        uColorSize: { value: new THREE.Vector2() },
        uSourceProjectionInverse: { value: new THREE.Matrix4() },
        uSourceWorld: { value: new THREE.Matrix4() },
        uSourceViewProjection: { value: new THREE.Matrix4() },
        uViewProjection: { value: new THREE.Matrix4() },
        uFocalRatio: { value: new THREE.Vector2() },
        uTitles: { value: Array.from({ length: MAX_TITLES }, () => new THREE.Vector3()) },
      },
      blending: THREE.NoBlending,
      side: THREE.DoubleSide,
    });
    this.grid = new THREE.Mesh(new THREE.BufferGeometry(), this.warpMaterial);
    this.grid.frustumCulled = false;
    this.gridScene.add(this.grid);

    this.composite = new THREE.ShaderMaterial({
      vertexShader: COMPOSITE_VERTEX,
      fragmentShader: COMPOSITE_FRAGMENT,
      uniforms: { uA: { value: null }, uB: { value: null }, uMix: { value: 0 } },
      blending: THREE.NoBlending,
      depthTest: false,
      depthWrite: false,
    });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.composite);
    quad.frustumCulled = false;
    this.quadScene.add(quad);
  }

  /** Drawing-buffer size: the grid and the two re-projection targets follow it. */
  resize(width: number, height: number) {
    if (this.size.x === width && this.size.y === height) return;
    this.size.set(width, height);
    this.targets?.forEach((t) => t.dispose());
    this.targets = null;
    this.composited = false;
    this.scratch?.dispose();
    this.scratch = null;
    const [cols, rows] = this.gridSize();
    const positions = new Float32Array(cols * rows * 3);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const o = (j * cols + i) * 3;
        positions[o] = i / (cols - 1);
        positions[o + 1] = j / (rows - 1);
      }
    }
    const index = new Uint32Array((cols - 1) * (rows - 1) * 6);
    let k = 0;
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        const a = j * cols + i;
        index.set([a, a + 1, a + cols, a + 1, a + cols + 1, a + cols], k);
        k += 6;
      }
    }
    this.grid.geometry.dispose();
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(index, 1));
    this.grid.geometry = geometry;
  }

  /** Grid vertices: one per 2×2 pixels. */
  private gridSize(): [number, number] {
    return [Math.max(2, Math.ceil(this.size.x / 2)), Math.max(2, Math.ceil(this.size.y / 2))];
  }

  /**
   * The view distance of everything the camera sees: the cave model, the
   * section titles and the stand-in for the voxel box. `frame` is reused if given.
   */
  renderDepth(camera: THREE.PerspectiveCamera, model: THREE.Object3D, titles: THREE.Mesh[], frame: DepthFrame | null): DepthFrame {
    const depthTarget = (w: number, h: number, depthBuffer: boolean) =>
      new THREE.WebGLRenderTarget(w, h, {
        type: THREE.HalfFloatType,
        format: THREE.RGFormat,
        minFilter: THREE.NearestFilter,
        magFilter: THREE.NearestFilter,
        depthBuffer,
      });
    this.scratch ??= depthTarget(this.size.x, this.size.y, true);
    const [w, h] = this.gridSize();
    let target = frame?.target;
    if (!target || target.width !== w || target.height !== h) {
      target?.dispose();
      target = depthTarget(w, h, false);
    }
    const gl = this.gl;
    const saved = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
    model.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      saved.set(mesh, mesh.material);
      mesh.material = this.depthMaterial;
    });
    const clear = gl.getClearColor(this.clear).clone();
    const alpha = gl.getClearAlpha();
    gl.setRenderTarget(this.scratch);
    gl.setClearColor(new THREE.Color(DEPTH_FAR, 0, 0), 1);
    gl.clear();
    gl.render(model, camera);
    for (const [mesh, material] of saved) mesh.material = material;
    gl.render(this.hole, camera);
    titles.slice(0, MAX_TITLES).forEach((title, i) => {
      this.titleCentres[i].copy(title.position);
      if (!title.visible) return;
      const original = title.material;
      title.material = this.titleMaterial(title, i + 1);
      gl.render(title, camera);
      title.material = original;
    });
    this.reduce.uniforms.uDepth.value = this.scratch.texture;
    const quad = this.quadScene.children[0] as THREE.Mesh;
    quad.material = this.reduce;
    gl.setRenderTarget(target);
    gl.render(this.quadScene, this.quadCamera);
    quad.material = this.composite;
    gl.setRenderTarget(null);
    gl.setClearColor(clear, alpha);
    camera.updateMatrixWorld();
    return {
      target,
      projection: camera.projectionMatrix.clone(),
      projectionInverse: camera.projectionMatrixInverse.clone(),
      world: camera.matrixWorld.clone(),
      viewProjection: camera.projectionMatrix.clone().multiply(camera.matrixWorldInverse),
    };
  }

  private titleMaterial(title: THREE.Mesh, id: number): THREE.ShaderMaterial {
    let material = this.titleMaterials.get(title);
    if (!material) {
      const source = (title.material as THREE.ShaderMaterial).uniforms;
      material = new THREE.ShaderMaterial({
        vertexShader: TITLE_DEPTH_VERTEX,
        fragmentShader: TITLE_DEPTH_FRAGMENT,
        // Shared uniform objects: the title's live size and field.
        uniforms: { uSize: source.uSize, uField: source.uField, uTitle: { value: id } },
      });
      this.titleMaterials.set(title, material);
    }
    return material;
  }

  /**
   * Re-projects `source` once, off screen. The first time compiles the warp
   * and uploads its grid (a few hundred ms), and every keyframe's textures
   * cost tens of ms on some drivers the first time they are sampled: idle-time
   * work, so no zoom pays for it.
   */
  warm(camera: THREE.PerspectiveCamera, source: WarpSource) {
    this.warpInto(0, camera, source);
    if (!this.composited) {
      this.composited = true;
      this.composite.uniforms.uA.value = this.targets![0].texture;
      this.composite.uniforms.uB.value = this.targets![0].texture;
      this.gl.setRenderTarget(this.targets![1]);
      this.gl.render(this.quadScene, this.quadCamera);
    }
    this.gl.setRenderTarget(null);
  }

  /** Draws keyframes `a` and `b` as seen from `camera`, `mix` of the way from a to b, to the canvas. */
  draw(camera: THREE.PerspectiveCamera, a: WarpSource, b: WarpSource, mix: number) {
    const sources = mix <= 0 ? [a] : mix >= 1 ? [b] : [a, b];
    sources.forEach((source, i) => this.warpInto(i, camera, source));
    const u = this.composite.uniforms;
    u.uA.value = this.targets![0].texture;
    u.uB.value = this.targets![sources.length - 1].texture;
    u.uMix.value = sources.length === 1 ? 0 : mix;
    this.gl.setRenderTarget(null);
    this.gl.render(this.quadScene, this.quadCamera);
  }

  /** `source` re-projected to `camera`, into target `i` (alpha: how reliable each pixel is). */
  private warpInto(i: number, camera: THREE.PerspectiveCamera, source: WarpSource) {
    const gl = this.gl;
    if (!this.targets) {
      const options = { depthBuffer: true, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter };
      this.targets = [
        new THREE.WebGLRenderTarget(this.size.x, this.size.y, options),
        new THREE.WebGLRenderTarget(this.size.x, this.size.y, options),
      ];
    }
    camera.updateMatrixWorld();
    this.viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const clear = gl.getClearColor(this.clear).clone();
    const alpha = gl.getClearAlpha();
    gl.setClearColor(0x000000, 0);
    gl.setRenderTarget(this.targets[i]);
    gl.clear();
    gl.setClearColor(clear, alpha);
    if (!source.texture || !source.depth) return;
    const u = this.warpMaterial.uniforms;
    u.uDepth.value = source.depth.target.texture;
    u.uColor.value = source.texture;
    u.uColorSize.value.copy(this.size);
    u.uSourceProjectionInverse.value.copy(source.depth.projectionInverse);
    u.uSourceWorld.value.copy(source.depth.world);
    u.uSourceViewProjection.value.copy(source.depth.viewProjection);
    u.uViewProjection.value.copy(this.viewProjection);
    const from = source.depth.projection.elements;
    const to = camera.projectionMatrix.elements;
    u.uFocalRatio.value.set(to[0] / from[0], to[5] / from[5]);
    u.uTitles.value.forEach((v: THREE.Vector3, k: number) => v.copy(this.titleCentres[k]));
    gl.render(this.gridScene, this.quadCamera);
  }

  dispose() {
    this.targets?.forEach((t) => t.dispose());
    this.scratch?.dispose();
    this.reduce.dispose();
    this.grid.geometry.dispose();
    this.hole.geometry.dispose();
    this.depthMaterial.dispose();
    this.warpMaterial.dispose();
    this.composite.dispose();
    for (const material of this.titleMaterials.values()) material.dispose();
    (this.quadScene.children[0] as THREE.Mesh).geometry.dispose();
  }
}
