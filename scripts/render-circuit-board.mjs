/**
 * Headless verification for circuit-board: renders seeds to SVG + PNG and
 * prints metrics against the reference illustration
 * (plans/chatgpt/top view spaced out.png).
 *
 *   node scripts/render-circuit-board.mjs [--style bw|neon] [seed ...]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import { CONFIG } from '../circuit-board/js/config.js';
import { generate } from '../circuit-board/js/core/index.js';
import { modelToSvg } from '../circuit-board/js/render/svg.js';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
let style = CONFIG.defaultStyle;
const seeds = [];
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--style' && args[i + 1]) style = args[++i];
    else if (Number.isFinite(Number(args[i]))) seeds.push(Number(args[i]));
}
if (!seeds.length) seeds.push(1, 2, 3, 4, 5);

const outDir = fileURLToPath(new URL('../plans/circuit design/board-renders/', import.meta.url));
const referencePng = fileURLToPath(new URL('../plans/chatgpt/top view spaced out.png', import.meta.url));
mkdirSync(outDir, { recursive: true });

// Every trace end must land on a pin anchor or a via -- no bare ends, ever.
function closureViolations(model) {
    const anchors = [];
    for (const part of model.parts) {
        for (const pin of part.pins) anchors.push([pin.x, pin.y]);
    }
    for (const via of model.vias) anchors.push([via.x, via.y]);

    const bad = [];
    for (const t of model.traces) {
        for (const p of [t.points[0], t.points[t.points.length - 1]]) {
            const hit = anchors.some(([ax, ay]) => Math.hypot(ax - p[0], ay - p[1]) < 1);
            if (!hit) bad.push(p);
        }
    }
    return bad;
}

// Median perpendicular distance between nearby parallel runs of different
// traces. The ribbon pitch should dominate this number.
function medianParallelGap(model) {
    const step = 6;
    const samples = [];
    for (let ti = 0; ti < model.traces.length; ti++) {
        const pts = model.traces[ti].points;
        for (let i = 0; i + 1 < pts.length; i++) {
            const [x1, y1] = pts[i];
            const [x2, y2] = pts[i + 1];
            const len = Math.hypot(x2 - x1, y2 - y1);
            const angle = Math.atan2(y2 - y1, x2 - x1);
            for (let d = 0; d < len; d += step) {
                samples.push({
                    x: x1 + ((x2 - x1) * d) / len,
                    y: y1 + ((y2 - y1) * d) / len,
                    angle,
                    trace: ti,
                });
            }
        }
    }

    const cellSize = 30;
    const buckets = new Map();
    const keyOf = (x, y) => `${Math.floor(x / cellSize)},${Math.floor(y / cellSize)}`;
    for (const s of samples) {
        const k = keyOf(s.x, s.y);
        if (!buckets.has(k)) buckets.set(k, []);
        buckets.get(k).push(s);
    }

    const gaps = [];
    for (const s of samples) {
        let best = Infinity;
        const bx = Math.floor(s.x / cellSize);
        const by = Math.floor(s.y / cellSize);
        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                for (const o of buckets.get(`${bx + dx},${by + dy}`) ?? []) {
                    if (o.trace === s.trace) continue;
                    let da = Math.abs(o.angle - s.angle) % Math.PI;
                    da = Math.min(da, Math.PI - da);
                    if (da > 0.17) continue;
                    // Perpendicular component of the offset.
                    const off = Math.abs(
                        -(o.x - s.x) * Math.sin(s.angle) + (o.y - s.y) * Math.cos(s.angle),
                    );
                    if (off > 1 && off < best) best = off;
                }
            }
        }
        if (best < cellSize) gaps.push(best);
    }
    gaps.sort((a, b) => a - b);
    return gaps.length ? gaps[Math.floor(gaps.length / 2)] : 0;
}

async function inkRatio(pngPath) {
    const sharp = require('sharp');
    const { data, info } = await sharp(pngPath)
        .grayscale()
        .raw()
        .toBuffer({ resolveWithObject: true });
    let lit = 0;
    for (let i = 0; i < data.length; i++) {
        if (data[i] > 40) lit++;
    }
    return lit / (info.width * info.height);
}

const svgPaths = [];
for (const seed of seeds) {
    const model = generate(seed, CONFIG);
    const suffix = style === CONFIG.defaultStyle ? '' : `-${style}`;
    const svgPath = `${outDir}seed-${seed}${suffix}.svg`;
    writeFileSync(svgPath, modelToSvg(model, CONFIG, { style }));
    svgPaths.push(svgPath);

    const byKind = new Map();
    for (const p of model.parts) byKind.set(p.kind, (byKind.get(p.kind) || 0) + 1);
    const counts = [...byKind.entries()].map(([k, n]) => `${k}:${n}`).join(' ');

    console.log(`\nseed ${seed}: ${model.parts.length} parts, ${model.traces.length} traces, ${model.vias.length} vias`);
    console.log(`  parts: ${counts}`);
    const bad = closureViolations(model);
    console.log(`  ${bad.length === 0 ? ' ok ' : 'WARN'} bare trace ends: ${bad.length} (target 0)`);
    const gap = medianParallelGap(model);
    console.log(`  ${gap >= 10 && gap <= 12.5 ? ' ok ' : 'WARN'} median parallel gap: ${gap.toFixed(1)}px (ribbon pitch target ~12px)`);
}

const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
for (const svgPath of svgPaths) {
    await page.goto(`file://${svgPath}`);
    await page.setViewportSize({ width: CONFIG.board.width, height: CONFIG.board.height });
    const pngPath = svgPath.replace(/\.svg$/, '.png');
    await page.screenshot({ path: pngPath });
    console.log(`\nwrote ${pngPath}`);
    console.log(`  ink ratio: ${(await inkRatio(pngPath)).toFixed(4)}`);
}
await browser.close();
console.log(`\nreference ink ratio: ${(await inkRatio(referencePng)).toFixed(4)}`);
