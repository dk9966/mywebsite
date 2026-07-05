import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Line } from "@react-three/drei";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import {
  boardCenterZ,
  boardY,
  pickBoardPoint,
  type BoardPickView,
} from "../lib/circuitBoardPick";
import type { CircuitMesh } from "../lib/circuitMeshes";
import { resolveLineMoveSelection } from "../lib/circuitSelectionMove";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  pointOnAxis,
  previewSnapPoint,
  resolveSegmentGeom,
  segmentDragAxis,
  type SegmentAxis,
  type SegmentGeom,
} from "../lib/circuitTopology";
import { useCircuitSelectionMove } from "../hooks/useCircuitSelectionMove";
import { useCircuitTuning } from "../stores/circuitTuning";

const _ray = new THREE.Raycaster();
const _ndc = new THREE.Vector2();
const _dir = new THREE.Vector3();
const _camDir = new THREE.Vector3();
const _normal = new THREE.Vector3();
const _anchor = new THREE.Vector3();
const _plane = new THREE.Plane();
const _hit = new THREE.Vector3();

function segmentBaseGeom(
  path: GridPath,
  topology: ReturnType<typeof useCircuitTuning.getState>["topology"],
): SegmentGeom | null {
  return resolveSegmentGeom(path, topology);
}

/**
 * Cursor-tracking pick constrained to the segment axis: intersect the mouse ray
 * with the plane that contains the axis and faces the camera, then project onto
 * the axis. Stable for any line orientation (no near-parallel blowup).
 */
function pickPointOnDragAxis(
  clientX: number,
  clientY: number,
  axis: SegmentAxis,
  camera: THREE.Camera,
  domElement: HTMLCanvasElement,
): Vec3 {
  const rect = domElement.getBoundingClientRect();
  _ndc.set(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  );
  _ray.setFromCamera(_ndc, camera);

  _dir.set(axis.dir[0], axis.dir[1], axis.dir[2]);
  camera.getWorldDirection(_camDir);

  // Plane normal = view direction with its along-axis component removed, so the
  // plane contains the axis and is as front-facing as possible.
  _normal.copy(_camDir).addScaledVector(_dir, -_camDir.dot(_dir));
  if (_normal.lengthSq() < 1e-8) _normal.set(0, 1, 0);
  _normal.normalize();

  _anchor.set(axis.anchor[0], axis.anchor[1], axis.anchor[2]);
  _plane.setFromNormalAndCoplanarPoint(_normal, _anchor);

  if (!_ray.ray.intersectPlane(_plane, _hit)) {
    return [axis.anchor[0], axis.anchor[1], axis.anchor[2]];
  }

  // Project the hit onto the axis; keep the dragged end from crossing the anchor.
  const t = Math.max(
    0,
    (_hit.x - axis.anchor[0]) * axis.dir[0] +
      (_hit.y - axis.anchor[1]) * axis.dir[1] +
      (_hit.z - axis.anchor[2]) * axis.dir[2],
  );
  return pointOnAxis(axis.anchor, axis.dir, t);
}

/** Drag a vertex along its segment axis; snaps on release. */
function VertexHandle({
  segmentId,
  end,
  position,
  paths,
  selected,
}: {
  segmentId: string;
  end: 0 | 1;
  position: Vec3;
  paths: GridPath[];
  selected: boolean;
}) {
  const select = useCircuitTuning((s) => s.select);
  const selectVertex = useCircuitTuning((s) => s.selectVertex);
  const pushUndo = useCircuitTuning((s) => s.pushUndo);
  const setVertices = useCircuitTuning((s) => s.setVertices);
  const moveVertex = useCircuitTuning((s) => s.moveVertex);
  const setDraggingVertex = useCircuitTuning((s) => s.setDraggingVertex);

  const { camera, gl, controls } = useThree();
  const pathsRef = useRef(paths);
  useEffect(() => {
    pathsRef.current = paths;
  }, [paths]);

  const drag = useRef<{
    axis: SegmentAxis;
    baseGeom: SegmentGeom;
  } | null>(null);
  const [snapPreview, setSnapPreview] = useState<Vec3 | null>(null);

  const onPointerDown = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      e.nativeEvent.preventDefault();
      if (controls) controls.enabled = false;

      select(segmentId);
      selectVertex(end);
      pushUndo();
      setDraggingVertex(true);

      const livePaths = pathsRef.current;
      const topology = useCircuitTuning.getState().topology;
      const path = livePaths.find((p) => p.id === segmentId);
      const baseGeom = path ? segmentBaseGeom(path, topology) : null;
      const axis = baseGeom ? segmentDragAxis(baseGeom, end) : null;
      if (!baseGeom || !axis) {
        setDraggingVertex(false);
        return;
      }

      drag.current = { axis, baseGeom };
      gl.domElement.setPointerCapture(e.pointerId);
    },
    [
      segmentId,
      end,
      select,
      selectVertex,
      pushUndo,
      setDraggingVertex,
      gl.domElement,
      controls,
    ],
  );

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!drag.current) return;
      e.preventDefault();

      const { axis, baseGeom } = drag.current;
      const point = pickPointOnDragAxis(
        e.clientX,
        e.clientY,
        axis,
        camera,
        gl.domElement,
      );

      const livePaths = pathsRef.current;
      setSnapPreview(
        previewSnapPoint(point, livePaths, segmentId, axis),
      );

      setVertices([
        { segmentId, end, point, baseGeom },
      ]);
    };

    const onUp = (e: PointerEvent) => {
      if (!drag.current) return;
      e.preventDefault();

      const { axis, baseGeom } = drag.current;
      const point = pickPointOnDragAxis(
        e.clientX,
        e.clientY,
        axis,
        camera,
        gl.domElement,
      );
      const livePaths = pathsRef.current;
      const snap = previewSnapPoint(point, livePaths, segmentId, axis);
      setSnapPreview(null);

      moveVertex(segmentId, end, snap, livePaths, baseGeom, true, axis);

      drag.current = null;
      setDraggingVertex(false);
      gl.domElement.releasePointerCapture(e.pointerId);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [
    segmentId,
    end,
    camera,
    setVertices,
    moveVertex,
    setDraggingVertex,
    gl.domElement,
  ]);

  return (
    <>
      <mesh position={position} renderOrder={1001} onPointerDown={onPointerDown}>
        <sphereGeometry args={[selected ? 0.14 : 0.09, 12, 10]} />
        <meshBasicMaterial
          color={selected ? "#ffe066" : "#80cbc4"}
          transparent
          opacity={selected ? 1 : 0.85}
          depthTest={false}
        />
      </mesh>
      {snapPreview ? (
        <mesh position={snapPreview} renderOrder={1002}>
          <sphereGeometry args={[0.11, 10, 8]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.55} depthTest={false} />
        </mesh>
      ) : null}
    </>
  );
}

function VertexHandles({ paths }: { paths: GridPath[] }) {
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedId = selectedLineIds[0] ?? null;
  const editTool = useCircuitTuning((s) => s.editTool);
  const selected = useMemo(
    () => paths.find((p) => p.id === selectedId) ?? null,
    [paths, selectedId],
  );

  if (editTool !== "select" || !selected?.id || selected.hidden || selected.waypoints.length < 2) {
    return null;
  }

  return (
    <group>
      <VertexHandle
        segmentId={selected.id}
        end={0}
        position={selected.waypoints[0]}
        paths={paths}
        selected
      />
      <VertexHandle
        segmentId={selected.id}
        end={1}
        position={selected.waypoints[1]}
        paths={paths}
        selected
      />
    </group>
  );
}

const GHOST_LINE_COLOR = "#66f0f0";
const GHOST_MIN_LEN = 0.05;

/** Two-click line placement on the board plane (locked top/side views only). */
function AddLineTool({
  paths,
  view,
  locked,
  centerZ,
}: {
  paths: GridPath[];
  view: BoardPickView;
  locked: boolean;
  centerZ: number;
}) {
  const editTool = useCircuitTuning((s) => s.editTool);
  const addLineStart = useCircuitTuning((s) => s.addLineStart);
  const setAddLineStart = useCircuitTuning((s) => s.setAddLineStart);
  const addLineSegment = useCircuitTuning((s) => s.addLineSegment);
  const pushUndo = useCircuitTuning((s) => s.pushUndo);

  const { camera, gl } = useThree();
  const y = useMemo(() => boardY(paths), [paths]);
  const [previewEnd, setPreviewEnd] = useState<Vec3 | null>(null);

  const pickBoard = useCallback(
    (clientX: number, clientY: number): Vec3 | null =>
      pickBoardPoint(clientX, clientY, camera, gl.domElement, y, view, centerZ),
    [camera, centerZ, gl.domElement, view, y],
  );

  const updatePreview = useCallback(
    (clientX: number, clientY: number) => {
      if (!addLineStart) return;
      const point = pickBoard(clientX, clientY);
      if (!point) return;
      setPreviewEnd(previewSnapPoint(point, paths, "__new__"));
    },
    [addLineStart, paths, pickBoard],
  );

  useEffect(() => {
    if (editTool !== "addLine" || !addLineStart) {
      setPreviewEnd(null);
      return;
    }

    const el = gl.domElement;
    const onMove = (e: PointerEvent) => updatePreview(e.clientX, e.clientY);
    el.addEventListener("pointermove", onMove);
    return () => el.removeEventListener("pointermove", onMove);
  }, [addLineStart, editTool, gl.domElement, updatePreview]);

  const ghostPoints = useMemo((): [number, number, number][] | null => {
    if (!addLineStart || !previewEnd) return null;
    const len = Math.hypot(
      previewEnd[0] - addLineStart[0],
      previewEnd[1] - addLineStart[1],
      previewEnd[2] - addLineStart[2],
    );
    if (len < GHOST_MIN_LEN) return null;
    return [addLineStart, previewEnd];
  }, [addLineStart, previewEnd]);

  const onPlaneClick = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const point = pickBoard(e.clientX, e.clientY);
      if (!point) return;
      const snapped = previewSnapPoint(point, paths, "__new__");

      if (!addLineStart) {
        pushUndo();
        setAddLineStart(snapped);
        return;
      }

      addLineSegment(addLineStart, snapped);
      setPreviewEnd(snapped);
    },
    [
      addLineStart,
      addLineSegment,
      paths,
      pickBoard,
      pushUndo,
      setAddLineStart,
    ],
  );

  if (editTool !== "addLine" || !locked) return null;

  return (
    <>
      {view === "top" ? (
        <mesh
          position={[0, y, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
          onPointerDown={onPlaneClick}
        >
          <planeGeometry args={[500, 500]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      ) : (
        <mesh position={[0, 0, centerZ]} onPointerDown={onPlaneClick}>
          <planeGeometry args={[500, 500]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      )}
      {ghostPoints ? (
        <Line
          points={ghostPoints}
          color={GHOST_LINE_COLOR}
          lineWidth={2}
          transparent
          opacity={0.38}
          depthTest={false}
          renderOrder={1002}
          dashed
          dashSize={0.12}
          gapSize={0.08}
        />
      ) : null}
      {addLineStart ? (
        <mesh position={addLineStart} renderOrder={1003}>
          <sphereGeometry args={[0.12, 10, 8]} />
          <meshBasicMaterial color="#a5d6a7" depthTest={false} />
        </mesh>
      ) : null}
      {previewEnd && ghostPoints ? (
        <mesh position={previewEnd} renderOrder={1003}>
          <sphereGeometry args={[0.07, 8, 6]} />
          <meshBasicMaterial
            color={GHOST_LINE_COLOR}
            transparent
            opacity={0.45}
            depthTest={false}
          />
        </mesh>
      ) : null}
    </>
  );
}

function PickLine({
  id,
  waypoints,
  beginMove,
  shiftMoveHandledByOverlay,
  onSplit,
}: {
  id: string;
  waypoints: Vec3[];
  beginMove: (
    clientX: number,
    clientY: number,
    lineIds: string[],
    meshIds: string[],
  ) => boolean;
  shiftMoveHandledByOverlay: boolean;
  onSplit: (clientX: number, clientY: number, id: string) => void;
}) {
  const editTool = useCircuitTuning((s) => s.editTool);
  const positions = useMemo(
    () => waypoints as [number, number, number][],
    [waypoints],
  );

  const { gl } = useThree();

  const onPointerDown = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      if (editTool === "split") {
        e.stopPropagation();
        onSplit(e.clientX, e.clientY, id);
        return;
      }
      if (editTool !== "select") return;
      e.stopPropagation();

      const store = useCircuitTuning.getState();

      if (e.shiftKey) {
        if (shiftMoveHandledByOverlay) return;

        const resolved = resolveLineMoveSelection(
          id,
          store.selectedLineIds,
          store.selectedMeshIds,
          e.metaKey,
        );
        if (!resolved || resolved.selectOnly) return;

        if (
          resolved.lineIds.length === 1 &&
          resolved.meshIds.length === 0 &&
          !store.selectedLineIds.includes(id)
        ) {
          store.setBoxSelection(resolved.lineIds, resolved.meshIds);
        }

        if (
          beginMove(
            e.clientX,
            e.clientY,
            resolved.lineIds,
            resolved.meshIds,
          )
        ) {
          gl.domElement.setPointerCapture(e.pointerId);
        }
        return;
      }

      if (e.metaKey) {
        const next = store.selectedLineIds.includes(id)
          ? store.selectedLineIds.filter((lineId) => lineId !== id)
          : [...store.selectedLineIds, id];
        store.setBoxSelection(next, store.selectedMeshIds);
        return;
      }

      if (
        !store.selectedLineIds.includes(id) ||
        store.selectedMeshIds.length > 0
      ) {
        store.setBoxSelection([id], []);
      }
    },
    [beginMove, editTool, gl.domElement, id, onSplit, shiftMoveHandledByOverlay],
  );

  if (editTool === "addLine") return null;

  return (
    <Line
      points={positions}
      lineWidth={6}
      transparent
      opacity={0}
      depthWrite={false}
      renderOrder={10}
      onPointerDown={onPointerDown}
    />
  );
}

function PickProxies({
  paths,
  beginMove,
  shiftMoveHandledByOverlay,
  onSplit,
}: {
  paths: GridPath[];
  beginMove: (
    clientX: number,
    clientY: number,
    lineIds: string[],
    meshIds: string[],
  ) => boolean;
  shiftMoveHandledByOverlay: boolean;
  onSplit: (clientX: number, clientY: number, id: string) => void;
}) {
  return (
    <group>
      {paths.map((p) =>
        p.id && !p.hidden ? (
          <PickLine
            key={p.id}
            id={p.id}
            waypoints={p.waypoints}
            beginMove={beginMove}
            shiftMoveHandledByOverlay={shiftMoveHandledByOverlay}
            onSplit={onSplit}
          />
        ) : null,
      )}
    </group>
  );
}

function SpawnMarkers({ paths }: { paths: GridPath[] }) {
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedId = selectedLineIds[0] ?? null;
  const selected = useMemo(
    () => paths.find((p) => p.id === selectedId) ?? null,
    [paths, selectedId],
  );
  if (!selected?.id || selected.hidden || selected.waypoints.length < 2) return null;

  return (
    <group>
      <mesh position={selected.waypoints[0]} renderOrder={998}>
        <sphereGeometry args={[0.05, 8, 6]} />
        <meshBasicMaterial color="#ffe066" transparent opacity={0.5} depthTest={false} />
      </mesh>
      <mesh position={selected.waypoints[1]} renderOrder={998}>
        <sphereGeometry args={[0.04, 8, 6]} />
        <meshBasicMaterial color="#607d8b" transparent opacity={0.45} depthTest={false} />
      </mesh>
    </group>
  );
}

function SelectionHighlight({ paths }: { paths: GridPath[] }) {
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selected = useMemo(() => {
    const ids = new Set(selectedLineIds);
    return paths.filter((p) => p.id && ids.has(p.id) && p.waypoints.length >= 2);
  }, [paths, selectedLineIds]);
  if (selected.length === 0) return null;
  return (
    <group>
      {selected.map((p) => (
        <Line
          key={p.id}
          points={p.waypoints as [number, number, number][]}
          color="#ffffff"
          lineWidth={4}
          transparent
          opacity={0.95}
          depthTest={false}
          renderOrder={999}
        />
      ))}
    </group>
  );
}

/** Click-to-place or drag-drop from the mesh palette. */
function AddMeshTool({ paths }: { paths: GridPath[] }) {
  const editTool = useCircuitTuning((s) => s.editTool);
  const addMeshKind = useCircuitTuning((s) => s.addMeshKind);
  const addMeshAt = useCircuitTuning((s) => s.addMeshAt);
  const pushUndo = useCircuitTuning((s) => s.pushUndo);

  const { camera, gl } = useThree();
  const y = useMemo(() => boardY(paths), [paths]);

  const onPlaneClick = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      if (!addMeshKind) return;
      e.stopPropagation();
      const point = pickBoardPoint(
        e.clientX,
        e.clientY,
        camera,
        gl.domElement,
        y,
      );
      if (!point) return;
      pushUndo();
      addMeshAt(addMeshKind, point[0], point[2]);
    },
    [addMeshKind, addMeshAt, camera, gl.domElement, pushUndo, y],
  );

  if (editTool !== "addMesh" || !addMeshKind) return null;

  return (
    <mesh
      position={[0, y, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
      onPointerDown={onPlaneClick}
    >
      <planeGeometry args={[500, 500]} />
      <meshBasicMaterial transparent opacity={0} depthWrite={false} />
    </mesh>
  );
}

export default function CircuitSelectionLayer({
  paths,
  meshes = [],
  view = "top",
  locked = true,
  centerZ,
  beginMove: beginMoveProp,
  shiftMoveHandledByOverlay = false,
}: {
  paths: GridPath[];
  meshes?: CircuitMesh[];
  view?: BoardPickView;
  locked?: boolean;
  centerZ?: number;
  beginMove?: (
    clientX: number,
    clientY: number,
    lineIds: string[],
    meshIds: string[],
  ) => boolean;
  /** When true, shift+move is handled by the HTML overlay (3D editor box-select layer). */
  shiftMoveHandledByOverlay?: boolean;
}) {
  const { beginMove: hookBeginMove } = useCircuitSelectionMove(paths, meshes);
  const beginMove = beginMoveProp ?? hookBeginMove;
  const pickCenterZ = centerZ ?? boardCenterZ(paths);

  const { camera, gl } = useThree();
  const splitY = useMemo(() => boardY(paths), [paths]);
  const onSplit = useCallback(
    (clientX: number, clientY: number, id: string) => {
      const store = useCircuitTuning.getState();
      if (store.editTool !== "split") return;
      // Only the selected line is splittable — clicks on others are ignored.
      if (!store.selectedLineIds.includes(id)) return;
      const point = pickBoardPoint(
        clientX,
        clientY,
        camera,
        gl.domElement,
        splitY,
        view,
        pickCenterZ,
      );
      if (!point) return;
      store.splitSegmentAtPoint(paths, id, point);
    },
    [camera, gl.domElement, paths, pickCenterZ, splitY, view],
  );

  return (
    <>
      <AddLineTool
        paths={paths}
        view={view}
        locked={locked}
        centerZ={pickCenterZ}
      />
      <AddMeshTool paths={paths} />
      <PickProxies
        paths={paths}
        beginMove={beginMove}
        shiftMoveHandledByOverlay={shiftMoveHandledByOverlay}
        onSplit={onSplit}
      />
      <SelectionHighlight paths={paths} />
      <VertexHandles paths={paths} />
      <SpawnMarkers paths={paths} />
    </>
  );
}
