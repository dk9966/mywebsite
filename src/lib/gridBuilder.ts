export type Vec3 = [number, number, number];

export type GridPath = {
  waypoints: Vec3[];
  spawnTime: number;
};

export function buildScene(_seed = 42): GridPath[] {
  const paths: GridPath[] = [];

  // --- Ground lines (flat, z=0) ---

  // Main horizontal line from far left to center-right
  paths.push({
    waypoints: [[-30, 0, 0], [16, 0, 0]],
    spawnTime: 0,
  });

  // Branch up from (-8, 0)
  paths.push({
    waypoints: [[-8, 0, 0], [-8, 18, 0]],
    spawnTime: 1.5,
  });

  // Branch down from (0, 0)
  paths.push({
    waypoints: [[0, 0, 0], [0, -14, 0]],
    spawnTime: 2.0,
  });

  // Horizontal branch from (-8, 10) going right
  paths.push({
    waypoints: [[-8, 10, 0], [10, 10, 0]],
    spawnTime: 2.8,
  });

  // Short branch from (10, 10) going down
  paths.push({
    waypoints: [[10, 10, 0], [10, -6, 0]],
    spawnTime: 3.5,
  });

  // Connect (0, -14) going right
  paths.push({
    waypoints: [[0, -14, 0], [14, -14, 0]],
    spawnTime: 3.2,
  });

  // Branch from (14, -14) going up
  paths.push({
    waypoints: [[14, -14, 0], [14, 0, 0]],
    spawnTime: 4.0,
  });

  // --- Box 1: small, near center (starts early) ---
  // Footprint: (0, 0) to (6, 6), height 8
  const b1 = { x: 0, y: 0, w: 6, h: 6, z: 8 };
  // Vertical edges + top edges
  paths.push({
    waypoints: [[b1.x, b1.y, 0], [b1.x, b1.y, b1.z], [b1.x + b1.w, b1.y, b1.z]],
    spawnTime: 3.0,
  });
  paths.push({
    waypoints: [[b1.x + b1.w, b1.y, 0], [b1.x + b1.w, b1.y, b1.z], [b1.x + b1.w, b1.y + b1.h, b1.z]],
    spawnTime: 3.8,
  });
  paths.push({
    waypoints: [[b1.x + b1.w, b1.y + b1.h, 0], [b1.x + b1.w, b1.y + b1.h, b1.z], [b1.x, b1.y + b1.h, b1.z]],
    spawnTime: 4.5,
  });
  paths.push({
    waypoints: [[b1.x, b1.y + b1.h, 0], [b1.x, b1.y + b1.h, b1.z], [b1.x, b1.y, b1.z]],
    spawnTime: 5.2,
  });

  // --- Box 2: taller, offset right (starts a bit later) ---
  // Footprint: (10, -6) to (14, 0), height 14
  paths.push({
    waypoints: [[10, -6, 0], [10, -6, 14], [14, -6, 14]],
    spawnTime: 4.2,
  });
  paths.push({
    waypoints: [[14, -6, 0], [14, -6, 14], [14, 0, 14]],
    spawnTime: 5.0,
  });
  paths.push({
    waypoints: [[14, 0, 0], [14, 0, 14], [10, 0, 14]],
    spawnTime: 5.6,
  });
  paths.push({
    waypoints: [[10, 0, 0], [10, 0, 14], [10, -6, 14]],
    spawnTime: 6.2,
  });

  // --- Box 3: wide and short, upper area ---
  // Footprint: (-8, 10) to (2, 18), height 5
  paths.push({
    waypoints: [[-8, 10, 0], [-8, 10, 5], [2, 10, 5]],
    spawnTime: 5.5,
  });
  paths.push({
    waypoints: [[2, 10, 0], [2, 10, 5], [2, 18, 5]],
    spawnTime: 6.0,
  });
  paths.push({
    waypoints: [[2, 18, 0], [2, 18, 5], [-8, 18, 5]],
    spawnTime: 6.8,
  });
  paths.push({
    waypoints: [[-8, 18, 0], [-8, 18, 5], [-8, 10, 5]],
    spawnTime: 7.3,
  });

  // Bottom edges for box 1
  paths.push({
    waypoints: [[b1.x, b1.y, 0], [b1.x + b1.w, b1.y, 0], [b1.x + b1.w, b1.y + b1.h, 0]],
    spawnTime: 5.8,
  });
  paths.push({
    waypoints: [[b1.x + b1.w, b1.y + b1.h, 0], [b1.x, b1.y + b1.h, 0]],
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
