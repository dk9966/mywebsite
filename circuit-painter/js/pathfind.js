// A* over the wire grid. Used by bus mode to stitch bus segments.
//
// Pin-bus routing runs in a Web Worker via pathfindClient.js; this module
// serves the lighter bus-mode slant connections.

import { params } from './params.js';
import { aStarCore } from './pathfindCore.js';

export function aStar(start, end, grid, gridWidth, gridHeight, options = {}) {
    const goalSet = end instanceof Set ? end : null;
    const isGoal = (cell) => (goalSet ? goalSet.has(cell) : cell === end);

    if (goalSet) {
        if (goalSet.size === 0) return null;
        if (goalSet.has(start)) return [start];
    } else {
        if (start === end) return [start];
        if (!end.available) return null;
    }

    const { available, headings } = snapshotGrid(grid, gridWidth, gridHeight);

    const run = (from, to, opts) => {
        const path = aStarCore(
            available,
            headings,
            gridWidth,
            gridHeight,
            { x: from.x, y: from.y },
            { x: to.x, y: to.y },
            {
                ...opts,
                turnSmoothness: params.turnSmoothness,
                diagonalChance: params.diagonalChance,
            },
        );
        return path ? path.map(({ x, y }) => grid[x][y]) : null;
    };

    if (goalSet) {
        // Dijkstra over multiple goals — rare, small searches in bus mode.
        return aStarMultiGoal(start, goalSet, grid, gridWidth, gridHeight, options);
    }

    return run(start, end, options);
}

function snapshotGrid(grid, gridWidth, gridHeight) {
    const n = gridWidth * gridHeight;
    const available = new Uint8Array(n);
    const headings = new Int8Array(n);
    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            const i = x * gridHeight + y;
            const c = grid[x][y];
            available[i] = c.available ? 1 : 0;
            headings[i] = c.heading;
        }
    }
    return { available, headings };
}

// Multi-goal search kept inline for bus.js Set goals — simpler than serializing Sets.
function aStarMultiGoal(start, goalSet, grid, gridWidth, gridHeight, options) {
    const bundleBonus = Math.max(0, options.bundle || 0);
    const turnPenalty = params.turnSmoothness * (gridWidth + gridHeight);
    const dc = params.diagonalChance < 0 ? 0 : params.diagonalChance > 1 ? 1 : params.diagonalChance;
    const diagCost = Math.SQRT2 + (1 - dc) * 2.5;

    const DIRS = [
        [-1, -1], [0, -1], [1, -1], [1, 0],
        [1, 1], [0, 1], [-1, 1], [-1, 0],
    ];

    class MinHeap {
        constructor() { this.items = []; }
        get size() { return this.items.length; }
        push(item) {
            this.items.push(item);
            let i = this.items.length - 1;
            while (i > 0) {
                const p = (i - 1) >> 1;
                if (this.items[i].f < this.items[p].f) {
                    [this.items[i], this.items[p]] = [this.items[p], this.items[i]];
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
                    [this.items[i], this.items[m]] = [this.items[m], this.items[i]];
                    i = m;
                }
            }
            return top;
        }
    }

    const keyOf = (c, dir) => c.x * gridHeight + c.y + (turnPenalty > 0 ? (dir + 1) * gridWidth * gridHeight : 0);
    const bestG = new Map();
    const parentOf = new Map();
    const open = new MinHeap();
    const startKey = keyOf(start, -1);
    bestG.set(startKey, 0);
    open.push({ f: 0, g: 0, cell: start, dir: -1, key: startKey });

    let expansions = 0;
    const maxExpansions = options.maxExpansions || gridWidth * gridHeight * 4;

    while (open.size > 0) {
        const node = open.pop();
        if (node.g !== bestG.get(node.key)) continue;
        if (++expansions > maxExpansions) return null;
        if (goalSet.has(node.cell)) {
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

            const isDiag = dx !== 0 && dy !== 0;
            if (isDiag) {
                const o1 = grid[node.cell.x + dx][node.cell.y];
                const o2 = grid[node.cell.x][node.cell.y + dy];
                if (!o1.available && !o2.available) continue;
            }

            let stepCost = isDiag ? diagCost : 1;
            if (node.dir !== -1) {
                const delta = (i - node.dir + 8) % 8;
                if (delta >= 2 && delta <= 6) continue;
            }

            let bundle = 0;
            if (bundleBonus > 0) {
                for (const perp of [(i + 2) % 8, (i + 6) % 8]) {
                    const sx = nx + DIRS[perp][0];
                    const sy = ny + DIRS[perp][1];
                    if (sx < 0 || sx >= gridWidth || sy < 0 || sy >= gridHeight) continue;
                    const side = grid[sx][sy];
                    if (!side.available && (side.heading === i || side.heading === (i + 4) % 8)) {
                        bundle = bundleBonus;
                        break;
                    }
                }
            }

            const g = node.g + stepCost - bundle;
            const nKey = keyOf(ncell, i);
            const prevBest = bestG.get(nKey);
            if (prevBest !== undefined && prevBest <= g) continue;

            bestG.set(nKey, g);
            parentOf.set(nKey, { cell: node.cell, dir: node.dir });
            open.push({ f: g, g, cell: ncell, dir: i, key: nKey });
        }
    }
    return null;
}
