import { useCallback, useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

/** Drag rotates, shift+drag pans — same bindings as the 3D editor. */
export default function FreeOrbitMouseBindings({
  active,
}: {
  active: boolean;
}) {
  const gl = useThree((s) => s.gl);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const shiftHeld = useRef(false);

  const syncMouseButtons = useCallback(
    (shift: boolean) => {
      if (!controls || !active) return;
      controls.mouseButtons = {
        LEFT: shift ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN,
      };
    },
    [controls, active],
  );

  useEffect(() => {
    syncMouseButtons(shiftHeld.current);
  }, [syncMouseButtons, active]);

  useEffect(() => {
    if (!active) return;

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
  }, [active, syncMouseButtons]);

  useEffect(() => {
    if (!active) return;
    const dom = gl.domElement;
    const onPointerDown = (e: PointerEvent) => syncMouseButtons(e.shiftKey);
    dom.addEventListener("pointerdown", onPointerDown, true);
    syncMouseButtons(false);
    return () => dom.removeEventListener("pointerdown", onPointerDown, true);
  }, [gl, active, syncMouseButtons]);

  return null;
}
