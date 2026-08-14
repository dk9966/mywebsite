// Island layout plan (from phase1prompt.md), with x/z spread out so decks
// don't overlap and bridges get real spans.

export type IslandDef = {
  position: [number, number, number];
  radius: number;
  height: number;
};

const SPREAD = 1.55;

function spread([x, y, z]: [number, number, number]): [number, number, number] {
  return [x * SPREAD, y, z * SPREAD];
}

export const islandLayout = {
  projects: {
    position: [0, 0, 0] as [number, number, number],
    radius: 5.5,
    height: 8,
  },
  about: {
    position: spread([-7, 1.5, -3]),
    radius: 3.2,
    height: 6,
  },
  workshop: {
    position: spread([-8, -1, 3.5]),
    radius: 3.8,
    height: 4.5,
  },
  experiences: {
    position: spread([7, 1.5, -3]),
    radius: 4.2,
    height: 6,
  },
  contact: {
    position: spread([10, 0, 0.4]),
    radius: 2.8,
    height: 5,
  },
  minecraft: {
    position: spread([6.8, -1.2, 5.3]),
    radius: 3.5,
    height: 3.5,
  },
  // foreground entrance platform (car/vehicle pad, no cars yet)
  garage: {
    position: [1.9, -1.6, 11.8],
    radius: 2.6,
    height: 3,
  },
} satisfies Record<string, IslandDef>;

/**
 * Point on the deck rim of island `a`, on the side facing island `b`.
 * `inset` pulls the point slightly inside the rim so bridges overlap decks.
 */
export function rimPoint(
  a: IslandDef,
  b: IslandDef,
  inset = 0.35,
): [number, number, number] {
  const dx = b.position[0] - a.position[0];
  const dz = b.position[2] - a.position[2];
  const len = Math.hypot(dx, dz) || 1;
  const r = a.radius - inset;
  return [
    a.position[0] + (dx / len) * r,
    a.position[1] + 0.02,
    a.position[2] + (dz / len) * r,
  ];
}
