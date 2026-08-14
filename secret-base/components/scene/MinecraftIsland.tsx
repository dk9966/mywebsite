import { useMemo } from "react";
import { Instances, Instance } from "@react-three/drei";
import * as THREE from "three";
import { Sign } from "./Sign";
import {
  crateOrange,
  lampWarm,
  mcDirt,
  mcFlowerRed,
  mcFlowerYellow,
  mcGrass,
  mcLeaves,
  mcStone,
  mcWater,
  mcWood,
} from "./materials";
import { islandLayout } from "./layout";

const C = 0.72; // cube size

// terrain heightmap (0 = empty)
const H = [
  [0, 0, 1, 1, 1, 0, 0, 0],
  [0, 1, 2, 2, 2, 1, 1, 0],
  [1, 1, 2, 3, 2, 2, 1, 1],
  [1, 2, 3, 3, 3, 2, 2, 1],
  [1, 2, 3, 3, 3, 2, 2, 1],
  [0, 1, 2, 2, 2, 2, 1, 0],
  [0, 1, 1, 2, 2, 1, 1, 0],
  [0, 0, 1, 1, 1, 0, 0, 0],
];

type V3 = [number, number, number];

function buildVoxels() {
  const grass: V3[] = [];
  const dirt: V3[] = [];
  const stone: V3[] = [];
  const wood: V3[] = [];
  const leaves: V3[] = [];

  const rows = H.length;
  const cols = H[0].length;
  const cx = (cols - 1) / 2;
  const cz = (rows - 1) / 2;

  const at = (gx: number, gz: number, y: number): V3 => [
    (gx - cx) * C,
    y * C,
    (gz - cz) * C,
  ];

  for (let gz = 0; gz < rows; gz++) {
    for (let gx = 0; gx < cols; gx++) {
      const h = H[gz][gx];
      if (h === 0) continue;
      for (let y = 0; y < h; y++) {
        if (y === h - 1) grass.push(at(gx, gz, y));
        else dirt.push(at(gx, gz, y));
      }
      // stone underside, thicker toward the center
      const dist = Math.hypot(gx - cx, gz - cz);
      const depth = Math.max(1, Math.round(3.5 - dist * 0.8));
      for (let y = 1; y <= depth; y++) {
        stone.push(at(gx, gz, -y));
      }
    }
  }

  // small stone cliff with a cave mouth on the front-right (like the reference)
  const cliffCells: [number, number][] = [
    [4, 5],
    [5, 5],
  ];
  for (const [cx2, cz2] of cliffCells) {
    const base = H[cz2][cx2];
    stone.push(at(cx2, cz2, base));
  }

  // two simple blocky trees
  const trees: [number, number][] = [
    [2, 2],
    [2, 5],
  ];
  for (const [tx, tz] of trees) {
    const base = H[tz][tx];
    wood.push(at(tx, tz, base), at(tx, tz, base + 1));
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        if (Math.abs(dx) + Math.abs(dz) === 2) continue; // clip corners
        leaves.push(at(tx + dx, tz + dz, base + 2));
      }
    }
    leaves.push(at(tx, tz, base + 3));
  }

  return { grass, dirt, stone, wood, leaves };
}

function VoxelGroup({
  positions,
  material,
}: {
  positions: V3[];
  material: THREE.Material;
}) {
  return (
    <Instances material={material} limit={positions.length} frustumCulled={false}>
      <boxGeometry args={[C, C, C]} />
      {positions.map((p, i) => (
        <Instance key={i} position={p} />
      ))}
    </Instances>
  );
}

/** Voxel Minecraft island: cube terrain, trees, waterfall, sign. */
export function MinecraftIsland() {
  const { position } = islandLayout.minecraft;
  const { grass, dirt, stone, wood, leaves } = useMemo(buildVoxels, []);

  return (
    <group name="minecraftIsland" position={position}>
      <VoxelGroup positions={grass} material={mcGrass} />
      <VoxelGroup positions={dirt} material={mcDirt} />
      <VoxelGroup positions={stone} material={mcStone} />
      <VoxelGroup positions={wood} material={mcWood} />
      <VoxelGroup positions={leaves} material={mcLeaves} />

      {/* dark cave mouth in the cliff face */}
      <mesh position={[0.72 * C, 2 * C, 1.52 * C]}>
        <boxGeometry args={[C * 1.1, C * 0.8, C * 0.4]} />
        <meshBasicMaterial color="#04070f" />
      </mesh>

      {/* river running to the front edge, then a cube waterfall */}
      <group position={[-0.6 * C, 0, 2.0 * C]}>
        {/* river strip on top of the front blocks */}
        <mesh material={mcWater} position={[0, 0.42 * C, -0.5 * C]}>
          <boxGeometry args={[C * 0.9, C * 0.3, C * 2.4]} />
        </mesh>
        {/* lip pouring over the edge */}
        <mesh material={mcWater} position={[0, 0.15 * C, 0.85 * C]}>
          <boxGeometry args={[C * 0.9, C * 0.85, C * 0.5]} />
        </mesh>
        {/* falling column */}
        {Array.from({ length: 11 }, (_, i) => (
          <mesh
            key={i}
            material={mcWater}
            position={[0, (-0.6 - i * 0.95) * C, 0.95 * C]}
          >
            <boxGeometry args={[C * 0.85, C, C * 0.5]} />
          </mesh>
        ))}
      </group>

      {/* flowers, pumpkin, torch */}
      <mesh material={mcFlowerRed} position={[-0.36 * 1, 1.26, -1.8]}>
        <boxGeometry args={[0.11, 0.2, 0.11]} />
      </mesh>
      <mesh material={mcFlowerYellow} position={[0.36, 1.26, -1.08]}>
        <boxGeometry args={[0.11, 0.2, 0.11]} />
      </mesh>
      <mesh material={mcFlowerRed} position={[-1.08, 1.98, 0.36]}>
        <boxGeometry args={[0.11, 0.2, 0.11]} />
      </mesh>
      <mesh material={mcFlowerYellow} position={[-1.6, 1.26, -0.5]}>
        <boxGeometry args={[0.11, 0.2, 0.11]} />
      </mesh>
      <mesh material={crateOrange} position={[1.08, 1.26, -1.08]}>
        <boxGeometry args={[0.34, 0.3, 0.34]} />
      </mesh>
      <group position={[0.36, 0, 1.08]}>
        <mesh material={mcWood} position={[0, 2.0, 0]}>
          <boxGeometry args={[0.08, 0.4, 0.08]} />
        </mesh>
        <mesh material={lampWarm} position={[0, 2.24, 0]}>
          <boxGeometry args={[0.12, 0.12, 0.12]} />
        </mesh>
      </group>

      <Sign
        text="MINECRAFT"
        width={2.6}
        position={[1.4, 1.5, 2.6]}
        rotation={[0, 0.45, 0]}
        postHeight={1.0}
      />
    </group>
  );
}
