/**
 * Headless verification for circuit-pcb: renders seeds to SVG + PNG and prints
 * metrics against the reference illustration
 * (plans/board pcb road circuits.png).
 *
 *   node scripts/render-circuit-pcb.mjs [--style teal|blueprint] [seed ...]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import { CONFIG } from '../circuit-pcb/js/config.js';
import { generate } from '../circuit-pcb/js/core/index.js';
import { modelToSvg } from '../circuit-pcb/js/render/svg.js';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
let style = null;
const seeds = [];
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--style' && args[i + 1]) style = args[++i];
    else if (Number.isFinite(Number(args[i]))) seeds.push(Number(args[i]));
}
if (!seeds.length) seeds.push(1, 2, 3, 4, 5);
style = style ?? CONFIG.defaultStyle;

const outDir = fileURLToPath(new URL('../plans/circuit design/pcb-renders/', import.meta.url));
const referencePng = fileURLToPath(new URL('../plans/board pcb road circuits.png', import.meta.url));
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
