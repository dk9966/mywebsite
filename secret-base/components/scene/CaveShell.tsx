import { caveWall, neonCyanFaint, rock, rockDark } from "./materials";

// x, y, z, radius, height — hand-placed, deterministic
const STALACTITES: [number, number, number, number, number][] = [
  [-16, 14, -12, 1.8, 7],
  [-7, 15, -16, 2.6, 9],
  [2, 14, -13, 1.4, 6],
  [9, 15, -16, 2.2, 8],
  [18, 14, -10, 1.6, 7],
  [-22, 15, 2, 2.0, 8],
  [24, 15, 4, 1.8, 7],
  [-2, 19, -22, 3.0, 10],
  [14, 17, -20, 1.5, 6],
  [-13, 17, -20, 1.7, 7],
  [-19, 16, -6, 1.2, 5],
  [5, 16, -18, 1.0, 4],
  [22, 16, -14, 2.4, 9],
  [-26, 14, -10, 2.8, 10],
  [12, 15, -8, 0.9, 3.5],
  [-4, 15, -10, 0.8, 3],
  [28, 13, -4, 1.4, 6],
  [-10, 14, -7, 0.7, 2.6],
];

// stalagmites rising from the chasm floor: x, z, radius, height
const STALAGMITES: [number, number, number, number][] = [
  [-18, 8, 1.6, 5],
  [-26, -2, 2.4, 8],
  [7, 14, 1.3, 4],
  [22, 10, 1.8, 6],
  [30, -2, 2.2, 7],
  [-8, 16, 1.0, 3.5],
  [16, 16, 1.5, 5],
  [-30, 6, 1.9, 6],
];

// loose boulders on the floor: x, z, size
const FLOOR_BOULDERS: [number, number, number][] = [
  [-14, 12, 1.1],
  [4, 18, 0.9],
  [12, 12, 0.7],
  [26, 4, 1.3],
  [-24, 4, 1.0],
  [-4, 20, 1.2],
  [20, -6, 0.8],
  [-30, -4, 1.4],
];

// x, z, radius, height
const FAR_PILLARS: [number, number, number, number][] = [
  [-24, -20, 2.6, 46],
  [-10, -26, 3.4, 50],
  [6, -28, 2.8, 48],
  [20, -24, 3.6, 50],
  [30, -12, 2.2, 44],
  [-32, -8, 2.4, 44],
  [36, -18, 3.0, 48],
  [-38, -14, 2.8, 46],
];

// faint vertical cyan light strips on far walls: x, z
const LIGHT_STRIPS: [number, number][] = [
  [-18, -23],
  [-1, -27],
  [13, -25],
  [26, -16],
  [-27, -15],
  [34, -8],
  [7, -24],
];

// drifting mist discs near the floor: x, z, radius
const MIST: [number, number, number][] = [
  [-10, 6, 14],
  [12, 10, 12],
  [24, -4, 10],
  [-24, -2, 11],
];

/** Simplified low-poly cave shell: faceted dome, formations, far pillars. */
export function CaveShell() {
  return (
    <group name="caveShell">
      {/* faceted cave dome (viewed from inside) */}
      <mesh material={caveWall} position={[0, 4, -6]} scale={[1.25, 1, 1.1]}>
        <sphereGeometry args={[52, 13, 9]} />
      </mesh>
      {/* chasm floor far below */}
      <mesh
        material={rockDark}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -26, 0]}
      >
        <circleGeometry args={[70, 16]} />
      </mesh>
      {/* stalactites */}
      {STALACTITES.map(([x, y, z, r, h], i) => (
        <mesh
          key={i}
          material={rock}
          position={[x, y - h / 2, z]}
          rotation={[Math.PI, 0, 0]}
        >
          <coneGeometry args={[r, h, 5]} />
        </mesh>
      ))}
      {/* stalagmites on the floor */}
      {STALAGMITES.map(([x, z, r, h], i) => (
        <mesh key={i} material={rock} position={[x, -26 + h / 2, z]}>
          <coneGeometry args={[r, h, 5]} />
        </mesh>
      ))}
      {/* floor boulders */}
      {FLOOR_BOULDERS.map(([x, z, s], i) => (
        <mesh
          key={i}
          material={rockDark}
          position={[x, -26 + s * 0.55, z]}
          rotation={[0.4 * i, i, 0.3]}
        >
          <icosahedronGeometry args={[s, 0]} />
        </mesh>
      ))}
      {/* distant pillar silhouettes */}
      {FAR_PILLARS.map(([x, z, r, h], i) => (
        <mesh key={i} material={rockDark} position={[x, -26 + h / 2, z]}>
          <cylinderGeometry args={[r * 0.7, r, h, 6]} />
        </mesh>
      ))}
      {/* faint vertical cyan strips, running floor to ceiling */}
      {LIGHT_STRIPS.map(([x, z], i) => (
        <mesh key={i} material={neonCyanFaint} position={[x, -5, z]}>
          <boxGeometry args={[0.14, 42, 0.14]} />
        </mesh>
      ))}
      {/* low mist above the chasm floor */}
      {MIST.map(([x, z, r], i) => (
        <mesh
          key={i}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[x, -24.6 + i * 0.35, z]}
        >
          <circleGeometry args={[r, 12]} />
          <meshBasicMaterial
            color="#1d3765"
            transparent
            opacity={0.28}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
