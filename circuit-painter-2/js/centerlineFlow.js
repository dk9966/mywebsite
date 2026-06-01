// Turn the medial-axis centerlines into a direction field the greedy walker
// can follow. Each centerline segment has an axis (its grid direction); that
// axis is stamped into the flow grid along the segment and then spread outward
// with a linear falloff, so every free cell "knows" which way the nearest
// corridor runs. The walker reads this through getFlowStrength exactly like it
// reads mouse-painted flow -- so wires near the same corridor align onto its
// axis and bundle up.

import { params } from './params.js';
import { mapDirection8ToFlow4, addFlowStrength } from './flowGrid.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

// Closest of the 8 grid directions to the vector (dx, dy), by cosine. Returns
// -1 for a zero vector.
function segmentToDir8(dx, dy) {
    const len = Math.hypot(dx, dy);
    if (len === 0) return -1;
    const ux = dx / len;
    const uy = dy / len;
    let best = -1;
    let bestDot = -Infinity;
    for (let i = 0; i < 8; i++) {
        const [ex, ey] = DIRS[i];
        const el = Math.hypot(ex, ey);
        const dot = (ux * ex + uy * ey) / el;
        if (dot > bestDot) {
            bestDot = dot;
            best = i;
        }
    }
    return best;
}

// Bresenham cells from (x0,y0) to (x1,y1), inclusive.
function* lineCells(x0, y0, x1, y1) {
    let dx = Math.abs(x1 - x0);
    let dy = Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1;
    const sy = y0 < y1 ? 1 : -1;
    let err = dx - dy;
    let x = x0;
    let y = y0;
    while (true) {
        yield [x, y];
        if (x === x1 && y === y1) break;
        const e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x += sx; }
        if (e2 < dx) { err += dx; y += sy; }
    }
}

// Populate the flow grid from centerline polylines. `grid` gates the outward
// spread so a corridor's axis never leaks across an obstacle into the next gap.
export function applyCenterlineFlow(polylines, grid, gridWidth, gridHeight) {
    if (!params.alignToCenterlines || !polylines.length) return;

    const maxStr = clamp(params.centerlineStrength | 0, 0, 255);
    if (maxStr <= 0) return;
    const falloff = Math.max(1, params.centerlineFalloff | 0);

    const idx = (x, y) => x * gridHeight + y;
    const dirOf = new Int8Array(gridWidth * gridHeight).fill(-1);
    const strOf = new Uint8Array(gridWidth * gridHeight);
    const queue = [];

    for (const poly of polylines) {
        for (let i = 0; i < poly.length - 1; i++) {
            const [ax, ay] = poly[i];
            const [bx, by] = poly[i + 1];
            const d8 = segmentToDir8(bx - ax, by - ay);
            if (d8 < 0) continue;
            const bucket = mapDirection8ToFlow4(d8);

            for (const [cx, cy] of lineCells(ax | 0, ay | 0, bx | 0, by | 0)) {
                if (cx < 0 || cy < 0 || cx >= gridWidth || cy >= gridHeight) continue;
                const k = idx(cx, cy);
                if (strOf[k] >= maxStr) continue;
                strOf[k] = maxStr;
                dirOf[k] = bucket;
                queue.push(k);
            }
        }
    }

    let head = 0;
    while (head < queue.length) {
        const k = queue[head++];
        const next = strOf[k] - falloff;
        if (next <= 0) continue;
        const x = Math.floor(k / gridHeight);
        const y = k % gridHeight;
        for (let i = 0; i < 8; i++) {
            const nx = x + DIRS[i][0];
            const ny = y + DIRS[i][1];
            if (nx < 0 || ny < 0 || nx >= gridWidth || ny >= gridHeight) continue;
            if (!grid[nx][ny].available) continue;
            const nk = idx(nx, ny);
            if (strOf[nk] >= next) continue;
            strOf[nk] = next;
            dirOf[nk] = dirOf[k];
            queue.push(nk);
        }
    }

    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            const k = idx(x, y);
            if (strOf[k] > 0 && dirOf[k] >= 0) addFlowStrength(x, y, dirOf[k], strOf[k]);
        }
    }
}

function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
