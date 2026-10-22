import { useEffect } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

export interface BlenderView {
  /** Camera position and the point it looks at, in scene space (Y up). */
  position: [number, number, number];
  target: [number, number, number];
}

const ORBIT_RADIANS_PER_PIXEL = 0.007; // Blender's default turntable sensitivity
const KEY_STEP = THREE.MathUtils.degToRad(15); // Blender's "Rotation Angle" preference
const MIN_DISTANCE = 0.5;
const MAX_DISTANCE = 150;

type Gesture = "orbit" | "pan" | "zoom";

/** Blender's modifier layering: Shift pans, Ctrl zooms, nothing orbits. */
function gestureFor(e: { shiftKey: boolean; ctrlKey: boolean }): Gesture {
  return e.shiftKey ? "pan" : e.ctrlKey ? "zoom" : "orbit";
}

/**
 * Blender's 3D-viewport navigation: a turntable orbit around a pivot point with
 * no angle limits (it flips over the poles like Blender does).
 *
 *   Middle mouse drag           orbit        (Alt + left drag when emulating)
 *   Shift + middle drag         pan
 *   Ctrl + middle drag          zoom
 *   Scroll wheel / pinch        zoom         (Shift + scroll pans)
 *   Numpad 1/3/7 (+ Ctrl)       front/right/top (back/left/bottom)
 *   Numpad 2/4/6/8              step-orbit   (+ Ctrl pans)
 *   Numpad + / -                zoom
 *   Home                        back to the starting view
 *
 * The scene renders on demand, so every change asks for a frame.
 */
export function BlenderControls({ view }: { view: BlenderView }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const dom = useThree((s) => s.gl.domElement);
  const invalidate = useThree((s) => s.invalidate);

  useEffect(() => {
    const start = new THREE.Vector3(...view.position);
    const initialTarget = new THREE.Vector3(...view.target);
    const offset = start.clone().sub(initialTarget);
    const initial = {
      target: initialTarget,
      distance: offset.length(),
      yaw: Math.atan2(offset.x, offset.z),
      pitch: -Math.asin(offset.y / offset.length()),
    };

    const target = initial.target.clone();
    let { distance, yaw, pitch } = initial;
    const rotation = new THREE.Quaternion();
    const euler = new THREE.Euler(0, 0, 0, "YXZ");
    const scratch = new THREE.Vector3();

    const apply = () => {
      euler.set(pitch, yaw, 0);
      rotation.setFromEuler(euler);
      camera.quaternion.copy(rotation);
      camera.position.set(0, 0, distance).applyQuaternion(rotation).add(target);
      camera.up.set(0, 1, 0);
      camera.updateMatrixWorld();
      invalidate();
    };

    /** Past the poles the view is upside down and horizontal drags must mirror. */
    const turntableSign = () => (Math.cos(pitch) < 0 ? -1 : 1);
    const orbit = (dx: number, dy: number, perPixel: number) => {
      yaw -= dx * perPixel * turntableSign();
      pitch -= dy * perPixel;
      yaw = THREE.MathUtils.euclideanModulo(yaw + Math.PI, Math.PI * 2) - Math.PI;
      pitch = THREE.MathUtils.euclideanModulo(pitch + Math.PI, Math.PI * 2) - Math.PI;
      apply();
    };
    /** Pan in the view plane so the scene follows the cursor one-to-one. */
    const pan = (dx: number, dy: number) => {
      const height = dom.clientHeight || 1;
      const perPixel = (2 * distance * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2)) / height;
      scratch.setFromMatrixColumn(camera.matrix, 0).multiplyScalar(-dx * perPixel);
      target.add(scratch);
      scratch.setFromMatrixColumn(camera.matrix, 1).multiplyScalar(dy * perPixel);
      target.add(scratch);
      apply();
    };
    const zoom = (factor: number) => {
      distance = THREE.MathUtils.clamp(distance * factor, MIN_DISTANCE, MAX_DISTANCE);
      apply();
    };
    const snap = (nextYaw: number, nextPitch: number) => {
      yaw = nextYaw;
      pitch = nextPitch;
      apply();
    };
    const reset = () => {
      target.copy(initial.target);
      distance = initial.distance;
      snap(initial.yaw, initial.pitch);
    };

    // Active pointers, for middle-drag, Alt+left-drag and touch.
    const pointers = new Map<number, { x: number; y: number }>();
    let drag: Gesture | null = null;

    const onPointerDown = (e: PointerEvent) => {
      const emulated = e.button === 0 && e.altKey;
      const touch = e.pointerType === "touch";
      if (!(e.button === 1 || emulated || touch)) return;
      e.preventDefault();
      dom.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      drag = touch ? "orbit" : gestureFor(e);
    };
    const onPointerMove = (e: PointerEvent) => {
      const last = pointers.get(e.pointerId);
      if (!last || !drag) return;
      const dx = e.clientX - last.x;
      const dy = e.clientY - last.y;
      if (e.pointerType === "touch" && pointers.size === 2) {
        // Two fingers: pinch to zoom, drag together to pan.
        const [a, b] = [...pointers.values()];
        const before = Math.hypot(a.x - b.x, a.y - b.y);
        last.x = e.clientX;
        last.y = e.clientY;
        const [c, d] = [...pointers.values()];
        const after = Math.hypot(c.x - d.x, c.y - d.y);
        if (before > 0 && after > 0) zoom(before / after);
        pan(dx / 2, dy / 2);
        return;
      }
      last.x = e.clientX;
      last.y = e.clientY;
      if (drag === "orbit") orbit(dx, dy, ORBIT_RADIANS_PER_PIXEL);
      else if (drag === "pan") pan(dx, dy);
      else zoom(Math.exp(-dy * 0.006));
    };
    const onPointerUp = (e: PointerEvent) => {
      pointers.delete(e.pointerId);
      if (dom.hasPointerCapture(e.pointerId)) dom.releasePointerCapture(e.pointerId);
      if (pointers.size === 0) drag = null;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? dom.clientHeight : 1;
      const dx = e.deltaX * unit;
      const dy = e.deltaY * unit;
      // Browsers synthesize ctrl+wheel for trackpad pinch, with much smaller deltas.
      const pinch = e.ctrlKey && e.deltaMode === 0 && !Number.isInteger(e.deltaY);
      if (e.shiftKey) pan(-dx || -dy, dx ? -dy : 0);
      else zoom(Math.exp(dy * (pinch ? 0.01 : 0.0012)));
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      const flip = e.ctrlKey ? Math.PI : 0;
      let handled = true;
      switch (e.code) {
        case "Numpad1": snap(flip, 0); break; // front / back
        case "Numpad3": snap(flip ? -Math.PI / 2 : Math.PI / 2, 0); break; // right / left
        case "Numpad7": snap(yaw, e.ctrlKey ? Math.PI / 2 : -Math.PI / 2); break; // top / bottom
        case "Numpad4": e.ctrlKey ? pan(-60, 0) : orbit(-KEY_STEP / ORBIT_RADIANS_PER_PIXEL, 0, ORBIT_RADIANS_PER_PIXEL); break;
        case "Numpad6": e.ctrlKey ? pan(60, 0) : orbit(KEY_STEP / ORBIT_RADIANS_PER_PIXEL, 0, ORBIT_RADIANS_PER_PIXEL); break;
        case "Numpad8": e.ctrlKey ? pan(0, -60) : orbit(0, -KEY_STEP / ORBIT_RADIANS_PER_PIXEL, ORBIT_RADIANS_PER_PIXEL); break;
        case "Numpad2": e.ctrlKey ? pan(0, 60) : orbit(0, KEY_STEP / ORBIT_RADIANS_PER_PIXEL, ORBIT_RADIANS_PER_PIXEL); break;
        case "NumpadAdd": zoom(1 / 1.2); break;
        case "NumpadSubtract": zoom(1.2); break;
        case "Home": reset(); break;
        default: handled = false;
      }
      if (handled) e.preventDefault();
    };
    const suppress = (e: Event) => e.preventDefault();

    dom.style.touchAction = "none";
    dom.addEventListener("pointerdown", onPointerDown);
    dom.addEventListener("pointermove", onPointerMove);
    dom.addEventListener("pointerup", onPointerUp);
    dom.addEventListener("pointercancel", onPointerUp);
    dom.addEventListener("wheel", onWheel, { passive: false });
    dom.addEventListener("auxclick", suppress); // middle-click would otherwise autoscroll
    dom.addEventListener("contextmenu", suppress);
    window.addEventListener("keydown", onKeyDown);
    apply();

    return () => {
      dom.removeEventListener("pointerdown", onPointerDown);
      dom.removeEventListener("pointermove", onPointerMove);
      dom.removeEventListener("pointerup", onPointerUp);
      dom.removeEventListener("pointercancel", onPointerUp);
      dom.removeEventListener("wheel", onWheel);
      dom.removeEventListener("auxclick", suppress);
      dom.removeEventListener("contextmenu", suppress);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [camera, dom, invalidate, view]);

  return null;
}
