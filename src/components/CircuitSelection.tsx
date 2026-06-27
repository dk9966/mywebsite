import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Line } from "@react-three/drei";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  pointOnAxis,
  previewSnapPoint,
  resolveSegmentGeom,
  segmentDragAxis,
  type SegmentAxis,
  type SegmentGeom,
} from "../lib/circuitTopology";
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

function boardY(paths: GridPath[]): number {
  for (const p of paths) {
    if (p.waypoints.length > 0) return p.waypoints[0][1];
  }
  return 0.022;
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

/** Two-click line placement on the board plane. */
function AddLineTool({ paths }: { paths: GridPath[] }) {
  const editTool = useCircuitTuning((s) => s.editTool);
  const addLineStart = useCircuitTuning((s) => s.addLineStart);
  const setAddLineStart = useCircuitTuning((s) => s.setAddLineStart);
  const addLineSegment = useCircuitTuning((s) => s.addLineSegment);
  const pushUndo = useCircuitTuning((s) => s.pushUndo);

  const { camera, gl } = useThree();
  const y = useMemo(() => boardY(paths), [paths]);

  const boardPlane = useRef(new THREE.Plane());
  const boardHit = useRef(new THREE.Vector3());

  const pickBoard = useCallback(
    (clientX: number, clientY: number): Vec3 | null => {
      const rect = gl.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1,
      );
      _ray.setFromCamera(ndc, camera);
      boardPlane.current.set(new THREE.Vector3(0, 1, 0), -y);
      return _ray.ray.intersectPlane(boardPlane.current, boardHit.current)
        ? ([boardHit.current.x, y, boardHit.current.z] as Vec3)
        : null;
    },
    [camera, gl.domElement, y],
  );

  const onPlaneClick = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const point = pickBoard(e.clientX, e.clientY);
      if (!point) return;

      if (!addLineStart) {
        pushUndo();
        setAddLineStart(point);
        return;
      }

      addLineSegment(addLineStart, point);
    },
    [addLineStart, addLineSegment, pickBoard, pushUndo, setAddLineStart],
  );

  if (editTool !== "addLine") return null;

  return (
    <>
      <mesh position={[0, y, 0]} rotation={[-Math.PI / 2, 0, 0]} onPointerDown={onPlaneClick}>
        <planeGeometry args={[500, 500]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {addLineStart ? (
        <mesh position={addLineStart} renderOrder={1003}>
          <sphereGeometry args={[0.12, 10, 8]} />
          <meshBasicMaterial color="#a5d6a7" depthTest={false} />
        </mesh>
      ) : null}
    </>
  );
}

function PickLine({
  id,
  waypoints,
  onSelect,
}: {
  id: string;
  waypoints: Vec3[];
  onSelect: (id: string) => void;
}) {
  const editTool = useCircuitTuning((s) => s.editTool);
  const positions = useMemo(() => {
    const arr = new Float32Array(waypoints.length * 3);
    for (let i = 0; i < waypoints.length; i++) {
      arr[i * 3] = waypoints[i][0];
      arr[i * 3 + 1] = waypoints[i][1];
      arr[i * 3 + 2] = waypoints[i][2];
    }
    return arr;
  }, [waypoints]);

  if (editTool === "addLine") return null;

  return (
    <line
      onPointerDown={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial transparent opacity={0} depthWrite={false} />
    </line>
  );
}

function PickProxies({ paths }: { paths: GridPath[] }) {
  const select = useCircuitTuning((s) => s.select);
  return (
    <group>
      {paths.map((p) =>
        p.id && !p.hidden ? (
          <PickLine key={p.id} id={p.id} waypoints={p.waypoints} onSelect={select} />
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
  const selectedId = selectedLineIds[0] ?? null;
  const selected = useMemo(
    () => paths.find((p) => p.id === selectedId) ?? null,
    [paths, selectedId],
  );
  if (!selected || selected.waypoints.length < 2) return null;
  return (
    <Line
      points={selected.waypoints as [number, number, number][]}
      color="#ffffff"
      lineWidth={4}
      transparent
      opacity={0.95}
      depthTest={false}
      renderOrder={999}
    />
  );
}

export default function CircuitSelectionLayer({ paths }: { paths: GridPath[] }) {
  return (
    <>
      <AddLineTool paths={paths} />
      <PickProxies paths={paths} />
      <SelectionHighlight paths={paths} />
      <VertexHandles paths={paths} />
      <SpawnMarkers paths={paths} />
    </>
  );
}
