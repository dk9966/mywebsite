import {
  graphite,
  graphiteDark,
  neonCyan,
} from "./materials";
import { MechanicalPillar } from "./MechanicalPillar";

/** Railing arc on the deck rim: posts + a low-poly top rail. */
function RailArc({
  radius,
  start,
  end,
}: {
  radius: number;
  start: number;
  end: number;
}) {
  const span = end - start;
  const count = Math.max(2, Math.round(span / 0.42));
  const angles = Array.from(
    { length: count + 1 },
    (_, i) => start + (span * i) / count,
  );
  return (
    <group>
      {angles.map((t, i) => (
        <mesh
          key={i}
          material={graphiteDark}
          position={[radius * Math.cos(t), 0.26, -radius * Math.sin(t)]}
        >
          <boxGeometry args={[0.08, 0.52, 0.08]} />
        </mesh>
      ))}
      <mesh
        rotation={[-Math.PI / 2, 0, start]}
        position={[0, 0.52, 0]}
        material={graphite}
      >
        <torusGeometry args={[radius, 0.04, 4, 20, span]} />
      </mesh>
    </group>
  );
}

/**
 * Shared platform for all non-voxel islands. Deck top sits at local y = 0.
 * `depth` is the distance from the deck down to the cave floor, so pillars
 * always land on the ground (world floor is at y = -26).
 */
export function IslandBase({
  radius,
  depth,
  segments = 8,
  railArcs = [],
}: {
  radius: number;
  depth: number;
  segments?: number;
  railArcs?: [number, number][];
}) {
  const panelCount = segments * 2;
  const panelW = ((Math.PI * 2 * radius) / panelCount) * 0.88;
  const braceCount = 6;

  return (
    <group name="islandBase">
      {/* deck */}
      <mesh material={graphite} position={[0, -0.32, 0]}>
        <cylinderGeometry args={[radius, radius * 1.02, 0.64, segments]} />
      </mesh>
      {/* cyan rim trim */}
      <mesh
        material={neonCyan}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.03, 0]}
      >
        <torusGeometry args={[radius * 0.97, 0.055, 4, segments]} />
      </mesh>
      {/* blocky fascia panels hanging below the rim */}
      {Array.from({ length: panelCount }, (_, i) => {
        const t = ((i + 0.5) / panelCount) * Math.PI * 2;
        const h = 0.55 + ((i * 37) % 3) * 0.22;
        const r = radius * 0.99;
        return (
          <mesh
            key={i}
            material={i % 5 === 0 ? graphite : graphiteDark}
            position={[r * Math.cos(t), -0.62 - h / 2 + 0.3, -r * Math.sin(t)]}
            rotation={[0, t + Math.PI / 2, 0]}
          >
            <boxGeometry args={[panelW, h, 0.22]} />
          </mesh>
        );
      })}
      {/* stacked ring base */}
      <mesh material={graphiteDark} position={[0, -1.0, 0]}>
        <cylinderGeometry
          args={[radius * 0.84, radius * 0.92, 0.55, segments]}
        />
      </mesh>
      <mesh material={graphiteDark} position={[0, -1.48, 0]}>
        <cylinderGeometry args={[radius * 0.68, radius * 0.78, 0.5, segments]} />
      </mesh>
      {/* cyan seam between rings */}
      <mesh
        material={neonCyan}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -1.26, 0]}
      >
        <torusGeometry args={[radius * 0.79, 0.04, 4, segments]} />
      </mesh>
      {/* diagonal support braces from the lower ring up to the deck rim */}
      {Array.from({ length: braceCount }, (_, i) => {
        const t = ((i + 0.5) / braceCount) * Math.PI * 2;
        const xInner = radius * 0.66;
        const xOuter = radius * 0.94;
        const yInner = -1.45;
        const yOuter = -0.5;
        const len = Math.hypot(xOuter - xInner, yOuter - yInner);
        const phi = Math.atan2(yOuter - yInner, xOuter - xInner);
        return (
          <group key={i} rotation={[0, t, 0]}>
            <mesh
              material={graphite}
              position={[(xInner + xOuter) / 2, (yInner + yOuter) / 2, 0]}
              rotation={[0, 0, phi]}
            >
              <boxGeometry args={[len, 0.12, 0.14]} />
            </mesh>
          </group>
        );
      })}
      <MechanicalPillar radius={radius} depth={depth} segments={segments} />
      {railArcs.map(([a, b], i) => (
        <RailArc key={i} radius={radius - 0.28} start={a} end={b} />
      ))}
    </group>
  );
}
