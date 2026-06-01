// Mouse: flow-field painting and obstacle corner resize (when edit mode is on).

import { params } from './params.js';
import { mapDirection8ToFlow4, addFlowStrength, subFlowStrength } from './flowGrid.js';
import {
    hitTestCorner, resizeObstacle, pixelToGrid,
} from './obstacles.js';
import { getCanvas, redraw } from './canvas.js';
import { editPointerDown, editPointerDrag, editPointerUp } from './wireEdit.js';

const TWO_PI = Math.PI * 2;
// Pointer travel (px) past which a press counts as a drag, not a click.
const CLICK_SLOP = 3;

let mouseAngle = null;
let lastX = null;
let lastY = null;
let isPainting = false;
let gridWidth = 0;
let gridHeight = 0;
let recreateCallback = null;
let rerouteWiresCallback = null;

// Obstacle corner drag state
let resizeTarget = null; // { obstacle, corner }
let isResizing = false;

// Wire-edit drag state
let editAction = null; // { kind: 'vertex' | 'segment', wire, ... }
let editDownX = 0;
let editDownY = 0;
let editMoved = false;

export function setGridDimensionsForMouse(w, h) {
    gridWidth = w;
    gridHeight = h;
}

export function setRecreateCallback(cb) {
    recreateCallback = cb;
}

export function setRerouteWiresCallback(cb) {
    rerouteWiresCallback = cb;
}

export function handleMouseDown(e) {
    const target = e.target;
    if (target && (target.closest?.('.dg') || target.classList?.contains('dg'))) return;

    const canvas = getCanvas();
    if (target !== canvas) return;

    const pos = getMousePos(e);
    if (pos.x <= 0 || pos.x >= canvas.width || pos.y <= 0 || pos.y >= canvas.height) return;

    // Wire editing owns the pointer when on: grab a joint to drag, or record a
    // press on the trace to resolve as a click on release.
    if (params.editWires) {
        editAction = editPointerDown(pos.x, pos.y);
        editDownX = pos.x;
        editDownY = pos.y;
        editMoved = false;
        return;
    }

    // Corner resize takes priority over flow painting when edit mode is on.
    if (params.editObstacles && params.obstaclesEnabled) {
        const hit = hitTestCorner(pos.x, pos.y, canvas);
        if (hit) {
            isResizing = true;
            resizeTarget = hit;
            const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
            resizeObstacle(hit.obstacle, hit.corner, gx, gy);
            redraw();
            return;
        }
    }

    if (!params.paintFlow) return;

    isPainting = true;
    mouseAngle = null;
    lastX = pos.x;
    lastY = pos.y;

    applyBrush(pos.x, pos.y, 1);
    redraw();
}

export function handleMouseMove(e) {
    const canvas = getCanvas();
    const pos = getMousePos(e);

    if (params.editWires) {
        if (!editAction) return;
        if (!editMoved
            && Math.hypot(pos.x - editDownX, pos.y - editDownY) > CLICK_SLOP) {
            editMoved = true;
        }
        if (editMoved) {
            editPointerDrag(editAction, pos.x, pos.y);
            redraw();
        }
        return;
    }

    if (isResizing && resizeTarget) {
        const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
        resizeObstacle(resizeTarget.obstacle, resizeTarget.corner, gx, gy);
        redraw();
        lastX = pos.x;
        lastY = pos.y;
        return;
    }

    if (!isPainting || !params.paintFlow) {
        lastX = pos.x;
        lastY = pos.y;
        return;
    }

    const dx = pos.x - lastX;
    const dy = pos.y - lastY;
    if (Math.abs(dx) > 0.1 || Math.abs(dy) > 0.1) {
        const newAngle = (Math.atan2(dy, dx) + TWO_PI) % TWO_PI;
        if (mouseAngle === null) {
            mouseAngle = newAngle;
        } else {
            let diff = newAngle - mouseAngle;
            if (diff > Math.PI) diff -= TWO_PI;
            if (diff < -Math.PI) diff += TWO_PI;
            mouseAngle = (mouseAngle + diff * params.angleSmoothing + TWO_PI) % TWO_PI;
        }

        const dir8 = (Math.round(mouseAngle / (TWO_PI / 8)) + 3) % 8;
        const flowDir = mapDirection8ToFlow4(dir8);

        applyBrush(pos.x, pos.y, flowDir);
        redraw();
    }

    lastX = pos.x;
    lastY = pos.y;
}

export function handleMouseUp() {
    if (params.editWires) {
        if (editAction) {
            editPointerUp(editAction, editDownX, editDownY, editMoved);
            editAction = null;
            redraw();
        }
        return;
    }

    if (isResizing) {
        isResizing = false;
        resizeTarget = null;
        // Re-route wires around the user's resized obstacles. Must NOT call
        // recreateCallback here -- that would regenerate obstacles from seed
        // and wipe the user's resize.
        if (rerouteWiresCallback) rerouteWiresCallback();
        return;
    }

    if (isPainting && params.autoRegenerate && recreateCallback) recreateCallback();
    isPainting = false;
    mouseAngle = null;
    lastX = null;
    lastY = null;
}

function applyBrush(px, py, flowDir) {
    const canvas = getCanvas();
    const sx = (1 + canvas.width / params.cellSize) / gridWidth;
    const sy = (1 + canvas.height / params.cellSize) / gridHeight;
    const cw = params.cellSize * sx;
    const ch = params.cellSize * sy;

    const centerGx = px / cw;
    const centerGy = py / ch;
    const radius = params.brushSize;
    const radiusSq = radius * radius;

    for (let dx = -radius; dx <= radius; dx++) {
        for (let dy = -radius; dy <= radius; dy++) {
            const distSq = dx * dx + dy * dy;
            if (distSq > radiusSq) continue;

            const gx = Math.floor(centerGx + dx);
            const gy = Math.floor(centerGy + dy);
            if (gx < 0 || gx >= gridWidth || gy < 0 || gy >= gridHeight) continue;

            const dist = Math.sqrt(distSq);
            let falloff = dist > 0 ? 1 - dist / radius : 1;
            falloff = falloff * falloff * (3 - 2 * falloff);

            const amount = Math.floor(params.brushOpacity * falloff * 255);
            if (amount <= 0) continue;

            if (params.brushMode === 'brush') addFlowStrength(gx, gy, flowDir, amount);
            else subFlowStrength(gx, gy, flowDir, amount);
        }
    }
}

function getMousePos(e) {
    const canvas = getCanvas();
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}
