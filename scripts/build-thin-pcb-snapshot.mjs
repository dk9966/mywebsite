import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import {
    THIN_PCB_PARAMS,
    THIN_PCB_SNAPSHOT_NAME,
    generateThinPcbLayout,
} from '../circuit-painter/js/boards/thinPcb.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const outPath = path.join(root, 'circuit-painter', 'seeds', 'thin-pcb.json');
const port = process.env.VITE_PORT || '5174';
const url = `http://localhost:${port}/circuit-painter/?board=thin-pcb`;
const cellSize = THIN_PCB_PARAMS.cellSize || 9;
const gridWidth = Math.max(3, Math.floor(THIN_PCB_PARAMS.mapWidth / cellSize));
const gridHeight = Math.max(3, Math.floor(THIN_PCB_PARAMS.mapHeight / cellSize));
const layout = generateThinPcbLayout(THIN_PCB_PARAMS.seed, gridWidth, gridHeight);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__circuitPainter?.captureSnapshot);

const snapshot = await page.evaluate(async ({ obstacles, baseParams, name }) => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));

    window.__circuitPainter.applyLayout(obstacles, {
        ...baseParams,
        showBuses: true,
        showGreedyCircuits: false,
        busMode: false,
    });
    await wait(4500);
    const routedSnap = window.__circuitPainter.captureSnapshot(name);
    window.__circuitPainter.loadSnapshotData(routedSnap.data);
    await wait(500);

    return {
        snapshot: {
            ...routedSnap,
            thumbnail: window.__circuitPainter.captureSnapshot(name).thumbnail,
        },
        busWires: routedSnap.data.wires.length,
        greedyWires: 0,
    };
}, {
    obstacles: layout.obstacles,
    baseParams: {
        ...THIN_PCB_PARAMS,
        thinPcbRouteHints: layout.routeHints,
    },
    name: THIN_PCB_SNAPSHOT_NAME,
});

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(snapshot.snapshot, null, 2));

await page.screenshot({
    path: path.join(root, 'plans', 'circuit design', 'thin-pcb-built.png'),
});

await browser.close();

console.log(`Wrote ${outPath}`);
console.log(
    `Obstacles: ${layout.obstacles.length}, `
    + `pin-bus wires: ${snapshot.busWires}, `
    + `greedy wires: ${snapshot.greedyWires}, `
    + `total: ${snapshot.snapshot.data.wires.length}`,
);
