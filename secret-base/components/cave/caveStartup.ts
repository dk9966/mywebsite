import * as THREE from "three";
import type { CaveLight } from "./caveAssets";

/**
 * The cave's power-on: the amber practicals are already lit, and the cool
 * white lights stutter on like fluorescent tubes, each zone on its own
 * schedule, all steady after STARTUP_SECONDS; then the platform titles strike
 * the same way, a beat later.
 *
 * The Blender rig fakes most of the white light (overhead spots, fills,
 * bounce cards, the baked GI), so the flicker is tied back to the physical
 * fixtures: every zone's rig lights and the white lenses and strips in that
 * zone share one level, and everything that stands in for bounce light (the
 * cave-wide fills, the dim reflected blues, the baked indirect light) follows
 * the zones round it, weighted by their power and distance.
 */

export const STARTUP_SECONDS = 2;
/** The platform titles strike after the lights have settled, each within this window. */
const TITLES_DELAY = 0.5;
const TITLES_SPREAD = 0.4;

/** Each CaveLabels title's power, 0..1 (its `uLevel` uniform; shared, so it survives the labels remounting). */
export const TITLE_POWER = Array.from({ length: 4 }, () => ({ value: 1 }));

/** The rig's light zones ("RL | <zone> | ..."); the Center zone lights the console and its panel wall. */
const ZONES = ["Center", "Rear left", "Front left", "Upper right", "Lower right"];
/** The emitters that are physical white fixtures; they flicker with the zone they sit in. */
export const WHITE_FIXTURES = new Set(["Lower | cool white practical diffuser", "Lower | circular light cool white lenses"]);
/** Softens the distance weighting of zones for bounce light (m²): a zone's pull fades over a few metres, not at a point. */
export const MIX_SOFTNESS = 9;

export const ALWAYS_ON = -2;
export const MIXED = -1;

export type LightGroups = {
  /** Per light: its zone, MIXED for bounce stand-ins (weighted by the zones round it), ALWAYS_ON for amber and the holo table. */
  zone: number[];
  /** Per mixed light: each zone's share of its level. */
  mix: Float32Array[];
  /** Per zone: power-weighted centre (xyz) and total power (w). Shared with the lit materials' uniforms. */
  anchors: THREE.Vector4[];
  /** Per zone: its current level, 0..1. Shared with the lit materials' uniforms. */
  levels: Float32Array;
  /** The white fixtures' materials, one per zone they appear in, with their full colour. */
  fixtures: { material: THREE.MeshBasicMaterial; color: THREE.Color; zone: number }[];
};

const isWhite = (l: CaveLight) => !l.name.startsWith("Holo table") && l.color[2] >= l.color[0];

function zoneOf(l: CaveLight) {
  const [rig, zone] = l.name.split(" | ");
  if (rig === "RL") return ZONES.indexOf(zone); // "Cave" fills: -1, mixed
  if (rig === "Lower") return ZONES.indexOf("Lower right"); // the lower bay's wall washes
  return MIXED;
}

/** Each zone's share of the light at a point (bounce light comes from every zone, mostly the near ones). */
export function zoneShares(anchors: THREE.Vector4[], p: THREE.Vector3): Float32Array {
  const shares = new Float32Array(anchors.length);
  let total = 0;
  anchors.forEach((a, i) => {
    const dx = p.x - a.x, dy = p.y - a.y, dz = p.z - a.z;
    shares[i] = a.w / (dx * dx + dy * dy + dz * dz + MIX_SOFTNESS);
    total += shares[i];
  });
  return shares.map((s) => s / total);
}

export function groupLights(lights: CaveLight[]): LightGroups {
  const zone = lights.map((l) => (isWhite(l) ? zoneOf(l) : ALWAYS_ON));
  const anchors = ZONES.map(() => new THREE.Vector4());
  lights.forEach((l, i) => {
    const a = anchors[zone[i]];
    if (!a) return;
    a.x += l.position[0] * l.power;
    a.y += l.position[1] * l.power;
    a.z += l.position[2] * l.power;
    a.w += l.power;
  });
  for (const a of anchors) a.set(a.x / a.w, a.y / a.w, a.z / a.w, a.w);
  const mix = lights.map((l, i) => (zone[i] === MIXED ? zoneShares(anchors, new THREE.Vector3(...l.position)) : new Float32Array(0)));
  return { zone, mix, anchors, levels: new Float32Array(ZONES.length).fill(1), fixtures: [] };
}

/**
 * Splits a white fixture mesh by zone (each triangle goes to the nearest zone
 * centre), one material per zone, so each zone's lenses dim with its light.
 */
export function splitFixture(mesh: THREE.Mesh, groups: LightGroups) {
  const material = mesh.material as THREE.MeshBasicMaterial;
  const geometry = mesh.geometry;
  const position = geometry.getAttribute("position");
  const index = geometry.index?.array ?? Array.from({ length: position.count }, (_, i) => i);
  const centres = groups.anchors.map((anchor) => new THREE.Vector3(anchor.x, anchor.y, anchor.z));
  const byZone = centres.map(() => [] as number[]);
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  for (let t = 0; t < index.length; t += 3) {
    a.fromBufferAttribute(position, index[t]);
    b.fromBufferAttribute(position, index[t + 1]);
    c.fromBufferAttribute(position, index[t + 2]);
    const centre = a.add(b).add(c).divideScalar(3).applyMatrix4(mesh.matrixWorld);
    let nearest = 0;
    centres.forEach((zone, z) => {
      if (centre.distanceToSquared(zone) < centre.distanceToSquared(centres[nearest])) nearest = z;
    });
    byZone[nearest].push(index[t], index[t + 1], index[t + 2]);
  }
  const materials: THREE.MeshBasicMaterial[] = [];
  const sorted: number[] = [];
  geometry.clearGroups();
  byZone.forEach((triangles, zone) => {
    if (!triangles.length) return;
    const zoned = material.clone();
    groups.fixtures.push({ material: zoned, color: material.color.clone(), zone });
    geometry.addGroup(sorted.length, triangles.length, materials.length);
    materials.push(zoned);
    sorted.push(...triangles);
  });
  geometry.setIndex(sorted);
  mesh.material = materials;
  material.dispose();
}

/* ------------------------------------------------------------ flicker --- */

function random(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Schedule = { on: number; blinks: { from: number; to: number; level: number }[] };

/**
 * A tube striking: dark, a few short blinks that come closer together and
 * brighter as it catches, then steady from `on`. Blinks last 60–180 ms, as a
 * cave frame takes up to ~100 ms and shorter ones would be dropped.
 */
function schedule(seed: number, on: number): Schedule {
  const next = random(seed);
  const blinks: Schedule["blinks"] = [];
  let t = 0.12 + next() * 0.3;
  while (t < on - 0.12) {
    const progress = t / on;
    const length = 0.06 + next() * 0.12;
    blinks.push({ from: t, to: Math.min(t + length, on - 0.06), level: 0.25 + progress * 0.45 + next() * 0.3 });
    t += length + (0.08 + next() * 0.32) * (1 - 0.6 * progress);
  }
  return { on, blinks };
}

function levelAt({ on, blinks }: Schedule, t: number) {
  if (t >= on) return 1;
  for (const b of blinks) if (t >= b.from && t < b.to) return Math.min(b.level, 1);
  return 0;
}

/**
 * Plays the power-on once. The clock starts on the second frame, after the
 * first one has compiled every shader (a multi-second stall that would eat
 * the flicker); until then the white lights are off.
 */
export class LightStartup {
  private readonly data: THREE.DataTexture;
  private readonly groups: LightGroups;
  private readonly texelsPerLight: number;
  private readonly onLevels?: (gains: Float32Array, overall: number) => void;
  private readonly values: Float32Array;
  private readonly base: Float32Array;
  private readonly schedules: Schedule[];
  /** Per title: when it starts striking, and its strike. */
  private readonly titles: { start: number; schedule: Schedule }[];
  private readonly end: number;
  private readonly gains: Float32Array;
  /** Frames seen so far (the clock starts on the second), and when it started. */
  private frames = 0;
  private start = 0;
  private done = false;

  /** `onLevels` gets every light's gain and the cave-wide (power-weighted) level, e.g. for the beams. */
  constructor(data: THREE.DataTexture, groups: LightGroups, texelsPerLight: number, onLevels?: (gains: Float32Array, overall: number) => void) {
    this.data = data;
    this.groups = groups;
    this.texelsPerLight = texelsPerLight;
    this.onLevels = onLevels;
    this.values = data.image.data as Float32Array;
    this.base = this.values.slice();
    this.gains = new Float32Array(groups.zone.length).fill(1);
    const seed = Math.floor(Math.random() * 1e9);
    // The Center zone (the console and its panels) catches last, at exactly STARTUP_SECONDS.
    this.schedules = groups.anchors.map((_, zone) =>
      schedule(seed + zone * 7919, zone === 0 ? STARTUP_SECONDS : STARTUP_SECONDS - 0.7 + random(seed + zone)() * 0.55),
    );
    this.titles = TITLE_POWER.map((_, i) => {
      const next = random(seed + 104729 * (i + 1));
      return { start: STARTUP_SECONDS + TITLES_DELAY + next() * TITLES_SPREAD, schedule: schedule(seed + i * 31337, 0.7 + next() * 0.4) };
    });
    this.end = Math.max(...this.titles.map((title) => title.start + title.schedule.on));
    this.apply(0);
  }

  /** Advances the flicker; true while it still needs frames. */
  tick(now: number): boolean {
    if (this.done) return false;
    if (++this.frames === 1) return true;
    if (this.frames === 2) this.start = now;
    const t = (now - this.start) / 1000;
    this.apply(t);
    if (t >= this.end) this.done = true;
    return true;
  }

  /** Everything at full power, as if it had played out. */
  finish() {
    this.done = true;
    this.apply(Infinity);
  }

  private apply(t: number) {
    const { zone, mix, anchors, levels, fixtures } = this.groups;
    this.schedules.forEach((s, z) => (levels[z] = levelAt(s, t)));
    zone.forEach((z, i) => {
      this.gains[i] = z >= 0 ? levels[z] : z === MIXED ? mix[i].reduce((sum, share, k) => sum + share * levels[k], 0) : 1;
      const at = (i * this.texelsPerLight + 2) * 4;
      for (let c = 0; c < 3; c++) this.values[at + c] = this.base[at + c] * this.gains[i];
    });
    this.data.needsUpdate = true;
    for (const f of fixtures) f.material.color.copy(f.color).multiplyScalar(levels[f.zone]);
    const power = anchors.reduce((sum, a) => sum + a.w, 0);
    this.onLevels?.(this.gains, anchors.reduce((sum, a, z) => sum + a.w * levels[z], 0) / power);
    this.titles.forEach(({ start, schedule }, i) => (TITLE_POWER[i].value = levelAt(schedule, t - start)));
  }
}
