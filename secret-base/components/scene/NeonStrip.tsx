import { neonCyan } from "./materials";

type Vec3 = [number, number, number];

/** Thin cyan emissive box strip. */
export function NeonStrip({
  position,
  size,
  rotation = [0, 0, 0],
}: {
  position: Vec3;
  size: Vec3;
  rotation?: Vec3;
}) {
  return (
    <mesh position={position} rotation={rotation} material={neonCyan}>
      <boxGeometry args={size} />
    </mesh>
  );
}
