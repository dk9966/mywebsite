// Orchestrates a regeneration cycle:
//   seed -> grid -> obstacles -> available list -> wires -> redraw
//
// Obstacles are applied as "unavailable" cells on the same grid the routing
// algorithm walks, so it naturally routes around them without any special path
// logic.

import { setSeed, rndInt } from './rng.js';
import { params, rgbaToHex, hexToRgba } from './params.js';
import { initFlowGrid, resetFlowGrid } from './flowGrid.js';
import { Cell, Wire } from './wire.js';
import {
    generateObstacles, applyObstaclesToGrid, getQFPPinSeeds, setObstacleGridDimensions,
    clampObstaclesToGrid,
} from './obstacles.js';
import { initSnapshots } from './snapshots.js';
import {
    initCanvas, getCanvas, setWires, setGridDimensions, redraw, resize,
} from './canvas.js';
import {
    handleMouseDown, handleMouseMove, handleMouseUp,
    setRecreateCallback, setRerouteWiresCallback, setGridDimensionsForMouse,
} from './mouse.js';

let grid = [];
let wires = [];
let gridWidth = 0;
let gridHeight = 0;

// rebuildBoard handles both code paths. When regenerateObstacles=true (default),
// obstacles are placed from scratch using the seed. When false, the current
// obstacles array is kept verbatim (e.g. after the user dragged a corner) and
// only the wires are re-routed around them.
function rebuildBoard({ regenerateObstacles }) {
    setSeed(params.seed);
    const canvas = getCanvas();

    const prevWidth = gridWidth;
    const prevHeight = gridHeight;
    gridWidth = Math.ceil(canvas.width / params.cellSize) + 1;
    gridHeight = Math.ceil(canvas.height / params.cellSize) + 1;

    grid = [];
    for (let x = 0; x < gridWidth; x++) {
        grid[x] = [];
        for (let y = 0; y < gridHeight; y++) grid[x][y] = new Cell(x, y);
    }

    // Preserve painted flow only when dimensions match; otherwise reset.
    initFlowGrid(gridWidth, gridHeight);
    if (prevWidth !== gridWidth || prevHeight !== gridHeight) resetFlowGrid();

    setGridDimensions(gridWidth, gridHeight);
    setGridDimensionsForMouse(gridWidth, gridHeight);
    setObstacleGridDimensions(gridWidth, gridHeight);

    if (regenerateObstacles) {
        generateObstacles(gridWidth, gridHeight);
    }
    // Always clamp before applying: a no-op for freshly-generated obstacles,
    // but the safety net that lets snapshot-loaded obstacles survive a
    // cellSize / viewport change.
    clampObstaclesToGrid(gridWidth, gridHeight);
    applyObstaclesToGrid(grid, gridWidth, gridHeight);

    const available = [];
    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            if (grid[x][y].available) available.push(grid[x][y]);
        }
    }

    wires = [];

    // QFP pin wires are seeded BEFORE the regular wires so they get first
    // crack at the area around each chip -- regular wires then fill the rest.
    // Pin wires also bypass cutOffLength / prioritizeLongWires (a chip with
    // missing pins looks broken), which is why they're spawned in a separate
    // loop here instead of going through the main loop's gating.
    //
    // Done in two passes: reserve every pin cell FIRST so an earlier pin wire
    // can't accidentally consume a later pin's seed (which would silently drop
    // pins). Then grow a wire from each reserved cell.
    const pinSeeds = getQFPPinSeeds(gridWidth, gridHeight);
    const reservedPins = [];
    for (const seed of pinSeeds) {
        const cell = grid[seed.x][seed.y];
        if (!cell.available) continue;
        cell.available = false;
        cell.heading = seed.heading;
        const pos = available.indexOf(cell);
        if (pos !== -1) available.splice(pos, 1);
        reservedPins.push({ cell, heading: seed.heading });
    }
    for (const { cell, heading } of reservedPins) {
        const wire = new Wire(cell, grid, gridWidth, gridHeight, heading);
        wire.isQFPPin = true;
        wire.generate();
        wires.push(wire);
        for (const c of wire.cells) {
            const pos = available.indexOf(c);
            if (pos !== -1) available.splice(pos, 1);
        }
    }

    // When prioritizeLongWires is on, wires whose final length wouldn't even
    // clear cutOffLength get rolled back (their cells are released) so the
    // algorithm can try again in a different spot. We cap consecutive failures
    // so densely-fragmented regions don't trap us in an infinite retry loop.
    const retry = params.prioritizeLongWires;
    const minLength = retry ? Math.max(2, params.cutOffLength + 1) : 0;
    const maxConsecutiveFailures = 60;
    let failures = 0;

    while (available.length) {
        const i = rndInt(available.length);
        const start = available.splice(i, 1)[0];
        start.available = false;

        const wire = new Wire(start, grid, gridWidth, gridHeight);
        wire.generate();

        if (retry && wire.cells.length < minLength) {
            for (const c of wire.cells) {
                c.available = true;
                c.heading = -1;
                available.push(c);
            }
            if (++failures >= maxConsecutiveFailures) break;
            continue;
        }

        failures = 0;
        wires.push(wire);
        for (const c of wire.cells) {
            const pos = available.indexOf(c);
            if (pos !== -1) available.splice(pos, 1);
        }
    }

    setWires(wires);
    redraw();
}

function recreate() {
    rebuildBoard({ regenerateObstacles: true });
}

// Keep the user-edited obstacles, re-route wires only. Called when the user
// drags an obstacle corner -- preserves their resize instead of snapping the
// box back to its seeded shape.
function rerouteWires() {
    rebuildBoard({ regenerateObstacles: false });
}

function setup() {
    initCanvas();
    const canvas = getCanvas();

    params.clearFlowGrid = () => { resetFlowGrid(); redraw(); };
    params.regenerate = () => { recreate(); };
    params.savePNG = () => {
        const link = document.createElement('a');
        link.download = `circuit_${params.seed}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    setRecreateCallback(recreate);
    setRerouteWiresCallback(rerouteWires);

    const gui = new dat.GUI();

    const flow = gui.addFolder('Flow Field Painting');
    flow.add(params, 'paintFlow').name('Enable Painting');
    flow.add(params, 'brushMode', ['brush', 'eraser']).name('Tool');
    flow.add(params, 'brushSize', 1, 20, 1).name('Brush Size');
    flow.add(params, 'brushOpacity', 0, 1, 0.01).name('Opacity');
    flow.add(params, 'angleSmoothing', 0.1, 1, 0.05).name('Angle Smoothing');
    flow.add(params, 'flowInfluence', 0, 1, 0.05).name('Flow Influence');
    flow.add(params, 'autoRegenerate').name('Auto Regenerate');
    flow.add(params, 'showFlowGrid').name('Show Flow Field').onChange(redraw);
    flow.add(params, 'clearFlowGrid').name('Clear Flow Grid');
    flow.open();

    // Ranges widened from the original on cellSize / wireLength / cutOffLength
    // / straightness per request: smaller cells + longer, straighter wires +
    // looser cutoff.
    gui.add(params, 'cellSize', 2, 80, 1).onChange(recreate);
    gui.add(params, 'wireLength', 1, 500, 1).onChange(recreate);
    gui.add(params, 'cutOffLength', 0, 50, 1).onChange(recreate);
    gui.add(params, 'prioritizeLongWires').name('Prioritize Long Wires').onChange(recreate);
    gui.add(params, 'straightness', 0.01, 50, 0.01).onChange(recreate);
    gui.add(params, 'diagonalChance', 0, 1, 0.01).name('Diagonal Chance').onChange(recreate);
    gui.add(params, 'directionality', -1, 1, 0.01).name('Directionality').onChange(recreate);
    gui.add(params, 'collectiveness', 0, 1, 0.01).name('Collectiveness').onChange(recreate);
    gui.add(params, 'showGrid').name('Show Grid').onChange(redraw);
    gui.add(params, 'seed', 0, 10000, 1).name('Seed').onChange(recreate);

    const obstaclesFolder = gui.addFolder('Obstacles');
    obstaclesFolder.add(params, 'obstaclesEnabled').name('Enable Obstacles').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleCount', 1, 500, 1).name('Count').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleSize', 2, 40, 1).name('Size (cells)').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleSizeRandomness', 0, 1, 0.01)
        .name('Size Randomness').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleKeepOut', 0, 5, 1).name('Keep-out').onChange(recreate);
    obstaclesFolder.add(params, 'editObstacles').name('Edit Obstacles (drag corners)').onChange(redraw);
    obstaclesFolder.add(params, 'obstacleSpacingRandomness', 0, 1, 0.01)
        .name('Spacing Randomness').onChange(recreate);
    obstaclesFolder.add(params, 'qfpStyle').name('QFP Style').onChange(recreate);
    obstaclesFolder.add(params, 'qfpFraction', 0, 1, 0.01).name('QFP Fraction').onChange(recreate);
    obstaclesFolder.add(params, 'qfpPinSpacing', 1, 8, 1).name('QFP Pin Spacing').onChange(recreate);
    obstaclesFolder.open();

    initSnapshots({
        gui,
        // After load: params + obstacles already mutated; rerouteWires keeps
        // those obstacles and rebuilds the grid + wires around them.
        onLoad: rerouteWires,
    });

    Object.defineProperty(params, 'bgColorHex', {
        get: () => rgbaToHex(params.bgColor),
        set: (hex) => { params.bgColor = hexToRgba(hex); redraw(); },
    });
    Object.defineProperty(params, 'fgColorHex', {
        get: () => rgbaToHex(params.fgColor),
        set: (hex) => { params.fgColor = hexToRgba(hex); redraw(); },
    });
    gui.addColor(params, 'bgColorHex').name('Background Color');
    gui.addColor(params, 'fgColorHex').name('Foreground Color');
    gui.add(params, 'savePNG').name('Save PNG');

    canvas.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseUp);

    window.addEventListener('resize', () => { resize(); recreate(); });

    recreate();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
} else {
    setup();
}
