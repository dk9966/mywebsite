// Octilinear A* on flat grid buffers:
//   - interior corners <= 90 degrees are hard-banned (45-degree bends only)
//   - clearance shaping keeps an even gap around component keepouts
//   - bundle shaping makes parallel traces settle at a 2-cell ribbon pitch
//     (1 cell away is penalized, 2 cells away earns a bonus)
//   - optional corridor bias pulls follower traces along their leader's chord

import { DIRS } from './dirs.js';

export function idx(x, y, gridHeight) {
    return x * gridHeight + y;
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

function distanceToSegment(x, y, [ax, ay], [bx, by]) {
    const dx = bx - ax;
    const dy = by - ay;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(x - ax, y - ay);
    const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / lenSq));
    return Math.hypot(x - (ax + dx * t), y - (ay + dy * t));
}

// Corridors are polylines ([[x,y], ...]) so a follower can shadow its
// leader's actual route, detours included, instead of a straight chord.
function distanceToPolyline(x, y, pts) {
    if (pts.length === 1) return Math.hypot(x - pts[0][0], y - pts[0][1]);
    let best = Infinity;
    for (let i = 0; i + 1 < pts.length; i++) {
        const d = distanceToSegment(x, y, pts[i], pts[i + 1]);
        if (d < best) best = d;
    }
    return best;
}

// grid: { available: Uint8Array, headings: Int8Array, clearance: Uint8Array,
//         gw, gh, inset }. start/end are {x, y} cells. Returns [{x,y},...] or null.
export function aStar(grid, start, end, options = {}) {
    const { available, clearance, gw, gh, inset } = grid;
    const endIdx = idx(end.x, end.y, gh);
    if (start.x === end.x && start.y === end.y) return [start];
    if (!available[endIdx]) return null;

    const segMin = Math.max(0, options.segMin || 0);
    const segPenalty = options.segPenalty ?? 2;
    const startDir = Number.isInteger(options.startDir) ? options.startDir : -1;
    const endDir = Number.isInteger(options.endDir) ? options.endDir : -1;
    const turnPenalty = (options.turnSmoothness ?? 0) * (gw + gh);
    const diagCost = options.diagCost ?? Math.SQRT2;
    const clearanceTarget = options.clearanceTarget ?? 0;
    const clearanceWeight = options.clearanceWeight ?? 0;
    const nearPenalty = options.bundleNearPenalty ?? 0;
    const farBonus = options.bundleFarBonus ?? 0;
    const corridor = options.corridor || null;
    const corridorWeight = corridor ? options.corridorWeight ?? 0 : 0;
    const corridorRadius = options.corridorRadius ?? 0;
    const maxExpansions = options.maxExpansions || gw * gh * 4;

    const shaping = segMin > 0;
    const RUN_CAP = 31;
    const keyOf = (x, y, dir, run) => {
        const base = idx(x, y, gh);
        if (shaping) return base * (9 * 32) + (dir + 1) * 32 + Math.min(run, RUN_CAP);
        return base * 9 + (dir + 1);
    };

    const h = (x, y) => Math.max(Math.abs(x - end.x), Math.abs(y - end.y));

    const bestG = new Map();
    const parentOf = new Map();
    const open = new MinHeap();

    const startKey = keyOf(start.x, start.y, startDir, 0);
    bestG.set(startKey, 0);
    open.push({ f: h(start.x, start.y), g: 0, x: start.x, y: start.y, dir: startDir, run: 0, key: startKey });

    let expansions = 0;
    while (open.size > 0) {
        const node = open.pop();
        if (node.g !== bestG.get(node.key)) continue;
        if (++expansions > maxExpansions) return null;

        if (node.x === end.x && node.y === end.y) {
            // Arrival within 45 degrees of endDir keeps the joint into a pin smooth.
            if (endDir >= 0 && node.dir >= 0) {
                const d = (endDir - node.dir + 8) % 8;
                if (d >= 2 && d <= 6) continue;
            }
            const path = [];
            let key = node.key;
            let info = { x: node.x, y: node.y };
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
            if (nx < inset || ny < inset || nx >= gw - inset || ny >= gh - inset) continue;

            const nIdx = idx(nx, ny, gh);
            if (!available[nIdx]) continue;

            const isDiag = dx !== 0 && dy !== 0;
            if (isDiag) {
                // Never cut visually through two occupied diagonal neighbours.
                const o1 = available[idx(node.x + dx, node.y, gh)];
                const o2 = available[idx(node.x, node.y + dy, gh)];
                if (!o1 && !o2) continue;
            }

            const delta = node.dir === -1 ? 0 : (i - node.dir + 8) % 8;
            if (node.dir !== -1 && delta >= 2 && delta <= 6) continue;

            let stepCost = isDiag ? diagCost : 1;
            let nextRun;
            if (shaping) {
                if (delta === 0) {
                    nextRun = node.run + 1;
                } else {
                    nextRun = 1;
                    if (node.dir !== -1 && node.run < segMin && !(nx === end.x && ny === end.y)) {
                        stepCost += (segMin - node.run) * segPenalty;
                    }
                }
            } else {
                nextRun = 0;
            }
            if (node.dir !== -1 && delta !== 0) stepCost += turnPenalty;

            if (clearanceWeight > 0) {
                const d = clearance[nIdx];
                if (d < clearanceTarget) stepCost += clearanceWeight * (clearanceTarget - d);
            }

            if (corridorWeight > 0) {
                const drift = Math.max(0, distanceToPolyline(nx, ny, corridor) - corridorRadius);
                stepCost += corridorWeight * drift;
            }

            if (nearPenalty > 0 || farBonus > 0) {
                for (const perp of [(i + 2) % 8, (i + 6) % 8]) {
                    const [px, py] = DIRS[perp];
                    const tier = parallelTier(grid, nx, ny, px, py, i);
                    if (tier === 1) stepCost += nearPenalty;
                    else if (tier === 2) stepCost -= farBonus;
                }
                // Diagonal runs offset by one orthogonal cell are only
                // cell/sqrt2 apart -- the perpendicular wheel above never sees
                // them, so check the four orthogonal neighbours explicitly and
                // punish hard to keep slanted ribbons at full pitch.
                if (isDiag) {
                    for (const ortho of [1, 3, 5, 7]) {
                        const [px, py] = DIRS[ortho];
                        if (parallelTier(grid, nx, ny, px, py, i) === 1) {
                            stepCost += nearPenalty * 2;
                        }
                    }
                }
            }

            const g = node.g + stepCost;
            const nKey = keyOf(nx, ny, i, nextRun);
            const prevBest = bestG.get(nKey);
            if (prevBest !== undefined && prevBest <= g) continue;

            bestG.set(nKey, g);
            parentOf.set(nKey, { x: node.x, y: node.y, dir: node.dir, run: node.run });
            open.push({ f: g + h(nx, ny), g, x: nx, y: ny, dir: i, run: nextRun, key: nKey });
        }
    }
    return null;
}

// 1 if a parallel trace sits one cell away in direction (px,py), 2 if the
// nearest one is two cells away, 0 otherwise.
function parallelTier(grid, x, y, px, py, heading) {
    const { available, headings, gw, gh } = grid;
    for (let step = 1; step <= 2; step++) {
        const sx = x + px * step;
        const sy = y + py * step;
        if (sx < 0 || sx >= gw || sy < 0 || sy >= gh) return 0;
        const sIdx = idx(sx, sy, gh);
        if (!available[sIdx]) {
            const sideHeading = headings[sIdx];
            if (sideHeading === heading || sideHeading === (heading + 4) % 8) return step;
            return 0;
        }
    }
    return 0;
}
