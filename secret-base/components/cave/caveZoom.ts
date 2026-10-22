import * as THREE from "three";
import { create } from "zustand";
import type { EffectComposer } from "postprocessing";
import type { CaveManifest, Vec3 } from "./caveAssets";
import { ZoomWarp, type DepthFrame } from "./zoomWarp";

/**
 * Click a platform to zoom in on it; Esc or the Back button zooms back out.
 *
 * A cave frame costs 50–130 ms of GPU time, far too slow to render while the
 * camera moves, so every zoom is played back from frames rendered ahead of
 * time, once, in idle time, and the scene only renders live again once the
 * camera is at rest:
 *
 * - The central platform is a lens zoom: the camera stays put and narrows its
 *   frustum onto the platform (`setViewOffset`), which is exactly a crop of
 *   the main frame. It plays back by scaling a few nested crops (no more than
 *   2× apart), each at its own resolution, so no part of the screen is ever
 *   magnified more than ~1.4×.
 * - The side platforms are orbits: the camera swings round to face each
 *   platform's open side square on, moving in as it goes. A few keyframes
 *   along the way are saved with their depth, and the two either side of the
 *   current camera are re-projected to it and blended (zoomWarp.ts), which
 *   keeps the parallax and lets the titles turn to face the camera.
 *
 * Both ends of every zoom land exactly on a native-resolution render.
 */

/** Centre of a view in its frame's coordinates (0..1, y down) and its zoom (1 = the whole frame). */
export type View = { x: number; y: number; z: number };
const FULL: View = { x: 0.5, y: 0.5, z: 1 };

/** A whole camera setup: where it stands and looks, Blender's lens shift and a crop of that frame. */
type Shot = { position: THREE.Vector3; quaternion: THREE.Quaternion; shift: [number, number]; view: View };

/** A platform's footprint in glTF metres (x, z) and the heights it spans (y). */
type Shape =
  | { kind: "circle"; centre: [number, number]; radius: number; y: [number, number] }
  | { kind: "box"; min: [number, number]; max: [number, number]; y: [number, number] };

/**
 * The four section platforms, from the collections of
 * platform-controls/cave-platform-sliders.blend (bounds in glTF space).
 * `hit` is what a click on the platform covers (supports included); `frame`
 * is what the zoom fits to the screen, together with the platform's title
 * (CaveLabels' `title-<title>` mesh). `orbit` swings the camera round to look
 * at `centre` from `facing` (degrees in the ground plane, from +x toward +z):
 * square on to the platform's open side.
 */
export const PLATFORMS: { title: string; hit: Shape; frame: Shape; orbit?: { centre: Vec3; facing: number } }[] = [
  {
    // "02 | Machined rings" disc and its underframe, the console and the panel wall above it.
    title: "Projects",
    hit: { kind: "circle", centre: [21.3, 0], radius: 5.15, y: [5, 10] },
    frame: { kind: "circle", centre: [21.3, 0], radius: 5.15, y: [6.45, 7.3] },
  },
  {
    // "151 | Octagonal service apron" with its workshop walls ("162/163", on its +x side), roof and supports.
    title: "About Me",
    hit: { kind: "circle", centre: [26.48, 7.05], radius: 5, y: [4.38, 9.8] },
    frame: { kind: "circle", centre: [26.48, 7.05], radius: 4.9, y: [6.62, 9.75] },
    orbit: { centre: [26.48, 7.6, 7.05], facing: 180 },
  },
  {
    // "152/171/173 | Upper gallery": its walls stand on the +x side, the rest is buried in the cliff.
    title: "Contact",
    hit: { kind: "box", min: [24.03, 1.03], max: [32.48, 9.48], y: [11.3, 14.05] },
    frame: { kind: "box", min: [26.5, 1.9], max: [32.4, 9.4], y: [11.5, 13.8] },
    orbit: { centre: [28.5, 12.6, 5.6], facing: 180 },
  },
  {
    // "167/169 | Left platform", its display bay (walls on the -x side) and cliff supports.
    // Square on (from +x) the central platform stands in the way: this looks
    // into the bay past its left side.
    title: "Experiences",
    hit: { kind: "box", min: [5.1, -11.45], max: [17.65, 4.2], y: [0.4, 6.8] },
    frame: { kind: "box", min: [5.1, -11.45], max: [17.65, 4.2], y: [2.5, 6.8] },
    orbit: { centre: [11.4, 3.2, -3.6], facing: 55 },
  },
];

const DURATION_S = 0.9;
/** An orbit takes this much longer per 90° it turns. */
const ORBIT_EXTRA_S = 0.4;
/** The platform (and its title) spans this share of the frame on its tighter axis. */
const FILL = 0.94;
const MAX_ZOOM = 6;
/** Largest zoom ratio between neighbouring crop levels. */
const LEVEL_STEP = 2;
/** Largest turn (radians) and approach (distance ratio) between neighbouring orbit keyframes. */
const KEY_TURN = THREE.MathUtils.degToRad(15);
const KEY_APPROACH = 1.5;
/** In-between orbit keyframes see this much wider than the camera does there. */
const KEY_OVERSCAN = 1.25;
/** Quiet time after the last live frame before re-rendering stale levels. */
const IDLE_MS = 800;
/** A press that moves further than this is a drag, not a click. */
const CLICK_SLOP_PX = 5;
/** Hit mask resolution relative to the canvas' CSS size. */
const MASK_SCALE = 0.5;
/** The HUD panel wall (DOM, see CavePanels) stands on the Projects console. */
const PANEL_SELECTOR = ".hud-screen";
const PANEL_PLATFORM = "Projects";
const WORLD_UP = new THREE.Vector3(0, 1, 0);

/**
 * Hand adjustments to a platform's final camera (zoomLayout.json, edited
 * with the dev sliders, see CaveZoomControls). Orbits: `facing` and
 * `elevation` in degrees round the orbit centre, `distance` in metres from
 * it. Crops (Projects): `zoom`. Both: `panX` / `panY`, a shift of the final
 * frame in frame widths / heights. Anything left out is fitted automatically.
 */
export type Tuning = { facing?: number; elevation?: number; distance?: number; zoom?: number; panX?: number; panY?: number };

/** A platform's final camera as the sliders show it: what it is now, and what the automatic fit would be. */
export type FinalShot = { platform: string; kind: "crop" | "orbit"; value: Required<Tuning>; auto: Required<Tuning> };

/** The Back button, Esc and the dev sliders talk to the director through this store. */
export const useCaveZoom = create<{
  platform: string | null;
  zoomTo: (platform: string | null) => void;
  /** The final camera of the platform the camera rests on (null in the main view or mid-zoom). */
  shot: FinalShot | null;
  tunings: Record<string, Tuning>;
  /** Merges `patch` into a platform's tuning (null: back to the automatic fit). */
  tune: (platform: string, patch: Tuning | null) => void;
  /** Replaces every platform's tuning. */
  loadTunings: (tunings: Record<string, Tuning>) => void;
}>(() => ({
  platform: null,
  zoomTo: () => {},
  shot: null,
  tunings: {},
  tune: () => {},
  loadTunings: () => {},
}));

type Size = { width: number; height: number };

/** Puts the camera on `shot`: its pose, then its frustum (Blender's lens shift, in units of the larger frame dimension, and the crop). */
function applyShot(camera: THREE.PerspectiveCamera, size: Size, shot: Shot) {
  camera.position.copy(shot.position);
  camera.quaternion.copy(shot.quaternion);
  camera.updateMatrixWorld();
  const { width, height } = size;
  const longest = Math.max(width, height);
  const { shift, view } = shot;
  const w = width / view.z;
  const h = height / view.z;
  camera.setViewOffset(width, height, shift[0] * longest + view.x * width - w / 2, -shift[1] * longest + view.y * height - h / 2, w, h);
}

/**
 * drei's `<Html transform>` layers assume a centred frustum: they follow its
 * scale on their own but need its off-centre part as a screen translation,
 * in CSS px. That is the view's centre relative to the un-shifted frame's,
 * scaled by the zoom.
 */
function htmlOffset(size: Size, shot: Shot): [number, number] {
  const longest = Math.max(size.width, size.height);
  const { shift, view } = shot;
  return [
    -view.z * ((view.x - 0.5) * size.width + shift[0] * longest),
    -view.z * ((view.y - 0.5) * size.height - shift[1] * longest),
  ];
}

/** drei's Html layers: every child of the canvas root except the canvas' own container. */
function htmlLayers(html: HTMLElement): HTMLElement[] {
  return [...html.children].filter((el): el is HTMLElement => el instanceof HTMLElement && !el.querySelector(":scope > canvas"));
}

/**
 * At rest the offset goes on the root as variables (`.cave-html-shift` in
 * cave.css), so layers that mount later pick it up too.
 */
function htmlRest(html: HTMLElement, size: Size, shot: Shot) {
  const [x, y] = htmlOffset(size, shot);
  html.classList.add("cave-html-shift");
  html.style.setProperty("--lens-shift-x", `${x}px`);
  html.style.setProperty("--lens-shift-y", `${y}px`);
  for (const layer of htmlLayers(html)) {
    layer.style.translate = "";
    layer.style.scale = "";
    layer.style.willChange = "";
  }
}

/**
 * Mid-crop the camera stays at `rest`, so drei keeps the panel wall's 3D
 * transforms as they are (recomputing them re-layers every panel slice each
 * frame), and each layer gets one 2D scale and offset that carries it to
 * `view`: the same crop the canvas shows, done by the compositor. Inline on
 * the few layers, not through the inherited variables, so the panels'
 * subtree is not restyled every frame.
 */
function htmlZoom(layers: HTMLElement[], size: Size, rest: Shot, view: View) {
  const k = view.z / rest.view.z;
  const [rx, ry] = htmlOffset(size, rest);
  const x = k * rx + (rest.view.x - view.x) * view.z * size.width;
  const y = k * ry + (rest.view.y - view.y) * view.z * size.height;
  for (const layer of layers) {
    layer.style.translate = `${x}px ${y}px`;
    layer.style.scale = `${k}`;
    layer.style.willChange = "transform";
  }
}

/** Mid-orbit the camera really moves (drei re-lays the layers); only the off-centre offset is set, inline. */
function htmlFollow(layers: HTMLElement[], size: Size, shot: Shot) {
  const [x, y] = htmlOffset(size, shot);
  for (const layer of layers) layer.style.translate = `${x}px ${y}px`;
}

type Level = {
  shot: Shot;
  texture: THREE.FramebufferTexture | null;
  version: number;
  /** Orbit keyframes (and the main frame they start from) are re-projected, so they keep their depth. */
  needsDepth: boolean;
  depth: DepthFrame | null;
};

/**
 * Main frame → one platform. `shotAt(u)` is the camera `u` (0..1) of the way
 * along; `levels[k]` is the pre-rendered shot at u = k / (levels.length - 1),
 * `levels[0]` being the main frame.
 */
type Path = {
  platform: string;
  kind: "crop" | "orbit";
  levels: Level[];
  duration: number;
  shotAt: (u: number) => Shot;
  /** Its final camera, for the sliders. */
  final: FinalShot;
};

/** Along a path, in u. */
type Anim = { path: Path; from: number; to: number; start: number; duration: number };

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const lerp = THREE.MathUtils.lerp;

/** The camera at `position` looking at `target`, upright. */
function lookFrom(position: THREE.Vector3, target: THREE.Vector3) {
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(position, target, WORLD_UP));
}

const VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

/**
 * Screen → main frame → each crop level's own frame. The textures hold
 * finished display pixels (copied from the canvas), so they are written back
 * untouched.
 */
const FRAGMENT = /* glsl */ `
  uniform sampler2D uCoarse;
  uniform sampler2D uFine;
  uniform vec3 uView;
  uniform vec3 uCoarseView;
  uniform vec3 uFineView;
  uniform float uMix;
  uniform float uFeather;
  varying vec2 vUv;
  vec2 levelUv(vec3 level, vec2 m) {
    vec2 l = (m - level.xy) * level.z + 0.5;
    return vec2(l.x, 1.0 - l.y);
  }
  void main() {
    vec2 screen = vec2(vUv.x, 1.0 - vUv.y);
    vec2 m = uView.xy + (screen - 0.5) / uView.z;
    vec4 coarse = texture2D(uCoarse, levelUv(uCoarseView, m));
    vec2 f = levelUv(uFineView, m);
    float inside = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
    float cover = uFeather > 0.0 ? smoothstep(0.0, uFeather, inside) : step(-1e-3, inside);
    gl_FragColor = mix(coarse, texture2D(uFine, f), uMix * cover);
  }
`;

/** Which platform (1-based, 0 = none) each fragment belongs to, by its world position. */
const MASK_VERTEX = /* glsl */ `
  varying vec3 vWorld;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const MASK_FRAGMENT = /* glsl */ `
  uniform vec4 uFootprint[${PLATFORMS.length}];
  uniform vec4 uHeights[${PLATFORMS.length}];
  varying vec3 vWorld;
  void main() {
    float best = 1e9;
    float id = 0.0;
    for (int i = 0; i < ${PLATFORMS.length}; i++) {
      vec4 a = uFootprint[i];
      vec4 b = uHeights[i];
      if (vWorld.y < b.y || vWorld.y > b.z) continue;
      vec2 d = vWorld.xz - a.xy;
      float n = b.x < 0.5 ? length(d) / a.z : max(abs(d.x) / a.z, abs(d.y) / a.w);
      if (n <= 1.0 && n < best) { best = n; id = float(i + 1); }
    }
    gl_FragColor = vec4(id / 255.0, 0.0, 0.0, 1.0);
  }
`;

type Layout = {
  paths: Map<string, Path>;
  titles: { platform: string; rect: [number, number, number, number] }[];
  /** Where the titles were when it was framed (dev: they can still move after load). */
  titleKey: string;
};

export class ZoomDirector {
  private composer: EffectComposer | null = null;
  private size: Size = { width: 1, height: 1 };
  private readonly mainShot: Shot;
  private readonly main: Level;
  private layout: Layout | null = null;
  private rest: Path | null = null;
  private anim: Anim | null = null;
  /** Where the zoom is this frame (set before drei reads the camera, drawn after). */
  private frameU = 0;
  /** The shot the camera holds at rest, which drei's Html layers are laid out for. */
  private cameraShot: Shot;
  /** The frame after a zoom: drei re-lays the Html layers for the new camera while the canvas is redrawn as is. */
  private syncFrame = false;
  /** drei's Html layers, looked up once per zoom. */
  private zoomLayers: HTMLElement[] | null = null;
  /** Bumped by every live frame; a level rendered before it may be out of date. */
  private version = 0;
  private mask: { data: Uint8Array; width: number; height: number } | null = null;
  private idleTimer = 0;
  private idleSince = performance.now();
  private disposed = false;
  private readonly quadScene = new THREE.Scene();
  private readonly quadCamera = new THREE.OrthographicCamera();
  private readonly blend: THREE.ShaderMaterial;
  private readonly warp: ZoomWarp;
  private readonly buffer = new THREE.Vector2();

  private readonly gl: THREE.WebGLRenderer;
  private readonly scene: THREE.Scene;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly model: THREE.Object3D;
  private readonly html: HTMLElement | undefined;
  private readonly invalidate: () => void;
  private readonly enabled: boolean;
  private tunings: Record<string, Tuning>;

  constructor(options: {
    gl: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    /** The cave model, rendered alone for the hit mask and the keyframes' depth. */
    model: THREE.Object3D;
    /** The Blender camera (manifest.camera): the main frame. */
    shot: CaveManifest["camera"];
    /** The rear hole the voxel box sits in (not part of the model). */
    hole: CaveManifest["hole"];
    /** The canvas root (r3f's event target), which holds the canvas and drei's Html layers. */
    html: HTMLElement | undefined;
    invalidate: () => void;
    /** Off: no zooming, the camera keeps the main frame. */
    enabled: boolean;
    /** Hand adjustments to each platform's final camera (zoomLayout.json). */
    tunings: Record<string, Tuning>;
  }) {
    this.gl = options.gl;
    this.scene = options.scene;
    this.camera = options.camera;
    this.model = options.model;
    this.html = options.html;
    this.invalidate = options.invalidate;
    this.enabled = options.enabled;
    this.tunings = structuredClone(options.tunings);
    const { position, direction, up, shift } = options.shot;
    const eye = new THREE.Vector3(...position);
    this.mainShot = {
      position: eye,
      quaternion: new THREE.Quaternion().setFromRotationMatrix(
        new THREE.Matrix4().lookAt(eye, eye.clone().add(new THREE.Vector3(...direction)), new THREE.Vector3(...up)),
      ),
      shift: shift ?? [0, 0],
      view: FULL,
    };
    this.main = { shot: this.mainShot, texture: null, version: -1, needsDepth: true, depth: null };
    this.cameraShot = this.mainShot;
    this.warp = new ZoomWarp(this.gl, options.hole);
    this.blend = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      uniforms: {
        uCoarse: { value: null },
        uFine: { value: null },
        uView: { value: new THREE.Vector3() },
        uCoarseView: { value: new THREE.Vector3() },
        uFineView: { value: new THREE.Vector3() },
        uMix: { value: 0 },
        uFeather: { value: 0 },
      },
      blending: THREE.NoBlending,
      depthTest: false,
      depthWrite: false,
    });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.blend);
    quad.frustumCulled = false;
    this.quadScene.add(quad);
  }

  private get restLevel(): Level {
    return this.rest ? this.rest.levels[this.rest.levels.length - 1] : this.main;
  }

  /** The composer that draws the live scene (rebuilt with the cave's GPU state). */
  setComposer(composer: EffectComposer | null) {
    this.composer = composer;
    this.version++;
    if (composer) this.scheduleIdle();
  }

  /** Canvas resized (CSS px): every pre-rendered level and the framing are redone. */
  setSize(width: number, height: number) {
    this.size = { width, height };
    if (this.anim) {
      this.rest = this.anim.to > this.anim.from ? this.anim.path : null;
      this.anim = null;
    }
    this.dropTextures(true);
    this.mask = null;
    if (this.layout) this.layout.titleKey = "";
    if (this.rest) this.ensureLayout();
    this.settleCamera();
    if (this.html) htmlRest(this.html, this.size, this.cameraShot);
    this.scheduleIdle();
  }

  private settleCamera() {
    this.cameraShot = this.restLevel.shot;
    applyShot(this.camera, this.size, this.cameraShot);
    useCaveZoom.setState({ shot: this.rest?.final ?? null });
  }

  /** Replaces every platform's tuning (the dev sliders load the file as it is on disk). */
  setTunings(tunings: Record<string, Tuning>) {
    this.tunings = structuredClone(tunings);
    useCaveZoom.setState({ tunings: structuredClone(this.tunings) });
    for (const { title } of PLATFORMS) this.retune(title);
  }

  /** Re-fits one platform's zoom with its tuning; if the camera rests there, it moves there at once. */
  private retune(platform: string) {
    if (!this.layout || this.anim) return;
    const old = this.layout.paths.get(platform);
    const spec = PLATFORMS.find((p) => p.title === platform);
    const path = spec && this.pathFor(spec);
    if (!path) return;
    old?.levels.forEach((level) => level !== this.main && this.dropLevel(level));
    this.layout.paths.set(platform, path);
    if (this.rest?.platform === platform) {
      this.rest = path;
      this.settleCamera();
      if (this.html) htmlRest(this.html, this.size, this.cameraShot);
      this.invalidate();
    }
    this.scheduleIdle();
  }

  /** Before drei's Html layers (and the voxel box) read the camera this frame: move it along the zoom. */
  beforeFrame() {
    const anim = this.anim;
    if (!anim) {
      if (this.syncFrame && this.html) htmlRest(this.html, this.size, this.cameraShot);
      this.zoomLayers = null;
      return;
    }
    const now = performance.now();
    if (anim.start < 0) anim.start = now;
    this.frameU = this.uAt(anim, now);
    const shot = anim.path.shotAt(this.frameU);
    if (anim.path.kind === "orbit") applyShot(this.camera, this.size, shot);
    if (!this.html) return;
    this.zoomLayers ??= htmlLayers(this.html);
    if (anim.path.kind === "orbit") htmlFollow(this.zoomLayers, this.size, shot);
    else htmlZoom(this.zoomLayers, this.size, this.cameraShot, shot.view);
  }

  /** The canvas' frame: the zoom's pre-rendered frames while animating, otherwise the live scene. */
  render(delta: number) {
    const composer = this.composer;
    if (!composer) return;
    if (this.anim) {
      this.syncFrame = false;
      this.drawAnim();
      return;
    }
    const level = this.restLevel;
    if (this.syncFrame && level.version === this.version && this.fits(level.texture)) {
      // The canvas already shows this; redraw it as is (the frame exists for drei's Html layers).
      this.syncFrame = false;
      this.draw(level.shot.view, level, level, 0, 0);
      return;
    }
    this.syncFrame = false;
    composer.render(delta);
    this.version++;
    this.copyInto(this.restLevel);
    this.scheduleIdle();
  }

  request(platform: string | null) {
    if (!this.enabled || !this.composer) return;
    const anim = this.anim;
    if (anim) {
      // Only a reversal is allowed mid-zoom; it continues from where it is.
      const target = platform === null ? 0 : platform === anim.path.platform ? 1 : NaN;
      if (Number.isNaN(target) || target === anim.to) return;
      const now = performance.now();
      const from = this.uAt(anim, now);
      this.anim = { path: anim.path, from, to: target, start: now, duration: anim.path.duration * Math.abs(target - from) };
      useCaveZoom.setState({ platform });
      this.invalidate();
      return;
    }
    const current = this.rest?.platform ?? null;
    // From a platform the only way is back out (Esc / Back).
    if (platform === current || (current && platform)) return;
    const path = platform ? this.ensureLayout().paths.get(platform) : this.rest;
    if (!path) return;
    window.clearTimeout(this.idleTimer);
    // Normally all pre-rendered already; anything missing is rendered now, once.
    for (const level of path.levels) if (this.missing(level)) this.renderLevel(level);
    this.anim = { path, from: platform ? 0 : 1, to: platform ? 1 : 0, start: -1, duration: path.duration };
    useCaveZoom.setState({ platform, shot: null });
    this.invalidate();
  }

  /** The platform under a pointer, judged on the main frame (titles first, then the hit mask). */
  platformAt(clientX: number, clientY: number): string | null {
    if (this.anim || this.rest || !this.composer) return null;
    const rect = this.gl.domElement.getBoundingClientRect();
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return null;
    const layout = this.ensureLayout();
    for (const { platform, rect: [x0, y0, x1, y1] } of layout.titles) {
      if (x >= x0 && x <= x1 && y >= y0 && y <= y1) return platform;
    }
    // The panel wall is DOM over the canvas, not in the mask.
    for (const panel of this.html?.querySelectorAll(PANEL_SELECTOR) ?? []) {
      const r = panel.getBoundingClientRect();
      if (clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom) return PANEL_PLATFORM;
    }
    const mask = this.ensureMask();
    const px = Math.min(mask.width - 1, Math.floor(x * mask.width));
    const py = Math.min(mask.height - 1, Math.floor((1 - y) * mask.height));
    const id = mask.data[(py * mask.width + px) * 4];
    return id ? PLATFORMS[id - 1].title : null;
  }

  /** Pointer and keyboard input; returns the detach function. */
  attach(): () => void {
    if (!this.enabled) return () => {};
    // The canvas root, not the canvas: the panel wall's DOM takes the pointer
    // over the panels, and its events bubble up through here too.
    const target = this.html ?? this.gl.domElement;
    let press: { id: number; x: number; y: number } | null = null;
    const onMove = (e: PointerEvent) => {
      if (press) return;
      target.style.cursor = this.platformAt(e.clientX, e.clientY) ? "pointer" : "";
    };
    const onDown = (e: PointerEvent) => {
      press = e.button === 0 ? { id: e.pointerId, x: e.clientX, y: e.clientY } : null;
    };
    const onUp = (e: PointerEvent) => {
      const start = press;
      press = null;
      if (!start || start.id !== e.pointerId || Math.hypot(e.clientX - start.x, e.clientY - start.y) > CLICK_SLOP_PX) return;
      const platform = this.platformAt(e.clientX, e.clientY);
      if (!platform) return;
      target.style.cursor = "";
      this.request(platform);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") this.request(null);
    };
    target.addEventListener("pointermove", onMove);
    target.addEventListener("pointerdown", onDown);
    target.addEventListener("pointerup", onUp);
    window.addEventListener("keydown", onKey);
    useCaveZoom.setState({
      zoomTo: (platform) => this.request(platform),
      tunings: structuredClone(this.tunings),
      tune: (platform, patch) => {
        this.tunings[platform] = patch ? { ...this.tunings[platform], ...patch } : {};
        useCaveZoom.setState({ tunings: structuredClone(this.tunings) });
        this.retune(platform);
      },
      loadTunings: (tunings) => this.setTunings(tunings),
    });
    return () => {
      target.removeEventListener("pointermove", onMove);
      target.removeEventListener("pointerdown", onDown);
      target.removeEventListener("pointerup", onUp);
      window.removeEventListener("keydown", onKey);
      target.style.cursor = "";
      useCaveZoom.setState({ platform: null, zoomTo: () => {}, shot: null, tune: () => {}, loadTunings: () => {} });
    };
  }

  dispose() {
    this.disposed = true;
    window.clearTimeout(this.idleTimer);
    this.dropTextures(true);
    this.warp.dispose();
    this.blend.dispose();
    (this.quadScene.children[0] as THREE.Mesh).geometry.dispose();
  }

  /** 0..1 through the zoom's time; it starts on the first frame drawn. */
  private progress(anim: Anim, now: number) {
    if (anim.duration <= 0) return 1;
    return anim.start < 0 ? 0 : Math.min(1, (now - anim.start) / (anim.duration * 1000));
  }

  private uAt(anim: Anim, now: number) {
    return anim.from + (anim.to - anim.from) * ease(this.progress(anim, now));
  }

  private drawAnim() {
    const anim = this.anim!;
    const { levels, kind } = anim.path;
    const u = this.frameU;
    // The two levels either side of the current point.
    const n = levels.length - 1;
    const k = Math.min(n - 1, Math.floor(u * n));
    const mix = THREE.MathUtils.clamp(u * n - k, 0, 1);
    const a = levels[k];
    const b = levels[k + 1];
    if (kind === "orbit") this.warp.draw(this.camera, a, b, mix);
    else this.draw(anim.path.shotAt(u).view, a, b, mix, 0.15 * (1 - mix));
    if (this.progress(anim, performance.now()) < 1) {
      this.invalidate();
      return;
    }
    this.anim = null;
    this.rest = anim.to > anim.from ? anim.path : null;
    this.settleCamera();
    // One more frame re-lays drei's Html layers for the new camera. It redraws
    // the end level, or renders live if that level is out of date (the voxel
    // box moved meanwhile).
    this.syncFrame = true;
    this.invalidate();
  }

  /** Crop levels: the screen shows `view` of the main frame, `mix` of the way from `coarse` to `fine`. */
  private draw(view: View, coarse: Level, fine: Level, mix: number, feather: number) {
    const u = this.blend.uniforms;
    const c = coarse.shot.view;
    const f = fine.shot.view;
    u.uCoarse.value = coarse.texture;
    u.uFine.value = fine.texture;
    u.uView.value.set(view.x, view.y, view.z);
    u.uCoarseView.value.set(c.x, c.y, c.z);
    u.uFineView.value.set(f.x, f.y, f.z);
    u.uMix.value = mix;
    u.uFeather.value = feather;
    this.gl.setRenderTarget(null);
    this.gl.render(this.quadScene, this.quadCamera);
  }

  private fits(texture: THREE.FramebufferTexture | null) {
    this.gl.getDrawingBufferSize(this.buffer);
    return !!texture && texture.image.width === this.buffer.x && texture.image.height === this.buffer.y;
  }

  /** Never rendered at this size (as opposed to merely out of date). */
  private missing(level: Level) {
    return !this.fits(level.texture) || (level.needsDepth && !level.depth);
  }

  /** Copies what the canvas shows into a level's texture. */
  private copyInto(level: Level) {
    if (!this.enabled) return;
    if (!this.fits(level.texture)) {
      level.texture?.dispose();
      const texture = new THREE.FramebufferTexture(this.buffer.x, this.buffer.y);
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      level.texture = texture;
    }
    this.gl.setRenderTarget(null);
    this.gl.copyFramebufferToTexture(level.texture!);
    level.version = this.version;
  }

  /**
   * Renders a level off screen: drawn into the canvas, copied out (with its
   * depth for the orbits), and the resting frame put straight back, all in
   * one task, so it never shows.
   */
  private renderLevel(level: Level) {
    const composer = this.composer!;
    applyShot(this.camera, this.size, level.shot);
    composer.render(0);
    this.copyInto(level);
    if (level.needsDepth) {
      this.gl.getDrawingBufferSize(this.buffer);
      this.warp.resize(this.buffer.x, this.buffer.y);
      level.depth = this.warp.renderDepth(this.camera, this.model, this.titleMeshes(), level.depth);
      this.warp.warm(this.camera, level);
    }
    applyShot(this.camera, this.size, this.cameraShot);
    const rest = this.restLevel;
    if (rest !== level && this.fits(rest.texture)) {
      // The new level rides along at zero weight: its first sampling costs
      // tens of ms on some drivers, better spent now than in the first zoom.
      this.draw(rest.shot.view, rest, level, 0, 0);
    } else if (rest !== level) {
      composer.render(0);
      this.copyInto(rest);
    }
  }

  private dropLevel(level: Level) {
    level.texture?.dispose();
    level.texture = null;
    level.depth?.target.dispose();
    level.depth = null;
  }

  /** Every level of the current framing; the main frame's colour too if `includeMain` (its depth always: it holds the titles). */
  private dropTextures(includeMain: boolean) {
    if (includeMain) {
      this.dropLevel(this.main);
    } else {
      this.main.depth?.target.dispose();
      this.main.depth = null;
    }
    for (const path of this.layout?.paths.values() ?? []) {
      for (const level of path.levels) if (level !== this.main) this.dropLevel(level);
    }
  }

  private scheduleIdle() {
    if (!this.enabled || this.disposed) return;
    this.idleSince = performance.now();
    window.clearTimeout(this.idleTimer);
    this.idleTimer = window.setTimeout(() => this.idleStep(), IDLE_MS);
  }

  /** One stale level per idle slot, so the page stays responsive while they render. */
  private idleStep() {
    if (this.disposed || this.anim || !this.composer) return;
    // The section titles load on their own; the framing includes them, so wait for them (briefly).
    if (!this.layout && !this.titlesReady() && performance.now() - this.idleSince < 4000) {
      this.idleTimer = window.setTimeout(() => this.idleStep(), 250);
      return;
    }
    const layout = this.ensureLayout();
    if (!this.mask) {
      this.ensureMask();
    } else {
      const levels = [this.main, ...[...layout.paths.values()].flatMap((path) => path.levels.slice(1).reverse())];
      const stale = levels.find((level) => this.missing(level) || level.version < this.version);
      if (!stale) return;
      this.renderLevel(stale);
    }
    this.afterGpu(() => {
      if (typeof window.requestIdleCallback === "function") window.requestIdleCallback(() => this.idleStep(), { timeout: 500 });
      else this.idleStep();
    });
  }

  /**
   * Runs `next` once the GPU has finished everything queued so far. A level
   * takes far longer to draw than to submit; without this the job would queue
   * them all at once and the first zoom would wait behind the backlog.
   */
  private afterGpu(next: () => void) {
    const ctx = this.gl.getContext() as WebGL2RenderingContext;
    const fence = ctx.fenceSync(ctx.SYNC_GPU_COMMANDS_COMPLETE, 0);
    ctx.flush();
    const poll = () => {
      if (this.disposed) return;
      if (fence && ctx.getSyncParameter(fence, ctx.SYNC_STATUS) !== ctx.SIGNALED) {
        this.idleTimer = window.setTimeout(poll, 16);
        return;
      }
      if (fence) ctx.deleteSync(fence);
      this.idleTimer = window.setTimeout(next, 16);
    };
    this.idleTimer = window.setTimeout(poll, 16);
  }

  private titles: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>[] = [];

  /** CaveLabels' title meshes (cached once all are found). */
  private titleMeshes() {
    if (this.titles.length < PLATFORMS.length) {
      this.titles = PLATFORMS.map(({ title }) => this.scene.getObjectByName(`title-${title}`) as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>).filter(Boolean);
    }
    return this.titles;
  }

  private titlesReady() {
    const titles = this.titleMeshes();
    return titles.length === PLATFORMS.length && titles.every((mesh) => mesh.visible);
  }

  private titleKey() {
    return this.titleMeshes()
      .map((mesh) => (mesh.visible ? [...mesh.position.toArray(), ...(mesh.material.uniforms.uSize.value as THREE.Vector2).toArray()].join() : "-"))
      .join("|");
  }

  /** Runs `fn` with the camera on `shot` (put back on its resting shot after). */
  private withShot<T>(shot: Shot, fn: () => T): T {
    applyShot(this.camera, this.size, shot);
    try {
      return fn();
    } finally {
      applyShot(this.camera, this.size, this.cameraShot);
    }
  }

  /** The platforms' framing, made on first use and redone if a title has moved. */
  private ensureLayout(): Layout {
    const titleKey = this.titleKey();
    if (this.layout && (this.layout.titleKey === titleKey || this.anim)) return this.layout;
    // Levels rendered for an old framing go; the main frame's colour stays valid.
    const platform = this.rest?.platform;
    this.dropTextures(false);
    this.layout = this.frame(titleKey);
    if (platform) {
      this.rest = this.layout.paths.get(platform) ?? null;
      this.settleCamera();
      if (this.html) htmlRest(this.html, this.size, this.cameraShot);
    }
    return this.layout;
  }

  /** A platform's frame shape and title, as points to fit on screen. */
  private framePoints(shape: Shape): THREE.Vector3[] {
    const points: THREE.Vector3[] = [];
    for (const y of shape.y) {
      if (shape.kind === "circle") {
        for (let i = 0; i < 32; i++) {
          const a = (i / 32) * Math.PI * 2;
          points.push(new THREE.Vector3(shape.centre[0] + Math.cos(a) * shape.radius, y, shape.centre[1] + Math.sin(a) * shape.radius));
        }
      } else {
        for (const x of [shape.min[0], shape.max[0]]) for (const z of [shape.min[1], shape.max[1]]) points.push(new THREE.Vector3(x, y, z));
      }
    }
    return points;
  }

  /** Where `points` and a title land in the frame of `camera` (0..1, y down); the title is a billboard facing it. */
  private frameBox(camera: THREE.PerspectiveCamera, points: THREE.Vector3[], title: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial> | undefined) {
    const box = new THREE.Box2();
    const p = new THREE.Vector3();
    const add = (v: THREE.Vector3) => {
      p.copy(v).project(camera);
      box.expandByPoint(new THREE.Vector2((p.x + 1) / 2, (1 - p.y) / 2));
    };
    points.forEach(add);
    let titleRect: THREE.Box2 | null = null;
    if (title?.visible) {
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
      const size = title.material.uniforms.uSize.value as THREE.Vector2;
      const before = box.clone();
      box.makeEmpty();
      for (const sx of [-0.5, 0.5]) {
        for (const sy of [-0.5, 0.5]) add(new THREE.Vector3().copy(title.position).addScaledVector(right, sx * size.x).addScaledVector(up, sy * size.y));
      }
      titleRect = box.clone();
      box.union(before);
    }
    return { box, titleRect };
  }

  /** Each platform's zoomed framing (platform + title) and the levels leading to it. */
  private frame(titleKey: string): Layout {
    const paths = new Map<string, Path>();
    const titles: Layout["titles"] = [];
    for (const platform of PLATFORMS) {
      const title = this.titleMeshes().find((m) => m.name === `title-${platform.title}`);
      const { titleRect } = this.withShot(this.mainShot, () => this.frameBox(this.camera, [], title));
      if (titleRect) titles.push({ platform: platform.title, rect: [titleRect.min.x, titleRect.min.y, titleRect.max.x, titleRect.max.y] });
      const path = this.pathFor(platform);
      if (path) paths.set(platform.title, path);
    }
    return { paths, titles, titleKey };
  }

  /** One platform's zoom, with its tuning. */
  private pathFor(platform: (typeof PLATFORMS)[number]): Path | null {
    const title = this.titleMeshes().find((m) => m.name === `title-${platform.title}`);
    const points = this.framePoints(platform.frame);
    const tuning = this.tunings[platform.title] ?? {};
    if (platform.orbit) return this.orbitPath(platform.title, platform.orbit, points, title, tuning);
    const { box } = this.withShot(this.mainShot, () => this.frameBox(this.camera, points, title));
    return this.cropPath(platform.title, box, tuning);
  }

  /** The camera stays on the main frame and narrows onto `box` (main-frame coordinates). */
  private cropPath(platform: string, box: THREE.Box2, tuning: Tuning): Path | null {
    // Only what is inside the main frame can be zoomed into.
    box.intersect(new THREE.Box2(new THREE.Vector2(0, 0), new THREE.Vector2(1, 1)));
    if (box.isEmpty()) return null;
    const extent = box.getSize(new THREE.Vector2());
    const autoZoom = THREE.MathUtils.clamp(FILL / Math.max(extent.x, extent.y), 1.05, MAX_ZOOM);
    const zoom = THREE.MathUtils.clamp(tuning.zoom ?? autoZoom, 1.05, MAX_ZOOM);
    const panX = tuning.panX ?? 0;
    const panY = tuning.panY ?? 0;
    const centre = box.getCenter(new THREE.Vector2()).add(new THREE.Vector2(panX, panY));
    const half = 0.5 / zoom;
    centre.set(THREE.MathUtils.clamp(centre.x, half, 1 - half), THREE.MathUtils.clamp(centre.y, half, 1 - half));
    // The point that stays put on screen: every view is the main frame scaled about it.
    const pivot = centre.clone().multiplyScalar(zoom).subScalar(0.5).divideScalar(zoom - 1);
    const main = this.mainShot;
    const shotAt = (u: number): Shot => {
      const z = zoom ** u;
      return { ...main, view: { x: pivot.x + (0.5 - pivot.x) / z, y: pivot.y + (0.5 - pivot.y) / z, z } };
    };
    const steps = Math.max(1, Math.ceil(Math.log(zoom) / Math.log(LEVEL_STEP)));
    const levels = [this.main];
    for (let k = 1; k <= steps; k++) levels.push({ shot: shotAt(k / steps), texture: null, version: -1, needsDepth: false, depth: null });
    const final: FinalShot = {
      platform,
      kind: "crop",
      value: { facing: 0, elevation: 0, distance: 0, zoom, panX, panY },
      auto: { facing: 0, elevation: 0, distance: 0, zoom: autoZoom, panX: 0, panY: 0 },
    };
    return { platform, kind: "crop", levels, duration: DURATION_S, shotAt, final };
  }

  /**
   * The camera swings round `centre`, from the main camera to `facing` (by
   * default at the main camera's height angle), looking from where the main
   * frame looked to `centre`, and moves in until the platform and its title
   * fill the frame (unless tuned).
   */
  private orbitPath(
    platform: string,
    orbit: { centre: Vec3; facing: number },
    points: THREE.Vector3[],
    title: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial> | undefined,
    tuning: Tuning,
  ): Path {
    const { degToRad, radToDeg } = THREE.MathUtils;
    const main = this.mainShot;
    const centre = new THREE.Vector3(...orbit.centre);
    const from = main.position.clone().sub(centre);
    const r0 = from.length();
    const az0 = Math.atan2(from.z, from.x);
    const el0 = Math.asin(from.y / r0);
    const facing = tuning.facing ?? orbit.facing;
    const el1 = degToRad(THREE.MathUtils.clamp(tuning.elevation ?? radToDeg(el0), -80, 85));
    let turn = degToRad(facing) - az0;
    turn = Math.atan2(Math.sin(turn), Math.cos(turn));
    // Where the main frame looks, at the platform's distance.
    const look0 = main.position.clone().add(new THREE.Vector3(0, 0, -1).applyQuaternion(main.quaternion).multiplyScalar(r0));
    const positionAt = (az: number, el: number, r: number) =>
      new THREE.Vector3(Math.cos(el) * Math.cos(az), Math.sin(el), Math.cos(el) * Math.sin(az)).multiplyScalar(r).add(centre);

    // The distance at which the platform and title fill the frame, then the crop that centres them.
    const probe = this.camera.clone();
    const end = (r: number): Shot => {
      const position = positionAt(az0 + turn, el1, r);
      return { position, quaternion: lookFrom(position, centre), shift: [0, 0], view: FULL };
    };
    const fit = (r: number) => {
      applyShot(probe, this.size, end(r));
      return this.frameBox(probe, points, title).box;
    };
    let near = 1;
    let far = r0 * 1.5;
    for (let i = 0; i < 30; i++) {
      const r = (near + far) / 2;
      const extent = fit(r).getSize(new THREE.Vector2());
      if (Math.max(extent.x, extent.y) > FILL) near = r;
      else far = r;
    }
    const autoDistance = far;
    const r1 = Math.max(0.5, tuning.distance ?? autoDistance);
    const panX = tuning.panX ?? 0;
    const panY = tuning.panY ?? 0;
    // Closer than the platform's own extent, parts of its frame (and the title)
    // end up behind the camera and their projection is meaningless: the crop
    // is centred as if from the nearest distance where all of it is in front.
    const toCamera = new THREE.Vector3(Math.cos(el1) * Math.cos(az0 + turn), Math.sin(el1), Math.cos(el1) * Math.sin(az0 + turn));
    let safe = 0;
    for (const p of title ? [...points, title.position] : points) safe = Math.max(safe, p.clone().sub(centre).dot(toCamera));
    const centreOnScreen = fit(Math.max(r1, safe + 0.5)).getCenter(new THREE.Vector2());
    const endView: View = { x: centreOnScreen.x + panX, y: centreOnScreen.y + panY, z: 1 };

    const shotAt = (u: number): Shot => {
      if (u <= 0) return main;
      const position = positionAt(az0 + turn * u, lerp(el0, el1, u), r0 * (r1 / r0) ** u);
      return {
        position,
        quaternion: lookFrom(position, look0.clone().lerp(centre, u)),
        shift: [lerp(main.shift[0], 0, u), lerp(main.shift[1], 0, u)],
        view: { x: lerp(0.5, endView.x, u), y: lerp(0.5, endView.y, u), z: 1 },
      };
    };
    const steps = Math.max(2, Math.ceil(Math.abs(turn) / KEY_TURN), Math.ceil(Math.log(r0 / r1) / Math.log(KEY_APPROACH)));
    const levels = [this.main];
    for (let k = 1; k <= steps; k++) {
      const shot = shotAt(k / steps);
      // The keyframes in between are only ever seen re-projected: a wider view
      // covers what turns into the frame between them.
      if (k < steps) shot.view = { ...shot.view, z: 1 / KEY_OVERSCAN };
      levels.push({ shot, texture: null, version: -1, needsDepth: true, depth: null });
    }
    const duration = DURATION_S + ORBIT_EXTRA_S * (Math.abs(turn) / (Math.PI / 2));
    const final: FinalShot = {
      platform,
      kind: "orbit",
      value: { facing, elevation: radToDeg(el1), distance: r1, zoom: 1, panX, panY },
      auto: { facing: orbit.facing, elevation: radToDeg(el0), distance: autoDistance, zoom: 1, panX: 0, panY: 0 },
    };
    return { platform, kind: "orbit", levels, duration, shotAt, final };
  }

  /**
   * Renders the cave once, off screen, with every fragment coloured by the
   * platform its world position falls in, and keeps it on the CPU: hover and
   * click become a lookup, with occlusion handled by the depth buffer.
   */
  private ensureMask() {
    if (this.mask) return this.mask;
    const width = Math.max(1, Math.round(this.size.width * MASK_SCALE));
    const height = Math.max(1, Math.round(this.size.height * MASK_SCALE));
    const target = new THREE.WebGLRenderTarget(width, height, { depthBuffer: true });
    const material = new THREE.ShaderMaterial({
      vertexShader: MASK_VERTEX,
      fragmentShader: MASK_FRAGMENT,
      side: THREE.DoubleSide,
      uniforms: {
        uFootprint: {
          value: PLATFORMS.map(({ hit: s }) =>
            s.kind === "circle"
              ? new THREE.Vector4(s.centre[0], s.centre[1], s.radius, s.radius)
              : new THREE.Vector4((s.min[0] + s.max[0]) / 2, (s.min[1] + s.max[1]) / 2, (s.max[0] - s.min[0]) / 2, (s.max[1] - s.min[1]) / 2),
          ),
        },
        uHeights: { value: PLATFORMS.map(({ hit: s }) => new THREE.Vector4(s.kind === "circle" ? 0 : 1, s.y[0], s.y[1], 0)) },
      },
    });
    const data = new Uint8Array(width * height * 4);
    const saved = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
    this.model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        const mesh = o as THREE.Mesh;
        saved.set(mesh, mesh.material);
        mesh.material = material;
      }
    });
    const gl = this.gl;
    const clear = gl.getClearColor(new THREE.Color());
    const alpha = gl.getClearAlpha();
    this.withShot(this.mainShot, () => {
      gl.setRenderTarget(target);
      gl.setClearColor(0x000000, 1);
      gl.clear();
      gl.render(this.model, this.camera);
      gl.readRenderTargetPixels(target, 0, 0, width, height, data);
    });
    gl.setRenderTarget(null);
    gl.setClearColor(clear, alpha);
    for (const [mesh, original] of saved) mesh.material = original;
    material.dispose();
    target.dispose();
    this.mask = { data, width, height };
    return this.mask;
  }
}
