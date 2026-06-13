// Fraying gives bundles their hand-drawn character: open ends stagger, some
// lanes stop early, some peel away with a final jog, and a fraction of unused
// pins grow short decorative stubs. Roughly half the reference traces touch
// no box at one or both ends -- the fraying is where that material comes from.

const EPS = 1e-6;

// The chip cluster's bounding band: between the obstacles, near the spine.
// Inside it every line must connect on both sides, so no trace end may stop
// there -- open ends must clear the cluster horizontally or leave the band
// vertically before they die.
export function coreZone(state) {
    return {
        x0: Math.min(...state.chips.map((c) => c.x)),
        x1: Math.max(...state.chips.map((c) => c.x + c.w)),
        y0: Math.min(...state.chips.map((c) => c.y)),
        y1: Math.max(...state.chips.map((c) => c.y + c.h)),
    };
}

export function inCoreZone(state, x, y) {
    const z = coreZone(state);
    return x > z.x0 && x < z.x1 && y > z.y0 && y < z.y1;
}

export function segRect(p, q) {
    return {
        x0: Math.min(p[0], q[0]),
        x1: Math.max(p[0], q[0]),
        y0: Math.min(p[1], q[1]),
        y1: Math.max(p[1], q[1]),
    };
}

function rectsOverlap(r, q, pad) {
    return r.x0 - pad < q.x1 && r.x1 + pad > q.x0 && r.y0 - pad < q.y1 && r.y1 + pad > q.y0;
}

export function areaClear(state, config, rect, { exceptBundles = [], exceptChips = [] } = {}) {
    const pad = config.lanes.clearance;
    if (rect.x0 < config.board.marginX || rect.x1 > config.board.width - config.board.marginX) {
        return false;
    }
    for (const r of state.occupancy) {
        if (exceptBundles.includes(r.owner)) continue;
        if (rectsOverlap(rect, r, pad)) return false;
    }
    for (const c of state.chips) {
        if (exceptChips.includes(c)) continue;
        if (rectsOverlap(rect, { x0: c.x, x1: c.x + c.w, y0: c.y, y1: c.y + c.h }, pad)) {
            return false;
        }
    }
    return true;
}

function endsHorizontally(lane) {
    return Math.abs(lane[lane.length - 1][1] - lane[lane.length - 2][1]) < EPS;
}

// Pull an open end back by a random amount so sibling lanes don't all stop at
// the same x. Never back into the core zone, where ends may not float.
function staggerEnd(rng, state, lane, config) {
    if (!endsHorizontally(lane)) return;
    const last = lane[lane.length - 1];
    const prev = lane[lane.length - 2];
    const len = Math.abs(last[0] - prev[0]);
    const cut = Math.min(rng.range(...config.fray.endJitter), len - config.routing.minStraight * 0.6);
    if (cut <= 0) return;
    const nx = last[0] - Math.sign(last[0] - prev[0]) * cut;
    if (inCoreZone(state, nx, last[1])) return;
    last[0] = nx;
}

// Cut a lane to a fraction of its length; cuts inside diagonals snap back to
// the previous vertex so every end stays on a horizontal run. Cuts that
// would leave a bendless dash, or strand the end in the core zone, are
// skipped -- the lane keeps its wander.
function truncateLane(rng, state, lane, minStraight) {
    const lens = [];
    let total = 0;
    for (let i = 0; i + 1 < lane.length; i++) {
        const len = Math.hypot(lane[i + 1][0] - lane[i][0], lane[i + 1][1] - lane[i][1]);
        lens.push(len);
        total += len;
    }
    let target = total * rng.range(0.45, 0.8);
    if (target < minStraight) return;

    const out = [lane[0]];
    for (let i = 0; i + 1 < lane.length; i++) {
        if (target >= lens[i]) {
            out.push(lane[i + 1]);
            target -= lens[i];
            continue;
        }
        const p = lane[i];
        const q = lane[i + 1];
        if (Math.abs(q[1] - p[1]) < EPS && target > minStraight * 0.5) {
            out.push([p[0] + Math.sign(q[0] - p[0]) * target, p[1]]);
        }
        break;
    }
    if (out.length < 4) return;
    const end = out[out.length - 1];
    if (inCoreZone(state, end[0], end[1])) return;
    lane.length = 0;
    lane.push(...out);
}

// A peeled lane leaves the bundle at its end: one outward 45 deg jog plus a
// short run. Outward = away from the bundle center, which keeps the new
// segments on the bundle's fringe.
function peelLane(rng, state, config, bundle, lane, oSign) {
    if (!endsHorizontally(lane)) return;
    const last = lane[lane.length - 1];
    const dirX = Math.sign(last[0] - lane[lane.length - 2][0]);
    const dy = rng.range(...config.fray.stubJog);
    const run = rng.range(...config.fray.peelRun);
    const p1 = [last[0] + dy * dirX, last[1] + dy * oSign];
    const p2 = [p1[0] + run * dirX, p1[1]];

    if (inCoreZone(state, p2[0], p2[1])) return;
    const r1 = segRect(last, p1);
    const r2 = segRect(p1, p2);
    if (!areaClear(state, config, r1, { exceptBundles: [bundle] })) return;
    if (!areaClear(state, config, r2, { exceptBundles: [bundle] })) return;

    lane.push(p1, p2);
    state.occupancy.push({ ...r1, owner: bundle }, { ...r2, owner: bundle });
}

function growStubs(rng, state, config) {
    for (const chip of state.chips) {
        for (const side of ['left', 'right']) {
            const used = state.usedPins.get(chip)[side];
            const pins = chip.pins[side];
            const dirX = side === 'right' ? 1 : -1;
            const wallX = side === 'right' ? chip.x + chip.w : chip.x;

            for (let i = 0; i < pins.length; i++) {
                if (used.has(i) || !rng.chance(config.fray.stubChance)) continue;

                const pts = [[wallX, pins[i]]];
                let x = wallX + dirX * rng.range(...config.fray.stubLead);
                let y = pins[i];
                pts.push([x, y]);
                if (rng.chance(0.6)) {
                    const dy = rng.range(...config.fray.stubJog);
                    const sy = rng.sign();
                    x += dirX * dy;
                    y += sy * dy;
                    pts.push([x, y]);
                    if (rng.chance(0.5)) {
                        x += dirX * rng.range(...config.fray.stubTail);
                        pts.push([x, y]);
                    }
                }

                // A stub's free end is a dangler; the core zone allows none.
                if (inCoreZone(state, x, y)) continue;

                const rects = [];
                let ok = true;
                for (let k = 0; k + 1 < pts.length; k++) {
                    const r = segRect(pts[k], pts[k + 1]);
                    rects.push(r);
                    if (!areaClear(state, config, r, { exceptChips: [chip] })) {
                        ok = false;
                        break;
                    }
                }
                if (!ok) continue;

                const bundle = {
                    lanes: [pts],
                    sinkType: 'open',
                    guestList: [],
                    stub: true,
                    pins: [{ chip, side, index: i }],
                };
                state.bundles.push(bundle);
                for (const r of rects) state.occupancy.push({ ...r, owner: bundle });
                used.add(i);
            }
        }
    }
}

export function frayBundles(rng, state, config) {
    for (const bundle of state.bundles.slice()) {
        // Only still-dangling ends fray; lines hosting junctions must keep
        // their geometry intact or guests would be left floating.
        if (bundle.sinkType !== 'open' || bundle.guestList.length > 0) continue;
        const meanY = bundle.lanes.reduce((s, l) => s + l[0][1], 0) / bundle.lanes.length;
        for (const lane of bundle.lanes) {
            staggerEnd(rng, state, lane, config);
            if (rng.chance(config.fray.truncateChance)) {
                truncateLane(rng, state, lane, config.routing.minStraight);
            }
            if (rng.chance(config.fray.peelChance)) {
                const oSign = Math.sign(lane[0][1] - meanY) || rng.sign();
                peelLane(rng, state, config, bundle, lane, oSign);
            }
        }
    }
    growStubs(rng, state, config);
}
