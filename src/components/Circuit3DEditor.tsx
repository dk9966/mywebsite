import {
  OrbitControls,
  OrthographicCamera,
  PerspectiveCamera,
  useGLTF,
} from "@react-three/drei";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import {
  Suspense,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ElementRef,
} from "react";
import * as THREE from "three";
import {
  buildOutlineModel,
  transformedOutlinePaths,
  type OutlineModel,
} from "../lib/circuit3DMeshes";
import type { ScreenRect } from "../lib/circuitBoxSelect";
import {
  boardPickXZ,
  boardY,
  pickBoardPoint,
  type BoardPickView,
  type BoardPickXZ,
} from "../lib/circuitBoardPick";
import { MESH_LABELS, type MeshKind } from "../lib/circuitMeshBoxes";
import {
  loadVariantCatalog,
  useVariantCatalog,
  variantOutlinePaths,
  type VariantCatalog,
  type VariantEntry,
} from "../lib/qfpVariantCatalog";
import {
  footprintsToMeshes,
  moveMeshBounds,
  resizeMeshFromCorner,
  resolveMeshes,
  type CircuitMesh,
  type MeshBounds,
  type MeshHandle,
  type MeshSize,
} from "../lib/circuitMeshes";
import { applyTopology } from "../lib/circuitTopology";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  buildRawCircuitPaths,
  layoutFromPaths,
  type CircuitsTracedLayout,
} from "../lib/tronPathsFromCircuitsTraced";
import { setEditPathsGetter, useCircuitTuning } from "../stores/circuitTuning";
import { useLineConfig } from "../stores/lineConfig";
import {
  SHORTCUT_BTN,
  useShortcutButtonFlash,
} from "../hooks/useShortcutButtonFlash";
import "./Circuit3DEditor.css";
import CircuitSelectionLayer from "./CircuitSelection";
import MeshVariantPreview from "./MeshVariantPreview";
import {
  BoxSelectLayer,
  BoxSelectOverlay,
  CameraRefBridge,
} from "./CircuitBoxSelect";
import TronGrid from "./TronGrid";

const PALETTE_SCALE_KEY = "c3d-palette-scale";
const PALETTE_W_KEY = "c3d-palette-w";
const DEFAULT_PALETTE_SCALE = 1;
const MIN_PALETTE_SCALE = 0.75;
const MAX_PALETTE_SCALE = 2.5;
const PALETTE_SCALE_DRAG = 220;

function readPaletteScale(): number {
  try {
    const scale = Number(localStorage.getItem(PALETTE_SCALE_KEY));
    if (Number.isFinite(scale)) {
      return Math.max(
        MIN_PALETTE_SCALE,
        Math.min(MAX_PALETTE_SCALE, scale),
      );
    }
    const legacyW = Number(localStorage.getItem(PALETTE_W_KEY));
    if (Number.isFinite(legacyW)) {
      return Math.max(
        MIN_PALETTE_SCALE,
        Math.min(MAX_PALETTE_SCALE, legacyW / 88),
      );
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_PALETTE_SCALE;
}

type PaletteMeshGhost = {
  kind: MeshKind;
  size: MeshSize;
  variant: string | null;
  clientX: number;
  clientY: number;
};

type PaletteDrag = {
  kind: MeshKind;
  size: MeshSize;
  variant: string | null;
  startX: number;
  startY: number;
  dragging: boolean;
  pointerId: number;
  sourceEl: HTMLElement;
  /** Same variant was already armed when this press started. */
  wasArmed: boolean;
  /** Last board hit while dragging — used when release-time pick races bridge teardown. */
  lastPick: { x: number; z: number } | null;
};

function pointerOutsideRect(
  clientX: number,
  clientY: number,
  rect: DOMRect,
): boolean {
  return (
    clientX < rect.left ||
    clientX > rect.right ||
    clientY < rect.top ||
    clientY > rect.bottom
  );
}

type BoardPickApi = {
  pick: BoardPickXZ;
  canvas: HTMLCanvasElement;
};

/** Exposes board raycast picking to the HTML palette (outside the Canvas). */
function BoardPickBridge({
  paths,
  view,
  centerZ,
  onReady,
}: {
  paths: GridPath[];
  view: ViewKind;
  centerZ: number;
  onReady: (api: BoardPickApi | null) => void;
}) {
  const { camera, gl } = useThree();
  const y = useMemo(() => boardY(paths), [paths]);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  const pickCtxRef = useRef({ camera, gl, y, view, centerZ });
  pickCtxRef.current = { camera, gl, y, view, centerZ };

  useEffect(() => {
    const pick: BoardPickXZ = (clientX, clientY) => {
      const ctx = pickCtxRef.current;
      return boardPickXZ(
        clientX,
        clientY,
        ctx.camera,
        ctx.gl.domElement,
        ctx.y,
        ctx.view,
        ctx.centerZ,
      );
    };
    onReadyRef.current({ pick, canvas: gl.domElement });
    return () => onReadyRef.current(null);
  }, [gl.domElement]);

  return null;
}

const OUTLINE_GLB_URL = "/models/circuits-traced-outline.glb";
useGLTF.preload(OUTLINE_GLB_URL);
loadVariantCatalog();

/** Camera distance as a multiple of the board span (fits the wide board). */
const VIEW_DIST_FACTOR = 1.5;
const VIEW_ANIM_MS = 300;
const FOV = 40;

type ProjectionKind = "ortho" | "perspective";

/** Extra breathing room around the board when the ortho zoom is fit to it. */
const FIT_MARGIN = 1.12;

/**
 * Orthographic zoom that frames `span` world units within the smaller viewport
 * dimension. R3F's default ortho frustum is pixel-sized (1 unit = 1px at zoom
 * 1), so visible world width = viewportPx / zoom → zoom = viewportPx / worldSpan.
 */
function fitOrthoZoom(
  size: { width: number; height: number },
  span: number,
): number {
  const minDim = Math.min(size.width, size.height);
  return minDim / (Math.max(span, 1) * FIT_MARGIN);
}

/** Ortho zoom that matches perspective framing at the same target distance. */
function orthoZoomFromPerspectiveDistance(
  size: { width: number; height: number },
  distance: number,
  fov: number,
): number {
  const fovRad = (fov * Math.PI) / 180;
  const visibleHeight = 2 * distance * Math.tan(fovRad / 2);
  return size.height / Math.max(visibleHeight, 1e-6);
}

/** Keep position/framing when swapping ortho <-> perspective cameras. */
function preserveCameraOnProjectionSwap(
  prevCamera: THREE.Camera,
  camera: THREE.Camera,
  lookTarget: THREE.Vector3,
  size: { width: number; height: number },
): number {
  camera.position.copy(prevCamera.position);
  camera.up.copy(prevCamera.up);
  camera.lookAt(lookTarget);

  const distance = camera.position.distanceTo(lookTarget);

  if (camera instanceof THREE.OrthographicCamera) {
    if (prevCamera instanceof THREE.OrthographicCamera) {
      camera.zoom = prevCamera.zoom;
    } else if (prevCamera instanceof THREE.PerspectiveCamera) {
      camera.zoom = orthoZoomFromPerspectiveDistance(
        size,
        distance,
        prevCamera.fov,
      );
    }
    camera.updateProjectionMatrix();
  } else if (camera instanceof THREE.PerspectiveCamera) {
    camera.updateProjectionMatrix();
  }

  return distance;
}

function applyFitCamera(
  camera: THREE.Camera,
  preset: ViewPreset,
  target: THREE.Vector3,
  size: { width: number; height: number },
  span: number,
): number {
  const distance = preset.pos.distanceTo(target);
  if (camera instanceof THREE.OrthographicCamera) {
    camera.zoom = fitOrthoZoom(size, span);
    camera.updateProjectionMatrix();
    return distance;
  }
  camera.position.copy(preset.pos);
  camera.up.copy(preset.up);
  camera.lookAt(target);
  return distance;
}

type ViewKind = BoardPickView;

/** Screen-pixel stroke width — stays readable at any zoom without bloom. */
const EDITOR_SCREEN_LINE_WIDTH = 2.5;

const LINE_CONFIG_OVERRIDES = {
  lineColor: "#66f0f0",
  lineOpacity: 1,
  tipColor: "#66f0f0",
  lineEmission: 1,
  gridOpacity: 0,
};

function isEditableLine(id: string | undefined): boolean {
  return !!id && (id.startsWith("trace-") || id.startsWith("user-"));
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

type ViewPreset = { pos: THREE.Vector3; up: THREE.Vector3 };

type Presets = { target: THREE.Vector3; top: ViewPreset; side: ViewPreset };

function computePresets(layout: CircuitsTracedLayout): Presets {
  const [cx, cy, cz] = layout.center;
  const span = Math.max(layout.span, 1);
  const d = span * VIEW_DIST_FACTOR;
  return {
    target: new THREE.Vector3(cx, cy, cz),
    // Straight down the -Y axis (board XZ plane), screen-up = world -Z so +X is
    // to the right and +Z runs down the screen — matching the old 2D editor.
    top: {
      pos: new THREE.Vector3(cx, cy + d, cz),
      up: new THREE.Vector3(0, 0, -1),
    },
    // Camera on +Z, level with board center — pure side elevation (Y up, X across).
    side: {
      pos: new THREE.Vector3(cx, cy, cz + d),
      up: new THREE.Vector3(0, 1, 0),
    },
  };
}

// --- Board-plane picking ----------------------------------------------------

const _ray = new THREE.Raycaster();
const _ndc = new THREE.Vector2();
const _plane = new THREE.Plane();
const _hit = new THREE.Vector3();

function pickBoard(
  clientX: number,
  clientY: number,
  y: number,
  camera: THREE.Camera,
  dom: HTMLCanvasElement,
): { x: number; z: number } | null {
  const rect = dom.getBoundingClientRect();
  _ndc.set(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  );
  _ray.setFromCamera(_ndc, camera);
  _plane.set(new THREE.Vector3(0, 1, 0), -y);
  return _ray.ray.intersectPlane(_plane, _hit)
    ? { x: _hit.x, z: _hit.z }
    : null;
}

// --- Camera rig (presets, t-animation, lock/unlock) -------------------------

const LOCKED_VIEW_AXIS: Record<ViewKind, THREE.Vector3> = {
  top: new THREE.Vector3(0, 1, 0),
  side: new THREE.Vector3(0, 0, 1),
};

const _lockedAxisOffset = new THREE.Vector3();

function snapLockedCamera(
  view: ViewKind,
  camera: THREE.Camera,
  lookAt: THREE.Vector3,
  distance: number,
  up: THREE.Vector3,
): void {
  _lockedAxisOffset.copy(LOCKED_VIEW_AXIS[view]).multiplyScalar(distance);
  camera.position.copy(lookAt).add(_lockedAxisOffset);
  camera.up.copy(up);
  camera.lookAt(lookAt);
}

type CameraRigProps = {
  layout: CircuitsTracedLayout;
  view: ViewKind;
  locked: boolean;
  viewToken: number;
  fitToken: number;
};

function CameraRig({
  layout,
  view,
  locked,
  viewToken,
  fitToken,
}: CameraRigProps) {
  const camera = useThree((s) => s.camera);
  const gl = useThree((s) => s.gl);
  const size = useThree((s) => s.size);
  const controlsRef = useRef<ElementRef<typeof OrbitControls> | null>(null);
  const presets = useMemo(() => computePresets(layout), [layout]);
  const presetsRef = useRef(presets);
  presetsRef.current = presets;
  const spanRef = useRef(layout.span);
  spanRef.current = layout.span;
  const sizeRef = useRef(size);
  sizeRef.current = size;
  const viewDistanceRef = useRef(
    presets.top.pos.distanceTo(presets.target),
  );
  const orbitTargetRef = useRef(presets.target.clone());
  const [controlsReady, setControlsReady] = useState(false);
  const prevFitToken = useRef(fitToken);
  const shiftHeld = useRef(false);
  const lockedRef = useRef(locked);
  lockedRef.current = locked;

  const initControlsTarget = useCallback(() => {
    const controls = controlsRef.current;
    if (!controls || controlsReady) return;

    const p = presetsRef.current;
    const preset = view === "top" ? p.top : p.side;
    controls.target.copy(p.target);
    orbitTargetRef.current.copy(p.target);
    viewDistanceRef.current = applyFitCamera(
      camera,
      preset,
      p.target,
      sizeRef.current,
      spanRef.current,
    );
    if (lockedRef.current) {
      snapLockedCamera(
        view,
        camera,
        p.target,
        viewDistanceRef.current,
        preset.up,
      );
    }
    controls.update();
    setControlsReady(true);
  }, [view, camera, controlsReady]);

  const bindControls = useCallback(
    (node: ElementRef<typeof OrbitControls> | null) => {
      controlsRef.current = node;
      if (node) initControlsTarget();
    },
    [initControlsTarget],
  );

  useLayoutEffect(() => {
    initControlsTarget();
  }, [initControlsTarget, presets]);

  // Preserve framing when the active camera swaps (ortho <-> perspective). The
  // drei camera's makeDefault effect changes `camera`, which may recreate
  // OrbitControls — orbitTargetRef holds the last target across that remount.
  const prevCameraRef = useRef(camera);
  useLayoutEffect(() => {
    if (prevCameraRef.current === camera) return;
    const prevCamera = prevCameraRef.current;
    prevCameraRef.current = camera;
    const controls = controlsRef.current;
    if (!controls) return;

    const p = presetsRef.current;
    const preset = view === "top" ? p.top : p.side;
    const lookTarget = orbitTargetRef.current.clone();
    viewDistanceRef.current = preserveCameraOnProjectionSwap(
      prevCamera,
      camera,
      lookTarget,
      sizeRef.current,
    );
    controls.target.copy(lookTarget);
    if (lockedRef.current) {
      snapLockedCamera(
        view,
        camera,
        lookTarget,
        viewDistanceRef.current,
        preset.up,
      );
    }
    controls.update();
  }, [camera, view]);

  const syncMouseButtons = useCallback((shift: boolean) => {
    const controls = controlsRef.current;
    if (!controls) return;
    const selectTool = useCircuitTuning.getState().editTool === "select";
    if (selectTool && shift) {
      // Shift+drag is box-select — don't map left button to pan/rotate.
      controls.mouseButtons = {
        LEFT: THREE.MOUSE.ROTATE,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN,
      };
      return;
    }
    if (lockedRef.current) {
      // Pinned to top/side: drag only pans, never rotates.
      controls.mouseButtons = {
        LEFT: THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN,
      };
      return;
    }
    // Free orbit: drag rotates, shift+drag pans.
    controls.mouseButtons = {
      LEFT: shift ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.PAN,
    };
  }, []);

  // Re-map buttons whenever the lock state flips.
  useEffect(() => {
    syncMouseButtons(shiftHeld.current);
  }, [locked, syncMouseButtons]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Shift") return;
      shiftHeld.current = true;
      syncMouseButtons(true);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key !== "Shift") return;
      shiftHeld.current = false;
      syncMouseButtons(false);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [syncMouseButtons]);

  useEffect(() => {
    const dom = gl.domElement;
    const onPointerDown = (e: PointerEvent) => syncMouseButtons(e.shiftKey);
    dom.addEventListener("pointerdown", onPointerDown, true);
    syncMouseButtons(false);
    return () => dom.removeEventListener("pointerdown", onPointerDown, true);
  }, [gl, syncMouseButtons]);

  // After a locked pan/zoom, re-square the camera once — not every frame.
  useEffect(() => {
    if (!locked) return;
    const dom = gl.domElement;

    const resquare = () => {
      const controls = controlsRef.current;
      if (!controls) return;
      const preset =
        view === "top" ? presetsRef.current.top : presetsRef.current.side;
      const lookAt = controls.target;
      const distance =
        view === "top"
          ? Math.max(camera.position.y - lookAt.y, 0.5)
          : Math.max(camera.position.z - lookAt.z, 0.5);
      viewDistanceRef.current = distance;
      snapLockedCamera(view, camera, lookAt, distance, preset.up);
      controls.update();
    };

    let wheelTimer = 0;
    const onWheel = () => {
      window.clearTimeout(wheelTimer);
      wheelTimer = window.setTimeout(resquare, 80);
    };

    dom.addEventListener("pointerup", resquare);
    dom.addEventListener("wheel", onWheel, { passive: true });
    return () => {
      dom.removeEventListener("pointerup", resquare);
      dom.removeEventListener("wheel", onWheel);
      window.clearTimeout(wheelTimer);
    };
  }, [locked, view, camera, gl]);

  const anim = useRef<{
    fromPos: THREE.Vector3;
    toPos: THREE.Vector3;
    fromUp: THREE.Vector3;
    toUp: THREE.Vector3;
    lookTarget: THREE.Vector3;
    start: number;
  } | null>(null);

  // Animate to a locked preset. Layout edits must not retrigger this — only
  // explicit view / fit / lock changes do.
  useEffect(() => {
    if (!controlsReady) return;

    const p = presetsRef.current;
    const controls = controlsRef.current;
    const preset = view === "top" ? p.top : p.side;
    const isFit = fitToken !== prevFitToken.current;
    prevFitToken.current = fitToken;

    // Free orbit: the user drives the camera. Fit still recenters + reframes.
    if (!locked) {
      anim.current = null;
      if (isFit && controls) {
        controls.target.copy(p.target);
        viewDistanceRef.current = applyFitCamera(
          camera,
          preset,
          p.target,
          sizeRef.current,
          spanRef.current,
        );
        controls.update();
      }
      return;
    }

    const lookTarget = isFit
      ? p.target.clone()
      : (controls?.target.clone() ?? p.target.clone());

    if (isFit && controls) {
      controls.target.copy(lookTarget);
      viewDistanceRef.current = applyFitCamera(
        camera,
        preset,
        p.target,
        sizeRef.current,
        spanRef.current,
      );
    }

    const axis = LOCKED_VIEW_AXIS[view].clone().multiplyScalar(
      viewDistanceRef.current,
    );
    anim.current = {
      fromPos: camera.position.clone(),
      toPos: lookTarget.clone().add(axis),
      fromUp: camera.up.clone(),
      toUp: preset.up.clone(),
      lookTarget,
      start: performance.now(),
    };
  }, [view, locked, viewToken, fitToken, controlsReady]);

  useFrame(() => {
    const controls = controlsRef.current;
    if (!controls) return;

    if (!anim.current) {
      orbitTargetRef.current.copy(controls.target);
    }

    const a = anim.current;
    if (a) {
      controls.enabled = false;
      const t = Math.min(1, (performance.now() - a.start) / VIEW_ANIM_MS);
      const e = easeInOutCubic(t);

      const fromOff = a.fromPos.clone().sub(a.lookTarget);
      const toOff = a.toPos.clone().sub(a.lookTarget);
      const len = THREE.MathUtils.lerp(fromOff.length(), toOff.length(), e);
      const dirFrom = fromOff.clone().normalize();
      const dirTo = toOff.clone().normalize();
      const qFull = new THREE.Quaternion().setFromUnitVectors(dirFrom, dirTo);
      const qStep = new THREE.Quaternion().slerpQuaternions(
        new THREE.Quaternion(),
        qFull,
        e,
      );
      const curOff = dirFrom.applyQuaternion(qStep).multiplyScalar(len);

      camera.position.copy(a.lookTarget).add(curOff);
      camera.up.copy(a.fromUp.clone().lerp(a.toUp, e).normalize());
      camera.lookAt(a.lookTarget);

      if (t >= 1) {
        snapLockedCamera(
          view,
          camera,
          a.lookTarget,
          viewDistanceRef.current,
          a.toUp,
        );
        controls.target.copy(a.lookTarget);
        controls.update();
        anim.current = null;
      }
      return;
    }

    const st = useCircuitTuning.getState();
    const shiftBoxSelect =
      st.editTool === "select" && shiftHeld.current;
    const block =
      st.isDraggingVertex ||
      st.editTool !== "select" ||
      shiftBoxSelect;
    controls.enabled =
      !shiftBoxSelect &&
      !st.isDraggingVertex &&
      st.editTool === "select";
    controls.enableRotate = !locked && !block;
    controls.enablePan = !block;
    controls.enableZoom = true;
  });

  return (
    <OrbitControls
      ref={bindControls}
      makeDefault
      enableDamping
      dampingFactor={0.12}
      minZoom={1}
      maxZoom={4000}
      minDistance={0.5}
      maxDistance={8000}
    />
  );
}

// --- Mesh gizmos (move / scale / select) ------------------------------------

const MESH_HANDLES: MeshHandle[] = ["nw", "ne", "sw", "se"];

function boxEdgePositions(b: MeshBounds, y0: number, y1: number): Float32Array {
  const { minX, maxX, minZ, maxZ } = b;
  const c = [
    [minX, y0, minZ],
    [maxX, y0, minZ],
    [maxX, y0, maxZ],
    [minX, y0, maxZ],
    [minX, y1, minZ],
    [maxX, y1, minZ],
    [maxX, y1, maxZ],
    [minX, y1, maxZ],
  ];
  const edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0],
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 4],
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7],
  ];
  const arr = new Float32Array(edges.length * 6);
  edges.forEach(([a, bb], i) => {
    arr.set(c[a], i * 6);
    arr.set(c[bb], i * 6 + 3);
  });
  return arr;
}

function CornerHandle({
  meshId,
  handle,
  position,
  startBounds,
  boardY,
}: {
  meshId: string;
  handle: MeshHandle;
  position: Vec3;
  startBounds: MeshBounds;
  boardY: number;
}) {
  const { camera, gl } = useThree();
  const pushUndo = useCircuitTuning((s) => s.pushUndo);
  const setMeshBounds = useCircuitTuning((s) => s.setMeshBounds);
  const setDraggingVertex = useCircuitTuning((s) => s.setDraggingVertex);
  const dragging = useRef(false);

  const onPointerDown = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      e.nativeEvent.preventDefault();
      pushUndo();
      dragging.current = true;
      setDraggingVertex(true);
      gl.domElement.setPointerCapture(e.pointerId);
    },
    [pushUndo, setDraggingVertex, gl.domElement],
  );

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!dragging.current) return;
      const hit = pickBoard(
        e.clientX,
        e.clientY,
        boardY,
        camera,
        gl.domElement,
      );
      if (!hit) return;
      setMeshBounds(
        meshId,
        resizeMeshFromCorner(startBounds, handle, hit.x, hit.z),
      );
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      setDraggingVertex(false);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [
    meshId,
    handle,
    startBounds,
    boardY,
    camera,
    gl.domElement,
    setMeshBounds,
    setDraggingVertex,
  ]);

  return (
    <mesh position={position} renderOrder={1001} onPointerDown={onPointerDown}>
      <sphereGeometry args={[0.18, 12, 10]} />
      <meshBasicMaterial color="#ffffff" depthTest={false} />
    </mesh>
  );
}

function VariantThumb({ variant }: { variant: VariantEntry }) {
  return (
    <svg
      className="c3d__variant-thumb"
      viewBox={variant.thumb.viewBox}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden
    >
      <path d={variant.thumb.d} />
    </svg>
  );
}

function MeshItem({
  mesh,
  selected,
  soleSelected,
  boardY,
  boxTop,
  hasOutline,
}: {
  mesh: CircuitMesh;
  selected: boolean;
  soleSelected: boolean;
  boardY: number;
  boxTop: number;
  hasOutline: boolean;
}) {
  const { camera, gl } = useThree();
  const editTool = useCircuitTuning((s) => s.editTool);
  const move = useRef<{
    start: MeshBounds;
    hitX: number;
    hitZ: number;
    pushed: boolean;
  } | null>(null);

  const cx = (mesh.minX + mesh.maxX) / 2;
  const cz = (mesh.minZ + mesh.maxZ) / 2;
  const w = mesh.maxX - mesh.minX;
  const h = mesh.maxZ - mesh.minZ;
  const midY = (boardY + boxTop) / 2;
  const boxH = Math.max(boxTop - boardY, 0.4);

  const onPointerDown = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      if (editTool !== "select") return;
      if (e.shiftKey) return;
      e.stopPropagation();
      const store = useCircuitTuning.getState();

      if (e.metaKey) {
        const next = store.selectedMeshIds.includes(mesh.id)
          ? store.selectedMeshIds.filter((id) => id !== mesh.id)
          : [...store.selectedMeshIds, mesh.id];
        store.setBoxSelection(store.selectedLineIds, next);
        return;
      }

      store.selectMesh(mesh.id);
      const hit = pickBoard(
        e.clientX,
        e.clientY,
        boardY,
        camera,
        gl.domElement,
      );
      if (!hit) return;
      move.current = {
        start: {
          minX: mesh.minX,
          maxX: mesh.maxX,
          minZ: mesh.minZ,
          maxZ: mesh.maxZ,
        },
        hitX: hit.x,
        hitZ: hit.z,
        pushed: false,
      };
      store.setDraggingVertex(true);
      gl.domElement.setPointerCapture(e.pointerId);
    },
    [editTool, mesh, boardY, camera, gl.domElement],
  );

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      const m = move.current;
      if (!m) return;
      const hit = pickBoard(
        e.clientX,
        e.clientY,
        boardY,
        camera,
        gl.domElement,
      );
      if (!hit) return;
      const dx = hit.x - m.hitX;
      const dz = hit.z - m.hitZ;
      const store = useCircuitTuning.getState();
      if (!m.pushed && (Math.abs(dx) > 0.02 || Math.abs(dz) > 0.02)) {
        store.pushUndo();
        m.pushed = true;
      }
      if (m.pushed)
        store.setMeshBounds(mesh.id, moveMeshBounds(m.start, dx, dz));
    };
    const onUp = () => {
      if (!move.current) return;
      move.current = null;
      useCircuitTuning.getState().setDraggingVertex(false);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [mesh.id, boardY, camera, gl.domElement]);

  const edges = useMemo(
    () => boxEdgePositions(mesh, boardY, boxTop),
    [mesh, boardY, boxTop],
  );

  return (
    <group>
      {/* Invisible pick body for selection + drag-move. */}
      <mesh position={[cx, midY, cz]} onPointerDown={onPointerDown}>
        <boxGeometry args={[Math.max(w, 0.2), boxH, Math.max(h, 0.2)]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* User-placed meshes have no real outline — show a visible placeholder box. */}
      {!hasOutline ? (
        <>
          <mesh position={[cx, midY, cz]}>
            <boxGeometry args={[Math.max(w, 0.2), boxH, Math.max(h, 0.2)]} />
            <meshBasicMaterial
              color="#2fd6c2"
              transparent
              opacity={0.28}
              depthWrite={false}
            />
          </mesh>
          <lineSegments renderOrder={998}>
            <bufferGeometry>
              <bufferAttribute attach="attributes-position" args={[edges, 3]} />
            </bufferGeometry>
            <lineBasicMaterial
              color="#2fd6c2"
              transparent
              opacity={0.7}
              depthTest={false}
            />
          </lineSegments>
        </>
      ) : null}

      {selected ? (
        <lineSegments renderOrder={1000}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[edges, 3]} />
          </bufferGeometry>
          <lineBasicMaterial color="#ffffff" transparent depthTest={false} />
        </lineSegments>
      ) : null}

      {soleSelected
        ? MESH_HANDLES.map((handle) => {
            const hx =
              handle === "nw" || handle === "sw" ? mesh.minX : mesh.maxX;
            const hz =
              handle === "nw" || handle === "ne" ? mesh.minZ : mesh.maxZ;
            return (
              <CornerHandle
                key={handle}
                meshId={mesh.id}
                handle={handle}
                position={[hx, boxTop, hz]}
                startBounds={{
                  minX: mesh.minX,
                  maxX: mesh.maxX,
                  minZ: mesh.minZ,
                  maxZ: mesh.maxZ,
                }}
                boardY={boardY}
              />
            );
          })
        : null}
    </group>
  );
}

function AddMeshDragGhost({
  ghost,
  paths,
  view,
  centerZ,
  model,
  catalog,
}: {
  ghost: PaletteMeshGhost;
  paths: GridPath[];
  view: ViewKind;
  centerZ: number;
  model: OutlineModel;
  catalog: VariantCatalog | null;
}) {
  const { camera, gl } = useThree();
  const boardYVal = useMemo(() => boardY(paths), [paths]);
  const boxTop = Math.max(model.yMax, model.yMin + 0.6);

  const hit = useMemo(
    () =>
      pickBoardPoint(
        ghost.clientX,
        ghost.clientY,
        camera,
        gl.domElement,
        boardYVal,
        view,
        centerZ,
      ),
    [
      ghost.clientX,
      ghost.clientY,
      camera,
      gl.domElement,
      boardYVal,
      view,
      centerZ,
    ],
  );

  const ghostMesh = useMemo((): CircuitMesh | null => {
    if (!hit) return null;
    const { w, h } = ghost.size;
    return {
      id: "__palette-ghost__",
      kind: ghost.kind,
      minX: hit[0] - w / 2,
      maxX: hit[0] + w / 2,
      minZ: hit[2] - h / 2,
      maxZ: hit[2] + h / 2,
      ...(ghost.variant ? { variant: ghost.variant } : {}),
    };
  }, [ghost.kind, ghost.size, ghost.variant, hit]);

  const outlinePaths = useMemo(() => {
    if (!ghostMesh || !ghost.variant || !catalog) return [];
    return variantOutlinePaths([ghostMesh], catalog, boardYVal);
  }, [boardYVal, catalog, ghost.variant, ghostMesh]);

  const edges = useMemo(
    () => (ghostMesh ? boxEdgePositions(ghostMesh, boardYVal, boxTop) : null),
    [ghostMesh, boardYVal, boxTop],
  );

  if (!ghostMesh || !edges) return null;

  const cx = (ghostMesh.minX + ghostMesh.maxX) / 2;
  const cz = (ghostMesh.minZ + ghostMesh.maxZ) / 2;
  const w = ghostMesh.maxX - ghostMesh.minX;
  const h = ghostMesh.maxZ - ghostMesh.minZ;
  const midY = (boardYVal + boxTop) / 2;
  const boxH = Math.max(boxTop - boardYVal, 0.4);
  const hasVariantOutline = outlinePaths.length > 0;

  return (
    <group>
      {!hasVariantOutline ? (
        <>
          <mesh position={[cx, midY, cz]} renderOrder={1001}>
            <boxGeometry args={[Math.max(w, 0.2), boxH, Math.max(h, 0.2)]} />
            <meshBasicMaterial
              color="#2fd6c2"
              transparent
              opacity={0.2}
              depthWrite={false}
            />
          </mesh>
          <lineSegments renderOrder={1002}>
            <bufferGeometry>
              <bufferAttribute attach="attributes-position" args={[edges, 3]} />
            </bufferGeometry>
            <lineBasicMaterial
              color="#2fd6c2"
              transparent
              opacity={0.55}
              depthTest={false}
            />
          </lineSegments>
        </>
      ) : (
        <>
          <mesh position={[cx, midY, cz]} renderOrder={1000}>
            <boxGeometry args={[Math.max(w, 0.2), boxH, Math.max(h, 0.2)]} />
            <meshBasicMaterial
              color="#2fd6c2"
              transparent
              opacity={0.1}
              depthWrite={false}
            />
          </mesh>
          <TronGrid
            paths={outlinePaths}
            showBackgroundGrid={false}
            animated={false}
            screenLineWidth={EDITOR_SCREEN_LINE_WIDTH}
          />
        </>
      )}
    </group>
  );
}

function meshHasRenderedOutline(
  mesh: CircuitMesh,
  model: OutlineModel,
  catalog: VariantCatalog | null,
): boolean {
  if (model.segmentsByComp.has(mesh.id)) return true;
  return Boolean(mesh.variant && catalog?.byId.has(mesh.variant));
}

function MeshLayer({
  meshes,
  model,
  catalog,
}: {
  meshes: CircuitMesh[];
  model: OutlineModel;
  catalog: VariantCatalog | null;
}) {
  const selectedMeshIds = useCircuitTuning((s) => s.selectedMeshIds);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedSet = useMemo(
    () => new Set(selectedMeshIds),
    [selectedMeshIds],
  );
  const boardY = model.yMin;
  const boxTop = Math.max(model.yMax, model.yMin + 0.6);
  const soleId =
    selectedMeshIds.length === 1 && selectedLineIds.length === 0
      ? selectedMeshIds[0]
      : null;

  return (
    <group>
      {meshes.map((m) => (
        <MeshItem
          key={m.id}
          mesh={m}
          selected={selectedSet.has(m.id)}
          soleSelected={m.id === soleId}
          boardY={boardY}
          boxTop={boxTop}
          hasOutline={meshHasRenderedOutline(m, model, catalog)}
        />
      ))}
    </group>
  );
}

// --- Scene ------------------------------------------------------------------

type SceneData = { paths: GridPath[]; meshes: CircuitMesh[] };

function EditorScene({
  view,
  locked,
  projection,
  viewToken,
  fitToken,
  paletteGhost,
  onData,
  onBoardPickReady,
  cameraRef,
}: {
  view: ViewKind;
  locked: boolean;
  projection: ProjectionKind;
  viewToken: number;
  fitToken: number;
  paletteGhost: PaletteMeshGhost | null;
  onData: (d: SceneData) => void;
  onBoardPickReady: (api: BoardPickApi | null) => void;
  cameraRef: React.MutableRefObject<THREE.Camera | null>;
}) {
  const { scene } = useGLTF(OUTLINE_GLB_URL);
  const catalog = useVariantCatalog();
  const topology = useCircuitTuning((s) => s.topology);
  const meshEdits = useCircuitTuning((s) => s.meshEdits);

  const raw = useMemo(() => buildRawCircuitPaths(scene), [scene]);
  const model = useMemo(() => buildOutlineModel(raw), [raw]);
  const baselineMeshes = useMemo(
    () => footprintsToMeshes(model.footprints),
    [model],
  );

  const editableBaseline = useMemo(
    () => raw.filter((p) => isEditableLine(p.id)),
    [raw],
  );
  const editablePaths = useMemo(
    () => applyTopology(editableBaseline, topology),
    [editableBaseline, topology],
  );

  const resolvedMeshes = useMemo(
    () => resolveMeshes(baselineMeshes, meshEdits),
    [baselineMeshes, meshEdits],
  );
  const outlinePaths = useMemo(() => {
    const baseline = transformedOutlinePaths(model, resolvedMeshes);
    if (!catalog) return baseline;
    return [
      ...baseline,
      ...variantOutlinePaths(resolvedMeshes, catalog, model.yMin),
    ];
  }, [model, resolvedMeshes, catalog]);

  const layout = useMemo(
    () => layoutFromPaths([...outlinePaths, ...editablePaths]),
    [outlinePaths, editablePaths],
  );

  useEffect(() => {
    onData({ paths: editablePaths, meshes: resolvedMeshes });
  }, [editablePaths, resolvedMeshes, onData]);

  return (
    <>
      <color attach="background" args={["#04090b"]} />
      {/* The active projection camera. CameraRig owns its transform/zoom, so we
          only set static frustum params here and never position — that avoids
          drei re-applying props and fighting the rig every render. */}
      {projection === "ortho" ? (
        <OrthographicCamera makeDefault near={0.1} far={4000} />
      ) : (
        <PerspectiveCamera makeDefault fov={FOV} near={0.1} far={4000} />
      )}
      <CameraRig
        layout={layout}
        view={view}
        locked={locked}
        viewToken={viewToken}
        fitToken={fitToken}
      />
      {/* Real component outlines (the "meshes") — static, full length. */}
      <TronGrid
        paths={outlinePaths}
        showBackgroundGrid={false}
        animated={false}
        screenLineWidth={EDITOR_SCREEN_LINE_WIDTH}
      />
      {/* Editable circuit traces — static, full length. */}
      <TronGrid
        paths={editablePaths}
        showBackgroundGrid={false}
        animated={false}
        screenLineWidth={EDITOR_SCREEN_LINE_WIDTH}
      />
      <MeshLayer meshes={resolvedMeshes} model={model} catalog={catalog} />
      {paletteGhost ? (
        <AddMeshDragGhost
          ghost={paletteGhost}
          paths={editablePaths}
          view={view}
          centerZ={layout.center[2]}
          model={model}
          catalog={catalog}
        />
      ) : null}
      <BoardPickBridge
        paths={editablePaths}
        view={view}
        centerZ={layout.center[2]}
        onReady={onBoardPickReady}
      />
      <CameraRefBridge cameraRef={cameraRef} />
      <CircuitSelectionLayer
        paths={editablePaths}
        meshes={resolvedMeshes}
        view={view}
        locked={locked}
        centerZ={layout.center[2]}
        shiftMoveHandledByOverlay
      />
    </>
  );
}

// --- Editor shell (overlay UI + key handling) -------------------------------

export default function Circuit3DEditor() {
  useLayoutEffect(() => {
    useLineConfig.getState().set(LINE_CONFIG_OVERRIDES);
  }, []);

  const [view, setView] = useState<ViewKind>("top");
  const [locked, setLocked] = useState(true);
  const [projection, setProjection] = useState<ProjectionKind>("ortho");
  const [viewToken, setViewToken] = useState(0);
  const [fitToken, setFitToken] = useState(0);
  const [status, setStatus] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [boxSelectRect, setBoxSelectRect] = useState<ScreenRect | null>(null);
  const [pickCanvas, setPickCanvas] = useState<HTMLCanvasElement | null>(null);
  const [shiftHeld, setShiftHeld] = useState(false);
  const { flash: flashShortcut, btnClass, btnTitle } = useShortcutButtonFlash();

  const dataRef = useRef<SceneData>({ paths: [], meshes: [] });
  const cameraRef = useRef<THREE.Camera | null>(null);
  const boardPickRef = useRef<BoardPickApi | null>(null);
  const paletteDragRef = useRef<PaletteDrag | null>(null);
  const paletteResizeRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startScale: number;
  } | null>(null);
  const [paletteScale, setPaletteScale] = useState(readPaletteScale);
  const [armedFlyoutKind, setArmedFlyoutKind] = useState<MeshKind | null>(null);
  const [hoverPreviewVariantId, setHoverPreviewVariantId] = useState<
    string | null
  >(null);
  const [paletteGhost, setPaletteGhost] = useState<PaletteMeshGhost | null>(
    null,
  );
  const onData = useCallback((d: SceneData) => {
    dataRef.current = d;
    if (d.paths.length > 0) setLoaded(true);
  }, []);
  const onBoardPickReady = useCallback((api: BoardPickApi | null) => {
    boardPickRef.current = api;
    setPickCanvas(api?.canvas ?? null);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Shift") setShiftHeld(true);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key === "Shift") setShiftHeld(false);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  const catalog = useVariantCatalog();
  const editTool = useCircuitTuning((s) => s.editTool);
  const addMeshKind = useCircuitTuning((s) => s.addMeshKind);
  const addMeshVariant = useCircuitTuning((s) => s.addMeshVariant);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedMeshIds = useCircuitTuning((s) => s.selectedMeshIds);
  const clipboardLineCount = useCircuitTuning((s) => s.clipboardLineCount);
  const snapMergeEps = useCircuitTuning((s) => s.snapMergeEps);
  const setSnapMergeEps = useCircuitTuning((s) => s.setSnapMergeEps);
  const setTool = useCircuitTuning((s) => s.setEditTool);

  const armAddMesh = useCallback(
    (kind: MeshKind, size: MeshSize, variant: string | null) => {
      useCircuitTuning.setState({
        editTool: "addMesh",
        addMeshKind: kind,
        addMeshSize: size,
        addMeshVariant: variant,
        addLineStart: null,
        selectedLineIds: [],
        selectedVertex: null,
        selectedMeshIds: [],
      });
    },
    [],
  );

  const endPalettePointer = useCallback(() => {
    paletteDragRef.current = null;
    setArmedFlyoutKind(null);
    setHoverPreviewVariantId(null);
    setPaletteGhost(null);
    document.body.classList.remove("c3d--palette-dragging");
  }, []);

  const onPaletteResizeDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      paletteResizeRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        startScale: paletteScale,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
      document.body.classList.add("c3d--palette-resizing");
    },
    [paletteScale],
  );

  const onPaletteResizeMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const d = paletteResizeRef.current;
      if (!d || e.pointerId !== d.pointerId) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      const delta = (-dx + dy) / PALETTE_SCALE_DRAG;
      setPaletteScale(
        Math.max(
          MIN_PALETTE_SCALE,
          Math.min(MAX_PALETTE_SCALE, d.startScale + delta),
        ),
      );
    },
    [],
  );

  const endPaletteResize = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const d = paletteResizeRef.current;
      if (!d || e.pointerId !== d.pointerId) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      const delta = (-dx + dy) / PALETTE_SCALE_DRAG;
      const next = Math.max(
        MIN_PALETTE_SCALE,
        Math.min(MAX_PALETTE_SCALE, d.startScale + delta),
      );
      paletteResizeRef.current = null;
      document.body.classList.remove("c3d--palette-resizing");
      setPaletteScale(next);
      try {
        localStorage.setItem(PALETTE_SCALE_KEY, String(next));
        localStorage.removeItem(PALETTE_W_KEY);
      } catch {
        /* ignore */
      }
    },
    [],
  );

  const onPalettePointerMove = useCallback((e: PointerEvent) => {
    const d = paletteDragRef.current;
    if (!d || e.pointerId !== d.pointerId) return;

    const outside = pointerOutsideRect(
      e.clientX,
      e.clientY,
      d.sourceEl.getBoundingClientRect(),
    );

    if (outside) {
      if (!d.dragging) {
        d.dragging = true;
        setHoverPreviewVariantId(null);
        document.body.classList.add("c3d--palette-dragging");
      }
      const pt = boardPickRef.current?.pick(e.clientX, e.clientY);
      if (pt) d.lastPick = pt;
      setPaletteGhost({
        kind: d.kind,
        size: d.size,
        variant: d.variant,
        clientX: e.clientX,
        clientY: e.clientY,
      });
    } else {
      setPaletteGhost(null);
    }
  }, []);

  const onPalettePointerUp = useCallback(
    (e: PointerEvent) => {
      const d = paletteDragRef.current;
      if (!d || e.pointerId !== d.pointerId) return;

      window.removeEventListener("pointermove", onPalettePointerMove);
      window.removeEventListener("pointerup", onPalettePointerUp);
      window.removeEventListener("pointercancel", onPalettePointerUp);

      if (d.dragging) {
        const pt =
          boardPickRef.current?.pick(e.clientX, e.clientY) ?? d.lastPick;
        if (pt) {
          useCircuitTuning.setState({
            addMeshKind: d.kind,
            addMeshSize: d.size,
            addMeshVariant: d.variant,
          });
          useCircuitTuning.getState().pushUndo();
          useCircuitTuning.getState().addMeshAt(d.kind, pt.x, pt.z);
        }
      } else if (d.wasArmed) {
        useCircuitTuning.getState().cancelEditTool();
      }

      endPalettePointer();
    },
    [endPalettePointer, onPalettePointerMove],
  );

  const onPalettePointerDown = useCallback(
    (
      e: React.PointerEvent<HTMLButtonElement>,
      kind: MeshKind,
      size: MeshSize,
      variant: string | null,
    ) => {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      setHoverPreviewVariantId(null);

      const st = useCircuitTuning.getState();
      const wasArmed =
        st.editTool === "addMesh" &&
        st.addMeshKind === kind &&
        st.addMeshVariant === variant &&
        st.addMeshSize?.w === size.w &&
        st.addMeshSize?.h === size.h;

      armAddMesh(kind, size, variant);
      setArmedFlyoutKind(kind);
      paletteDragRef.current = {
        kind,
        size,
        variant,
        startX: e.clientX,
        startY: e.clientY,
        dragging: false,
        pointerId: e.pointerId,
        sourceEl: e.currentTarget,
        wasArmed,
        lastPick: null,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
      window.addEventListener("pointermove", onPalettePointerMove);
      window.addEventListener("pointerup", onPalettePointerUp);
      window.addEventListener("pointercancel", onPalettePointerUp);
    },
    [armAddMesh, onPalettePointerMove, onPalettePointerUp],
  );

  const flashStatus = useCallback((msg: string) => {
    setStatus(msg);
    window.setTimeout(() => setStatus(""), 2500);
  }, []);

  const onSnap45 = useCallback(() => {
    const { paths, meshes } = dataRef.current;
    const { changed, merged, collapsed, meshSnapped } = useCircuitTuning
      .getState()
      .snapAnglesToGrid(paths, meshes);
    const parts: string[] = [];
    if (changed > 0)
      parts.push(`snapped ${changed} line${changed === 1 ? "" : "s"}`);
    if (merged > 0)
      parts.push(`merged ${merged} vertex${merged === 1 ? "" : "es"}`);
    if (collapsed > 0)
      parts.push(`rejoined ${collapsed} split line${collapsed === 1 ? "" : "s"}`);
    if (meshSnapped > 0)
      parts.push(
        `connected ${meshSnapped} endpoint${meshSnapped === 1 ? "" : "s"}`,
      );
    flashStatus(parts.length ? parts.join(", ") : "nothing to snap or merge");
  }, [flashStatus]);

  const toggleView = useCallback(() => {
    setView((v) => (v === "top" ? "side" : "top"));
    setLocked(true);
    setViewToken((n) => n + 1);
  }, []);

  const toggleProjection = useCallback(() => {
    setProjection((p) => (p === "ortho" ? "perspective" : "ortho"));
  }, []);

  useEffect(() => {
    if (!locked && editTool === "addLine") {
      setTool("select");
    }
  }, [editTool, locked, setTool]);

  // Register the path resolver so the store's copy reads live trace geometry.
  useEffect(() => {
    setEditPathsGetter(() => dataRef.current.paths);
    return () => setEditPathsGetter(null);
  }, []);

  // Editor shortcuts: a (add line), r (snap 45), f (toggle view), l (lock).
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === "a") {
        e.preventDefault();
        if (!locked) return;
        const store = useCircuitTuning.getState();
        const next = store.editTool === "addLine" ? "select" : "addLine";
        store.setEditTool(next);
        flashShortcut(next === "addLine" ? SHORTCUT_BTN.addLine : SHORTCUT_BTN.select);
      } else if (k === "r") {
        e.preventDefault();
        flashShortcut(SHORTCUT_BTN.snap45);
        onSnap45();
      } else if (k === "f") {
        e.preventDefault();
        flashShortcut(view === "top" ? SHORTCUT_BTN.side : SHORTCUT_BTN.top);
        toggleView();
      } else if (k === "l") {
        e.preventDefault();
        flashShortcut(SHORTCUT_BTN.lock);
        setLocked((v) => !v);
      } else if (k === "o") {
        e.preventDefault();
        flashShortcut(SHORTCUT_BTN.projection);
        toggleProjection();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [flashShortcut, locked, onSnap45, toggleProjection, toggleView, view]);

  const onSave = useCallback(async () => {
    const ok = await useCircuitTuning.getState().saveAsDefault();
    flashStatus(
      ok
        ? "saved to circuits-tuning.json"
        : "downloaded JSON (dev save unavailable)",
    );
  }, [flashStatus]);

  const onCopy = useCallback(() => {
    const count = useCircuitTuning.getState().selectedLineIds.filter(
      (id) => id.startsWith("trace-") || id.startsWith("user-"),
    ).length;
    if (count === 0) {
      flashStatus("select one or more lines to copy");
      return;
    }
    if (useCircuitTuning.getState().copySelectedLines()) {
      flashStatus(`copied ${count} line${count === 1 ? "" : "s"}`);
    }
  }, [flashStatus]);

  const onPaste = useCallback(() => {
    if (!useCircuitTuning.getState().pasteLines()) {
      flashStatus("nothing to paste — copy lines first");
      return;
    }
    const count = useCircuitTuning.getState().selectedLineIds.length;
    flashStatus(`pasted ${count} line${count === 1 ? "" : "s"}`);
  }, [flashStatus]);

  const onExport = useCallback(() => {
    const text = useCircuitTuning.getState().exportJSON();
    const blob = new Blob([`${text}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "circuits-tuning.json";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const fileRef = useRef<HTMLInputElement | null>(null);
  const onImportFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      const text = await file.text();
      const ok = useCircuitTuning.getState().importJSON(text);
      flashStatus(ok ? "imported tuning" : "import failed: invalid JSON");
    },
    [flashStatus],
  );

  const hasSelection = selectedLineIds.length > 0 || selectedMeshIds.length > 0;

  return (
    <div className="c3d">
      <div className="c3d__viewport">
        <Canvas
          className="c3d__canvas"
          gl={{ antialias: true, alpha: false }}
          onPointerMissed={(e) => {
            const st = useCircuitTuning.getState();
            // Keep the selected line while splitting so a missed click doesn't
            // force the user to re-select before trying again.
            if (e.shiftKey || st.isDraggingVertex || st.editTool === "split") {
              return;
            }
            st.clearSelection();
          }}
          onCreated={(state) => {
            state.raycaster.params.Line = { threshold: 0.3 };
            setPickCanvas(state.gl.domElement);
          }}
        >
          <Suspense fallback={null}>
            <EditorScene
              view={view}
              locked={locked}
              projection={projection}
              viewToken={viewToken}
              fitToken={fitToken}
              paletteGhost={paletteGhost}
              onData={onData}
              onBoardPickReady={onBoardPickReady}
              cameraRef={cameraRef}
            />
          </Suspense>
        </Canvas>

        <BoxSelectLayer
          active={shiftHeld && editTool === "select"}
          canvas={pickCanvas}
          cameraRef={cameraRef}
          dataRef={dataRef}
          onRectChange={setBoxSelectRect}
        />
        <BoxSelectOverlay rect={boxSelectRect} canvas={pickCanvas} />
      </div>

      <div className="c3d__toolbar">
        <div className="c3d__group">
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.select,
              editTool === "select" ? "c3d__btn c3d__btn--active" : "c3d__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.select)}
            onClick={() => setTool("select")}
          >
            Select
          </button>
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.addLine,
              editTool === "addLine" ? "c3d__btn c3d__btn--active" : "c3d__btn",
            )}
            disabled={!locked}
            title={
              locked
                ? btnTitle(SHORTCUT_BTN.addLine)
                : "Lock the view to add lines"
            }
            onClick={() => {
              if (!locked) return;
              setTool(editTool === "addLine" ? "select" : "addLine");
            }}
          >
            Add line
          </button>
        </div>

        <div className="c3d__sep" />

        <div className="c3d__group">
          <button
            type="button"
            className={
              editTool === "split" ? "c3d__btn c3d__btn--active" : "c3d__btn"
            }
            disabled={selectedLineIds.length !== 1 && editTool !== "split"}
            onClick={() => setTool(editTool === "split" ? "select" : "split")}
          >
            Split
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.delete, "c3d__btn c3d__btn--danger")}
            disabled={!hasSelection}
            title={btnTitle(SHORTCUT_BTN.delete)}
            onClick={() => useCircuitTuning.getState().deleteSelection()}
          >
            Delete
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.snap45, "c3d__btn")}
            title={btnTitle(SHORTCUT_BTN.snap45)}
            onClick={onSnap45}
          >
            Snap 45°
          </button>
          <label className="c3d__snap-merge">
            <span className="c3d__snap-merge-label">Snap merge</span>
            <input
              className="c3d__snap-merge-slider"
              type="range"
              min={0.05}
              max={1}
              step={0.01}
              value={snapMergeEps}
              onChange={(e) => setSnapMergeEps(Number(e.target.value))}
            />
            <span className="c3d__snap-merge-value">
              {snapMergeEps.toFixed(2)}
            </span>
          </label>
        </div>

        <div className="c3d__sep" />

        <div className="c3d__group">
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.top,
              view === "top" ? "c3d__btn c3d__btn--active" : "c3d__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.top)}
            onClick={() => {
              setView("top");
              setLocked(true);
              setViewToken((n) => n + 1);
            }}
          >
            Top
          </button>
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.side,
              view === "side" ? "c3d__btn c3d__btn--active" : "c3d__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.side)}
            onClick={() => {
              setView("side");
              setLocked(true);
              setViewToken((n) => n + 1);
            }}
          >
            Side
          </button>
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.lock,
              locked ? "c3d__btn c3d__btn--active" : "c3d__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.lock)}
            onClick={() => setLocked((v) => !v)}
          >
            {locked ? "Locked" : "Free"}
          </button>
          <button
            type="button"
            className="c3d__btn"
            onClick={() => setFitToken((n) => n + 1)}
          >
            Fit
          </button>
          <button
            type="button"
            className={btnClass(
              SHORTCUT_BTN.projection,
              projection === "ortho"
                ? "c3d__btn c3d__btn--active"
                : "c3d__btn",
            )}
            title={btnTitle(SHORTCUT_BTN.projection)}
            onClick={toggleProjection}
          >
            {projection === "ortho" ? "Ortho" : "Persp"}
          </button>
        </div>

        <div className="c3d__sep" />

        <div className="c3d__group">
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.copy, "c3d__btn")}
            disabled={selectedLineIds.length === 0}
            title={btnTitle(SHORTCUT_BTN.copy)}
            onClick={onCopy}
          >
            Copy
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.paste, "c3d__btn")}
            disabled={clipboardLineCount === 0}
            title={btnTitle(SHORTCUT_BTN.paste)}
            onClick={onPaste}
          >
            Paste
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.undo, "c3d__btn")}
            title={btnTitle(SHORTCUT_BTN.undo)}
            onClick={() => useCircuitTuning.getState().undo()}
          >
            Undo
          </button>
          <button
            type="button"
            className={btnClass(SHORTCUT_BTN.redo, "c3d__btn")}
            title={btnTitle(SHORTCUT_BTN.redo)}
            onClick={() => useCircuitTuning.getState().redo()}
          >
            Redo
          </button>
          <button type="button" className="c3d__btn" onClick={onSave}>
            Save
          </button>
          <button type="button" className="c3d__btn" onClick={onExport}>
            Export
          </button>
          <button
            type="button"
            className="c3d__btn"
            onClick={() => fileRef.current?.click()}
          >
            Import
          </button>
          <button
            type="button"
            className="c3d__btn"
            onClick={() => {
              useCircuitTuning.getState().resetAll();
              flashStatus("reset to committed default");
            }}
          >
            Reset
          </button>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="application/json"
          hidden
          onChange={onImportFile}
        />
      </div>

      <aside
        className="c3d__palette"
        style={
          { "--c3d-palette-scale": paletteScale } as CSSProperties
        }
      >
        <p className="c3d__palette-title">Meshes</p>
        <ul className="c3d__palette-types">
          {(catalog?.categories ?? []).map((group) => {
            const active =
              editTool === "addMesh" && addMeshKind === group.kind;
            const previewVariant = hoverPreviewVariantId
              ? group.variants.find((v) => v.id === hoverPreviewVariantId)
              : null;
            return (
              <li
                className={
                  armedFlyoutKind === group.kind
                    ? "c3d__palette-type c3d__palette-type--armed"
                    : "c3d__palette-type"
                }
                key={group.kind}
              >
                <button
                  type="button"
                  className={
                    active
                      ? "c3d__palette-type-btn c3d__palette-type-btn--active"
                      : "c3d__palette-type-btn"
                  }
                  style={{ "--mesh-accent": group.color } as CSSProperties}
                  title={`${group.label} — hover for variants`}
                >
                  <span className="c3d__palette-label">{group.label}</span>
                </button>
                <div
                  className="c3d__palette-flyout"
                  role="group"
                  aria-label={`${group.label} variants`}
                  onPointerLeave={() => {
                    if (!paletteDragRef.current) {
                      setHoverPreviewVariantId(null);
                    }
                  }}
                >
                  <div className="c3d__palette-variants">
                    {group.variants.map((variant) => {
                      const vActive =
                        editTool === "addMesh" &&
                        addMeshVariant === variant.id;
                      return (
                        <button
                          key={variant.id}
                          type="button"
                          className={
                            vActive
                              ? "c3d__variant c3d__variant--active"
                              : "c3d__variant"
                          }
                          style={
                            { "--mesh-accent": group.color } as CSSProperties
                          }
                          onPointerEnter={() => {
                            if (!paletteDragRef.current) {
                              setHoverPreviewVariantId(variant.id);
                            }
                          }}
                          onPointerDown={(e) => {
                            e.stopPropagation();
                            onPalettePointerDown(
                              e,
                              group.kind,
                              variant.placeSize,
                              variant.id,
                            );
                          }}
                          title={`Place ${variant.label} (click or drag onto board)`}
                        >
                          <VariantThumb variant={variant} />
                          <span className="c3d__variant-label">
                            {variant.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  {previewVariant ? (
                    <div className="c3d__variant-preview">
                      <MeshVariantPreview
                        variant={previewVariant}
                        color={group.color}
                      />
                      <span className="c3d__variant-preview-label">
                        {previewVariant.label}
                      </span>
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
        <div
          className="c3d__palette-resize"
          role="separator"
          aria-label="Resize meshes panel"
          onPointerDown={onPaletteResizeDown}
          onPointerMove={onPaletteResizeMove}
          onPointerUp={endPaletteResize}
          onPointerCancel={endPaletteResize}
        />
      </aside>

      <div className="c3d__status">
        {status && <span className="c3d__status-line--accent">{status}</span>}
        <span>
          {loaded
            ? editTool === "split"
              ? "click on the selected line where you want to split it"
              : hasSelection
              ? [
                  selectedLineIds.length > 0
                    ? `${selectedLineIds.length} line${selectedLineIds.length === 1 ? "" : "s"}`
                    : null,
                  selectedMeshIds.length > 0
                    ? `${selectedMeshIds.length} mesh${selectedMeshIds.length === 1 ? "" : "es"}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(", ")
              : editTool === "addMesh" && addMeshKind
                ? `click to place ${MESH_LABELS[addMeshKind]} · click again to cancel`
                : editTool === "addLine"
                  ? `click two points to add a line · ${view} view`
                  : locked
                    ? `${view} view · locked · ${projection} · drag: pan`
                    : `${projection} · free · drag: rotate · shift+drag: pan`
            : "loading board..."}
        </span>
        <span className="c3d__hint">
          f: top/side view · l: lock/free · o: ortho/persp · locked drag: pan ·
          free drag: rotate (shift: pan) · shift-drag: box select / move · a:
          add line (locked) · r: snap 45° · drag mesh: move · mesh panel: click or drag
          to place · drag to place · corners: scale · ⌘-click: add to group ·
          ⌘C/⌘V: copy/paste
        </span>
      </div>
    </div>
  );
}
