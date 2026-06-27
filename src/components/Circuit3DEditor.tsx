import { OrbitControls, useGLTF } from "@react-three/drei";
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
  useMemo,
  useRef,
  useState,
  type ElementRef,
} from "react";
import * as THREE from "three";
import {
  buildOutlineModel,
  transformedOutlinePaths,
  type OutlineModel,
} from "../lib/circuit3DMeshes";
import { MESH_LABELS, MESH_PALETTE } from "../lib/circuitMeshBoxes";
import {
  footprintsToMeshes,
  moveMeshBounds,
  resizeMeshFromCorner,
  resolveMeshes,
  type CircuitMesh,
  type MeshBounds,
  type MeshHandle,
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
import "./Circuit3DEditor.css";
import CircuitSelectionLayer from "./CircuitSelection";
import TronGrid from "./TronGrid";

const OUTLINE_GLB_URL = "/models/circuits-traced-outline.glb";
useGLTF.preload(OUTLINE_GLB_URL);

const FOV = 40;
/** Camera distance as a multiple of the board span (fits the wide board). */
const VIEW_DIST_FACTOR = 1.5;
const VIEW_ANIM_MS = 300;

type ViewKind = "top" | "side";

const LINE_CONFIG_OVERRIDES = {
  lineColor: "#3ee8d2",
  lineOpacity: 1,
  tipColor: "#3ee8d2",
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

function lockedViewDistance(
  view: ViewKind,
  camera: THREE.Camera,
  lookAt: THREE.Vector3,
): number {
  if (view === "top") return Math.max(camera.position.y - lookAt.y, 0.5);
  return Math.max(camera.position.z - lookAt.z, 0.5);
}

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
  const controlsRef = useRef<ElementRef<typeof OrbitControls> | null>(null);
  const presets = useMemo(() => computePresets(layout), [layout]);
  const presetsRef = useRef(presets);
  presetsRef.current = presets;
  const viewDistanceRef = useRef(
    presets.top.pos.distanceTo(presets.target),
  );
  const targetInitialized = useRef(false);
  const prevFitToken = useRef(fitToken);
  const shiftHeld = useRef(false);
  const lockedRef = useRef(locked);
  lockedRef.current = locked;

  // OrbitControls target is owned by the rig — never reset from layout updates.
  useEffect(() => {
    if (targetInitialized.current) return;
    const controls = controlsRef.current;
    if (!controls) return;
    controls.target.copy(presets.target);
    viewDistanceRef.current = lockedViewDistance(view, camera, presets.target);
    targetInitialized.current = true;
  }, [presets, view, camera]);

  const syncMouseButtons = useCallback((shift: boolean) => {
    const controls = controlsRef.current;
    if (!controls) return;
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
    if (!locked) {
      anim.current = null;
      return;
    }
    const p = presetsRef.current;
    const controls = controlsRef.current;
    const preset = view === "top" ? p.top : p.side;
    const isFit = fitToken !== prevFitToken.current;
    prevFitToken.current = fitToken;

    const lookTarget = isFit
      ? p.target.clone()
      : (controls?.target.clone() ?? p.target.clone());

    if (isFit && controls) {
      controls.target.copy(lookTarget);
      viewDistanceRef.current = preset.pos.distanceTo(p.target);
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
  }, [view, locked, viewToken, fitToken, camera]);

  // Run after OrbitControls so locked pan/zoom can be corrected each frame.
  useFrame(() => {
    const controls = controlsRef.current;
    if (!controls) return;

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
    const block = st.isDraggingVertex || st.editTool !== "select";
    controls.enabled = true;
    controls.enableRotate = !locked && !block;
    controls.enablePan = !block;
    controls.enableZoom = true;

    if (locked) {
      const preset =
        view === "top" ? presetsRef.current.top : presetsRef.current.side;
      const lookAt = controls.target;
      viewDistanceRef.current = lockedViewDistance(view, camera, lookAt);
      snapLockedCamera(
        view,
        camera,
        lookAt,
        viewDistanceRef.current,
        preset.up,
      );
    }
  }, 1);

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.12}
      minDistance={0.5}
      maxDistance={4000}
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
      e.stopPropagation();
      const store = useCircuitTuning.getState();

      if (e.metaKey || e.shiftKey) {
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

      {/* User-placed meshes have no real outline, so show a faint solid box. */}
      {!hasOutline ? (
        <mesh position={[cx, midY, cz]}>
          <boxGeometry args={[Math.max(w, 0.2), boxH, Math.max(h, 0.2)]} />
          <meshBasicMaterial color="#1bbfac" transparent opacity={0.12} />
        </mesh>
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

function MeshLayer({
  meshes,
  model,
}: {
  meshes: CircuitMesh[];
  model: OutlineModel;
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
          hasOutline={model.segmentsByComp.has(m.id)}
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
  viewToken,
  fitToken,
  onData,
}: {
  view: ViewKind;
  locked: boolean;
  viewToken: number;
  fitToken: number;
  onData: (d: SceneData) => void;
}) {
  const { scene } = useGLTF(OUTLINE_GLB_URL);
  const topology = useCircuitTuning((s) => s.topology);
  const meshEdits = useCircuitTuning((s) => s.meshEdits);

  useEffect(() => {
    useLineConfig.getState().set(LINE_CONFIG_OVERRIDES);
  }, []);

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
  const outlinePaths = useMemo(
    () => transformedOutlinePaths(model, resolvedMeshes),
    [model, resolvedMeshes],
  );

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
      />
      {/* Editable circuit traces — static, full length. */}
      <TronGrid
        paths={editablePaths}
        showBackgroundGrid={false}
        animated={false}
      />
      <MeshLayer meshes={resolvedMeshes} model={model} />
      <CircuitSelectionLayer paths={editablePaths} />
    </>
  );
}

// --- Editor shell (overlay UI + key handling) -------------------------------

export default function Circuit3DEditor() {
  const [view, setView] = useState<ViewKind>("top");
  const [locked, setLocked] = useState(true);
  const [viewToken, setViewToken] = useState(0);
  const [fitToken, setFitToken] = useState(0);
  const [status, setStatus] = useState("");
  const [loaded, setLoaded] = useState(false);

  const dataRef = useRef<SceneData>({ paths: [], meshes: [] });
  const onData = useCallback((d: SceneData) => {
    dataRef.current = d;
    if (d.paths.length > 0) setLoaded(true);
  }, []);

  const editTool = useCircuitTuning((s) => s.editTool);
  const addMeshKind = useCircuitTuning((s) => s.addMeshKind);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedMeshIds = useCircuitTuning((s) => s.selectedMeshIds);
  const snapMergeEps = useCircuitTuning((s) => s.snapMergeEps);
  const setSnapMergeEps = useCircuitTuning((s) => s.setSnapMergeEps);
  const setTool = useCircuitTuning((s) => s.setEditTool);
  const startAddMesh = useCircuitTuning((s) => s.startAddMesh);

  const flash = useCallback((msg: string) => {
    setStatus(msg);
    window.setTimeout(() => setStatus(""), 2500);
  }, []);

  const onSnap45 = useCallback(() => {
    const { paths, meshes } = dataRef.current;
    const { changed, merged, meshSnapped } = useCircuitTuning
      .getState()
      .snapAnglesToGrid(paths, meshes);
    const parts: string[] = [];
    if (changed > 0)
      parts.push(`snapped ${changed} line${changed === 1 ? "" : "s"}`);
    if (merged > 0)
      parts.push(`merged ${merged} vertex${merged === 1 ? "" : "es"}`);
    if (meshSnapped > 0)
      parts.push(
        `connected ${meshSnapped} endpoint${meshSnapped === 1 ? "" : "s"}`,
      );
    flash(parts.length ? parts.join(", ") : "nothing to snap or merge");
  }, [flash]);

  const toggleView = useCallback(() => {
    setView((v) => (v === "top" ? "side" : "top"));
    setLocked(true);
    setViewToken((n) => n + 1);
  }, []);

  // Register the path resolver so the store's copy reads live trace geometry.
  useEffect(() => {
    setEditPathsGetter(() => dataRef.current.paths);
    return () => setEditPathsGetter(null);
  }, []);

  // Editor shortcuts: a (add line), s (snap 45), t (toggle view), l (lock).
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === "a") {
        e.preventDefault();
        const store = useCircuitTuning.getState();
        store.setEditTool(store.editTool === "addLine" ? "select" : "addLine");
      } else if (k === "s") {
        e.preventDefault();
        onSnap45();
      } else if (k === "t") {
        e.preventDefault();
        toggleView();
      } else if (k === "l") {
        e.preventDefault();
        setLocked((v) => !v);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onSnap45, toggleView]);

  const onSave = useCallback(async () => {
    const ok = await useCircuitTuning.getState().saveAsDefault();
    flash(
      ok
        ? "saved to circuits-tuning.json"
        : "downloaded JSON (dev save unavailable)",
    );
  }, [flash]);

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
      flash(ok ? "imported tuning" : "import failed: invalid JSON");
    },
    [flash],
  );

  const hasSelection = selectedLineIds.length > 0 || selectedMeshIds.length > 0;

  return (
    <div className="c3d">
      <Canvas
        className="c3d__canvas"
        gl={{ antialias: true, alpha: false }}
        onPointerMissed={() => useCircuitTuning.getState().clearSelection()}
        onCreated={(state) => {
          state.raycaster.params.Line = { threshold: 0.3 };
        }}
        camera={{ position: [0, 60, 0], fov: FOV, near: 0.1, far: 4000 }}
      >
        <Suspense fallback={null}>
          <EditorScene
            view={view}
            locked={locked}
            viewToken={viewToken}
            fitToken={fitToken}
            onData={onData}
          />
        </Suspense>
      </Canvas>

      <div className="c3d__toolbar">
        <div className="c3d__group">
          <button
            type="button"
            className={
              editTool === "select" ? "c3d__btn c3d__btn--active" : "c3d__btn"
            }
            onClick={() => setTool("select")}
          >
            Select
          </button>
          <button
            type="button"
            className={
              editTool === "addLine" ? "c3d__btn c3d__btn--active" : "c3d__btn"
            }
            onClick={() => setTool("addLine")}
          >
            Add line
          </button>
        </div>

        <div className="c3d__sep" />

        <div className="c3d__group">
          <button
            type="button"
            className="c3d__btn"
            disabled={selectedLineIds.length !== 1}
            onClick={() =>
              useCircuitTuning
                .getState()
                .splitSelectedSegment(dataRef.current.paths)
            }
          >
            Split
          </button>
          <button
            type="button"
            className="c3d__btn c3d__btn--danger"
            disabled={!hasSelection}
            onClick={() => useCircuitTuning.getState().deleteSelection()}
          >
            Delete
          </button>
          <button type="button" className="c3d__btn" onClick={onSnap45}>
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
            className={
              view === "top" ? "c3d__btn c3d__btn--active" : "c3d__btn"
            }
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
            className={
              view === "side" ? "c3d__btn c3d__btn--active" : "c3d__btn"
            }
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
            className={locked ? "c3d__btn c3d__btn--active" : "c3d__btn"}
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
        </div>

        <div className="c3d__sep" />

        <div className="c3d__group">
          <button
            type="button"
            className="c3d__btn"
            onClick={() => useCircuitTuning.getState().undo()}
          >
            Undo
          </button>
          <button
            type="button"
            className="c3d__btn"
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
              flash("reset to committed default");
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

      <aside className="c3d__palette">
        <p className="c3d__palette-title">Meshes</p>
        {MESH_PALETTE.map((kind) => (
          <button
            key={kind}
            type="button"
            className={
              editTool === "addMesh" && addMeshKind === kind
                ? "c3d__palette-item c3d__palette-item--active"
                : "c3d__palette-item"
            }
            onClick={() => startAddMesh(kind)}
            title={`Place ${MESH_LABELS[kind]}`}
          >
            <span className="c3d__palette-preview">{MESH_LABELS[kind]}</span>
            <span>{MESH_LABELS[kind]}</span>
          </button>
        ))}
      </aside>

      <div className="c3d__status">
        {status && <span className="c3d__status-line--accent">{status}</span>}
        <span>
          {loaded
            ? hasSelection
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
                ? `click to place ${MESH_LABELS[addMeshKind]}`
                : editTool === "addLine"
                  ? "click two points to add a line"
                  : locked
                    ? `${view} view · locked · drag: pan`
                    : "free · drag: rotate · shift+drag: pan"
            : "loading board..."}
        </span>
        <span className="c3d__hint">
          t: top/side view · l: lock/free · locked drag: pan · free drag:
          rotate (shift: pan) · a: add line · s: snap 45° · drag mesh: move ·
          corners: scale · ⌘C/⌘V: copy/paste · del: delete · auto-saves
        </span>
      </div>
    </div>
  );
}
