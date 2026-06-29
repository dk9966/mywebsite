import { useCallback, useEffect, useMemo, useRef } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Html, Line as DreiLine } from "@react-three/drei";
import * as THREE from "three";
import { useDeskLayout } from "../stores/deskLayout";
import "./HudScreen.css";
import "./hudContactPortal.css";

// drei's <Html transform> divides the group's matrix by 40 internally
// (defaults from distanceFactor=10 → 400/10 scale on the inner CSS matrix).
// So to land at "1 CSS px = WORLD_PER_CSS_PX world units" the group's scale
// must be WORLD_PER_CSS_PX * 40. 0.002 m/px = 2 mm per CSS pixel makes a
// 400 px-wide panel ≈ 0.8 m in the scene at the default scale.
const WORLD_PER_CSS_PX = 0.002;
const GROUP_SCALE = WORLD_PER_CSS_PX * 40;

// drei's <Html transform center> applies an internal /40 scale to its CSS
// matrix so 1 CSS px = WORLD_PER_CSS_PX world units. Meshes in the same
// outer group use CSS px / 40 as local vertex units.
const PX_TO_LOCAL = 1 / 40;

/** Matches `.hud-screen__frame` border-radius in CSS px. */
const CORNER_RADIUS_PX = 22;

export type ResizeHandle =
  | "tl"
  | "tr"
  | "bl"
  | "br"
  | "top"
  | "bottom"
  | "left"
  | "right";

// Per-handle drag signs: dW>0 always means "this panel got wider", dH>0
// "taller", whichever edge you grabbed. The layout owner turns those signed
// deltas into the right boundary moves.
const HANDLE_SIGN: Record<ResizeHandle, { sx: number; sy: number }> = {
  tl: { sx: -1, sy: -1 },
  tr: { sx: 1, sy: -1 },
  bl: { sx: -1, sy: 1 },
  br: { sx: 1, sy: 1 },
  top: { sx: 0, sy: -1 },
  bottom: { sx: 0, sy: 1 },
  left: { sx: -1, sy: 0 },
  right: { sx: 1, sy: 0 },
};

type ResizeDrag = {
  pointerId: number;
  prevX: number;
  prevY: number;
  cssScale: number;
  handle: ResizeHandle;
};

export interface HudScreenProps {
  /** World-space position of the panel center, in meters. */
  position: [number, number, number];
  /** Rotation about the vertical axis, radians — tangent to the shared bent wall. */
  yaw: number;
  /** Live DOM size in CSS px (owned by the layout, not the panel). */
  widthPx: number;
  heightPx: number;
  title: string;
  /** Optional small status text on the right of the title bar. */
  tag?: string;
  /** Shared bend radius in CSS px — the panel face curves across its width on
   *  this cylinder, the same one the whole wall sits on. */
  curveRadiusPx: number;
  /** Glass background alpha (0..1) and backdrop blur (px). */
  bgOpacity: number;
  bgBlur: number;
  /** Panel title font size in CSS px. */
  headerFontPx: number;
  /** Content rendered on the right of the title row. */
  headerAside?: ReactNode;
  /** Screen-space links rendered as invisible 3D hit targets (CSS3D breaks <a> clicks). */
  headerLinks?: { href: string; label: string }[];
  /** Title row only — omit the body slot. */
  headerOnly?: boolean;
  /** Omit the title bar — for compact strips like contact icons. */
  hideHeader?: boolean;
  /** Cap padding on short panels so content isn't clipped by overflow. */
  compactPadding?: boolean;
  /** Incremental resize feedback: dW/dH are this panel's signed size change
   *  in CSS px since the previous event. */
  onResizeDelta?: (handle: ResizeHandle, dW: number, dH: number) => void;
  children: ReactNode;
}

export default function HudScreen({
  position,
  yaw,
  widthPx,
  heightPx,
  title,
  tag: _tag,
  curveRadiusPx,
  bgOpacity,
  bgBlur,
  headerFontPx,
  headerAside,
  headerLinks,
  headerOnly = false,
  hideHeader = false,
  compactPadding = false,
  onResizeDelta,
  children,
}: HudScreenProps) {
  const contentPaddingPx = useDeskLayout((s) => s.contentPaddingPx);
  const groupRef = useRef<THREE.Group>(null);
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);

  const resizeDrag = useRef<ResizeDrag | null>(null);

  useEffect(() => {
    const g = groupRef.current;
    if (!g) return;
    g.position.set(...position);
    // Tangent to the shared bent wall — same yaw every point on the flat
    // plane gets after the cylinder bend, so panels stay co-planar.
    g.rotation.set(0, yaw, 0);
  }, [position, yaw]);

  // Screen-px → panel-CSS-px scale at the panel's current depth. Collapses to
  // ~1 when the panel sits at its calibrated distance, so cursor and edge
  // travel match 1:1 there.
  const captureCssScale = useCallback((): number | null => {
    const g = groupRef.current;
    if (!g) return null;
    const persp = camera as THREE.PerspectiveCamera;
    const distance = camera.position.distanceTo(g.position);
    const fovRad = (persp.fov * Math.PI) / 180;
    const pixelToWorld = (2 * distance * Math.tan(fovRad / 2)) / size.height;
    return pixelToWorld / WORLD_PER_CSS_PX;
  }, [camera, size.height]);

  const onResizePointerDown = useCallback(
    (handle: ResizeHandle) => (e: ReactPointerEvent<HTMLDivElement>) => {
      e.stopPropagation();
      const cssScale = captureCssScale();
      if (cssScale == null) return;
      resizeDrag.current = {
        pointerId: e.pointerId,
        prevX: e.clientX,
        prevY: e.clientY,
        cssScale,
        handle,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [captureCssScale],
  );

  const onResizePointerMove = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      const d = resizeDrag.current;
      if (!d || d.pointerId !== e.pointerId) return;
      const dxScreen = e.clientX - d.prevX;
      const dyScreen = e.clientY - d.prevY;
      d.prevX = e.clientX;
      d.prevY = e.clientY;
      const { sx, sy } = HANDLE_SIGN[d.handle];
      const dW = sx * dxScreen * d.cssScale;
      const dH = sy * dyScreen * d.cssScale;
      if (dW !== 0 || dH !== 0) onResizeDelta?.(d.handle, dW, dH);
    },
    [onResizeDelta],
  );

  const endResizeDrag = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    if (resizeDrag.current?.pointerId === e.pointerId) {
      resizeDrag.current = null;
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  }, []);

  const handleProps = (handle: ResizeHandle) => ({
    onPointerDown: onResizePointerDown(handle),
    onPointerMove: onResizePointerMove,
    onPointerUp: endResizeDrag,
    onPointerCancel: endResizeDrag,
  });

  const panelStyle: CSSProperties = {
    width: `${widthPx}px`,
    height: `${heightPx}px`,
  };

  // The visible panel face — handle bar + content. Rendered once per slice as
  // a full-width layer that each slice clips to a vertical strip, so the
  // content (text, placeholders) bends together on the cylinder.
  const facePadV = compactPadding
    ? Math.min(contentPaddingPx, 10)
    : contentPaddingPx;
  const facePadH = compactPadding
    ? Math.min(contentPaddingPx, 16)
    : contentPaddingPx;
  const faceGap = compactPadding ? 6 : 12;

  const face = (
    <div
      className={
        hideHeader
          ? "hud-screen__face hud-screen__face--headerless"
          : headerOnly
            ? "hud-screen__face hud-screen__face--header-only"
            : compactPadding
              ? "hud-screen__face hud-screen__face--compact"
              : "hud-screen__face"
      }
      style={{
        padding: hideHeader
          ? `${facePadV}px ${facePadH}px`
          : `${facePadV}px ${facePadH}px`,
        gap: headerOnly ? "0px" : `${faceGap}px`,
      }}
    >
      {!hideHeader ? (
        <div className="hud-screen__handle" style={{ fontSize: `${headerFontPx}px` }}>
          <span className="hud-screen__handle-title">{title}</span>
          {headerAside}
        </div>
      ) : null}
      {!headerOnly ? (
        <div
          className={
            compactPadding ? "hud-screen__body hud-screen__body--compact" : "hud-screen__body"
          }
        >
          {children}
        </div>
      ) : null}
    </div>
  );

  const blurStyle =
    bgBlur > 0
      ? ({
          backdropFilter: `blur(${bgBlur}px)`,
          WebkitBackdropFilter: `blur(${bgBlur}px)`,
        } as CSSProperties)
      : undefined;

  return (
    <group ref={groupRef} scale={GROUP_SCALE}>
      <CurvedFillMesh
        widthPx={widthPx}
        heightPx={heightPx}
        curveRadiusPx={curveRadiusPx}
        opacity={bgOpacity}
      />
      <CurvedFaceSlices
        widthPx={widthPx}
        heightPx={heightPx}
        curveRadiusPx={curveRadiusPx}
        blurStyle={blurStyle}
        allowPointerEvents={!headerOnly}
      >
        {face}
      </CurvedFaceSlices>
      {headerLinks && headerLinks.length > 0 ? (
        <HeaderLinkPortal links={headerLinks} />
      ) : null}
      <BezelLines
        widthPx={widthPx}
        heightPx={heightPx}
        curveRadiusPx={curveRadiusPx}
      />
      <Html transform center zIndexRange={[110, 0]} pointerEvents="none">
        <div className="hud-screen hud-screen--handles" style={panelStyle}>
          <div className="hud-screen__edge hud-screen__edge--top" {...handleProps("top")} />
          <div className="hud-screen__edge hud-screen__edge--bottom" {...handleProps("bottom")} />
          <div className="hud-screen__edge hud-screen__edge--left" {...handleProps("left")} />
          <div className="hud-screen__edge hud-screen__edge--right" {...handleProps("right")} />
          <div className="hud-screen__corner hud-screen__corner--tl" {...handleProps("tl")} />
          <div className="hud-screen__corner hud-screen__corner--tr" {...handleProps("tr")} />
          <div className="hud-screen__corner hud-screen__corner--bl" {...handleProps("bl")} />
          <div className="hud-screen__corner hud-screen__corner--br" {...handleProps("br")} />
        </div>
      </Html>
    </group>
  );
}

function HeaderLinkPortal({
  links,
}: {
  links: { href: string; label: string }[];
}) {
  const anchorsRef = useRef<HTMLAnchorElement[]>([]);

  useEffect(() => {
    const container = document.createElement("div");
    container.className = "hud-contact-portal";
    document.body.appendChild(container);

    anchorsRef.current = links.map((link) => {
      const a = document.createElement("a");
      a.className = "hud-contact-portal__link";
      a.href = link.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.setAttribute("aria-label", link.label);
      a.title = link.label;
      a.addEventListener("pointerdown", (e) => e.stopPropagation());
      container.appendChild(a);
      return a;
    });

    return () => {
      container.remove();
      anchorsRef.current = [];
    };
  }, [links]);

  // Match screen-space hit targets to the decorative icons each frame. We
  // cannot render <a> through React inside R3F — the reconciler treats it as
  // a THREE primitive and crashes the canvas. Each curved slice repeats the
  // same icon row, so pick the largest on-screen rect per link index.
  useFrame(() => {
    const icons = document.querySelectorAll<HTMLElement>(".hud-contact__icon");
    const n = links.length;

    for (let i = 0; i < n; i++) {
      const el = anchorsRef.current[i];
      if (!el) continue;

      let best: DOMRect | null = null;
      let bestArea = 0;
      icons.forEach((icon, idx) => {
        if (idx % n !== i) return;
        const r = icon.getBoundingClientRect();
        const area = r.width * r.height;
        if (area > bestArea) {
          bestArea = area;
          best = r;
        }
      });

      if (!best || bestArea < 1) {
        el.style.display = "none";
        continue;
      }

      const pad = 8;
      el.style.display = "block";
      el.style.left = `${best.left - pad}px`;
      el.style.top = `${best.top - pad}px`;
      el.style.width = `${best.width + pad * 2}px`;
      el.style.height = `${best.height + pad * 2}px`;
    }
  });

  return null;
}

// Bend a flat panel by slicing it into vertical strips placed on the shared
// cylinder. CSS 3D inside a single drei's <Html transform> stays flat — the
// wrapper's matrix3d breaks nested preserve-3d — so each strip gets its own
// R3F group position/yaw plus a small Html clipped to that column.
const SLICE_PX = 90;
const MAX_SLICES = 12;

type CylinderSlice = {
  key: number;
  width: number;
  localU: number;
  position: [number, number, number];
  yaw: number;
  borderRadius: string;
};

function useCylinderSlices(
  widthPx: number,
  heightPx: number,
  curveRadiusPx: number,
): CylinderSlice[] {
  return useMemo(() => {
    const n = Math.max(1, Math.min(MAX_SLICES, Math.round(widthPx / SLICE_PX)));
    const sliceW = widthPx / n;
    const r = Math.min(CORNER_RADIUS_PX, sliceW, heightPx / 2);
    return Array.from({ length: n }, (_, i) => {
      const localU = (i + 0.5 - n / 2) * sliceW;
      const theta = localU / curveRadiusPx;
      const isFirst = i === 0;
      const isLast = i === n - 1;
      return {
        key: i,
        width: sliceW,
        localU,
        position: [
          curveRadiusPx * Math.sin(theta) * PX_TO_LOCAL,
          0,
          curveRadiusPx * (1 - Math.cos(theta)) * PX_TO_LOCAL,
        ],
        yaw: -theta,
        borderRadius: `${isFirst ? r : 0}px ${isLast ? r : 0}px ${isLast ? r : 0}px ${isFirst ? r : 0}px`,
      };
    });
  }, [widthPx, heightPx, curveRadiusPx]);
}

// The bent translucent glass, drawn as a real curved mesh in WebGL rather than
// CSS strips. A CSS approach can't both bend and stay seamless: slicing a
// translucent fill leaves overlap/gap seam lines, and the group-opacity trick
// that hides them forces `transform-style: flat`, which un-bends the strips.
// A single curved mesh sidesteps both: it bends smoothly on the same cylinder
// as the bezel and content, and its translucency comes from one material so
// there are no seams. It sits behind the CSS content (which composites on top).
const FILL_SEG_PX = 14;

// A canvas texture carries the vertical glass gradient and the rounded-corner
// alpha mask, so the mesh itself can stay a plain bent rectangle while still
// reading as a rounded glass panel.
function makeGlassTexture(widthPx: number, heightPx: number): THREE.CanvasTexture {
  const cap = 512;
  const scale = Math.min(1, cap / Math.max(widthPx, heightPx));
  const w = Math.max(2, Math.round(widthPx * scale));
  const h = Math.max(2, Math.round(heightPx * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const r = CORNER_RADIUS_PX * scale;

  ctx.beginPath();
  ctx.roundRect(0, 0, w, h, r);
  ctx.clip();

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgb(20, 40, 50)");
  grad.addColorStop(1, "rgb(6, 14, 20)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// A width-subdivided plane whose vertices are wrapped onto the cylinder (same
// math as the bezel), in the group's local units (CSS px / 40).
function buildCurvedFillGeometry(
  widthPx: number,
  heightPx: number,
  curveRadiusPx: number,
): THREE.BufferGeometry {
  const wSeg = Math.max(8, Math.min(64, Math.round(widthPx / FILL_SEG_PX)));
  const halfW = widthPx / 2;
  const top = (heightPx / 2) * PX_TO_LOCAL;
  const bottom = -(heightPx / 2) * PX_TO_LOCAL;

  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let j = 0; j <= wSeg; j++) {
    const u = -halfW + (j / wSeg) * widthPx;
    const theta = u / curveRadiusPx;
    const lx = curveRadiusPx * Math.sin(theta) * PX_TO_LOCAL;
    const lz = curveRadiusPx * (1 - Math.cos(theta)) * PX_TO_LOCAL;
    positions.push(lx, top, lz);
    uvs.push(j / wSeg, 1);
    positions.push(lx, bottom, lz);
    uvs.push(j / wSeg, 0);
  }
  for (let j = 0; j < wSeg; j++) {
    const a = j * 2;
    const b = j * 2 + 1;
    const c = (j + 1) * 2;
    const d = (j + 1) * 2 + 1;
    indices.push(a, b, c, c, b, d);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  return geo;
}

function CurvedFillMesh({
  widthPx,
  heightPx,
  curveRadiusPx,
  opacity,
}: {
  widthPx: number;
  heightPx: number;
  curveRadiusPx: number;
  opacity: number;
}) {
  const geometry = useMemo(
    () => buildCurvedFillGeometry(widthPx, heightPx, curveRadiusPx),
    [widthPx, heightPx, curveRadiusPx],
  );
  const texture = useMemo(
    () => makeGlassTexture(widthPx, heightPx),
    [widthPx, heightPx],
  );
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => texture.dispose(), [texture]);

  return (
    // Nudged a hair behind the bezel so the crisp outline always reads on top.
    <mesh geometry={geometry} position={[0, 0, -0.003]} renderOrder={-1}>
      <meshBasicMaterial
        map={texture}
        transparent
        opacity={opacity}
        depthWrite={false}
        toneMapped={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function CurvedFaceSlices({
  widthPx,
  heightPx,
  curveRadiusPx,
  blurStyle,
  allowPointerEvents = true,
  children,
}: {
  widthPx: number;
  heightPx: number;
  curveRadiusPx: number;
  blurStyle?: CSSProperties;
  allowPointerEvents?: boolean;
  children: ReactNode;
}) {
  const slices = useCylinderSlices(widthPx, heightPx, curveRadiusPx);
  const sliceClass = allowPointerEvents
    ? "hud-screen__slice-strip"
    : "hud-screen__slice-strip hud-screen__slice-strip--pass-through";

  return (
    <>
      {slices.map((slice) => (
        <group key={slice.key} position={slice.position} rotation={[0, slice.yaw, 0]}>
          <Html
            transform
            center
            zIndexRange={[100, 0]}
            pointerEvents={allowPointerEvents ? "auto" : "none"}
          >
            <div
              className={sliceClass}
              style={{
                width: `${slice.width}px`,
                height: `${heightPx}px`,
                borderRadius: slice.borderRadius,
              }}
            >
              {blurStyle ? (
                <div className="hud-screen__backdrop" style={blurStyle} />
              ) : null}
              <div
                className="hud-screen__slice-inner"
                style={{
                  width: `${widthPx}px`,
                  height: `${heightPx}px`,
                  transform: `translateX(calc(-50% - ${slice.localU}px))`,
                }}
              >
                {children}
              </div>
            </div>
          </Html>
        </group>
      ))}
    </>
  );
}

// 3D bezel — drawn as fat Line2s in the WebGL canvas instead of as an SVG
// inside drei's Html. SVG strokes under a CSS3D matrix3d transform alias
// badly on tilted panel edges; Line2 strokes go through the renderer's MSAA
// pass and pick up the same bloom that lights the desk lines, so the panel
// outline reads as part of the same cyan world rather than a flat decal.
//
const BEZEL_COLOR = "#9cf8f8";

function roundedRectOutline(
  halfW: number,
  halfH: number,
  radius: number,
  segments = 10,
): [number, number, number][] {
  const r = Math.min(radius, halfW, halfH);
  const pts: [number, number, number][] = [];

  const pushArc = (cx: number, cy: number, start: number, end: number) => {
    for (let i = 0; i <= segments; i++) {
      const t = start + ((end - start) * i) / segments;
      pts.push([cx + Math.cos(t) * r, cy + Math.sin(t) * r, 0]);
    }
  };

  const pushLine = (x0: number, x1: number, y: number, steps: number) => {
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      pts.push([x0 + (x1 - x0) * t, y, 0]);
    }
  };

  const pushVLine = (x: number, y0: number, y1: number, steps: number) => {
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      pts.push([x, y0 + (y1 - y0) * t, 0]);
    }
  };

  // Clockwise from the top edge, starting just right of the top-left arc.
  pushLine(-(halfW - r), halfW - r, halfH, 8);
  pushArc( halfW - r, halfH - r, Math.PI / 2, 0);
  pushVLine( halfW, halfH - r, -(halfH - r), 4);
  pushArc( halfW - r, -(halfH - r), 0, -Math.PI / 2);
  pushLine( halfW - r, -(halfW - r), -halfH, 8);
  pushArc(-(halfW - r), -(halfH - r), -Math.PI / 2, -Math.PI);
  pushVLine(-halfW, -(halfH - r), halfH - r, 4);
  pushArc(-(halfW - r), halfH - r, Math.PI, Math.PI / 2);
  pushLine(-(halfW - r), -(halfW - r), halfH, 8);

  return pts;
}

function BezelLines({
  widthPx,
  heightPx,
  curveRadiusPx,
}: {
  widthPx: number;
  heightPx: number;
  curveRadiusPx: number;
}) {
  const bezelEmission = useDeskLayout((s) => s.bezelEmission);
  const bezelLineWidth = useDeskLayout((s) => s.bezelLineWidth);
  const bezelOpacity = useDeskLayout((s) => s.bezelOpacity);

  const outline = useMemo(() => {
    const halfW = (widthPx * PX_TO_LOCAL) / 2;
    const halfH = (heightPx * PX_TO_LOCAL) / 2;
    const radius = CORNER_RADIUS_PX * PX_TO_LOCAL;
    const flat = roundedRectOutline(halfW, halfH, radius);
    // Bend the outline across width on the same cylinder as the face so the
    // crisp edge tracks the bent surface. Work in CSS px (local / PX_TO_LOCAL),
    // then convert back. Center at z=0, edges sweep toward +Z (toward viewer).
    const R = curveRadiusPx;
    return flat.map(([x, y]) => {
      const xPx = x / PX_TO_LOCAL;
      const theta = xPx / R;
      const bentX = R * Math.sin(theta) * PX_TO_LOCAL;
      const bentZ = R * (1 - Math.cos(theta)) * PX_TO_LOCAL;
      return [bentX, y, bentZ] as [number, number, number];
    });
  }, [widthPx, heightPx, curveRadiusPx]);

  const lineColor = useMemo(
    () => new THREE.Color(BEZEL_COLOR).multiplyScalar(bezelEmission),
    [bezelEmission],
  );

  return (
    <DreiLine
      points={outline}
      color={lineColor}
      lineWidth={bezelLineWidth}
      transparent
      opacity={bezelOpacity}
      toneMapped={false}
      depthWrite={false}
    />
  );
}
