import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { usePanelBorder, usePanelCorners } from "./panelCornerStore";

/**
 * Four holograms standing in the air over the workshop desk.
 *
 * The desk is not a straight bench: it is a centre run with two wings angled
 * back at PHI, and those two corners cut the space above it into three bays.
 * One panel fills the centre bay in front of the rack stack, one spans the
 * left wing, and the right wing carries a pair split down its middle. The
 * constants below are the same ones `export_pillar.py` used to build the desk,
 * so the panels stay glued to the wings if the desk is ever rebuilt.
 */
const CA = THREE.MathUtils.degToRad(56); // desk frame's yaw about the pillar
const PHI = THREE.MathUtils.degToRad(38); // wing splay
const U_BACK = 1.76; // back line of the desk, along +u
const WC = 1.9; // centre-run width, along v

const PILLAR_X = 21.3; // pillar axis in the glTF's pre-recentre space
const MACHINERY_TOP_Y = 8.125; // top of the tallest centre rack

/** Panel height. Their centres sit on the machinery's top edge, so this also
 *  fixes the gap over the desk: (8.125 − 1.14/2) − 7.3552 ≈ 0.2 m of air. */
const PANEL_H = 1.14;
/** How far forward of each bay's back line the screen floats. */
const PANEL_DEPTH = 0.36;
// Move the whole assembly toward the racks without changing the wing gaps.
const PANEL_SETBACK = 0.24;
const PANEL_SCALE = 1.5;
// Scale around the centre bay and lift the lower datum, keeping every panel
// above the tabletop instead of growing downward into it.
const PANEL_ANCHOR_U = U_BACK - PANEL_DEPTH + PANEL_SETBACK;
const PANEL_LIFT = PANEL_H * (PANEL_SCALE - 1) / 2 - 0.04;

const WING_W = 0.8;
const BAY_W = 1.55;
const PANEL_GAP = 0.12;
const HALF_H = (PANEL_H - PANEL_GAP) / 2;

// Solve the distance between adjacent inner edges in the desk's XZ plane.
// Both splayed wings get the same 12 cm clearance as the right stack seam.
const cornerU = PANEL_DEPTH * (1 - Math.cos(PHI));
const cornerV = WC / 2 - BAY_W / 2 - PANEL_DEPTH * Math.sin(PHI);
const alongProjection = -cornerU * Math.sin(PHI) + cornerV * Math.cos(PHI);
const perpendicular = cornerU * Math.cos(PHI) + cornerV * Math.sin(PHI);
const WING_ALONG = WING_W / 2 - alongProjection
  + Math.sqrt(PANEL_GAP ** 2 - perpendicular ** 2);

type Section = -1 | 0 | 1;

/** Origin, tangent and outward normal of one desk bay, in the (u, v) frame. */
function bay(section: Section) {
  if (section === 0) {
    return { origin: [U_BACK, 0], tangent: [0, 1], normal: [1, 0] } as const;
  }
  const g = section > 0 ? 1 : -1;
  return {
    origin: [U_BACK, (g * WC) / 2],
    tangent: [-Math.sin(PHI), g * Math.cos(PHI)],
    normal: [Math.cos(PHI), g * Math.sin(PHI)],
  } as const;
}

/** (u, v) of a point `along` a bay's tangent and `depth` in front of it. */
function onBay(section: Section, along: number, depth: number) {
  const { origin, tangent, normal } = bay(section);
  return [
    origin[0] + along * tangent[0] - depth * normal[0],
    origin[1] + along * tangent[1] - depth * normal[1],
  ] as const;
}

/** (u, v, height) → glTF position, matching `uvp()` in export_pillar.py. */
function place(u: number, v: number, y: number): [number, number, number] {
  const c = Math.cos(CA);
  const s = Math.sin(CA);
  return [PILLAR_X + u * c - v * s, y, -(u * s + v * c)];
}

/** Yaw that turns a panel's face (+Z) back towards the seat. */
function yaw(section: Section): number {
  const { normal } = bay(section);
  const c = Math.cos(CA);
  const s = Math.sin(CA);
  const du = -normal[0];
  const dv = -normal[1];
  return Math.atan2(du * c - dv * s, -(du * s + dv * c));
}

type PanelKey = "description" | "demo" | "architecture" | "results";
type PanelSpec = {
  key: PanelKey;
  section: Section;
  along: number;
  width: number;
  height: number;
  rise: number;
};

// All outer edges share the same top and bottom datums. The right stack
// divides that exact height, including the gap between its two panels.
const PANELS: readonly PanelSpec[] = [
  { key: "description", section: 1, along: WING_ALONG, width: WING_W, height: PANEL_H, rise: 0 },
  { key: "demo", section: 0, along: 0, width: BAY_W, height: PANEL_H, rise: 0 },
  { key: "architecture", section: -1, along: WING_ALONG, width: WING_W, height: HALF_H, rise: (HALF_H + PANEL_GAP) / 2 },
  { key: "results", section: -1, along: WING_ALONG, width: WING_W, height: HALF_H, rise: -(HALF_H + PANEL_GAP) / 2 },
];
const TITLES: Record<PanelKey, string> = {
  description: "Project description",
  demo: "Demo",
  architecture: "System architecture",
  results: "Results",
};
const CHAMFER = 0.04;
const BORDER = 0.004;
const INK = "#eff8ff";
const MUTED = "#b9d7ec";
const BLUE = "#65c5f2";

function chamferedPath(w: number, h: number, r: number) {
  const shape = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  if (r === 0) {
    shape.moveTo(x, y);
    shape.lineTo(x + w, y);
    shape.lineTo(x + w, y + h);
    shape.lineTo(x, y + h);
    shape.closePath();
    return shape;
  }
  shape.moveTo(x + r, y);
  shape.lineTo(x + w - r, y);
  shape.lineTo(x + w, y + r);
  shape.lineTo(x + w, y + h - r);
  shape.lineTo(x + w - r, y + h);
  shape.lineTo(x + r, y + h);
  shape.lineTo(x, y + h - r);
  shape.lineTo(x, y + r);
  shape.closePath();
  return shape;
}

/** Logical pixels use one shared physical scale, including every header. */
function drawPanel(spec: PanelSpec, cornerCut: number) {
  const w = spec.width * 1000, h = spec.height * 1000;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(w * 2);
  canvas.height = Math.round(h * 2);
  const ctx = canvas.getContext("2d")!;
  ctx.scale(2, 2);
  ctx.textBaseline = "middle";
  const text = (value: string, x: number, y: number, size = 24, color = INK, weight = 500) => {
    ctx.font = `${weight} ${size * 1.14}px -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif`;
    ctx.fillStyle = color;
    ctx.fillText(value, x, y);
  };
  const line = (x: number, y: number, x2: number, y2: number, alpha = 0.3) => {
    ctx.strokeStyle = `rgba(100, 198, 245, ${alpha})`;
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke();
  };
  const chamfer = (x: number, y: number, bw: number, bh: number, cut: number) => {
    ctx.beginPath();
    ctx.moveTo(x + cut, y); ctx.lineTo(x + bw - cut, y);
    ctx.lineTo(x + bw, y + cut); ctx.lineTo(x + bw, y + bh - cut);
    ctx.lineTo(x + bw - cut, y + bh); ctx.lineTo(x + cut, y + bh);
    ctx.lineTo(x, y + bh - cut); ctx.lineTo(x, y + cut); ctx.closePath();
  };

  // The display dims the scene behind it without reflection or refraction.
  chamfer(0, 0, w, h, cornerCut * 1000); ctx.clip();
  text(TITLES[spec.key], 42, 52, 32, INK, 500);
  line(42, 88, w - 42, 88);
  line(42, 88, 122, 88, 0.8);

  // Illustrative data is fixed and labelled; these are layout placeholders.
  const series = [0.2, 0.38, 0.29, 0.64, 0.47, 0.24, 0.33, 0.52, 0.41, 0.73, 0.56, 0.39, 0.62, 0.84, 0.5, 0.68, 0.43, 0.9, 0.59, 0.75];
  const plot = (x: number, y: number, pw: number, ph: number, bars = false) => {
    for (let i = 0; i <= 4; i++) line(x, y + ph * i / 4, x + pw, y + ph * i / 4, 0.15);
    if (bars) {
      const step = pw / series.length;
      series.forEach((v, i) => {
        ctx.fillStyle = i % 3 === 0 ? BLUE : "rgba(112, 177, 215, 0.5)";
        ctx.fillRect(x + i * step + 2, y + ph * (1 - v), step * 0.65, ph * v);
      });
    } else {
      ctx.beginPath();
      series.forEach((v, i) => {
        const px = x + i * pw / (series.length - 1), py = y + ph * (1 - v);
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      });
      ctx.strokeStyle = BLUE; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.lineTo(x + pw, y + ph); ctx.lineTo(x, y + ph); ctx.closePath();
      const fill = ctx.createLinearGradient(0, y, 0, y + ph);
      fill.addColorStop(0, "rgba(101, 197, 242, 0.42)"); fill.addColorStop(1, "rgba(101, 197, 242, 0.015)");
      ctx.fillStyle = fill; ctx.fill();
    }
  };

  if (spec.key === "description") {

    text("Project name", 65, 179, 46, INK, 500);
    text("A concise project introduction", 65, 240, 26, MUTED);
    text("Purpose, audience and approach", 65, 283, 24, MUTED);
    text("Project 01  /  Concept preview", 65, 333, 20, BLUE);

    text("Overview", 65, 442, 29, INK, 500);
    ["Describe the problem this project solves.", "Explain the central idea and the", "experience you designed around it.", "Add the important decisions here."].forEach((t, i) => text(t, 65, 495 + i * 38, 25, MUTED));

    [["Role", "Your role"], ["Timeline", "Project timeline"], ["Stack", "Tools and technologies"]].forEach(([label, value], i) => {
      text(label, 65, 742 + i * 65, 24, MUTED);
      text(value, 244, 742 + i * 65, 25);
      if (i < 2) line(65, 771 + i * 65, w - 65, 771 + i * 65, 0.14);
    });
    text("Project details to be added", 44, 995, 22, MUTED);
    text("Placeholder content", 44, h - 54, 20, MUTED);
  } else if (spec.key === "demo") {
    text("Analytics workspace", 44, 139, 36, INK, 500);
    text("Illustrative demo / sample data", 44, 184, 22, MUTED);
    const cw = (w - 116) / 3;
    ["Activity", "Response", "Completion"].forEach((label, i) => {
      const x = 38 + i * (cw + 20);

      text(label, x + 24, 261, 24, MUTED);
      text(["2,480", "128 ms", "94.2%"][i], x + 24, 321, 49, INK, 400);
      text("Sample metric", x + 24, 368, 18, MUTED);
    });
    const leftW = (w - 96) * 0.6;

    text("Activity over time", 63, 454, 27, INK, 500);
    plot(70, 499, leftW - 64, 205);
    text("Mon           Tue           Wed           Thu           Fri", 70, 733, 18, MUTED);
    const rx = 58 + leftW, rw = w - rx - 38;

    text("Event volume", rx + 25, 454, 27, INK, 500);
    plot(rx + 30, 499, rw - 60, 205, true);
    text("Sample distribution", rx + 30, 733, 18, MUTED);

    text("Processing overview", 63, 823, 27, INK, 500);
    plot(68, 864, w - 136, 116, true);
    text("Demo placeholder", 44, h - 51, 21, MUTED);
    ctx.textAlign = "right"; text("01 / 01", w - 44, h - 51, 20, BLUE); ctx.textAlign = "left";
  } else if (spec.key === "architecture") {
    const nodeW = 190;
    const xs = [44, w / 2 - nodeW / 2, w - 44 - nodeW];
    xs.forEach((x, i) => {

      ctx.textAlign = "center"; text(["CLIENT", "SERVICE", "DATA"][i], x + nodeW / 2, 197, 22, INK, 500); ctx.textAlign = "left";
      if (i < 2) {
        line(x + nodeW, 197, xs[i + 1], 197, 0.7);
        line(xs[i + 1] - 9, 192, xs[i + 1], 197, 0.7);
        line(xs[i + 1] - 9, 202, xs[i + 1], 197, 0.7);
      }
    });
    line(w / 2, 233, w / 2, 294, 0.7);

    ctx.textAlign = "center"; text("INFRASTRUCTURE", w / 2, 327, 21, MUTED); ctx.textAlign = "left";
    text("Example flow / replace with your system", 44, h - 57, 21, MUTED);
  } else {
    const col = (w - 100) / 3;
    ["Speed", "Uptime", "Impact"].forEach((label, i) => {
      const x = 38 + i * (col + 12);

      text(label, x + 15, 152, 21, MUTED);
      text(["128 ms", "99.9%", "+24%"][i], x + 15, 206, 35, INK, 400);
    });

    text("Outcome trend", 58, 298, 24, INK, 500);
    plot(60, 327, w - 120, 86);
    text("Illustrative results / sample data", 44, h - 38, 19, MUTED);
  }
  return canvas;
}

// Screen-space derivatives filter both sides of the chamfered border.
// Unlike a subpixel triangle strip, coverage changes smoothly while orbiting.
const BORDER_VERTEX = `
  varying vec2 panelPosition;
  void main() {
    panelPosition = position.xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const BORDER_FRAGMENT = `
  varying vec2 panelPosition;
  uniform vec2 halfSize;
  uniform float chamfer;
  uniform float borderWidth;
  uniform vec3 lightColor;
  float segmentDistance(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    // A square corner collapses the diagonal segment to a single point.
    return length(p - a - ab * clamp(dot(p - a, ab) / max(dot(ab, ab), 0.00000001), 0.0, 1.0));
  }
  void main() {
    vec2 p = abs(panelPosition);
    vec2 h = halfSize - borderWidth * 0.5;
    // Measure the actual connected segments. Intersecting half-plane fields
    // had discontinuous derivatives at the two ends of each diagonal cut.
    vec2 topJoin = vec2(h.x - chamfer, h.y);
    vec2 sideJoin = vec2(h.x, h.y - chamfer);
    float edge = min(
      segmentDistance(p, vec2(0.0, h.y), topJoin),
      min(segmentDistance(p, topJoin, sideJoin),
          segmentDistance(p, sideJoin, vec2(h.x, 0.0))));
    // A rectangular distance field gives exact 90-degree joins, rather than
    // the rounded end caps produced by distance-to-segment at each corner.
    if (chamfer == 0.0) edge = abs(max(p.x - h.x, p.y - h.y));
    // Derive pixel size from the continuous panel coordinates, not distance
    // to the edge, whose gradient changes direction at a corner.
    float aa = max(length(vec2(length(dFdx(panelPosition)), length(dFdy(panelPosition)))), 0.00001);
    // Pixel coverage of a thin stroke: subpixel lines fade proportionally
    // instead of being widened to a mandatory one-pixel glowing border.
    float halfWidth = borderWidth * 0.5;
    float core = clamp((halfWidth - edge) / aa + 0.5, 0.0, 1.0)
      - clamp((-halfWidth - edge) / aa + 0.5, 0.0, 1.0);
    gl_FragColor = vec4(lightColor, core);
    #include <colorspace_fragment>
  }
`;

function Panel({ spec, lightColor, square }: { spec: PanelSpec; lightColor: THREE.Color; square: boolean }) {
  const thickness = usePanelBorder((state) => state.thickness);
  const borderMaterial = useRef<THREE.ShaderMaterial>(null);
  const invalidate = useThree((state) => state.invalidate);
  const cornerCut = square ? 0 : CHAMFER;
  const [u, v] = onBay(spec.section, spec.along, PANEL_DEPTH);
  const assets = useMemo(() => {
    const shape = chamferedPath(spec.width, spec.height, cornerCut);
    const texture = new THREE.CanvasTexture(drawPanel(spec, cornerCut));
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 16;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    return {
      texture,
      surface: new THREE.ShapeGeometry(shape),
      borderUniforms: {
        halfSize: { value: new THREE.Vector2(spec.width / 2, spec.height / 2) },
        chamfer: { value: cornerCut },
        borderWidth: { value: BORDER },
      },
    };
  }, [spec, cornerCut]);
  useEffect(() => () => {
    assets.texture.dispose(); assets.surface.dispose();
  }, [assets]);
  useLayoutEffect(() => {
    if (!borderMaterial.current) return;
    borderMaterial.current.uniforms.borderWidth.value = BORDER * thickness;
    borderMaterial.current.uniforms.lightColor.value.copy(lightColor);
    invalidate();
  }, [thickness, lightColor, invalidate]);

  return (
    <group name={`stationPanel_${spec.key}`} position={place(
      PANEL_ANCHOR_U + (u + PANEL_SETBACK - PANEL_ANCHOR_U) * PANEL_SCALE,
      v * PANEL_SCALE,
      MACHINERY_TOP_Y + PANEL_LIFT + spec.rise * PANEL_SCALE,
    )} rotation={[0, yaw(spec.section), 0]} scale={PANEL_SCALE}>
      <mesh geometry={assets.surface} renderOrder={1}>
        <meshBasicMaterial color="#08192c" transparent opacity={0.95} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0, 0.003]} renderOrder={2}>
        <planeGeometry args={[spec.width, spec.height]} />
        <meshBasicMaterial map={assets.texture} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {/* Analytic pixel coverage keeps thin HDR edges smooth at any angle.
          The padded quad leaves room for the antialiasing outside the rim. */}
      <mesh position={[0, 0, 0.005]} renderOrder={3}>
        <planeGeometry args={[spec.width + 0.04, spec.height + 0.04]} />
        <shaderMaterial
          key={`border-${thickness}`}
          ref={borderMaterial}
          uniforms={{ ...assets.borderUniforms, borderWidth: { value: BORDER * thickness }, lightColor: { value: lightColor } }}
          vertexShader={BORDER_VERTEX}
          fragmentShader={BORDER_FRAGMENT}
          transparent
          depthWrite={false}
          toneMapped={false}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}

export function StationPanels({ lightColor }: { lightColor: THREE.Color }) {
  const square = usePanelCorners((state) => state.square);
  const invalidate = useThree((state) => state.invalidate);
  // Commit the new geometry and shader before requesting a demand-mode frame.
  useLayoutEffect(() => { invalidate(); }, [square, invalidate]);
  return (
    <group name="stationPanels">
      {PANELS.map((spec) => <Panel key={`${spec.key}-${square ? "square" : "beveled"}`} spec={spec} lightColor={lightColor} square={square} />)}

    </group>
  );
}
