import { graphiteDark, lampWarm, neonCyan } from "./materials";

type Vec3 = [number, number, number];

/** Short rim bollard with a glowing cyan tip. */
export function Bollard({ position }: { position: Vec3 }) {
  return (
    <group position={position}>
      <mesh material={graphiteDark} position={[0, 0.16, 0]}>
        <boxGeometry args={[0.11, 0.32, 0.11]} />
      </mesh>
      <mesh material={neonCyan} position={[0, 0.35, 0]}>
        <boxGeometry args={[0.09, 0.06, 0.09]} />
      </mesh>
    </group>
  );
}

/** Square warm lamp on a short post (the amber accent lamps in the reference). */
export function Lamp({
  position,
  height = 0.9,
}: {
  position: Vec3;
  height?: number;
}) {
  return (
    <group position={position}>
      <mesh material={graphiteDark} position={[0, height / 2, 0]}>
        <boxGeometry args={[0.09, height, 0.09]} />
      </mesh>
      <mesh material={lampWarm} position={[0, height + 0.11, 0]}>
        <boxGeometry args={[0.2, 0.24, 0.2]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, height + 0.26, 0]}>
        <boxGeometry args={[0.24, 0.06, 0.24]} />
      </mesh>
    </group>
  );
}
