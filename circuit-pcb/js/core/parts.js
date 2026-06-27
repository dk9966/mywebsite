// Component archetypes. Every maker returns a spec with a cell footprint
// (cols x rows), pin anchors in cell coordinates, and draw primitives in local
// pixels (origin = footprint top-left). Renderers never special-case kinds --
// they just replay primitives, which keeps SVG and canvas identical.
//
// Pin anchors sit one cell OUTSIDE the footprint; the drawn tab spans from the
// body edge to the anchor cell center so a trace starting there fuses with it.
//
// Everything is hollow for the thin silkscreen read: bodies fill 'bg' (to mask
// the black board) and stroke 'fg'. Color tokens: 'fg', 'bg'.

import { UP, RIGHT, DOWN, LEFT } from './dirs.js';

const rect = (x, y, w, h, o = {}) => ({ t: 'rect', x, y, w, h, ...o });
const circle = (cx, cy, r, o = {}) => ({ t: 'circle', cx, cy, r, ...o });
const line = (x1, y1, x2, y2, sw) => ({ t: 'line', x1, y1, x2, y2, sw });
const poly = (pts, o = {}) => ({ t: 'poly', pts, ...o });

const HOLLOW = { fill: 'bg', stroke: 'fg', sw: 1.4 };
const TAB = 1.3;

function pinOffsets(span, { pitch, inset }) {
    const offs = [];
    for (let c = inset; c <= span - 1 - inset; c += pitch) offs.push(c);
    return offs;
}

function octagonPts(cx, cy, r) {
    const pts = [];
    for (let k = 0; k < 8; k++) {
        const a = Math.PI / 8 + (k * Math.PI) / 4;
        pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return pts;
}

// === Pin-row chips (bus-routable) ===========================================

export function makeQfp(rng, config) {
    const cell = config.grid.cell;
    const body = rng.int(...config.place.qfp.body);
    const cols = body + 2;
    const rows = cols;
    const b = { x: cell, y: cell, w: body * cell, h: body * cell };
    const pins = [];
    const prims = [];

    for (const c of pinOffsets(cols, config.pins)) {
        const px = (c + 0.5) * cell;
        pins.push({ c, r: -1, dir: UP, side: 'top' });
        pins.push({ c, r: rows, dir: DOWN, side: 'bottom' });
        prims.push(line(px, b.y, px, -0.5 * cell, TAB));
        prims.push(line(px, b.y + b.h, px, (rows + 0.5) * cell, TAB));
    }
    for (const r of pinOffsets(rows, config.pins)) {
        const py = (r + 0.5) * cell;
        pins.push({ c: -1, r, dir: LEFT, side: 'left' });
        pins.push({ c: cols, r, dir: RIGHT, side: 'right' });
        prims.push(line(b.x, py, -0.5 * cell, py, TAB));
        prims.push(line(b.x + b.w, py, (cols + 0.5) * cell, py, TAB));
    }

    prims.push(rect(b.x, b.y, b.w, b.h, HOLLOW));
    prims.push(rect(b.x + 5, b.y + 5, b.w - 10, b.h - 10, { stroke: 'fg', sw: 1 }));
    prims.push(circle(b.x + 9, b.y + 9, 2.2, { stroke: 'fg', sw: 1 })); // pin-1 marker

    return { kind: 'qfp', cols, rows, pinRows: true, pins, prims };
}

export function makeSoic(rng, config) {
    const cell = config.grid.cell;
    const bodyW = rng.int(...config.place.soic.bodyW);
    const bodyH = rng.int(...config.place.soic.bodyH);
    const cols = bodyW + 2;
    const rows = bodyH + 2;
    const b = { x: cell, y: cell, w: bodyW * cell, h: bodyH * cell };
    const pins = [];
    const prims = [];

    for (const c of pinOffsets(cols, config.pins)) {
        const px = (c + 0.5) * cell;
        pins.push({ c, r: -1, dir: UP, side: 'top' });
        pins.push({ c, r: rows, dir: DOWN, side: 'bottom' });
        prims.push(line(px, b.y, px, -0.5 * cell, TAB));
        prims.push(line(px, b.y + b.h, px, (rows + 0.5) * cell, TAB));
    }

    prims.push(rect(b.x, b.y, b.w, b.h, HOLLOW));
    prims.push(line(b.x + 4, b.y + 5, b.x + b.w - 4, b.y + 5, 1));

    const spec = { kind: 'soic', cols, rows, pinRows: true, pins, prims };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// === Dumbbell passives (single + banks) =====================================

// One horizontal dumbbell: pads at both ends, a link between, tabs reaching the
// left/right pin anchors. Footprint 6x3 cells (cell=6 -> 36x18 px).
function passiveSpec() {
    return {
        kind: 'passive',
        cols: 6,
        rows: 3,
        pins: [
            { c: -1, r: 1, dir: LEFT, side: 'left' },
            { c: 6, r: 1, dir: RIGHT, side: 'right' },
        ],
        prims: [
            line(6, 9, -3, 9, TAB),
            line(30, 9, 39, 9, TAB),
            rect(6, 4, 7, 10, HOLLOW),
            rect(23, 4, 7, 10, HOLLOW),
            line(13, 9, 23, 9, 1.2),
        ],
    };
}

export function makePassive(rng) {
    const spec = passiveSpec();
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// A comb of dumbbells: N units stacked across their short axis. This is the
// reference's hallmark texture -- tidy rows and columns of identical passives.
export function makePassiveBank(rng, config) {
    const n = rng.int(...config.place.passiveBank.size);
    const pitch = config.place.passiveBank.pitch;
    const vertical = rng.chance(0.5);
    const unit = vertical ? transposeSpec(passiveSpec()) : passiveSpec();
    const specs = [];
    for (let i = 0; i < n; i++) {
        const [dc, dr] = vertical ? [i * pitch, 0] : [0, i * pitch];
        specs.push(shiftSpec(unit, dc, dr, config));
    }
    return mergeSpecs('passiveBank', specs);
}

// === Round through-holes ====================================================

// Single annular pad with one tab -- a connectable test point / via pad.
export function makeHolePad(rng) {
    const spec = {
        kind: 'holePad',
        cols: 3,
        rows: 3,
        pins: [{ c: 3, r: 1, dir: RIGHT, side: 'right' }],
        prims: [
            line(15, 9, 21, 9, TAB),
            circle(9, 9, 6.5, HOLLOW),
            circle(9, 9, 3, { stroke: 'fg', sw: 1 }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// A block of plain mounting holes (2x2, 1x2, or 2x1) -- decorative, no pins.
export function makeHoleCluster(rng) {
    const [cw, ch] = rng.pick([[2, 2], [1, 2], [2, 1]]);
    const r = rng.range(8, 11);
    const step = r * 2 + 8;
    const pad = 6;
    const prims = [];
    for (let i = 0; i < cw; i++) {
        for (let j = 0; j < ch; j++) {
            const cx = pad + r + i * step;
            const cy = pad + r + j * step;
            prims.push(circle(cx, cy, r, HOLLOW));
            prims.push(circle(cx, cy, r * 0.45, { stroke: 'fg', sw: 1 }));
        }
    }
    const cell = 6;
    const wPx = pad * 2 + (cw - 1) * step + r * 2;
    const hPx = pad * 2 + (ch - 1) * step + r * 2;
    return {
        kind: 'holeCluster',
        cols: Math.ceil(wPx / cell),
        rows: Math.ceil(hPx / cell),
        pins: [],
        prims,
    };
}

// === Octagonal pads =========================================================

// Big octagonal pad/connector with a tab on each side.
export function makeOctagon(rng, config) {
    const cell = config.grid.cell;
    const R = rng.int(6, 8);
    const cols = 2 * R + 2;
    const rows = cols;
    const c = ((R + 1) * cell);
    const r = R * cell;
    const pins = [
        { c: -1, r: R + 1, dir: LEFT, side: 'left' },
        { c: cols, r: R + 1, dir: RIGHT, side: 'right' },
        { c: R + 1, r: -1, dir: UP, side: 'top' },
        { c: R + 1, r: rows, dir: DOWN, side: 'bottom' },
    ];
    const prims = [
        line(c - r, c, -0.5 * cell, c, TAB),
        line(c + r, c, (cols + 0.5) * cell, c, TAB),
        line(c, c - r, c, -0.5 * cell, TAB),
        line(c, c + r, c, (rows + 0.5) * cell, TAB),
        poly(octagonPts(c, c, r), HOLLOW),
        poly(octagonPts(c, c, r * 0.62), { stroke: 'fg', sw: 1 }),
    ];
    return { kind: 'octagon', cols, rows, pins, prims };
}

// Small octagonal solder pad with one tab -- a connectable small part.
export function makeOctPad(rng) {
    const spec = {
        kind: 'octPad',
        cols: 3,
        rows: 3,
        pins: [{ c: 3, r: 1, dir: RIGHT, side: 'right' }],
        prims: [
            line(15, 9, 21, 9, TAB),
            poly(octagonPts(9, 9, 7), HOLLOW),
            circle(9, 9, 2, { stroke: 'fg', sw: 1 }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// Square solder pad with one tab.
export function makePad(rng) {
    const spec = {
        kind: 'pad',
        cols: 3,
        rows: 3,
        pins: [{ c: 3, r: 1, dir: RIGHT, side: 'right' }],
        prims: [
            line(14, 9, 21, 9, TAB),
            rect(3, 3, 12, 12, { rx: 2, ...HOLLOW }),
            circle(9, 9, 2, { stroke: 'fg', sw: 1 }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// === Pill connector (rounded-rect tube) =====================================

export function makePill(rng, config) {
    const cell = config.grid.cell;
    const len = rng.int(8, 13);
    const cols = len + 2;
    const rows = 4;
    const w = len * cell;
    const h = 2 * cell;
    const x = cell;
    const y = cell;
    const cy = y + h / 2;
    const prims = [
        line(x, cy, -0.5 * cell, cy, TAB),
        line(x + w, cy, (cols + 0.5) * cell, cy, TAB),
        rect(x, y, w, h, { rx: h / 2, ...HOLLOW }),
        rect(x + 6, y + 3, w - 12, h - 6, { rx: (h - 6) / 2, stroke: 'fg', sw: 1 }),
    ];
    const spec = {
        kind: 'pill',
        cols,
        rows,
        pins: [
            { c: -1, r: 1, dir: LEFT, side: 'left' },
            { c: cols, r: 1, dir: RIGHT, side: 'right' },
        ],
        prims,
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// === Pin header / edge connector ============================================

export function makeHeader(rng) {
    const n = rng.int(5, 8);
    const step = 12;
    const w = 10 + (n - 1) * step + 10;
    const prims = [rect(2, 2, w - 4, 22, { ...HOLLOW, sw: 1.3 })];
    for (let i = 0; i < n; i++) {
        prims.push(circle(10 + i * step, 13, 3.4, { stroke: 'fg', sw: 1.2 }));
    }
    const cell = 6;
    const cols = Math.ceil(w / cell);
    const rows = 5;
    return {
        kind: 'header',
        cols,
        rows,
        pins: [
            { c: 2, r: rows, dir: DOWN, side: 'bottom' },
            { c: cols - 2, r: rows, dir: DOWN, side: 'bottom' },
        ],
        prims,
    };
}

// === Ribbon-cable bundle ====================================================

// A framed block packed with parallel lines -- a flex/ribbon cable stub.
// Decorative (no pins); reads as a striped rectangle like the reference.
export function makeRibbon(rng) {
    const cell = 6;
    const vertical = rng.chance(0.5);
    const lines = rng.int(8, 14);
    const pitch = 5;
    const span = rng.int(60, 120); // length of each strand, px
    const thick = (lines - 1) * pitch + 8;
    const wPx = vertical ? thick : span;
    const hPx = vertical ? span : thick;
    const prims = [rect(0, 0, wPx, hPx, { stroke: 'fg', sw: 1.2 })];
    for (let i = 0; i < lines; i++) {
        const o = 4 + i * pitch;
        if (vertical) prims.push(line(o, 4, o, hPx - 4, 1.3));
        else prims.push(line(4, o, wPx - 4, o, 1.3));
    }
    return {
        kind: 'ribbon',
        cols: Math.ceil(wPx / cell),
        rows: Math.ceil(hPx / cell),
        pins: [],
        prims,
    };
}

export const FILL_MAKERS = {
    passiveBank: makePassiveBank,
    passive: makePassive,
    pad: makePad,
    holePad: makeHolePad,
    octPad: makeOctPad,
};

// === Spec transforms ========================================================

// Shift a spec by whole cells, growing the bounding footprint from the origin.
function shiftSpec(spec, dCols, dRows, config) {
    const cell = config.grid.cell;
    const dx = dCols * cell;
    const dy = dRows * cell;
    return {
        ...spec,
        cols: spec.cols + dCols,
        rows: spec.rows + dRows,
        pins: spec.pins.map((p) => ({ ...p, c: p.c + dCols, r: p.r + dRows })),
        prims: spec.prims.map((p) => translatePrim(p, dx, dy)),
    };
}

// Union of pre-shifted specs into one part.
function mergeSpecs(kind, specs) {
    return {
        kind,
        cols: Math.max(...specs.map((s) => s.cols)),
        rows: Math.max(...specs.map((s) => s.rows)),
        pins: specs.flatMap((s) => s.pins),
        prims: specs.flatMap((s) => s.prims),
    };
}

// Swap x/y everywhere, turning a horizontal part into a vertical one.
function transposeSpec(spec) {
    return {
        ...spec,
        cols: spec.rows,
        rows: spec.cols,
        pins: spec.pins.map((p) => ({
            c: p.r,
            r: p.c,
            dir: transposeDir(p.dir),
            side: transposeSide(p.side),
        })),
        prims: spec.prims.map(transposePrim),
    };
}

function transposeDir(dir) {
    const map = { [UP]: LEFT, [LEFT]: UP, [DOWN]: RIGHT, [RIGHT]: DOWN };
    return map[dir] ?? dir;
}

function transposeSide(side) {
    const map = { top: 'left', left: 'top', bottom: 'right', right: 'bottom' };
    return map[side] ?? side;
}

function transposePrim(p) {
    switch (p.t) {
        case 'rect': return { ...p, x: p.y, y: p.x, w: p.h, h: p.w };
        case 'circle': return { ...p, cx: p.cy, cy: p.cx };
        case 'line': return { ...p, x1: p.y1, y1: p.x1, x2: p.y2, y2: p.x2 };
        case 'poly': return { ...p, pts: p.pts.map(([x, y]) => [y, x]) };
        default: return p;
    }
}

function translatePrim(p, dx, dy) {
    switch (p.t) {
        case 'rect': return { ...p, x: p.x + dx, y: p.y + dy };
        case 'circle': return { ...p, cx: p.cx + dx, cy: p.cy + dy };
        case 'line': return { ...p, x1: p.x1 + dx, y1: p.y1 + dy, x2: p.x2 + dx, y2: p.y2 + dy };
        case 'poly': return { ...p, pts: p.pts.map(([x, y]) => [x + dx, y + dy]) };
        default: return p;
    }
}
