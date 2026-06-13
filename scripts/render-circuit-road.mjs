/**
 * Headless renderer for the isolated PCB road-circuit study.
 *
 *   node scripts/render-circuit-road.mjs [--style neon|blueprint] [seed ...]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { CONFIG } from '../circuit-road/js/config.js';
import { generate } from '../circuit-road/js/core/index.js';
import { modelToSvg } from '../circuit-road/js/render/svg.js';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
let style = CONFIG.defaultStyle;
const seeds = [];

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--style' && args[i + 1]) style = args[++i];
    else if (Number.isFinite(Number(args[i]))) seeds.push(Number(args[i]));
}
if (!seeds.length) seeds.push(1, 2, 3, 4, 5);

const outDir = fileURLToPath(new URL('../plans/circuit design/road-renders/', import.meta.url));
mkdirSync(outDir, { recursive: true });

function closureViolations(model) {
    const anchors = [];
    for (const part of model.parts) {
        for (const pin of part.pins) anchors.push([pin.x, pin.y]);
    }
    for (const via of model.vias) anchors.push([via.x, via.y]);

    const bad = [];
    for (const trace of model.traces) {
        for (const point of [trace.points[0], trace.points[trace.points.length - 1]]) {
            const hit = anchors.some(([x, y]) => Math.hypot(x - point.x, y - point.y) < 1);
            if (!hit) bad.push(point);
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
        if (data[i] > 36) lit++;
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
    for (const part of model.parts) byKind.set(part.kind, (byKind.get(part.kind) || 0) + 1);
    const counts = [...byKind.entries()].map(([kind, count]) => `${kind}:${count}`).join(' ');
    const bad = closureViolations(model);

    console.log(`\nseed ${seed}: ${model.parts.length} parts, ${model.traces.length} traces, ${model.vias.length} vias`);
    console.log(`  parts: ${counts}`);
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

