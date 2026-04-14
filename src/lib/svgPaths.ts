import type { PathCommand } from "opentype.js";

export type DrainDirection =
  | "left"
  | "right"
  | "top"
  | "bottom"
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right";

export function commandsToD(commands: PathCommand[]): string {
  const parts: string[] = [];
  for (const c of commands) {
    switch (c.type) {
      case "M":
        parts.push(`M${c.x} ${c.y}`);
        break;
      case "L":
        parts.push(`L${c.x} ${c.y}`);
        break;
      case "Q":
        parts.push(`Q${c.x1} ${c.y1} ${c.x} ${c.y}`);
        break;
      case "C":
        parts.push(`C${c.x1} ${c.y1} ${c.x2} ${c.y2} ${c.x} ${c.y}`);
        break;
      case "Z":
        parts.push("Z");
        break;
    }
  }
  return parts.join("");
}

export function splitSubpaths(commands: PathCommand[]): PathCommand[][] {
  const subpaths: PathCommand[][] = [];
  let current: PathCommand[] = [];

  for (const cmd of commands) {
    current.push(cmd);
    if (cmd.type === "Z") {
      subpaths.push(current);
      current = [];
    }
  }

  if (current.length > 0) subpaths.push(current);
  return subpaths;
}

function getEndpoints(subpath: PathCommand[]): { x: number; y: number }[] {
  const pts: { x: number; y: number }[] = [];
  for (const cmd of subpath) {
    if (cmd.type !== "Z" && cmd.x != null && cmd.y != null) {
      pts.push({ x: cmd.x, y: cmd.y });
    }
  }
  return pts;
}

function directionScore(
  v: { x: number; y: number },
  direction: DrainDirection,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
): number {
  const w = bounds.maxX - bounds.minX || 1;
  const h = bounds.maxY - bounds.minY || 1;
  const nx = (v.x - bounds.minX) / w;
  const ny = (v.y - bounds.minY) / h;

  switch (direction) {
    case "left":
      return nx;
    case "right":
      return 1 - nx;
    case "top":
      return ny;
    case "bottom":
      return 1 - ny;
    case "top-left":
      return nx + ny;
    case "top-right":
      return 1 - nx + ny;
    case "bottom-left":
      return nx + (1 - ny);
    case "bottom-right":
      return 1 - nx + (1 - ny);
  }
}

/**
 * Rotates a closed subpath [M, ...body, Z] so that it starts from
 * a different vertex. The contour shape is preserved; only the
 * starting point changes, which controls where stroke-dashoffset
 * begins revealing.
 */
function reindexSubpath(
  subpath: PathCommand[],
  vertexIdx: number,
): PathCommand[] {
  if (vertexIdx === 0 || subpath.length < 3) return subpath;

  const m = subpath[0];
  const hasZ = subpath[subpath.length - 1].type === "Z";
  const body = subpath.slice(1, hasZ ? -1 : undefined);

  if (body.length === 0 || vertexIdx > body.length) return subpath;

  // vertex[0] = M point, vertex[i] = endpoint of body[i-1]
  // body[i] is the edge from vertex[i] to vertex[i+1]
  const newStart = body[vertexIdx - 1];

  const rotated: PathCommand[] = [];
  for (let i = vertexIdx; i < body.length; i++) rotated.push(body[i]);
  rotated.push({ type: "L", x: m.x, y: m.y });
  for (let i = 0; i < vertexIdx; i++) rotated.push(body[i]);

  const result: PathCommand[] = [
    { type: "M", x: newStart.x!, y: newStart.y! },
    ...rotated,
  ];
  if (hasZ) result.push({ type: "Z" });
  return result;
}

/**
 * Reindexes every closed subpath so that the stroke animation starts
 * from the vertex closest to the given drain direction.
 */
export function reindexForDirection(
  commands: PathCommand[],
  direction: DrainDirection,
): PathCommand[] {
  const subpaths = splitSubpaths(commands);
  const result: PathCommand[] = [];

  for (const sp of subpaths) {
    const pts = getEndpoints(sp);
    if (pts.length < 3) {
      result.push(...sp);
      continue;
    }

    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    const bounds = {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };

    let bestIdx = 0;
    let bestScore = Infinity;
    for (let i = 0; i < pts.length; i++) {
      const s = directionScore(pts[i], direction, bounds);
      if (s < bestScore) {
        bestScore = s;
        bestIdx = i;
      }
    }

    result.push(...reindexSubpath(sp, bestIdx));
  }

  return result;
}
