// Connection planning. Chips join an MST (plus a few extra short edges) and
// each edge becomes a ribbon bus of pin pairs on facing sides. Leftover chip
// pins are grouped into runs of adjacent pins -- each group fans out as one
// parallel ribbon -- and small-part pads are nominated for short traces.

export function buildNetlist(rng, parts, config) {
    const chips = parts.filter((p) => p.pinRows);
    const buses = [];
    for (const [a, b] of chipEdges(rng, chips, config)) {
        const bus = makeBus(rng, a, b, config);
        if (bus) buses.push(bus);
    }

    const smalls = [];
    for (const p of parts) {
        if (p.pinRows) continue;
        for (const pin of p.pins) {
            if (rng.chance(config.net.smallChance)) smalls.push(pin);
        }
    }

    const soloGroups = [];
    for (const c of chips) {
        for (const side of ['top', 'right', 'bottom', 'left']) {
            for (const run of freeRuns(c, side, config.pins.pitch)) {
                for (const group of chunkRun(rng, run, config)) {
                    if (rng.chance(config.net.soloChance)) soloGroups.push(group);
                }
            }
        }
    }

    return { buses, smalls, soloGroups: rng.shuffle(soloGroups) };
}

// Maximal runs of adjacent (one pitch apart) free pins along a chip side.
function freeRuns(chip, side, pitch) {
    const free = freePinsOnSide(chip, side);
    const horizontal = side === 'top' || side === 'bottom';
    const runs = [];
    let run = [];
    for (const p of free) {
        const prev = run[run.length - 1];
        const gap = prev ? (horizontal ? p.cx - prev.cx : p.cy - prev.cy) : 0;
        if (prev && gap !== pitch) {
            runs.push(run);
            run = [];
        }
        run.push(p);
    }
    if (run.length) runs.push(run);
    return runs;
}

function chunkRun(rng, run, config) {
    const groups = [];
    let i = 0;
    while (i < run.length) {
        const size = Math.min(run.length - i, rng.weighted(config.net.soloGroupSizes));
        groups.push(run.slice(i, i + size));
        i += size;
    }
    return groups;
}

function chipEdges(rng, chips, config) {
    if (chips.length < 2) return [];
    const dist = (a, b) => Math.hypot(a.cx - b.cx, a.cy - b.cy);

    // Prim's MST over chip centers.
    const inTree = new Set([chips[0]]);
    const edges = [];
    while (inTree.size < chips.length) {
        let best = null;
        for (const a of inTree) {
            for (const b of chips) {
                if (inTree.has(b)) continue;
                if (!best || dist(a, b) < dist(best[0], best[1])) best = [a, b];
            }
        }
        edges.push(best);
        inTree.add(best[1]);
    }

    // A few extra short edges for loops, like the reference's cross-links.
    const used = new Set(edges.map(([a, b]) => key(a, b)));
    const candidates = [];
    for (let i = 0; i < chips.length; i++) {
        for (let j = i + 1; j < chips.length; j++) {
            if (!used.has(key(chips[i], chips[j]))) candidates.push([chips[i], chips[j]]);
        }
    }
    candidates.sort((p, q) => dist(...p) - dist(...q));
    edges.push(...candidates.slice(0, rng.int(...config.net.extraEdges)));
    return edges;
}

function key(a, b) {
    return a.cellX * 1e6 + a.cellY < b.cellX * 1e6 + b.cellY
        ? `${a.cellX},${a.cellY}|${b.cellX},${b.cellY}`
        : `${b.cellX},${b.cellY}|${a.cellX},${a.cellY}`;
}

const SIDE_NORMALS = {
    top: [0, -1],
    bottom: [0, 1],
    left: [-1, 0],
    right: [1, 0],
};

// Sides of `chip` ranked by how well they face direction (dx, dy).
function facingSides(chip, dx, dy) {
    const len = Math.hypot(dx, dy) || 1;
    const sides = [...new Set(chip.pins.map((p) => p.side))];
    return sides.sort((s1, s2) => score(s2) - score(s1));

    function score(side) {
        const [nx, ny] = SIDE_NORMALS[side];
        return (nx * dx + ny * dy) / len;
    }
}

function freePinsOnSide(chip, side) {
    const pins = chip.pins.filter((p) => p.side === side && !p.used);
    const horizontal = side === 'top' || side === 'bottom';
    return pins.sort((a, b) => (horizontal ? a.cx - b.cx : a.cy - b.cy));
}

function centeredRun(arr, n) {
    const start = Math.floor((arr.length - n) / 2);
    return arr.slice(start, start + n);
}

function makeBus(rng, a, b, config) {
    const dx = b.cx - a.cx;
    const dy = b.cy - a.cy;
    let pinsA = [];
    let pinsB = [];
    for (const side of facingSides(a, dx, dy)) {
        pinsA = freePinsOnSide(a, side);
        if (pinsA.length) break;
    }
    for (const side of facingSides(b, -dx, -dy)) {
        pinsB = freePinsOnSide(b, side);
        if (pinsB.length) break;
    }

    const n = Math.min(pinsA.length, pinsB.length, rng.int(...config.net.busSize));
    if (n < 1) return null;
    const runA = centeredRun(pinsA, n);
    const runB = centeredRun(pinsB, n);

    // Zip in whichever order crosses less.
    const cost = (bs) => runA.reduce(
        (s, p, i) => s + (p.x - bs[i].x) ** 2 + (p.y - bs[i].y) ** 2,
        0,
    );
    const reversed = [...runB].reverse();
    const ordered = cost(runB) <= cost(reversed) ? runB : reversed;

    const pairs = runA.map((p, i) => [p, ordered[i]]);
    for (const [p, q] of pairs) {
        p.used = true;
        q.used = true;
    }
    return { pairs };
}
