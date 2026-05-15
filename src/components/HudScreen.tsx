import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { useThree } from "@react-three/fiber";
import { Html, Line as DreiLine } from "@react-three/drei";
import * as THREE from "three";
import "./HudScreen.css";

// drei's <Html transform> divides the group's matrix by 40 internally
// (defaults from distanceFactor=10 → 400/10 scale on the inner CSS matrix).
// So to land at "1 CSS px = WORLD_PER_CSS_PX world units" the group's scale
// must be WORLD_PER_CSS_PX * 40. 0.0015 m/px = 1.5 mm per CSS pixel makes a
// 400 px-wide panel ≈ 0.6 m in the scene — tablet-sized.
const WORLD_PER_CSS_PX = 0.0015;
const GROUP_SCALE = WORLD_PER_CSS_PX * 40;

const MIN_WIDTH_PX = 180;
const MIN_HEIGHT_PX = 120;

type ResizeCorner = "tl" | "tr" | "bl" | "br";

type DragBasis = {
  origin: THREE.Vector3;
  right: THREE.Vector3;
  up: THREE.Vector3;
  pixelToWorld: number;
};

type MoveDrag = DragBasis & {
  pointerId: number;
  startX: number;
  startY: number;
};

type ResizeDrag = DragBasis & {
  pointerId: number;
  startX: number;
  startY: number;
  startWidth: number;
  startHeight: number;
  corner: ResizeCorner;
};

export interface HudScreenProps {
  // World-space position (the panel will lookAt the camera on mount so it
  // initially faces the user).
  position: [number, number, number];
  // Initial DOM size in CSS pixels. World size is widthPx * WORLD_PER_CSS_PX.
  // The user can resize at runtime by dragging a corner; we keep the live
  // size in local state so the bezel and the CSS panel stay in sync.
  widthPx: number;
  heightPx: number;
  title: string;
  // Optional small text shown on the right of the title bar — usually a
  // status / "tag" string per widget.
  tag?: string;
  children: ReactNode;
}

export default function HudScreen({
  position,
  widthPx: initialWidthPx,
  heightPx: initialHeightPx,
  title,
  tag,
  children,
}: HudScreenProps) {
  const groupRef = useRef<THREE.Group>(null);
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);

  const [widthPx, setWidthPx] = useState(initialWidthPx);
  const [heightPx, setHeightPx] = useState(initialHeightPx);

  // We freeze the camera basis at pointerdown so move/resize both happen on
  // the panel's "screen plane" — they feel like sliding/stretching the panel
  // on its own face rather than wobbling around the user's view.
  const moveDrag = useRef<MoveDrag | null>(null);
  const resizeDrag = useRef<ResizeDrag | null>(null);

  useEffect(() => {
    const g = groupRef.current;
    if (!g) return;
    g.position.set(...position);
    // Face the user. lookAt rotates -Z toward target, which matches the way
    // Html transform projects (the DOM normal is the group's local +Z).
    g.lookAt(camera.position);
  }, [position, camera]);

  const captureBasis = useCallback((): DragBasis | null => {
    const g = groupRef.current;
    if (!g) return null;
    const right = new THREE.Vector3();
    const up = new THREE.Vector3();
    const fwd = new THREE.Vector3();
    camera.matrixWorld.extractBasis(right, up, fwd);
    const persp = camera as THREE.PerspectiveCamera;
    const distance = camera.position.distanceTo(g.position);
    const fovRad = (persp.fov * Math.PI) / 180;
    // Pixels-per-world at the panel's depth, using the canvas height as the
    // reference dimension (matches three.js perspective math).
    const pixelToWorld = (2 * distance * Math.tan(fovRad / 2)) / size.height;
    return { origin: g.position.clone(), right, up, pixelToWorld };
  }, [camera, size.height]);

  // ---- Move (any edge) -----------------------------------------------------

  const onMovePointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      e.stopPropagation();
      const basis = captureBasis();
      if (!basis) return;
      moveDrag.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        ...basis,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [captureBasis],
  );

  const onMovePointerMove = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    const d = moveDrag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    const g = groupRef.current;
    if (!g) return;
    const dx = (e.clientX - d.startX) * d.pixelToWorld;
    const dy = (e.clientY - d.startY) * d.pixelToWorld;
    g.position.copy(d.origin).addScaledVector(d.right, dx).addScaledVector(d.up, -dy);
  }, []);

  const endMoveDrag = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    if (moveDrag.current?.pointerId === e.pointerId) {
      moveDrag.current = null;
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  }, []);

  const moveHandlers = {
    onPointerDown: onMovePointerDown,
    onPointerMove: onMovePointerMove,
    onPointerUp: endMoveDrag,
    onPointerCancel: endMoveDrag,
  };

  // ---- Resize (corners) ----------------------------------------------------

  const onResizePointerDown = useCallback(
    (corner: ResizeCorner) =>
      (e: ReactPointerEvent<HTMLDivElement>) => {
        e.stopPropagation();
        const basis = captureBasis();
        if (!basis) return;
        resizeDrag.current = {
          pointerId: e.pointerId,
          startX: e.clientX,
          startY: e.clientY,
          startWidth: widthPx,
          startHeight: heightPx,
          corner,
          ...basis,
        };
        e.currentTarget.setPointerCapture(e.pointerId);
      },
    [captureBasis, widthPx, heightPx],
  );

  const onResizePointerMove = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    const d = resizeDrag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    const g = groupRef.current;
    if (!g) return;

    // Cursor delta in screen pixels → panel CSS px via the camera-depth
    // scale. cssScale collapses to ~1 when the panel sits at its calibrated
    // distance, so cursor and corner travel match 1:1 at that depth.
    const dxScreen = e.clientX - d.startX;
    const dyScreen = e.clientY - d.startY;
    const cssScale = d.pixelToWorld / WORLD_PER_CSS_PX;
    const dxPanel = dxScreen * cssScale;
    const dyPanel = dyScreen * cssScale;

    const signX = d.corner === "tl" || d.corner === "bl" ? -1 : 1;
    const signY = d.corner === "tl" || d.corner === "tr" ? -1 : 1;

    const targetW = d.startWidth + signX * dxPanel;
    const targetH = d.startHeight + signY * dyPanel;
    const newW = Math.max(MIN_WIDTH_PX, targetW);
    const newH = Math.max(MIN_HEIGHT_PX, targetH);

    // Keep the opposite corner stationary: the center moves by half the
    // *actual* size change toward the dragged corner. Using actual (post-
    // clamp) instead of requested means the panel doesn't keep sliding once
    // we've hit the minimum size.
    const actualDW = newW - d.startWidth;
    const actualDH = newH - d.startHeight;
    const shiftRightWorld = (signX * actualDW * WORLD_PER_CSS_PX) / 2;
    const shiftUpWorld = -(signY * actualDH * WORLD_PER_CSS_PX) / 2;

    g.position
      .copy(d.origin)
      .addScaledVector(d.right, shiftRightWorld)
      .addScaledVector(d.up, shiftUpWorld);

    setWidthPx(newW);
    setHeightPx(newH);
  }, []);

  const endResizeDrag = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    if (resizeDrag.current?.pointerId === e.pointerId) {
      resizeDrag.current = null;
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  }, []);

  const cornerHandlers = (corner: ResizeCorner) => ({
    onPointerDown: onResizePointerDown(corner),
    onPointerMove: onResizePointerMove,
    onPointerUp: endResizeDrag,
    onPointerCancel: endResizeDrag,
  });

  const panelStyle: CSSProperties = {
    width: `${widthPx}px`,
    height: `${heightPx}px`,
  };

  return (
    <group ref={groupRef} scale={GROUP_SCALE}>
      <Html transform center zIndexRange={[100, 0]}>
        <div className="hud-screen" style={panelStyle}>
          <div className="hud-screen__frame">
            <div className="hud-screen__handle" {...moveHandlers}>
              <span className="hud-screen__dot" />
              <span className="hud-screen__title">{title}</span>
              {tag ? <span className="hud-screen__tag">{tag}</span> : null}
            </div>
            <div className="hud-screen__body">{children}</div>
            {/* Move zones on the remaining three edges. Top edge is the
                title bar above. */}
            <div className="hud-screen__edge hud-screen__edge--bottom" {...moveHandlers} />
            <div className="hud-screen__edge hud-screen__edge--left" {...moveHandlers} />
            <div className="hud-screen__edge hud-screen__edge--right" {...moveHandlers} />
            {/* Resize zones at the corners. z-indexed above edges + handle so
                the corner of the title bar acts as a resize handle instead of
                a move handle. */}
            <div className="hud-screen__corner hud-screen__corner--tl" {...cornerHandlers("tl")} />
            <div className="hud-screen__corner hud-screen__corner--tr" {...cornerHandlers("tr")} />
            <div className="hud-screen__corner hud-screen__corner--bl" {...cornerHandlers("bl")} />
            <div className="hud-screen__corner hud-screen__corner--br" {...cornerHandlers("br")} />
          </div>
        </div>
      </Html>
      <BezelLines widthPx={widthPx} heightPx={heightPx} />
    </group>
  );
}

// 3D bezel — drawn as fat Line2s in the WebGL canvas instead of as an SVG
// inside drei's Html. SVG strokes under a CSS3D matrix3d transform alias
// badly on tilted panel edges; Line2 strokes go through the renderer's MSAA
// pass and pick up the same bloom that lights the desk lines, so the panel
// outline reads as part of the same cyan world rather than a flat decal.
//
// drei's <Html transform center> applies an internal /40 scale to its CSS
// matrix so 1 CSS px = WORLD_PER_CSS_PX world units. We sit in the same
// outer group (scale = WORLD_PER_CSS_PX * 40), so to match the Html panel's
// CSS-px perimeter our local vertex units are (CSS-px / 40).
const BEZEL_COLOR = "#9cf8f8";
const BRACKET_ARM_PX = 16;
const PX_TO_LOCAL = 1 / 40;

function BezelLines({ widthPx, heightPx }: { widthPx: number; heightPx: number }) {
  const lines = useMemo(() => {
    const halfW = (widthPx * PX_TO_LOCAL) / 2;
    const halfH = (heightPx * PX_TO_LOCAL) / 2;
    const arm = BRACKET_ARM_PX * PX_TO_LOCAL;

    const rect: [number, number, number][] = [
      [-halfW, -halfH, 0],
      [ halfW, -halfH, 0],
      [ halfW,  halfH, 0],
      [-halfW,  halfH, 0],
      [-halfW, -halfH, 0],
    ];
    const tl: [number, number, number][] = [
      [-halfW, halfH - arm, 0],
      [-halfW, halfH, 0],
      [-halfW + arm, halfH, 0],
    ];
    const tr: [number, number, number][] = [
      [ halfW - arm, halfH, 0],
      [ halfW, halfH, 0],
      [ halfW, halfH - arm, 0],
    ];
    const br: [number, number, number][] = [
      [ halfW, -halfH + arm, 0],
      [ halfW, -halfH, 0],
      [ halfW - arm, -halfH, 0],
    ];
    const bl: [number, number, number][] = [
      [-halfW + arm, -halfH, 0],
      [-halfW, -halfH, 0],
      [-halfW, -halfH + arm, 0],
    ];
    return { rect, tl, tr, br, bl };
  }, [widthPx, heightPx]);

  return (
    <>
      <DreiLine
        points={lines.rect}
        color={BEZEL_COLOR}
        lineWidth={1.4}
        transparent
        opacity={0.6}
        depthWrite={false}
      />
      <DreiLine points={lines.tl} color={BEZEL_COLOR} lineWidth={2.6} depthWrite={false} />
      <DreiLine points={lines.tr} color={BEZEL_COLOR} lineWidth={2.6} depthWrite={false} />
      <DreiLine points={lines.br} color={BEZEL_COLOR} lineWidth={2.6} depthWrite={false} />
      <DreiLine points={lines.bl} color={BEZEL_COLOR} lineWidth={2.6} depthWrite={false} />
    </>
  );
}
