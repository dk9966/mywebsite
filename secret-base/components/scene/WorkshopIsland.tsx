import { IslandBase } from "./IslandBase";
import { Sign } from "./Sign";
import { Lamp } from "./Lamp";
import {
  crateOrange,
  graphite,
  graphiteDark,
  lampWarm,
  neonCyanFaint,
  screenBlue,
} from "./materials";
import { islandLayout } from "./layout";

/** Simple two-segment robot arm on a round base. */
function RobotArm({
  position,
  rotation = [0, 0, 0],
}: {
  position: [number, number, number];
  rotation?: [number, number, number];
}) {
  return (
    <group position={position} rotation={rotation}>
      <mesh material={graphiteDark} position={[0, 0.14, 0]}>
        <cylinderGeometry args={[0.34, 0.42, 0.28, 8]} />
      </mesh>
      {/* upper arm */}
      <group position={[0, 0.28, 0]} rotation={[0, 0, -0.55]}>
        <mesh material={graphite} position={[0, 0.55, 0]}>
          <boxGeometry args={[0.18, 1.1, 0.18]} />
        </mesh>
        {/* elbow + forearm */}
        <group position={[0, 1.1, 0]} rotation={[0, 0, 1.75]}>
          <mesh material={graphiteDark}>
            <sphereGeometry args={[0.13, 6, 5]} />
          </mesh>
          <mesh material={graphite} position={[0, 0.45, 0]}>
            <boxGeometry args={[0.15, 0.9, 0.15]} />
          </mesh>
          {/* claw */}
          <mesh material={graphiteDark} position={[-0.06, 0.95, 0]}>
            <boxGeometry args={[0.06, 0.22, 0.1]} />
          </mesh>
          <mesh material={graphiteDark} position={[0.06, 0.95, 0]}>
            <boxGeometry args={[0.06, 0.22, 0.1]} />
          </mesh>
        </group>
      </group>
    </group>
  );
}

/** Workshop island: workbench, robot arm, crates, warm lighting. */
export function WorkshopIsland() {
  const { position, radius } = islandLayout.workshop;
  return (
    <group name="workshopIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[[2.4, 3.6]]}
      />

      {/* work-area floor plate */}
      <mesh material={graphiteDark} position={[-0.4, 0.045, 0.2]}>
        <boxGeometry args={[3.4, 0.09, 2.3]} />
      </mesh>
      <mesh material={neonCyanFaint} position={[-0.4, 0.095, 0.2]}>
        <boxGeometry args={[3.44, 0.02, 0.06]} />
      </mesh>

      {/* tall cabinet machine */}
      <group position={[1.9, 0, -1.2]} rotation={[0, -0.3, 0]}>
        <mesh material={graphiteDark} position={[0, 0.65, 0]}>
          <boxGeometry args={[0.75, 1.3, 0.65]} />
        </mesh>
        <mesh material={graphite} position={[0, 1.5, 0]}>
          <boxGeometry args={[0.62, 0.42, 0.55]} />
        </mesh>
        <mesh material={screenBlue} position={[0, 0.95, 0.34]}>
          <boxGeometry args={[0.4, 0.3, 0.04]} />
        </mesh>
        <mesh material={lampWarm} position={[0, 1.5, 0.29]}>
          <boxGeometry args={[0.12, 0.12, 0.05]} />
        </mesh>
      </group>

      <Sign
        text="WORKSHOP"
        width={2.7}
        position={[-0.7, 2.3, -1.7]}
        rotation={[0, 0.55, 0]}
        postHeight={1.6}
      />

      {/* workbench */}
      <group position={[-1.0, 0, 0.5]} rotation={[0, 0.3, 0]}>
        <mesh material={graphiteDark} position={[0, 0.78, 0]}>
          <boxGeometry args={[1.9, 0.14, 0.95]} />
        </mesh>
        {[
          [-0.82, -0.38],
          [0.82, -0.38],
          [-0.82, 0.38],
          [0.82, 0.38],
        ].map(([x, z], i) => (
          <mesh key={i} material={graphite} position={[x, 0.36, z]}>
            <boxGeometry args={[0.1, 0.72, 0.1]} />
          </mesh>
        ))}
        {/* tool blocks on the bench */}
        <mesh material={graphite} position={[-0.5, 0.95, 0.1]}>
          <boxGeometry args={[0.3, 0.2, 0.24]} />
        </mesh>
        <mesh material={crateOrange} position={[0.1, 0.92, -0.2]}>
          <boxGeometry args={[0.22, 0.14, 0.2]} />
        </mesh>
        <mesh
          material={screenBlue}
          position={[0.65, 0.97, 0]}
          rotation={[-0.5, -0.4, 0]}
        >
          <boxGeometry args={[0.4, 0.26, 0.03]} />
        </mesh>
        {/* overhead gantry with hanging work light */}
        {[-1.15, 1.15].map((x) => (
          <mesh key={x} material={graphiteDark} position={[x, 0.95, -0.35]}>
            <boxGeometry args={[0.13, 1.9, 0.13]} />
          </mesh>
        ))}
        <mesh material={graphiteDark} position={[0, 1.92, -0.35]}>
          <boxGeometry args={[2.5, 0.12, 0.14]} />
        </mesh>
        <mesh material={graphite} position={[0, 1.72, -0.35]}>
          <boxGeometry args={[0.04, 0.3, 0.04]} />
        </mesh>
        <mesh material={lampWarm} position={[0, 1.52, -0.35]}>
          <boxGeometry args={[0.18, 0.12, 0.18]} />
        </mesh>
        {/* tool board hung on the gantry */}
        <mesh material={graphiteDark} position={[0, 1.3, -0.44]}>
          <boxGeometry args={[1.7, 0.65, 0.07]} />
        </mesh>
        {[
          [-0.6, 1.32],
          [-0.3, 1.22],
          [0.05, 1.38],
          [0.35, 1.25],
          [0.65, 1.35],
        ].map(([x, y], i) => (
          <mesh
            key={i}
            material={i % 2 === 0 ? graphite : crateOrange}
            position={[x, y, -0.39]}
          >
            <boxGeometry args={[0.1, 0.18, 0.05]} />
          </mesh>
        ))}
      </group>

      {/* barrels */}
      <mesh material={graphite} position={[0.4, 0.29, 2.0]}>
        <cylinderGeometry args={[0.24, 0.24, 0.58, 8]} />
      </mesh>
      <mesh material={crateOrange} position={[-2.5, 0.26, 1.1]}>
        <cylinderGeometry args={[0.22, 0.22, 0.52, 8]} />
      </mesh>

      {/* floor pipe run from the cabinet toward the bench */}
      <mesh material={graphiteDark} position={[0.6, 0.13, -0.85]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.06, 0.06, 1.7, 6]} />
      </mesh>
      <mesh material={graphiteDark} position={[-0.28, 0.13, -0.85]}>
        <boxGeometry args={[0.16, 0.16, 0.16]} />
      </mesh>
      <mesh material={graphiteDark} position={[-0.28, 0.13, -0.35]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 0.9, 6]} />
      </mesh>

      {/* robot arm reaching over the bench */}
      <RobotArm position={[0.9, 0, -0.4]} rotation={[0, 2.4, 0]} />

      {/* crates */}
      <mesh material={crateOrange} position={[1.9, 0.26, 1.1]} rotation={[0, 0.4, 0]}>
        <boxGeometry args={[0.52, 0.52, 0.52]} />
      </mesh>
      <mesh material={graphiteDark} position={[2.45, 0.21, 0.55]} rotation={[0, -0.2, 0]}>
        <boxGeometry args={[0.42, 0.42, 0.42]} />
      </mesh>
      <mesh material={graphite} position={[1.75, 0.7, 1.25]} rotation={[0, -0.3, 0]}>
        <boxGeometry args={[0.34, 0.34, 0.34]} />
      </mesh>

      {/* warm practical lighting */}
      <Lamp position={[-2.4, 0, -0.9]} />
      <Lamp position={[0.4, 0, 1.9]} height={1.1} />
    </group>
  );
}
