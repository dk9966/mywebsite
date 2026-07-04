export type Vec3 = [number, number, number];

export type GridPath = {
  waypoints: Vec3[];
  spawnTime: number;
  /** Per-path draw speed (world units/sec). Falls back to global cursor speed. */
  cursorSpeed?: number;
  /** Stable identity used by the tuner to address a single line. */
  id?: string;
  /** When true the path is kept in the layout but neither drawn nor picked. */
  hidden?: boolean;
  /** Override the global line color for this path (hex, e.g. component outlines). */
  lineColor?: string;
};

/** Split a polyline into individual two-point segments, each with its own id. */
export function splitPathIntoSegments(path: GridPath): GridPath[] {
  const { waypoints } = path;
  if (waypoints.length < 2) return [];

  const baseId = path.id ?? "seg";
  const segments: GridPath[] = [];

  for (let i = 0; i < waypoints.length - 1; i++) {
    segments.push({
      ...path,
      id: `${baseId}-seg-${i}`,
      waypoints: [waypoints[i], waypoints[i + 1]],
      spawnTime: path.spawnTime,
      cursorSpeed: path.cursorSpeed,
      hidden: path.hidden,
    });
  }

  return segments;
}

export function splitPathsIntoSegments(paths: GridPath[]): GridPath[] {
  const out: GridPath[] = [];
  for (const path of paths) {
    out.push(...splitPathIntoSegments(path));
  }
  return out;
}

export function buildScene(_seed = 42): GridPath[] {
  const paths: GridPath[] = [];

  // --- Ground lines (flat, z=0) ---

  // Main horizontal line from far left to center-right
  paths.push({
    waypoints: [
      [-30, 0, 0],
      [16, 0, 0],
    ],
    spawnTime: 0,
  });

  // Branch up from (-8, 0)
  paths.push({
    waypoints: [
      [-8, 0, 0],
      [-8, 18, 0],
    ],
    spawnTime: 1.5,
  });

  // Branch down from (0, 0)
  paths.push({
    waypoints: [
      [0, 0, 0],
      [0, -14, 0],
    ],
    spawnTime: 2.0,
  });

  // Horizontal branch from (-8, 10) going right
  paths.push({
    waypoints: [
      [-8, 10, 0],
      [10, 10, 0],
    ],
    spawnTime: 2.8,
  });

  // Short branch from (10, 10) going down
  paths.push({
    waypoints: [
      [10, 10, 0],
      [10, -6, 0],
    ],
    spawnTime: 3.5,
  });

  // Connect (0, -14) going right
  paths.push({
    waypoints: [
      [0, -14, 0],
      [14, -14, 0],
    ],
    spawnTime: 3.2,
  });

  // Branch from (14, -14) going up
  paths.push({
    waypoints: [
      [14, -14, 0],
      [14, 0, 0],
    ],
    spawnTime: 4.0,
  });

  // --- Box 1: small, near center (starts early) ---
  // Footprint: (0, 0) to (6, 6), height 8
  const b1 = { x: 0, y: 0, w: 6, h: 6, z: 8 };
  // Vertical edges + top edges
  paths.push({
    waypoints: [
      [b1.x, b1.y, 0],
      [b1.x, b1.y, b1.z],
      [b1.x + b1.w, b1.y, b1.z],
    ],
    spawnTime: 3.0,
  });
  paths.push({
    waypoints: [
      [b1.x + b1.w, b1.y, 0],
      [b1.x + b1.w, b1.y, b1.z],
      [b1.x + b1.w, b1.y + b1.h, b1.z],
    ],
    spawnTime: 3.8,
  });
  paths.push({
    waypoints: [
      [b1.x + b1.w, b1.y + b1.h, 0],
      [b1.x + b1.w, b1.y + b1.h, b1.z],
      [b1.x, b1.y + b1.h, b1.z],
    ],
    spawnTime: 4.5,
  });
  paths.push({
    waypoints: [
      [b1.x, b1.y + b1.h, 0],
      [b1.x, b1.y + b1.h, b1.z],
      [b1.x, b1.y, b1.z],
    ],
    spawnTime: 5.2,
  });

  // --- Box 2: taller, offset right (starts a bit later) ---
  // Footprint: (10, -6) to (14, 0), height 14
  paths.push({
    waypoints: [
      [10, -6, 0],
      [10, -6, 14],
      [14, -6, 14],
    ],
    spawnTime: 4.2,
  });
  paths.push({
    waypoints: [
      [14, -6, 0],
      [14, -6, 14],
      [14, 0, 14],
    ],
    spawnTime: 5.0,
  });
  paths.push({
    waypoints: [
      [14, 0, 0],
      [14, 0, 14],
      [10, 0, 14],
    ],
    spawnTime: 5.6,
  });
  paths.push({
    waypoints: [
      [10, 0, 0],
      [10, 0, 14],
      [10, -6, 14],
    ],
    spawnTime: 6.2,
  });

  // --- Box 3: wide and short, upper area ---
  // Footprint: (-8, 10) to (2, 18), height 5
  paths.push({
    waypoints: [
      [-8, 10, 0],
      [-8, 10, 5],
      [2, 10, 5],
    ],
    spawnTime: 5.5,
  });
  paths.push({
    waypoints: [
      [2, 10, 0],
      [2, 10, 5],
      [2, 18, 5],
    ],
    spawnTime: 6.0,
  });
  paths.push({
    waypoints: [
      [2, 18, 0],
      [2, 18, 5],
      [-8, 18, 5],
    ],
    spawnTime: 6.8,
  });
  paths.push({
    waypoints: [
      [-8, 18, 0],
      [-8, 18, 5],
      [-8, 10, 5],
    ],
    spawnTime: 7.3,
  });

  // Bottom edges for box 1
  paths.push({
    waypoints: [
      [b1.x, b1.y, 0],
      [b1.x + b1.w, b1.y, 0],
      [b1.x + b1.w, b1.y + b1.h, 0],
    ],
    spawnTime: 5.8,
  });
  paths.push({
    waypoints: [
      [b1.x + b1.w, b1.y + b1.h, 0],
      [b1.x, b1.y + b1.h, 0],
    ],
    spawnTime: 6.5,
  });

  return paths;
}

export function totalPathLength(waypoints: Vec3[]): number {
  let len = 0;
  for (let i = 1; i < waypoints.length; i++) {
    const dx = waypoints[i][0] - waypoints[i - 1][0];
    const dy = waypoints[i][1] - waypoints[i - 1][1];
    const dz = waypoints[i][2] - waypoints[i - 1][2];
    len += Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
  return len;
}

/** Latest moment every leader finishes drawing, plus a short settle hold. */
export function sceneDuration(
  paths: GridPath[],
  defaultCursorSpeed: number,
  holdSec = 0.5,
): number {
  if (paths.length === 0 || defaultCursorSpeed <= 0) return 20;

  let end = 0;
  for (const path of paths) {
    if (path.hidden) continue;
    const speed = path.cursorSpeed ?? defaultCursorSpeed;
    if (speed <= 0) continue;
    const finish = path.spawnTime + totalPathLength(path.waypoints) / speed;
    if (finish > end) end = finish;
  }

  return Math.ceil((end + holdSec) * 10) / 10;
}

export function samplePath(waypoints: Vec3[], distance: number): Vec3 {
  let remaining = distance;
  for (let i = 1; i < waypoints.length; i++) {
    const dx = waypoints[i][0] - waypoints[i - 1][0];
    const dy = waypoints[i][1] - waypoints[i - 1][1];
    const dz = waypoints[i][2] - waypoints[i - 1][2];
    const segLen = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (remaining <= segLen) {
      const t = remaining / segLen;
      return [
        waypoints[i - 1][0] + dx * t,
        waypoints[i - 1][1] + dy * t,
        waypoints[i - 1][2] + dz * t,
      ];
    }
    remaining -= segLen;
  }
  return waypoints[waypoints.length - 1];
}
