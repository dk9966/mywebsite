// Flow planning and centerline routing.
//
// Lines depart chips in pin groups but every line routes *individually*: its
// own earliest-arrival Dijkstra over (level, free-interval) nodes, its own
// jog positions, its own slant bias. Because each routed line immediately
// occupies its levels, sibling lines get pushed onto neighboring corridors
// and diverge naturally -- they fan out instead of traveling as a rigid
// ribbon. Branches then fork off existing lines at 45 deg for the
// intertwined look of the reference.
//
// Routing happens in mirrored coordinates (x' = dir * x) so "forward" is
// always +x' regardless of whether the line travels left or right.

import { freeIntervals } from './corridors.js';
import { segRect, areaClear, coreZone } from './fray.js';

const SNAP = 6; // corridor levels closer than this to a pin level get dropped

function mirrorIntervals(intervals, dir) {
    if (dir === 1) return intervals.map((iv) => iv.slice());
    return intervals.map(([a, b]) => [-b, -a]).reverse();
}

function buildLevels(state, config, dir, keepYs) {
    const ys = keepYs.slice();
    for (const c of state.corridors) {
        if (ys.every((y) => Math.abs(y - c) >= SNAP)) ys.push(c);
    }
    ys.sort((a, b) => a - b);
    return ys.map((y) => ({
        y,
        intervals: mirrorIntervals(freeIntervals(y, state.chips, state.occupancy, config), dir),
    }));
}

// The source/target levels are cut by the line's own chip inflation; reopen
// the interval right up to the chip wall so the trace can actually depart
// from / arrive at the pin.
function openSourceInterval(level, sx, minStraight) {
    for (let i = 0; i < level.intervals.length; i++) {
        const [a, b] = level.intervals[i];
        if (a >= sx - 1 && a - sx < 80 && b - sx > minStraight) {
            level.intervals[i] = [sx, b];
            return i;
        }
        if (a <= sx && b - sx > minStraight) return i; // floating start mid-interval
    }
    return -1;
}

function openTargetInterval(level, tx, minStraight) {
    for (let i = 0; i < level.intervals.length; i++) {
        const [a, b] = level.intervals[i];
        if (b <= tx + 1 && tx - b < 80 && tx - a > minStraight) {
            level.intervals[i] = [a, tx];
            return i;
        }
        if (b >= tx && tx - a > minStraight) return i;
    }
    return -1;
}

// A jog's diagonal sweeps the space *between* two levels, which the interval
// tests don't see. These per-level-pair blockers close that gap: merged
// (mirrored) x-ranges of every rect whose inflated band intersects the open
// strip between the two level ys. A jog starting at xs occupies x in
// [xs, xs + dy], so it conflicts with a blocker [b0, b1] iff xs is inside
// (b0 - dy, b1).
function makeJogBlockers(state, config, levels, dir) {
    const inflate = config.lanes.clearance;
    const cache = new Map();
    return (li, lj) => {
        const k = li < lj ? li * 1024 + lj : lj * 1024 + li;
        if (cache.has(k)) return cache.get(k);
        const yLo = Math.min(levels[li].y, levels[lj].y) + 1;
        const yHi = Math.max(levels[li].y, levels[lj].y) - 1;

        const raw = [];
        for (const r of state.occupancy) {
            if (r.y0 - inflate < yHi && r.y1 + inflate > yLo) {
                raw.push([r.x0 - inflate, r.x1 + inflate]);
            }
        }
        for (const c of state.chips) {
            if (c.y - inflate < yHi && c.y + c.h + inflate > yLo) {
                raw.push([c.x - inflate, c.x + c.w + inflate]);
            }
        }

        const mirroredRaw = dir === 1 ? raw : raw.map(([a, b]) => [-b, -a]);
        mirroredRaw.sort((a, b) => a[0] - b[0]);
        const merged = [];
        for (const [a, b] of mirroredRaw) {
            const last = merged[merged.length - 1];
            if (last && a <= last[1]) last[1] = Math.max(last[1], b);
            else merged.push([a, b]);
        }
        cache.set(k, merged);
        return merged;
    };
}

// Smallest xs in [lo, hi] whose jog [xs, xs + dy] avoids all blockers.
function earliestFeasibleJog(lo, hi, dy, blockers) {
    let xs = lo;
    for (const [b0, b1] of blockers) {
        if (xs + dy <= b0) break; // sorted: no later blocker can conflict
        if (xs >= b1) continue;
        xs = b1;
        if (xs > hi) return null;
    }
    return xs <= hi ? xs : null;
}

// Sub-ranges of [lo, hi] where a jog start avoids all blockers.
function feasibleJogRanges(lo, hi, dy, blockers) {
    const out = [];
    let cur = lo;
    for (const [b0, b1] of blockers) {
        const winLo = b0 - dy;
        const winHi = b1;
        if (winLo > hi) break;
        if (winHi <= cur) continue;
        if (winLo > cur) out.push([cur, Math.min(winLo, hi)]);
        cur = Math.max(cur, winHi);
        if (cur > hi) break;
    }
    if (cur <= hi) out.push([cur, hi]);
    return out;
}

// Crowding: existing horizontal trace runs within crowdRadius of a level,
// as mirrored x-intervals. Deliberately NOT merged -- summing overlaps per
// neighbor makes the tax proportional to how many lines already travel
// there, so a third co-traveler pays more than a second. This is what
// breaks up bus-like packs of parallel straights.
function makeCrowd(state, config, levels, dir) {
    const radius = config.routing.crowdRadius;
    const cache = new Map();
    return (li) => {
        if (cache.has(li)) return cache.get(li);
        const y = levels[li].y;
        const ivs = [];
        for (const r of state.occupancy) {
            if (r.y1 - r.y0 > 1) continue; // diagonals don't read as parallel
            const dy = Math.abs(r.y0 - y);
            if (dy < 0.5 || dy > radius) continue; // own level is clearance's job
            ivs.push(dir === 1 ? [r.x0, r.x1] : [-r.x1, -r.x0]);
        }
        ivs.sort((p, q) => p[0] - q[0]);
        cache.set(li, ivs);
        return ivs;
    };
}

function overlapLen(a, b, intervals) {
    let sum = 0;
    for (const [c, d] of intervals) {
        if (c >= b) break;
        if (d <= a) continue;
        sum += Math.min(b, d) - Math.max(a, c);
    }
    return sum;
}

// Straight pin-to-pin span with nothing in the way (endpoint chips excluded
// by the asymmetric pads). This is how neighboring chips link across gaps
// that are far too tight for the interval machinery.
function directSpanClear(state, config, lo, hi, y) {
    const pad = config.lanes.clearance;
    for (const r of state.occupancy) {
        if (y >= r.y0 - pad && y <= r.y1 + pad && r.x0 - pad < hi - 2 && r.x1 + pad > lo + 2) {
            return false;
        }
    }
    const chipPad = pad + config.style.pinLength + 1;
    for (const c of state.chips) {
        if (y >= c.y - pad && y <= c.y + c.h + pad && c.x < hi - chipPad && c.x + c.w > lo + chipPad) {
            return false;
        }
    }
    return true;
}

function routeCenterline(rng, state, config, opts) {
    // minOpenSpan may be overridden per call: a follower peeling off a ribbon
    // already covered part of its span riding the prefix.
    const { srcX, srcY, dir, sink, noDirect = false, forceDirect = false, bias = null, minOpenSpan = config.routing.minOpenSpan } = opts;
    const { minStraight, jogPenalty, hopPenalty, reversePenalty, sameDirMax, hopNoise, openHops, maxRun, edgeRunChance, spinePull, crowdPenalty, crowdRadius, driftPenalty } = config.routing;
    const spineY = config.board.height / 2;
    // Horizontal travel gets taxed by how far the level sits from the spine.
    // Outside the chip band the levels are obstacle-free, so without this
    // tax the cheapest routes balloon around the chips; with it, threading
    // the gaps *between* chips is what wins, and detours snap back. Open
    // lines branch OUT of the spine band, so they pay a reduced rate -- but
    // enough that their fans settle just outside the band instead of
    // wandering off toward the board corners.
    const pull = sink.type === 'chip' ? spinePull : spinePull * 0.55;
    const levelTax = (y) => 1 + pull * Math.abs(y - spineY) / 100;
    // The reference's open cascades run up to three same-direction steps;
    // chip links stay at two so detours keep their calm, wavy shape.
    const dirMax = sink.type === 'chip' ? sameDirMax : sameDirMax + 1;
    const [jogMin, jogMax] = config.routing.jogSpan;
    // Each line samples its own bend rhythm: tight spacing gives staircase
    // cascades, wide spacing gives long calm runs -- siblings vary instead
    // of stepping in unison.
    const jogSpacing = rng.range(...config.routing.jogSpacing);
    const fx = (x) => dir * x;

    // A dead-straight shot is allowed but never guaranteed: most aligned
    // pairs still take a stepped route, like the reference. Tight gaps may
    // force it -- a detour in a short gap waves up and down.
    let allowDirect = !noDirect && (forceDirect || rng.chance(config.routing.directChance));
    if (allowDirect && sink.type === 'chip' && Math.abs(sink.y - srcY) < 0.5) {
        const lo = Math.min(srcX, sink.x);
        const hi = Math.max(srcX, sink.x);
        // A straight shot next to existing parallel runs would extend a
        // bus; crowded spans must take the stepped route instead. This
        // revokes allowDirect (not just the early return): the Dijkstra
        // could otherwise emit the identical 0-hop straight without ever
        // paying the crowd tax.
        let crowd = 0;
        for (const r of state.occupancy) {
            if (r.y1 - r.y0 > 1) continue;
            const dy = Math.abs(r.y0 - srcY);
            if (dy < 0.5 || dy > crowdRadius) continue;
            crowd += Math.max(0, Math.min(hi, r.x1) - Math.max(lo, r.x0));
        }
        if (!forceDirect && crowd >= 0.45 * (hi - lo)) {
            allowDirect = false;
        } else if (hi - lo >= minStraight * 0.8 && directSpanClear(state, config, lo, hi, srcY)) {
            return { points: [[srcX, srcY], [sink.x, srcY]], hops: 0 };
        }
    }

    const keepYs = sink.type === 'chip' && Math.abs(sink.y - srcY) > 0.5
        ? [srcY, sink.y]
        : [srcY];
    const levels = buildLevels(state, config, dir, keepYs);

    const sx = fx(srcX);
    const srcLevel = levels.findIndex((l) => Math.abs(l.y - srcY) < 0.5);
    const srcInterval = openSourceInterval(levels[srcLevel], sx, minStraight);
    if (srcInterval === -1) return null;

    let tgtLevel = -1;
    let tgtInterval = -1;
    let tx = 0;
    if (sink.type === 'chip') {
        tx = fx(sink.x);
        tgtLevel = levels.findIndex((l) => Math.abs(l.y - sink.y) < 0.5);
        tgtInterval = openTargetInterval(levels[tgtLevel], tx, minStraight);
        if (tgtInterval === -1) return null;
    }

    const jogBlockers = makeJogBlockers(state, config, levels, dir);
    const crowd = makeCrowd(state, config, levels, dir);

    // Earliest-arrival Dijkstra: node = (level, interval), label = leftmost
    // feasible x' plus accumulated cost (distance + jog penalty + noise).
    const key = (li, ii) => li * 64 + ii;
    const best = new Map();
    const start = {
        cost: 0,
        x: sx,
        hops: 0,
        li: srcLevel,
        ii: srcInterval,
        lastSign: 0,
        sameRun: 0,
        parent: null,
    };
    best.set(key(srcLevel, srcInterval), start);
    const queue = [start];

    while (queue.length) {
        let bi = 0;
        for (let i = 1; i < queue.length; i++) if (queue[i].cost < queue[bi].cost) bi = i;
        const cur = queue.splice(bi, 1)[0];
        if (best.get(key(cur.li, cur.ii)) !== cur) continue;

        const [, b] = levels[cur.li].intervals[cur.ii];
        for (let lj = 0; lj < levels.length; lj++) {
            if (lj === cur.li) continue;
            const dy = Math.abs(levels[lj].y - levels[cur.li].y);
            if (dy < jogMin || dy > jogMax) continue;
            const ivs = levels[lj].intervals;
            for (let jj = 0; jj < ivs.length; jj++) {
                const [c, d] = ivs[jj];
                // Consecutive slants must sit a full jogSpacing apart --
                // clustered bends read as waves, isolated ones as angles.
                const lo = Math.max(cur.x + (cur.parent ? jogSpacing : minStraight), c - dy);
                const xsMax = Math.min(b - dy, d - minStraight - dy);
                if (lo > xsMax) continue;
                const xsMin = earliestFeasibleJog(lo, xsMax, dy, jogBlockers(cur.li, lj));
                if (xsMin === null) continue;
                const arrive = xsMin + dy;
                // The reference drifts: short same-direction staircases are
                // twice as common as reversals there. Cap staircases at
                // sameDirMax, but charge for reversing -- an up-then-down
                // pair is the mountain silhouette we want to avoid.
                const sign = Math.sign(levels[lj].y - levels[cur.li].y);
                const sameRun = sign === cur.lastSign ? cur.sameRun + 1 : 1;
                if (sameRun > dirMax) continue;
                const reversed = cur.lastSign !== 0 && sign !== cur.lastSign;
                // Open lines branch OUT: jogs cutting back toward the spine
                // pay per px of span. Each fan leans away from the spine, so
                // groups above/below it (and left/right of a chip) mirror
                // each other -- cohesive sections that juxtapose, while
                // noise and jog placement keep every line unique. Chip
                // sinks are exempt: their shape is endpoint-driven.
                const inward = sink.type === 'open'
                    && sign !== (Math.sign(levels[cur.li].y - spineY) || sign);
                const cost = cur.cost + (arrive - cur.x) * levelTax(levels[cur.li].y)
                    + crowdPenalty * overlapLen(cur.x, arrive, crowd(cur.li))
                    + jogPenalty * dy + hopPenalty
                    + (reversed ? reversePenalty : 0)
                    + (inward ? driftPenalty * dy : 0)
                    + rng.range(0, hopNoise);
                const k = key(lj, jj);
                const prev = best.get(k);
                if (!prev || cost < prev.cost) {
                    const node = { cost, x: arrive, hops: cur.hops + 1, li: lj, ii: jj, lastSign: sign, sameRun, parent: cur };
                    best.set(k, node);
                    queue.push(node);
                }
            }
        }
    }

    // Pick the goal node and the final x'.
    let goal = null;
    let endX = 0;
    if (sink.type === 'chip') {
        goal = best.get(key(tgtLevel, tgtInterval));
        if (!goal || tx - goal.x < minStraight) return null;
        if (!allowDirect && goal.hops === 0) return null; // forced detour
        endX = tx;
    } else {
        const reached = [...best.values()];
        const maxHops = Math.max(...reached.map((n) => n.hops));
        // A hopless open route is a bare straight dash to nowhere; better
        // no line at all than that.
        if (maxHops === 0) return null;
        const want = Math.max(1, Math.min(rng.int(...openHops), maxHops));
        // Between the obstacles, near the spine, every line must connect on
        // both sides: inside the chip band an open end may stop before the
        // cluster or past it, never in the middle of it.
        const zone = coreZone(state);
        const inBand = (y) => y > zone.y0 && y < zone.y1;
        const enterX = dir === 1 ? zone.x0 : -zone.x1;
        const exitX = dir === 1 ? zone.x1 : -zone.x0;
        // An open line needs both its hops and room to run: ends that die
        // a few steps from their source read as orphaned clutter. If no
        // goal offers the wanted hops with runway (dense starts -- forks
        // mid-band -- rarely do), settle for fewer rather than no line.
        const fits = (n) => {
            const [, d] = levels[n.li].intervals[n.ii];
            const minEnd = Math.max(n.x + minStraight, sx + minOpenSpan);
            if (d < minEnd) return false;
            return !inBand(levels[n.li].y) || minEnd <= enterX || d >= exitX;
        };
        let cands = [];
        for (let w = want; w >= 1 && !cands.length; w--) {
            cands = reached.filter((n) => n.hops === w && fits(n));
        }
        if (!cands.length) return null;
        // Open ends branch out from the spine band: pick among the cheapest
        // arrivals. The accumulated cost already taxes against-drift jogs,
        // so goals reached by leaning with the section win. The final run
        // is untaxed by the Dijkstra, so charge its crowding here: a goal
        // whose runway already carries parallel lines would finish as a bus.
        const goalScore = (n) => n.cost
            + crowdPenalty * overlapLen(n.x, n.x + maxRun * 0.7, crowd(n.li));
        cands.sort((a, b) => goalScore(a) - goalScore(b));
        goal = rng.pick(cands.slice(0, 3));
        const [, d] = levels[goal.li].intervals[goal.ii];
        const domainEnd = fx(dir === 1 ? config.board.width - config.board.marginX : config.board.marginX);
        const reachesEdge = d >= domainEnd - 1;
        const minEnd = Math.max(goal.x + minStraight, sx + minOpenSpan);
        endX = reachesEdge && rng.chance(edgeRunChance)
            ? d
            : Math.min(d, Math.max(minEnd, goal.x + rng.range(minStraight, Math.min(d - goal.x, maxRun))));
        // The candidate filter guarantees one side of the cluster is
        // reachable; move an end that landed inside it to that side. Pushed
        // ends overshoot by a random amount so they don't align on the
        // cluster edge.
        if (inBand(levels[goal.li].y) && endX > enterX && endX < exitX) {
            endX = d >= exitX
                ? Math.min(d, exitX + rng.range(0, maxRun * 0.4))
                : Math.min(endX, enterX);
        }
    }

    // Backtrack the hop chain, then re-place each jog with random slack.
    // Each line gets its own bias exponent so siblings fan out differently.
    const chain = [];
    for (let n = goal; n; n = n.parent) chain.unshift(n);

    const jogs = [];
    for (let k = 1; k < chain.length; k++) {
        const from = chain[k - 1];
        const to = chain[k];
        const dy = Math.abs(levels[to.li].y - levels[from.li].y);
        jogs.push({
            dy,
            fromB: levels[from.li].intervals[from.ii][1],
            toC: levels[to.li].intervals[to.ii][0],
            toD: levels[to.li].intervals[to.ii][1],
            toY: levels[to.li].y,
            blockers: jogBlockers(from.li, to.li),
        });
    }

    let limit = endX - minStraight;
    const maxStarts = new Array(jogs.length);
    for (let k = jogs.length - 1; k >= 0; k--) {
        const j = jogs[k];
        maxStarts[k] = Math.min(j.fromB - j.dy, j.toD - minStraight - j.dy, limit - j.dy);
        limit = maxStarts[k] - jogSpacing;
    }

    const jogBias = bias ?? rng.range(...config.routing.slantBias);
    const pts = [[sx, levels[srcLevel].y]];
    let x = sx;
    let yCur = levels[srcLevel].y;
    for (let k = 0; k < jogs.length; k++) {
        const j = jogs[k];
        const lo = Math.max(x + (k > 0 ? jogSpacing : minStraight), j.toC - j.dy);
        if (maxStarts[k] < lo - 1e-6) return null;
        const ranges = feasibleJogRanges(lo, maxStarts[k], j.dy, j.blockers);
        if (!ranges.length) return null;
        const total = ranges.reduce((s, [a, b]) => s + (b - a), 0);
        let t = total * rng.float() ** jogBias;
        let xs = ranges[0][0];
        for (const [a, b] of ranges) {
            if (t <= b - a) {
                xs = a + t;
                break;
            }
            t -= b - a;
        }
        pts.push([xs, yCur]);
        x = xs + j.dy;
        yCur = j.toY;
        pts.push([x, yCur]);
    }
    pts.push([endX, yCur]);

    return {
        points: pts.map(([px, py]) => [fx(px), py]),
        hops: jogs.length,
    };
}

// --- pin bookkeeping -------------------------------------------------------

function freeRunStarts(state, chip, side, n, config) {
    const pins = chip.pins[side];
    const used = state.usedPins.get(chip)[side];
    if (used.size + n > config.lanes.maxPerEdge) return [];
    const starts = [];
    for (let s = 0; s + n <= pins.length; s++) {
        let free = true;
        for (let k = s; k < s + n; k++) if (used.has(k)) { free = false; break; }
        if (free) starts.push(s);
    }
    return starts;
}

function pickPinRun(rng, state, config, chip, side, n) {
    const starts = freeRunStarts(state, chip, side, n, config);
    if (!starts.length) return null;
    return { start: rng.pick(starts), n };
}

function runCenter(chip, side, start, n) {
    const pins = chip.pins[side];
    return (pins[start] + pins[start + n - 1]) / 2;
}

// Free run whose center sits closest to refY -- aligned runs route with few
// (often zero) jogs, which is what makes chip-to-chip connections succeed.
function pickAlignedRun(state, config, chip, side, n, refY) {
    const starts = freeRunStarts(state, chip, side, n, config);
    if (!starts.length) return null;
    let best = starts[0];
    for (const s of starts) {
        if (Math.abs(runCenter(chip, side, s, n) - refY) < Math.abs(runCenter(chip, side, best, n) - refY)) {
            best = s;
        }
    }
    return { start: best, n };
}

function markPin(state, chip, side, index) {
    state.usedPins.get(chip)[side].add(index);
    return { chip, side, index };
}

// Lines already connecting this chip pair. Capped at flows.maxPairLinks
// everywhere: a pair of parallel traces is the reference texture, anything
// wider reads as a bus no matter how the individual lines wiggle.
function pairLinks(state, a, b) {
    let n = 0;
    for (const bundle of state.bundles) {
        let hasA = false;
        let hasB = false;
        for (const p of bundle.pins) {
            if (p.chip === a) hasA = true;
            else if (p.chip === b) hasB = true;
        }
        if (hasA && hasB) n += 1;
    }
    return n;
}

// --- ribbon co-travel -------------------------------------------------------

function translatePath(points, dy) {
    return points.map(([x, y]) => [x, y + dy]);
}

// Prefix of an octilinear path cut at `dist` of x-travel from its start.
// Routed paths are x-monotonic in their travel direction, so the cut point
// is unique; cuts that land on a diagonal or too close behind a bend
// return null and the caller retries with a shorter prefix.
function cutPrefix(points, dir, dist, minStraight) {
    const x0 = points[0][0];
    const out = [points[0].slice()];
    for (let i = 0; i + 1 < points.length; i++) {
        const p = points[i];
        const q = points[i + 1];
        if (dir * (q[0] - x0) < dist) {
            out.push(q.slice());
            continue;
        }
        if (Math.abs(q[1] - p[1]) > 1e-6) return null;
        if (dist - dir * (p[0] - x0) < minStraight * 0.5) return null;
        out.push([x0 + dir * dist, p[1]]);
        return out;
    }
    return null;
}

// Every segment of a candidate polyline is clear of the world. Ribbon
// siblings are excepted: pitch-offset copies never truly collide, but
// parallel diagonals have overlapping bounding boxes that would veto every
// copy. Sibling remainders all start beyond this polyline's end (peel
// order is longest-prefix first), so the exception hides no real overlap.
function pathClear(state, config, points, exceptBundles, exceptChips) {
    for (let i = 0; i + 1 < points.length; i++) {
        const rect = segRect(points[i], points[i + 1]);
        if (!areaClear(state, config, rect, { exceptBundles, exceptChips })) return false;
    }
    return true;
}

// --- line assembly ---------------------------------------------------------

function addBundle(state, bundle) {
    bundle.guestList = []; // lines forking from / merging into this one
    bundle.pins = bundle.pins ?? []; // chip pins this line occupies
    state.bundles.push(bundle);
    for (const lane of bundle.lanes) {
        for (let i = 0; i + 1 < lane.length; i++) {
            const [x1, y1] = lane[i];
            const [x2, y2] = lane[i + 1];
            state.occupancy.push({
                x0: Math.min(x1, x2),
                x1: Math.max(x1, x2),
                y0: Math.min(y1, y2),
                y1: Math.max(y1, y2),
                owner: bundle,
            });
        }
    }
    return bundle;
}

// A pin group departs as a ribbon. The leader routes for real -- chip sink
// if one was found, open otherwise -- and every follower rides a
// pitch-offset copy of the leader's path: the whole way when it owns a
// pair-budget slot on the target chip (endpoints land on the pitch-aligned
// pins by construction), or up to a staggered peel point where it breaks
// into an open route of its own. The outermost pin peels first and the
// leader's pitch-mate rides longest, so ribbons fray outward one line at a
// time, like the reference. Followers that can't hold the ribbon (blocked
// copy, failed remainder) fall back to routing individually.
function routeChipFlow(rng, state, config, chip, side) {
    let run = null;
    for (let n = rng.int(...config.lanes.bundleSize); n >= 1; n--) {
        run = pickPinRun(rng, state, config, chip, side, n);
        if (run) break;
    }
    if (!run) return;

    const dir = side === 'right' ? 1 : -1;
    const tSide = dir === 1 ? 'left' : 'right';
    const srcX = side === 'right' ? chip.x + chip.w : chip.x;
    const pins = chip.pins[side].slice(run.start, run.start + run.n);

    let target = null;
    let targetRun = null;
    let chipSlots = 0;
    if (rng.weighted(config.flows.sinkMix) === 'chip') {
        const refY = runCenter(chip, side, run.start, run.n);
        // Skip near neighbors (the bootstrap already links those): groups
        // need travel distance to diverge instead of stacking into a bus.
        const candidates = state.chips.filter(
            (c) => c !== chip && (dir === 1 ? c.x > srcX + 140 : c.x + c.w < srcX - 140),
        );
        for (const cand of rng.shuffle(candidates)) {
            // Only the pair budget's worth of pins may land on this target;
            // the rest of the ribbon peels off and frays away.
            const budget = config.flows.maxPairLinks - pairLinks(state, chip, cand);
            if (budget < 1) continue;
            const tRun = pickAlignedRun(state, config, cand, tSide, run.n, refY);
            if (tRun) {
                target = cand;
                targetRun = tRun;
                chipSlots = budget;
                break;
            }
        }
    }
    const tPins = target
        ? target.pins[tSide].slice(targetRun.start, targetRun.start + targetRun.n)
        : null;
    const tX = target ? (dir === 1 ? target.x : target.x + target.w) : 0;

    // Departures count across the whole edge, not just this group: a third
    // line leaving any edge must slant away immediately or the edge's pin
    // band reads as a bus regardless of which group each line belongs to.
    const departed = state.usedPins.get(chip)[side].size;
    const bias = (k) => (departed + k >= 2 ? rng.range(4, 6) : null);

    // Leader: the first pin that routes at all anchors the ribbon.
    let leader = null;
    let leaderK = -1;
    let connected = false;
    for (let k = 0; k < pins.length && !leader; k++) {
        const base = { srcX, srcY: pins[k], dir, bias: bias(k) };
        if (tPins) {
            leader = routeCenterline(rng, state, config, {
                ...base,
                sink: { type: 'chip', x: tX, y: tPins[k] },
            });
            connected = !!leader;
        }
        if (!leader) leader = routeCenterline(rng, state, config, { ...base, sink: { type: 'open' } });
        if (leader) leaderK = k;
    }
    if (!leader) return;

    const leaderPins = [markPin(state, chip, side, run.start + leaderK)];
    if (connected) leaderPins.push(markPin(state, target, tSide, targetRun.start + leaderK));
    const group = [addBundle(state, {
        lanes: [leader.points],
        dir,
        sinkType: connected ? 'chip' : 'open',
        pins: leaderPins,
    })];

    // Peel schedule: full riders (paired chip link) first, then open
    // co-travelers longest-prefix first, so every peeled remainder routes
    // with all longer prefixes already occupying space.
    const open = [];
    const followers = [];
    let slots = connected ? chipSlots - 1 : 0;
    for (let k = leaderK + 1; k < pins.length; k++) {
        if (slots > 0) {
            followers.push({ k, frac: 1 });
            slots -= 1;
        } else {
            open.push(k);
        }
    }
    for (let i = 0; i < open.length; i++) {
        followers.push({ k: open[i], frac: (open.length - i - rng.range(0.15, 0.85)) / open.length });
    }
    followers.sort((a, b) => b.frac - a.frac);

    const ms = config.routing.minStraight;
    const span = dir * (leader.points[leader.points.length - 1][0] - srcX);
    let directUsed = leader.hops === 0;

    for (const f of followers) {
        const dy = pins[f.k] - pins[leaderK];
        const shifted = translatePath(leader.points, dy);
        let made = null;

        if (f.frac >= 1) {
            if (pathClear(state, config, shifted, group, [chip, target])) {
                made = { points: shifted, toChip: true };
            }
        } else {
            for (const scale of [1, 0.7, 0.45]) {
                const cut = Math.max(ms * 1.5, f.frac * scale * span);
                if (cut > span * 0.85) continue;
                const prefix = cutPrefix(shifted, dir, cut, ms);
                if (!prefix || !pathClear(state, config, prefix, group, [chip])) continue;
                const [px, py] = prefix[prefix.length - 1];
                const rest = routeCenterline(rng, state, config, {
                    srcX: px,
                    srcY: py,
                    dir,
                    sink: { type: 'open' },
                    minOpenSpan: Math.max(config.routing.minOpenSpanFloor, config.routing.minOpenSpan - cut),
                });
                if (!rest) continue;
                made = { points: prefix.concat(rest.points.slice(1)), toChip: false };
                break;
            }
        }

        if (!made) {
            // Ribbon broken: route this pin individually, as before.
            const base = { srcX, srcY: pins[f.k], dir, noDirect: directUsed, bias: bias(f.k) };
            let result = null;
            if (f.frac >= 1) {
                result = routeCenterline(rng, state, config, {
                    ...base,
                    sink: { type: 'chip', x: tX, y: tPins[f.k] },
                });
            }
            const toChip = !!result;
            if (result && result.hops === 0) directUsed = true;
            if (!result) result = routeCenterline(rng, state, config, { ...base, sink: { type: 'open' } });
            if (!result) continue;
            made = { points: result.points, toChip };
        }

        const pinRefs = [markPin(state, chip, side, run.start + f.k)];
        if (made.toChip) pinRefs.push(markPin(state, target, tSide, targetRun.start + f.k));
        group.push(addBundle(state, {
            lanes: [made.points],
            dir,
            sinkType: made.toChip ? 'chip' : 'open',
            pins: pinRefs,
        }));
    }
}

// Branches fork off an existing line mid-segment: a 45 deg diagonal down/up
// to a nearby corridor, then an open route of its own. The fork itself is a
// mesh junction, so a branch is born with its start anchored. xHint (from
// the balance pass) restricts forks to a sparse column.
export function spawnBranches(rng, state, config, count, xHint = null) {
    const ms = config.routing.minStraight;
    const [jogMin, jogMax] = config.routing.jogSpan;
    let spawned = 0;

    for (let i = 0; i < count; i++) {
        for (let attempt = 0; attempt < 24; attempt++) {
            // Prefer anchored parents -- a fork on a dangler protects it from
            // the anchored-share cleanup. Fall back to any non-stub line.
            let parents = state.bundles.filter((b) => !b.stub && b.sinkType !== 'open');
            if (!parents.length) parents = state.bundles.filter((b) => !b.stub);
            if (!parents.length) return spawned;
            const parent = rng.pick(parents);
            const line = parent.lanes[0];

            // Forks only live between the obstacles: the host run must sit
            // inside the cluster band and the fork point inside its x-range.
            // Density grows in the middle and the margins stay calm -- a
            // trailing line past the outermost chip never sprouts branches.
            const zone = coreZone(state);
            const segs = [];
            for (let s = 0; s + 1 < line.length; s++) {
                const [x1, y1] = line[s];
                const [x2, y2] = line[s + 1];
                if (Math.abs(y2 - y1) > 1e-6) continue;
                if (y1 <= zone.y0 || y1 >= zone.y1) continue;
                const lo = Math.max(Math.min(x1, x2) + ms, zone.x0);
                const hi = Math.min(Math.max(x1, x2) - ms, zone.x1);
                if (hi - lo < ms) continue;
                if (xHint !== null && (xHint < lo || xHint > hi)) continue;
                segs.push({ lo, hi, y: y1, dirX: Math.sign(x2 - x1) });
            }
            if (!segs.length) continue;
            // Length-weighted pick: long straight runs are exactly where a
            // fork adds the most contrast.
            const total = segs.reduce((s, g) => s + (g.hi - g.lo), 0);
            let tPick = rng.float() * total;
            let seg = segs[0];
            for (const cand of segs) {
                if (tPick <= cand.hi - cand.lo) {
                    seg = cand;
                    break;
                }
                tPick -= cand.hi - cand.lo;
            }
            const { lo: pxLo, hi: pxHi, y: py, dirX } = seg;

            // The fork diagonal may run half again longer than a routed jog:
            // a branch born mid-band needs the reach to clear the dense
            // spine in one deliberate slant.
            const levelCands = state.corridors.filter((c) => {
                const dy = Math.abs(c - py);
                return dy >= jogMin && dy <= jogMax * 1.5;
            });
            if (!levelCands.length) continue;
            // A split diverges outward: the fork's first move heads away
            // from the spine -- same lean as its section's other open ends,
            // so the branch peels off with the local flow instead of
            // cutting back into the dense band.
            const spineY = config.board.height / 2;
            const outward = levelCands.filter((c) => Math.sign(c - py) === Math.sign(py - spineY));
            const forkLevels = outward.length ? outward : levelCands;

            // The band is dense: a single random fork point usually collides
            // with a neighbor, so probe several placements before giving up
            // on this segment.
            let fork = null;
            for (let probe = 0; probe < 6 && !fork; probe++) {
                const px = rng.range(pxLo, pxHi);
                const cy = rng.pick(forkLevels);
                const forkX = px + dirX * Math.abs(cy - py);
                if (areaClear(state, config, segRect([px, py], [forkX, cy]), { exceptBundles: [parent] })) {
                    fork = { px, cy, forkX };
                }
            }
            if (!fork) continue;

            const result = routeCenterline(rng, state, config, {
                srcX: fork.forkX,
                srcY: fork.cy,
                dir: dirX,
                sink: { type: 'open' },
            });
            if (!result) continue;

            result.points.unshift([fork.px, py]);
            parent.guestList.push(
                addBundle(state, { lanes: [result.points], dir: dirX, sinkType: 'open', branch: true }),
            );
            spawned += 1;
            break;
        }
    }
    return spawned;
}

// Sign and length of the line's trailing same-direction slant streak, so
// merge diagonals respect the same cap as routed jogs.
function trailingSlants(line) {
    let sign = 0;
    let run = 0;
    for (let i = line.length - 2; i >= 0; i--) {
        const dy = line[i + 1][1] - line[i][1];
        if (Math.abs(dy) < 1e-6) continue;
        const s = Math.sign(dy);
        if (sign === 0) {
            sign = s;
            run = 1;
        } else if (s === sign) {
            run += 1;
        } else {
            break;
        }
    }
    return { sign, run };
}

// One anchoring attempt at the line's current end: trim/extend the final
// run, then land on an unused chip pin facing the travel direction. A line
// must never terminate on another line -- that reads as two flows
// consolidating into one. Junctions only ever split: the host keeps going
// and a branch diverges off it. So the only legal terminations for an end
// are a chip pin or open space.
function tryMergeAt(state, config, bundle, line) {
    const ms = config.routing.minStraight;
    const [jogMin] = config.routing.jogSpan;
    const jogMax = config.mesh.mergeJogMax;
    const { mergeReach, mergeCandidates } = config.mesh;

    const last = line[line.length - 1];
    const prev = line[line.length - 2];
    const dirX = Math.sign(last[0] - prev[0]);
    const y = last[1];
    const trailing = trailingSlants(line);
    const slantBlocked = (ty) => trailing.run >= config.routing.sameDirMax
        && Math.sign(ty - y) === trailing.sign;

    const pinSide = dirX === 1 ? 'left' : 'right';
    const srcChip = bundle.pins[0]?.chip ?? null;
    const tries = [];
    for (const chip of state.chips) {
        const wallX = dirX === 1 ? chip.x : chip.x + chip.w;
        if ((wallX - last[0]) * dirX <= 0 || Math.abs(wallX - last[0]) > mergeReach) continue;
        // Landing here would exceed the pair budget -- the lines between
        // these two chips already read as a pair.
        if (srcChip && pairLinks(state, srcChip, chip) >= config.flows.maxPairLinks) continue;
        const used = state.usedPins.get(chip)[pinSide];
        const pins = chip.pins[pinSide];
        for (let i = 0; i < pins.length; i++) {
            if (used.has(i)) continue;
            const dy = Math.abs(pins[i] - y);
            if (dy > 0.5 && (dy < jogMin || dy > jogMax || slantBlocked(pins[i]))) continue;
            tries.push({
                chip,
                pinSide,
                pinIndex: i,
                ty: pins[i],
                dy,
                wallX,
                cost: Math.abs(wallX - last[0]) + dy,
            });
        }
    }

    tries.sort((a, b) => a.cost - b.cost);
    for (const t of tries.slice(0, mergeCandidates)) {
        if (tryPinMerge(state, config, bundle, line, t, { dirX, ms })) return true;
    }
    return false;
}

// End a dangling line on an unused pin: optional 45 deg jog onto the pin
// level, then a short lead into the chip wall.
function tryPinMerge(state, config, bundle, line, t, { dirX, ms }) {
    const last = line[line.length - 1];
    const prev = line[line.length - 2];
    const y = last[1];
    const { chip, ty, dy, wallX } = t;
    const except = { exceptBundles: [bundle], exceptChips: [chip] };

    if (dy <= 0.5) {
        // Already on the pin level: extend straight into the wall.
        if ((wallX - prev[0]) * dirX < ms) return false;
        if (!areaClear(state, config, segRect(last, [wallX, y]), except)) return false;
        last[0] = wallX;
        state.occupancy.push({ ...segRect(prev, last), owner: bundle });
    } else {
        const lead = 14; // straight run between the jog and the wall
        const xs = wallX - dirX * (dy + lead);
        if ((xs - prev[0]) * dirX < ms * 0.5) return false;
        const jx = xs + dirX * dy;
        const diagRect = segRect([xs, y], [jx, ty]);
        const leadRect = segRect([jx, ty], [wallX, ty]);
        const extends_ = (xs - last[0]) * dirX > 0;
        if (extends_ && !areaClear(state, config, segRect(last, [xs, y]), except)) return false;
        if (!areaClear(state, config, diagRect, except)) return false;
        if (!areaClear(state, config, leadRect, except)) return false;
        last[0] = xs;
        line.push([jx, ty], [wallX, ty]);
        state.occupancy.push(
            { ...segRect(prev, last), owner: bundle },
            { ...diagRect, owner: bundle },
            { ...leadRect, owner: bundle },
        );
    }

    bundle.pins.push(markPin(state, chip, t.pinSide, t.pinIndex));
    bundle.sinkType = 'chip';
    return true;
}

// Anchor dangling ends: each one tries to land on an unused chip pin,
// sacrificing its final jog and retrying from the shortened end -- unless
// it hosts guests, whose fork junctions sit on that geometry. The trims are
// speculative: an end that never finds a pin gets its full wander back and
// stays open to fray later.
export function mergeDanglingEnds(state, config) {
    for (const bundle of state.bundles) {
        if (bundle.sinkType !== 'open' || bundle.stub) continue;
        const line = bundle.lanes[0];
        const saved = line.map((p) => p.slice());
        const maxTrims = bundle.guestList.length > 0 ? 1 : 4;
        let landed = false;
        for (let trim = 0; trim < maxTrims; trim++) {
            const last = line[line.length - 1];
            const prev = line[line.length - 2];
            const horizontal = Math.abs(last[1] - prev[1]) < 1e-6;
            if (horizontal && tryMergeAt(state, config, bundle, line)) {
                landed = true;
                break;
            }
            if (line.length < 4) break;
            if (trim + 1 < maxTrims) line.splice(line.length - 2, 2);
        }
        if (!landed) {
            line.length = 0;
            line.push(...saved);
        }
    }
}

// Bootstrap spine: connect neighboring chips directly so the mesh has
// anchored material from the start -- branch parents prefer it. Pin pairs
// are tried smallest-dy first: grid alignment makes
// dy = 0 pairs common, and those connect with a single straight run even
// across the tightest gaps.
function connectPair(rng, state, config, a, b, { stitch = false } = {}) {
    // Tight gaps can't fan visually, so close neighbors get a single link;
    // anything more stacks into a bus. Roomy gaps take the full pair budget
    // -- the spine is the backbone, so it gets all the material the budget
    // allows. The budget counts links made by earlier passes too.
    const gap = b.x - (a.x + a.w);
    const budget = config.flows.maxPairLinks - pairLinks(state, a, b);
    const want = Math.min(stitch || gap < config.routing.pairGapStitch ? 1 : config.flows.maxPairLinks, budget);
    const usedA = state.usedPins.get(a).right;
    const usedB = state.usedPins.get(b).left;

    const pairs = [];
    for (let i = 0; i < a.pins.right.length; i++) {
        if (usedA.has(i)) continue;
        for (let j = 0; j < b.pins.left.length; j++) {
            if (usedB.has(j)) continue;
            const dy = Math.abs(a.pins.right[i] - b.pins.left[j]);
            if (dy <= config.routing.pinDyMax) pairs.push({ i, j, dy });
        }
    }
    pairs.sort((p, q) => p.dy - q.dy);

    let made = 0;
    const cap = config.lanes.maxPerEdge;
    for (const p of pairs) {
        if (made >= want || usedA.size >= cap || usedB.size >= cap) break;
        if (usedA.has(p.i) || usedB.has(p.j)) continue;
        const result = routeCenterline(rng, state, config, {
            srcX: a.x + a.w,
            srcY: a.pins.right[p.i],
            dir: 1,
            sink: { type: 'chip', x: b.x, y: b.pins.left[p.j] },
            // One straight shot per pair reads as a deliberate link; a wall
            // of parallel straights reads as a bus, so the rest must detour,
            // slanting away early.
            noDirect: made > 0,
            forceDirect: made === 0 && (stitch || gap < config.routing.pairGapDirect),
            bias: made >= 2 ? rng.range(4, 6) : null,
        });
        if (!result) continue;
        addBundle(state, {
            lanes: [result.points],
            dir: 1,
            sinkType: 'chip',
            pins: [markPin(state, a, 'right', p.i), markPin(state, b, 'left', p.j)],
        });
        made += 1;
    }
    return made;
}

export function planFlows(rng, state, config) {
    // Spine: every chip links forward to the y-nearest chip of the next
    // station; an occasional cross link to the station sibling adds the
    // weave. Stacked pairs share an x, so x-sorting alone can't chain them.
    const stations = new Map();
    for (const chip of state.chips) {
        if (!stations.has(chip.station)) stations.set(chip.station, []);
        stations.get(chip.station).push(chip);
    }
    const order = [...stations.keys()].sort((a, b) => a - b);
    for (let i = 0; i + 1 < order.length; i++) {
        const next = stations.get(order[i + 1]);
        for (const chip of stations.get(order[i])) {
            const cy = chip.y + chip.h / 2;
            const sorted = [...next].sort(
                (a, b) => Math.abs(a.y + a.h / 2 - cy) - Math.abs(b.y + b.h / 2 - cy),
            );
            connectPair(rng, state, config, chip, sorted[0]);
            if (sorted.length > 1 && rng.chance(0.5)) {
                connectPair(rng, state, config, chip, sorted[1]);
            }
        }
    }

    // Branch out from the spine while it is still the only material on the
    // board: every parent is a spine link, and the open routes still have
    // room to escape the band. Branching after the chip flows fill the
    // band fails far more often than it succeeds.
    const branchTotal = rng.int(...config.flows.branchCount);
    const branchedEarly = spawnBranches(rng, state, config, Math.ceil(branchTotal * 0.7));

    // Outward-facing edges (no pins beyond them to land on) spawn doomed
    // danglers, so they get at most one damped flow.
    const facesOutward = (chip, side) => (side === 'left'
        ? !state.chips.some((c) => c.x + c.w < chip.x)
        : !state.chips.some((c) => c.x > chip.x + chip.w));

    const edges = [];
    for (const chip of state.chips) {
        edges.push({ chip, side: 'left' }, { chip, side: 'right' });
    }
    // Flow budget scales with the chip count: a sparse board has the same
    // area but fewer destinations, so an unscaled budget turns its few
    // edges into hairy fans of open ends.
    const edgeCap = Math.round(state.chips.length / 2.5);
    for (const { chip, side } of rng.shuffle(edges)) {
        // Outward edges always fan toward the board edge -- the reference
        // tapers off both ends with open lines.
        const count = facesOutward(chip, side)
            ? 1
            : Math.min(rng.int(...config.flows.perEdge), edgeCap);
        for (let i = 0; i < count; i++) routeChipFlow(rng, state, config, chip, side);
    }

    // No chip may end up orphaned: force a flow from any chip whose pins
    // are all unused, trying the side facing the board center first.
    for (const chip of state.chips) {
        const used = state.usedPins.get(chip);
        if (used.left.size + used.right.size > 0) continue;
        const center = chip.x + chip.w / 2 < config.board.width / 2;
        for (const side of center ? ['right', 'left'] : ['left', 'right']) {
            routeChipFlow(rng, state, config, chip, side);
            if (used.left.size + used.right.size > 0) break;
        }
    }

    connectComponents(rng, state, config);

    // Anchor ends, then spend whatever branch budget the early pass could
    // not: late forks land on the flow lines too, and their ends try for
    // pins in the second merge pass.
    mergeDanglingEnds(state, config);
    spawnBranches(rng, state, config, branchTotal - branchedEarly);
    mergeDanglingEnds(state, config);
}

// The board must read as ONE web. Union chips over shared bundles (pins) and
// fork relations, then stitch neighboring components together with extra
// chip-to-chip links, closest pair first.
function connectComponents(rng, state, config) {
    const parent = new Map();
    const find = (k) => {
        while (parent.get(k) !== k) {
            parent.set(k, parent.get(parent.get(k)));
            k = parent.get(k);
        }
        return k;
    };
    const union = (a, b) => parent.set(find(a), find(b));

    for (const chip of state.chips) parent.set(chip, chip);
    for (const b of state.bundles) parent.set(b, b);
    for (const b of state.bundles) {
        for (const p of b.pins) union(b, p.chip);
        for (const g of b.guestList) union(b, g);
    }

    for (let guard = 0; guard < state.chips.length; guard++) {
        const comps = new Map();
        for (const chip of state.chips) {
            const root = find(chip);
            if (!comps.has(root)) comps.set(root, []);
            comps.get(root).push(chip);
        }
        if (comps.size <= 1) return;

        // Try cross-component chip pairs closest-first until one connects.
        const groups = [...comps.values()];
        const pairs = [];
        for (let i = 0; i < groups.length; i++) {
            for (let j = i + 1; j < groups.length; j++) {
                for (const a of groups[i]) {
                    for (const b of groups[j]) {
                        const [l, r] = a.x < b.x ? [a, b] : [b, a];
                        const gap = r.x - (l.x + l.w);
                        if (gap < 20) continue;
                        pairs.push({ l, r, d: gap + Math.abs(a.y - b.y) });
                    }
                }
            }
        }
        pairs.sort((a, b) => a.d - b.d);

        let stitched = false;
        for (const { l, r } of pairs.slice(0, 12)) {
            if (connectPair(rng, state, config, l, r, { stitch: true })) {
                union(l, r);
                stitched = true;
                break;
            }
        }
        if (!stitched) return;
    }
}
