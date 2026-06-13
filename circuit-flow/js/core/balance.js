// Spatial balance pass: fill sparse cluster columns with extra branches,
// enforce clearance as a final safety net, then enforce the mesh contract:
// at least `mesh.anchoredShare` of all lines must have BOTH ends anchored
// (start on a pin or fork, end on a pin). Excess danglers get dropped,
// shortest first -- the rest stay open and fray, like the reference.

import { spawnBranches, mergeDanglingEnds } from './flows.js';

function densityStrips(state, config) {
    const { columns } = config.balance;
    const stripW = config.board.width / columns;
    const strips = new Array(columns).fill(0);
    for (const b of state.bundles) {
        for (const lane of b.lanes) {
            for (let i = 0; i + 1 < lane.length; i++) {
                const len = Math.hypot(lane[i + 1][0] - lane[i][0], lane[i + 1][1] - lane[i][1]);
                const mid = (lane[i][0] + lane[i + 1][0]) / 2;
                const idx = Math.max(0, Math.min(columns - 1, Math.floor(mid / stripW)));
                strips[idx] += len;
            }
        }
    }
    return strips;
}

// Fillers only target columns inside the chip cluster -- the space between
// the obstacles is where density belongs. Each filler is a branch (anchored
// by its fork); its end takes a pin right away if one is in reach.
function addFillers(rng, state, config) {
    const { sparseRatio, maxFillers, columns } = config.balance;
    const stripW = config.board.width / columns;
    const clusterMin = Math.min(...state.chips.map((c) => c.x));
    const clusterMax = Math.max(...state.chips.map((c) => c.x + c.w));

    for (let i = 0; i < maxFillers; i++) {
        const strips = densityStrips(state, config);
        const mean = strips.reduce((s, v) => s + v, 0) / columns;
        let worst = -1;
        let worstVal = Infinity;
        for (let j = 0; j < columns; j++) {
            const cx = (j + 0.5) * stripW;
            if (cx < clusterMin || cx > clusterMax) continue;
            if (strips[j] < worstVal) {
                worstVal = strips[j];
                worst = j;
            }
        }
        if (worst === -1 || worstVal >= sparseRatio * mean) break;
        if (!spawnBranches(rng, state, config, 1, (worst + 0.5) * stripW)) break;
    }
    mergeDanglingEnds(state, config);
}

// Min distance squared between two segments (standard clamped closest-point).
function segDist2(p1, q1, p2, q2) {
    const d1x = q1[0] - p1[0];
    const d1y = q1[1] - p1[1];
    const d2x = q2[0] - p2[0];
    const d2y = q2[1] - p2[1];
    const rx = p1[0] - p2[0];
    const ry = p1[1] - p2[1];
    const a = d1x * d1x + d1y * d1y;
    const e = d2x * d2x + d2y * d2y;
    const f = d2x * rx + d2y * ry;

    let s;
    let t;
    if (a <= 1e-12 && e <= 1e-12) {
        s = 0;
        t = 0;
    } else if (a <= 1e-12) {
        s = 0;
        t = Math.max(0, Math.min(1, f / e));
    } else {
        const c = d1x * rx + d1y * ry;
        if (e <= 1e-12) {
            t = 0;
            s = Math.max(0, Math.min(1, -c / a));
        } else {
            const b = d1x * d2x + d1y * d2y;
            const denom = a * e - b * b;
            s = denom > 1e-12 ? Math.max(0, Math.min(1, (b * f - c * e) / denom)) : 0;
            t = (b * s + f) / e;
            if (t < 0) {
                t = 0;
                s = Math.max(0, Math.min(1, -c / a));
            } else if (t > 1) {
                t = 1;
                s = Math.max(0, Math.min(1, (b - c) / a));
            }
        }
    }
    const cx = p1[0] + d1x * s - (p2[0] + d2x * t);
    const cy = p1[1] + d1y * s - (p2[1] + d2y * t);
    return cx * cx + cy * cy;
}

function bundlesTooClose(a, b, limit) {
    const lim2 = limit * limit;
    for (const la of a.lanes) {
        for (let i = 0; i + 1 < la.length; i++) {
            for (const lb of b.lanes) {
                for (let j = 0; j + 1 < lb.length; j++) {
                    if (segDist2(la[i], la[i + 1], lb[j], lb[j + 1]) < lim2) return true;
                }
            }
        }
    }
    return false;
}

// Dropping a line releases its pins (no bare tabs) and must take its guest
// subtree along: a junction without its host would float in space.
function releaseSubtree(state, keep, bundle) {
    const stack = [bundle];
    while (stack.length) {
        const b = stack.pop();
        if (!keep.has(b)) continue;
        keep.delete(b);
        for (const p of b.pins ?? []) {
            state.usedPins.get(p.chip)[p.side].delete(p.index);
        }
        for (const g of b.guestList ?? []) stack.push(g);
    }
}

function subtreeSize(keep, bundle) {
    let n = 0;
    const stack = [bundle];
    const seen = new Set();
    while (stack.length) {
        const b = stack.pop();
        if (seen.has(b) || !keep.has(b)) continue;
        seen.add(b);
        n += 1;
        for (const g of b.guestList ?? []) stack.push(g);
    }
    return n;
}

function dropViolators(state, config, keep) {
    const limit = config.lanes.clearance * 0.75;
    for (const d of state.bundles) {
        if (!d.stub || d.guestList.length > 0) continue;
        for (const other of state.bundles) {
            if (other === d || !keep.has(other)) continue;
            if (bundlesTooClose(d, other, limit)) {
                releaseSubtree(state, keep, d);
                break;
            }
        }
    }
}

// The mesh contract: drop dangling lines until the both-ends-anchored share
// reaches the configured floor. Guest-free danglers go first (stubs, then
// shortest); if only junction hosts remain, the smallest subtree goes.
function enforceAnchoredShare(state, config, keep) {
    const lineLen = (b) => {
        let len = 0;
        for (const lane of b.lanes) {
            for (let i = 0; i + 1 < lane.length; i++) {
                len += Math.hypot(lane[i + 1][0] - lane[i][0], lane[i + 1][1] - lane[i][1]);
            }
        }
        return len;
    };

    for (;;) {
        const kept = state.bundles.filter((b) => keep.has(b));
        if (!kept.length) return;
        const dangling = kept.filter((b) => b.sinkType === 'open');
        if (dangling.length / kept.length <= 1 - config.mesh.anchoredShare) return;

        const droppable = dangling.filter((b) => b.guestList.length === 0);
        if (droppable.length) {
            // Drop order: stubs, then plain open lines (shortest first),
            // then branches last -- a branch is anchored at its fork and
            // is the deliberate branch-out material, not wandering excess.
            const rank = (b) => (b.stub ? 0 : b.branch ? 2 : 1);
            droppable.sort(
                (a, b) => rank(a) - rank(b) || lineLen(a) - lineLen(b),
            );
            releaseSubtree(state, keep, droppable[0]);
            continue;
        }

        const hosts = dangling.sort((a, b) => subtreeSize(keep, a) - subtreeSize(keep, b));
        if (!hosts.length || subtreeSize(keep, hosts[0]) > 4) return;
        releaseSubtree(state, keep, hosts[0]);
    }
}

export function balanceModel(rng, state, config) {
    addFillers(rng, state, config);
    const keep = new Set(state.bundles);
    dropViolators(state, config, keep);
    enforceAnchoredShare(state, config, keep);

    const traces = [];
    let anchoredBoth = 0;
    let lines = 0;
    for (const b of state.bundles) {
        if (!keep.has(b)) continue;
        lines += 1;
        if (b.sinkType !== 'open') anchoredBoth += 1;
        for (const lane of b.lanes) {
            traces.push({
                points: lane,
                width: config.style.traceWidth,
                open: b.sinkType === 'open',
                branch: !!b.branch,
            });
        }
    }
    return { traces, meshStats: { lines, anchoredBoth } };
}
