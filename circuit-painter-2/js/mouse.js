import { params } from './params.js';
import { hitTestCorner, resizeObstacle, pixelToGrid } from './obstacles.js';
import { getCanvas, redraw } from './canvas.js';

let gridWidth = 0;
let gridHeight = 0;
let recreateCallback = null;
let rerouteCallback = null;

let resizeTarget = null;
let isResizing = false;

export function setGridDimensionsForMouse(w, h) {
    gridWidth = w;
    gridHeight = h;
}

export function setRecreateCallback(cb) {
    recreateCallback = cb;
}

export function setRerouteCallback(cb) {
    rerouteCallback = cb;
}

export function handleMouseDown(e) {
    const target = e.target;
    if (target && (target.closest?.('.dg') || target.classList?.contains('dg'))) return;

    const canvas = getCanvas();
    if (target !== canvas) return;

    const pos = getMousePos(e);
    if (pos.x <= 0 || pos.x >= canvas.width || pos.y <= 0 || pos.y >= canvas.height) return;

    if (params.editObstacles && params.obstaclesEnabled) {
        const hit = hitTestCorner(pos.x, pos.y, canvas);
        if (hit) {
            isResizing = true;
            resizeTarget = hit;
            const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
            resizeObstacle(hit.obstacle, hit.corner, gx, gy);
            redraw();
        }
    }
}

export function handleMouseMove(e) {
    if (!isResizing || !resizeTarget) return;

    const canvas = getCanvas();
    const pos = getMousePos(e);
    const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
    resizeObstacle(resizeTarget.obstacle, resizeTarget.corner, gx, gy);
    redraw();
}

export function handleMouseUp() {
    if (isResizing) {
        isResizing = false;
        resizeTarget = null;
        if (rerouteCallback) rerouteCallback();
    }
}

function getMousePos(e) {
    const canvas = getCanvas();
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}
