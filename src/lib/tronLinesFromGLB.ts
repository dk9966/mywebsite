import * as THREE from "three";
import type { GridPath, Vec3 } from "./gridBuilder";

// Authored in Blender as edge-only meshes inside a `TronLines` collection,
// exported via glTF "Loose Edges". See plans/tron-lines-on-table.md.
//
// Name grammar:
//   TronLine_<order>_<delaySec>[_<tag>...]
//
// `order` is a sort hint; `delaySec` becomes GridPath.spawnTime.
const NAME_PREFIX = "TronLine_";

type ParsedName = {
  order: number;
  delaySec: number;
  tags: string[];
};

function parseTronLineName(name: string): ParsedName | null {
  if (!name.startsWith(NAME_PREFIX)) return null;
  const parts = name.slice(NAME_PREFIX.length).split("_");
  if (parts.length < 2) return null;

  const order = Number.parseInt(parts[0], 10);
  const delaySec = Number.parseFloat(parts[1]);
  if (!Number.isFinite(order) || !Number.isFinite(delaySec)) return null;

  return { order, delaySec, tags: parts.slice(2) };
}

// Reconstructs travel order from an edge-pair index buffer.
// Returns ordered vertex indices, or null if the graph is unusable.
function chainFromEdgePairs(
  index: ArrayLike<number>,
  vertexCount: number,
  nodeName: string,
): number[] | null {
  if (index.length < 2 || index.length % 2 !== 0) return null;

  const adj = new Map<number, number[]>();
  const addEdge = (a: number, b: number) => {
    if (!adj.has(a)) adj.set(a, []);
    adj.get(a)!.push(b);
  };
  for (let i = 0; i < index.length; i += 2) {
    const a = index[i];
    const b = index[i + 1];
    if (a === b) continue;
    addEdge(a, b);
    addEdge(b, a);
  }

  const endpoints: number[] = [];
  let branched = false;
  for (const [v, neighbors] of adj) {
    if (neighbors.length === 1) endpoints.push(v);
    if (neighbors.length > 2) branched = true;
  }

  if (branched) {
    console.warn(
      `[tronLinesFromGLB] "${nodeName}" has branching vertices; walking the longest chain only.`,
    );
  }

  let start: number;
  if (endpoints.length >= 1) {
    start = endpoints[0];
  } else if (adj.size > 0) {
    console.warn(
      `[tronLinesFromGLB] "${nodeName}" is a closed loop or has no clear start; using vertex 0.`,
    );
    start = adj.keys().next().value as number;
  } else {
    return null;
  }

  const chain: number[] = [start];
  const visited = new Set<number>([start]);
  let current = start;

  for (;;) {
    const neighbors = adj.get(current);
    if (!neighbors) break;
    const next = neighbors.find((n) => !visited.has(n));
    if (next === undefined) break;
    chain.push(next);
    visited.add(next);
    current = next;
  }

  if (chain.length < 2 || chain.some((idx) => idx < 0 || idx >= vertexCount)) {
    return null;
  }

  return chain;
}

function extractOrderedWaypoints(line: THREE.Object3D): Vec3[] | null {
  const geo = (line as THREE.Mesh).geometry as THREE.BufferGeometry | undefined;
  if (!geo) return null;

  const posAttr = geo.getAttribute("position") as THREE.BufferAttribute | undefined;
  if (!posAttr) return null;

  const vertexCount = posAttr.count;
  if (vertexCount < 2) return null;

  const indexAttr = geo.getIndex();
  const indexArray: ArrayLike<number> = indexAttr
    ? indexAttr.array
    : sequentialPairs(vertexCount);

  const chain = chainFromEdgePairs(indexArray, vertexCount, line.name);
  if (!chain) return null;

  line.updateMatrixWorld(true);
  const m = line.matrixWorld;
  const v = new THREE.Vector3();
  const out: Vec3[] = new Array(chain.length);
  for (let i = 0; i < chain.length; i++) {
    const idx = chain[i];
    v.fromBufferAttribute(posAttr, idx).applyMatrix4(m);
    out[i] = [v.x, v.y, v.z];
  }
  return out;
}

// Fallback for the unusual non-indexed case: treat every adjacent pair of
// vertices as an edge, matching glTF LINES semantics.
function sequentialPairs(count: number): number[] {
  const pairs: number[] = [];
  for (let i = 0; i + 1 < count; i += 2) {
    pairs.push(i, i + 1);
  }
  return pairs;
}

export function tronLinesFromGLB(root: THREE.Object3D): GridPath[] {
  const paths: Array<GridPath & { _order: number }> = [];

  root.traverse((obj) => {
    const parsed = parseTronLineName(obj.name);
    if (!parsed) return;

    const waypoints = extractOrderedWaypoints(obj);
    if (!waypoints) {
      console.warn(`[tronLinesFromGLB] skipping "${obj.name}" (no usable polyline geometry).`);
      return;
    }

    paths.push({
      waypoints,
      spawnTime: parsed.delaySec,
      _order: parsed.order,
    });
  });

  paths.sort((a, b) => a.spawnTime - b.spawnTime || a._order - b._order);
  return paths.map(({ _order: _, ...p }) => p);
}
