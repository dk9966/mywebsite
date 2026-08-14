import { IslandBase } from "./IslandBase";
import { Lamp, Bollard } from "./Lamp";
import {
  graphite,
  graphiteDark,
  neonCyanFaint,
  paperWhite,
  screenBlue,
} from "./materials";
import { islandLayout } from "./layout";

/**
 * Foreground entrance island: a vehicle platform in the same style as the
 * other islands — painted parking bays and a charging post, no cars yet.
 */
export function GarageIsland() {
  const { position, radius } = islandLayout.garage;
  return (
    <group name="garageIsland" position={position}>
      <IslandBase
        radius={radius}
        depth={position[1] + 26}
        railArcs={[
          [2.4, 4.4],
          [5.0, 6.5],
        ]}
      />

      {/* two painted parking bays */}
      {[-1.0, 0.1, 1.2].map((x) => (
        <mesh key={x} material={paperWhite} position={[x, 0.012, 0.55]}>
          <boxGeometry args={[0.07, 0.012, 1.9]} />
        </mesh>
      ))}
      <mesh material={paperWhite} position={[0.1, 0.012, 1.5]}>
        <boxGeometry args={[2.27, 0.012, 0.07]} />
      </mesh>
      {/* faint bay glow lines inside */}
      {[-0.45, 0.65].map((x) => (
        <mesh key={x} material={neonCyanFaint} position={[x, 0.012, -0.25]}>
          <boxGeometry args={[0.5, 0.012, 0.05]} />
        </mesh>
      ))}

      {/* charging post with cable */}
      <group position={[1.95, 0, -0.4]} rotation={[0, -0.5, 0]}>
        <mesh material={graphiteDark} position={[0, 0.38, 0]}>
          <boxGeometry args={[0.3, 0.76, 0.24]} />
        </mesh>
        <mesh material={screenBlue} position={[0, 0.52, 0.13]}>
          <boxGeometry args={[0.2, 0.18, 0.03]} />
        </mesh>
        <mesh material={graphite} position={[0, 0.72, 0]}>
          <boxGeometry args={[0.34, 0.08, 0.28]} />
        </mesh>
        <mesh
          material={graphiteDark}
          position={[-0.35, 0.18, 0.1]}
          rotation={[0, 0, 0.9]}
        >
          <boxGeometry args={[0.035, 0.55, 0.035]} />
        </mesh>
      </group>

      {/* exit chevrons toward the staircase */}
      {[0, 1].map((i) => (
        <mesh
          key={i}
          material={neonCyanFaint}
          position={[0.05 - i * 0.1, 0.012, -1.3 - i * 0.45]}
          rotation={[0, 0.05, 0]}
        >
          <boxGeometry args={[0.55, 0.02, 0.08]} />
        </mesh>
      ))}

      <Lamp position={[-1.9, 0, 0.6]} />
      <Bollard position={[-1.1, 0, -1.9]} />
      <Bollard position={[1.35, 0, -1.75]} />
    </group>
  );
}
