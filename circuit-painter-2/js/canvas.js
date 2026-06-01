import { params } from './params.js';
import { drawObstacles, drawObstacleHandles } from './obstacles.js';
import { drawCenterlines } from './centerlines.js';
import { drawFlowOverlay } from './flowGrid.js';

let canvas = null;
let ctx = null;
let wires = [];
let centerlines = [];
let gridWidth = 0;
let gridHeight = 0;

export function getCanvas() { return canvas; }
export function getCtx() { return ctx; }
export function setWires(next) { wires = next || []; }
export function setCenterlines(next) { centerlines = next || []; }
export function setGridDimensions(w, h) { gridWidth = w; gridHeight = h; }

export function initCanvas() {
    canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.zIndex = '0';
    document.body.appendChild(canvas);

    ctx = canvas.getContext('2d');
    resize();
}

export function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    return { width: canvas.width, height: canvas.height };
}

export function draw() {
    ctx.fillStyle = params.bgColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Obstacles first, then traces on top -- this is what fuses a QFP pin tab
    // with the trace that starts at the adjacent pin cell.
    drawObstacles(canvas, ctx, gridWidth, gridHeight);
    drawObstacleHandles(canvas, ctx);

    for (const w of wires) {
        if (w.isQFPPin || w.cells.length > params.cutOffLength) {
            if (params.trunksOnly && !w.isTrunk && !w.isQFPPin) continue;
            w.render(canvas, ctx);
        }
    }

    if (params.showCenterlines) {
        drawCenterlines(canvas, ctx, gridWidth, gridHeight, centerlines);
    }
    drawFlowOverlay(canvas, ctx, params);
    drawGridOverlay();
}

export function redraw() {
    draw();
}

function drawGridOverlay() {
    if (!params.showGrid) return;
    const sx = (1 + canvas.width / params.cellSize) / gridWidth;
    const sy = (1 + canvas.height / params.cellSize) / gridHeight;
    const cw = params.cellSize * sx;
    const ch = params.cellSize * sy;

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
