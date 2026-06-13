// Bus mode: carve the free space into rectangular gaps, pack each gap with a
// tight set of parallel straight traces (a bus), then stitch the buses together
// with 45 degree slants so the whole board reads as one connected network.
//
// busSpineMode 'centerline' replaces gap-rect placement with corridor spines
// derived from the medial axis; slant connection is unchanged.

import { rndInt } from './rng.js';
import { params } from './params.js';
import { Wire, sanitizePathRightAngles } from './wire.js';
import { aStar } from './pathfind.js';
import {
    computeCorridorGeometry, computeRoutingClearance, packLinesOnEdge, edgeDebugRect,
} from './corridorGeom.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

const RECT_MARGIN = 2;

export function generateBuses(grid, W, H) {
    if (params.busSpineMode === 'centerline') {
        return generateCenterlineBuses(grid, W, H);
    }
    return generateGapRectBuses(grid, W, H);
}

function generateGapRectBuses(grid, W, H) {
    const rects = placeGapRects(grid, W, H);

    const wires = [];
    const lines = [];
    const lineRect = [];

    let rectId = 0;
    for (const r of rects) {
        for (const body of busBodies(r, orientationFor(r))) {
            const id = lineRect.length;
            const cells = stampLine(body, grid, rectId, id);
            if (cells.length < 2) continue;
            lineRect.push(rectId);
            wires.push(makeBusWire([cells[0], cells[cells.length - 1]], grid, W, H));
            lines.push({ id, ends: [cells[0], cells[cells.length - 1]], rectId });
        }
        rectId++;
    }

    if (params.connectBuses) connectBuses(lines, lineRect, grid, W, H, wires);

    return { rects, wires };
}

function generateCenterlineBuses(grid, W, H) {
    const { graph } = computeCorridorGeometry(W, H);
    const wires = [];
    const lines = [];
    const lineRect = [];
    const rects = [];

    let edgeId = 0;
    for (const edge of graph.edges) {
        rects.push(edgeDebugRect(edge));
        const bodies = packLinesOnEdge(edge, W, H);
        for (const body of bodies) {
            const id = lineRect.length;
            const cells = stampLineClipped(body, grid, edgeId, id);
            if (cells.length < 2) continue;
            lineRect.push(edgeId);
            wires.push(makeBusWire([cells[0], cells[cells.length - 1]], grid, W, H));
            lines.push({ id, ends: [cells[0], cells[cells.length - 1]], rectId: edgeId });
        }
        edgeId++;
    }

    if (params.connectBuses) connectBuses(lines, lineRect, grid, W, H, wires);

    return { rects, wires };
}

// === Gap rectangles ========================================================

function placeGapRects(grid, W, H) {
    const idx = (x, y) => x * H + y;
    const taken = new Uint8Array(W * H);
    for (let x = 0; x < W; x++) {
        for (let y = 0; y < H; y++) {
            if (!grid[x][y].available) taken[idx(x, y)] = 1;
        }
    }

    const minSize = Math.max(2, params.gapRectMinSize | 0);
    const maxSize = Math.max(minSize, params.gapRectMaxSize | 0);
    const cap = Math.max(0, params.gapRectCount | 0);
    const fullAfterMisses = 800;

    const rects = [];
    let misses = 0;
    while (rects.length < cap && misses < fullAfterMisses) {
        const sx = 1 + rndInt(Math.max(1, W - 2));
        const sy = 1 + rndInt(Math.max(1, H - 2));
        if (taken[idx(sx, sy)]) { misses++; continue; }

        const rect = growRect(sx, sy, taken, idx, W, H, maxSize);
        if (rect.w < minSize || rect.h < minSize) { misses++; continue; }

        markTaken(rect, taken, idx, W, H, RECT_MARGIN);
        rects.push(rect);
        misses = 0;
    }
    return rects;
}

function growRect(sx, sy, taken, idx, W, H, maxSize) {
    let w = 0;
    while (w < maxSize && sx + w < W - 1 && !taken[idx(sx + w, sy)]) w++;

    let h = 0;
    grow: while (h < maxSize && sy + h < H - 1) {
        for (let x = sx; x < sx + w; x++) {
            if (taken[idx(x, sy + h)]) break grow;
        }
        h++;
    }
    return { x: sx, y: sy, w, h };
}

function markTaken(r, taken, idx, W, H, margin) {
    const x0 = Math.max(0, r.x - margin);
    const y0 = Math.max(0, r.y - margin);
    const x1 = Math.min(W - 1, r.x + r.w + margin);
    const y1 = Math.min(H - 1, r.y + r.h + margin);
    for (let x = x0; x < x1; x++) {
        for (let y = y0; y < y1; y++) taken[idx(x, y)] = 1;
    }
}

function orientationFor(r) {
    const band = Math.max(4, Math.round((params.gapRectMinSize + params.gapRectMaxSize) / 2));
    const bx = Math.floor((r.x + r.w / 2) / band);
    const by = Math.floor((r.y + r.h / 2) / band);
    return ((bx + by) & 1) === 0 ? 'h' : 'v';
}

// === Bus bodies ============================================================

function busBodies(r, orient) {
    const step = Math.max(1, (params.busLineSpacing | 0) + 1);
    const inset = 1;
    const out = [];
    if (orient === 'h') {
        const x0 = r.x + inset;
        const x1 = r.x + r.w - 1 - inset;
        if (x1 - x0 < 1) return out;
        for (let y = r.y + inset; y <= r.y + r.h - 1 - inset; y += step) {
            out.push({ x0, y0: y, x1, y1: y });
        }
    } else {
        const y0 = r.y + inset;
        const y1 = r.y + r.h - 1 - inset;
        if (y1 - y0 < 1) return out;
        for (let x = r.x + inset; x <= r.x + r.w - 1 - inset; x += step) {
            out.push({ x0: x, y0, x1: x, y1 });
        }
    }
    return out;
}

function stampLine(b, grid, rectId, lineId) {
    const cells = [];
    const dx = Math.sign(b.x1 - b.x0);
    const dy = Math.sign(b.y1 - b.y0);
    let x = b.x0;
    let y = b.y0;
    while (true) {
        const c = grid[x][y];
        c.available = false;
        c.busRect = rectId;
        c.busLine = lineId;
        cells.push(c);
        if (x === b.x1 && y === b.y1) break;
        x += dx;
        y += dy;
    }
    return cells;
}

function stampLineClipped(b, grid, rectId, lineId) {
    const cells = [];
    const dx = Math.sign(b.x1 - b.x0);
    const dy = Math.sign(b.y1 - b.y0);
    let x = b.x0;
    let y = b.y0;
    while (true) {
        const c = grid[x][y];
        if (c.available) {
            c.available = false;
            c.busRect = rectId;
            c.busLine = lineId;
            cells.push(c);
        }
        if (x === b.x1 && y === b.y1) break;
        x += dx;
        y += dy;
    }
    return cells;
}

// === Connecting buses with slants ==========================================

function connectBuses(lines, lineRect, grid, W, H, wires) {
    const net = buildNet(grid, W, H);
    const reach = Math.max(6, (params.busTailLength | 0) * 3);
    const clearance = params.obstaclesEnabled ? computeRoutingClearance(W, H) : null;
    const slantOpts = clearance ? {
        clearance,
        clearanceTarget: params.routeClearanceTarget,
        clearanceWeight: params.routeClearanceBias,
    } : {};

    for (const L of lines) {
        for (const sameGapOk of [false, true]) {
            let connected = false;
            for (const end of L.ends) {
                const goal = goalCells(net, lineRect, L, sameGapOk);
                if (!goal.size) continue;
                const path = aStar(end, goal, grid, W, H, slantOpts);
                if (!path || path.length < 2 || path.length > reach) continue;
                sanitizePathRightAngles(path, grid, W, H);
                commitSlant(path, grid, W, H, net);
                wires.push(makeBusWire(path, grid, W, H));
                connected = true;
            }
            if (connected) break;
        }
    }
}

function buildNet(grid, W, H) {
    const net = new Map();
    for (let x = 0; x < W; x++) {
        for (let y = 0; y < H; y++) {
            const c = grid[x][y];
            if (c.busLine === undefined) continue;
            addNeighbours(c, c.busLine, grid, W, H, net);
        }
    }
    return net;
}

function addNeighbours(cell, lineId, grid, W, H, net) {
    for (let i = 0; i < 8; i++) {
        const nx = cell.x + DIRS[i][0];
        const ny = cell.y + DIRS[i][1];
        if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
        const n = grid[nx][ny];
        if (!n.available) continue;
        let s = net.get(n);
        if (!s) { s = new Set(); net.set(n, s); }
        s.add(lineId);
    }
}

function goalCells(net, lineRect, L, sameGapOk) {
    const goal = new Set();
    for (const [cell, ids] of net) {
        for (const lid of ids) {
            if (lid === L.id) continue;
            if (!sameGapOk && lineRect[lid] === L.rectId) continue;
            goal.add(cell);
            break;
        }
    }
    return goal;
}

function commitSlant(path, grid, W, H, net) {
    for (const c of path) c.available = false;
    for (const c of path) addNeighbours(c, -1, grid, W, H, net);
}

function makeBusWire(vertices, grid, W, H) {
    const wire = new Wire(vertices[0], grid, W, H);
    wire.cells = vertices;
    wire.isBus = true;
    return wire;
}
