import { IslandBase } from "./IslandBase";
import { Tier } from "./Tier";
import { Sign } from "./Sign";
import { Screen } from "./Screen";
import { Lamp } from "./Lamp";
import {
  crateOrange,
  graphite,
  graphiteDark,
  neonCyanFaint,
  paperWhite,
  purpleGlow,
} from "./materials";
import { islandLayout } from "./layout";

/** Lattice communication tower: angled corner legs, braced tiers, mast, beacon. */
function Antenna({ position }: { position: [number, number, number] }) {
  const legOffsets: [number, number][] = [
    [0.3, 0.3],
    [-0.3, 0.3],
    [0.3, -0.3],
    [-0.3, -0.3],
  ];
  return (
    <group position={position}>
      {/* base slab */}
      <mesh material={graphiteDark} position={[0, 0.1, 0]}>
        <boxGeometry args={[0.95, 0.2, 0.95]} />
      </mesh>
      {/* lower angled legs */}
      {legOffsets.map(([dx, dz], i) => (
        <mesh
          key={i}
          material={graphite}
          position={[dx * 0.75, 0.75, dz * 0.75]}
          rotation={[dz * 0.42, 0, -dx * 0.42]}
        >
          <boxGeometry args={[0.09, 1.25, 0.09]} />
        </mesh>
      ))}
      {/* mid platform + horizontal frame */}
      <mesh material={graphiteDark} position={[0, 1.35, 0]}>
        <boxGeometry args={[0.6, 0.14, 0.6]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, 0.75, 0]} rotation={[0, Math.PI / 4, 0]}>
        <boxGeometry args={[0.72, 0.05, 0.05]} />
      </mesh>
      {/* upper angled legs */}
      {legOffsets.map(([dx, dz], i) => (
        <mesh
          key={`u${i}`}
          material={graphite}
          position={[dx * 0.42, 1.85, dz * 0.42]}
          rotation={[dz * 0.3, 0, -dx * 0.3]}
        >
          <boxGeometry args={[0.07, 0.95, 0.07]} />
        </mesh>
      ))}
      <mesh material={graphiteDark} position={[0, 2.3, 0]}>
        <boxGeometry args={[0.34, 0.1, 0.34]} />
      </mesh>
      {/* mast + dish bar + beacon */}
      <mesh material={graphite} position={[0, 2.75, 0]}>
        <cylinderGeometry args={[0.035, 0.06, 0.85, 4]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, 2.6, 0]} rotation={[0, 0.6, 0]}>
        <boxGeometry args={[0.5, 0.04, 0.04]} />
      </mesh>
      <mesh material={purpleGlow} position={[0, 3.25, 0]}>
        <sphereGeometry args={[0.14, 8, 6]} />
      </mesh>
      {/* signal rings around the beacon */}
      <mesh material={purpleGlow} position={[0, 3.25, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.26, 0.015, 3, 12]} />
      </mesh>
      <mesh material={purpleGlow} position={[0, 3.25, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.38, 0.012, 3, 12]} />
      </mesh>
      {/* small side dish */}
      <mesh material={graphite} position={[0.2, 2.05, 0.14]} rotation={[0.9, 0, 0.4]}>
        <cylinderGeometry args={[0.17, 0.12, 0.06, 8]} />
      </mesh>
    </group>
  );
}

/** Contact island: envelope terminal, second screen, antenna tower. */
export function ContactIsland() {
  const { position, radius } = islandLayout.contact;
  return (
    <group name="contactIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[[5.6, 6.6]]}
      />

      {/* raised terminal tier */}
      <Tier
        radius={1.5}
        height={0.26}
        position={[-0.3, 0, 0.35]}
        step={Math.PI / 1.6}
      />

      <Sign
        text="CONTACT"
        width={2.2}
        position={[0.9, 2.35, -1.0]}
        rotation={[0, 0.35, 0]}
        postHeight={1.75}
      />

      {/* terminal desk with envelope screen */}
      <group position={[-0.5, 0.26, 0.4]} rotation={[0, 0.55, 0]}>
        <mesh material={graphiteDark} position={[0, 0.42, 0]}>
          <boxGeometry args={[1.25, 0.16, 0.7]} />
        </mesh>
        <mesh material={graphiteDark} position={[0, 0.17, 0]}>
          <boxGeometry args={[0.9, 0.34, 0.5]} />
        </mesh>
        <Screen
          variant="envelope"
          width={0.95}
          height={0.65}
          position={[0, 0.88, -0.15]}
          rotation={[-0.15, 0, 0]}
        />
        {/* stack of letters on the desk */}
        {[0, 1, 2].map((i) => (
          <mesh
            key={i}
            material={paperWhite}
            position={[0.42, 0.53 + i * 0.035, 0.18]}
            rotation={[0, 0.3 * i - 0.2, 0]}
          >
            <boxGeometry args={[0.28, 0.03, 0.2]} />
          </mesh>
        ))}
      </group>

      {/* cable from the tower down to the terminal */}
      <mesh
        material={graphiteDark}
        position={[-1.0, 0.95, -0.35]}
        rotation={[0.24, 0.59, 0]}
      >
        <boxGeometry args={[0.035, 0.035, 2.0]} />
      </mesh>

      {/* blocky mailbox on a post */}
      <group position={[1.5, 0, 1.35]} rotation={[0, -0.5, 0]}>
        <mesh material={graphiteDark} position={[0, 0.32, 0]}>
          <boxGeometry args={[0.09, 0.64, 0.09]} />
        </mesh>
        <mesh material={graphite} position={[0, 0.75, 0]}>
          <boxGeometry args={[0.44, 0.3, 0.3]} />
        </mesh>
        <mesh material={neonCyanFaint} position={[0, 0.78, 0.16]}>
          <boxGeometry args={[0.28, 0.05, 0.02]} />
        </mesh>
        <mesh material={crateOrange} position={[0.24, 0.95, 0]}>
          <boxGeometry args={[0.04, 0.2, 0.04]} />
        </mesh>
      </group>

      {/* second, larger envelope screen */}
      <Screen
        variant="envelope"
        width={1.35}
        height={0.95}
        position={[0.8, 1.15, 0.9]}
        rotation={[0, 0.55, 0]}
        stand
      />

      {/* antenna / communication tower */}
      <Antenna position={[-1.5, 0, -1.1]} />

      <Lamp position={[-1.8, 0, -0.6]} />
      <Lamp position={[1.9, 0, 0.2]} />
    </group>
  );
}
