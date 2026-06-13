// Corridors are the horizontal highways traces travel on. A flow's own
// departure/arrival levels get merged into this global set at routing time;
// corridors only provide the transfer levels in between.
//
// Free intervals are computed per flow because the blocked width depends on
// the bundle's half-width, and previously routed bundles occupy space too.

// The walk grows outward from the spine, not top-down: stacked pairs
// straddle the spine, so the seed group is guaranteed to thread every
// stack gap -- those lanes are the backbone the spine pull routes onto.
//
// Corridors come in groups: a few lanes at exact lane pitch (the
// reference's 12-14px parallel runs), then a wide gap, then the next
// group. The bimodal spacing is the point -- co-travelers ride one group
// as a tight ribbon, and crossing to another group is a deliberate jog.
export function buildCorridors(rng, chips, config) {
    const spineY = config.board.height / 2;
    const top = Math.min(...chips.map((c) => c.y));
    const bottom = Math.max(...chips.map((c) => c.y + c.h));
    const { groupSize, groupGap } = config.corridors;
    const pitch = config.lanes.pitch;

    // Seed group contains the spine lane at a random position within it.
    const seedN = rng.int(...groupSize);
    const seedShift = rng.int(0, seedN - 1);
    const ys = [];
    for (let k = 0; k < seedN; k++) ys.push(spineY + (k - seedShift) * pitch);

    // Walk outward on each side until `extra` whole groups sit beyond the
    // chip band -- the escape levels open branches climb onto.
    const extra = rng.int(...config.corridors.extraAboveBelow);
    for (const dirY of [1, -1]) {
        const limit = dirY === 1 ? bottom : top;
        let edge = dirY === 1 ? Math.max(...ys) : Math.min(...ys);
        let beyond = 0;
        while (beyond < extra) {
            const start = edge + dirY * rng.range(...groupGap);
            const n = rng.int(...groupSize);
            for (let k = 0; k < n; k++) ys.push(start + dirY * k * pitch);
            edge = start + dirY * (n - 1) * pitch;
            if (dirY * (start - limit) > 0) beyond += 1;
        }
    }
    return ys.sort((a, b) => a - b);
}

// Maximal free x-ranges on a horizontal level. Chips block a level when the
// inflated rect spans its y; occupancy rects block the same way.
export function freeIntervals(y, chips, occupancy, config) {
    const { board, lanes, style } = config;
    const inflate = lanes.clearance;
    const blocked = [];

    for (const c of chips) {
        if (y >= c.y - inflate && y <= c.y + c.h + inflate) {
            blocked.push([c.x - inflate - style.pinLength, c.x + c.w + inflate + style.pinLength]);
        }
    }
    for (const r of occupancy) {
        if (y >= r.y0 - inflate && y <= r.y1 + inflate) {
            blocked.push([r.x0 - inflate, r.x1 + inflate]);
        }
    }

    blocked.sort((a, b) => a[0] - b[0]);
    const intervals = [];
    let cursor = board.marginX;
    const end = board.width - board.marginX;
    for (const [a, b] of blocked) {
        if (a > cursor) intervals.push([cursor, Math.min(a, end)]);
        cursor = Math.max(cursor, b);
        if (cursor >= end) break;
    }
    if (cursor < end) intervals.push([cursor, end]);
    return intervals.filter(([a, b]) => b - a > 10);
}
