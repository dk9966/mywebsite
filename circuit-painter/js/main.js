// Orchestrates a regeneration cycle:
//   seed -> grid -> obstacles -> available list -> wires -> redraw
//
// Obstacles are applied as "unavailable" cells on the same grid the routing
// algorithm walks, so it naturally routes around them without any special path
// logic.

import { generateBuses } from './bus.js';
import {
    getCanvas,
    getCtx,
    initCanvas,
    redraw, resize, resizeLayout,
    setGapRects, setGridDimensions,
    setWires,
} from './canvas.js';
import { initFlowGrid, resetFlowGrid } from './flowGrid.js';
import {
    handleMouseDown, handleMouseMove, handleMouseUp,
    setGridDimensionsForMouse,
    setRecreateCallback, setRerouteWiresCallback,
} from './mouse.js';
import {
    applyObstaclesToGrid,
    clampObstaclesToGrid,
    generateObstacles,
    getQFPPinSeeds, setObstacleGridDimensions,
} from './obstacles.js';
import { hexToRgba, params, rgbaToHex } from './params.js';
import { generatePinBusesAsync } from './pinBuses.js';
import { rndInt, setSeed } from './rng.js';
import { initSnapshots } from './snapshots.js';
import { Cell, Wire, carveLead, joinAdjacentWires } from './wire.js';

let grid = [];
let wires = [];
let gridWidth = 0;
let gridHeight = 0;
let rebuildToken = 0;
let debounceTimer = null;

const REBUILD_DEBOUNCE_MS = 200;

// How many cells each QFP pin runs straight out from the chip before its trace
// is free to wander. A short perpendicular lead reads as a real pin (the
// classic QFP fan-out) and, reserved up front for every pin, guarantees no pin
// is left as a disconnected pad. carveLead clamps this against bounds and
// neighbours, so a value larger than the local gap simply yields a shorter run.
const PIN_LEAD_LENGTH = 3;

// Show/hide a dat.GUI controller by toggling its <li> row. dat.GUI stores the
// row as `__li`; the parent of the controller's input div is the same element
// as a fallback.
function setControllerVisible(controller, visible) {
    const li = controller.__li || controller.domElement?.parentElement;
    if (li) li.style.display = visible ? '' : 'none';
}

// rebuildBoard handles both code paths. When regenerateObstacles=true (default),
// obstacles are placed from scratch using the seed. When false, the current
// obstacles array is kept verbatim (e.g. after the user dragged a corner) and
// only the wires are re-routed around them.
async function rebuildBoard({ regenerateObstacles, token }) {
    setSeed(params.seed);
    resize();
    const canvas = getCanvas();
    const ctx = getCtx();

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

    setObstacleGridDimensions(gridWidth, gridHeight);

    if (regenerateObstacles) {
        generateObstacles(gridWidth, gridHeight);
    }
    clampObstaclesToGrid(gridWidth, gridHeight);
    applyObstaclesToGrid(grid, gridWidth, gridHeight);

    function commit() {
        if (token !== rebuildToken) return false;
        setGridDimensions(gridWidth, gridHeight);
        setGridDimensionsForMouse(gridWidth, gridHeight);
        return true;
    }

    if (params.busMode) {
        const { rects, wires: busWires } = generateBuses(grid, gridWidth, gridHeight);
        if (!commit()) return;
        wires = busWires;
        setGapRects(rects);
        setWires(wires);
        redraw();
        return;
    }

    if (params.showBuses) {
        ctx.fillStyle = params.bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        wires = await generatePinBusesAsync(grid, gridWidth, gridHeight);
        if (!commit()) return;
        setGapRects([]);
        setWires(wires);
        redraw();
        return;
    }

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
    // Done in three passes so every pin ends up connected to a trace rather
    // than stranded as a bare pad against the chip body:
    //   1. Reserve every pin cell, so an earlier pin wire can't consume a
    //      later pin's seed.
    //   2. Reserve a short straight escape lead outward from every pin. Doing
    //      this for ALL pins before growing any wire is what guarantees
    //      fairness: a pin's wandering trace can no longer eat the corridor a
    //      sibling pin needs to reach the board.
    //   3. Grow each pin's wire onward from the tip of its lead, so the lead
    //      becomes the start of a real trace that weaves into the routing.
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

    if (params.joinEndpoints) joinAdjacentWires(wires);

    if (!commit()) return;
    setWires(wires);
    redraw();
}

function scheduleRebuild(regenerateObstacles, immediate = false) {
    rebuildToken++;
    const token = rebuildToken;
    clearTimeout(debounceTimer);

    const run = () => { rebuildBoard({ regenerateObstacles, token }); };

    if (immediate) {
        run();
    } else {
        debounceTimer = setTimeout(run, REBUILD_DEBOUNCE_MS);
    }
}

function recreate() {
    scheduleRebuild(true);
}

function recreateImmediate() {
    scheduleRebuild(true, true);
}

// Keep the user-edited obstacles, re-route wires only. Called when the user
// drags an obstacle corner -- preserves their resize instead of snapping the
// box back to its seeded shape.
function rerouteWires() {
    scheduleRebuild(false);
}

function rerouteWiresImmediate() {
    scheduleRebuild(false, true);
}

function setup() {
    initCanvas();
    const canvas = getCanvas();

    params.clearFlowGrid = () => { resetFlowGrid(); redraw(); };
    params.regenerate = () => { recreateImmediate(); };
    params.savePNG = () => {
        const link = document.createElement('a');
        link.download = `circuit_${params.seed}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    setRecreateCallback(recreate);
    setRerouteWiresCallback(rerouteWires);

    const gui = new dat.GUI();

    // One folder, two faces. The Bus Mode checkbox swaps between the bus
    // controls (default) and the legacy flow-field painting controls; only one
    // set is visible at a time.
    const flow = gui.addFolder('Circuit Lines');
    flow.add(params, 'busMode').name('Bus Mode')
        .onChange(() => { syncCircuitModeUI(); recreate(); });

    const busControls = [
        flow.add(params, 'busSpineMode', ['gapRects', 'centerline']).name('Bus Spine')
            .onChange(() => { syncBusSpineUI(); recreate(); }),
        flow.add(params, 'gapRectMinSize', 2, 40, 1).name('Gap Min Size').onChange(recreate),
        flow.add(params, 'gapRectMaxSize', 4, 80, 1).name('Gap Max Size').onChange(recreate),
        flow.add(params, 'gapRectCount', 1, 600, 1).name('Max Gaps').onChange(recreate),
        flow.add(params, 'centerlineMinLength', 1, 20, 1).name('Min Corridor Len').onChange(recreate),
        flow.add(params, 'centerlineSimplify', 0, 2, 0.05).name('Corridor Simplify').onChange(recreate),
        flow.add(params, 'corridorJunctionInset', 0, 8, 1).name('Junction Inset').onChange(recreate),
        flow.add(params, 'corridorMaxLines', 1, 40, 1).name('Max Lines / Corridor').onChange(recreate),
        flow.add(params, 'busLineSpacing', 0, 12, 1).name('Line Spacing').onChange(recreate),
        flow.add(params, 'connectBuses').name('Connect Buses').onChange(recreate),
        flow.add(params, 'busTailLength', 0, 20, 1).name('Slant Length').onChange(recreate),
        flow.add(params, 'showGapRects').name('Show Gaps').onChange(redraw),
    ];

    const gapRectControls = busControls.slice(1, 4);
    const centerlineControls = busControls.slice(4, 8);
    const sharedBusControls = busControls.slice(8);

    const flowControls = [
        flow.add(params, 'paintFlow').name('Enable Painting'),
        flow.add(params, 'brushMode', ['brush', 'eraser']).name('Tool'),
        flow.add(params, 'brushSize', 1, 20, 1).name('Brush Size'),
        flow.add(params, 'brushOpacity', 0, 1, 0.01).name('Opacity'),
        flow.add(params, 'angleSmoothing', 0.1, 1, 0.05).name('Angle Smoothing'),
        flow.add(params, 'flowInfluence', 0, 1, 0.05).name('Flow Influence'),
        flow.add(params, 'autoRegenerate').name('Auto Regenerate'),
        flow.add(params, 'showFlowGrid').name('Show Flow Field').onChange(redraw),
        flow.add(params, 'clearFlowGrid').name('Clear Flow Grid'),
    ];

    function syncBusSpineUI() {
        const centerline = params.busSpineMode === 'centerline';
        for (const c of gapRectControls) setControllerVisible(c, !centerline);
        for (const c of centerlineControls) setControllerVisible(c, centerline);
    }

    function syncCircuitModeUI() {
        for (const c of busControls) setControllerVisible(c, params.busMode);
        for (const c of flowControls) setControllerVisible(c, !params.busMode);
        if (params.busMode) syncBusSpineUI();
    }
    syncCircuitModeUI();
    flow.domElement.style.display = 'none';

    // Ranges widened from the original on cellSize / wireLength / cutOffLength
    // / straightness per request: smaller cells + longer, straighter wires +
    // looser cutoff.
    gui.add(params, 'cellSize', 2, 80, 1).onChange(recreate);
    gui.add(params, 'mapWidth', 500, 2000, 10).name('Map Width')
        .onChange(() => { resizeLayout(); recreate(); });
    gui.add(params, 'mapHeight', 50, 1200, 10).name('Map Height')
        .onChange(() => { resizeLayout(); recreate(); });
    gui.add(params, 'wireLength', 1, 500, 1).onChange(recreate);
    gui.add(params, 'cutOffLength', 0, 50, 1).onChange(recreate);
    gui.add(params, 'prioritizeLongWires').name('Prioritize Long Wires').onChange(recreate);
    gui.add(params, 'joinEndpoints').name('Join Trace Ends').onChange(recreate);
    gui.add(params, 'straightness', 0.01, 50, 0.01).onChange(recreate);
    gui.add(params, 'diagonalChance', 0, 1, 0.01).name('Diagonal Chance').onChange(recreate);
    gui.add(params, 'turnSmoothness', 0, 1, 0.01).name('Turn Smoothness').onChange(recreate);
    gui.add(params, 'directionality', -1, 1, 0.01).name('Directionality').onChange(recreate);
    gui.add(params, 'collectiveness', 0, 1, 0.01).name('Collectiveness').onChange(recreate);
    gui.add(params, 'showBuses').name('Show Buses').onChange(recreate);
    gui.add(params, 'pinBusSlantLength', 1, 30, 1).name('Slant Length').onChange(recreate);
    gui.add(params, 'pinBusStraightMax', 2, 60, 1).name('Straight Max').onChange(recreate);
    gui.add(params, 'pinBusWireCount', 1, 16, 1).name('Bus Wires').onChange(recreate);
    gui.add(params, 'showCircuits').name('Show Circuits').onChange(redraw);
    gui.add(params, 'editWires').name('Edit Wires (drag joints)').onChange(redraw);
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
    obstaclesFolder.add(params, 'qfpSize', 2, 40, 1).name('QFP Size (cells)').onChange(recreate);
    obstaclesFolder.add(params, 'qfpSizeRandomness', 0, 1, 0.01)
        .name('QFP Size Randomness').onChange(recreate);
    obstaclesFolder.add(params, 'qfpPinSpacing', 1, 8, 1).name('QFP Pin Spacing').onChange(recreate);
    obstaclesFolder.open();

    initSnapshots({
        gui,
        onLoad: rerouteWiresImmediate,
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

    window.addEventListener('resize', () => { resize(); redraw(); });

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            resize();
            redraw();
        }
    });

    recreateImmediate();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
} else {
    setup();
}
