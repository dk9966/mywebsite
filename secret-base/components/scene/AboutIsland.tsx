import { useMemo } from "react";
import * as THREE from "three";
import { IslandBase } from "./IslandBase";
import { Lamp } from "./Lamp";
import {
  graphite,
  graphiteDark,
  hologram,
  hologramWire,
  holoCore,
  mcLeaves,
  neonCyan,
  neonCyanFaint,
  rock,
} from "./materials";
import { islandLayout } from "./layout";
import { profile, skillGroups } from "../../../src/data/resume";

// the whole holo rig faces the camera's approach direction (toward Projects)
const RIG_YAW = 1.165;

function makeTexture(
  w: number,
  h: number,
  draw: (ctx: CanvasRenderingContext2D) => void,
): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  draw(canvas.getContext("2d")!);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

function panelChrome(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.beginPath();
  ctx.roundRect(8, 8, w - 16, h - 16, 18);
  ctx.fillStyle = "rgba(12, 32, 96, 0.85)";
  ctx.fill();
  ctx.strokeStyle = "rgba(90, 150, 255, 0.45)";
  ctx.lineWidth = 10;
  ctx.stroke();
  ctx.strokeStyle = "#74aaff";
  ctx.lineWidth = 4;
  ctx.stroke();
}

function sectionHeader(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
) {
  ctx.fillStyle = "#7cd7ff";
  ctx.font = "bold 34px 'Segoe UI', Arial, sans-serif";
  ctx.fillText(text, x, y);
  ctx.strokeStyle = "rgba(140,180,255,0.5)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x - 2, y + 28);
  ctx.lineTo(x + ctx.measureText(text).width + 30, y + 28);
  ctx.stroke();
}

const SKILL_PCTS = [95, 90, 86, 82, 76];

/**
 * The big combined panel from the reference: PROFILE and SKILLS columns
 * side by side, EXPERIENCE (badge + impact chart) spanning underneath.
 */
function drawResumePanel(ctx: CanvasRenderingContext2D) {
  const w = 1100;
  const h = 780;
  panelChrome(ctx, w, h);
  ctx.textBaseline = "middle";

  // column divider
  ctx.strokeStyle = "rgba(110,160,255,0.25)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(530, 56);
  ctx.lineTo(530, 452);
  ctx.stroke();

  // ---- left column: PROFILE ----
  sectionHeader(ctx, "PROFILE", 56, 66);
  const rows: [string, string, string?][] = [
    ["Name", profile.name],
    ["Role", profile.role],
    ["Location", "Urbana-Champaign, IL"],
    ["Education", "MCS CS · UIUC"],
    ["Availability", "Open to Work", "#4ade80"],
  ];
  rows.forEach(([label, value, color], i) => {
    const y = 152 + i * 70;
    ctx.fillStyle = "#7cd7ff";
    ctx.font = "20px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(label, 56, y);
    ctx.fillStyle = color ?? "#eef4ff";
    ctx.font = "bold 27px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(value, 56, y + 30);
  });

  // ---- right column: SKILLS ----
  sectionHeader(ctx, "SKILLS", 572, 66);
  const langs = skillGroups[0].items;
  langs.forEach((skill, i) => {
    const y = 158 + i * 62;
    const pct = SKILL_PCTS[i] ?? 70;
    ctx.fillStyle = "#eef4ff";
    ctx.font = "23px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(skill, 572, y);
    ctx.fillStyle = "rgba(90,140,220,0.3)";
    ctx.fillRect(724, y - 9, 240, 18);
    ctx.fillStyle = "#4fc3f7";
    ctx.fillRect(724, y - 9, (240 * pct) / 100, 18);
    ctx.fillStyle = "#c6d9ff";
    ctx.font = "20px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(`${pct}%`, 982, y);
  });

  // ---- spanning section: EXPERIENCE ----
  sectionHeader(ctx, "EXPERIENCE", 56, 512);
  // internships badge
  ctx.strokeStyle = "#4fc3f7";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.arc(150, 650, 62, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "#eef4ff";
  ctx.textAlign = "center";
  ctx.font = "bold 52px 'Segoe UI', Arial, sans-serif";
  ctx.fillText(profile.stats[1].value, 150, 638);
  ctx.font = "18px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("internships", 150, 682);
  ctx.textAlign = "left";

  // impact area chart
  const pts: [number, number][] = [
    [330, 712],
    [450, 688],
    [560, 694],
    [670, 654],
    [790, 622],
    [910, 632],
    [1020, 574],
  ];
  const base = 726;
  const grad = ctx.createLinearGradient(0, 560, 0, base);
  grad.addColorStop(0, "rgba(79,195,247,0.4)");
  grad.addColorStop(1, "rgba(79,195,247,0.02)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], base);
  pts.forEach(([px, py]) => ctx.lineTo(px, py));
  ctx.lineTo(pts[pts.length - 1][0], base);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#4fc3f7";
  ctx.lineWidth = 5;
  ctx.beginPath();
  pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
  ctx.stroke();
  ctx.fillStyle = "#8aa6d6";
  ctx.font = "17px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("2021", 330, 748);
  ctx.fillText("impact over time", 560, 748);
  ctx.fillText("2026", 985, 748);
}

/** Small square widget: target/compass dial. */
function drawDial(ctx: CanvasRenderingContext2D) {
  const s = 256;
  panelChrome(ctx, s, s);
  const c = s / 2;
  ctx.strokeStyle = "#7cc4ff";
  ctx.lineWidth = 5;
  [92, 62].forEach((r) => {
    ctx.beginPath();
    ctx.arc(c, c, r, 0, Math.PI * 2);
    ctx.stroke();
  });
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(c, c - 104);
  ctx.lineTo(c, c + 104);
  ctx.moveTo(c - 104, c);
  ctx.lineTo(c + 104, c);
  ctx.stroke();
  ctx.fillStyle = "#7cc4ff";
  ctx.beginPath();
  ctx.moveTo(c, c);
  ctx.lineTo(c + 40, c - 52);
  ctx.lineTo(c + 12, c - 8);
  ctx.closePath();
  ctx.fill();
  ctx.beginPath();
  ctx.arc(c, c, 8, 0, Math.PI * 2);
  ctx.fill();
}

/** Small square widget: bar chart. */
function drawBars(ctx: CanvasRenderingContext2D) {
  const s = 256;
  panelChrome(ctx, s, s);
  ctx.strokeStyle = "rgba(120,170,255,0.3)";
  ctx.lineWidth = 2;
  [70, 120, 170].forEach((y) => {
    ctx.beginPath();
    ctx.moveTo(36, y);
    ctx.lineTo(220, y);
    ctx.stroke();
  });
  [64, 108, 52, 128, 88].forEach((bh, i) => {
    ctx.fillStyle = "#4fc3f7";
    ctx.fillRect(44 + i * 36, 204 - bh, 24, bh);
  });
}

/** Bright radar disc projected on the platform top. */
function drawDisc(ctx: CanvasRenderingContext2D) {
  const s = 512;
  const c = s / 2;
  ctx.clearRect(0, 0, s, s);
  const grad = ctx.createRadialGradient(c, c, 6, c, c, c - 8);
  grad.addColorStop(0, "rgba(235, 250, 255, 1)");
  grad.addColorStop(0.12, "rgba(140, 205, 255, 0.75)");
  grad.addColorStop(0.35, "rgba(60, 150, 255, 0.4)");
  grad.addColorStop(0.8, "rgba(30, 90, 220, 0.2)");
  grad.addColorStop(1, "rgba(30, 90, 220, 0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(c, c, c - 8, 0, Math.PI * 2);
  ctx.fill();
  // solid rings
  ctx.strokeStyle = "rgba(150, 215, 255, 0.85)";
  [42, 78, 116, 154, 192, 232].forEach((r, i, all) => {
    ctx.lineWidth = i === all.length - 1 ? 8 : 3;
    ctx.beginPath();
    ctx.arc(c, c, r, 0, Math.PI * 2);
    ctx.stroke();
  });
  // dashed tick ring
  ctx.save();
  ctx.setLineDash([10, 14]);
  ctx.lineWidth = 5;
  ctx.strokeStyle = "rgba(170, 225, 255, 0.7)";
  ctx.beginPath();
  ctx.arc(c, c, 212, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
  // spokes
  ctx.strokeStyle = "rgba(140, 210, 255, 0.3)";
  ctx.lineWidth = 2;
  for (let i = 0; i < 24; i++) {
    const a = (i / 24) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(c + 42 * Math.cos(a), c + 42 * Math.sin(a));
    ctx.lineTo(c + 232 * Math.cos(a), c + 232 * Math.sin(a));
    ctx.stroke();
  }
}

/** Inset console screen for the projector drum fascia. */
function drawConsole(accent: "blue" | "red") {
  return (ctx: CanvasRenderingContext2D) => {
    const w = 256;
    const h = 128;
    ctx.fillStyle = "#0a1526";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#31507e";
    ctx.lineWidth = 6;
    ctx.strokeRect(4, 4, w - 8, h - 8);
    // small screen with readout lines
    ctx.fillStyle = "#0e2a52";
    ctx.fillRect(20, 22, 130, 84);
    ctx.fillStyle = "#5fb2ff";
    for (let i = 0; i < 4; i++) {
      ctx.globalAlpha = 0.85 - i * 0.15;
      ctx.fillRect(30, 34 + i * 20, 60 + ((i * 47) % 50), 8);
    }
    ctx.globalAlpha = 1;
    // button cluster
    ctx.fillStyle = accent === "red" ? "#ff5252" : "#4fc3f7";
    ctx.beginPath();
    ctx.arc(190, 44, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#2b74d8";
    ctx.beginPath();
    ctx.arc(226, 44, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#1d3f70";
    ctx.fillRect(176, 74, 64, 14);
  };
}

/** Bolted metal plate for the ABOUT ME sign. */
function drawSignPlate(ctx: CanvasRenderingContext2D) {
  const w = 1024;
  const h = 288;
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#39415a");
  grad.addColorStop(0.5, "#262d44");
  grad.addColorStop(1, "#1c2236");
  ctx.fillStyle = grad;
  // plate with clipped corners
  const cut = 34;
  ctx.beginPath();
  ctx.moveTo(cut, 6);
  ctx.lineTo(w - cut, 6);
  ctx.lineTo(w - 6, cut);
  ctx.lineTo(w - 6, h - cut);
  ctx.lineTo(w - cut, h - 6);
  ctx.lineTo(cut, h - 6);
  ctx.lineTo(6, h - cut);
  ctx.lineTo(6, cut);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#4d5878";
  ctx.lineWidth = 8;
  ctx.stroke();
  ctx.strokeStyle = "rgba(10,14,24,0.8)";
  ctx.lineWidth = 3;
  ctx.stroke();
  // corner bolts
  [
    [52, 52],
    [w - 52, 52],
    [52, h - 52],
    [w - 52, h - 52],
  ].forEach(([bx, by]) => {
    ctx.fillStyle = "#151b2c";
    ctx.beginPath();
    ctx.arc(bx, by, 15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#5d6a8e";
    ctx.beginPath();
    ctx.arc(bx - 3, by - 3, 9, 0, Math.PI * 2);
    ctx.fill();
  });
  // text
  ctx.fillStyle = "#f2f6ff";
  ctx.font = "bold 128px 'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("ABOUT ME", w / 2, h / 2 + 6);
}

function HoloPanelMesh({
  texture,
  width,
  height,
  position,
  rotation = [0, 0, 0],
}: {
  texture: THREE.CanvasTexture;
  width: number;
  height: number;
  position: [number, number, number];
  rotation?: [number, number, number];
}) {
  return (
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={[width, height]} />
      <meshBasicMaterial
        map={texture}
        transparent
        toneMapped={false}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

/** Holographic bust: hooded low-poly figure + wireframe + glowing core. */
function HoloBust() {
  return (
    <group name="holoBust">
      {/* chest: wide shoulders tapering down */}
      <mesh material={hologram} position={[0, 2.02, 0]}>
        <cylinderGeometry args={[0.58, 0.38, 0.7, 10]} />
      </mesh>
      <mesh material={hologramWire} position={[0, 2.02, 0]}>
        <cylinderGeometry args={[0.585, 0.385, 0.7, 10]} />
      </mesh>
      {/* rounded shoulder caps */}
      {[-0.5, 0.5].map((x) => (
        <mesh key={x} material={hologram} position={[x, 2.3, 0]}>
          <sphereGeometry args={[0.15, 8, 6]} />
        </mesh>
      ))}
      {/* hood bunched behind the neck */}
      <mesh
        material={hologram}
        position={[0, 2.42, -0.14]}
        scale={[1, 0.55, 0.8]}
      >
        <sphereGeometry args={[0.24, 10, 8]} />
      </mesh>
      {/* collar + neck */}
      <mesh material={hologram} position={[0, 2.4, 0]}>
        <cylinderGeometry args={[0.16, 0.2, 0.1, 8]} />
      </mesh>
      <mesh material={hologram} position={[0, 2.5, 0]}>
        <cylinderGeometry args={[0.1, 0.12, 0.14, 8]} />
      </mesh>
      {/* head + hair cap */}
      <mesh material={hologram} position={[0, 2.72, 0]}>
        <sphereGeometry args={[0.27, 12, 10]} />
      </mesh>
      <mesh material={hologramWire} position={[0, 2.72, 0]}>
        <sphereGeometry args={[0.275, 12, 10]} />
      </mesh>
      <mesh
        material={hologram}
        position={[0, 2.76, -0.02]}
        rotation={[-0.3, 0, 0]}
      >
        <sphereGeometry args={[0.29, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>
      {/* glowing chest core */}
      <mesh material={holoCore} position={[0, 2.06, 0.12]}>
        <sphereGeometry args={[0.09, 8, 6]} />
      </mesh>
      {/* horizontal scan rings */}
      {(
        [
          [1.78, 0.46],
          [2.06, 0.58],
          [2.34, 0.3],
          [2.66, 0.32],
        ] as [number, number][]
      ).map(([y, r]) => (
        <mesh key={y} material={hologram} rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]}>
          <torusGeometry args={[r, 0.012, 4, 24]} />
        </mesh>
      ))}
      {/* projection cone: converges to the bright emitter on the disc */}
      <mesh position={[0, 1.35, 0]}>
        <cylinderGeometry args={[0.55, 0.1, 1.2, 16, 1, true]} />
        <meshBasicMaterial
          color="#4a9aff"
          transparent
          opacity={0.16}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}

/** ABOUT ME plate hung from an overhead beam on two side posts. */
function SignRig({ texture }: { texture: THREE.CanvasTexture }) {
  const beamY = 4.35;
  const plateY = 3.72;
  const z = -0.5;
  return (
    <group name="aboutSign">
      {/* side posts */}
      {[-1.55, 1.55].map((x) => (
        <mesh key={x} material={graphiteDark} position={[x, beamY / 2, z]}>
          <boxGeometry args={[0.11, beamY, 0.11]} />
        </mesh>
      ))}
      {/* beam */}
      <mesh material={graphite} position={[0, beamY, z]}>
        <boxGeometry args={[3.35, 0.13, 0.13]} />
      </mesh>
      {/* hanger straps */}
      {[-1.05, 1.05].map((x) => (
        <mesh key={x} material={graphiteDark} position={[x, (beamY + plateY) / 2, z]}>
          <boxGeometry args={[0.06, beamY - plateY + 0.3, 0.06]} />
        </mesh>
      ))}
      {/* plate */}
      <mesh material={graphiteDark} position={[0, plateY, z - 0.04]}>
        <boxGeometry args={[2.95, 0.86, 0.08]} />
      </mesh>
      <mesh position={[0, plateY, z]}>
        <planeGeometry args={[2.85, 0.8]} />
        <meshBasicMaterial map={texture} toneMapped={false} />
      </mesh>
    </group>
  );
}

/** About island: holo projector with bust + resume panels (per reference). */
export function AboutIsland() {
  const { position, radius } = islandLayout.about;

  const resumeTex = useMemo(() => makeTexture(1100, 780, drawResumePanel), []);
  const dialTex = useMemo(() => makeTexture(256, 256, drawDial), []);
  const barsTex = useMemo(() => makeTexture(256, 256, drawBars), []);
  const discTex = useMemo(() => makeTexture(512, 512, drawDisc), []);
  const signTex = useMemo(() => makeTexture(1024, 288, drawSignPlate), []);
  const consoleBlueTex = useMemo(
    () => makeTexture(256, 128, drawConsole("blue")),
    [],
  );
  const consoleRedTex = useMemo(
    () => makeTexture(256, 128, drawConsole("red")),
    [],
  );

  return (
    <group name="aboutIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[[1.7, 2.9]]}
      />

      <group rotation={[0, RIG_YAW, 0]}>
        {/* projector drum: two dark tiers + lip */}
        <mesh material={graphiteDark} position={[0, 0.26, 0]}>
          <cylinderGeometry args={[2.05, 2.15, 0.52, 20]} />
        </mesh>
        <mesh material={graphite} position={[0, 0.6, 0]}>
          <cylinderGeometry args={[1.88, 2.0, 0.18, 20]} />
        </mesh>
        {/* inset console screens + neon seams around the fascia */}
        {Array.from({ length: 10 }, (_, i) => {
          const a = (i / 10) * Math.PI * 2 + 0.16;
          const pos: [number, number, number] = [
            2.16 * Math.cos(a),
            0.28,
            -2.16 * Math.sin(a),
          ];
          const rot: [number, number, number] = [0, a + Math.PI / 2, 0];
          if (i % 2 === 1) {
            return (
              <mesh
                key={i}
                material={i % 4 === 1 ? neonCyan : graphite}
                position={pos}
                rotation={rot}
              >
                <boxGeometry args={[0.4, i % 4 === 1 ? 0.07 : 0.26, 0.05]} />
              </mesh>
            );
          }
          return (
            <group key={i} position={pos} rotation={rot}>
              <mesh material={graphiteDark} position={[0, 0, -0.03]}>
                <boxGeometry args={[0.62, 0.34, 0.05]} />
              </mesh>
              <mesh>
                <planeGeometry args={[0.56, 0.28]} />
                <meshBasicMaterial
                  map={i === 4 ? consoleRedTex : consoleBlueTex}
                  toneMapped={false}
                />
              </mesh>
            </group>
          );
        })}
        {/* glowing radar disc + emitter core */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.71, 0]}>
          <circleGeometry args={[1.8, 40]} />
          <meshBasicMaterial
            map={discTex}
            transparent
            toneMapped={false}
            depthWrite={false}
          />
        </mesh>
        <mesh material={holoCore} position={[0, 0.72, 0]}>
          <sphereGeometry args={[0.12, 10, 8]} />
        </mesh>
        <mesh
          material={neonCyan}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.7, 0]}
        >
          <torusGeometry args={[1.88, 0.05, 4, 40]} />
        </mesh>
        {/* faint echo ring inscribed on the deck */}
        <mesh
          material={neonCyanFaint}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.03, 0]}
        >
          <torusGeometry args={[2.55, 0.03, 4, 40]} />
        </mesh>

        <HoloBust />

        {/* combined resume panel on the right */}
        <HoloPanelMesh
          texture={resumeTex}
          width={2.75}
          height={1.95}
          position={[2.4, 2.35, 0.15]}
          rotation={[0, -0.38, 0]}
        />
        {/* small widgets stacked on the left */}
        <HoloPanelMesh
          texture={dialTex}
          width={0.72}
          height={0.72}
          position={[-2.05, 3.0, -0.5]}
          rotation={[0, 0.42, 0]}
        />
        <HoloPanelMesh
          texture={barsTex}
          width={0.72}
          height={0.72}
          position={[-2.0, 2.14, -0.4]}
          rotation={[0, 0.42, 0]}
        />

        <SignRig texture={signTex} />
      </group>

      {/* blocky rock backdrop with plants + lantern */}
      <group name="rockStack">
        {(
          [
            [-2.35, -0.5, 0.9, 1.9],
            [-1.75, -1.35, 0.8, 2.5],
            [-2.5, -1.15, 0.7, 1.2],
            [-1.15, -1.95, 0.85, 1.5],
            [-2.05, -0.85, 0.6, 2.9],
          ] as [number, number, number, number][]
        ).map(([x, z, w, h], i) => (
          <mesh
            key={i}
            material={i % 2 === 0 ? rock : graphiteDark}
            position={[x, h / 2, z]}
            rotation={[0, i * 0.35, 0]}
          >
            <boxGeometry args={[w, h, w * 0.9]} />
          </mesh>
        ))}
        <mesh material={neonCyanFaint} position={[-2.08, 1.5, -0.52]}>
          <boxGeometry args={[0.06, 1.6, 0.06]} />
        </mesh>
        <Lamp position={[-1.75, 2.5, -1.35]} height={0.55} />
        {/* plants */}
        <group position={[-1.35, 0, -0.75]}>
          <mesh material={mcLeaves} position={[0, 0.22, 0]}>
            <boxGeometry args={[0.34, 0.44, 0.34]} />
          </mesh>
          <mesh material={mcLeaves} position={[0.2, 0.5, 0.08]}>
            <boxGeometry args={[0.2, 0.3, 0.2]} />
          </mesh>
        </group>
        <mesh material={mcLeaves} position={[-0.7, 0.18, -2.1]}>
          <boxGeometry args={[0.3, 0.36, 0.3]} />
        </mesh>
      </group>

      {/* simple platform steps toward the bridge side */}
      <mesh material={graphiteDark} position={[2.1, -0.12, 1.6]} rotation={[0, -0.7, 0]}>
        <boxGeometry args={[1.1, 0.18, 0.5]} />
      </mesh>
      <mesh material={graphiteDark} position={[2.45, -0.3, 2.0]} rotation={[0, -0.7, 0]}>
        <boxGeometry args={[1.1, 0.18, 0.5]} />
      </mesh>

      <Lamp position={[-0.6, 0, 2.4]} />
      <Lamp position={[2.4, 0, -0.8]} />
      <Lamp position={[2.65, 0, 1.4]} height={0.7} />
      <mesh material={mcLeaves} position={[1.6, 0.16, 2.35]}>
        <boxGeometry args={[0.26, 0.32, 0.26]} />
      </mesh>
    </group>
  );
}
