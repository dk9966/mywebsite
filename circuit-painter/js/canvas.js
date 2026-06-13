// Canvas setup + draw loop. Owns the <canvas> element and orchestrates the
// per-frame composition: background, wires, obstacles, flow overlay, grid.

import { params } from './params.js';
import { drawFlowOverlay } from './flowGrid.js';
import { drawObstacles, drawObstacleHandles } from './obstacles.js';
import { drawChainPreview, drawSelectedSegment, drawWireHandles } from './wireEdit.js';

let stage = null;
let canvas = null;
let ctx = null;
let wires = [];
let gapRects = [];
let gridWidth = 0;
let gridHeight = 0;

export function getCanvas() { return canvas; }
export function getCtx() { return ctx; }
export function setWires(next) { wires = next; }
export function getWires() { return wires; }
export function appendWire(w) { wires.push(w); }
export function removeWire(w) {
    const i = wires.indexOf(w);
    if (i !== -1) wires.splice(i, 1);
}
export function setGapRects(next) { gapRects = next || []; }
export function setGridDimensions(w, h) { gridWidth = w; gridHeight = h; }
export function getGridDimensions() { return { w: gridWidth, h: gridHeight }; }

// Single source of truth for "is this wire on screen right now" -- shared by
// the draw loop and the wire editor so handles only appear on visible traces.
function isWireVisible(w) {
    if (!params.showCircuits) return false;
    if (w.manual || w.points) return true;
    if (w.isRoute) return true;
    if (w.isBus && !params.showBuses) return false;
    if (w.isQFPPin && !params.showBuses) return false;
    if (w.isGreedy && !params.showGreedyCircuits) return false;
    if (w.isBus || w.isQFPPin) return true;
    if (w.isGreedy) return w.cells.length > params.cutOffLength;
    return w.cells.length > params.cutOffLength;
}

export function getVisibleWires() { return wires.filter(isWireVisible); }

export function initCanvas() {
    stage = document.createElement('div');
    stage.className = 'map-stage';

    canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.position = 'absolute';
    canvas.style.zIndex = '0';
    stage.appendChild(canvas);
    document.body.appendChild(stage);

    ctx = canvas.getContext('2d');
    resize();
}

function mapDimensions() {
    return {
        w: Math.min(2000, Math.max(500, params.mapWidth | 0)),
        h: Math.min(1200, Math.max(50, params.mapHeight | 0)),
    };
}

// Vertical room kept clear at the top so the centered canvas never slides
// under the fixed component palette bar.
const TOP_RESERVE = 104;

// CSS/stage layout only — does not touch canvas.width/height, so the backing
// buffer (and current frame) stay intact while a debounced rebuild is pending.
export function resizeLayout() {
    const { w, h } = mapDimensions();
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const stageW = Math.max(window.innerWidth, w);
    const stageH = Math.max(window.innerHeight, h + TOP_RESERVE);
    stage.style.width = `${stageW}px`;
    stage.style.height = `${stageH}px`;
    canvas.style.left = `${(stageW - w) / 2}px`;
    canvas.style.top = `${Math.max(TOP_RESERVE, (stageH - h) / 2)}px`;
}

export function resize() {
    const { w, h } = mapDimensions();
    // Reassigning width/height clears the backing buffer even when the value
    // is unchanged -- skip if we already match so incidental resize events
    // (tab switch, mobile URL bar) don't wipe the frame.
    if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
    }
    resizeLayout();

    return { width: w, height: h };
}

export function draw() {
    ctx.fillStyle = params.bgColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Obstacles first, then wires on top. This is what gives QFP pin tabs
    // their visual connection to the trace: the trace's first segment renders
    // over the pin tab, fusing them into one continuous fg-colored shape.
    drawObstacles(canvas, ctx, gridWidth, gridHeight);
    drawObstacleHandles(canvas, ctx);
    drawGapRects();

    // QFP pin stubs always render even if shorter than cutOffLength -- an
    // invisible pin would look like a broken chip (see isWireVisible).
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    ctx.clip();
    for (const w of getVisibleWires()) w.render(canvas, ctx);
    ctx.restore();

    if (params.editWires) drawSelectedSegment(ctx);

    drawFlowOverlay(canvas, ctx, params);
    drawGridOverlay();

    if (params.editWires) {
        drawWireHandles(ctx);
        drawChainPreview(ctx);
    }
}

export function redraw() {
    draw();
}

function drawGapRects() {
    if (!params.showGapRects || !gapRects.length) return;
    const cw = canvas.width / gridWidth;
    const ch = canvas.height / gridHeight;

    ctx.strokeStyle = params.fgColor;
    ctx.globalAlpha = 0.25;
    ctx.lineWidth = 1;
    for (const r of gapRects) {
        ctx.strokeRect(r.x * cw, r.y * ch, r.w * cw, r.h * ch);
    }
    ctx.globalAlpha = 1;
}

function drawGridOverlay() {
    if (!params.showGrid) return;
    const cw = canvas.width / gridWidth;
    const ch = canvas.height / gridHeight;

    ctx.strokeStyle = 'rgba(230, 230, 230, 0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i <= gridWidth; i++) {
        ctx.moveTo(i * cw, 0);
        ctx.lineTo(i * cw, canvas.height);
    }
    for (let j = 0; j <= gridHeight; j++) {
        ctx.moveTo(0, j * ch);
        ctx.lineTo(canvas.width, j * ch);
    }
    ctx.stroke();
}
