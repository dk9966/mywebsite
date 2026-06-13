/**
 * Headless render of the circuit-generator default board to an SVG, for fast
 * visual iteration on the routing algorithm without a browser.
 *
 * Usage: node scripts/render-generator-svg.mjs [seed] [out.svg]
 */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
globalThis.Math.seedrandom = require('seedrandom');

import { writeFileSync } from 'fs';
import { Cell } from '../circuit-painter/js/wire.js';
import { params } from '../circuit-painter/js/params.js';
import { applyModeDefaults } from '../circuit-painter/js/appMode.js';
import {
    applyObstaclesToGrid, clampObstaclesToGrid, generateObstacles, getObstacles,
    setObstacles, setObstacleGridDimensions,
} from '../circuit-painter/js/obstacles.js';
import {
    GENERATOR_DEFAULT_OBSTACLES, GENERATOR_DEFAULT_PARAMS,
} from '../circuit-painter/js/boards/generatorDefault.js';
import { generatePinBuses } from '../circuit-painter/js/pinBuses.js';
import { setSeed } from '../circuit-painter/js/rng.js';

const seed = process.argv[2] || '1';
const out = process.argv[3] || '/tmp/generator.svg';

applyModeDefaults(params, 'generator');
Object.assign(params, GENERATOR_DEFAULT_PARAMS);
params.seed = seed;

const gridWidth = Math.max(3, Math.floor(params.mapWidth / params.cellSize));
const gridHeight = Math.max(3, Math.floor(params.mapHeight / params.cellSize));

setSeed(params.seed);
const grid = [];
for (let x = 0; x < gridWidth; x++) {
    grid[x] = [];
    for (let y = 0; y < gridHeight; y++) grid[x][y] = new Cell(x, y);
}
setObstacleGridDimensions(gridWidth, gridHeight);
if (process.env.RANDOM_OBSTACLES) {
    generateObstacles(gridWidth, gridHeight);
} else {
    setObstacles(GENERATOR_DEFAULT_OBSTACLES);
}
clampObstaclesToGrid(gridWidth, gridHeight);
applyObstaclesToGrid(grid, gridWidth, gridHeight);

const t0 = Date.now();
const wires = generatePinBuses(grid, gridWidth, gridHeight);
console.log(`seed ${seed}: ${wires.length} wires in ${Date.now() - t0}ms -> ${out}`);

const cs = params.cellSize;
const px = (v) => ((v + 0.5) * cs).toFixed(1);
const parts = [];
parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${gridWidth * cs}" height="${gridHeight * cs}">`);
parts.push(`<rect width="100%" height="100%" fill="#330533"/>`);

for (const o of getObstacles()) {
    parts.push(`<rect x="${o.x * cs}" y="${o.y * cs}" width="${o.w * cs}" height="${o.h * cs}" fill="none" stroke="#a3ccc2" stroke-width="1.5"/>`);
}

if (process.env.SHOW_OCCUPANCY) {
    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            if (!grid[x][y].available) {
                parts.push(`<rect x="${(x + 0.3) * cs}" y="${(y + 0.3) * cs}" width="${cs * 0.4}" height="${cs * 0.4}" fill="#ff5577" opacity="0.5"/>`);
            }
        }
    }
}

for (const w of wires) {
    const pts = w.cells.map((c) => `${px(c.x)},${px(c.y)}`).join(' ');
    parts.push(`<polyline points="${pts}" fill="none" stroke="#a3ccc2" stroke-width="${(cs * 0.25).toFixed(1)}"/>`);
    const end = w.cells[w.cells.length - 1];
    if (!w.isBus) {
        parts.push(`<circle cx="${px(end.x)}" cy="${px(end.y)}" r="${(cs / 4).toFixed(1)}" fill="#330533" stroke="#a3ccc2" stroke-width="${(cs / 6).toFixed(1)}"/>`);
    }
}

parts.push('</svg>');
writeFileSync(out, parts.join('\n'));
