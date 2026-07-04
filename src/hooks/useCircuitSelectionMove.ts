import { useCallback, useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import type * as THREE from "three";
import { boardY } from "../lib/circuitBoardPick";
import type { CircuitMesh } from "../lib/circuitMeshes";
import {
  beginSelectionMoveDrag,
  stepSelectionMoveDrag,
  type SelectionMoveDrag,
} from "../lib/circuitSelectionMove";
import type { GridPath } from "../lib/gridBuilder";
import { useCircuitTuning } from "../stores/circuitTuning";

export function useCircuitSelectionMove(
  paths: GridPath[],
  meshes: CircuitMesh[],
) {
  const { camera, gl, controls } = useThree();
  const dragRef = useRef<SelectionMoveDrag | null>(null);
  const pathsRef = useRef(paths);
  const meshesRef = useRef(meshes);
  pathsRef.current = paths;
  meshesRef.current = meshes;

  const beginMove = useCallback(
    (
      clientX: number,
      clientY: number,
      lineIds: string[],
      meshIds: string[],
    ): boolean => {
      const move = beginSelectionMoveDrag(
        clientX,
        clientY,
        camera,
        gl.domElement,
        pathsRef.current,
        meshesRef.current,
        lineIds,
        meshIds,
        useCircuitTuning.getState().topology,
      );
      if (!move) return false;

      dragRef.current = move;
      useCircuitTuning.getState().setDraggingVertex(true);
      if (controls && "enabled" in controls) {
        (controls as { enabled: boolean }).enabled = false;
      }
      return true;
    },
    [camera, controls, gl.domElement],
  );

  const endMove = useCallback(() => {
    if (!dragRef.current) return;
    dragRef.current = null;
    useCircuitTuning.getState().setDraggingVertex(false);
    if (controls && "enabled" in controls) {
      (controls as { enabled: boolean }).enabled = true;
    }
  }, [controls]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;

      dragRef.current = stepSelectionMoveDrag(
        drag,
        e.clientX,
        e.clientY,
        camera as THREE.Camera,
        gl.domElement,
        pathsRef.current,
      );
    };

    const onUp = () => endMove();

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [camera, endMove, gl.domElement]);

  return { beginMove, endMove, dragRef };
}
