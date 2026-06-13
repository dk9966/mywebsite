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
    getWires,
    initCanvas,
    redraw, resize, resizeLayout,
    setGapRects, setGridDimensions,
    setWires,
} from './canvas.js';
import { initFlowGrid, resetFlowGrid } from './flowGrid.js';
import {
    handleMouseDown, handleMouseMove, handleMouseUp, handleWireEditKeydown, handleWireEditKeyup,
    setGridDimensionsForMouse,
    setRecreateCallback, setRerouteWiresCallback,
} from './mouse.js';
import {
    THIN_PCB_PARAMS,
    generateThinPcbLayout,
} from './boards/thinPcb.js';
import {
    addComponentAtPixel,
    applyObstaclesToGrid,
    clampObstaclesToGrid,
    generateObstacles,
    getObstacles,
    setObstacles,
    setObstacleGridDimensions,
} from './obstacles.js';
import { applyModeDefaults, isGeneratorMode, isPainterMode, resolveAppMode } from './appMode.js';
import {
    GENERATOR_DEFAULT_OBSTACLES,
    GENERATOR_DEFAULT_PARAMS,
} from './boards/generatorDefault.js';
import { buildGui } from './guiSetup.js';
import { DRAG_MIME, getDraggingKind, initPalette } from './palette.js';
import { initObstacleMenu } from './obstacleMenu.js';
import { params } from './params.js';
import { generatePinBusesAsync } from './pinBuses.js';
import { rndInt, setSeed } from './rng.js';
import { captureSnapshot, initSnapshots, saveSnapshotNamed } from './snapshots.js';
import {
    clearWireOverlay, getWireOverlay, hasWireOverlay, importWiresFromOverlay,
    serializeWiresForSnapshot, setWireEditContext, setWireOverlay, syncOverlayFromWires,
} from './wireEdit.js';
import { Cell, Wire, joinAdjacentWires } from './wire.js';

let grid = [];
let wires = [];
let gridWidth = 0;
let gridHeight = 0;
let rebuildToken = 0;
let debounceTimer = null;

const REBUILD_DEBOUNCE_MS = 200;
const PAINTER_SESSION_KEY = 'circuit-painter:session:v2';

function savePainterSession() {
    if (!isPainterMode(resolveAppMode())) return;
    try {
        const wires = getWires();
        if (wires.length) syncOverlayFromWires(wires);
        sessionStorage.setItem(PAINTER_SESSION_KEY, JSON.stringify({
            obstacles: getObstacles().map((o) => ({
                x: o.x, y: o.y, w: o.w, h: o.h, kind: o.kind, qfp: !!o.qfp,
                rot: o.rot | 0,
            })),
            wires: getWireOverlay() || serializeWiresForSnapshot(wires),
        }));
    } catch (err) {
        console.warn('Could not save painter session:', err);
    }
}

function restorePainterSession() {
    try {
        const raw = sessionStorage.getItem(PAINTER_SESSION_KEY);
        if (!raw) return false;
        const data = JSON.parse(raw);
        setObstacles(data.obstacles || []);
        setWireOverlay(data.wires?.length ? data.wires : null);
        return true;
    } catch {
        return false;
    }
}

function startEmptyBoard() {
    setObstacles([]);
    clearWireOverlay();
    rerouteWiresImmediate();
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
    // Floor so the last cell center stays inside the canvas (no +1 spill column).
    gridWidth = Math.max(3, Math.floor(canvas.width / params.cellSize));
    gridHeight = Math.max(3, Math.floor(canvas.height / params.cellSize));

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
        if (params.thinPcbProcedural) {
            const layout = generateThinPcbLayout(params.seed, gridWidth, gridHeight);
            params.thinPcbRouteHints = layout.routeHints;
            setObstacles(layout.obstacles);
        } else {
            params.thinPcbRouteHints = null;
            generateObstacles(gridWidth, gridHeight);
        }
    }
    clampObstaclesToGrid(gridWidth, gridHeight);
    applyObstaclesToGrid(grid, gridWidth, gridHeight);

    setWireEditContext({ grid, gridWidth, gridHeight });

    function commit() {
        if (token !== rebuildToken) return false;
        setGridDimensions(gridWidth, gridHeight);
        setGridDimensionsForMouse(gridWidth, gridHeight);
        return true;
    }

    if (hasWireOverlay()) {
        wires = importWiresFromOverlay(grid, gridWidth, gridHeight);
        if (!commit()) return;
        setGapRects([]);
        setWires(wires);
        redraw();
        savePainterSession();
        return;
    }

    if (params.busMode) {
        const { rects, wires: busWires } = generateBuses(grid, gridWidth, gridHeight);
        if (!commit()) return;
        wires = busWires;
        setGapRects(rects);
        setWires(wires);
        redraw();
        savePainterSession();
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
        savePainterSession();
        return;
    }

    // Show Buses off: no QFP pin stubs — obstacles only unless greedy fill is on.
    wires = [];

    if (params.showGreedyCircuits) {
        const available = [];
        for (let x = 0; x < gridWidth; x++) {
            for (let y = 0; y < gridHeight; y++) {
                if (grid[x][y].available) available.push(grid[x][y]);
            }
        }

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
            wire.isGreedy = true;
            wires.push(wire);
            for (const c of wire.cells) {
                const pos = available.indexOf(c);
                if (pos !== -1) available.splice(pos, 1);
            }
        }

        if (params.joinEndpoints) joinAdjacentWires(wires);
    }

    if (!commit()) return;
    setGapRects([]);
    setWires(wires);
    redraw();
    savePainterSession();
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
    const mode = resolveAppMode();
    applyModeDefaults(params, mode);
    document.title = isPainterMode(mode)
        ? 'Circuit Board Painter'
        : 'Circuit Generator';

    initCanvas();
    const canvas = getCanvas();

    params.clearFlowGrid = () => { resetFlowGrid(); redraw(); };
    params.regenerate = () => {
        clearWireOverlay();
        recreateImmediate();
    };
    params.savePNG = () => {
        const link = document.createElement('a');
        link.download = `circuit_${params.seed}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    setRecreateCallback(recreate);
    setRerouteWiresCallback(rerouteWires);

    const gui = new dat.GUI();
    buildGui(gui, mode, {
        recreate,
        recreateImmediate,
        redraw,
        resizeLayout,
        clearWireOverlay,
    });

    if (isPainterMode(mode)) {
        initSnapshots({
            gui,
            onLoad: rerouteWiresImmediate,
            seedUrls: [
                '/circuit-painter/seeds/thin-pcb.json',
                '/circuit-painter/seeds/circuits-tracing.json',
            ],
        });
    } else if (isGeneratorMode(mode)) {
        initSnapshots({
            gui,
            onLoad: rerouteWiresImmediate,
            seedUrls: [
                '/circuit-painter/seeds/generator-default.json',
                '/circuit-painter/seeds/circuits-tracing.json',
            ],
            storageKey: 'circuit-generator:snapshots:v1',
        });
    }

    document.addEventListener('keyup', (e) => {
        if (isPainterMode(mode)) handleWireEditKeyup(e);
    });

    document.addEventListener('keydown', (e) => {
        if (isPainterMode(mode) && handleWireEditKeydown(e)) return;
        if (e.key !== 'h' && e.key !== 'H') return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.target.closest('input, textarea, select')) return;
        e.preventDefault();
        const hidden = gui.domElement.style.display === 'none';
        gui.domElement.style.display = hidden ? '' : 'none';
        const snapshots = document.getElementById('snapshots-panel');
        if (snapshots) snapshots.style.display = hidden ? '' : 'none';
    });

    initObstacleMenu({
        onChange: () => {
            if (getWires().length) syncOverlayFromWires(getWires());
            rerouteWiresImmediate();
        },
    });

    initPalette();
    canvas.addEventListener('dragover', (e) => {
        if (!getDraggingKind() && !e.dataTransfer.types.includes(DRAG_MIME)) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });
    canvas.addEventListener('drop', (e) => {
        const id = e.dataTransfer.getData(DRAG_MIME) || getDraggingKind();
        if (!id) return;
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        addComponentAtPixel(id, e.clientX - rect.left, e.clientY - rect.top, canvas);
        clearWireOverlay();
        rerouteWiresImmediate();
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

    window.__circuitPainter = {
        applyLayout(obstacles, paramPatch = {}) {
            Object.assign(params, paramPatch);
            setObstacles(obstacles);
            clearWireOverlay();
            rerouteWiresImmediate();
        },
        loadSnapshotData(data) {
            Object.assign(params, data.params);
            setObstacles(data.obstacles);
            setWireOverlay(data.wires?.length ? data.wires : null);
            rerouteWiresImmediate();
        },
        captureSnapshot,
        saveSnapshot: saveSnapshotNamed,
    };

    const boardParam = new URLSearchParams(window.location.search).get('board');
    if (boardParam === 'thin-pcb') {
        Object.assign(params, THIN_PCB_PARAMS);
        clearWireOverlay();
        recreateImmediate();
    } else if (isPainterMode(mode)) {
        if (restorePainterSession()) {
            rerouteWiresImmediate();
        } else {
            startEmptyBoard();
        }
    } else {
        Object.assign(params, GENERATOR_DEFAULT_PARAMS);
        setObstacles(GENERATOR_DEFAULT_OBSTACLES);
        clearWireOverlay();
        rerouteWiresImmediate();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
} else {
    setup();
}
