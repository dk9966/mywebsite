/**
 * Headless verification for circuit-flow: renders seeds to SVG + PNG and
 * prints geometry stats next to the reference targets measured from
 * plans/circuit design/circuits-traced.json.
 *
 *   node scripts/render-circuit-flow.mjs [--scale N] [seed ...]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import { CONFIG, scaleConfig } from '../circuit-flow/js/config.js';
import { generate } from '../circuit-flow/js/core/index.js';
import { modelToSvg } from '../circuit-flow/js/render/svg.js';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
let scale = 1;
const seeds = [];
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--scale' && args[i + 1]) {
        scale = Number(args[++i]) || 1;
    } else {
        seeds.push(Number(args[i]));
    }
}
if (!seeds.length) seeds.push(1, 2, 3, 4, 5);

const config = scaleConfig(CONFIG, scale);
const scaleSuffix = scale === 1 ? '' : `-${scale}x`;

const outDir = fileURLToPath(new URL('../plans/circuit design/flow-renders/', import.meta.url));
mkdirSync(outDir, { recursive: true });

// Reference targets from the traced polylines (see config.js header).
const TARGETS = {
    octilinearShare: 0.95,
    horizontalShare: [0.55, 0.8],
    bendsPerTrace: [1.2, 3.5],
};

function stats(model) {
    const angleHist = new Map();
    let octi = 0;
    let segCount = 0;
    let horizLen = 0;
    let totalLen = 0;
    let bends = 0;

    for (const t of model.traces) {
        bends += Math.max(0, t.points.length - 2);
        for (let i = 0; i + 1 < t.points.length; i++) {
            const [x1, y1] = t.points[i];
            const [x2, y2] = t.points[i + 1];
            const len = Math.hypot(x2 - x1, y2 - y1);
            if (len < 1e-6) continue;
            let a = Math.round((Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI / 5) * 5;
            a = ((a % 180) + 180) % 180;
            angleHist.set(a, (angleHist.get(a) || 0) + 1);
            segCount++;
            totalLen += len;
            if (a === 0 || a === 45 || a === 90 || a === 135) octi++;
            if (a === 0) horizLen += len;
        }
    }
    return {
        traces: model.traces.length,
        chips: model.chips.length,
        angleHist: [...angleHist.entries()].sort((a, b) => a[0] - b[0]),
        octilinearShare: octi / segCount,
        horizontalShare: horizLen / totalLen,
        bendsPerTrace: bends / model.traces.length,
    };
}

function check(label, value, [lo, hi]) {
    const ok = value >= lo && value <= hi;
    return `${ok ? ' ok ' : 'WARN'} ${label}: ${value.toFixed(2)} (target ${lo}-${hi})`;
}

// Sectional coherence: share of diagonal length on branch-out material
// (open-ended traces) that leans away from the spine. Fans above/below the
// spine mirror each other, so cohesive sections juxtapose by construction.
// Chip-to-chip links are excluded -- both ends pinned, their detours are
// structurally up-then-down and cannot lean. Drift is a soft cost, so the
// target is a clear majority, not unanimity.
function driftAlignment(model) {
    const spineY = config.board.height / 2;
    let aligned = 0;
    let total = 0;
    for (const t of model.traces) {
        if (!t.open) continue;
        for (let i = 0; i + 1 < t.points.length; i++) {
            const [x1, y1] = t.points[i];
            const [x2, y2] = t.points[i + 1];
            const dy = y2 - y1;
            if (Math.abs(dy) < 1e-6) continue;
            const len = Math.hypot(x2 - x1, dy);
            total += len;
            if (Math.abs(y2 - spineY) > Math.abs(y1 - spineY)) aligned += len;
        }
    }
    return total > 0 ? aligned / total : 1;
}

function pointSegDist([px, py], [x1, y1], [x2, y2]) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len2 = dx * dx + dy * dy;
    const t = len2 > 0 ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len2)) : 0;
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

// Between the obstacles, near the spine, every line must connect on both
// sides: no trace endpoint may float inside the chip cluster's bounding box
// unless it sits on a chip wall (pin) or on another trace (fork junction).
function coreZoneViolations(model) {
    const zone = {
        x0: Math.min(...model.chips.map((c) => c.x)),
        x1: Math.max(...model.chips.map((c) => c.x + c.w)),
        y0: Math.min(...model.chips.map((c) => c.y)),
        y1: Math.max(...model.chips.map((c) => c.y + c.h)),
    };
    const onChipWall = ([x, y]) => model.chips.some(
        (c) => y >= c.y - 1 && y <= c.y + c.h + 1
            && (Math.abs(x - c.x) < 1 || Math.abs(x - (c.x + c.w)) < 1),
    );
    const onOtherTrace = (p, self) => model.traces.some((t) => {
        if (t === self) return false;
        for (let i = 0; i + 1 < t.points.length; i++) {
            if (pointSegDist(p, t.points[i], t.points[i + 1]) < 0.75) return true;
        }
        return false;
    });

    const bad = [];
    for (const t of model.traces) {
        for (const p of [t.points[0], t.points[t.points.length - 1]]) {
            const inZone = p[0] > zone.x0 + 1 && p[0] < zone.x1 - 1
                && p[1] > zone.y0 + 1 && p[1] < zone.y1 - 1;
            if (inZone && !onChipWall(p) && !onOtherTrace(p, t)) bad.push(p);
        }
    }
    return bad;
}

const svgPaths = [];
for (const seed of seeds) {
    const model = generate(seed, config);
    const svgPath = `${outDir}seed-${seed}${scaleSuffix}.svg`;
    writeFileSync(svgPath, modelToSvg(model, config));
    svgPaths.push(svgPath);

    const s = stats(model);
    const { lines, anchoredBoth } = model.meshStats;
    const share = anchoredBoth / lines;
    const shareFloor = config.mesh.anchoredShare;
    console.log(`\nseed ${seed}: ${s.chips} chips, ${s.traces} traces`);
    console.log(
        `  ${share >= shareFloor ? ' ok ' : 'WARN'} both-ends-anchored share: ${share.toFixed(2)} (${anchoredBoth}/${lines}, target >= ${shareFloor})`,
    );
    console.log(`  angles: ${s.angleHist.map(([a, c]) => `${a}:${c}`).join(' ')}`);
    console.log(
        `  ${s.octilinearShare >= TARGETS.octilinearShare ? ' ok ' : 'WARN'} octilinear share: ${s.octilinearShare.toFixed(3)} (target >= ${TARGETS.octilinearShare})`,
    );
    console.log(`  ${check('horizontal length share', s.horizontalShare, TARGETS.horizontalShare)}`);
    console.log(`  ${check('bends per trace', s.bendsPerTrace, TARGETS.bendsPerTrace)}`);
    const drift = driftAlignment(model);
    console.log(`  ${drift >= 0.6 ? ' ok ' : 'WARN'} drift alignment: ${drift.toFixed(2)} (target >= 0.6)`);
    const bad = coreZoneViolations(model);
    console.log(
        `  ${bad.length === 0 ? ' ok ' : 'WARN'} dead ends in core zone: ${bad.length}${
            bad.length ? ` at ${bad.map(([x, y]) => `(${x.toFixed(0)},${y.toFixed(0)})`).join(' ')}` : ''
        }`,
    );
}

const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
for (const svgPath of svgPaths) {
    await page.goto(`file://${svgPath}`);
    await page.setViewportSize({ width: config.board.width, height: config.board.height });
    const pngPath = svgPath.replace(/\.svg$/, '.png');
    await page.screenshot({ path: pngPath });
    console.log(`\nwrote ${pngPath}`);
}
await browser.close();
