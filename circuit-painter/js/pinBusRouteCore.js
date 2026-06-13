// Pin-bus routing on flat grid buffers. Used by the worker and as a main-thread
// fallback when the worker is unavailable.

import { aStarCore, directionBetween, isSharpCorner } from './pathfindCore.js';

const BUNDLE_BONUS = 0.7;

function idx(x, y, gridHeight) {
    return x * gridHeight + y;
}

// Retry ladder: each later attempt searches harder and relaxes the segment
// shaping (shorter runs allowed, then soft minimums). The ≤ 90° corner ban is
// built into aStarCore unconditionally, so every attempt keeps the 135° rule.
function attemptsFor(segMin, cellCount) {
    return [
        { segMin, maxExpansions: cellCount * 4 },
        { segMin: Math.max(2, segMin >> 1), maxExpansions: cellCount * 6 },
        { segMin: 2, hardSegMin: false, maxExpansions: cellCount * 10 },
    ];
}

// A* states are (cell, dir, run), so an optimal path may pass through the same
// cell twice with different headings -- on screen that is a tight 360° knot or
// a trace crossing itself. Splice out revisit loops, then reject the path if a
// sharp corner or a diagonal self-crossing remains.
function cleanSelfOverlap(path) {
    const seen = new Map();
    const out = [];
    for (const p of path) {
        const k = `${p.x},${p.y}`;
        const at = seen.get(k);
        if (at !== undefined) {
            for (let r = at + 1; r < out.length; r++) {
                seen.delete(`${out[r].x},${out[r].y}`);
            }
            out.length = at + 1;
        } else {
            seen.set(k, out.length);
            out.push(p);
        }
    }
    if (out.length < 2) return null;

    const steps = new Set();
    for (let i = 1; i < out.length; i++) {
        const a = out[i - 1];
        const b = out[i];
        if (i >= 2 && isSharpCorner(directionBetween(out[i - 2], a), directionBetween(a, b))) {
            return null;
        }
        steps.add(`${a.x},${a.y}>${b.x},${b.y}`);
    }
    for (let i = 1; i < out.length; i++) {
        const a = out[i - 1];
        const b = out[i];
        if (a.x === b.x || a.y === b.y) continue;
        if (steps.has(`${a.x},${b.y}>${b.x},${a.y}`) || steps.has(`${b.x},${a.y}>${a.x},${b.y}`)) {
            return null;
        }
    }
    return out;
}

function routeIsLocal(path, route, routeParams) {
    const direct = Math.max(
        1,
        Math.hypot(route.srcTip.x - route.dstTip.x, route.srcTip.y - route.dstTip.y),
    );
    const maxDetour = Math.max(1.4, routeParams.maxDetourRatio ?? 2.1);
    return path.length <= direct * maxDetour + 8 && !wrapsUnrelatedObstacle(path, route, routeParams);
}

function wrapsUnrelatedObstacle(path, route, routeParams) {
    const obstacles = routeParams.obstacles || [];
    for (let i = 0; i < obstacles.length; i++) {
        if (i === route.sourceChipIndex || i === route.targetChipIndex) continue;
        const o = obstacles[i];
        let left = false;
        let right = false;
        let top = false;
        let bottom = false;
        for (const p of path) {
            const yOverlap = p.y >= o.y - 1 && p.y <= o.y + o.h;
            const xOverlap = p.x >= o.x - 1 && p.x <= o.x + o.w;
            if (yOverlap && p.x < o.x) left = true;
            if (yOverlap && p.x > o.x + o.w - 1) right = true;
            if (xOverlap && p.y < o.y) top = true;
            if (xOverlap && p.y > o.y + o.h - 1) bottom = true;
            if ((left && right) || (top && bottom)) return true;
        }
    }
    return false;
}

function routeTraceCore(available, headings, gridWidth, gridHeight, route, routeParams) {
    // A short hop can't honor a long minimum leg: the router would overshoot
    // and circle back in ≥ segMin legs, drawing giant octagonal detours. Scale
    // the minimum down so legs stay proportional to the route's span.
    const span = Math.max(
        Math.abs(route.srcTip.x - route.dstTip.x),
        Math.abs(route.srcTip.y - route.dstTip.y),
    );
    const tap = !!route.tap;
    const segMin = tap
        ? Math.max(1, Math.min(4, Math.max(2, span >> 3)))
        : Math.max(1, Math.min(routeParams.segMin | 0, Math.max(2, span >> 2)));
    const segMax = tap
        ? Math.max(segMin + 1, Math.min(12, Math.max(5, span >> 1)))
        : Math.max(segMin + 1, routeParams.segMax | 0);
    const cellCount = gridWidth * gridHeight;
    const corridor = route.corridor
        ? { ...route.corridor, weight: tap ? routeParams.tapCorridorWeight : routeParams.corridorWeight }
        : null;
    const base = {
        // Tap routes terminate on the committed backbone; bundling pulls them onto
        // the same cells the trunk already draws, which reads as doubled traces.
        bundle: tap ? 0 : BUNDLE_BONUS,
        onlyObtuse: true,
        segMax,
        hardSegMin: true,
        startDir: route.startDir,
        endDir: route.endDir,
        bounds: route.bounds,
        corridor,
        turnSmoothness: routeParams.turnSmoothness,
        diagonalChance: routeParams.diagonalChance,
        clearance: routeParams.clearance,
        clearanceTarget: routeParams.clearanceTarget,
        clearanceWeight: routeParams.clearanceWeight,
    };

    const direct = routeDirectTrace(available, gridWidth, gridHeight, route);
    if (direct && routeIsLocal(direct, route, routeParams)) return direct;

    // Cheap feasibility probe: same ≤ 90° corner ban, no segment shaping, so
    // its state space is ~30x smaller. Any shaped path is a valid probe path,
    // so a probe failure means the expensive ladder below cannot succeed --
    // routes walled off by earlier buses get rejected at a fraction of the cost.
    const probe = aStarCore(available, headings, gridWidth, gridHeight, route.srcTip, route.dstTip, {
        bundle: tap ? 0 : BUNDLE_BONUS,
        startDir: route.startDir,
        endDir: route.endDir,
        bounds: route.bounds,
        corridor,
        turnSmoothness: routeParams.turnSmoothness,
        diagonalChance: routeParams.diagonalChance,
        clearance: routeParams.clearance,
        clearanceTarget: routeParams.clearanceTarget,
        clearanceWeight: routeParams.clearanceWeight,
        maxExpansions: cellCount * 3,
    });
    if (!probe) return null;

    for (const extra of attemptsFor(segMin, cellCount)) {
        const path = aStarCore(available, headings, gridWidth, gridHeight, route.srcTip, route.dstTip, {
            ...base,
            ...extra,
        });
        if (path) {
            const clean = cleanSelfOverlap(path);
            if (clean && routeIsLocal(clean, route, routeParams)) return clean;
        }
    }
    // Shaping made it unroutable but the probe path is geometrically valid
    // (only 45° bends): use it raw rather than dropping the connection.
    const cleanProbe = cleanSelfOverlap(probe);
    return cleanProbe && routeIsLocal(cleanProbe, route, routeParams) ? cleanProbe : null;
}

function routeDirectTrace(available, gridWidth, gridHeight, route) {
    const variants = [
        buildMonotonicTrace(route.srcTip, route.dstTip, 'diag-first'),
        buildMonotonicTrace(route.srcTip, route.dstTip, 'straight-first'),
    ];
    for (const path of variants) {
        if (!path || path.length < 2) continue;
        if (!pathMatchesRoute(path, available, gridWidth, gridHeight, route)) continue;
        const clean = cleanSelfOverlap(path);
        if (clean) return clean;
    }
    return null;
}

function buildMonotonicTrace(start, end, mode) {
    const path = [{ x: start.x, y: start.y }];
    let x = start.x;
    let y = start.y;
    let dx = end.x - x;
    let dy = end.y - y;
    const sx = Math.sign(dx);
    const sy = Math.sign(dy);

    if (sx === 0 && sy === 0) return path;
    if (sx === 0 || sy === 0 || Math.abs(dx) === Math.abs(dy)) {
        walkDirect(path, end.x, end.y);
        return path;
    }

    if (mode === 'diag-first') {
        const diagSteps = Math.min(Math.abs(dx), Math.abs(dy));
        for (let i = 0; i < diagSteps; i++) {
            x += sx;
            y += sy;
            path.push({ x, y });
        }
        walkDirect(path, end.x, end.y);
        return path;
    }

    const straightSteps = Math.abs(dx) > Math.abs(dy)
        ? Math.abs(dx) - Math.abs(dy)
        : Math.abs(dy) - Math.abs(dx);
    for (let i = 0; i < straightSteps; i++) {
        if (Math.abs(dx) > Math.abs(dy)) x += sx;
        else y += sy;
        path.push({ x, y });
    }
    walkDirect(path, end.x, end.y);
    return path;
}

function walkDirect(path, targetX, targetY) {
    let { x, y } = path[path.length - 1];
    while (x !== targetX || y !== targetY) {
        x += Math.sign(targetX - x);
        y += Math.sign(targetY - y);
        path.push({ x, y });
    }
}

function pathMatchesRoute(path, available, gridWidth, gridHeight, route) {
    for (let i = 1; i < path.length; i++) {
        const prev = path[i - 1];
        const cur = path[i];
        if (!inRouteBoundsForCore(cur.x, cur.y, gridWidth, gridHeight)) return false;
        if (!insideBounds(cur, route.bounds)) return false;
        if (!available[idx(cur.x, cur.y, gridHeight)]) return false;

        const dir = directionBetween(prev, cur);
        if (i === 1 && route.startDir >= 0 && isSharpCorner(route.startDir, dir)) return false;
        if (i >= 2 && isSharpCorner(directionBetween(path[i - 2], prev), dir)) return false;
        if (Math.abs(cur.x - prev.x) === 1 && Math.abs(cur.y - prev.y) === 1) {
            const o1 = available[idx(cur.x, prev.y, gridHeight)];
            const o2 = available[idx(prev.x, cur.y, gridHeight)];
            if (!o1 && !o2) return false;
        }
    }

    if (route.endDir >= 0 && path.length >= 2) {
        const lastDir = directionBetween(path[path.length - 2], path[path.length - 1]);
        if (isSharpCorner(lastDir, route.endDir)) return false;
    }
    return true;
}

function insideBounds(p, bounds) {
    if (!bounds) return true;
    return p.x >= bounds.minX && p.y >= bounds.minY && p.x <= bounds.maxX && p.y <= bounds.maxY;
}

function inRouteBoundsForCore(x, y, gridWidth, gridHeight) {
    return x >= 1 && y >= 1 && x < gridWidth - 1 && y < gridHeight - 1;
}

function markPath(available, headings, gridHeight, path) {
    for (let i = 1; i < path.length; i++) {
        const c = path[i];
        const cellIdx = idx(c.x, c.y, gridHeight);
        available[cellIdx] = 0;
        headings[cellIdx] = directionBetween(path[i - 1], c);
    }
}

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

// How many cells in front of each tip stay reserved for that route's own
// approach. Without this, an earlier lane hugging a pin comb (bundle bonus
// pulls it tight) parks exactly on a later lane's only entry cells and
// entombs it.
const DOORWAY_DEPTH = 2;

function doorwayCells(route, gridWidth, gridHeight) {
    const cells = [];
    const add = (x, y) => {
        if (x >= 0 && y >= 0 && x < gridWidth && y < gridHeight) {
            cells.push(idx(x, y, gridHeight));
        }
    };
    for (let k = 1; k <= DOORWAY_DEPTH; k++) {
        if (route.startDir >= 0) {
            const [dx, dy] = DIRS[route.startDir];
            add(route.srcTip.x + dx * k, route.srcTip.y + dy * k);
        }
        if (route.endDir >= 0) {
            const [dx, dy] = DIRS[route.endDir];
            add(route.dstTip.x - dx * k, route.dstTip.y - dy * k);
        }
    }
    return cells;
}

// `routes`: [{ srcTip, dstTip, startDir, endDir, group }] in routing order,
// contiguous per group (one group = one bus).
// Mutates `available`/`headings`. Returns paths aligned to `routes` (null = failed).
export function routePinBusCore(available, headings, gridWidth, gridHeight, routes, routeParams) {
    const paths = new Array(routes.length).fill(null);

    // Within a bus, pending sibling lanes' doorways are masked off; each lane
    // unmasks its own just before routing. Masking globally would starve
    // narrow corridors for unrelated buses, so the reservation is per group.
    // `base` remembers true availability under the mask.
    const base = available.slice();
    const reserved = new Uint8Array(available.length);
    const doorways = routes.map((r) => doorwayCells(r, gridWidth, gridHeight));
    let maskedGroup;

    for (let i = 0; i < routes.length; i++) {
        const route = routes[i];
        if (route.group !== maskedGroup) {
            maskedGroup = route.group;
            for (let j = i; j < routes.length && routes[j].group === maskedGroup; j++) {
                for (const c of doorways[j]) {
                    reserved[c]++;
                    if (base[c]) available[c] = 0;
                }
            }
        }
        for (const c of doorways[i]) {
            if (--reserved[c] === 0) available[c] = base[c];
        }

        const dstIdx = idx(route.dstTip.x, route.dstTip.y, gridHeight);
        const wasOpen = available[dstIdx];
        available[dstIdx] = 1;

        const path = routeTraceCore(
            available,
            headings,
            gridWidth,
            gridHeight,
            route,
            routeParams,
        );

        available[dstIdx] = wasOpen ? 1 : 0;

        if (!path || path.length < 2) continue;

        for (let j = 1; j < path.length; j++) {
            base[idx(path[j].x, path[j].y, gridHeight)] = 0;
        }
        markPath(available, headings, gridHeight, path);
        paths[i] = path;
    }

    return paths;
}
