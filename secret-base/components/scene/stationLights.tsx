import * as THREE from "three";

type PointSpec = {
  kind: "point";
  position: [number, number, number];
  color: string;
  energy: number;
  distance: number;
};

type AreaSpec = {
  kind: "area";
  position: [number, number, number];
  lookAt: [number, number, number];
  color: string;
  energy: number;
  size: number;
};

/**
 * Workshop lamps from base.blend, in glTF space (Blender XYZ → X, Z, -Y).
 * Key/fill/rim are left out — those are the old environment rig.
 */
export const STATION_LIGHTS: readonly (PointSpec | AreaSpec)[] = [
  // desk: key / fill / rim / under-slab / edge wash
  area([22.39, 1.617, 8.605], [-0.325, -0.482, -0.814], "#6ba8ff", 5.0, 2.4),
  area([21.887, 0.87, 8.305], [0.36, 0.534, -0.765], "#6ba8ff", 2.0, 2.8),
  area([22.754, 2.155, 7.905], [-0.55, -0.816, 0.178], "#85a3ff", 3.2, 2.0),
  area([22.13, 1.231, 7.255], [0, 0, -1], "#6ba8ff", 0.8, 3.0),
  area([21.949, 0.962, 7.275], [0, 0, -1], "#4d94ff", 1.5, 2.0),
  point([22.969, 0.355, 7.495], "#6ba8ff", 0.5, 2.4),
  point([21.004, 1.68, 7.495], "#6ba8ff", 0.5, 2.4),
  point([22.62, 1.957, 7.635], "#85a3ff", 1.1, 2.2),
  point([21.518, 2.29, 7.415], "#4d94ff", 0.8, 2.6),
  point([21.899, 2.033, 7.515], "#4d94ff", 0.8, 2.6),
  point([22.43, 1.675, 7.655], "#4d94ff", 0.8, 2.6),
  point([22.944, 1.328, 7.495], "#4d94ff", 0.8, 2.6),
  point([23.325, 1.071, 7.475], "#4d94ff", 0.8, 2.6),

  // lanterns along the railing
  point([19.541, 2.065, 7.402], "#ff9933", 7.0, 4.5),
  point([18.65, 0.578, 7.402], "#ff9933", 7.0, 4.5),
  point([18.841, -1.144, 7.402], "#ff9933", 7.0, 4.5),
  point([20.036, -2.399, 7.402], "#ff9933", 7.0, 4.5),
  point([21.746, -2.675, 7.402], "#ff9933", 7.0, 4.5),
  point([23.275, -1.859, 7.402], "#ff9933", 7.0, 4.5),
  point([23.997, -0.283, 7.477], "#ff9933", 7.0, 4.5),

  // floor rings, hub, crystals
  point([21.237, 0.714, 7.023], "#4d9eff", 2.4, 3.0),
  point([20.0, 1.428, 7.023], "#4d9eff", 2.4, 3.0),
  point([18.763, 0.714, 7.023], "#4d9eff", 2.4, 3.0),
  point([18.763, -0.714, 7.023], "#4d9eff", 2.4, 3.0),
  point([20.0, -1.428, 7.023], "#4d9eff", 2.4, 3.0),
  point([21.237, -0.714, 7.023], "#4d9eff", 2.4, 3.0),
  point([20.0, 0.0, 7.275], "#4d9eff", 8.0, 6.0),
  point([18.854, 2.154, 7.651], "#9e4dff", 6.0, 4.0),
  point([18.22, -0.868, 7.019], "#9e4dff", 3.0, 3.2),
  point([19.862, -1.975, 7.019], "#9e4dff", 3.0, 3.2),
  point([18.285, 0.99, 7.019], "#9e4dff", 3.0, 3.2),
  point([21.56, -1.219, 7.019], "#9e4dff", 3.0, 3.2),

  // pillar shaft — local, not the old cave fill
  area([18.94, -1.696, 6.507], [0.4, 0.64, -0.2], "#577fcc", 8.0, 1.6),
  area([18.94, -1.696, 5.587], [0.4, 0.64, -0.2], "#577fcc", 8.0, 1.6),
  area([18.94, -1.696, 4.547], [0.4, 0.64, -0.2], "#577fcc", 9.0, 1.8),
];

function toGltf(p: [number, number, number]): [number, number, number] {
  return [p[0], p[2], -p[1]];
}

function point(
  blender: [number, number, number],
  color: string,
  energy: number,
  distance: number,
): PointSpec {
  return { kind: "point", position: toGltf(blender), color, energy, distance };
}

function area(
  blender: [number, number, number],
  fwd: [number, number, number],
  color: string,
  energy: number,
  size: number,
): AreaSpec {
  const position = toGltf(blender);
  const dir = toGltf(fwd);
  return {
    kind: "area",
    position,
    lookAt: [position[0] + dir[0], position[1] + dir[1], position[2] + dir[2]],
    color,
    energy,
    size,
  };
}

export function StationLights() {
  return (
    <group name="stationLights">
      {STATION_LIGHTS.map((spec, i) =>
        spec.kind === "point" ? (
          <pointLight
            key={i}
            position={spec.position}
            color={spec.color}
            intensity={spec.energy * 0.22}
            distance={spec.distance}
            decay={2}
          />
        ) : (
          <rectAreaLight
            key={i}
            position={spec.position}
            color={spec.color}
            intensity={spec.energy * 0.18}
            width={spec.size}
            height={spec.size}
            onUpdate={(light) => {
              light.lookAt(new THREE.Vector3(...spec.lookAt));
            }}
          />
        ),
      )}
    </group>
  );
}
