// Pure A* on flat grid buffers. Shared by the main thread wrapper and the
// pathfind worker — no Cell objects, no DOM, no params import.

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

// On the 8-dir wheel, heading changes of ±1 (45°) give interior corners > 90°.
// Changes of 2–6 give interior angles ≤ 90° (right, acute, or reverse).
export function turnDelta(fromDir, toDir) {
    return (toDir - fromDir + 8) % 8;
}

export function isSharpCorner(fromDir, toDir) {
    if (fromDir < 0) return false;
    const delta = turnDelta(fromDir, toDir);
    return delta >= 2 && delta <= 6;
}

/** DIRS indices to step from a corner cell when replacing a sharp turn. */
export function chamferDirsForCorner(fromDir, toDir) {
    const delta = turnDelta(fromDir, toDir);
    if (delta === 2) return [(fromDir + 1) % 8];
    if (delta === 6) return [(fromDir + 7) % 8];
    if (delta === 3) return [(fromDir + 1) % 8, (fromDir + 2) % 8];
    if (delta === 5) return [(fromDir + 7) % 8, (fromDir + 6) % 8];
    if (delta === 4) return [(fromDir + 1) % 8, (fromDir + 7) % 8];
    return [];
}

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

function chebyshev(a, b) {
    return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}

function idx(x, y, gridHeight) {
    return x * gridHeight + y;
}

function cellAt(available, x, y, gridWidth, gridHeight) {
    if (x < 0 || x >= gridWidth || y < 0 || y >= gridHeight) return null;
    return available[idx(x, y, gridHeight)] !== 0;
}

// `available` and `headings` are mutated in place by callers that mark cells
// taken. `start`/`end` are {x,y}. Returns [{x,y}, ...] or null.
export function aStarCore(available, headings, gridWidth, gridHeight, start, end, options = {}) {
    const endIdx = idx(end.x, end.y, gridHeight);
    if (start.x === end.x && start.y === end.y) return [start];
    if (!available[endIdx]) return null;

    const bundleBonus = Math.max(0, options.bundle || 0);
    const onlyObtuse = !!options.onlyObtuse;
    const segMin = Math.max(0, options.segMin || 0);
    const hardSegMin = !!options.hardSegMin;
    const segMax = options.segMax > 0 ? options.segMax : Infinity;
    const segPenalty = options.segPenalty != null ? options.segPenalty : 3;
    const startDir = Number.isInteger(options.startDir) ? options.startDir : -1;
    const shaping = onlyObtuse || segMin > 0 || segMax !== Infinity;

    const turnSmoothness = options.turnSmoothness ?? 0;
    const diagonalChance = options.diagonalChance ?? 0.5;
    const turnPenalty = turnSmoothness * (gridWidth + gridHeight);
    const dc = diagonalChance < 0 ? 0 : diagonalChance > 1 ? 1 : diagonalChance;
    const diagCost = Math.SQRT2 + (1 - dc) * 2.5;

    const trackDir = shaping || turnPenalty > 0;
    const RUN_CAP = 31;
    const keyOf = (x, y, dir, run = 0) => {
        const base = idx(x, y, gridHeight);
        if (trackDir && shaping) return base * (9 * 32) + (dir + 1) * 32 + Math.min(run, RUN_CAP);
        if (trackDir) return base * 9 + (dir + 1);
        return base;
    };

    const h = (x, y) => chebyshev({ x, y }, end);

    const bestG = new Map();
    const parentOf = new Map();
    const open = new MinHeap();

    const startKey = keyOf(start.x, start.y, startDir, 0);
    bestG.set(startKey, 0);
    open.push({
        f: h(start.x, start.y),
        g: 0,
        x: start.x,
        y: start.y,
        dir: startDir,
        run: 0,
        key: startKey,
    });

    let expansions = 0;
    const defaultCap = gridWidth * gridHeight * 4;
    const maxExpansions = options.maxExpansions || defaultCap;

    while (open.size > 0) {
        const node = open.pop();
        if (node.g !== bestG.get(node.key)) continue;
        if (++expansions > maxExpansions) return null;

        if (node.x === end.x && node.y === end.y) {
            const path = [];
            let key = node.key;
            let info = { x: node.x, y: node.y, dir: node.dir };
            while (info) {
                path.unshift({ x: info.x, y: info.y });
                const parent = parentOf.get(key);
                if (!parent) break;
                key = keyOf(parent.x, parent.y, parent.dir, parent.run ?? 0);
                info = parent;
            }
            return path;
        }

        for (let i = 0; i < 8; i++) {
            const [dx, dy] = DIRS[i];
            const nx = node.x + dx;
            const ny = node.y + dy;
            if (nx < 0 || nx >= gridWidth || ny < 0 || ny >= gridHeight) continue;

            const nIdx = idx(nx, ny, gridHeight);
            if (!available[nIdx]) continue;

            const isDiag = dx !== 0 && dy !== 0;
            if (isDiag) {
                const ortho1 = cellAt(available, node.x + dx, node.y, gridWidth, gridHeight);
                const ortho2 = cellAt(available, node.x, node.y + dy, gridWidth, gridHeight);
                if (!ortho1 && !ortho2) continue;
            }

            const delta = node.dir === -1 ? 0 : (i - node.dir + 8) % 8;

            // Hard ban: interior corner ≤ 90° (heading change 2–6 on the wheel).
            if (node.dir !== -1 && delta >= 2 && delta <= 6) continue;

            let stepCost = isDiag ? diagCost : 1;
            let nextRun;

            if (shaping) {
                const turning = node.dir !== -1 && delta !== 0;
                if (delta === 0) {
                    nextRun = node.run + 1;
                    if (node.run >= segMax) stepCost += (node.run - segMax + 1) * segPenalty;
                } else {
                    nextRun = 1;
                    if (turning && node.run < segMin) {
                        const atGoal = nx === end.x && ny === end.y;
                        if (hardSegMin && !atGoal) continue;
                        if (!hardSegMin) stepCost += (segMin - node.run) * segPenalty;
                    }
                }
            } else {
                nextRun = 0;
            }

            let bundle = 0;
            if (bundleBonus > 0) {
                for (const perp of [(i + 2) % 8, (i + 6) % 8]) {
                    const sx = nx + DIRS[perp][0];
                    const sy = ny + DIRS[perp][1];
                    if (sx < 0 || sx >= gridWidth || sy < 0 || sy >= gridHeight) continue;
                    const sIdx = idx(sx, sy, gridHeight);
                    if (!available[sIdx]) {
                        const sideHeading = headings[sIdx];
                        if (sideHeading === i || sideHeading === (i + 4) % 8) {
                            bundle = bundleBonus;
                            break;
                        }
                    }
                }
            }

            const g = node.g + stepCost - bundle;
            const nKey = keyOf(nx, ny, i, nextRun);
            const prevBest = bestG.get(nKey);
            if (prevBest !== undefined && prevBest <= g) continue;

            bestG.set(nKey, g);
            parentOf.set(nKey, { x: node.x, y: node.y, dir: node.dir, run: node.run });
            open.push({
                f: g + h(nx, ny),
                g,
                x: nx,
                y: ny,
                dir: i,
                run: nextRun,
                key: nKey,
            });
        }
    }
    return null;
}

export function serializeGrid(grid, gridWidth, gridHeight) {
    const n = gridWidth * gridHeight;
    const available = new Uint8Array(n);
    const headings = new Int8Array(n);
    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            const i = idx(x, y, gridHeight);
            const c = grid[x][y];
            available[i] = c.available ? 1 : 0;
            headings[i] = c.heading;
        }
    }
    return { available, headings };
}

export function directionBetween(a, b) {
    const dx = Math.sign(b.x - a.x);
    const dy = Math.sign(b.y - a.y);
    for (let d = 0; d < 8; d++) {
        if (DIRS[d][0] === dx && DIRS[d][1] === dy) return d;
    }
    return 1;
}
