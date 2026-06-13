/**
 * Headless scan for interior corners ≤ 90° on generated pin-bus wires.
 */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
globalThis.Math.seedrandom = require('seedrandom');

import { Cell } from '../circuit-painter/js/wire.js';
import { params } from '../circuit-painter/js/params.js';
import { applyModeDefaults } from '../circuit-painter/js/appMode.js';
import {
    generateObstacles, applyObstaclesToGrid, setObstacleGridDimensions,
} from '../circuit-painter/js/obstacles.js';
import { generatePinBuses } from '../circuit-painter/js/pinBuses.js';
import { isSharpCorner } from '../circuit-painter/js/pathfindCore.js';
import { setSeed } from '../circuit-painter/js/rng.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

function directionBetween(a, b) {
    const dx = Math.sign(b.x - a.x);
    const dy = Math.sign(b.y - a.y);
    for (let d = 0; d < 8; d++) {
        if (DIRS[d][0] === dx && DIRS[d][1] === dy) return d;
    }
    return -1;
}

function findSharpCorners(cells) {
    const hits = [];
    for (let i = 1; i < cells.length - 1; i++) {
        const prev = cells[i - 1];
        const cur = cells[i];
        const next = cells[i + 1];
        if (prev.x === cur.x && prev.y === cur.y) continue;
        if (cur.x === next.x && cur.y === next.y) continue;
        const fromDir = directionBetween(prev, cur);
        const toDir = directionBetween(cur, next);
        if (fromDir < 0 || toDir < 0) {
            hits.push({ i, reason: 'non-adjacent', prev, cur, next });
            continue;
        }
        if (isSharpCorner(fromDir, toDir)) {
            hits.push({ i, fromDir, toDir, delta: (toDir - fromDir + 8) % 8, prev, cur, next });
        }
    }
    return hits;
}

function buildGrid(w, h) {
    const grid = [];
    for (let x = 0; x < w; x++) {
        grid[x] = [];
        for (let y = 0; y < h; y++) grid[x][y] = new Cell(x, y);
    }
    return grid;
}

applyModeDefaults(params, 'generator');
const gridWidth = Math.ceil(params.mapWidth / params.cellSize) + 1;
const gridHeight = Math.ceil(params.mapHeight / params.cellSize) + 1;

let totalSharp = 0;
const seedsWithSharp = [];

let totalWires = 0;
let failedSeeds = 0;

for (let seed = 1; seed <= 200; seed++) {
    setSeed(seed);
    const grid = buildGrid(gridWidth, gridHeight);
    setObstacleGridDimensions(gridWidth, gridHeight);
    generateObstacles(gridWidth, gridHeight);
    applyObstaclesToGrid(grid);

    const wires = generatePinBuses(grid, gridWidth, gridHeight);
    totalWires += wires.length;
    if (!wires.length) failedSeeds++;
    let sharp = 0;
    for (const w of wires) {
        const hits = findSharpCorners(w.cells);
        sharp += hits.length;
    }
    if (sharp) seedsWithSharp.push({ seed, sharp });
    totalSharp += sharp;
}

console.log(`Checked seeds 1-200: ${totalSharp} sharp corners, ${totalWires} wires, ${failedSeeds} empty seeds`);
console.log('Seeds with sharp corners:', seedsWithSharp);
