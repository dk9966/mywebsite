// Greedy random-walk circuit generator that aligns to the medial-axis
// centerlines of the gaps between obstacles.
//
// Pipeline per rebuild:
//   seed -> grid -> obstacles -> centerlines -> flow field (from centerlines)
//        -> QFP pin wires -> trunk lines -> random-walk fill -> join -> draw
//
// The only new idea vs the original generator: instead of a mouse-painted flow
// grid, the flow grid is filled from the centerline directions, so every wire
// near a corridor leans onto that corridor's axis and the traces bundle.

import { setSeed, rndInt } from './rng.js';
import { params, rgbaToHex, hexToRgba } from './params.js';
import { initFlowGrid, resetFlowGrid } from './flowGrid.js';
import { Cell, Wire, joinAdjacentWires, carveLead } from './wire.js';
import {
    generateObstacles, applyObstaclesToGrid, getQFPPinSeeds,
    setObstacleGridDimensions, clampObstaclesToGrid,
} from './obstacles.js';
import { aStar, pickEdgeCell, pickOppositeEdgeCell } from './pathfind.js';
import { computeCenterlines } from './centerlines.js';
import { applyCenterlineFlow } from './centerlineFlow.js';
import { initSnapshots } from './snapshots.js';
import {
    initCanvas, getCanvas, setWires, setCenterlines, setGridDimensions, redraw, resize,
} from './canvas.js';
import {
    handleMouseDown, handleMouseMove, handleMouseUp,
    setRecreateCallback, setRerouteCallback, setGridDimensionsForMouse,
} from './mouse.js';

let grid = [];
let wires = [];
let gridWidth = 0;
let gridHeight = 0;

const PIN_LEAD_LENGTH = 3;

function rebuildBoard({ regenerateObstacles }) {
    setSeed(params.seed);
    const canvas = getCanvas();

    gridWidth = Math.ceil(canvas.width / params.cellSize) + 1;
    gridHeight = Math.ceil(canvas.height / params.cellSize) + 1;

    grid = [];
    for (let x = 0; x < gridWidth; x++) {
        grid[x] = [];
        for (let y = 0; y < gridHeight; y++) grid[x][y] = new Cell(x, y);
    }

    setGridDimensions(gridWidth, gridHeight);
    setGridDimensionsForMouse(gridWidth, gridHeight);
    setObstacleGridDimensions(gridWidth, gridHeight);

    if (regenerateObstacles) {
        generateObstacles(gridWidth, gridHeight);
    }
    clampObstaclesToGrid(gridWidth, gridHeight);
    applyObstaclesToGrid(grid, gridWidth, gridHeight);

    // Centerlines drive both the optional guide overlay and the flow field.
    const centerlines = computeCenterlines(gridWidth, gridHeight);
    setCenterlines(centerlines);

    // The flow grid is regenerated from scratch every rebuild -- it's derived
    // data, not user-painted, so a clean reset keeps it deterministic.
    initFlowGrid(gridWidth, gridHeight);
    resetFlowGrid();
    applyCenterlineFlow(centerlines, grid, gridWidth, gridHeight);

    wires = [];

    // QFP pin wires first: reserve every pin cell, carve a straight escape
    // lead for each, then grow a trace from each lead tip. Three passes so no
    // pin is starved of its corridor by a sibling's wandering trace.
    const available = [];
    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            if (grid[x][y].available) available.push(grid[x][y]);
        }
    }

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
    for (const pin of reservedPins) {
        pin.lead = carveLead(pin.cell, pin.heading, PIN_LEAD_LENGTH, grid, gridWidth, gridHeight);
    }
    for (const { lead, heading } of reservedPins) {
        const wire = new Wire(lead[0], grid, gridWidth, gridHeight, heading);
        wire.cells = lead;
        wire.last = heading;
        wire.isQFPPin = true;
        wire.generate();
        wires.push(wire);
        for (const c of wire.cells) {
            const pos = available.indexOf(c);
            if (pos !== -1) available.splice(pos, 1);
        }
    }

    // Trunk lines: edge-to-edge A* paths laid before the fill so the random
    // walker routes around them.
    const trunkCount = Math.max(0, params.trunkWireCount | 0);
    for (let t = 0; t < trunkCount; t++) {
        const startInfo = pickEdgeCell(grid, gridWidth, gridHeight);
        if (!startInfo) break;
        const end = pickOppositeEdgeCell(startInfo.side, grid, gridWidth, gridHeight);
        if (!end) break;
        const path = aStar(startInfo.cell, end, grid, gridWidth, gridHeight);
        if (!path || path.length < 2) continue;

        const wire = new Wire(path[0], grid, gridWidth, gridHeight);
        wire.cells = path;
        wire.isTrunk = true;
        for (const c of path) {
            c.available = false;
            c.heading = -1;
            const pos = available.indexOf(c);
            if (pos !== -1) available.splice(pos, 1);
        }
        wires.push(wire);
    }

    // Random-walk fill.
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

    if (params.joinEndpoints) joinAdjacentWires(wires);

    setWires(wires);
    redraw();
}

function recreate() {
    rebuildBoard({ regenerateObstacles: true });
}

function rerouteWires() {
    rebuildBoard({ regenerateObstacles: false });
}

function setup() {
    initCanvas();
    const canvas = getCanvas();

    params.regenerate = () => { recreate(); };
    params.savePNG = () => {
        const link = document.createElement('a');
        link.download = `circuit2_${params.seed}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    setRecreateCallback(recreate);
    setRerouteCallback(rerouteWires);

    const gui = new dat.GUI();

    const lines = gui.addFolder('Circuit Lines');
    lines.add(params, 'alignToCenterlines').name('Align To Centerlines').onChange(recreate);
    lines.add(params, 'centerlineStrength', 0, 255, 1).name('Align Strength').onChange(recreate);
    lines.add(params, 'centerlineFalloff', 1, 80, 1).name('Align Reach (falloff)').onChange(recreate);
    lines.add(params, 'collectiveness', 0, 1, 0.01).name('Bundle (collectiveness)').onChange(recreate);
    lines.add(params, 'flowInfluence', 0, 1, 0.05).name('Flow Influence').onChange(recreate);
    lines.add(params, 'showCenterlines').name('Show Centerlines').onChange(redraw);
    lines.add(params, 'showFlowField').name('Show Flow Field').onChange(redraw);
    lines.open();

    gui.add(params, 'cellSize', 2, 80, 1).onChange(recreate);
    gui.add(params, 'wireLength', 1, 500, 1).onChange(recreate);
    gui.add(params, 'cutOffLength', 0, 50, 1).onChange(recreate);
    gui.add(params, 'prioritizeLongWires').name('Prioritize Long Wires').onChange(recreate);
    gui.add(params, 'trunkWireCount', 0, 20, 1).name('Trunk Lines').onChange(recreate);
    gui.add(params, 'trunksOnly').name('Trunks Only').onChange(redraw);
    gui.add(params, 'joinEndpoints').name('Join Trace Ends').onChange(recreate);
    gui.add(params, 'straightness', 0.01, 50, 0.01).onChange(recreate);
    gui.add(params, 'diagonalChance', 0, 1, 0.01).name('Diagonal Chance').onChange(recreate);
    gui.add(params, 'turnSmoothness', 0, 1, 0.01).name('Turn Smoothness').onChange(recreate);
    gui.add(params, 'directionality', -1, 1, 0.01).name('Directionality').onChange(recreate);
    gui.add(params, 'centerlineMinLength', 1, 20, 1).name('Min Centerline Len').onChange(recreate);
    gui.add(params, 'centerlineSimplify', 0, 2, 0.05).name('Centerline Simplify').onChange(recreate);
    gui.add(params, 'showGrid').name('Show Grid').onChange(redraw);
    gui.add(params, 'seed', 0, 10000, 1).name('Seed').onChange(recreate);

    const obstaclesFolder = gui.addFolder('Obstacles');
    obstaclesFolder.add(params, 'obstaclesEnabled').name('Enable Obstacles').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleCount', 1, 500, 1).name('Count').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleSize', 2, 40, 1).name('Size (cells)').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleSizeRandomness', 0, 1, 0.01)
        .name('Size Randomness').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleKeepOut', 0, 5, 1).name('Keep-out').onChange(recreate);
    obstaclesFolder.add(params, 'obstacleMinSpacing', 0, 20, 1).name('Min Spacing').onChange(recreate);
    obstaclesFolder.add(params, 'editObstacles').name('Edit Obstacles (drag corners)').onChange(redraw);
    obstaclesFolder.add(params, 'obstacleSpacingRandomness', 0, 1, 0.01)
        .name('Spacing Randomness').onChange(recreate);
    obstaclesFolder.add(params, 'qfpStyle').name('QFP Style').onChange(recreate);
    obstaclesFolder.add(params, 'qfpFraction', 0, 1, 0.01).name('QFP Fraction').onChange(recreate);
    obstaclesFolder.add(params, 'qfpPinSpacing', 1, 8, 1).name('QFP Pin Spacing').onChange(recreate);
    obstaclesFolder.open();

    initSnapshots({
        gui,
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

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'h' && e.key !== 'H') return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.target.closest('input, textarea, select')) return;
        e.preventDefault();
        const hidden = gui.domElement.style.display === 'none';
        gui.domElement.style.display = hidden ? '' : 'none';
        const snapshots = document.getElementById('snapshots-panel');
        if (snapshots) snapshots.style.display = hidden ? '' : 'none';
    });

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
