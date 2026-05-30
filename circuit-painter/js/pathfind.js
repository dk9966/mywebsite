// A* over the wire grid. Used to lay "trunk" lines that span the canvas
// edge-to-edge -- the random walker in wire.js can't guarantee reaching a
// specific destination, so anything that needs to look like a long bus
// running off the board comes through here.
//
// Conventions:
//   * `available === false` cells are walls (obstacle cells, QFP pin cells,
//     and cells already taken by another wire).
//   * Diagonal moves are allowed but a diagonal can't slice between two
//     blocked cells -- same rule the random walker enforces, so paths can
//     never visually cross another trace.

import { rndInt } from './rng.js';
import { params } from './params.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

// Tiny binary min-heap keyed by `.f`. Stays small; we never need to update
// in place because A*'s stale-entry guard (best-g check) does that lazily.
class MinHeap {
    constructor() { this.items = []; }
    get size() { return this.items.length; }

    push(item) {
        this.items.push(item);
        let i = this.items.length - 1;
        while (i > 0) {
            const p = (i - 1) >> 1;
            if (this.items[i].f < this.items[p].f) {
                const t = this.items[i];
                this.items[i] = this.items[p];
                this.items[p] = t;
                i = p;
            } else break;
        }
    }

    pop() {
        if (!this.items.length) return null;
        const top = this.items[0];
        const last = this.items.pop();
        if (this.items.length) {
            this.items[0] = last;
            const n = this.items.length;
            let i = 0;
            while (true) {
                const l = 2 * i + 1;
                const r = 2 * i + 2;
                let m = i;
                if (l < n && this.items[l].f < this.items[m].f) m = l;
                if (r < n && this.items[r].f < this.items[m].f) m = r;
                if (m === i) break;
                const t = this.items[i];
                this.items[i] = this.items[m];
                this.items[m] = t;
                i = m;
            }
        }
        return top;
    }
}

// Chebyshev distance is admissible because diagonals cost the same number of
// "moves" as cardinals; we use a 1 vs sqrt(2) step cost to keep A* honest
// about real path length, but the heuristic only needs the move count.
function chebyshev(a, b) {
    return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}

export function aStar(start, end, grid, gridWidth, gridHeight) {
    if (start === end) return [start];
    if (!start.available || !end.available) return null;

    // A 90 degree corner costs this much extra g. Scaled so that at
    // turnSmoothness === 1 a single right angle is pricier than any detour the
    // board could offer, so A* takes a 45 degree diagonal staircase wherever one
    // exists and only falls back to a right angle when geometry leaves no choice
    // (which keeps trunks from failing on a tightly packed board).
    const turnPenalty = params.turnSmoothness * (gridWidth + gridHeight);

    // When charging a turn penalty, the cost to reach a cell depends on the
    // heading we arrived with, so the search state is (cell, incoming dir).
    // Otherwise direction is irrelevant and we collapse back to one state per
    // cell -- identical to the plain grid A* and just as cheap. dir === -1 marks
    // the start, which is exempt from the first turn charge.
    const trackDir = turnPenalty > 0;
    const keyOf = (c, dir) => {
        const base = c.x * gridHeight + c.y;
        return trackDir ? base * 9 + (dir + 1) : base;
    };

    const bestG = new Map();
    const parentOf = new Map();
    const open = new MinHeap();

    const startKey = keyOf(start, -1);
    bestG.set(startKey, 0);
    open.push({ f: chebyshev(start, end), g: 0, cell: start, dir: -1, key: startKey });

    while (open.size > 0) {
        const node = open.pop();
        // Stale entry: a cheaper path to this state was found after we
        // pushed this one. Skip without touching closed/parent state.
        if (node.g !== bestG.get(node.key)) continue;

        if (node.cell === end) {
            const path = [];
            let key = node.key;
            let info = { cell: node.cell, dir: node.dir };
            while (info) {
                path.unshift(info.cell);
                const parent = parentOf.get(key);
                if (!parent) break;
                key = keyOf(parent.cell, parent.dir);
                info = parent;
            }
            return path;
        }

        for (let i = 0; i < 8; i++) {
            const [dx, dy] = DIRS[i];
            const nx = node.cell.x + dx;
            const ny = node.cell.y + dy;
            if (nx < 0 || nx >= gridWidth || ny < 0 || ny >= gridHeight) continue;

            const ncell = grid[nx][ny];
            if (!ncell.available) continue;

            if (dx !== 0 && dy !== 0) {
                const ortho1 = grid[node.cell.x + dx][node.cell.y];
                const ortho2 = grid[node.cell.x][node.cell.y + dy];
                if (!ortho1.available && !ortho2.available) continue;
            }

            let turn = 0;
            if (node.dir !== -1 && turnPenalty > 0) {
                const delta = (i - node.dir + 8) % 8;
                if (delta === 2 || delta === 6) turn = turnPenalty;
            }

            const stepCost = (dx !== 0 && dy !== 0) ? Math.SQRT2 : 1;
            const g = node.g + stepCost + turn;
            const nKey = keyOf(ncell, i);
            const prevBest = bestG.get(nKey);
            if (prevBest !== undefined && prevBest <= g) continue;

            bestG.set(nKey, g);
            parentOf.set(nKey, { cell: node.cell, dir: node.dir });
            open.push({ f: g + chebyshev(ncell, end), g, cell: ncell, dir: i, key: nKey });
        }
    }
    return null;
}

// Pick a free cell on a random edge. `side`: 0=top, 1=right, 2=bottom, 3=left.
export function pickEdgeCell(grid, gridWidth, gridHeight) {
    const sides = [0, 1, 2, 3];
    while (sides.length) {
        const side = sides.splice(rndInt(sides.length), 1)[0];
        const candidates = edgeCellsOf(side, grid, gridWidth, gridHeight)
            .filter((c) => c.available);
        if (candidates.length) {
            return { cell: candidates[rndInt(candidates.length)], side };
        }
    }
    return null;
}

// Free cell on the side opposite `excludeSide`. Falls back to the perpendicular
// sides before giving up so we can still produce *some* trunk on a heavily
// blocked board.
export function pickOppositeEdgeCell(excludeSide, grid, gridWidth, gridHeight) {
    const opposite = (excludeSide + 2) % 4;
    const tryOrder = [opposite, (excludeSide + 1) % 4, (excludeSide + 3) % 4];
    for (const side of tryOrder) {
        const candidates = edgeCellsOf(side, grid, gridWidth, gridHeight)
            .filter((c) => c.available);
        if (candidates.length) return candidates[rndInt(candidates.length)];
    }
    return null;
}

function edgeCellsOf(side, grid, gridWidth, gridHeight) {
    const cells = [];
    if (side === 0) {
        for (let x = 0; x < gridWidth; x++) cells.push(grid[x][0]);
    } else if (side === 1) {
        for (let y = 0; y < gridHeight; y++) cells.push(grid[gridWidth - 1][y]);
    } else if (side === 2) {
        for (let x = 0; x < gridWidth; x++) cells.push(grid[x][gridHeight - 1]);
    } else {
        for (let y = 0; y < gridHeight; y++) cells.push(grid[0][y]);
    }
    return cells;
}
