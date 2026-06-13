// Mouse: flow-field painting and obstacle corner resize (when edit mode is on).

import { params } from './params.js';
import { mapDirection8ToFlow4, addFlowStrength, subFlowStrength } from './flowGrid.js';
import {
    hitTestCenter, hitTestCorner, moveObstacle, resizeObstacle, pixelToGrid,
} from './obstacles.js';
import { getCanvas, getWires, redraw } from './canvas.js';
import {
    clearWireChainDraft, deleteSelectedSegment, deleteSelectedWire,
    editPointerDown, editPointerDrag, editPointerUp, getWireChainDraft, pushWireUndo,
    redoWireEdit, setLiveEditAction, syncOverlayFromWires, undoWireEdit, updateChainPreview,
} from './wireEdit.js';

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

// Obstacle edit drag state
let resizeTarget = null; // { obstacle, corner }
let isResizing = false;
let moveTarget = null; // { obstacle, originX, originY, startGx, startGy }
let isMoving = false;

// Wire-edit drag state
let editAction = null; // { kind: 'vertex' | 'segment' | 'newWire', ... }

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
    // Left button only: right/middle clicks are reserved (right-click opens the
    // obstacle Delete menu) and must not start a paint/move/resize drag.
    if (e.button !== 0) return;

    const target = e.target;
    if (target && (target.closest?.('.dg') || target.classList?.contains('dg'))) return;

    const canvas = getCanvas();
    if (target !== canvas) return;

    const pos = getMousePos(e);
    if (pos.x <= 0 || pos.x >= canvas.width || pos.y <= 0 || pos.y >= canvas.height) return;

    // Wire hits first (no Shift). Shift = draw chain. Obstacles when no wire hit.
    if (params.editWires) {
        editAction = editPointerDown(pos.x, pos.y, {
            altKey: e.altKey,
            shiftKey: e.shiftKey,
        });
        if (editAction?.kind === 'deleted') {
            editAction = null;
            setLiveEditAction(null);
            redraw();
            return;
        }
        if (editAction) {
            setLiveEditAction(editAction);
            editDownX = pos.x;
            editDownY = pos.y;
            editMoved = false;
            return;
        }
    }

    if (params.editObstacles && params.obstaclesEnabled && !e.shiftKey) {
        const cornerHit = hitTestCorner(pos.x, pos.y, canvas);
        if (cornerHit) {
            isResizing = true;
            resizeTarget = cornerHit;
            const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
            resizeObstacle(cornerHit.obstacle, cornerHit.corner, gx, gy);
            redraw();
            return;
        }
        const centerHit = hitTestCenter(pos.x, pos.y, canvas);
        if (centerHit) {
            isMoving = true;
            moveTarget = centerHit;
            redraw();
            return;
        }
        return;
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

    if (params.editWires && e.shiftKey && getWireChainDraft()) {
        updateChainPreview(pos.x, pos.y);
        redraw();
        return;
    }

    if (editAction && editAction.kind !== 'deleted') {
        if (!editMoved
            && Math.hypot(pos.x - editDownX, pos.y - editDownY) > CLICK_SLOP) {
            editMoved = true;
            if (!editAction.undoPushed
                && (editAction.kind === 'segment' || editAction.kind === 'endpoint')) {
                pushWireUndo();
                editAction.undoPushed = true;
            }
        }
        if (editMoved
            || editAction.kind === 'segment'
            || editAction.kind === 'endpoint'
            || editAction.kind === 'chain') {
            editPointerDrag(editAction, pos.x, pos.y);
            setLiveEditAction(editAction);
            redraw();
        }
        return;
    }

    if (isMoving && moveTarget) {
        const { gx, gy } = pixelToGrid(pos.x, pos.y, canvas);
        moveObstacle(
            moveTarget.obstacle, gx, gy,
            moveTarget.originX, moveTarget.originY,
            moveTarget.startGx, moveTarget.startGy,
        );
        redraw();
        lastX = pos.x;
        lastY = pos.y;
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
    if (editAction) {
        if (editAction.kind !== 'deleted') {
            editPointerUp(editAction, editDownX, editDownY, editMoved);
        }
        editAction = null;
        setLiveEditAction(null);
        redraw();
        return;
    }

    if (isMoving) {
        isMoving = false;
        moveTarget = null;
        finishObstacleEdit();
        return;
    }

    if (isResizing) {
        isResizing = false;
        resizeTarget = null;
        finishObstacleEdit();
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
    const cw = canvas.width / gridWidth;
    const ch = canvas.height / gridHeight;

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

function finishObstacleEdit() {
    // Keep traced/manual wires when obstacles move or resize — only refresh the
    // occupancy grid and re-import the overlay polylines.
    if (getWires().length) syncOverlayFromWires(getWires());
    if (rerouteWiresCallback) rerouteWiresCallback();
}

function getMousePos(e) {
    const canvas = getCanvas();
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

export function handleWireEditKeyup(e) {
    if (!params.editWires) return false;
    if (e.key === 'Shift') {
        clearWireChainDraft();
        setLiveEditAction(null);
        redraw();
        return true;
    }
    return false;
}

export function handleWireEditKeydown(e) {
    if (!params.editWires) return false;
    if (e.target.closest('input, textarea, select')) return false;

    if ((e.metaKey || e.ctrlKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        const ok = e.shiftKey ? redoWireEdit() : undoWireEdit();
        if (ok) redraw();
        return true;
    }

    if (e.key === 'Delete' || e.key === 'Backspace') {
        if (deleteSelectedSegment() || deleteSelectedWire()) {
            e.preventDefault();
            redraw();
            return true;
        }
    }
    return false;
}
