// Bus mode: fill the gaps between obstacles with rectangles of parallel
// traces.
//
// Two steps, kept independent so each is easy to reason about:
//   1. placeGapRects -- carve large, non-overlapping rectangles out of the
//      free space (cells the obstacle pass left available).
//   2. buildBus      -- pack each rectangle with parallel straight lines. Every
//      line gets a 45 degree tail on each end (a straight body meeting a
//      diagonal is a 45 degree bend, never a 90). Adjacent rects alternate
//      orientation in a checkerboard, so a horizontal bus's down-right tails
//      run parallel to its vertical neighbor's lines and the two link up across
//      the gap.
//
// Lines are emitted as Wire objects carrying only their vertices (corners);
// the renderer strokes straight segments between them, so no per-cell walk is
// needed.

import { rndInt } from './rng.js';
import { params } from './params.js';
import { Wire } from './wire.js';

export function generateBuses(grid, gridWidth, gridHeight) {
    const rects = placeGapRects(grid, gridWidth, gridHeight);
    const wires = [];
    for (const r of rects) {
        buildBus(r, orientationFor(r), grid, gridWidth, gridHeight, wires);
    }
    return { rects, wires };
}

// Greedy maximal-rectangle placement. Each attempt drops a random seed on a
// free cell, grows a rectangle right-then-down until it hits something taken,
// and keeps it if it cleared the minimum size. Taken cells (obstacles + already
// placed rects) are tracked in a flat byte grid so growth and overlap are O(1)
// per cell.
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
    // gapRectCount is an upper bound. We otherwise keep dropping rects until a
    // long run of misses shows the free space is essentially full -- this packs
    // the board densely instead of quitting early when random seeds get unlucky.
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

        for (let x = rect.x; x < rect.x + rect.w; x++) {
            for (let y = rect.y; y < rect.y + rect.h; y++) taken[idx(x, y)] = 1;
        }
        rects.push(rect);
        misses = 0;
    }
    return rects;
}

// Grow a rectangle anchored at (sx, sy) as its top-left corner: extend the
// width while the seed row stays free, then extend the height while every
// column in that width stays free. Bounded by maxSize and the board edge.
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

// Checkerboard orientation keyed on the rect's center, so neighbours alternate
// horizontal/vertical and the board's overall direction keeps changing. The
// band size is roughly a typical rect, so adjacent rects usually land in
// different bands.
function orientationFor(r) {
    const band = Math.max(4, Math.round((params.gapRectMinSize + params.gapRectMaxSize) / 2));
    const bx = Math.floor((r.x + r.w / 2) / band);
    const by = Math.floor((r.y + r.h / 2) / band);
    return ((bx + by) & 1) === 0 ? 'h' : 'v';
}

function buildBus(r, orient, grid, W, H, out) {
    const step = Math.max(1, (params.busLineSpacing | 0) + 1);
    const inset = 1;
    const tail = params.connectBuses ? Math.max(0, params.busTailLength | 0) : 0;

    if (orient === 'h') {
        const x0 = r.x + inset;
        const x1 = r.x + r.w - 1 - inset;
        if (x1 - x0 < 2) return;
        for (let y = r.y + inset; y <= r.y + r.h - 1 - inset; y += step) {
            out.push(makeBusLine(lineH(x0, x1, y, tail, grid, W, H), grid, W, H));
        }
    } else {
        const y0 = r.y + inset;
        const y1 = r.y + r.h - 1 - inset;
        if (y1 - y0 < 2) return;
        for (let x = r.x + inset; x <= r.x + r.w - 1 - inset; x += step) {
            out.push(makeBusLine(lineV(x, y0, y1, tail, grid, W, H), grid, W, H));
        }
    }
}

// Horizontal line from x0 to x1 at row y, with up-left and down-right 45 degree
// tails. Both tails shear the same way so all lines in the bus stay parallel.
function lineH(x0, x1, y, tail, grid, W, H) {
    const a = diagTail(x0, y, -1, -1, tail, grid, W, H);
    const b = diagTail(x1, y, 1, 1, tail, grid, W, H);
    const v = [];
    if (a.x !== x0 || a.y !== y) v.push(a);
    v.push({ x: x0, y }, { x: x1, y });
    if (b.x !== x1 || b.y !== y) v.push(b);
    return v;
}

function lineV(x, y0, y1, tail, grid, W, H) {
    const a = diagTail(x, y0, -1, -1, tail, grid, W, H);
    const b = diagTail(x, y1, 1, 1, tail, grid, W, H);
    const v = [];
    if (a.x !== x || a.y !== y0) v.push(a);
    v.push({ x, y: y0 }, { x, y: y1 });
    if (b.x !== x || b.y !== y1) v.push(b);
    return v;
}

// Walk diagonally from (fromX, fromY) up to `len` cells, stopping at the board
// edge or the first obstacle so a tail never cuts through a chip. Returns the
// farthest cell reached (equal to the start if blocked immediately).
function diagTail(fromX, fromY, dirX, dirY, len, grid, W, H) {
    let x = fromX;
    let y = fromY;
    for (let i = 0; i < len; i++) {
        const nx = x + dirX;
        const ny = y + dirY;
        if (nx < 1 || nx > W - 2 || ny < 1 || ny > H - 2) break;
        if (!grid[nx][ny].available) break;
        x = nx;
        y = ny;
    }
    return { x, y };
}

function makeBusLine(vertices, grid, W, H) {
    const wire = new Wire(vertices[0], grid, W, H);
    wire.cells = vertices;
    wire.isBus = true;
    return wire;
}
