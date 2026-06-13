// Component kinds: the top-view shapes the palette offers, the canvas draws,
// and obstacles are tagged with. Footprints (w/h in grid cells) preserve the
// relative proportions measured from the reference board
// (plans/claude/files/component_reference.glb), scaled up so each shape reads
// clearly on the routing grid.
//
// `pins` lists chip edges that emit full pin rows. `auxPins` gives non-chip
// meshes a small aesthetic pair of connection tabs so buses can route into them
// without pretending they are dense IC packages.

import { params } from './params.js';

// Order here is the palette order, left to right.
// refW/refH: top-view footprint in GLB units, averaged from
// plans/claude/files/component_reference.glb (r0–r7 instance bboxes).
const PALETTE = [
    { id: 'qfp', label: 'QFP', shape: 'chip', w: 14, h: 14, refW: 2.3495, refH: 2.3495, pins: ['top', 'right', 'bottom', 'left'] },
    { id: 'soic', label: 'SOIC', shape: 'chip', w: 12, h: 6, refW: 1.736, refH: 0.8265, pins: ['top', 'bottom'] },
    { id: 'capacitor', label: 'Cap', shape: 'cap', w: 6, h: 6, refW: 0.6224, refH: 0.6046, pins: null, auxPins: { side: 'right', count: 2 } },
    { id: 'heatsink', label: 'Heatsink', shape: 'heatsink', w: 12, h: 9, refW: 1.8966, refH: 1.4363, pins: null, auxPins: { side: 'right', count: 2 } },
    { id: 'drum', label: 'Drum', shape: 'octagon', w: 8, h: 8, refW: 1.1154, refH: 1.0916, pins: null, auxPins: { side: 'right', count: 2 } },
    { id: 'header', label: 'Header', shape: 'header', w: 11, h: 4, refW: 1.7131, refH: 0.4843, pins: null, auxPins: { side: 'bottom', count: 2 } },
    { id: 'connector', label: 'Connector', shape: 'connector', w: 12, h: 5, refW: 1.7998, refH: 0.705, pins: null, auxPins: { side: 'top', count: 2 } },
    { id: 'smd', label: 'SMD', shape: 'smd', w: 6, h: 4, refW: 0.8152, refH: 0.4932, pins: null, auxPins: { side: 'right', count: 2 } },
    { id: 'pad', label: 'Pad', shape: 'pad', w: 3, h: 3, refW: 0.36, refH: 0.36, pins: null, auxPins: { side: 'right', count: 1 } },
    { id: 'via', label: 'Via', shape: 'via', w: 3, h: 3, refW: 0.36, refH: 0.36, pins: null, auxPins: { side: 'right', count: 1 } },
];

// `block` is the legacy seed-generated rectangle. It is not in the palette but
// still needs a kind entry so drawing and serialization round-trip cleanly.
const BLOCK = { id: 'block', label: 'Block', shape: 'block', w: 14, h: 14, pins: null };

const ALL = [...PALETTE, BLOCK];
const BY_ID = new Map(ALL.map((k) => [k.id, k]));

export const PALETTE_KINDS = PALETTE.map((k) => k.id);

// Largest footprint dimension across palette kinds (cells, at scale 1). Used by
// obstacle generation to leave enough room near the board edges.
export const MAX_KIND_DIM = Math.max(...PALETTE.map((k) => Math.max(k.w, k.h)));

// Reference dimension the obstacleSize slider maps onto: a scale of 1 yields
// each kind's native footprint (the QFP is 14x14, matching the slider default).
export const KIND_REFERENCE_DIM = 14;

export function listPaletteKinds() {
    return PALETTE.slice();
}

// Pin overhang beyond the GLB body bbox (half-cell in game units, converted
// back to GLB units via the kind's grid footprint).
function pinMarginGlb(kind) {
    if (!kind.pins?.length && !kind.auxPins) return 0;
    return 0.5 * Math.min(kind.refW / kind.w, kind.refH / kind.h);
}

// Pixel size for reference sheets: one shared scale so relative sizes match
// the GLB board (QFP largest, cap/SMD smallest, etc.).
export function referenceFootprintPx(kind, pxPerUnit) {
    const pin = pinMarginGlb(kind);
    const drawW = (kind.refW + pin * 2) * pxPerUnit;
    const drawH = (kind.refH + pin * 2) * pxPerUnit;
    return {
        drawW,
        drawH,
        cols: kind.w,
        rows: kind.h,
        cw: (kind.refW * pxPerUnit) / kind.w,
        ch: (kind.refH * pxPerUnit) / kind.h,
        pin,
    };
}

export function getKind(id) {
    return BY_ID.get(id) || null;
}

// Resolve the kind for a live obstacle, tolerating legacy data that only has
// the boolean `qfp` flag (snapshots taken before kinds existed).
export function resolveKind(o) {
    return BY_ID.get(o.kind) || (o.qfp ? BY_ID.get('qfp') : BLOCK);
}

export function hasPins(o) {
    return pinGroups(o).length > 0;
}

const PIN_SIDE_ORDER = ['top', 'right', 'bottom', 'left'];

export function pinSides(o) {
    return pinGroups(o).map((g) => g.side);
}

export function pinGroups(o) {
    const kind = resolveKind(o);
    const groups = [];
    if (kind.pins?.length) {
        for (const side of kind.pins) groups.push({ side, kind: 'row' });
    } else if (kind.auxPins) {
        groups.push({
            side: o.auxPinSide || kind.auxPins.side,
            kind: 'aux',
            count: Math.max(1, kind.auxPins.count | 0),
            ...(o.auxPinOffsets?.length ? { offsets: o.auxPinOffsets } : {}),
        });
    }
    if (!groups.length) return [];
    const steps = o.auxPinSide ? 0 : (o.rot || 0);
    return groups.map((g) => ({
        ...g,
        side: PIN_SIDE_ORDER[(PIN_SIDE_ORDER.indexOf(g.side) + steps) % 4],
    }));
}

export function pinCellOffsets(length, group, spacing) {
    if (group.kind !== 'aux') {
        const offsets = [];
        for (let i = 0; i < length; i += spacing) offsets.push(i);
        return offsets;
    }

    const count = Math.min(Math.max(1, group.count | 0), Math.max(1, length));
    if (group.offsets?.length) {
        const seen = new Set();
        const offsets = [];
        for (const raw of group.offsets) {
            const off = Math.min(length - 1, Math.max(0, raw | 0));
            if (seen.has(off)) continue;
            seen.add(off);
            offsets.push(off);
            if (offsets.length >= count) break;
        }
        if (offsets.length) return offsets;
    }

    const offsets = [];
    const start = Math.max(0, Math.floor((length - count) / 2));
    for (let i = 0; i < count; i++) {
        const off = Math.min(length - 1, start + i);
        if (!offsets.includes(off)) offsets.push(off);
    }
    return offsets;
}

// Pick a side and two along-edge cell offsets for aux-pin meshes (heatsinks, etc.).
export function randomAuxPinPlacement(rng, w, h, count = 2) {
    const sides = ['top', 'right', 'bottom', 'left'];
    const side = sides[Math.floor(rng() * sides.length)];
    const edgeLen = side === 'top' || side === 'bottom' ? w : h;
    const want = Math.min(Math.max(1, count | 0), edgeLen);
    const minGap = Math.max(1, Math.floor(edgeLen / 3));
    const offsets = [];

    for (let t = 0; t < 32 && offsets.length < want; t++) {
        const off = Math.floor(rng() * edgeLen);
        if (offsets.every((o) => Math.abs(o - off) >= minGap)) offsets.push(off);
    }

    if (offsets.length < want) {
        const start = Math.floor(rng() * Math.max(1, edgeLen - want + 1));
        offsets.length = 0;
        for (let i = 0; i < want; i++) {
            offsets.push(Math.min(edgeLen - 1, start + i * minGap));
        }
    }

    offsets.sort((a, b) => a - b);
    return { auxPinSide: side, auxPinOffsets: offsets };
}

// Pixel geometry for drawing an obstacle's canonical shape, centered on the
// origin so callers can translate to the bbox center and apply `rot` turns.
export function obstacleDrawGeom(o, kind, cw, ch) {
    const rot = o.rot || 0;
    const cols = kind.w;
    const rows = kind.h;
    const cwCell = (rot & 1) ? (o.w * cw / kind.h) : (o.w * cw / kind.w);
    const chCell = (rot & 1) ? (o.h * ch / kind.w) : (o.h * ch / kind.h);
    const pw = cols * cwCell;
    const ph = rows * chCell;
    return { rot, ox: -pw / 2, oy: -ph / 2, cols, rows, cw: cwCell, ch: chCell };
}

// === Drawing ===============================================================
//
// Every routine works in pixels off a footprint placed at (ox, oy) spanning
// cols x rows grid cells, with cw/ch the per-cell pixel size. The canvas passes
// the obstacle's grid box; the palette passes a synthetic box sized to its
// thumbnail. Pinned chips overhang the footprint by half a cell on each pinned
// side -- callers leave room for that.

export function drawComponent(ctx, kind, geom, obstacle = null) {
    if (kind.auxPins) drawAuxPins(ctx, kind, geom, obstacle);
    switch (kind.shape) {
        case 'chip': return drawChip(ctx, kind, geom);
        case 'cap': return drawCap(ctx, geom);
        case 'heatsink': return drawHeatsink(ctx, geom);
        case 'octagon': return drawOctagon(ctx, geom);
        case 'header': return drawHeader(ctx, geom);
        case 'connector': return drawConnector(ctx, geom);
        case 'smd': return drawSMD(ctx, geom);
        case 'pad': return drawPadComponent(ctx, geom);
        case 'via': return drawViaComponent(ctx, geom);
        case 'block': default: return drawBlock(ctx, geom);
    }
}

function drawAuxPins(ctx, kind, geom, obstacle) {
    const group = obstacle ? pinGroups(obstacle)[0] : {
        side: kind.auxPins.side,
        kind: 'aux',
        count: kind.auxPins.count,
    };
    const side = group.side;
    const { ox, oy, cols, rows, cw, ch } = geom;
    const unit = Math.min(cw, ch);
    const b = bodyBox(geom, unit * 0.15);
    const pinWid = unit * 0.28;
    const pinOverlap = unit * 0.1;
    const offsets = side === 'top' || side === 'bottom'
        ? pinCellOffsets(cols, group, params.qfpPinSpacing)
        : pinCellOffsets(rows, group, params.qfpPinSpacing);

    ctx.fillStyle = params.fgColor;
    for (const offset of offsets) {
        if (side === 'top') {
            const cx = ox + (offset + 0.5) * cw;
            const y0 = oy - 0.5 * ch - pinOverlap;
            ctx.fillRect(cx - pinWid / 2, y0, pinWid, b.y - y0);
        } else if (side === 'right') {
            const cy = oy + (offset + 0.5) * ch;
            const x1 = ox + (cols + 0.5) * cw + pinOverlap;
            ctx.fillRect(b.x + b.w, cy - pinWid / 2, x1 - (b.x + b.w), pinWid);
        } else if (side === 'bottom') {
            const cx = ox + (offset + 0.5) * cw;
            const y1 = oy + (rows + 0.5) * ch + pinOverlap;
            ctx.fillRect(cx - pinWid / 2, b.y + b.h, pinWid, y1 - (b.y + b.h));
        } else if (side === 'left') {
            const cy = oy + (offset + 0.5) * ch;
            const x0 = ox - 0.5 * cw - pinOverlap;
            ctx.fillRect(x0, cy - pinWid / 2, b.x - x0, pinWid);
        }
    }
}

function bodyBox(geom, inset) {
    const { ox, oy, cols, rows, cw, ch } = geom;
    return {
        x: ox + inset,
        y: oy + inset,
        w: cols * cw - inset * 2,
        h: rows * ch - inset * 2,
    };
}

function strokeBody(ctx, b, unit) {
    ctx.lineWidth = Math.max(1, unit / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.fillRect(b.x, b.y, b.w, b.h);
    ctx.strokeRect(b.x, b.y, b.w, b.h);
}

function drawChip(ctx, kind, geom) {
    const { ox, oy, cols, rows, cw, ch } = geom;
    const unit = Math.min(cw, ch);
    const bodyInset = unit * 0.5;
    const pinWid = unit * 0.28;
    const pinOverlap = unit * 0.1;
    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const sides = new Set(kind.pins);
    const b = bodyBox(geom, bodyInset);

    // Pin tabs first so the body case renders over their roots, fusing each
    // tab into one continuous lead with whatever trace starts at its pin cell.
    ctx.fillStyle = params.fgColor;
    if (sides.has('top') || sides.has('bottom')) {
        for (let i = 0; i < cols; i += spacing) {
            const cx = ox + (i + 0.5) * cw;
            if (sides.has('top')) {
                const topY = oy - 0.5 * ch - pinOverlap;
                ctx.fillRect(cx - pinWid / 2, topY, pinWid, b.y - topY);
            }
            if (sides.has('bottom')) {
                const botEnd = oy + (rows + 0.5) * ch + pinOverlap;
                ctx.fillRect(cx - pinWid / 2, b.y + b.h, pinWid, botEnd - (b.y + b.h));
            }
        }
    }
    if (sides.has('left') || sides.has('right')) {
        for (let j = 0; j < rows; j += spacing) {
            const cy = oy + (j + 0.5) * ch;
            if (sides.has('left')) {
                const leftX = ox - 0.5 * cw - pinOverlap;
                ctx.fillRect(leftX, cy - pinWid / 2, b.x - leftX, pinWid);
            }
            if (sides.has('right')) {
                const rightEnd = ox + (cols + 0.5) * cw + pinOverlap;
                ctx.fillRect(b.x + b.w, cy - pinWid / 2, rightEnd - (b.x + b.w), pinWid);
            }
        }
    }

    strokeBody(ctx, b, unit);

    const dotR = Math.min(b.w, b.h) * 0.08;
    if (dotR > 0.5) {
        ctx.fillStyle = params.fgColor;
        ctx.beginPath();
        ctx.arc(b.x + dotR * 2.8, b.y + dotR * 2.8, dotR, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawBlock(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.15);
    strokeBody(ctx, b, unit);
    ctx.fillStyle = params.fgColor;
    const padR = unit * 0.22;
    for (const [cx, cy] of [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.h], [b.x + b.w, b.y + b.h]]) {
        ctx.beginPath();
        ctx.arc(cx, cy, padR, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawCap(ctx, geom) {
    const { ox, oy, cols, rows, cw, ch } = geom;
    const unit = Math.min(cw, ch);
    const cx = ox + cols * cw / 2;
    const cy = oy + rows * ch / 2;
    const r = Math.min(cols * cw, rows * ch) / 2 - unit * 0.15;

    ctx.lineWidth = Math.max(1, unit / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Polarity crescent on one side so it reads as an electrolytic cap.
    ctx.fillStyle = params.fgColor;
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI * 0.66, Math.PI * 1.34);
    ctx.closePath();
    ctx.fill();
}

function drawHeatsink(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.15);
    strokeBody(ctx, b, unit);

    // Parallel fins running across the body.
    ctx.lineWidth = Math.max(1, unit / 6);
    ctx.strokeStyle = params.fgColor;
    const step = Math.max(3, unit * 0.6);
    const inY = unit * 0.2;
    for (let fx = b.x + step; fx < b.x + b.w - step * 0.5; fx += step) {
        ctx.beginPath();
        ctx.moveTo(fx, b.y + inY);
        ctx.lineTo(fx, b.y + b.h - inY);
        ctx.stroke();
    }
}

function drawOctagon(ctx, geom) {
    const { ox, oy, cols, rows, cw, ch } = geom;
    const unit = Math.min(cw, ch);
    const cx = ox + cols * cw / 2;
    const cy = oy + rows * ch / 2;
    const r = Math.min(cols * cw, rows * ch) / 2 - unit * 0.12;

    ctx.lineWidth = Math.max(1, unit / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.beginPath();
    for (let k = 0; k < 8; k++) {
        const a = Math.PI / 8 + k * Math.PI / 4;
        const px = cx + r * Math.cos(a);
        const py = cy + r * Math.sin(a);
        if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = params.fgColor;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.18, 0, Math.PI * 2);
    ctx.fill();
}

function drawHeader(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.12);
    strokeBody(ctx, b, unit);

    // Single row of pin holes down the strip.
    const holeR = Math.min(b.h, unit) * 0.22;
    const cy = b.y + b.h / 2;
    const step = Math.max(holeR * 2.6, unit * 1.6);
    ctx.fillStyle = params.fgColor;
    for (let hx = b.x + step / 2; hx <= b.x + b.w - holeR; hx += step) {
        ctx.beginPath();
        ctx.arc(hx, cy, holeR, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawConnector(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.15);
    strokeBody(ctx, b, unit);

    // Port mouth: a recessed slot along the lower edge with contact teeth.
    const slotH = b.h * 0.42;
    const slotY = b.y + b.h - slotH - unit * 0.15;
    const slotX = b.x + unit * 0.3;
    const slotW = b.w - unit * 0.6;
    ctx.fillStyle = params.fgColor;
    ctx.fillRect(slotX, slotY, slotW, slotH);
    ctx.fillStyle = params.bgColor;
    const teeth = Math.max(2, Math.round(slotW / (unit * 1.2)));
    const toothW = slotW / (teeth * 2 - 1);
    for (let t = 0; t < teeth; t++) {
        ctx.fillRect(slotX + t * toothW * 2, slotY, toothW, slotH);
    }
}

function drawSMD(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.18);
    strokeBody(ctx, b, unit);

    // Two end terminals, like a chip resistor / LED.
    const capW = Math.max(unit * 0.5, b.w * 0.22);
    ctx.fillStyle = params.fgColor;
    ctx.fillRect(b.x, b.y, capW, b.h);
    ctx.fillRect(b.x + b.w - capW, b.y, capW, b.h);
}

function drawPadComponent(ctx, geom) {
    const unit = Math.min(geom.cw, geom.ch);
    const b = bodyBox(geom, unit * 0.2);
    ctx.lineWidth = Math.max(1, unit / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.fillRect(b.x, b.y, b.w, b.h);
    ctx.strokeRect(b.x, b.y, b.w, b.h);
}

function drawViaComponent(ctx, geom) {
    const { ox, oy, cols, rows, cw, ch } = geom;
    const unit = Math.min(cw, ch);
    const cx = ox + cols * cw / 2;
    const cy = oy + rows * ch / 2;
    const r = Math.min(cols * cw, rows * ch) / 2 - unit * 0.2;

    ctx.lineWidth = Math.max(1, unit / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = params.fgColor;
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(1, r * 0.25), 0, Math.PI * 2);
    ctx.fill();
}
