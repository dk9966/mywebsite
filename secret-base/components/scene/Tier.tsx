import { graphite, graphiteDark, neonCyanFaint } from "./materials";

type Vec3 = [number, number, number];

/**
 * Raised sub-platform layer on top of an island deck, with a faint neon
 * trim and a small step block — used to give each section tiered depth.
 */
export function Tier({
  radius,
  height = 0.3,
  position,
  segments = 8,
  step,
}: {
  radius: number;
  height?: number;
  position: Vec3;
  segments?: number;
  /** angle (rad) the access step faces; omit for no step */
  step?: number;
}) {
  return (
    <group position={position} name="tier">
      <mesh material={graphite} position={[0, height / 2, 0]}>
        <cylinderGeometry args={[radius, radius * 1.04, height, segments]} />
      </mesh>
      <mesh
        material={neonCyanFaint}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, height + 0.005, 0]}
      >
        <torusGeometry args={[radius * 0.95, 0.035, 3, segments]} />
      </mesh>
      {step !== undefined && (
        <mesh
          material={graphiteDark}
          position={[
            (radius + 0.25) * Math.cos(step),
            height / 2 - 0.1,
            -(radius + 0.25) * Math.sin(step),
          ]}
          rotation={[0, step + Math.PI / 2, 0]}
        >
          <boxGeometry args={[1.0, height, 0.55]} />
        </mesh>
      )}
    </group>
  );
}
