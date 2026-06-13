/**
 * Tiled circuit-flow render: a board `factor`x bigger in both directions
 * that reads as one uniform field -- chips scattered evenly across the
 * whole sheet, traces flowing vertically through it (the wallpaper look of
 * the reference pattern, not a row of separate boards).
 *
 * Construction: many tightly packed horizontal bands, each generated at
 * native density on a wide board (stretchConfigX), stitched across every
 * seam by connectors between open ends, then the whole sheet is transposed
 * at render time so the flow runs vertically. Band spacing is close enough
 * that chip rows and fans interleave into an even scatter.
 * Band seeds derive deterministically from the base seed.
 *
 *   node scripts/render-circuit-flow-tiled.mjs [--factor N] [seed]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import { CONFIG, stretchConfigX } from '../circuit-flow/js/config.js';
import { createRng } from '../circuit-flow/js/rng.js';
import { generate } from '../circuit-flow/js/core/index.js';
import { modelToSvg } from '../circuit-flow/js/render/svg.js';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
let factor = 5;
let seed = 1;
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--factor' && args[i + 1]) {
        factor = Number(args[++i]) || 5;
    } else {
        seed = Number(args[i]);
    }
}

// The sheet is generated in horizontal-flow space and transposed at render
// time, so the source board is the final sheet with its axes swapped.
const srcW = CONFIG.board.height * factor;
const srcH = CONFIG.board.width * factor;

const bandConfig = stretchConfigX(CONFIG, srcW / CONFIG.board.width);
// Bands pack at a fraction of the reference board height, so each band's
// fans must stay shallow: one escape group keeps corridors within ~300px
// of the spine, clear of the neighbouring bands' chip rows. Stations sit
// denser than the lone-board grammar for the reference pattern's tight
// chip scatter.
bandConfig.corridors.extraAboveBelow = [1, 1];
bandConfig.chips.stations = [18, 22];
const bandHeight = CONFIG.board.height;

// Tight enough that chip rows and fans from neighbouring bands interleave
// into an even all-over scatter; jitter keeps the rhythm uneven.
const targetSpacing = 500;
const jitterMax = 30;
const bandCount = Math.max(2, Math.round(srcH / targetSpacing));
const spacing = srcH / bandCount;

const seedRng = createRng(seed);
const bands = [];
for (let band = 0; band < bandCount; band++) {
    const bandSeed = seedRng.int(1, 0x7fffffff);
    const jitter = seedRng.range(-jitterMax, jitterMax);
    const m = generate(bandSeed, bandConfig);
    const dy = (band + 0.5) * spacing - bandHeight / 2 + jitter;

    for (const chip of m.chips) {
        chip.y += dy;
        chip.pins.left = chip.pins.left.map((y) => y + dy);
        chip.pins.right = chip.pins.right.map((y) => y + dy);
    }
    for (const trace of m.traces) {
        trace.points = trace.points.map(([x, y]) => [x, y + dy]);
    }
    bands.push({ chips: m.chips, traces: m.traces, spineY: dy + bandHeight / 2 });

    const { lines, anchoredBoth } = m.meshStats;
    console.log(
        `band ${band} (seed ${bandSeed}): ${m.chips.length} chips, ${m.traces.length} traces, ` +
            `anchored share ${(anchoredBoth / lines).toFixed(2)}`,
    );
}

// ---- cross-seam stitching -------------------------------------------------
// Open ends fanning toward a seam join the neighbouring band, always in the
// native grammar (horizontal runs + 45deg diagonals). Two forms, in order
// of preference:
//   tip-to-tip  opposite-facing open ends fuse into one line; the connector
//               starts and ends collinear with the lines it joins
//   junction    a leftover open end lands its final diagonal on a horizontal
//               run of the other band, reading as a branch off that host
const STITCH = {
    maxReachX: 1000, // longest horizontal span of one connector
    runLength: 28, // horizontal run required around every diagonal (minStraight)
    maxReachY: 480, // deepest a junction connector may dive into the other band
    hostMargin: 24, // landing distance from a host segment's ends
    clearance: 8, // same as lanes.clearance
};

// A connector spanning |dy| needs ceil(|dy| / jogSpan) diagonals; demanding
// a real run beside each keeps deep dives reading as staircases instead of
// one long off-grammar diagonal.
function requiredDx(dy, config) {
    const span = Math.abs(dy);
    const k = Math.max(1, Math.ceil(span / config.routing.jogSpan[1]));
    return span + (k + 1) * STITCH.runLength;
}

function pointSegDist([px, py], [x1, y1], [x2, y2]) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len2 = dx * dx + dy * dy;
    const t = len2 > 0 ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len2)) : 0;
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

function orient([ax, ay], [bx, by], [cx, cy]) {
    return Math.sign((bx - ax) * (cy - ay) - (by - ay) * (cx - ax));
}

function segsIntersect(p1, p2, q1, q2) {
    return (
        orient(p1, p2, q1) !== orient(p1, p2, q2)
        && orient(q1, q2, p1) !== orient(q1, q2, p2)
    );
}

function segSegDist(p1, p2, q1, q2) {
    if (segsIntersect(p1, p2, q1, q2)) return 0;
    return Math.min(
        pointSegDist(p1, q1, q2),
        pointSegDist(p2, q1, q2),
        pointSegDist(q1, p1, p2),
        pointSegDist(q2, p1, p2),
    );
}

// Every trace segment on the sheet (connectors included as they land),
// indexed per trace so a connector can ignore the two lines it joins.
const segments = [];
function addTraceSegments(trace) {
    const pts = trace.points;
    for (let i = 0; i + 1 < pts.length; i++) {
        segments.push({ trace, a: pts[i], b: pts[i + 1] });
    }
}
for (const band of bands) for (const trace of band.traces) addTraceSegments(trace);

const allChips = bands.flatMap((b) => b.chips);

function connectorClear(pts, ignoreA, ignoreB) {
    const pad = STITCH.clearance;
    const x0 = Math.min(...pts.map((p) => p[0])) - pad;
    const x1 = Math.max(...pts.map((p) => p[0])) + pad;
    const y0 = Math.min(...pts.map((p) => p[1])) - pad;
    const y1 = Math.max(...pts.map((p) => p[1])) + pad;

    for (const chip of allChips) {
        if (chip.x + chip.w < x0 || chip.x > x1 || chip.y + chip.h < y0 || chip.y > y1) continue;
        for (let i = 0; i + 1 < pts.length; i++) {
            const corners = [
                [chip.x - pad, chip.y - pad],
                [chip.x + chip.w + pad, chip.y - pad],
                [chip.x + chip.w + pad, chip.y + chip.h + pad],
                [chip.x - pad, chip.y + chip.h + pad],
            ];
            for (let c = 0; c < 4; c++) {
                if (segsIntersect(pts[i], pts[i + 1], corners[c], corners[(c + 1) % 4])) return false;
            }
        }
    }

    // Transversal crossings are native to the grammar (every 45deg jog
    // crosses the corridor lanes between its levels), so only near-parallel
    // proximity -- the engine's crowding rule -- rejects a connector.
    for (const seg of segments) {
        if (seg.trace === ignoreA || seg.trace === ignoreB) continue;
        const sx0 = Math.min(seg.a[0], seg.b[0]);
        const sx1 = Math.max(seg.a[0], seg.b[0]);
        const sy0 = Math.min(seg.a[1], seg.b[1]);
        const sy1 = Math.max(seg.a[1], seg.b[1]);
        if (sx1 < x0 || sx0 > x1 || sy1 < y0 || sy0 > y1) continue;
        const segAngle = angleOf(seg.a, seg.b);
        for (let i = 0; i + 1 < pts.length; i++) {
            let d = Math.abs(angleOf(pts[i], pts[i + 1]) - segAngle) % 180;
            if (d > 90) d = 180 - d;
            if (d >= 15) continue;
            if (segSegDist(pts[i], pts[i + 1], seg.a, seg.b) < STITCH.clearance) return false;
        }
    }
    return true;
}

function angleOf([x1, y1], [x2, y2]) {
    return ((Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI + 180) % 180;
}

// An endpoint is stitchable when it hangs in open space (not on a chip wall,
// not a branch junction on another line) and exits horizontally.
function freeEndpoints(band) {
    const out = [];
    for (const trace of band.traces) {
        const pts = trace.points;
        for (const end of [0, pts.length - 1]) {
            const [x, y] = pts[end];
            const [px, py] = pts[end === 0 ? 1 : pts.length - 2];
            if (Math.abs(y - py) > 0.01) continue;
            const dir = Math.sign(x - px);
            if (dir === 0) continue;

            const onChip = band.chips.some(
                (c) => x >= c.x - 10 && x <= c.x + c.w + 10 && y >= c.y - 2 && y <= c.y + c.h + 2,
            );
            if (onChip) continue;
            const onTrace = band.traces.some((t) => {
                if (t === trace) return false;
                const q = t.points;
                for (let i = 0; i + 1 < q.length; i++) {
                    if (pointSegDist([x, y], q[i], q[i + 1]) < 1.5) return true;
                }
                return false;
            });
            if (onTrace) continue;
            out.push({ trace, x, y, dir });
        }
    }
    return out;
}

// Staircase from a to (bx, by): k equal 45deg diagonals sized within
// jogSpan, horizontal runs (rng-weighted) spending the leftover dx between
// them. Tip-to-tip joins end with a run (arriving collinear with the other
// line); junction landings end with a diagonal (arriving like a branch).
function buildConnector(a, bx, by, rng, config, endWithDiagonal) {
    const dir = Math.sign(bx - a.x);
    const dy = by - a.y;
    const span = Math.abs(dy);
    const k = Math.max(1, Math.ceil(span / config.routing.jogSpan[1]));
    const slack = Math.abs(bx - a.x) - span;
    const runs = endWithDiagonal ? k : k + 1;

    const weights = Array.from({ length: runs }, () => rng.range(0.5, 1.5));
    const wSum = weights.reduce((s, w) => s + w, 0);
    const pts = [[a.x, a.y]];
    let x = a.x;
    let y = a.y;
    for (let i = 0; i < k; i++) {
        x += dir * (slack * weights[i] / wSum);
        pts.push([x, y]);
        const d = span / k;
        x += dir * d;
        y += Math.sign(dy) * d;
        pts.push([x, y]);
    }
    pts.push([bx, by]);
    return pts;
}

// Horizontal runs of a band's traces inside [yMin, yMax]: landing strips
// for junction connectors.
function horizontalHosts(band, yMin, yMax) {
    const out = [];
    for (const trace of band.traces) {
        const pts = trace.points;
        for (let i = 0; i + 1 < pts.length; i++) {
            const [x1, y1] = pts[i];
            const [x2, y2] = pts[i + 1];
            if (Math.abs(y1 - y2) > 0.01) continue;
            if (y1 < yMin || y1 > yMax) continue;
            if (Math.abs(x2 - x1) < 2 * STITCH.hostMargin + 40) continue;
            out.push({ trace, y: y1, x0: Math.min(x1, x2), x1: Math.max(x1, x2) });
        }
    }
    return out;
}

// Land an open end's staircase on one of the host runs, diagonal-last.
function tryJunction(end, hosts, rng, config) {
    const sorted = hosts
        .filter((h) => {
            const dy = Math.abs(h.y - end.y);
            return dy >= config.lanes.pitch && dy <= STITCH.maxReachY;
        })
        .sort((p, q) => Math.abs(p.y - end.y) - Math.abs(q.y - end.y));

    for (const h of sorted) {
        const dy = Math.abs(h.y - end.y);
        const near = end.x + end.dir * requiredDx(dy, config);
        const far = end.x + end.dir * STITCH.maxReachX;
        const lo = Math.max(Math.min(near, far), h.x0 + STITCH.hostMargin);
        const hi = Math.min(Math.max(near, far), h.x1 - STITCH.hostMargin);
        if (lo > hi) continue;
        // Several tries per host: the first run must clear the staggered
        // sibling lanes of the end's own ribbon, so placement matters.
        for (let attempt = 0; attempt < 4; attempt++) {
            const bx = rng.range(lo, hi);
            const pts = buildConnector(end, bx, h.y, rng, config, true);
            if (!connectorClear(pts, end.trace, h.trace)) continue;
            return { points: pts, width: config.style.traceWidth, open: false, branch: true };
        }
    }
    return null;
}

let stitched = 0;
for (let s = 0; s + 1 < bands.length; s++) {
    const upper = bands[s];
    const lower = bands[s + 1];
    const ups = freeEndpoints(upper).filter((e) => e.y > upper.spineY);
    const downs = freeEndpoints(lower).filter((e) => e.y < lower.spineY);

    const pairs = [];
    for (const a of ups) {
        for (const b of downs) {
            const dir = Math.sign(b.x - a.x);
            if (dir === 0 || a.dir !== dir || b.dir !== -dir) continue;
            const adx = Math.abs(b.x - a.x);
            const ady = Math.abs(b.y - a.y);
            if (ady < bandConfig.lanes.pitch || adx > STITCH.maxReachX || adx < requiredDx(ady, bandConfig)) continue;
            pairs.push({ a, b, adx });
        }
    }
    pairs.sort((p, q) => p.adx - q.adx);

    const used = new Set();
    let fused = 0;
    for (const { a, b } of pairs) {
        if (used.has(a) || used.has(b)) continue;
        const pts = buildConnector(a, b.x, b.y, seedRng, bandConfig, false);
        if (!connectorClear(pts, a.trace, b.trace)) continue;
        const trace = { points: pts, width: bandConfig.style.traceWidth, open: false, branch: false };
        upper.traces.push(trace);
        addTraceSegments(trace);
        used.add(a);
        used.add(b);
        fused++;
    }

    // Leftover ends branch onto the other band's horizontal runs instead.
    // Hosts stay on the seam side of the other band's spine so connectors
    // join the facing fan rather than diving through it.
    const lowerHosts = horizontalHosts(lower, lower.spineY - bandHeight, lower.spineY);
    const upperHosts = horizontalHosts(upper, upper.spineY, upper.spineY + bandHeight);
    let branched = 0;
    const targets = [
        ...ups.map((end) => ({ end, hosts: lowerHosts })),
        ...downs.map((end) => ({ end, hosts: upperHosts })),
    ];
    for (const { end, hosts } of targets) {
        if (used.has(end)) continue;
        const trace = tryJunction(end, hosts, seedRng, bandConfig);
        if (!trace) continue;
        upper.traces.push(trace);
        addTraceSegments(trace);
        used.add(end);
        branched++;
    }

    stitched += fused + branched;
    console.log(
        `seam ${s}-${s + 1}: ${fused} tip-to-tip + ${branched} junction connectors `
            + `(${ups.length} up / ${downs.length} down ends)`,
    );
}

// ---- output ----------------------------------------------------------------

const model = {
    chips: allChips,
    traces: bands.flatMap((b) => b.traces),
};
const sheetConfig = structuredClone(bandConfig);
sheetConfig.board.height = srcH;

const outDir = fileURLToPath(new URL('../plans/circuit design/flow-renders/', import.meta.url));
mkdirSync(outDir, { recursive: true });
const svgPath = `${outDir}seed-${seed}-${factor}x.svg`;
writeFileSync(svgPath, modelToSvg(model, sheetConfig, { transpose: true }));
console.log(`\nsheet: ${srcH}x${srcW} (vertical flow), ` +
    `${model.chips.length} chips, ${model.traces.length} traces, ${stitched} seam connectors`);
console.log(`wrote ${svgPath}`);

const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(`file://${svgPath}`);
await page.setViewportSize({ width: srcH, height: srcW });
const pngPath = svgPath.replace(/\.svg$/, '.png');
await page.screenshot({ path: pngPath });
console.log(`wrote ${pngPath}`);
await browser.close();
