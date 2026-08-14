import type { ReactNode } from "react";
import type * as THREE from "three";
import { IslandBase } from "./IslandBase";
import { Tier } from "./Tier";
import { Sign } from "./Sign";
import { Screen } from "./Screen";
import { Lamp } from "./Lamp";
import { HoloPanel } from "./HoloPanel";
import {
  crateOrange,
  graphite,
  graphiteDark,
  lampWarm,
  mcLeaves,
  neonCyan,
  neonCyanFaint,
  neonMagenta,
  purpleGlow,
  screenBlue,
} from "./materials";
import { islandLayout } from "./layout";

const SPOKE_ANGLES = [0.4, 1.2, 2.0, 2.75, 3.55, 4.3, 5.1, 5.9];

const WALL_CENTER = Math.PI / 2; // back of the island (-z)
// rows: [centerY, height, radius, halfArc, depth]
const WALL_ROWS: [number, number, number, number, number][] = [
  [0.55, 1.1, 4.75, 0.85, 0.55],
  [1.62, 1.05, 4.6, 0.85, 0.55],
  [2.66, 1.0, 4.45, 0.8, 0.5],
  [3.66, 1.0, 4.15, 0.7, 0.5],
  [4.55, 0.85, 3.7, 0.55, 0.45],
  [5.2, 0.5, 3.3, 0.42, 0.4],
];

/** Giant blocky arch wall with purple/cyan light bars, doors and an alcove. */
function ArchWall() {
  const blocks: ReactNode[] = [];
  WALL_ROWS.forEach(([cy, h, r, halfArc, depth], row) => {
    const arcLen = 2 * halfArc * r;
    const count = Math.max(3, Math.round(arcLen / 0.85));
    for (let i = 0; i < count; i++) {
      const t = WALL_CENTER - halfArc + ((i + 0.5) / count) * halfArc * 2;
      const w = (arcLen / count) * 0.93;
      const hh = h * (1 + (((i + row) * 31) % 3) * 0.06 - 0.06);
      blocks.push(
        <mesh
          key={`${row}-${i}`}
          material={(i + row) % 4 === 0 ? graphite : graphiteDark}
          position={[r * Math.cos(t), cy, -r * Math.sin(t)]}
          rotation={[0, t + Math.PI / 2, 0]}
        >
          <boxGeometry args={[w, hh, depth]} />
        </mesh>,
      );
    }
  });

  // vertical neon bars (purple / cyan / magenta, like the reference)
  const vBars: [number, number, number, THREE.Material][] = [
    // [rowIdx, angle offset, barHeight, material]
    [0, -0.66, 0.8, purpleGlow],
    [0, 0.66, 0.8, neonCyan],
    [1, -0.36, 0.85, neonCyan],
    [1, 0.36, 0.85, purpleGlow],
    [2, -0.68, 0.75, neonMagenta],
    [2, 0.68, 0.75, purpleGlow],
    [3, -0.5, 0.75, purpleGlow],
    [3, 0.5, 0.75, neonMagenta],
    [4, -0.28, 0.6, neonCyan],
    [4, 0.28, 0.6, purpleGlow],
  ];
  // horizontal accent bars
  const hBars: [number, number, number, THREE.Material][] = [
    [4, 0, 1.1, neonMagenta],
    [2, 0.45, 0.7, neonCyan],
    [2, -0.45, 0.7, neonMagenta],
  ];

  const bar = (
    [row, dt, len, mat]: [number, number, number, THREE.Material],
    vertical: boolean,
    key: string,
  ) => {
    const [cy, , r, , depth] = WALL_ROWS[row];
    const t = WALL_CENTER + dt;
    const rr = r - depth / 2 - 0.045;
    return (
      <mesh
        key={key}
        material={mat}
        position={[rr * Math.cos(t), cy, -rr * Math.sin(t)]}
        rotation={[0, t + Math.PI / 2, 0]}
      >
        <boxGeometry
          args={vertical ? [0.1, len, 0.07] : [len, 0.12, 0.07]}
        />
      </mesh>
    );
  };

  // door panels flanking the central alcove
  const doors = [-0.55, 0.55].map((dt, i) => {
    const t = WALL_CENTER + dt;
    const rr = 4.38;
    return (
      <group key={i}>
        <mesh
          material={graphiteDark}
          position={[rr * Math.cos(t), 1.1, -rr * Math.sin(t)]}
          rotation={[0, t + Math.PI / 2, 0]}
        >
          <boxGeometry args={[1.0, 2.1, 0.14]} />
        </mesh>
        <mesh
          material={i === 0 ? purpleGlow : neonCyan}
          position={[rr * Math.cos(t), 2.32, -rr * Math.sin(t)]}
          rotation={[0, t + Math.PI / 2, 0]}
        >
          <boxGeometry args={[0.5, 0.08, 0.08]} />
        </mesh>
      </group>
    );
  });

  return (
    <group name="archWall">
      {blocks}
      {vBars.map((b, i) => bar(b, true, `v${i}`))}
      {hBars.map((b, i) => bar(b, false, `h${i}`))}
      {doors}
    </group>
  );
}

/** Workbench alcove set into the middle of the wall (tool board + shelves). */
function Alcove() {
  return (
    <group name="alcove" position={[0, 0, -3.75]}>
      {/* bench */}
      <mesh material={graphiteDark} position={[0, 0.78, 0]}>
        <boxGeometry args={[2.3, 0.14, 0.8]} />
      </mesh>
      {[-1.0, 1.0].map((x) => (
        <mesh key={x} material={graphite} position={[x, 0.36, 0]}>
          <boxGeometry args={[0.12, 0.72, 0.65]} />
        </mesh>
      ))}
      {/* gadgets on the bench */}
      <mesh material={graphite} position={[-0.6, 0.95, 0]}>
        <boxGeometry args={[0.4, 0.2, 0.3]} />
      </mesh>
      <mesh material={screenBlue} position={[0.15, 0.98, 0.05]} rotation={[-0.4, 0, 0]}>
        <boxGeometry args={[0.35, 0.25, 0.04]} />
      </mesh>
      <mesh material={crateOrange} position={[0.75, 0.94, -0.1]}>
        <boxGeometry args={[0.26, 0.18, 0.22]} />
      </mesh>
      {/* pegboard tool wall */}
      <mesh material={graphiteDark} position={[0, 1.85, -0.42]}>
        <boxGeometry args={[2.3, 1.15, 0.1]} />
      </mesh>
      {[-0.85, -0.5, -0.15, 0.2, 0.55, 0.9].map((x, i) => (
        <mesh
          key={i}
          material={i % 2 === 0 ? graphite : crateOrange}
          position={[x, 1.82 + (i % 3) * 0.08, -0.34]}
        >
          <boxGeometry args={[0.09, 0.34, 0.06]} />
        </mesh>
      ))}
      {/* strip light over the board */}
      <mesh material={neonCyan} position={[0, 2.5, -0.36]}>
        <boxGeometry args={[1.5, 0.07, 0.07]} />
      </mesh>
      {/* shelf above with boxes + plant */}
      <mesh material={graphite} position={[0, 2.95, -0.35]}>
        <boxGeometry args={[2.1, 0.08, 0.5]} />
      </mesh>
      <mesh material={graphiteDark} position={[-0.7, 3.15, -0.35]}>
        <boxGeometry args={[0.4, 0.32, 0.34]} />
      </mesh>
      <mesh material={crateOrange} position={[-0.15, 3.12, -0.35]}>
        <boxGeometry args={[0.3, 0.26, 0.3]} />
      </mesh>
      <group position={[0.7, 3.0, -0.35]}>
        <mesh material={graphiteDark} position={[0, 0.1, 0]}>
          <cylinderGeometry args={[0.09, 0.11, 0.18, 6]} />
        </mesh>
        <mesh material={mcLeaves} position={[0, 0.3, 0]}>
          <boxGeometry args={[0.2, 0.2, 0.2]} />
        </mesh>
      </group>
    </group>
  );
}

/** Desk workstation: dual monitors, keyboard, lamp, plant, purple crystal. */
function Workstation({
  position,
  rotation,
}: {
  position: [number, number, number];
  rotation: [number, number, number];
}) {
  return (
    <group position={position} rotation={rotation}>
      {/* desk + drawer block */}
      <mesh material={graphiteDark} position={[0, 0.42, 0]}>
        <boxGeometry args={[2.1, 0.14, 0.85]} />
      </mesh>
      <mesh material={graphite} position={[-0.85, 0.2, 0]}>
        <boxGeometry args={[0.3, 0.4, 0.7]} />
      </mesh>
      <mesh material={graphite} position={[0.85, 0.2, 0]}>
        <boxGeometry args={[0.3, 0.4, 0.7]} />
      </mesh>
      {/* dual monitors */}
      <Screen variant="ui" width={1.15} height={0.75} position={[-0.42, 1.0, -0.15]} rotation={[0, 0.12, 0]} stand />
      <Screen variant="ui" width={0.85} height={0.6} position={[0.62, 0.92, -0.12]} rotation={[0, -0.18, 0]} stand />
      {/* keyboard + mouse */}
      <mesh material={graphite} position={[-0.2, 0.52, 0.22]}>
        <boxGeometry args={[0.6, 0.04, 0.2]} />
      </mesh>
      <mesh material={graphite} position={[0.35, 0.52, 0.24]}>
        <boxGeometry args={[0.09, 0.04, 0.13]} />
      </mesh>
      {/* desk lamp */}
      <group position={[0.95, 0.49, -0.28]}>
        <mesh material={graphiteDark} position={[0, 0.03, 0]}>
          <cylinderGeometry args={[0.09, 0.11, 0.06, 6]} />
        </mesh>
        <mesh material={graphiteDark} position={[0.02, 0.22, 0]} rotation={[0, 0, -0.4]}>
          <boxGeometry args={[0.05, 0.4, 0.05]} />
        </mesh>
        <mesh material={lampWarm} position={[0.15, 0.4, 0]}>
          <boxGeometry args={[0.14, 0.09, 0.11]} />
        </mesh>
      </group>
      {/* plant + purple crystal */}
      <group position={[-0.95, 0.49, 0.22]}>
        <mesh material={graphiteDark} position={[0, 0.06, 0]}>
          <cylinderGeometry args={[0.08, 0.1, 0.12, 6]} />
        </mesh>
        <mesh material={mcLeaves} position={[0, 0.22, 0]}>
          <boxGeometry args={[0.18, 0.18, 0.18]} />
        </mesh>
      </group>
      <mesh material={purpleGlow} position={[0.15, 0.62, -0.28]} rotation={[0.2, 0.5, 0]}>
        <octahedronGeometry args={[0.12, 0]} />
      </mesh>
    </group>
  );
}

/** Rim pylon with a glowing cube (cyan/purple alternating). */
function Pylon({
  position,
  purple = false,
}: {
  position: [number, number, number];
  purple?: boolean;
}) {
  return (
    <group position={position}>
      <mesh material={graphiteDark} position={[0, 0.28, 0]}>
        <boxGeometry args={[0.16, 0.56, 0.16]} />
      </mesh>
      <mesh material={purple ? purpleGlow : neonCyan} position={[0, 0.66, 0]}>
        <boxGeometry args={[0.2, 0.2, 0.2]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, 0.8, 0]}>
        <boxGeometry args={[0.22, 0.05, 0.22]} />
      </mesh>
    </group>
  );
}

const PYLON_ANGLES = [0.15, 0.95, 1.75, 2.85, 4.05, 4.75, 5.65];
const PEDESTAL_BARS = 8;

/** Central hub: arch wall, projector pedestal, resume holo panel. */
export function ProjectsIsland() {
  const { position, radius } = islandLayout.projects;
  return (
    <group name="projectsIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[
          [0.55, 1.15],
          [1.95, 2.55],
          [3.5, 4.1],
          [5.2, 5.8],
        ]}
      />

      {/* raised inner tier */}
      <Tier radius={3.3} height={0.26} position={[0, 0, 0]} step={-Math.PI / 2} />

      {/* concentric deck seam rings */}
      {[2.95, 4.35].map((r) => (
        <mesh
          key={r}
          material={graphiteDark}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.006, 0]}
        >
          <torusGeometry args={[r, 0.03, 3, 40]} />
        </mesh>
      ))}
      {/* dashed neon arc rings (cyan + magenta, multiple radii) */}
      {Array.from({ length: 8 }, (_, i) => (
        <mesh
          key={`a${i}`}
          material={neonCyan}
          rotation={[-Math.PI / 2, 0, (i * Math.PI) / 4 + 0.14]}
          position={[0, 0.012, 0]}
        >
          <torusGeometry args={[3.9, 0.035, 3, 8, 0.5]} />
        </mesh>
      ))}
      {Array.from({ length: 6 }, (_, i) => (
        <mesh
          key={`b${i}`}
          material={neonMagenta}
          rotation={[-Math.PI / 2, 0, (i * Math.PI) / 3 + 0.4]}
          position={[0, 0.012, 0]}
        >
          <torusGeometry args={[3.35, 0.03, 3, 7, 0.38]} />
        </mesh>
      ))}
      {Array.from({ length: 8 }, (_, i) => (
        <mesh
          key={`c${i}`}
          material={i % 2 === 0 ? neonCyanFaint : neonMagenta}
          rotation={[-Math.PI / 2, 0, (i * Math.PI) / 4 - 0.1]}
          position={[0, 0.012, 0]}
        >
          <torusGeometry args={[4.6, 0.03, 3, 6, 0.3]} />
        </mesh>
      ))}

      {/* faint radial spokes */}
      {SPOKE_ANGLES.map((t, i) => (
        <group key={i} rotation={[0, t, 0]}>
          <mesh material={neonCyanFaint} position={[4.25, 0.012, 0]}>
            <boxGeometry args={[1.5, 0.02, 0.06]} />
          </mesh>
        </group>
      ))}

      {/* glowing rim pylons */}
      {PYLON_ANGLES.map((t, i) => (
        <Pylon
          key={i}
          purple={i % 2 === 1}
          position={[4.95 * Math.cos(t), 0, -4.95 * Math.sin(t)]}
        />
      ))}

      {/* arch wall + central alcove */}
      <ArchWall />
      <Alcove />

      {/* PROJECTS sign on the crown of the arch */}
      <Sign
        text="PROJECTS"
        width={2.7}
        position={[0, 5.35, -2.9]}
        rotation={[0, 0.12, 0]}
        posts={false}
      />

      {/* low round projector pedestal with glowing bar segments */}
      <mesh material={graphiteDark} position={[0, 0.5, 0]}>
        <cylinderGeometry args={[1.9, 2.05, 0.48, 18]} />
      </mesh>
      <mesh material={graphite} position={[0, 0.92, 0]}>
        <cylinderGeometry args={[1.45, 1.6, 0.4, 18]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, 1.24, 0]}>
        <cylinderGeometry args={[0.95, 1.1, 0.28, 18]} />
      </mesh>
      {Array.from({ length: PEDESTAL_BARS }, (_, i) => {
        const a = (i / PEDESTAL_BARS) * Math.PI * 2 + 0.25;
        const low = i % 2 === 0;
        const r = low ? 1.99 : 1.54;
        const y = low ? 0.55 : 0.95;
        return (
          <mesh
            key={i}
            material={i % 4 === 1 ? neonMagenta : neonCyan}
            position={[r * Math.cos(a), y, -r * Math.sin(a)]}
            rotation={[0, a + Math.PI / 2, 0]}
          >
            <boxGeometry args={[0.55, 0.14, 0.05]} />
          </mesh>
        );
      })}

      {/* projector lens + light beam up to the panel */}
      <mesh material={neonCyan} position={[0, 1.42, 0]}>
        <cylinderGeometry args={[0.55, 0.62, 0.08, 18]} />
      </mesh>
      <mesh position={[0, 2.2, 0]}>
        <cylinderGeometry args={[2.4, 0.45, 1.6, 24, 1, true]} />
        <meshBasicMaterial
          color="#3b82ff"
          transparent
          opacity={0.1}
          side={2}
          depthWrite={false}
        />
      </mesh>
      {/* flat holo rings hovering over the lens */}
      <mesh material={neonCyanFaint} rotation={[-Math.PI / 2, 0, 0]} position={[0, 1.62, 0]}>
        <torusGeometry args={[0.8, 0.025, 3, 24]} />
      </mesh>
      <mesh material={neonCyanFaint} rotation={[-Math.PI / 2, 0, 0]} position={[0, 1.8, 0]}>
        <torusGeometry args={[0.6, 0.02, 3, 20]} />
      </mesh>

      {/* the FEATURED PROJECTS hologram (content from src/data/resume.ts) */}
      <HoloPanel position={[0, 3.15, 0.25]} rotation={[0, 0.14, 0]} width={5.6} />

      {/* desk workstations flanking the pedestal */}
      <Workstation position={[-3.4, 0, -1.2]} rotation={[0, 1.0, 0]} />
      <Workstation position={[3.4, 0, -1.2]} rotation={[0, -1.0, 0]} />

      {/* supply crates near the rim */}
      <group position={[-3.9, 0, 1.8]} rotation={[0, 0.4, 0]}>
        <mesh material={crateOrange} position={[0, 0.26, 0]}>
          <boxGeometry args={[0.52, 0.52, 0.52]} />
        </mesh>
        <mesh material={graphiteDark} position={[0.55, 0.21, 0.15]}>
          <boxGeometry args={[0.42, 0.42, 0.42]} />
        </mesh>
        <mesh material={graphite} position={[0.15, 0.68, 0.05]}>
          <boxGeometry args={[0.32, 0.32, 0.32]} />
        </mesh>
      </group>

      {/* warm lamps for contrast */}
      <Lamp position={[-2.6, 0, 3.6]} />
      <Lamp position={[2.4, 0, 3.6]} />
      <Lamp position={[4.35, 0, -0.9]} />
    </group>
  );
}
