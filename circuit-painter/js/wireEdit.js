// Manual wire editing: slide segments orthogonally (H/V/45° preserved), joint
// click disconnects, draw/delete, snapshots, undo.

import { params } from './params.js';
import { getQFPPinSeeds } from './obstacles.js';
import {
    appendWire, getCanvas, getGridDimensions, getVisibleWires, getWires, removeWire,
    setWires,
} from './canvas.js';
import { Wire } from './wire.js';

const UNDO_MAX = 80;

let wireOverlay = null;
let undoStack = [];
let redoStack = [];
let editContext = null;
let selectedWire = null;
let selectedSegment = null; // { wire, segIndex }
let liveEditAction = null;
// Shift-click polyline: points committed so far + live preview to cursor.
let wireChainDraft = null;

export function setLiveEditAction(action) {
    liveEditAction = action;
}

export function getLiveEditAction() {
    return liveEditAction;
}

export function setWireEditContext(ctx) {
    editContext = ctx;
}

export function hasWireOverlay() {
    return wireOverlay !== null && wireOverlay.length > 0;
}

export function clearWireOverlay() {
    wireOverlay = null;
    clearWireUndo();
}

export function clearWireUndo() {
    undoStack = [];
    redoStack = [];
}

export function setWireOverlay(data) {
    wireOverlay = data?.length ? data : null;
    clearWireUndo();
}

export function getWireOverlay() {
    return wireOverlay;
}

export function getSelectedWire() {
    return selectedWire;
}

export function clearSelectedWire() {
    selectedWire = null;
    selectedSegment = null;
}

function selectSegment(wire, segIndex) {
    selectedWire = wire;
    selectedSegment = { wire, segIndex };
}

export function getSelectedSegment() {
    return selectedSegment;
}

export function getWireChainDraft() {
    return wireChainDraft;
}

export function clearWireChainDraft() {
    wireChainDraft = null;
}

// --- coordinates -----------------------------------------------------------

function metrics() {
    const canvas = getCanvas();
    const { w: gw, h: gh } = getGridDimensions();
    const cw = canvas.width / gw;
    const ch = canvas.height / gh;
    return { cw, ch };
}

function toPixel(p, cw, ch) {
    return { px: (p.x + 0.5) * cw, py: (p.y + 0.5) * ch };
}

function toGrid(px, py, cw, ch) {
    return { x: px / cw - 0.5, y: py / ch - 0.5 };
}

export function snapToGrid(p) {
    return { x: Math.round(p.x), y: Math.round(p.y) };
}

const DIRS_8 = [
    [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1],
];

function hitQFPPin(px, py, cw, ch) {
    const { w: gw, h: gh } = getGridDimensions();
    const seeds = getQFPPinSeeds(gw, gh);
    const r = Math.max(10, Math.min(cw, ch) * 0.65);
    let best = null;
    let bestDist = r;
    for (const s of seeds) {
        const { px: spx, py: spy } = toPixel({ x: s.x, y: s.y }, cw, ch);
        const d = Math.hypot(px - spx, py - spy);
        if (d <= bestDist) {
            bestDist = d;
            best = { x: s.x, y: s.y };
        }
    }
    return best;
}

function snapDrawPoint(px, py, anchor) {
    const { cw, ch } = metrics();
    const pin = hitQFPPin(px, py, cw, ch);
    if (pin) return pin;
    const raw = toGrid(px, py, cw, ch);
    if (anchor) return snapTraceEndpoint(anchor, raw);
    return snapToGrid(raw);
}

function syncChainToWire() {
    if (!editContext || !wireChainDraft || wireChainDraft.points.length < 2) return;

    const points = wireChainDraft.points.map((p) => ({ x: p.x, y: p.y }));
    if (!wireChainDraft.wire) {
        if (!wireChainDraft.undoPushed) {
            pushWireUndo();
            wireChainDraft.undoPushed = true;
        }
        const { grid, gridWidth, gridHeight } = editContext;
        wireChainDraft.wire = wireFromSerialized({ points, manual: true }, grid, gridWidth, gridHeight);
        appendWire(wireChainDraft.wire);
        selectedWire = wireChainDraft.wire;
    } else {
        wireChainDraft.wire.points = points;
        wireChainDraft.wire.manual = true;
    }
    commitEdits();
}

function initChainFromWire(wire, endIndex) {
    const pts = materialize(wire).map((p) => ({ x: p.x, y: p.y }));
    wireChainDraft = {
        wire,
        points: pts,
        undoPushed: true,
        previewEnd: { ...pts[endIndex] },
    };
    selectedWire = wire;
}

export function updateChainPreview(px, py) {
    if (!wireChainDraft?.points.length) return;
    const last = wireChainDraft.points[wireChainDraft.points.length - 1];
    wireChainDraft.previewEnd = snapDrawPoint(px, py, last);
}

function handleShiftWireClick(px, py) {
    const anchor = wireChainDraft?.points?.length
        ? wireChainDraft.points[wireChainDraft.points.length - 1]
        : null;
    const pt = snapDrawPoint(px, py, anchor);

    if (!wireChainDraft) {
        wireChainDraft = { points: [pt], wire: null, undoPushed: false };
        updateChainPreview(px, py);
        return true;
    }

    const last = wireChainDraft.points[wireChainDraft.points.length - 1];
    if (pt.x !== last.x || pt.y !== last.y) {
        wireChainDraft.points.push(pt);
        if (wireChainDraft.points.length >= 2) syncChainToWire();
    }
    updateChainPreview(px, py);
    return true;
}

function snapTraceEndpoint(anchor, raw) {
    const dx = raw.x - anchor.x;
    const dy = raw.y - anchor.y;
    if (dx === 0 && dy === 0) return { x: anchor.x, y: anchor.y };

    const ax = Math.abs(dx);
    const ay = Math.abs(dy);
    let best = null;
    let bestDist = Infinity;

    for (const [ux, uy] of DIRS_8) {
        let len;
        if (ux !== 0 && uy !== 0) {
            len = Math.max(1, Math.round(Math.min(ax, ay)));
        } else if (ux !== 0) {
            len = Math.max(1, Math.round(ax));
        } else {
            len = Math.max(1, Math.round(ay));
        }
        const x = anchor.x + ux * len;
        const y = anchor.y + uy * len;
        const dist = (x - raw.x) ** 2 + (y - raw.y) ** 2;
        if (dist < bestDist) {
            bestDist = dist;
            best = { x, y };
        }
    }
    return best;
}

function vertexHitRadius(cw, ch) {
    return Math.max(9, Math.min(cw, ch) * 0.75);
}

function segmentHitRadius(cw, ch) {
    return Math.max(6, Math.min(cw, ch) * 0.6);
}

// --- polyline geometry -----------------------------------------------------

export function cornersFromCells(cells) {
    if (cells.length <= 2) return cells.map((c) => ({ x: c.x, y: c.y }));
    const pts = [{ x: cells[0].x, y: cells[0].y }];
    for (let i = 1; i < cells.length - 1; i++) {
        const a = cells[i - 1];
        const b = cells[i];
        const c = cells[i + 1];
        const inX = Math.sign(b.x - a.x);
        const inY = Math.sign(b.y - a.y);
        const outX = Math.sign(c.x - b.x);
        const outY = Math.sign(c.y - b.y);
        if (inX !== outX || inY !== outY) pts.push({ x: b.x, y: b.y });
    }
    const last = cells[cells.length - 1];
    pts.push({ x: last.x, y: last.y });
    return pts;
}

export function wirePoints(wire) {
    return wire.points || cornersFromCells(wire.cells);
}

function materialize(wire) {
    if (!wire.points) wire.points = wirePoints(wire);
    wire.manual = true;
    return wire.points;
}

function pointToSegment(px, py, ax, ay, bx, by) {
    const vx = bx - ax;
    const vy = by - ay;
    const lenSq = vx * vx + vy * vy;
    let t = lenSq > 0 ? ((px - ax) * vx + (py - ay) * vy) / lenSq : 0;
    t = Math.max(0, Math.min(1, t));
    const cx = ax + t * vx;
    const cy = ay + t * vy;
    return { dist: Math.hypot(px - cx, py - cy), t };
}

function segmentDirection(a, b) {
    const dx = Math.sign(b.x - a.x);
    const dy = Math.sign(b.y - a.y);
    if (dx === 0 && dy === 0) return null;
    return { dx, dy };
}

function isValidSegment(a, b) {
    const dx = Math.abs(b.x - a.x);
    const dy = Math.abs(b.y - a.y);
    if (dx === 0 && dy === 0) return false;
    return dx === 0 || dy === 0 || dx === dy;
}

function orthoChoices(dx, dy) {
    if (dx !== 0 && dy === 0) return [[0, 1], [0, -1]];
    if (dx === 0 && dy !== 0) return [[1, 0], [-1, 0]];
    if (dx !== 0 && dy !== 0) return [[-dx, dy], [dx, -dy]];
    return null;
}

function pickOrthoSlide(delta, segDir) {
    const choices = orthoChoices(segDir.dx, segDir.dy);
    if (!choices) return null;
    let best = choices[0];
    let bestScore = -Infinity;
    for (const [ox, oy] of choices) {
        const score = delta.x * ox + delta.y * oy;
        if (Math.abs(score) > Math.abs(bestScore)) {
            bestScore = score;
            best = [ox, oy];
        }
    }
    const k = Math.round(delta.x * best[0] + delta.y * best[1]);
    return { k, ortho: best };
}

function projectOntoRay(origin, dir, target) {
    const { dx, dy } = dir;
    if (dx === 0 && dy !== 0) {
        return { x: origin.x, y: Math.round(target.y) };
    }
    if (dy === 0 && dx !== 0) {
        return { x: Math.round(target.x), y: origin.y };
    }
    const t = Math.round(((target.x - origin.x) / dx + (target.y - origin.y) / dy) / 2);
    return { x: origin.x + dx * t, y: origin.y + dy * t };
}

function applySegmentSlide(pts, baseline, segIndex, k, ortho) {
    const [ox, oy] = ortho;
    const a0 = baseline[segIndex];
    const b0 = baseline[segIndex + 1];
    const shiftedA = { x: a0.x + ox * k, y: a0.y + oy * k };
    const shiftedB = { x: b0.x + ox * k, y: b0.y + oy * k };

    if (segIndex > 0) {
        const prev = baseline[segIndex - 1];
        const dirPrev = segmentDirection(prev, a0);
        if (dirPrev) pts[segIndex] = projectOntoRay(prev, dirPrev, shiftedA);
        else pts[segIndex] = shiftedA;
    } else {
        pts[segIndex] = shiftedA;
    }

    if (segIndex + 1 < baseline.length - 1) {
        const next = baseline[segIndex + 2];
        const dirOut = segmentDirection(b0, next);
        if (dirOut) {
            pts[segIndex + 1] = projectOntoRay(next, { dx: -dirOut.dx, dy: -dirOut.dy }, shiftedB);
        } else {
            pts[segIndex + 1] = shiftedB;
        }
    } else {
        pts[segIndex + 1] = shiftedB;
    }
}

// --- serialization ---------------------------------------------------------

export function serializeWire(wire) {
    const pts = wirePoints(wire);
    return {
        points: pts.map((p) => ({ x: p.x, y: p.y })),
        isBus: !!wire.isBus,
        isGreedy: !!wire.isGreedy,
        isQFPPin: !!wire.isQFPPin,
        isRoute: !!wire.isRoute,
        noPads: !!wire.noPads,
        strokeScale: wire.strokeScale ?? null,
        manual: !!(wire.manual || wire.points),
    };
}

export function serializeWiresForSnapshot(wires) {
    return wires.filter((w) => {
        if (!params.showCircuits) return false;
        if (w.manual || w.points) return true;
        if (w.isRoute) return true;
        if (w.isBus && params.showBuses) return true;
        if (w.isQFPPin && params.showBuses) return true;
        if (w.isGreedy) {
            return params.showGreedyCircuits && w.cells.length > params.cutOffLength;
        }
        return w.cells.length > params.cutOffLength;
    }).map(serializeWire);
}

export function wireFromSerialized(rec, grid, gridWidth, gridHeight) {
    const pts = rec.points;
    const x = Math.max(0, Math.min(gridWidth - 1, Math.round(pts[0].x)));
    const y = Math.max(0, Math.min(gridHeight - 1, Math.round(pts[0].y)));
    const wire = new Wire(grid[x][y], grid, gridWidth, gridHeight);
    wire.cells = pts.map((p) => ({
        x: Math.max(0, Math.min(gridWidth - 1, Math.round(p.x))),
        y: Math.max(0, Math.min(gridHeight - 1, Math.round(p.y))),
    }));
    wire.points = pts.map((p) => ({ x: p.x, y: p.y }));
    wire.manual = rec.manual !== false;
    wire.isBus = !!rec.isBus;
    wire.isGreedy = !!rec.isGreedy;
    wire.isQFPPin = !!rec.isQFPPin;
    wire.isRoute = !!rec.isRoute;
    wire.noPads = !!rec.noPads;
    wire.strokeScale = rec.strokeScale;
    return wire;
}

export function importWiresFromOverlay(grid, gridWidth, gridHeight) {
    if (!wireOverlay?.length) return [];
    return wireOverlay.map((rec) => wireFromSerialized(rec, grid, gridWidth, gridHeight));
}

export function syncOverlayFromWires(wires) {
    wireOverlay = serializeWiresForSnapshot(wires);
}

function commitEdits() {
    syncOverlayFromWires(getWires());
}

// --- undo / redo -----------------------------------------------------------

export function pushWireUndo() {
    const snap = serializeWiresForSnapshot(getWires());
    undoStack.push(JSON.stringify(snap));
    if (undoStack.length > UNDO_MAX) undoStack.shift();
    redoStack = [];
}

function restoreWireSnapshot(json) {
    if (!editContext) return;
    const data = JSON.parse(json);
    const wires = data.map((rec) => wireFromSerialized(
        rec, editContext.grid, editContext.gridWidth, editContext.gridHeight,
    ));
    setWires(wires);
    syncOverlayFromWires(wires);
    selectedWire = null;
}

export function undoWireEdit() {
    if (!undoStack.length) return false;
    redoStack.push(JSON.stringify(serializeWiresForSnapshot(getWires())));
    restoreWireSnapshot(undoStack.pop());
    return true;
}

export function redoWireEdit() {
    if (!redoStack.length) return false;
    undoStack.push(JSON.stringify(serializeWiresForSnapshot(getWires())));
    restoreWireSnapshot(redoStack.pop());
    return true;
}

// --- hit testing -----------------------------------------------------------

function hitVertex(px, py) {
    const { cw, ch } = metrics();
    const r = vertexHitRadius(cw, ch);
    let best = null;
    let bestDist = r;
    for (const wire of getVisibleWires()) {
        const pts = wirePoints(wire);
        for (let i = 0; i < pts.length; i++) {
            const { px: vx, py: vy } = toPixel(pts[i], cw, ch);
            const d = Math.hypot(px - vx, py - vy);
            if (d <= bestDist) {
                bestDist = d;
                best = { wire, index: i };
            }
        }
    }
    return best;
}

function hitSegment(px, py) {
    const { cw, ch } = metrics();
    const r = segmentHitRadius(cw, ch);
    let best = null;
    let bestDist = r;
    for (const wire of getVisibleWires()) {
        const pts = wirePoints(wire);
        for (let i = 0; i < pts.length - 1; i++) {
            const a = toPixel(pts[i], cw, ch);
            const b = toPixel(pts[i + 1], cw, ch);
            const { dist, t } = pointToSegment(px, py, a.px, a.py, b.px, b.py);
            if (dist <= bestDist && t > 0.08 && t < 0.92) {
                bestDist = dist;
                best = { wire, segIndex: i };
            }
        }
    }
    return best;
}

function hitWire(px, py) {
    return hitVertex(px, py) || hitSegment(px, py);
}

// --- create / delete / disconnect ------------------------------------------

function createWireFromPoints(points) {
    if (!editContext || points.length < 2) return null;
    pushWireUndo();
    const { grid, gridWidth, gridHeight } = editContext;
    const wire = wireFromSerialized({ points, manual: true }, grid, gridWidth, gridHeight);
    appendWire(wire);
    commitEdits();
    selectedWire = wire;
    return wire;
}

function deleteWire(wire) {
    pushWireUndo();
    removeWire(wire);
    if (selectedWire === wire) clearSelectedWire();
    commitEdits();
}

function disconnectAtJoint(wire, index) {
    const pts = materialize(wire);
    if (index <= 0 || index >= pts.length - 1) return false;

    const left = pts.slice(0, index + 1).map((p) => ({ x: p.x, y: p.y }));
    const right = pts.slice(index).map((p) => ({ x: p.x, y: p.y }));
    if (left.length < 2 || right.length < 2) return false;

    pushWireUndo();
    const { grid, gridWidth, gridHeight } = editContext;
    removeWire(wire);
    appendWire(wireFromSerialized({ points: left, manual: true }, grid, gridWidth, gridHeight));
    const w2 = wireFromSerialized({ points: right, manual: true }, grid, gridWidth, gridHeight);
    appendWire(w2);
    selectedWire = w2;
    commitEdits();
    return true;
}

export function deleteSelectedSegment() {
    if (!selectedSegment) return false;
    const { wire, segIndex } = selectedSegment;
    const pts = materialize(wire);
    if (pts.length <= 2) {
        selectedSegment = null;
        deleteWire(wire);
        return true;
    }
    pushWireUndo();
    pts.splice(segIndex + 1, 1);
    if (pts.length < 2) {
        selectedSegment = null;
        removeWire(wire);
        if (selectedWire === wire) selectedWire = null;
    } else {
        selectedSegment = {
            wire,
            segIndex: Math.min(segIndex, pts.length - 2),
        };
    }
    commitEdits();
    return true;
}

export function deleteSelectedWire() {
    if (!selectedWire) return false;
    deleteWire(selectedWire);
    return true;
}

// --- pointer API -----------------------------------------------------------

export function editPointerDown(px, py, { altKey = false, shiftKey = false } = {}) {
    const { cw, ch } = metrics();

    if (altKey) {
        const hit = hitWire(px, py);
        if (hit?.wire) {
            deleteWire(hit.wire);
            return { kind: 'deleted' };
        }
        return null;
    }

    const v = hitVertex(px, py);
    if (v) {
        const pts = materialize(v.wire);
        selectedWire = v.wire;
        const isEnd = v.index === 0 || v.index === pts.length - 1;

        if (isEnd && shiftKey) {
            clearSelectedWire();
            initChainFromWire(v.wire, v.index);
            updateChainPreview(px, py);
            return { kind: 'chain' };
        }

        if (isEnd && pts.length >= 2) {
            const anchorIndex = v.index === 0 ? 1 : v.index - 1;
            return {
                kind: 'endpoint',
                wire: v.wire,
                freeIndex: v.index,
                anchorIndex,
                baseline: pts.map((p) => ({ x: p.x, y: p.y })),
                startGrid: snapToGrid(toGrid(px, py, cw, ch)),
            };
        }

        return { kind: 'joint', wire: v.wire, index: v.index };
    }

    const s = hitSegment(px, py);
    if (s) {
        const pts = materialize(s.wire);
        const a = pts[s.segIndex];
        const b = pts[s.segIndex + 1];
        if (!isValidSegment(a, b)) return null;
        selectSegment(s.wire, s.segIndex);
        return {
            kind: 'segment',
            wire: s.wire,
            segIndex: s.segIndex,
            baseline: pts.map((p) => ({ x: p.x, y: p.y })),
            startGrid: snapToGrid(toGrid(px, py, cw, ch)),
        };
    }

    if (!shiftKey) return null;

    clearSelectedWire();

    if (handleShiftWireClick(px, py)) return { kind: 'chain' };
    return null;
}

export function editPointerDrag(action, px, py) {
    if (!action) return;
    const { cw, ch } = metrics();
    const raw = toGrid(px, py, cw, ch);

    if (action.kind === 'endpoint' && action.baseline) {
        const anchor = action.baseline[action.anchorIndex];
        const dir = segmentDirection(anchor, action.baseline[action.freeIndex]);
        if (!dir) return;
        const snapped = snapTraceEndpoint(anchor, raw);
        let next = projectOntoRay(anchor, dir, snapped);
        if (next.x === anchor.x && next.y === anchor.y) {
            next = { x: anchor.x + dir.dx, y: anchor.y + dir.dy };
        }
        const free = action.wire.points[action.freeIndex];
        free.x = next.x;
        free.y = next.y;
        return;
    }

    if (action.kind !== 'segment' || !action.baseline) return;

    const pts = action.wire.points;
    const a0 = action.baseline[action.segIndex];
    const b0 = action.baseline[action.segIndex + 1];
    const segDir = segmentDirection(a0, b0);
    if (!segDir) return;

    const delta = { x: raw.x - action.startGrid.x, y: raw.y - action.startGrid.y };
    const slide = pickOrthoSlide(delta, segDir);
    if (!slide || slide.k === 0) {
        for (let i = 0; i < action.baseline.length; i++) {
            pts[i].x = action.baseline[i].x;
            pts[i].y = action.baseline[i].y;
        }
        return;
    }

    applySegmentSlide(pts, action.baseline, action.segIndex, slide.k, slide.ortho);
}

export function editPointerUp(action, px, py, moved) {
    if (!action || action.kind === 'deleted') return;

    const { cw, ch } = metrics();

    if (action.kind === 'chain') return;

    if (action.kind === 'endpoint' && moved) {
        if (!action.undoPushed) pushWireUndo();
        commitEdits();
        return;
    }

    if (action.kind === 'segment' && moved) {
        if (!action.undoPushed) pushWireUndo();
        commitEdits();
        return;
    }

    if (action.kind === 'joint' && !moved) {
        disconnectAtJoint(action.wire, action.index);
        return;
    }

}

export function drawSelectedSegment(ctx) {
    if (!selectedSegment) return;
    const { wire, segIndex } = selectedSegment;
    const pts = wirePoints(wire);
    if (segIndex < 0 || segIndex >= pts.length - 1) return;

    const { cw, ch } = metrics();
    const a = toPixel(pts[segIndex], cw, ch);
    const b = toPixel(pts[segIndex + 1], cw, ch);
    const lw = Math.max(2, params.cellSize * 0.42);

    ctx.beginPath();
    ctx.strokeStyle = 'rgba(120, 200, 255, 0.95)';
    ctx.lineWidth = lw;
    ctx.moveTo(a.px, a.py);
    ctx.lineTo(b.px, b.py);
    ctx.stroke();
}

export function drawWireHandles(ctx) {
    const { cw, ch } = metrics();
    const s = Math.max(5, Math.min(cw, ch) * 0.55);

    for (const wire of getVisibleWires()) {
        const pts = wirePoints(wire);
        for (let i = 0; i < pts.length; i++) {
            const { px, py } = toPixel(pts[i], cw, ch);
            const isEnd = i === 0 || i === pts.length - 1;
            const isInterior = !isEnd;
            const selected = wire === selectedWire;
            ctx.beginPath();
            ctx.rect(px - s / 2, py - s / 2, s, s);
            if (isInterior) {
                ctx.fillStyle = selected
                    ? 'rgba(255, 120, 120, 0.95)'
                    : 'rgba(255, 140, 140, 0.9)';
            } else {
                ctx.fillStyle = selected
                    ? 'rgba(120, 200, 255, 0.95)'
                    : 'rgba(255, 255, 255, 0.92)';
            }
            ctx.fill();
            ctx.lineWidth = 1;
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.55)';
            ctx.stroke();
        }
    }
}

export function drawChainPreview(ctx) {
    if (!wireChainDraft?.points.length || !wireChainDraft.previewEnd) return;
    const { cw, ch } = metrics();
    const pts = wireChainDraft.points;
    const preview = wireChainDraft.previewEnd;

    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255, 190, 40, 0.85)';
    ctx.lineWidth = Math.max(1, params.cellSize * 0.22);
    ctx.setLineDash([]);
    for (let i = 0; i < pts.length; i++) {
        const { px, py } = toPixel(pts[i], cw, ch);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
    }
    ctx.stroke();

    const last = pts[pts.length - 1];
    const a = toPixel(last, cw, ch);
    const b = toPixel(preview, cw, ch);
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255, 190, 40, 0.55)';
    ctx.lineWidth = Math.max(1, params.cellSize * 0.2);
    ctx.setLineDash([4, 4]);
    ctx.moveTo(a.px, a.py);
    ctx.lineTo(b.px, b.py);
    ctx.stroke();
    ctx.setLineDash([]);
}
