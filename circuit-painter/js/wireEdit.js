// Manual wire editing: draggable joints + click-to-slant.
//
// Plain-English: the auto-router gives you a polyline per wire. This module
// lets you grab the corners and move them, and click the trace to bevel a
// corner into a 45 degree slant -- so you can hand-tweak a board the generator
// got *almost* right instead of re-rolling the seed.
//
// How it hangs together:
//   - Every wire keeps a dense `cells` list. The first time you touch a wire we
//     "materialize" a sparse corner polyline onto `wire.points` (just the bends
//     + endpoints). From then on `wire.points` is the source of truth and the
//     renderer draws from it (see wire.js render()).
//   - All hit-testing happens in pixel space so handles line up with what you
//     see; edits are stored in grid coordinates and snapped to whole cells so
//     the result keeps the circuit's on-grid look.
//
// Interactions (driven by mouse.js):
//   - Drag a joint handle  -> move that joint (snaps to the grid).
//   - Click a corner handle -> bevel it into a 45 degree slant.
//   - Click the trace body  -> bevel the nearest corner, or (far from any
//                              corner) drop a new joint you can then drag.

import { params } from './params.js';
import { getCanvas, getGridDimensions, getVisibleWires } from './canvas.js';

// Default chamfer depth, in cells, when beveling a corner to 45 degrees.
const BEVEL_CELLS = 4;

// --- coordinate helpers -----------------------------------------------------

// Cell (cw, ch) sizes in pixels. Mirrors the mapping in wire.js / obstacles.js:
// a wire point at grid coord g sits at pixel (g + 0.5) * cell.
function metrics() {
    const canvas = getCanvas();
    const { w: gw, h: gh } = getGridDimensions();
    const cw = (params.cellSize * (1 + canvas.width / params.cellSize)) / gw;
    const ch = (params.cellSize * (1 + canvas.height / params.cellSize)) / gh;
    return { cw, ch };
}

function toPixel(p, cw, ch) {
    return { px: (p.x + 0.5) * cw, py: (p.y + 0.5) * ch };
}

function toGrid(px, py, cw, ch) {
    return { x: px / cw - 0.5, y: py / ch - 0.5 };
}

function snapToGrid(p) {
    return { x: Math.round(p.x), y: Math.round(p.y) };
}

// Pixel radius within which a click counts as "on" a joint handle.
function vertexHitRadius(cw, ch) {
    return Math.max(9, Math.min(cw, ch) * 0.75);
}

// Pixel distance within which a click counts as "on" the trace body.
function segmentHitRadius(cw, ch) {
    return Math.max(6, Math.min(cw, ch) * 0.6);
}

// --- polyline helpers -------------------------------------------------------

// Collapse a dense cell run into just its corners (+ both endpoints). A cell is
// a corner when the step direction into it differs from the step out of it.
function cornersFromCells(cells) {
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

// The corner polyline used for both display and hit-testing. Deterministic, so
// an index from a pre-materialize hit-test stays valid after materialize().
function wirePoints(wire) {
    return wire.points || cornersFromCells(wire.cells);
}

// Promote the wire to an editable polyline so mutations stick and the renderer
// switches to it. No-op once materialized.
function materialize(wire) {
    if (!wire.points) wire.points = wirePoints(wire);
    return wire.points;
}

// Shortest pixel distance from point P to segment AB, plus the clamped
// projection parameter t in [0, 1].
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

// --- hit testing ------------------------------------------------------------

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
            if (dist <= bestDist) {
                bestDist = dist;
                best = { wire, segIndex: i, t };
            }
        }
    }
    return best;
}

// --- edits ------------------------------------------------------------------

// Replace corner `index` with two points pulled back along each leg, so the
// connecting segment is a 45 degree slant. Returns true if it beveled.
function bevelCorner(wire, index) {
    const pts = materialize(wire);
    if (index <= 0 || index >= pts.length - 1) return false;

    const b = pts[index];
    const a = pts[index - 1];
    const c = pts[index + 1];
    const legA = Math.hypot(a.x - b.x, a.y - b.y);
    const legC = Math.hypot(c.x - b.x, c.y - b.y);
    // Need room on both legs, otherwise the chamfer would swallow a neighbor.
    if (Math.min(legA, legC) < 2) return false;

    const depth = Math.min(BEVEL_CELLS, legA - 1, legC - 1);
    const p1 = snapToGrid({
        x: b.x + ((a.x - b.x) / legA) * depth,
        y: b.y + ((a.y - b.y) / legA) * depth,
    });
    const p2 = snapToGrid({
        x: b.x + ((c.x - b.x) / legC) * depth,
        y: b.y + ((c.y - b.y) / legC) * depth,
    });
    pts.splice(index, 1, p1, p2);
    return true;
}

// --- public API (called by mouse.js) ---------------------------------------

// A vertex grab starts a drag; a segment hit is recorded but only acts on
// release (so we can tell a click from a stray drag). Returns null when the
// pointer missed every editable wire.
export function editPointerDown(px, py) {
    const v = hitVertex(px, py);
    if (v) {
        materialize(v.wire);
        return { kind: 'vertex', wire: v.wire, index: v.index };
    }
    const s = hitSegment(px, py);
    if (s) return { kind: 'segment', wire: s.wire, segIndex: s.segIndex };
    return null;
}

// Live-drag a joint to the pointer, snapped to the grid. No-op for segments.
export function editPointerDrag(action, px, py) {
    if (!action || action.kind !== 'vertex') return;
    const { cw, ch } = metrics();
    const g = snapToGrid(toGrid(px, py, cw, ch));
    action.wire.points[action.index] = g;
}

// Release. `moved` is true if the pointer dragged since press -- a drag has
// already been applied live, so we only act on genuine clicks.
export function editPointerUp(action, px, py, moved) {
    if (!action || moved) return;

    if (action.kind === 'vertex') {
        bevelCorner(action.wire, action.index);
        return;
    }

    // Segment click: bevel the nearer interior corner of the clicked segment;
    // if neither is close (a long straight run), drop a new draggable joint at
    // the click instead.
    const wire = action.wire;
    const pts = materialize(wire);
    const { cw, ch } = metrics();

    const candidates = [];
    if (action.segIndex > 0) candidates.push(action.segIndex);
    if (action.segIndex + 1 < pts.length - 1) candidates.push(action.segIndex + 1);

    let corner = null;
    let cornerDist = Infinity;
    for (const ci of candidates) {
        const { px: cx, py: cy } = toPixel(pts[ci], cw, ch);
        const d = Math.hypot(px - cx, py - cy);
        if (d < cornerDist) {
            cornerDist = d;
            corner = ci;
        }
    }

    const cornerZone = Math.max(cw, ch) * (BEVEL_CELLS - 1);
    if (corner !== null && cornerDist <= cornerZone && bevelCorner(wire, corner)) return;

    const g = snapToGrid(toGrid(px, py, cw, ch));
    pts.splice(action.segIndex + 1, 0, g);
}

// Overlay drawn on top of the board (canvas.js) while edit mode is on. Bends
// are amber squares, endpoints white, so a glance shows what's grabbable.
export function drawWireHandles(ctx) {
    const { cw, ch } = metrics();
    const s = Math.max(5, Math.min(cw, ch) * 0.55);

    for (const wire of getVisibleWires()) {
        const pts = wirePoints(wire);
        for (let i = 0; i < pts.length; i++) {
            const { px, py } = toPixel(pts[i], cw, ch);
            const isEnd = i === 0 || i === pts.length - 1;
            ctx.beginPath();
            ctx.rect(px - s / 2, py - s / 2, s, s);
            ctx.fillStyle = isEnd ? 'rgba(255, 255, 255, 0.92)' : 'rgba(255, 190, 40, 0.95)';
            ctx.fill();
            ctx.lineWidth = 1;
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.55)';
            ctx.stroke();
        }
    }
}
