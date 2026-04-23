import TraceSkeleton from "skeleton-tracing-js";
import type { Font } from "opentype.js";

/**
 * A polyline in glyph-local em units. Origin matches opentype.js's path
 * coordinate system (Y points down, baseline at y = 0). Reusable at any
 * render size — the caller scales when drawing.
 */
export type Stroke = [number, number][];

export interface ExtractOpts {
  /** Raster resolution in pixels per em. Higher = cleaner topology, slower. */
  rasterRes?: number;
  /** RDP tolerance, em-relative (fraction of unitsPerEm). */
  simplifyEps?: number;
  /** Drop any polyline shorter than this fraction of an em. */
  minStrokeLen?: number;
  /** Padding (in raster pixels) around the glyph so the skeleton terminates cleanly. */
  rasterPad?: number;
}

const DEFAULTS: Required<ExtractOpts> = {
  rasterRes: 512,
  simplifyEps: 0.01,
  minStrokeLen: 0.03,
  rasterPad: 4,
};

export interface ExtractResult {
  strokes: Stroke[];
  /** Em-space bounding box of the source glyph (so callers can position without re-querying). */
  bbox: { x1: number; y1: number; x2: number; y2: number };
  /** Wall time spent inside the extractor, ms. Useful for the debug page. */
  elapsedMs: number;
}

/**
 * Extract centerline polylines from a glyph by rasterizing → Zhang–Suen
 * thinning → polyline tracing (skeleton-tracing-js) → simplify → spur cull.
 * Pure: same input → same output.
 */
export function extractCenterlines(
  font: Font,
  char: string,
  opts: ExtractOpts = {},
): ExtractResult {
  const o = { ...DEFAULTS, ...opts };
  const t0 = performance.now();

  const glyph = font.charToGlyph(char);
  const path = glyph.path;
  const bb = path.getBoundingBox();
  const bw = bb.x2 - bb.x1;
  const bh = bb.y2 - bb.y1;

  if (bw <= 0 || bh <= 0) {
    return {
      strokes: [],
      bbox: { x1: bb.x1, y1: bb.y1, x2: bb.x2, y2: bb.y2 },
      elapsedMs: performance.now() - t0,
    };
  }

  const scale = o.rasterRes / font.unitsPerEm;
  const W = Math.ceil(bw * scale) + 2 * o.rasterPad;
  const H = Math.ceil(bh * scale) + 2 * o.rasterPad;

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("centerline: 2d context unavailable");

  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#fff";

  const d = path.toPathData(3);
  const p2d = new Path2D(d);

  ctx.save();
  ctx.translate(o.rasterPad - bb.x1 * scale, o.rasterPad - bb.y1 * scale);
  ctx.scale(scale, scale);
  ctx.fill(p2d, "evenodd");
  ctx.restore();

  const imageData = ctx.getImageData(0, 0, W, H);
  const traced = TraceSkeleton.fromImageData(imageData);

  const minLenEm = o.minStrokeLen * font.unitsPerEm;
  const epsEm = o.simplifyEps * font.unitsPerEm;
  const strokes: Stroke[] = [];

  for (const poly of traced.polylines) {
    if (poly.length < 2) continue;

    const em: Stroke = poly.map((pt) => [
      (pt[0] - o.rasterPad) / scale + bb.x1,
      (pt[1] - o.rasterPad) / scale + bb.y1,
    ]);

    const simplified = simplifyRDP(em, epsEm);
    if (polylineLength(simplified) < minLenEm) continue;
    strokes.push(simplified);
  }

  return {
    strokes,
    bbox: { x1: bb.x1, y1: bb.y1, x2: bb.x2, y2: bb.y2 },
    elapsedMs: performance.now() - t0,
  };
}

// ─── Phase 4: glyph-level cache ──────────────────────────────────────────

/**
 * Cached centerline + drain plan for one (font family, char) pair. Both
 * pieces always travel together at call sites, so they share an entry.
 */
const drainCache = new Map<
  string,
  { extract: ExtractResult; plan: DrainPlan }
>();

function manualNodesCacheKey(manualNodes: [number, number][]): string {
  return manualNodes
    .map(([x, y]) => `${x.toFixed(5)},${y.toFixed(5)}`)
    .join(";");
}

/**
 * Memoised wrapper around `extractCenterlines` + `planLiquidDrain`.
 * Centerlines stay in em units, so the cache key is independent of render
 * size — the same entry serves every `DrainText` instance using the same
 * font family. Manual node lists are part of the key when provided.
 */
export function getCenterlineDrain(
  font: Font,
  char: string,
  opts?: ExtractOpts & PlanOpts,
): { extract: ExtractResult; plan: DrainPlan } {
  const family = font.names?.fontFamily?.en ?? "unknown";
  const mn = opts?.manualNodes;
  const mnKey = mn?.length ? `|mn:${manualNodesCacheKey(mn)}` : "";
  const key = `${family}:${char}${mnKey}`;
  const hit = drainCache.get(key);
  if (hit) return hit;

  const extract = extractCenterlines(font, char, opts);
  const plan = planLiquidDrain(extract.strokes, opts);
  const entry = { extract, plan };
  drainCache.set(key, entry);
  return entry;
}

/** For tests / debug pages that want to force fresh extraction. */
export function clearCenterlineCache(): void {
  drainCache.clear();
}

/** For debug instrumentation. */
export function centerlineCacheSize(): number {
  return drainCache.size;
}

function polylineLength(pts: Stroke): number {
  let len = 0;
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0];
    const dy = pts[i][1] - pts[i - 1][1];
    len += Math.hypot(dx, dy);
  }
  return len;
}

// ─── Phase 2: liquid-drain ordering ──────────────────────────────────────

/**
 * One stroke's contribution to the glyph drain. Polyline is oriented
 * FAR -> NEAR so SVG `stroke-dashoffset` animating 0 -> length erases
 * the far side first.
 */
export interface DrainStroke {
  points: Stroke;
  length: number;
  /** Glyph-normalized time the drain front first touches this stroke, [0, 1]. */
  tStart: number;
  /** Glyph-normalized time the drain front leaves this stroke, > tStart. */
  tEnd: number;
}

export interface DrainPlan {
  strokes: DrainStroke[];
  /** Geodesic distance from the drain hole to the network's antipode (em). */
  totalDistance: number;
  /** Position of the chosen drain hole in glyph em coords. */
  hole: [number, number];
}

export interface PlanOpts {
  /** Endpoint snap tolerance in em units. Defaults to ~0.5% of the bbox diagonal. */
  snapTol?: number;
  /**
   * Fixed graph node positions (glyph-local em coords, opentype Y-down). Each
   * extracted stroke endpoint snaps to the nearest manual point when distance
   * is less than `snapTol`; the node keeps the manual coordinates (not the
   * skeleton endpoint). Endpoints without a manual in range use the usual grid
   * snap. Unused manual positions never appear in the graph.
   */
  manualNodes?: [number, number][];
}

interface GraphNode {
  id: number;
  x: number;
  y: number;
  degree: number;
  component: number;
}

interface GraphEdge {
  id: number;
  a: number;
  b: number;
  polyline: Stroke;
  length: number;
  /** Bridge edges connect disconnected components for distance computation only. */
  virtual?: boolean;
  /** Set when this edge has been replaced by a split. */
  removed?: boolean;
}

interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** node id -> incident edge ids (kept in sync across splits / virtual bridges). */
  adj: Map<number, number[]>;
}

/**
 * Plan a liquid-drain over the centerline network: pick a single drain
 * hole on the right side, compute geodesic distance to every node, then
 * convert each stroke's two endpoint distances into a [tStart, tEnd]
 * window on the glyph's drain timeline.
 *
 * Disconnected components (i, j, !, ?, :, ;) are linked by virtual
 * euclidean bridges (MST over components) before Dijkstra so the dot of
 * an "i" drains adjacent to the top of the stem rather than instantly or
 * at the very end.
 */
export function planLiquidDrain(
  strokes: Stroke[],
  opts: PlanOpts = {},
): DrainPlan {
  if (strokes.length === 0) {
    return { strokes: [], totalDistance: 0, hole: [0, 0] };
  }

  const bb = strokesBoundingBox(strokes);
  const diag = Math.hypot(bb.x2 - bb.x1, bb.y2 - bb.y1);
  const snapTol = opts.snapTol ?? Math.max(diag * 0.005, 1e-6);

  const graph = buildStrokeGraph(strokes, snapTol, opts.manualNodes);
  if (graph.nodes.length === 0) {
    return { strokes: [], totalDistance: 0, hole: [0, 0] };
  }

  const { nodeId: holeId, point: holePoint } = pickDrainHole(graph);
  bridgeComponents(graph, holeId);

  const dist = dijkstra(graph, holeId);

  let dmax = 0;
  for (const d of dist.values()) {
    if (Number.isFinite(d) && d > dmax) dmax = d;
  }
  if (dmax === 0) {
    return { strokes: [], totalDistance: 0, hole: holePoint };
  }

  const out: DrainStroke[] = [];
  for (const e of graph.edges) {
    if (e.removed || e.virtual) continue;
    const dA = dist.get(e.a);
    const dB = dist.get(e.b);
    if (dA === undefined || dB === undefined) continue;
    if (!Number.isFinite(dA) || !Number.isFinite(dB)) continue;

    const dFar = Math.max(dA, dB);
    const dNear = Math.min(dA, dB);
    // polyline runs a -> b in storage. We want FAR -> NEAR.
    const points = dB > dA ? e.polyline.slice().reverse() : e.polyline.slice();

    out.push({
      points,
      length: e.length,
      tStart: 1 - dFar / dmax,
      tEnd: 1 - dNear / dmax,
    });
  }

  return { strokes: out, totalDistance: dmax, hole: holePoint };
}

function strokesBoundingBox(strokes: Stroke[]): {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
} {
  let x1 = Infinity;
  let y1 = Infinity;
  let x2 = -Infinity;
  let y2 = -Infinity;
  for (const s of strokes) {
    for (const [x, y] of s) {
      if (x < x1) x1 = x;
      if (y < y1) y1 = y;
      if (x > x2) x2 = x;
      if (y > y2) y2 = y;
    }
  }
  return { x1, y1, x2, y2 };
}

/**
 * Snap stroke endpoints to a hash grid (cell = snapTol). Coincident
 * endpoints across separate polylines collapse onto a single node.
 * Optional `manualNodes`: each endpoint first snaps to the **closest**
 * manual position if within `snapTol` (node uses exact manual coords).
 * Each stroke becomes one edge weighted by arc length.
 */
function buildStrokeGraph(
  strokes: Stroke[],
  snapTol: number,
  manualNodes?: [number, number][],
): Graph {
  const nodes: GraphNode[] = [];
  const cells = new Map<string, number[]>();
  const cell = snapTol;
  const manualNodeIdByIndex: number[] = [];

  function registerInCells(nodeId: number, x: number, y: number) {
    const cx = Math.floor(x / cell);
    const cy = Math.floor(y / cell);
    const key = `${cx},${cy}`;
    let bucket = cells.get(key);
    if (!bucket) {
      bucket = [];
      cells.set(key, bucket);
    }
    bucket.push(nodeId);
  }

  /** Closest manual index if distance is less than snapTol, else -1. */
  function nearestManualIndex(x: number, y: number): number {
    if (!manualNodes?.length) return -1;
    let best = -1;
    let bestDist = snapTol;
    for (let i = 0; i < manualNodes.length; i++) {
      const [mx, my] = manualNodes[i];
      const d = Math.hypot(mx - x, my - y);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return best;
  }

  function ensureManualNode(i: number): number {
    const existing = manualNodeIdByIndex[i];
    if (existing !== undefined) return existing;
    const [mx, my] = manualNodes![i];
    const id = nodes.length;
    manualNodeIdByIndex[i] = id;
    nodes.push({ id, x: mx, y: my, degree: 0, component: -1 });
    registerInCells(id, mx, my);
    return id;
  }

  function getOrCreateAutoNode(x: number, y: number): number {
    const cx = Math.floor(x / cell);
    const cy = Math.floor(y / cell);
    let bestId = -1;
    let bestDist = snapTol;
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const ids = cells.get(`${cx + dx},${cy + dy}`);
        if (!ids) continue;
        for (const id of ids) {
          const n = nodes[id];
          const d = Math.hypot(n.x - x, n.y - y);
          if (d < bestDist) {
            bestDist = d;
            bestId = id;
          }
        }
      }
    }
    if (bestId !== -1) return bestId;

    const id = nodes.length;
    nodes.push({ id, x, y, degree: 0, component: -1 });
    registerInCells(id, x, y);
    return id;
  }

  function getOrCreateNode(x: number, y: number): number {
    const mi = nearestManualIndex(x, y);
    if (mi >= 0) return ensureManualNode(mi);
    return getOrCreateAutoNode(x, y);
  }

  const edges: GraphEdge[] = [];
  for (const poly of strokes) {
    if (poly.length < 2) continue;
    const a = getOrCreateNode(poly[0][0], poly[0][1]);
    const b = getOrCreateNode(poly[poly.length - 1][0], poly[poly.length - 1][1]);
    const length = polylineLength(poly);
    edges.push({ id: edges.length, a, b, polyline: poly, length });
    nodes[a].degree++;
    nodes[b].degree++;
  }

  const adj = new Map<number, number[]>();
  for (const n of nodes) adj.set(n.id, []);
  for (const e of edges) {
    adj.get(e.a)!.push(e.id);
    adj.get(e.b)!.push(e.id);
  }

  // Connected components via BFS on the adjacency list.
  let comp = 0;
  for (const root of nodes) {
    if (root.component !== -1) continue;
    root.component = comp;
    const queue: number[] = [root.id];
    let head = 0;
    while (head < queue.length) {
      const cur = queue[head++];
      for (const eid of adj.get(cur)!) {
        const e = edges[eid];
        const next = e.a === cur ? e.b : e.a;
        if (nodes[next].component === -1) {
          nodes[next].component = comp;
          queue.push(next);
        }
      }
    }
    comp++;
  }

  return { nodes, edges, adj };
}

/**
 * Drain hole = the terminal (degree-1 node) closest to the middle of
 * the right edge of the glyph bbox (Y-up em coords). The drain front
 * then sweeps roughly horizontally from left to right rather than
 * gravitationally toward the bottom-right corner.
 *
 * For closed loops with no terminals, fall back to the global rightmost
 * polyline vertex, splitting mid-edge if needed.
 */
function pickDrainHole(
  graph: Graph,
): { nodeId: number; point: [number, number] } {
  const terminals = graph.nodes.filter((n) => n.degree === 1);
  if (terminals.length > 0) {
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const n of graph.nodes) {
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    }
    const midY = (minY + maxY) / 2;
    let best = terminals[0];
    let bestScore = Infinity;
    for (const n of terminals) {
      const score = Math.hypot(n.x - maxX, n.y - midY);
      if (score < bestScore) {
        bestScore = score;
        best = n;
      }
    }
    return { nodeId: best.id, point: [best.x, best.y] };
  }

  let polyMaxX = -Infinity;
  let polyMinY = Infinity;
  let polyMaxY = -Infinity;
  for (const e of graph.edges) {
    if (e.removed || e.virtual) continue;
    for (const [x, y] of e.polyline) {
      if (x > polyMaxX) polyMaxX = x;
      if (y < polyMinY) polyMinY = y;
      if (y > polyMaxY) polyMaxY = y;
    }
  }
  const polyMidY = (polyMinY + polyMaxY) / 2;

  let bestEdge = -1;
  let bestVertex = -1;
  let bestScore = Infinity;
  let bestX = 0;
  let bestY = 0;
  for (const e of graph.edges) {
    if (e.removed || e.virtual) continue;
    for (let i = 0; i < e.polyline.length; i++) {
      const [x, y] = e.polyline[i];
      const score = Math.hypot(x - polyMaxX, y - polyMidY);
      if (score < bestScore) {
        bestScore = score;
        bestX = x;
        bestY = y;
        bestEdge = e.id;
        bestVertex = i;
      }
    }
  }
  if (bestEdge === -1) {
    const n = graph.nodes[0];
    return { nodeId: n.id, point: [n.x, n.y] };
  }

  const e = graph.edges[bestEdge];
  if (bestVertex === 0) return { nodeId: e.a, point: [bestX, bestY] };
  if (bestVertex === e.polyline.length - 1)
    return { nodeId: e.b, point: [bestX, bestY] };

  const newNodeId = splitEdgeAtVertex(graph, bestEdge, bestVertex);
  return { nodeId: newNodeId, point: [bestX, bestY] };
}

/**
 * Split an edge at an interior polyline vertex. Original edge is
 * marked `removed`; two new edges connect to a fresh node at the split.
 * Adjacency is patched so the original endpoints reference the new
 * edges instead of the old one.
 */
function splitEdgeAtVertex(
  graph: Graph,
  edgeId: number,
  vertexIndex: number,
): number {
  const e = graph.edges[edgeId];
  const [sx, sy] = e.polyline[vertexIndex];
  const newNode: GraphNode = {
    id: graph.nodes.length,
    x: sx,
    y: sy,
    degree: 2,
    component: graph.nodes[e.a].component,
  };
  graph.nodes.push(newNode);

  const polyA = e.polyline.slice(0, vertexIndex + 1);
  const polyB = e.polyline.slice(vertexIndex);
  const edgeA: GraphEdge = {
    id: graph.edges.length,
    a: e.a,
    b: newNode.id,
    polyline: polyA,
    length: polylineLength(polyA),
  };
  const edgeB: GraphEdge = {
    id: graph.edges.length + 1,
    a: newNode.id,
    b: e.b,
    polyline: polyB,
    length: polylineLength(polyB),
  };
  graph.edges.push(edgeA, edgeB);

  const adjA = graph.adj.get(e.a)!;
  const ia = adjA.indexOf(edgeId);
  if (ia !== -1) adjA[ia] = edgeA.id;
  const adjB = graph.adj.get(e.b)!;
  const ib = adjB.indexOf(edgeId);
  if (ib !== -1) adjB[ib] = edgeB.id;
  graph.adj.set(newNode.id, [edgeA.id, edgeB.id]);

  e.removed = true;
  return newNode.id;
}

/**
 * Connect every disconnected component to the hole's component with a
 * virtual euclidean edge (Prim's MST over components). The bridge edges
 * carry distance only; they do not appear in the output strokes.
 */
function bridgeComponents(graph: Graph, holeId: number): void {
  const comps = new Set<number>();
  for (const n of graph.nodes) comps.add(n.component);
  if (comps.size <= 1) return;

  const holeComp = graph.nodes[holeId].component;
  const connected = new Set<number>([holeComp]);
  const remaining = new Set<number>(comps);
  remaining.delete(holeComp);

  // Pre-bucket nodes by component for the inner loop.
  const byComp = new Map<number, GraphNode[]>();
  for (const n of graph.nodes) {
    let arr = byComp.get(n.component);
    if (!arr) {
      arr = [];
      byComp.set(n.component, arr);
    }
    arr.push(n);
  }

  while (remaining.size > 0) {
    let bestA = -1;
    let bestB = -1;
    let bestDist = Infinity;
    let bestComp = -1;

    for (const cc of connected) {
      const aNodes = byComp.get(cc)!;
      for (const rc of remaining) {
        const bNodes = byComp.get(rc)!;
        for (const na of aNodes) {
          for (const nb of bNodes) {
            const d = Math.hypot(na.x - nb.x, na.y - nb.y);
            if (d < bestDist) {
              bestDist = d;
              bestA = na.id;
              bestB = nb.id;
              bestComp = rc;
            }
          }
        }
      }
    }

    if (bestA === -1) break;

    // Bridge weight = 0: the drain front passes instantaneously between
    // disconnected components at their closest-point pair. This makes
    // the front continuous (e.g. dot of an "i" finishes draining
    // exactly as the top of the stem starts). Using the euclidean
    // distance instead would insert a visible pause.
    const a = graph.nodes[bestA];
    const b = graph.nodes[bestB];
    const eid = graph.edges.length;
    graph.edges.push({
      id: eid,
      a: bestA,
      b: bestB,
      polyline: [
        [a.x, a.y],
        [b.x, b.y],
      ],
      length: 0,
      virtual: true,
    });
    graph.adj.get(bestA)!.push(eid);
    graph.adj.get(bestB)!.push(eid);

    connected.add(bestComp);
    remaining.delete(bestComp);
  }
}

/**
 * Dijkstra over the graph (real edges + virtual bridges). Linear-scan
 * priority queue is fine — graphs are tiny (<100 nodes per glyph).
 */
function dijkstra(graph: Graph, source: number): Map<number, number> {
  const dist = new Map<number, number>();
  for (const n of graph.nodes) dist.set(n.id, Infinity);
  dist.set(source, 0);

  const visited = new Set<number>();
  const queue: { id: number; d: number }[] = [{ id: source, d: 0 }];

  while (queue.length > 0) {
    let bestIdx = 0;
    for (let i = 1; i < queue.length; i++) {
      if (queue[i].d < queue[bestIdx].d) bestIdx = i;
    }
    const { id, d } = queue.splice(bestIdx, 1)[0];
    if (visited.has(id)) continue;
    visited.add(id);

    for (const eid of graph.adj.get(id)!) {
      const e = graph.edges[eid];
      if (e.removed) continue;
      const next = e.a === id ? e.b : e.a;
      const nd = d + e.length;
      if (nd < (dist.get(next) ?? Infinity)) {
        dist.set(next, nd);
        queue.push({ id: next, d: nd });
      }
    }
  }

  return dist;
}

function perpDist(
  p: [number, number],
  a: [number, number],
  b: [number, number],
): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(
    0,
    Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lenSq),
  );
  const px = a[0] + t * dx;
  const py = a[1] + t * dy;
  return Math.hypot(p[0] - px, p[1] - py);
}

/**
 * Iterative Ramer–Douglas–Peucker. Keeps endpoints; recursively keeps the
 * point furthest from the current segment if its distance exceeds eps.
 */
function simplifyRDP(pts: Stroke, eps: number): Stroke {
  if (pts.length < 3) return pts.slice();
  const keep = new Array<boolean>(pts.length).fill(false);
  keep[0] = true;
  keep[pts.length - 1] = true;

  const stack: Array<[number, number]> = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop()!;
    let maxD = 0;
    let maxI = -1;
    for (let i = a + 1; i < b; i++) {
      const d = perpDist(pts[i], pts[a], pts[b]);
      if (d > maxD) {
        maxD = d;
        maxI = i;
      }
    }
    if (maxD > eps && maxI !== -1) {
      keep[maxI] = true;
      stack.push([a, maxI], [maxI, b]);
    }
  }

  const out: Stroke = [];
  for (let i = 0; i < pts.length; i++) if (keep[i]) out.push(pts[i]);
  return out;
}
