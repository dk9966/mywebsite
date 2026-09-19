import { useMemo } from "react";
import * as THREE from "three";
import { GRAZING_DEFAULT, useGrazingLight } from "./grazingLightStore";
import { stationLightColor, useStationLightColor } from "./stationLightColor";
import { useStationLightingMode } from "./stationLightingMode";

type RGB = readonly [number, number, number];
type Vec3 = readonly [number, number, number];

type PointSpec = {
  kind: "point";
  name: string;
  position: Vec3;
  color: RGB;
  /** candela — Blender watts / 4π */
  intensity: number;
};

type AreaSpec = {
  kind: "area";
  name: string;
  position: Vec3;
  /** unit forward vector (Blender's local -Z) */
  forward: Vec3;
  color: RGB;
  size: number;
  height?: number;
  /** nits — Blender watts / (area · π) */
  intensity: number;
};

type LightSpec = PointSpec | AreaSpec;

/** Keep fixture glows gentle and let the broad pillar lamps overlap. */
const GAIN: Record<string, number> = {
  rune: 0.3,
  // Boost all three grazers equally to preserve their blended color gradient.
  shaft: GRAZING_DEFAULT,
  lantern: 0.4,
  key: 0.2,
  fill: 0.2,
  rim: 1.4,
  core: 0.28,
  desk: 0.55,
  monitor: 0.8,
  floor_glow: 1,
};
const GAIN_DEFAULT = 0.7;

/** Most specific match wins: `shaft_rim_0`, then `shaft_rim`, then `shaft`. */
function gain(name: string): number {
  const parts = name.split("_");
  for (let i = parts.length; i > 0; i--) {
    const key = parts.slice(0, i).join("_");
    if (key in GAIN) return GAIN[key];
  }
  return GAIN_DEFAULT;
}

function point(
  name: string,
  position: Vec3,
  color: RGB,
  intensity: number,
): PointSpec {
  return { kind: "point", name, position, color, intensity: intensity * gain(name) };
}

function area(
  name: string,
  position: Vec3,
  forward: Vec3,
  color: RGB,
  size: number,
  intensity: number,
  height = size,
): AreaSpec {
  return {
    kind: "area",
    name,
    position,
    forward,
    color,
    size,
    height,
    intensity: intensity * gain(name),
  };
}

/** Station rig in glTF space, with soft floor pools and broad pillar lighting. */
export const STATION_LIGHTS: readonly LightSpec[] = [
  // Keep the hub glow centered on the current pillar axis and below the screen spill.
  point("core", [21.3, 7.2752, -0], [0.3, 0.62, 1], 2.069),
  point("core_up", [21.3, 7.6271, -0], [0.3, 0.62, 1], 2.3873),

  // Broad downward emitters soften the floor pools. The 0.53 nits over
  // 0.85² m² retains the original point lamp’s downward-hemisphere power.
  area("rune_0", [21.2367, 7.0231, -0.714], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),
  area("rune_1", [20, 7.0231, -1.428], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),
  area("rune_2", [18.7633, 7.0231, -0.714], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),
  area("rune_3", [18.7633, 7.0231, 0.714], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),
  area("rune_4", [20, 7.0231, 1.428], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),
  area("rune_5", [21.2367, 7.0231, 0.714], [0, -1, 0], [0.3, 0.62, 1], 0.85, 0.53),

  // railing lanterns
  point("lantern_0", [19.5415, 7.4023, -2.0647], [1, 0.6, 0.28], 0.557),
  point("lantern_1", [18.6503, 7.4023, -0.5785], [1, 0.6, 0.28], 0.557),
  point("lantern_2", [18.841, 7.4023, 1.1439], [1, 0.6, 0.28], 0.557),
  point("lantern_3", [20.0356, 7.4023, 2.3993], [1, 0.6, 0.28], 0.557),
  point("lantern_4", [21.7464, 7.4023, 2.6751], [1, 0.6, 0.28], 0.557),
  point("lantern_5", [23.275, 7.4023, 1.8587], [1, 0.6, 0.28], 0.557),
  point("lantern_6", [23.9972, 7.4774, 0.2835], [1, 0.6, 0.28], 0.557),

  // Raised point sources give circular, smoothly fading pools on the floor.
  // Their centers match the purple fixtures; height broadens the falloff.
  point("floor_glow_0", [19.5204, 7.48, 0.868], [0.4, 0.38, 1], 0.65),
  point("floor_glow_1", [21.1619, 7.48, 1.9752], [0.4, 0.38, 1], 0.65),
  point("floor_glow_2", [19.5853, 7.48, -0.99], [0.4, 0.38, 1], 0.65),
  point("floor_glow_3", [22.8603, 7.48, 1.219], [0.4, 0.38, 1], 0.65),
  point("crystal", [18.8545, 7.6511, -2.1544], [0.62, 0.3, 1], 0.25),

  // environment key / fill / rim — these carry most of the render's exposure
  area("key", [17.4, 12.8552, 5.2], [0.2795, -0.788, -0.5486], [0.55, 0.7, 1], 7, 0.3118),
  // Wider and shifted toward camera-right: a gentler, more even floor wash.
  area("fill", [21.3, 11.0552, 1.2], [0, -1, 0], [0.34, 0.55, 1], 6.2, 0.646),
  area("rim", [22.4, 10.2552, -5], [-0.3205, -0.6157, 0.7199], [0.45, 0.35, 0.95], 5, 0.2546),

  // Broad lamps outside the pillar blend across its faces without cone edges.
  area("shaft_key", [18.1, 5.05, 2.4], [0.8, -0.08, -0.6], [0.34, 0.5, 0.88], 3.2, 2.2, 2.4),
  area("shaft_fill", [24.3, 4.9, 1.8], [-0.85, -0.05, -0.52], [0.38, 0.44, 0.98], 3.2, 1.5, 2.4),
  area("shaft_back", [21.3, 4.8, -3], [0, 0, 1], [0.42, 0.34, 0.95], 3, 0.8, 2.4),

  // Broad blue screen spill, aimed from the monitor bank toward the open floor.
  area("monitor", [22.22, 8.48, -1.36], [-0.4, -0.65, 0.65], [0.24, 0.58, 1], 3, 0.48),

  // desk / console bank
  area("desk_0", [22.3904, 8.6052, -1.6166], [-0.3249, -0.8139, 0.4817], [0.42, 0.66, 1], 2.4, 0.2763),
  area("desk_1", [21.8872, 8.3052, -0.8705], [0.3602, -0.7648, -0.5341], [0.42, 0.66, 1], 2.8, 0.0812),
  area("desk_2", [22.7539, 7.9052, -2.1555], [-0.5502, 0.1782, 0.8158], [0.52, 0.64, 1], 2, 0.2546),
  area("desk_8", [21.9487, 7.2752, -0.9617], [0, -1, -0], [0.3, 0.58, 1], 2, 0.24),
  area("desk_11", [22.1304, 7.2552, -1.2311], [0, -1, -0], [0.42, 0.66, 1], 3, 0.08),
  point("desk_3", [21.5176, 7.4152, -2.2898], [0.3, 0.58, 1], 0.0637),
  point("desk_4", [21.899, 7.5152, -2.0325], [0.3, 0.58, 1], 0.0637),
  point("desk_5", [22.4296, 7.6552, -1.6747], [0.3, 0.58, 1], 0.0637),
  point("desk_6", [22.9436, 7.4952, -1.328], [0.3, 0.58, 1], 0.0637),
  point("desk_7", [23.3249, 7.4752, -1.0707], [0.3, 0.58, 1], 0.0637),
  point("desk_9", [21.004, 7.4952, -1.6802], [0.42, 0.66, 1], 0.0398),
  point("desk_10", [22.9688, 7.4952, -0.355], [0.42, 0.66, 1], 0.0398),
  point("desk_12", [22.6197, 7.6352, -1.9565], [0.52, 0.64, 1], 0.0875),
];

/** Blender's World: background colour × strength, as a flat environment term. */
const STATION_WORLD = {
  color: [0.002, 0.004, 0.012] as RGB,
  strength: 0.12,
};

/**
 * The one term with no counterpart in the .blend at all. EEVEE's fast GI puts
 * three diffuse bounces of the deck's own blue light into every crevice, the
 * shaft's far side and the space under the overhang; with only direct lighting
 * those all crush to black — the render holds them around 7/255 with a clear
 * blue cast, three was hitting 3/255 and neutral. This is that bounce, flat.
 */
const BOUNCE_FILL = {
  color: [0.022, 0.032, 0.075] as RGB,
  strength: 1.7,
};

function linear([r, g, b]: RGB): THREE.Color {
  return new THREE.Color().setRGB(r, g, b, THREE.LinearSRGBColorSpace);
}

function AreaLamp({ spec, strength = 1 }: { spec: AreaSpec; strength?: number }) {
  const { hue, tint } = useStationLightColor();
  const color = useMemo(() => stationLightColor(linear(spec.color), hue, tint), [spec.color, hue, tint]);
  const target = useMemo(
    () =>
      new THREE.Vector3(
        spec.position[0] + spec.forward[0],
        spec.position[1] + spec.forward[1],
        spec.position[2] + spec.forward[2],
      ),
    [spec.position, spec.forward],
  );
  // Both positions are local to the recentered rig. Object3D.lookAt expects
  // world coordinates, so compute the local orientation directly instead.
  const quaternion = useMemo(() => new THREE.Quaternion().setFromRotationMatrix(
    new THREE.Matrix4().lookAt(
      new THREE.Vector3(...spec.position), target, new THREE.Vector3(0, 1, 0),
    ),
  ), [spec.position, target]);
  return (
    <rectAreaLight
      name={spec.name}
      position={spec.position as unknown as THREE.Vector3Tuple}
      color={color}
      intensity={spec.intensity * strength}
      width={spec.size}
      height={spec.height ?? spec.size}
      quaternion={quaternion}
    />
  );
}

function PointLamp({ spec }: { spec: PointSpec }) {
  const { hue, tint } = useStationLightColor();
  const color = useMemo(() => spec.name.startsWith("lantern_") ? linear(spec.color) : stationLightColor(linear(spec.color), hue, tint), [spec.name, spec.color, hue, tint]);
  return (
    <pointLight
      name={spec.name}
      position={spec.position as unknown as THREE.Vector3Tuple}
      color={color}
      intensity={spec.intensity}
      distance={0}
      decay={2}
    />
  );
}

/** Fit the architectural rig to the exported second deck, including live resizes. */
export function experienceLights(scene: THREE.Object3D, role: "experience" | "about" | "contact" = "experience"): LightSpec[] {
  const project = scene.getObjectByName("island_pillar_project");
  const experience = scene.getObjectByName(`island_pillar_${role}`) ?? (role === "experience" ? scene.getObjectByName("island_pillar_empty") : undefined);
  const floor = scene.getObjectByName("deck_floor_b");
  const otherFloor = scene.getObjectByName(`deck_floor_${role}`) ?? (role === "experience" ? scene.getObjectByName("deck_floor_empty") : undefined);
  if (!project || !experience || !floor || !otherFloor) return [];
  scene.updateWorldMatrix(true, true);
  const from = project.getWorldPosition(new THREE.Vector3());
  const to = experience.getWorldPosition(new THREE.Vector3());
  const a = new THREE.Box3().setFromObject(floor);
  const b = new THREE.Box3().setFromObject(otherFloor);
  const scale = experience.scale.x / project.scale.x;
  const rotation = experience.getWorldQuaternion(new THREE.Quaternion()).multiply(
    project.getWorldQuaternion(new THREE.Quaternion()).invert(),
  );
  const specs = STATION_LIGHTS.filter(s =>
    /^(rune_|shaft_|floor_glow_|key$|fill$|rim$)/.test(s.name),
  ).map((spec): LightSpec => {
    const position: Vec3 = [
      to.x + (spec.position[0] - from.x) * scale,
      spec.name.startsWith("shaft_")
        ? spec.position[1] * (b.max.y / a.max.y)
        : b.max.y + (spec.position[1] - a.max.y) * scale,
      to.z + (spec.position[2] - from.z) * scale,
    ];
    const offset = new THREE.Vector3(position[0] - to.x, 0, position[2] - to.z).applyQuaternion(rotation);
    const rotated: Vec3 = [to.x + offset.x, position[1], to.z + offset.z];
    if (spec.kind === "point") return { ...spec, position: rotated, intensity: spec.intensity * scale * scale };
    const forward = new THREE.Vector3(...spec.forward).applyQuaternion(rotation).toArray();
    return { ...spec, position: rotated, forward, size: spec.size * scale, height: (spec.height ?? spec.size) * scale };
  });
  // The second deck has its own fence layout. Put the light at each real bulb,
  // not at the mesh origin (these fixtures contain world-authored vertices).
  scene.traverse(object => {
    const lantern = role === "experience"
      ? /^(experience_lantern_|bridge_lantern_(project|experience)_).*_glass$/
      : role === "about"
        ? /^(about_lantern_|bridge_about_lantern_|bridge_lantern_about_).*_glass$/
        : /^(contact_lantern_|bridge_contact_lantern_|bridge_lantern_contact_).*_glass$/;
    if (!lantern.test(object.name)) return;
    const center = new THREE.Box3().setFromObject(object).getCenter(new THREE.Vector3());
    specs.push(point(`lantern_${object.name}`, center.toArray(), [1, 0.6, 0.28], 0.557 * scale * scale));
  });
  return specs;
}

export function StationLights({ scene }: { scene: THREE.Object3D }) {
  const optimized = useStationLightingMode((state) => state.mode === "optimized");
  // Omit only the small spill lights; fixture materials and broad lighting stay intact.
  const keepLight = (spec: LightSpec) => !optimized || !/^(rune_|desk_)/.test(spec.name);
  const grazingStrength = useGrazingLight((state) => state.strength);
  const { hue, tint } = useStationLightColor();
  const world = useMemo(() => stationLightColor(linear(STATION_WORLD.color), hue, tint), [hue, tint]);
  const bounce = useMemo(() => stationLightColor(linear(BOUNCE_FILL.color), hue, tint), [hue, tint]);
  const otherLights = useMemo(() => experienceLights(scene), [scene]);
  const aboutLights = useMemo(() => experienceLights(scene, "about"), [scene]);
  const contactLights = useMemo(() => experienceLights(scene, "contact"), [scene]);
  const projectLights = useMemo(() => {
    const project = scene.getObjectByName("island_pillar_project");
    const angle = Number(project?.userData.station_rim_rotation ?? 0);
    const origin = project?.getWorldPosition(new THREE.Vector3()) ?? new THREE.Vector3();
    return STATION_LIGHTS.map(spec => {
      if (!spec.name.startsWith("lantern_")) return spec;
      const position = new THREE.Vector3(...spec.position).sub(origin)
        .applyAxisAngle(new THREE.Vector3(0, 1, 0), angle).add(origin).toArray();
      return { ...spec, position };
    });
  }, [scene]);
  return (
    <group name="stationLights">
      <ambientLight color={world} intensity={STATION_WORLD.strength} />
      <ambientLight color={bounce} intensity={BOUNCE_FILL.strength} />
      {projectLights.filter(keepLight).map((spec) => {
        if (spec.kind === "point")
          return <PointLamp key={spec.name} spec={spec} />;
        return <AreaLamp key={spec.name} spec={spec} strength={spec.name.startsWith("shaft_") ? grazingStrength / GRAZING_DEFAULT : 1} />;
      })}
      <group name="experienceLights">
        {otherLights.filter(keepLight).map(spec => spec.kind === "point"
          ? <PointLamp key={spec.name} spec={spec} />
          : <AreaLamp key={spec.name} spec={spec} strength={spec.name.startsWith("shaft_") ? grazingStrength / GRAZING_DEFAULT : 1} />)}
      </group>
      <group name="aboutLights">
        {aboutLights.filter(keepLight).map(spec => spec.kind === "point"
          ? <PointLamp key={spec.name} spec={spec} />
          : <AreaLamp key={spec.name} spec={spec} strength={spec.name.startsWith("shaft_") ? grazingStrength / GRAZING_DEFAULT : 1} />)}
      </group>
      <group name="contactLights">
        {contactLights.filter(keepLight).map(spec => spec.kind === "point"
          ? <PointLamp key={spec.name} spec={spec} />
          : <AreaLamp key={spec.name} spec={spec} strength={spec.name.startsWith("shaft_") ? grazingStrength / GRAZING_DEFAULT : 1} />)}
      </group>
    </group>
  );
}
