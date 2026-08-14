import { IslandBase } from "./IslandBase";
import { Sign } from "./Sign";
import { Screen } from "./Screen";
import { Lamp } from "./Lamp";
import {
  graphite,
  graphiteDark,
  mcLeaves,
  neonCyan,
  neonCyanFaint,
  screenBlue,
} from "./materials";
import { islandLayout } from "./layout";

const CARD_COUNT = 5;
const CARD_W = 0.68;
const CARD_GAP = 0.16;

/** Experiences island: card wall + timeline with circular nodes. */
export function ExperiencesIsland() {
  const { position, radius } = islandLayout.experiences;
  const wallW = CARD_COUNT * (CARD_W + CARD_GAP) + 0.5;

  return (
    <group name="experiencesIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[[0.2, 1.3]]}
      />

      {/* wall + cards + timeline, angled toward the camera */}
      <group position={[0.2, 0, -1.7]} rotation={[0, 0.35, 0]}>
        {/* raised apron platform under the wall */}
        <mesh material={graphite} position={[0, 0.13, 0.45]}>
          <boxGeometry args={[wallW + 0.7, 0.26, 1.7]} />
        </mesh>
        <mesh material={neonCyanFaint} position={[0, 0.27, 1.28]}>
          <boxGeometry args={[wallW + 0.6, 0.03, 0.06]} />
        </mesh>
        {/* back wall panel with side columns and top cap */}
        <mesh material={graphiteDark} position={[0, 1.5, 0]}>
          <boxGeometry args={[wallW, 2.1, 0.16]} />
        </mesh>
        {[wallW / 2 + 0.14, -wallW / 2 - 0.14].map((x) => (
          <mesh key={x} material={graphite} position={[x, 1.35, 0]}>
            <boxGeometry args={[0.26, 2.5, 0.3]} />
          </mesh>
        ))}
        <mesh material={graphite} position={[0, 2.62, 0]}>
          <boxGeometry args={[wallW + 0.55, 0.16, 0.32]} />
        </mesh>

        {/* sign mounted on top of the wall */}
        <Sign
          text="EXPERIENCES"
          width={3.2}
          position={[0, 3.0, 0.02]}
          postHeight={0.7}
        />

        {/* 4–5 simplified cards */}
        {Array.from({ length: CARD_COUNT }, (_, i) => {
          const x =
            -((CARD_COUNT - 1) * (CARD_W + CARD_GAP)) / 2 +
            i * (CARD_W + CARD_GAP);
          return (
            <Screen
              key={i}
              variant="card"
              width={CARD_W}
              height={1.05}
              position={[x, 1.75, 0.12]}
              frame={false}
            />
          );
        })}

        {/* timeline line with circular nodes */}
        <mesh material={neonCyan} position={[0, 0.62, 0.14]}>
          <boxGeometry args={[wallW - 0.5, 0.05, 0.05]} />
        </mesh>
        {Array.from({ length: CARD_COUNT }, (_, i) => {
          const x =
            -((CARD_COUNT - 1) * (CARD_W + CARD_GAP)) / 2 +
            i * (CARD_W + CARD_GAP);
          return (
            <mesh
              key={i}
              material={neonCyan}
              position={[x, 0.62, 0.16]}
              rotation={[0, 0, 0]}
            >
              <torusGeometry args={[0.09, 0.03, 5, 10]} />
            </mesh>
          );
        })}
        {/* uplights washing the wall */}
        {[-1.5, 0, 1.5].map((x) => (
          <mesh key={x} material={screenBlue} position={[x, 0.3, 0.3]}>
            <boxGeometry args={[0.2, 0.07, 0.12]} />
          </mesh>
        ))}
        {/* planters at the wall ends */}
        {[wallW / 2 + 0.55, -wallW / 2 - 0.55].map((x) => (
          <group key={x} position={[x, 0.26, 0.3]}>
            <mesh material={graphiteDark} position={[0, 0.18, 0]}>
              <boxGeometry args={[0.46, 0.36, 0.46]} />
            </mesh>
            <mesh material={mcLeaves} position={[0, 0.52, 0]}>
              <boxGeometry args={[0.32, 0.32, 0.32]} />
            </mesh>
          </group>
        ))}
      </group>

      {/* presenter podium facing the wall */}
      <group position={[-1.3, 0, 1.0]} rotation={[0, 2.6, 0]}>
        <mesh material={graphiteDark} position={[0, 0.3, 0]}>
          <boxGeometry args={[0.55, 0.6, 0.42]} />
        </mesh>
        <mesh material={screenBlue} position={[0, 0.64, -0.06]} rotation={[-0.5, 0, 0]}>
          <boxGeometry args={[0.45, 0.28, 0.04]} />
        </mesh>
      </group>

      {/* floor chevrons from the bridge landing toward the wall */}
      {[0, 1, 2].map((i) => (
        <mesh
          key={i}
          material={neonCyanFaint}
          position={[-3.0 + i * 0.65, 0.012, 1.55 - i * 0.4]}
          rotation={[0, 0.55, 0]}
        >
          <boxGeometry args={[0.5, 0.02, 0.08]} />
        </mesh>
      ))}

      {/* small console table */}
      <group position={[1.4, 0, 1.1]} rotation={[0, -0.5, 0]}>
        <mesh material={graphiteDark} position={[0, 0.4, 0]}>
          <boxGeometry args={[1.0, 0.14, 0.55]} />
        </mesh>
        <mesh material={graphiteDark} position={[0, 0.16, 0]}>
          <boxGeometry args={[0.5, 0.34, 0.4]} />
        </mesh>
        <mesh
          material={screenBlue}
          position={[0, 0.58, -0.05]}
          rotation={[-0.55, 0, 0]}
        >
          <boxGeometry args={[0.7, 0.3, 0.04]} />
        </mesh>
      </group>

      <Lamp position={[-2.4, 0, 0.6]} />
      <Lamp position={[2.9, 0, -0.6]} />
    </group>
  );
}
