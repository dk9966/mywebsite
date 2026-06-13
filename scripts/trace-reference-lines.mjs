/**
 * Scan cyan traces from a reference PNG into circuit-painter snapshot wire polylines.
 *
 * Usage:
 *   node scripts/trace-reference-lines.mjs [input.png] [output.json]
 *   node scripts/trace-reference-lines.mjs --verify   # screenshot via Playwright
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

const CELL_SIZE = 9;
const EXTRACT_CELL_SIZE = 5;
const MAP_WIDTH = Math.ceil(941 / CELL_SIZE) * CELL_SIZE;
const MAP_HEIGHT = Math.ceil(1672 / CELL_SIZE) * CELL_SIZE;
const GRID_W = Math.floor(MAP_WIDTH / CELL_SIZE);
const GRID_H = Math.floor(MAP_HEIGHT / CELL_SIZE);
const EXTRACT_W = Math.floor(MAP_WIDTH / EXTRACT_CELL_SIZE);
const EXTRACT_H = Math.floor(MAP_HEIGHT / EXTRACT_CELL_SIZE);

const DEFAULT_INPUT = path.join(root, 'plans/circuit design/circuits for tracing.png');
const DEFAULT_OUTPUT = path.join(root, 'circuit-painter/seeds/tracing-lines.json');
const SNAPSHOT_NAME = 'Tracing Lines';

const DIRS_8 = [
    [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1],
];

const PARAMS = {
    mapWidth: MAP_WIDTH,
    mapHeight: MAP_HEIGHT,
    cellSize: CELL_SIZE,
    wireLength: 28,
    cutOffLength: 1,
    straightness: 15,
    diagonalChance: 0.5,
    turnSmoothness: 1,
    collectiveness: 0,
    prioritizeLongWires: false,
    joinEndpoints: false,
    directionality: 0.8,
    showGrid: false,
    showCircuits: true,
    showGreedyCircuits: false,
    editWires: true,
    showBuses: false,
    pinBusSlantLength: 6,
    pinBusStraightMax: 14,
    routeClearanceTarget: 4,
    routeClearanceBias: 0.75,
    pinBusRouteMargin: 16,
    pinBusMaxDetourRatio: 1.75,
    pinBusCorridorWeight: 0.24,
    pinBusSpineRatio: 0.52,
    pinBusWireCount: 4,
    seed: 1,
    bgColor: 'rgba(1, 8, 12, 1)',
    fgColor: 'rgba(43, 238, 235, 1)',
};

function isTracePixel(r, g, b) {
    if (r + g + b < 30) return false;
    if (r > 120 && r > g && b < g) return false;
    if (g > 80 && b < 45 && r < 50) return false;
    return g > 100 && b > 50 && r < 60;
}

function buildTraceGrid(rgba, width, height) {
    const grid = new Uint8Array(EXTRACT_W * EXTRACT_H);
    const cellArea = EXTRACT_CELL_SIZE * EXTRACT_CELL_SIZE;
    const threshold = Math.max(3, Math.round(cellArea * 0.12));

    for (let gy = 0; gy < EXTRACT_H; gy++) {
        for (let gx = 0; gx < EXTRACT_W; gx++) {
            let hits = 0;
            const x0 = gx * EXTRACT_CELL_SIZE;
            const y0 = gy * EXTRACT_CELL_SIZE;
            for (let py = y0; py < y0 + EXTRACT_CELL_SIZE && py < height; py++) {
                for (let px = x0; px < x0 + EXTRACT_CELL_SIZE && px < width; px++) {
                    const i = (py * width + px) * 4;
                    if (isTracePixel(rgba[i], rgba[i + 1], rgba[i + 2])) hits++;
                }
            }
            if (hits >= threshold) grid[gy * EXTRACT_W + gx] = 1;
        }
    }
    return grid;
}

function pruneIsolatedCells(grid, w, h) {
    const out = grid.slice();
    for (let gy = 0; gy < h; gy++) {
        for (let gx = 0; gx < w; gx++) {
            if (!grid[gy * w + gx]) continue;
            let neighbors = 0;
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    if (dx === 0 && dy === 0) continue;
                    const nx = gx + dx;
                    const ny = gy + dy;
                    if (nx >= 0 && ny >= 0 && nx < w && ny < h && grid[ny * w + nx]) {
                        neighbors++;
                    }
                }
            }
            if (neighbors === 0) out[gy * w + gx] = 0;
        }
    }
    return out;
}

function toPainterCoord(v) {
    return (v * EXTRACT_CELL_SIZE) / CELL_SIZE;
}

function scalePolyline(poly) {
    return poly.map(([x, y]) => [toPainterCoord(x), toPainterCoord(y)]);
}

function directionBetween(a, b) {
    const dx = Math.sign(b[0] - a[0]);
    const dy = Math.sign(b[1] - a[1]);
    if (dx === 0 && dy === 0) return null;
    for (let i = 0; i < DIRS_8.length; i++) {
        if (DIRS_8[i][0] === dx && DIRS_8[i][1] === dy) return i;
    }
    return null;
}

function simplifyPolyline(poly) {
    if (poly.length < 2) return [];
    const pts = [poly[0]];
    let prevDir = directionBetween(poly[0], poly[1]);
    for (let i = 1; i < poly.length; i++) {
        const cur = poly[i];
        const next = poly[i + 1];
        if (!next) {
            if (pts[pts.length - 1][0] !== cur[0] || pts[pts.length - 1][1] !== cur[1]) {
                pts.push(cur);
            }
            break;
        }
        const dir = directionBetween(cur, next);
        if (dir !== prevDir) {
            if (pts[pts.length - 1][0] !== cur[0] || pts[pts.length - 1][1] !== cur[1]) {
                pts.push(cur);
            }
            prevDir = dir;
        }
    }
    return pts;
}

function polylineLength(pts) {
    let len = 0;
    for (let i = 1; i < pts.length; i++) {
        len += Math.max(Math.abs(pts[i][0] - pts[i - 1][0]), Math.abs(pts[i][1] - pts[i - 1][1]));
    }
    return len;
}

function polylinesToWires(polylines) {
    const wires = [];
    for (const raw of polylines) {
        const simplified = simplifyPolyline(raw);
        if (simplified.length < 2) continue;
        if (polylineLength(simplified) < 2) continue;
        wires.push({
            points: simplified.map(([x, y]) => ({ x, y })),
            isBus: false,
            isGreedy: false,
            isQFPPin: false,
            isRoute: false,
            noPads: true,
            strokeScale: null,
            manual: true,
        });
    }
    return wires;
}

function findPeaks(hist, minX) {
    const peaks = [];
    for (let i = 0; i < hist.length; i++) {
        const left = hist[i - 1] || 0;
        const right = hist[i + 1] || 0;
        if (hist[i] > 0 && hist[i] >= left && hist[i] >= right) {
            peaks.push(minX + i);
        }
    }
    return peaks;
}

function connectedComponents(grid, w, h) {
    const seen = new Uint8Array(w * h);
    const comps = [];

    for (let gy = 0; gy < h; gy++) {
        for (let gx = 0; gx < w; gx++) {
            const start = gy * w + gx;
            if (!grid[start] || seen[start]) continue;
            const cells = [];
            const stack = [[gx, gy]];
            seen[start] = 1;
            while (stack.length) {
                const [x, y] = stack.pop();
                cells.push([x, y]);
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const nx = x + dx;
                        const ny = y + dy;
                        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                        const ni = ny * w + nx;
                        if (!grid[ni] || seen[ni]) continue;
                        seen[ni] = 1;
                        stack.push([nx, ny]);
                    }
                }
            }
            comps.push(cells);
        }
    }
    return comps;
}

function splitIntoLanes(cells) {
    const xs = cells.map(([x]) => x);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const width = maxX - minX + 1;
    if (width <= 2) return [cells];

    const hist = new Array(width).fill(0);
    for (const [x] of cells) hist[x - minX]++;
    let peaks = findPeaks(hist, minX).filter((_, i, arr) => {
        if (i === 0) return true;
        return arr[i] - arr[i - 1] >= 2;
    });
    if (peaks.length <= 1) return [cells];

    const lanes = peaks.map(() => []);
    for (const cell of cells) {
        let best = 0;
        let bestDist = Infinity;
        for (let i = 0; i < peaks.length; i++) {
            const d = Math.abs(cell[0] - peaks[i]);
            if (d < bestDist) {
                bestDist = d;
                best = i;
            }
        }
        lanes[best].push(cell);
    }
    return lanes.filter((lane) => lane.length >= 2);
}

function laneToPolyline(cells) {
    if (cells.length <= 2) return scalePolyline(cells);
    const set = new Set(cells.map(([x, y]) => `${x},${y}`));
    const start = cells.reduce((best, c) => (c[1] < best[1] || (c[1] === best[1] && c[0] < best[0]) ? c : best), cells[0]);
    const poly = [start];
    const used = new Set([`${start[0]},${start[1]}`]);
    let cur = start;

    while (used.size < cells.length) {
        let next = null;
        let bestScore = Infinity;
        for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
                if (dx === 0 && dy === 0) continue;
                const nx = cur[0] + dx;
                const ny = cur[1] + dy;
                const key = `${nx},${ny}`;
                if (!set.has(key) || used.has(key)) continue;
                const score = (ny - cur[1]) * 100 + Math.abs(nx - cur[0]);
                if (score < bestScore) {
                    bestScore = score;
                    next = [nx, ny];
                }
            }
        }
        if (!next) break;
        poly.push(next);
        used.add(`${next[0]},${next[1]}`);
        cur = next;
    }

    for (const [x, y] of cells) {
        const key = `${x},${y}`;
        if (!used.has(key)) poly.push([x, y]);
    }
    return scalePolyline(poly);
}

function extractLanePolylines(grid, w, h) {
    const polylines = [];
    for (const comp of connectedComponents(grid, w, h)) {
        for (const lane of splitIntoLanes(comp)) {
            polylines.push(laneToPolyline(lane));
        }
    }
    return polylines;
}

export async function extractWiresFromImage(inputPath) {
    const meta = await sharp(inputPath).metadata();
    const padded = await sharp(inputPath)
        .extend({
            right: Math.max(0, MAP_WIDTH - meta.width),
            bottom: Math.max(0, MAP_HEIGHT - meta.height),
            background: { r: 0, g: 0, b: 0, alpha: 255 },
        })
        .ensureAlpha()
        .raw()
        .toBuffer({ resolveWithObject: true });

    const { data, info } = padded;
    let grid = buildTraceGrid(data, info.width, info.height);
    const occupiedBefore = grid.reduce((s, v) => s + v, 0);
    grid = pruneIsolatedCells(grid, EXTRACT_W, EXTRACT_H);
    const occupiedAfter = grid.reduce((s, v) => s + v, 0);

    const rawPolylines = extractLanePolylines(grid, EXTRACT_W, EXTRACT_H);
    const wires = polylinesToWires(rawPolylines);

    return {
        wires,
        stats: {
            gridW: GRID_W,
            gridH: GRID_H,
            extractW: EXTRACT_W,
            extractH: EXTRACT_H,
            occupiedBefore,
            occupiedAfter,
            rawPolylines: rawPolylines.length,
            wires: wires.length,
        },
    };
}

export function buildSnapshot(wires) {
    return {
        id: `${Date.now()}_tracing`,
        name: SNAPSHOT_NAME,
        createdAt: Date.now(),
        thumbnail: '',
        data: {
            params: { ...PARAMS },
            obstacles: [],
            wires,
        },
    };
}

async function writeSnapshot(inputPath, outputPath) {
    const { wires, stats } = await extractWiresFromImage(inputPath);
    const snapshot = buildSnapshot(wires);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, JSON.stringify(snapshot, null, 2));
    console.log(`Wrote ${outputPath}`);
    console.log(JSON.stringify(stats, null, 2));
    return snapshot;
}

async function verifySnapshot(snapshotPath) {
    const { chromium } = await import('playwright');
    const snapshot = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
    const port = process.env.VITE_PORT || '5173';
    const url = `http://localhost:${port}/circuit-painter/`;
    const outPng = path.join(root, 'plans/circuit design/tracing-lines-built.png');

    const browser = await chromium.launch();
    const page = await browser.newPage({
        viewport: {
            width: snapshot.data.params.mapWidth + 320,
            height: snapshot.data.params.mapHeight + 80,
        },
    });

    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__circuitPainter?.loadSnapshotData);
    await page.evaluate((data) => {
        window.__circuitPainter.loadSnapshotData(data);
    }, snapshot.data);
    await page.waitForTimeout(800);

    const canvas = page.locator('#circuit-canvas, canvas').first();
    await canvas.screenshot({ path: outPng });
    await browser.close();
    console.log(`Wrote ${outPng}`);
}

async function main() {
    const args = process.argv.slice(2);
    if (args[0] === '--verify') {
        const snapshotPath = args[1] || DEFAULT_OUTPUT;
        await verifySnapshot(snapshotPath);
        return;
    }

    const inputPath = args[0] || DEFAULT_INPUT;
    const outputPath = args[1] || DEFAULT_OUTPUT;
    await writeSnapshot(inputPath, outputPath);
}

const isMain = process.argv[1]
    && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMain) {
    main().catch((err) => {
        console.error(err);
        process.exit(1);
    });
}
