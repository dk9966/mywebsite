// Routing: builds the occupancy grid from placed parts, then routes ribbon
// buses, grouped solo-pin fans, small-part links, and anchored void fillers. Followers
// shadow their leader's actual path (polyline corridor + bundle shaping) so
// open-ended material reads as deliberate parallel ribbons, and grouped fans
// terminate in staggered via rows. Every open route ends on a via -- no trace
// end is ever bare. Failed routes are dropped silently; density tuning, not
// connectivity, is the contract.

import { gridSize } from '../config.js';
import { aStar, idx } from './astar.js';
import { DIRS, directionBetween, dirAngle, opposite } from './dirs.js';

export function routeAll(rng, parts, nets, config) {
    const grid = buildGrid(parts, config);
    const cell = config.grid.cell;
    const traces = [];
    const vias = [];
    const viaCells = [];

    const base = {
        segMin: config.route.segMin,
        segPenalty: config.route.segPenalty,
        turnSmoothness: config.route.turnSmoothness,
        diagCost: config.route.diagCost,
        clearanceTarget: config.route.clearanceTarget,
        clearanceWeight: config.route.clearanceWeight,
        bundleNearPenalty: config.route.bundleNearPenalty,
        bundleFarBonus: config.route.bundleFarBonus,
        maxExpansions: config.route.maxExpansions,
    };

    function tryRoute(pinA, target, opts, accept = null) {
        const ia = idx(pinA.cx, pinA.cy, grid.gh);
        const ib = idx(target.cx, target.cy, grid.gh);
        const restore = [];
        if (!grid.available[ia]) {
            grid.available[ia] = 1;
            restore.push(ia);
        }
        if (target.pin && !grid.available[ib]) {
            grid.available[ib] = 1;
            restore.push(ib);
        }
        const path = aStar(grid, { x: pinA.cx, y: pinA.cy }, { x: target.cx, y: target.cy }, {
            ...base,
            startDir: pinA.dir,
            endDir: target.pin ? opposite(target.pin.dir) : -1,
            ...opts,
        });
        if (!path || (accept && !accept(path))) {
            for (const i of restore) grid.available[i] = 0;
            return null;
        }
        markPath(grid, path);
        return path;
    }

    function pushTrace(path) {
        traces.push({ points: simplify(path.map((p) => [(p.x + 0.5) * cell, (p.y + 0.5) * cell])) });
    }

    function addVia(vx, vy) {
        vias.push({ x: (vx + 0.5) * cell, y: (vy + 0.5) * cell, ring: rng.chance(config.vias.ringChance) });
        viaCells.push([vx, vy]);
    }

    function routeBus(bus) {
        const pending = [...bus.pairs];
        let leader = null;
        while (pending.length && !leader) {
            const [a, b] = pending.shift();
            leader = tryRoute(a, { cx: b.cx, cy: b.cy, pin: b }, {});
            if (leader) pushTrace(leader);
        }
        if (!leader) return;
        const guide = cellVertices(leader);
        for (const [a, b] of pending) {
            const path = tryRoute(a, { cx: b.cx, cy: b.cy, pin: b }, {
                corridor: guide,
                corridorWeight: config.route.corridorWeight,
                corridorRadius: config.route.corridorRadius,
            });
            if (path) pushTrace(path);
        }
    }

    const anchorKinds = new Set(['qfp', 'heatsink', 'soic', 'header', 'connector']);
    const anchorPins = parts
        .filter((p) => anchorKinds.has(p.kind))
        .flatMap((p) => p.pins);

    // Pad-to-anchor: small circuitry should resolve into a QFP, heatsink, or
    // other substantial part rather than an isolated island.
    function routeToAnchor(pin, maxDistCells) {
        const targets = anchorPins
            .filter((q) => !q.used && q.partId !== pin.partId)
            .map((q) => ({ q, d: Math.hypot(q.cx - pin.cx, q.cy - pin.cy) }))
            .filter(({ d }) => d >= 5 && d <= maxDistCells)
            .sort((a, b) => a.d - b.d)
            .slice(0, 14);
        for (const { q } of targets) {
            const path = tryRoute(pin, { cx: q.cx, cy: q.cy, pin: q }, {
                corridor: [[pin.cx, pin.cy], [q.cx, q.cy]],
                corridorWeight: 0.07,
                corridorRadius: 9,
                maxExpansions: config.route.openMaxExpansions,
            }, (p) => maxSwing(p) < 180);
            if (path) {
                pushTrace(path);
                pin.used = true;
                q.used = true;
                return true;
            }
        }
        return false;
    }

    // Valid via spots near a pin, emptiest neighbourhood first, so open stubs
    // eat into unused board area.
    function openCandidates(pin, [dMin, dMax]) {
        const candidates = [];
        for (let attempt = 0; attempt < 30 && candidates.length < 5; attempt++) {
            const ang = dirAngle(pin.dir) + rng.range(-1.1, 1.1);
            const d = rng.range(dMin, dMax);
            const tx = Math.round(pin.cx + Math.cos(ang) * d);
            const ty = Math.round(pin.cy + Math.sin(ang) * d);
            if (openTargetOk(tx, ty)) candidates.push({ tx, ty, occ: localOccupancy(tx, ty) });
        }
        return candidates.sort((a, b) => a.occ - b.occ);
    }

    function routeToOpen(pin, distRange) {
        if (pin.used) return null;
        for (const { tx, ty } of openCandidates(pin, distRange)) {
            // Open stubs in the reference never double back on themselves:
            // cap the cumulative turn so hairpin loops get dropped.
            const path = tryRoute(pin, { cx: tx, cy: ty, pin: null }, {
                corridor: [[pin.cx, pin.cy], [tx, ty]],
                corridorWeight: 0.08,
                corridorRadius: 6,
                maxExpansions: config.route.openMaxExpansions,
            }, (p) => maxSwing(p) < 180);
            if (!path) continue;
            pushTrace(path);
            addVia(tx, ty);
            pin.used = true;
            return path;
        }
        return null;
    }

    // A run of adjacent chip pins fans out as one ribbon: the leader routes to
    // open space, followers shadow its path and land on a staggered via row.
    function routeSoloGroup(group) {
        const pins = group.filter((p) => !p.used);
        if (!pins.length) return;
        if (pins.length === 1) {
            const pin = pins[0];
            routeToOpen(pin, config.net.soloDist);
            return;
        }

        const leader = pins[0];
        const leaderPath = routeToOpen(leader, config.net.soloDist);
        if (!leaderPath) return;

        const guide = cellVertices(leaderPath);
        const end = leaderPath[leaderPath.length - 1];
        const heading = directionBetween(leaderPath[leaderPath.length - 2] ?? leaderPath[0], end);
        // Via row grows on the side the follower pins sit on.
        const along = [pins[1].cx - leader.cx, pins[1].cy - leader.cy];
        let perp = DIRS[(heading + 2) % 8];
        if (perp[0] * along[0] + perp[1] * along[1] < 0) perp = DIRS[(heading + 6) % 8];

        for (let i = 1; i < pins.length; i++) {
            const target = followerTarget(end, heading, perp, i);
            if (!target) continue;
            const path = tryRoute(pins[i], { cx: target[0], cy: target[1], pin: null }, {
                corridor: guide,
                corridorWeight: 0.12,
                corridorRadius: 2,
                maxExpansions: config.route.openMaxExpansions,
            }, (p) => maxSwing(p) < 180);
            if (!path) continue;
            pushTrace(path);
            addVia(target[0], target[1]);
            pins[i].used = true;
        }
    }

    // Staggered via spot for follower i: one ribbon pitch sideways per lane,
    // pulled back along the approach so the dots step like the reference.
    function followerTarget(end, heading, perp, i) {
        const [hx, hy] = DIRS[heading];
        for (const back of [i, i + 1, i - 1, 0, 2 * i]) {
            const tx = end.x + perp[0] * 2 * i - hx * back;
            const ty = end.y + perp[1] * 2 * i - hy * back;
            if (openTargetOk(tx, ty, config.vias.groupGapCells, 2)) return [tx, ty];
        }
        return null;
    }

    // Filler: start from a free anchor pin and push into the emptiest nearby
    // region, so density stays attached to QFPs and heatsinks.
    function routeFiller() {
        const starts = rng.shuffle([
            ...anchorPins.filter((p) => !p.used),
            ...viaCells.map(([cx, cy]) => ({ cx, cy, dir: -1, viaStart: true })),
        ]).slice(0, 32);
        if (!starts.length) return 'done';
        let best = null;
        for (const pin of starts) {
            for (let s = 0; s < 12; s++) {
                const baseAngle = pin.viaStart ? rng.range(0, Math.PI * 2) : dirAngle(pin.dir);
                const ang = baseAngle + rng.range(-1.4, 1.4);
                const d = rng.range(...config.net.fillerDist);
                const tx = Math.round(pin.cx + Math.cos(ang) * d);
                const ty = Math.round(pin.cy + Math.sin(ang) * d);
                if (!openTargetOk(tx, ty)) continue;
                const occ = localOccupancy(tx, ty, 8);
                if (!best || occ < best.occ) best = { pin, tx, ty, occ };
            }
        }
        if (!best || best.occ >= config.net.fillerStopOcc) return 'done';

        const path = tryRoute(best.pin, { cx: best.tx, cy: best.ty, pin: null }, {
            corridor: [[best.pin.cx, best.pin.cy], [best.tx, best.ty]],
            corridorWeight: 0.08,
            corridorRadius: 7,
            maxExpansions: config.route.openMaxExpansions,
        }, (p) => maxSwing(p) < 180);
        if (!path) return 'failed';
        pushTrace(path);
        addVia(best.tx, best.ty);
        if (!best.pin.viaStart) best.pin.used = true;
        if (!best.pin.viaStart && rng.chance(config.net.fillerPairChance)) routeFillerLane(path, best.pin);
        return 'routed';
    }

    // Second lane of a filler ribbon: starts from a neighboring anchor pin and
    // lands beside the leader via, preserving the connected-ribbon read.
    function routeFillerLane(leaderPath, anchorPin) {
        const b = leaderPath[leaderPath.length - 1];
        const heading = directionBetween(leaderPath[0], leaderPath[1] ?? b);
        const guide = cellVertices(leaderPath);
        const pins = anchorPins
            .filter((p) => !p.used && p.partId === anchorPin.partId)
            .map((p) => ({ p, d: Math.hypot(p.cx - anchorPin.cx, p.cy - anchorPin.cy) }))
            .filter(({ d }) => d > 0 && d <= 8)
            .sort((a, b) => a.d - b.d)
            .map(({ p }) => p);
        for (const pin of pins) {
            const offset = [pin.cx - anchorPin.cx, pin.cy - anchorPin.cy];
            const perps = [DIRS[(heading + 2) % 8], DIRS[(heading + 6) % 8]]
                .sort((a, b) => (b[0] * offset[0] + b[1] * offset[1]) - (a[0] * offset[0] + a[1] * offset[1]));
            for (const perp of perps) {
                const t = [b.x + perp[0] * 2, b.y + perp[1] * 2];
                if (!openTargetOk(t[0], t[1], config.vias.groupGapCells, 2)) continue;
                const path = tryRoute(pin, { cx: t[0], cy: t[1], pin: null }, {
                    corridor: guide,
                    corridorWeight: 0.12,
                    corridorRadius: 3,
                    maxExpansions: config.route.openMaxExpansions,
                }, (p) => maxSwing(p) < 180);
                if (!path) continue;
                pushTrace(path);
                addVia(t[0], t[1]);
                pin.used = true;
                return;
            }
        }
    }
    function localOccupancy(tx, ty, radius = 6) {
        let occ = 0;
        for (let x = Math.max(0, tx - radius); x <= Math.min(grid.gw - 1, tx + radius); x++) {
            for (let y = Math.max(0, ty - radius); y <= Math.min(grid.gh - 1, ty + radius); y++) {
                if (!grid.available[idx(x, y, grid.gh)]) occ++;
            }
        }
        return occ;
    }

    function openTargetOk(tx, ty, viaGap = config.vias.minGapCells, minClearance = 3) {
        const m = grid.inset + 1;
        if (tx < m || ty < m || tx >= grid.gw - m || ty >= grid.gh - m) return false;
        const i = idx(tx, ty, grid.gh);
        if (!grid.available[i]) return false;
        if (grid.clearance[i] < minClearance) return false;
        return viaCells.every(([vx, vy]) => Math.max(Math.abs(vx - tx), Math.abs(vy - ty)) >= viaGap);
    }

    function routeFillers(count) {
        let failed = 0;
        for (let i = 0; i < count; i++) {
            const result = routeFiller();
            if (result === 'done') break;
            failed = result === 'failed' ? failed + 1 : 0;
            if (failed >= 12) break;
        }
    }

    for (const bus of nets.buses) routeBus(bus);
    for (const group of nets.soloGroups) routeSoloGroup(group);
    routeFillers(Math.ceil(config.net.fillerMax * 0.6));
    for (const pin of nets.smalls) {
        if (pin.used) continue;
        routeToAnchor(pin, config.net.anchorLinkDist);
    }
    routeFillers(Math.floor(config.net.fillerMax * 0.4));

    return { traces, vias };
}

function buildGrid(parts, config) {
    const { gw, gh } = gridSize(config);
    const available = new Uint8Array(gw * gh).fill(1);
    const headings = new Int8Array(gw * gh).fill(-1);

    const block = (x, y) => {
        if (x >= 0 && x < gw && y >= 0 && y < gh) available[idx(x, y, gh)] = 0;
    };
    for (const part of parts) {
        for (let x = part.cellX; x < part.cellX + part.cols; x++) {
            for (let y = part.cellY; y < part.cellY + part.rows; y++) block(x, y);
        }
        // Pin anchors are blocked too: stray traces must not run through pin
        // tips. tryRoute frees the anchor of the pin actually being routed.
        for (const pin of part.pins) block(pin.cx, pin.cy);
    }

    return { available, headings, clearance: clearanceField(available, gw, gh), gw, gh, inset: config.grid.edgeMargin };
}

// Chebyshev distance (capped) to the nearest component cell, via multi-source BFS.
function clearanceField(available, gw, gh, cap = 7) {
    const field = new Uint8Array(gw * gh).fill(cap);
    let frontier = [];
    for (let i = 0; i < available.length; i++) {
        if (!available[i]) {
            field[i] = 0;
            frontier.push(i);
        }
    }
    for (let d = 1; d < cap && frontier.length; d++) {
        const next = [];
        for (const i of frontier) {
            const x = Math.floor(i / gh);
            const y = i % gh;
            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    const nx = x + dx;
                    const ny = y + dy;
                    if (nx < 0 || nx >= gw || ny < 0 || ny >= gh) continue;
                    const ni = nx * gh + ny;
                    if (field[ni] > d) {
                        field[ni] = d;
                        next.push(ni);
                    }
                }
            }
        }
        frontier = next;
    }
    return field;
}

function markPath(grid, path) {
    for (let i = 0; i < path.length; i++) {
        const cellIdx = idx(path[i].x, path[i].y, grid.gh);
        grid.available[cellIdx] = 0;
        const from = path[Math.max(0, i - 1)];
        const to = path[Math.min(path.length - 1, i + 1)];
        grid.headings[cellIdx] = directionBetween(from, i === 0 ? to : path[i]);
    }
}

// Turn points of a cell path, as corridor polyline input.
function cellVertices(path) {
    const out = [[path[0].x, path[0].y]];
    for (let i = 1; i + 1 < path.length; i++) {
        const a = path[i - 1];
        const b = path[i];
        const c = path[i + 1];
        if (b.x - a.x !== c.x - b.x || b.y - a.y !== c.y - b.y) out.push([b.x, b.y]);
    }
    out.push([path[path.length - 1].x, path[path.length - 1].y]);
    return out;
}

// Largest absolute cumulative turn (degrees) along a cell path.
function maxSwing(path) {
    let dir = null;
    let cum = 0;
    let maxAbs = 0;
    for (let i = 1; i < path.length; i++) {
        const d = directionBetween(path[i - 1], path[i]);
        if (dir !== null && d !== dir) {
            const raw = (d - dir + 8) % 8;
            cum += (raw <= 4 ? raw : raw - 8) * 45;
            maxAbs = Math.max(maxAbs, Math.abs(cum));
        }
        dir = d;
    }
    return maxAbs;
}

function simplify(points) {
    const out = [points[0]];
    for (let i = 1; i + 1 < points.length; i++) {
        const [ax, ay] = out[out.length - 1];
        const [bx, by] = points[i];
        const [cx, cy] = points[i + 1];
        if ((bx - ax) * (cy - by) !== (by - ay) * (cx - bx)) out.push(points[i]);
    }
    out.push(points[points.length - 1]);
    return out;
}
