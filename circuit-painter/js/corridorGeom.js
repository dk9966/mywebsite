// Shared corridor geometry: blocked grid, distance transform, skeleton,
// corridor graph cleanup, and centerline polylines.
//
// Top-level helpers accept an optional `cfg` so circuit-painter-2 can pass its
// own obstacles/params without sharing module state with circuit-painter.

import TraceSkeleton from 'skeleton-tracing-js';
import { params as defaultParams } from './params.js';
import { getObstacles as defaultGetObstacles } from './obstacles.js';

export function idx(x, y, H) {
    return x * H + y;
}

function resolveCfg(cfg = {}) {
    const obstacles = cfg.obstacles ?? defaultGetObstacles();
    const p = { ...defaultParams, ...cfg };
    return { obstacles, p };
}

export function buildBlocked(gridWidth, gridHeight, cfg) {
    const { obstacles, p } = resolveCfg(cfg);
    const blocked = new Uint8Array(gridWidth * gridHeight);
    const blockBuffer = Math.max(0, p.obstacleKeepOut | 0);

    for (let x = 0; x < gridWidth; x++) {
        blocked[idx(x, 0, gridHeight)] = 1;
        blocked[idx(x, gridHeight - 1, gridHeight)] = 1;
    }
    for (let y = 0; y < gridHeight; y++) {
        blocked[idx(0, y, gridHeight)] = 1;
        blocked[idx(gridWidth - 1, y, gridHeight)] = 1;
    }

    for (const o of obstacles) {
        const buffer = o.qfp ? 0 : blockBuffer;
        for (let x = o.x - buffer; x < o.x + o.w + buffer; x++) {
            for (let y = o.y - buffer; y < o.y + o.h + buffer; y++) {
                if (x < 0 || y < 0 || x >= gridWidth || y >= gridHeight) continue;
                blocked[idx(x, y, gridHeight)] = 1;
            }
        }
    }

    return blocked;
}

export function computeDistanceTransform(blocked, W, H) {
    const dist = new Int32Array(W * H);
    dist.fill(-1);
    const queue = [];

    for (let x = 0; x < W; x++) {
        for (let y = 0; y < H; y++) {
            if (!blocked[idx(x, y, H)]) continue;
            const i = idx(x, y, H);
            dist[i] = 0;
            queue.push(i);
        }
    }

    let head = 0;
    while (head < queue.length) {
        const i = queue[head++];
        const x = Math.floor(i / H);
        const y = i % H;
        const d = dist[i];

        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                if (dx === 0 && dy === 0) continue;
                const nx = x + dx;
                const ny = y + dy;
                if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
                const ni = idx(nx, ny, H);
                if (blocked[ni] || dist[ni] !== -1) continue;
                dist[ni] = d + 1;
                queue.push(ni);
            }
        }
    }

    for (let i = 0; i < dist.length; i++) {
        if (dist[i] === -1) dist[i] = 0;
    }
    return dist;
}

function blockedToImageData(blocked, W, H) {
    const data = new Uint8ClampedArray(W * H * 4);
    for (let x = 0; x < W; x++) {
        for (let y = 0; y < H; y++) {
            const i = (y * W + x) * 4;
            const v = blocked[idx(x, y, H)] ? 0 : 255;
            data[i] = v;
            data[i + 1] = v;
            data[i + 2] = v;
            data[i + 3] = 255;
        }
    }
    return new ImageData(data, W, H);
}

export function computeSkeletonPolylines(blocked, W, H) {
    const imageData = blockedToImageData(blocked, W, H);
    const traced = TraceSkeleton.fromImageData(imageData);
    return traced.polylines.map((poly) => poly.map((pt) => [pt[0], pt[1]]));
}

function polylineLength(pts) {
    let len = 0;
    for (let i = 1; i < pts.length; i++) {
        len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    }
    return len;
}

function perpDist(p, a, b) {
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
    const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lenSq));
    return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

export function simplifyRDP(pts, eps) {
    if (pts.length < 3) return pts.slice();
    const keep = new Array(pts.length).fill(false);
    keep[0] = true;
    keep[pts.length - 1] = true;
    const stack = [[0, pts.length - 1]];

    while (stack.length) {
        const [a, b] = stack.pop();
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

    const out = [];
    for (let i = 0; i < pts.length; i++) if (keep[i]) out.push(pts[i]);
    return out;
}

function key(x, y) {
    return `${x},${y}`;
}

function parseKey(k) {
    const [x, y] = k.split(',').map(Number);
    return [x, y];
}

function buildSkeletonAdj(polylines, W, H) {
    const points = new Set();
    for (const poly of polylines) {
        for (const [x, y] of poly) points.add(key(x, y));
    }

    const adj = new Map();
    for (const k of points) {
        const [x, y] = parseKey(k);
        const neighbors = [];
        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                if (dx === 0 && dy === 0) continue;
                const nk = key(x + dx, y + dy);
                if (points.has(nk)) neighbors.push(nk);
            }
        }
        adj.set(k, neighbors);
    }
    return adj;
}

function removeNode(adj, k) {
    const neighbors = adj.get(k) || [];
    for (const n of neighbors) {
        const list = adj.get(n);
        if (!list) continue;
        const i = list.indexOf(k);
        if (i !== -1) list.splice(i, 1);
    }
    adj.delete(k);
}

function walkSpur(start, adj) {
    const chain = [start];
    let prev = null;
    let cur = start;
    while (true) {
        const neighbors = (adj.get(cur) || []).filter((n) => n !== prev);
        if (neighbors.length !== 1) break;
        prev = cur;
        cur = neighbors[0];
        chain.push(cur);
    }
    return chain;
}

function pruneSpurs(adj, minLen) {
    let changed = true;
    while (changed) {
        changed = false;
        for (const k of [...adj.keys()]) {
            const neighbors = adj.get(k) || [];
            if (neighbors.length !== 1) continue;
            const spur = walkSpur(k, adj);
            if (spur.length < minLen) {
                for (const node of spur) removeNode(adj, node);
                changed = true;
            }
        }
    }
}

function isNode(k, adj) {
    const deg = (adj.get(k) || []).length;
    return deg !== 2;
}

function edgeKey(a, b) {
    return a < b ? `${a}|${b}` : `${b}|${a}`;
}

function dominantAxis(polyline) {
    let hRun = 0;
    let vRun = 0;
    for (let i = 1; i < polyline.length; i++) {
        hRun += Math.abs(polyline[i][0] - polyline[i - 1][0]);
        vRun += Math.abs(polyline[i][1] - polyline[i - 1][1]);
    }
    return hRun >= vRun ? 'h' : 'v';
}

function insetPolyline(polyline, inset) {
    if (polyline.length < 2 || inset <= 0) return polyline.slice();
    const n = polyline.length;
    const start = Math.min(inset, n - 2);
    const end = Math.max(start + 1, n - 1 - inset);
    if (end <= start) return [polyline[Math.floor(n / 2)]];
    return polyline.slice(start, end + 1);
}

function minDistOnPolyline(polyline, dist, H) {
    let min = Infinity;
    for (const [x, y] of polyline) {
        const d = dist[idx(x, y, H)];
        if (d < min) min = d;
    }
    return min;
}

function edgeBounds(polyline) {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const [x, y] of polyline) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
    }
    return { minX, minY, maxX, maxY };
}

export function buildCorridorGraph(polylines, dist, W, H, opts = {}) {
    const { p } = resolveCfg(opts);
    const minLen = Math.max(1, opts.minLength ?? p.centerlineMinLength ?? 3);
    const inset = Math.max(0, opts.junctionInset ?? p.corridorJunctionInset ?? 2);
    const adj = buildSkeletonAdj(polylines, W, H);
    pruneSpurs(adj, minLen);

    const edges = [];
    const visited = new Set();

    for (const start of adj.keys()) {
        if (!isNode(start, adj)) continue;
        for (const n of adj.get(start) || []) {
            const ek = edgeKey(start, n);
            if (visited.has(ek)) continue;
            visited.add(ek);

            const polyline = [parseKey(start)];
            let prev = start;
            let cur = n;
            while (!isNode(cur, adj)) {
                polyline.push(parseKey(cur));
                const next = (adj.get(cur) || []).find((x) => x !== prev);
                if (!next) break;
                prev = cur;
                cur = next;
            }
            polyline.push(parseKey(cur));

            if (polyline.length < 2) continue;
            const trimmed = insetPolyline(polyline, inset);
            if (trimmed.length < 2) continue;
            if (polylineLength(trimmed) < minLen) continue;

            edges.push({
                polyline: trimmed,
                orient: dominantAxis(trimmed),
                halfWidth: minDistOnPolyline(trimmed, dist, H),
            });
        }
    }

    return { edges };
}

export function packLinesOnEdge(edge, W, H, cfg) {
    const { p } = resolveCfg(cfg);
    const step = Math.max(1, (p.busLineSpacing | 0) + 1);
    const margin = 1;
    const maxLines = Math.max(1, p.corridorMaxLines | 0);
    const halfWidth = edge.halfWidth;
    if (halfWidth < 1) return [];

    const lineCount = Math.min(
        maxLines,
        Math.max(1, Math.floor((2 * halfWidth - margin) / step)),
    );
    const offsets = centeredOffsets(lineCount, step);
    const bounds = edgeBounds(edge.polyline);
    const bodies = [];

    if (edge.orient === 'h') {
        const centerY = Math.round(
            edge.polyline.reduce((s, p) => s + p[1], 0) / edge.polyline.length,
        );
        const x0 = bounds.minX + margin;
        const x1 = bounds.maxX - margin;
        if (x1 - x0 < 1) return [];
        for (const off of offsets) {
            bodies.push({ x0, y0: centerY + off, x1, y1: centerY + off });
        }
    } else {
        const centerX = Math.round(
            edge.polyline.reduce((s, p) => s + p[0], 0) / edge.polyline.length,
        );
        const y0 = bounds.minY + margin;
        const y1 = bounds.maxY - margin;
        if (y1 - y0 < 1) return [];
        for (const off of offsets) {
            bodies.push({ x0: centerX + off, y0, x1: centerX + off, y1 });
        }
    }

    return bodies;
}

function centeredOffsets(count, step) {
    if (count <= 1) return [0];
    const out = [];
    const half = (count - 1) / 2;
    for (let i = 0; i < count; i++) {
        out.push(Math.round((i - half) * step));
    }
    return out;
}

export function edgeDebugRect(edge) {
    const b = edgeBounds(edge.polyline);
    return {
        x: b.minX,
        y: b.minY,
        w: b.maxX - b.minX + 1,
        h: b.maxY - b.minY + 1,
    };
}

export function computeCenterlinePolylines(gridWidth, gridHeight, cfg) {
    const { p } = resolveCfg(cfg);
    if (!p.obstaclesEnabled) return [];

    const blocked = buildBlocked(gridWidth, gridHeight, cfg);
    const raw = computeSkeletonPolylines(blocked, gridWidth, gridHeight);
    const minLen = Math.max(1, p.centerlineMinLength | 0);
    const eps = Math.max(0, p.centerlineSimplify ?? 0);
    const polylines = [];

    for (const poly of raw) {
        if (poly.length < 2) continue;
        const simplified = eps > 0 ? simplifyRDP(poly, eps) : poly.slice();
        if (polylineLength(simplified) < minLen) continue;
        polylines.push(simplified);
    }

    return polylines;
}

export function computeCorridorGeometry(gridWidth, gridHeight, cfg) {
    const { p } = resolveCfg(cfg);
    const blocked = buildBlocked(gridWidth, gridHeight, cfg);
    const dist = computeDistanceTransform(blocked, gridWidth, gridHeight);
    const raw = computeSkeletonPolylines(blocked, gridWidth, gridHeight);
    const eps = Math.max(0, p.centerlineSimplify ?? 0);
    const simplified = raw
        .map((poly) => (eps > 0 ? simplifyRDP(poly, eps) : poly.slice()))
        .filter((poly) => poly.length >= 2);
    const graph = buildCorridorGraph(simplified, dist, gridWidth, gridHeight, cfg);
    return { blocked, dist, graph };
}
