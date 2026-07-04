import { useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import type * as THREE from "three";
import { boardY } from "../lib/circuitBoardPick";
import {
  BOX_SELECT_DRAG_THRESHOLD,
  canvasLocalPoint,
  linesInScreenBox,
  meshesInScreenBox,
  type ScreenRect,
} from "../lib/circuitBoxSelect";
import type { CircuitMesh } from "../lib/circuitMeshes";
import {
  beginSelectionMoveDrag,
  resolveShiftPointerTarget,
  stepSelectionMoveDrag,
  type SelectionMoveDrag,
} from "../lib/circuitSelectionMove";
import type { GridPath } from "../lib/gridBuilder";
import { useCircuitTuning } from "../stores/circuitTuning";

type BoxDragState = {
  kind: "box";
  pointerId: number;
  startSx: number;
  startSy: number;
  endSx: number;
  endSy: number;
  active: boolean;
};

type MoveDragState = {
  kind: "move";
  pointerId: number;
  move: SelectionMoveDrag;
};

type DragState = BoxDragState | MoveDragState;

/** Keeps the live camera on a ref for HTML-layer box select (outside the Canvas). */
export function CameraRefBridge({
  cameraRef,
}: {
  cameraRef: React.MutableRefObject<THREE.Camera | null>;
}) {
  const { camera } = useThree();
  cameraRef.current = camera;
  return null;
}

/**
 * Shift+drag on an HTML layer above the WebGL canvas.
 * Shift+drag on a selected line/mesh (or inside selection bounds) moves it;
 * shift+drag on empty space draws a box-select marquee.
 */
export function BoxSelectLayer({
  active,
  canvas,
  cameraRef,
  dataRef,
  onRectChange,
}: {
  active: boolean;
  canvas: HTMLCanvasElement | null;
  cameraRef: React.MutableRefObject<THREE.Camera | null>;
  dataRef: React.MutableRefObject<{ paths: GridPath[]; meshes: CircuitMesh[] }>;
  onRectChange: (rect: ScreenRect | null) => void;
}) {
  const dragRef = useRef<DragState | null>(null);
  const onRectChangeRef = useRef(onRectChange);
  onRectChangeRef.current = onRectChange;

  useEffect(() => {
    const endDrag = () => {
      dragRef.current = null;
      onRectChangeRef.current(null);
      useCircuitTuning.getState().setDraggingVertex(false);
    };

    const onPointerMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      const canvasEl = canvas;
      const camera = cameraRef.current;
      if (!drag || !canvasEl || !camera || drag.pointerId !== e.pointerId) return;

      if (drag.kind === "move") {
        e.preventDefault();
        const { paths } = dataRef.current;
        drag.move = stepSelectionMoveDrag(
          drag.move,
          e.clientX,
          e.clientY,
          camera,
          canvasEl,
          paths,
        );
        return;
      }

      const { sx, sy } = canvasLocalPoint(e.clientX, e.clientY, canvasEl);
      drag.endSx = sx;
      drag.endSy = sy;

      if (
        !drag.active &&
        Math.hypot(sx - drag.startSx, sy - drag.startSy) > BOX_SELECT_DRAG_THRESHOLD
      ) {
        drag.active = true;
      }

      if (!drag.active) return;

      e.preventDefault();
      onRectChangeRef.current({
        l: Math.min(drag.startSx, drag.endSx),
        r: Math.max(drag.startSx, drag.endSx),
        t: Math.min(drag.startSy, drag.endSy),
        b: Math.max(drag.startSy, drag.endSy),
      });
    };

    const onPointerUp = (e: PointerEvent) => {
      const drag = dragRef.current;
      const canvasEl = canvas;
      const camera = cameraRef.current;
      if (!drag || !canvasEl || !camera || drag.pointerId !== e.pointerId) return;

      if (drag.kind === "move") {
        e.preventDefault();
        endDrag();
        return;
      }

      if (drag.active) {
        e.preventDefault();

        const w = Math.abs(drag.endSx - drag.startSx);
        const h = Math.abs(drag.endSy - drag.startSy);
        const store = useCircuitTuning.getState();
        if (w > BOX_SELECT_DRAG_THRESHOLD || h > BOX_SELECT_DRAG_THRESHOLD) {
          const { paths, meshes } = dataRef.current;
          const y = boardY(paths);
          store.setBoxSelection(
            linesInScreenBox(
              paths,
              camera,
              canvasEl,
              drag.startSx,
              drag.startSy,
              drag.endSx,
              drag.endSy,
            ),
            meshesInScreenBox(
              meshes,
              y,
              camera,
              canvasEl,
              drag.startSx,
              drag.startSy,
              drag.endSx,
              drag.endSy,
            ),
          );
        } else {
          store.clearSelection();
        }
      }

      endDrag();
    };

    window.addEventListener("pointermove", onPointerMove, true);
    window.addEventListener("pointerup", onPointerUp, true);
    window.addEventListener("pointercancel", onPointerUp, true);

    return () => {
      window.removeEventListener("pointermove", onPointerMove, true);
      window.removeEventListener("pointerup", onPointerUp, true);
      window.removeEventListener("pointercancel", onPointerUp, true);
      endDrag();
    };
  }, [cameraRef, canvas, dataRef]);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!active || e.button !== 0 || !canvas) return;
    const store = useCircuitTuning.getState();
    if (store.editTool !== "select") return;

    e.preventDefault();
    e.stopPropagation();

    const { sx, sy } = canvasLocalPoint(e.clientX, e.clientY, canvas);
    const camera = cameraRef.current;
    if (!camera) return;

    const { paths, meshes } = dataRef.current;
    const target = resolveShiftPointerTarget(
      sx,
      sy,
      e.clientX,
      e.clientY,
      paths,
      meshes,
      camera,
      canvas,
      store.selectedLineIds,
      store.selectedMeshIds,
      store.topology,
      e.metaKey,
    );

    if (target.mode === "toggle") {
      store.setBoxSelection(target.lineIds, target.meshIds);
      return;
    }

    if (target.mode === "move") {
      if (
        target.lineIds.length === 1 &&
        target.meshIds.length === 0 &&
        !store.selectedLineIds.includes(target.lineIds[0])
      ) {
        store.setBoxSelection(target.lineIds, target.meshIds);
      }

      const move = beginSelectionMoveDrag(
        e.clientX,
        e.clientY,
        camera,
        canvas,
        paths,
        meshes,
        target.lineIds,
        target.meshIds,
        store.topology,
      );
      if (!move) return;

      dragRef.current = {
        kind: "move",
        pointerId: e.pointerId,
        move,
      };
      store.setDraggingVertex(true);
      e.currentTarget.setPointerCapture(e.pointerId);
      return;
    }

    dragRef.current = {
      kind: "box",
      pointerId: e.pointerId,
      startSx: sx,
      startSy: sy,
      endSx: sx,
      endSy: sy,
      active: false,
    };
    store.setDraggingVertex(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  return (
    <div
      className={
        active
          ? "c3d__box-select-layer c3d__box-select-layer--active"
          : "c3d__box-select-layer"
      }
      onPointerDown={onPointerDown}
      aria-hidden
    />
  );
}

export function BoxSelectOverlay({
  rect,
  canvas,
}: {
  rect: ScreenRect | null;
  canvas: HTMLCanvasElement | null;
}) {
  if (!rect || !canvas) return null;
  const bounds = canvas.getBoundingClientRect();
  const left = bounds.left + rect.l;
  const top = bounds.top + rect.t;
  const width = rect.r - rect.l;
  const height = rect.b - rect.t;

  return (
    <div
      className="c3d__box-select"
      style={{
        position: "fixed",
        left,
        top,
        width,
        height,
        pointerEvents: "none",
      }}
      aria-hidden
    />
  );
}
