// Component archetypes: every maker returns a spec with a cell footprint
// (cols x rows), pin anchors in cell coordinates, and draw primitives in
// local pixels (origin = footprint top-left). Renderers never special-case
// kinds -- they just replay primitives, which keeps SVG and canvas identical.
//
// Pin anchors sit one cell OUTSIDE the footprint; the drawn tab spans from the
// body edge to the anchor cell center so a trace starting there fuses with it.
//
// Primitive color tokens: 'fg', 'bg', 'accent' (resolved per style preset).

import { UP, RIGHT, DOWN, LEFT } from './dirs.js';

const rect = (x, y, w, h, o = {}) => ({ t: 'rect', x, y, w, h, ...o });
const circle = (cx, cy, r, o = {}) => ({ t: 'circle', cx, cy, r, ...o });
const line = (x1, y1, x2, y2, sw) => ({ t: 'line', x1, y1, x2, y2, sw });
const poly = (pts, o = {}) => ({ t: 'poly', pts, ...o });

function pinOffsets(span, { pitch, inset }) {
    const offs = [];
    for (let c = inset; c <= span - 1 - inset; c += pitch) offs.push(c);
    return offs;
}

function regularPolygon(cx, cy, r, n, startAngle) {
    const pts = [];
    for (let k = 0; k < n; k++) {
        const a = startAngle + (k * 2 * Math.PI) / n;
        pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return pts;
}

// === Chips (full pin rows, bus-routable) ====================================

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
        prims.push(line(px, b.y, px, -0.5 * cell, 2.2));
        prims.push(line(px, b.y + b.h, px, (rows + 0.5) * cell, 2.2));
    }
    for (const r of pinOffsets(rows, config.pins)) {
        const py = (r + 0.5) * cell;
        pins.push({ c: -1, r, dir: LEFT, side: 'left' });
        pins.push({ c: cols, r, dir: RIGHT, side: 'right' });
        prims.push(line(b.x, py, -0.5 * cell, py, 2.2));
        prims.push(line(b.x + b.w, py, (cols + 0.5) * cell, py, 2.2));
    }

    prims.push(rect(b.x, b.y, b.w, b.h, { fill: 'bg', stroke: 'accent', sw: 2 }));
    prims.push(rect(b.x + 5, b.y + 5, b.w - 10, b.h - 10, { stroke: 'fg', sw: 1 }));
    prims.push(circle(b.x + 10, b.y + 10, 2.6, { fill: 'fg' }));

    return { kind: 'qfp', cols, rows, pinRows: true, accent: 'green', pins, prims };
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
        prims.push(line(px, b.y, px, -0.5 * cell, 2.2));
        prims.push(line(px, b.y + b.h, px, (rows + 0.5) * cell, 2.2));
    }

    prims.push(rect(b.x, b.y, b.w, b.h, { fill: 'bg', stroke: 'accent', sw: 2 }));
    prims.push(line(b.x + 4, b.y + 5, b.x + b.w - 4, b.y + 5, 1));

    const spec = { kind: 'soic', cols, rows, pinRows: true, accent: 'pink', pins, prims };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// === Connected small parts ==================================================

export function makePassive(rng, config) {
    const spec = passiveSpec(config, 0);
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

export function makePassivePair(rng, config) {
    const a = passiveSpec(config, 0);
    const b = passiveSpec(config, 3);
    const spec = {
        kind: 'passivePair',
        cols: 5,
        rows: 6,
        pins: [...a.pins, ...b.pins],
        prims: [...a.prims, ...b.prims],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

// One passive body occupying footprint rows rowOff..rowOff+2 of a 5-wide box.
function passiveSpec(config, rowOff) {
    const y0 = rowOff * config.grid.cell;
    const cy = y0 + 9;
    return {
        kind: 'passive',
        cols: 5,
        rows: rowOff + 3,
        pins: [
            { c: -1, r: rowOff + 1, dir: LEFT, side: 'left' },
            { c: 5, r: rowOff + 1, dir: RIGHT, side: 'right' },
        ],
        prims: [
            line(4, cy, -3, cy, 2),
            line(26, cy, 33, cy, 2),
            rect(4, y0 + 3, 22, 12, { fill: 'bg', stroke: 'fg', sw: 1.6 }),
            rect(4, y0 + 3, 5, 12, { fill: 'fg' }),
            rect(21, y0 + 3, 5, 12, { fill: 'fg' }),
        ],
    };
}

export function makeSmd(rng, config) {
    const spec = {
        kind: 'smd',
        cols: 6,
        rows: 3,
        pins: [
            { c: -1, r: 1, dir: LEFT, side: 'left' },
            { c: 6, r: 1, dir: RIGHT, side: 'right' },
        ],
        prims: [
            line(4, 9, -3, 9, 2),
            line(32, 9, 39, 9, 2),
            rect(4, 2, 28, 14, { fill: 'bg', stroke: 'fg', sw: 1.8 }),
            rect(4, 2, 6, 14, { fill: 'fg' }),
            rect(26, 2, 6, 14, { fill: 'fg' }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

export function makeConnector() {
    return {
        kind: 'connector',
        cols: 12,
        rows: 5,
        pins: [
            { c: 3, r: 5, dir: DOWN, side: 'bottom' },
            { c: 8, r: 5, dir: DOWN, side: 'bottom' },
        ],
        prims: [
            line(21, 28, 21, 33, 2.2),
            line(51, 28, 51, 33, 2.2),
            rect(2, 2, 68, 26, { fill: 'bg', stroke: 'fg', sw: 2 }),
            rect(10, 14, 52, 10, { fill: 'fg' }),
        ],
    };
}

// === Round / odd-shaped connected parts =====================================

export function makeCapRound(rng) {
    const spec = {
        kind: 'capRound',
        cols: 5,
        rows: 5,
        pins: [{ c: 5, r: 2, dir: RIGHT, side: 'right' }],
        prims: [
            line(26, 15, 33, 15, 2),
            circle(15, 15, 12, { fill: 'bg', stroke: 'fg', sw: 2 }),
            circle(15, 15, 4.5, { stroke: 'fg', sw: 1.2 }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

export function makeLonePad(rng) {
    const spec = {
        kind: 'lonePad',
        cols: 3,
        rows: 3,
        pins: [{ c: 3, r: 1, dir: RIGHT, side: 'right' }],
        prims: [
            line(14, 9, 21, 9, 2),
            rect(3, 3, 12, 12, { rx: 3, fill: 'bg', stroke: 'fg', sw: 1.6 }),
            circle(9, 9, 2, { fill: 'fg' }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

export function makeDrum(rng) {
    const spec = {
        kind: 'drum',
        cols: 6,
        rows: 6,
        pins: [
            { c: -1, r: 2, dir: LEFT, side: 'left' },
            { c: 6, r: 2, dir: RIGHT, side: 'right' },
        ],
        prims: [
            line(6, 15, -3, 15, 2),
            line(30, 15, 39, 15, 2),
            poly(regularPolygon(18, 18, 14, 8, Math.PI / 8), { fill: 'bg', stroke: 'fg', sw: 2 }),
            circle(18, 18, 2.5, { fill: 'fg' }),
        ],
    };
    return rng.chance(0.5) ? transposeSpec(spec) : spec;
}

export function makeHeatsink() {
    const prims = [
        line(86, 21, 93, 21, 2.2),
        line(86, 39, 93, 39, 2.2),
        rect(2, 2, 86, 56, { fill: 'bg', stroke: 'fg', sw: 2 }),
    ];
    for (let x = 9; x <= 81; x += 7) prims.push(line(x, 7, x, 53, 2.2));
    return {
        kind: 'heatsink',
        cols: 15,
        rows: 10,
        pins: [
            { c: 15, r: 3, dir: RIGHT, side: 'right' },
            { c: 15, r: 6, dir: RIGHT, side: 'right' },
        ],
        prims,
    };
}

export function makeHeader() {
    const prims = [
        line(15, 22, 15, 27, 2.2),
        line(75, 22, 75, 27, 2.2),
        rect(2, 2, 86, 20, { fill: 'bg', stroke: 'fg', sw: 1.8 }),
    ];
    for (let x = 10; x <= 78; x += 12) {
        prims.push(circle(x, 12, 3.6, { fill: 'bg', stroke: 'fg', sw: 1.4 }));
    }
    return {
        kind: 'header',
        cols: 15,
        rows: 4,
        pins: [
            { c: 2, r: 4, dir: DOWN, side: 'bottom' },
            { c: 12, r: 4, dir: DOWN, side: 'bottom' },
        ],
        prims,
    };
}

export const SMALL_MAKERS = {
    passive: makePassive,
    passivePair: makePassivePair,
    smd: makeSmd,
    capRound: makeCapRound,
    lonePad: makeLonePad,
    drum: makeDrum,
};

// === Orientation ============================================================

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
