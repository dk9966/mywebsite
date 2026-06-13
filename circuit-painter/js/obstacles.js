// Obstacles ("meshes") that wires must avoid.
//
// The trick: this module doesn't change the routing algorithm at all. It just
// marks obstacle cells (plus a keep-out buffer around them) as unavailable on
// the same grid the wire generator already consults. The buffer is what gives
// the visible gap so wires never touch a mesh edge.

import { rnd, rndInt } from './rng.js';
import { params } from './params.js';
import {
    KIND_REFERENCE_DIM, MAX_KIND_DIM, drawComponent, getKind, hasPins,
    listPaletteKinds, obstacleDrawGeom, pinCellOffsets, pinGroups, resolveKind,
} from './components.js';

let obstacles = [];
let obstacleGridWidth = 0;
let obstacleGridHeight = 0;

export function getObstacles() {
    return obstacles;
}

// Replace the obstacles array wholesale. Used when loading snapshots.
export function setObstacles(next) {
    obstacles = Array.isArray(next) ? next.map((o) => {
        const kind = o.kind || (o.qfp ? 'qfp' : 'block');
        return {
            x: o.x | 0,
            y: o.y | 0,
            w: Math.max(2, o.w | 0),
            h: Math.max(2, o.h | 0),
            kind,
            qfp: kind === 'qfp',
            rot: (o.rot | 0) % 4,
            ...(o.auxPinSide ? { auxPinSide: o.auxPinSide } : {}),
            ...(o.auxPinOffsets?.length ? { auxPinOffsets: o.auxPinOffsets.slice() } : {}),
        };
    }) : [];
}

// Remove a specific obstacle (e.g. via the right-click Delete menu).
export function removeObstacle(o) {
    const i = obstacles.indexOf(o);
    if (i !== -1) obstacles.splice(i, 1);
}

// Rotate 90° clockwise around the obstacle center; swaps w/h and keeps the
// center fixed so pins and asymmetric silhouettes turn in place.
export function rotateObstacle(o) {
    const cx = o.x + o.w / 2;
    const cy = o.y + o.h / 2;
    const nw = o.h;
    const nh = o.w;
    o.w = nw;
    o.h = nh;
    o.rot = ((o.rot || 0) + 1) % 4;
    o.x = clamp(Math.round(cx - o.w / 2), 0, Math.max(0, obstacleGridWidth - o.w));
    o.y = clamp(Math.round(cy - o.h / 2), 0, Math.max(0, obstacleGridHeight - o.h));
}

// Drop a palette component onto the board, centered under the cursor. Returns
// the new obstacle so the caller can trigger a reroute.
export function addComponentAtPixel(kindId, px, py, canvas) {
    const kind = getKind(kindId);
    if (!kind) return null;
    const { cw, ch } = gridMetrics(canvas);
    const w = Math.max(2, kind.w | 0);
    const h = Math.max(2, kind.h | 0);
    const x = clamp(Math.round(px / cw - w / 2), 0, Math.max(0, obstacleGridWidth - w));
    const y = clamp(Math.round(py / ch - h / 2), 0, Math.max(0, obstacleGridHeight - h));
    const o = { x, y, w, h, kind: kind.id, qfp: kind.id === 'qfp', rot: 0 };
    obstacles.push(o);
    return o;
}

// Bring every obstacle inside the current grid bounds. No-op when obstacles
// were placed by generateObstacles (it already respects bounds); does real
// work when restoring a snapshot taken at a different cellSize/viewport.
export function clampObstaclesToGrid(gridWidth, gridHeight) {
    const filtered = [];
    for (const o of obstacles) {
        const x = Math.max(0, Math.min(gridWidth - 2, o.x));
        const y = Math.max(0, Math.min(gridHeight - 2, o.y));
        const w = Math.max(2, Math.min(o.w, gridWidth - 1 - x));
        const h = Math.max(2, Math.min(o.h, gridHeight - 1 - y));
        if (w < 2 || h < 2) continue;
        filtered.push({ ...o, x, y, w, h });
    }
    obstacles = filtered;
}

export function setObstacleGridDimensions(w, h) {
    obstacleGridWidth = w;
    obstacleGridHeight = h;
}

export function gridMetrics(canvas) {
    return {
        cw: canvas.width / obstacleGridWidth,
        ch: canvas.height / obstacleGridHeight,
    };
}

export function pixelToGrid(px, py, canvas) {
    const { cw, ch } = gridMetrics(canvas);
    return {
        gx: Math.floor(px / cw),
        gy: Math.floor(py / ch),
    };
}

// Seeded placement: relies on the caller having called setSeed() already.
//
// Algorithm:
//   1. Lay out a roughly-aspect-matched grid of anchor positions that holds
//      exactly `count` slots.
//   2. For each slot, lerp between its anchor (perfectly even) and an
//      independently-random point in the usable area, by `randomness`.
//      randomness=0 -> snap to grid; randomness=1 -> fully random.
//   3. Re-jitter a few times if the lerped spot would overlap an earlier one;
//      fall back to the bare anchor as a last resort.
export function generateObstacles(gridWidth, gridHeight) {
    obstacles = [];
    if (!params.obstaclesEnabled) return;

    if (params.generatorChipsOnly) {
        generateChipObstacles(gridWidth, gridHeight);
        return;
    }

    const count = Math.max(0, params.obstacleCount | 0);
    if (count === 0) return;

    // Every generated obstacle is a random component kind at the same scale,
    // so the slider stays meaningful (scale 1 = native footprints) while the
    // board fills with the full mix of shapes.
    const scale = Math.max(0.25, (params.obstacleSize | 0) / KIND_REFERENCE_DIM);
    const maxDim = Math.ceil(MAX_KIND_DIM * scale);
    const buffer = Math.max(0, params.obstacleKeepOut | 0);
    const randomness = clamp01(params.obstacleSpacingRandomness ?? 1);
    const edgePad = 2;
    const minSeparation = buffer + 1;

    const minX = edgePad;
    const minY = edgePad;
    const maxX = gridWidth - maxDim - edgePad;
    const maxY = gridHeight - maxDim - edgePad;
    if (maxX <= minX || maxY <= minY) return;

    const usableW = maxX - minX;
    const usableH = maxY - minY;

    const aspect = (usableW + 1) / (usableH + 1);
    let cols = Math.max(1, Math.round(Math.sqrt(count * aspect)));
    let rows = Math.max(1, Math.ceil(count / cols));
    while (rows * cols < count) {
        if (usableW > usableH) cols++; else rows++;
    }

    const cellW = cols > 1 ? usableW / (cols - 1) : 0;
    const cellH = rows > 1 ? usableH / (rows - 1) : 0;
    // If a row or column has only one slot, center the anchor in that axis.
    const baseOffsetX = cols === 1 ? usableW / 2 : 0;
    const baseOffsetY = rows === 1 ? usableH / 2 : 0;

    const triesPerSlot = randomness > 0 ? 16 : 1;

    let placed = 0;
    for (let row = 0; row < rows && placed < count; row++) {
        for (let col = 0; col < cols && placed < count; col++) {
            const anchorX = minX + baseOffsetX + col * cellW;
            const anchorY = minY + baseOffsetY + row * cellH;

            let chosen = null;
            for (let attempt = 0; attempt < triesPerSlot; attempt++) {
                const rx = minX + rndInt(usableW + 1);
                const ry = minY + rndInt(usableH + 1);
                const x = clamp(Math.round(lerp(anchorX, rx, randomness)), minX, maxX);
                const y = clamp(Math.round(lerp(anchorY, ry, randomness)), minY, maxY);
                const candidate = makeObstacle(x, y, scale);
                if (!overlapsAny(candidate, obstacles, minSeparation)) {
                    chosen = candidate;
                    break;
                }
            }
            if (!chosen) {
                const x = clamp(Math.round(anchorX), minX, maxX);
                const y = clamp(Math.round(anchorY), minY, maxY);
                const candidate = makeObstacle(x, y, scale);
                if (!overlapsAny(candidate, obstacles, minSeparation)) chosen = candidate;
            }
            if (chosen) {
                obstacles.push(chosen);
                placed++;
            }
        }
    }

    relaxObstacleSpacing(gridWidth, gridHeight);
}

// Generator layout: multiple QFPs and SOICs only — no mixed palette obstacles.
function generateChipObstacles(gridWidth, gridHeight) {
    const qfpCount = Math.max(1, params.generatorQfpCount | 0);
    const soicCount = Math.max(1, params.generatorSoicCount | 0);
    const count = qfpCount + soicCount;
    const scale = Math.max(0.25, (params.qfpSize | 0) / KIND_REFERENCE_DIM);
    const maxDim = Math.ceil(MAX_KIND_DIM * scale);
    const randomness = clamp01(params.obstacleSpacingRandomness ?? 0.35);
    const edgePad = 2;
    const minSeparation = Math.max(0, params.obstacleMinSpacing | 0) + 1;

    const minX = edgePad;
    const minY = edgePad;
    const maxX = gridWidth - maxDim - edgePad;
    const maxY = gridHeight - maxDim - edgePad;
    if (maxX <= minX || maxY <= minY) return;

    const usableW = maxX - minX;
    const usableH = maxY - minY;

    const aspect = (usableW + 1) / (usableH + 1);
    let cols = Math.max(1, Math.round(Math.sqrt(count * aspect)));
    let rows = Math.max(1, Math.ceil(count / cols));
    while (rows * cols < count) {
        if (usableW > usableH) cols++; else rows++;
    }

    const cellW = cols > 1 ? usableW / (cols - 1) : 0;
    const cellH = rows > 1 ? usableH / (rows - 1) : 0;
    const baseOffsetX = cols === 1 ? usableW / 2 : 0;
    const baseOffsetY = rows === 1 ? usableH / 2 : 0;

    const kinds = [];
    for (let i = 0; i < qfpCount; i++) kinds.push('qfp');
    for (let i = 0; i < soicCount; i++) kinds.push('soic');
    for (let i = kinds.length - 1; i > 0; i--) {
        const j = rndInt(i + 1);
        [kinds[i], kinds[j]] = [kinds[j], kinds[i]];
    }

    const triesPerSlot = randomness > 0 ? 16 : 1;
    let placed = 0;
    let kindIdx = 0;

    for (let row = 0; row < rows && placed < count; row++) {
        for (let col = 0; col < cols && placed < count; col++) {
            const anchorX = minX + baseOffsetX + col * cellW;
            const anchorY = minY + baseOffsetY + row * cellH;
            // Consume the kind only when the chip actually lands, otherwise a
            // failed slot burns a kind and later slots read past the array.
            const kindId = kinds[kindIdx];

            let chosen = null;
            for (let attempt = 0; attempt < triesPerSlot; attempt++) {
                const rx = minX + rndInt(usableW + 1);
                const ry = minY + rndInt(usableH + 1);
                const x = clamp(Math.round(lerp(anchorX, rx, randomness)), minX, maxX);
                const y = clamp(Math.round(lerp(anchorY, ry, randomness)), minY, maxY);
                const candidate = makeChipObstacle(x, y, kindId, scale);
                if (!overlapsAny(candidate, obstacles, minSeparation)) {
                    chosen = candidate;
                    break;
                }
            }
            if (!chosen) {
                const x = clamp(Math.round(anchorX), minX, maxX);
                const y = clamp(Math.round(anchorY), minY, maxY);
                const candidate = makeChipObstacle(x, y, kindId, scale);
                if (!overlapsAny(candidate, obstacles, minSeparation)) chosen = candidate;
            }
            if (chosen) {
                obstacles.push(chosen);
                placed++;
                kindIdx++;
            }
        }
    }

    relaxObstacleSpacing(gridWidth, gridHeight);
}

function makeChipObstacle(x, y, kindId, scale) {
    const kind = getKind(kindId);
    if (kindId === 'qfp') {
        const side = Math.max(2, Math.round(kind.w * scale));
        return { x, y, w: side, h: side, kind: 'qfp', qfp: true, rot: 0 };
    }
    if (rnd() > 0.5) {
        return {
            x,
            y,
            w: Math.max(2, Math.round(kind.w * scale)),
            h: Math.max(2, Math.round(kind.h * scale)),
            kind: 'soic',
            qfp: false,
            rot: 0,
        };
    }
    return {
        x,
        y,
        w: Math.max(2, Math.round(kind.h * scale)),
        h: Math.max(2, Math.round(kind.w * scale)),
        kind: 'soic',
        qfp: false,
        rot: 1,
    };
}

// Iterative push-apart relaxation. Honors params.obstacleMinSpacing as the
// minimum edge-to-edge gap between any two obstacles. Each pair that's too
// close is pushed along the axis where they're already MORE separated -- this
// is the cheapest escape direction and avoids unnecessary movement.
//
// Bounded by a hard iteration cap so a tightly packed board doesn't loop
// forever; chains of pushes converge geometrically since each pass roughly
// halves any remaining deficit. If grid bounds prevent full separation, we
// stop at the best-effort layout.
function relaxObstacleSpacing(gridWidth, gridHeight) {
    const minSpacing = Math.max(0, params.obstacleMinSpacing | 0);
    if (minSpacing <= 0 || obstacles.length < 2) return;

    const edgePad = 2;
    const maxIterations = 60;

    for (let iter = 0; iter < maxIterations; iter++) {
        let moved = false;

        for (let i = 0; i < obstacles.length - 1; i++) {
            for (let j = i + 1; j < obstacles.length; j++) {
                const a = obstacles[i];
                const b = obstacles[j];

                // Signed edge-gap on each axis. Positive = the boxes are
                // separated on that axis; negative = their projections
                // overlap there by |gap| cells.
                const gapX = Math.max(b.x - (a.x + a.w), a.x - (b.x + b.w));
                const gapY = Math.max(b.y - (a.y + a.h), a.y - (b.y + b.h));

                if (gapX >= minSpacing || gapY >= minSpacing) continue;

                if (gapX >= gapY) {
                    const push = Math.ceil((minSpacing - gapX) / 2);
                    if (a.x + a.w / 2 < b.x + b.w / 2) {
                        a.x -= push; b.x += push;
                    } else {
                        a.x += push; b.x -= push;
                    }
                } else {
                    const push = Math.ceil((minSpacing - gapY) / 2);
                    if (a.y + a.h / 2 < b.y + b.h / 2) {
                        a.y -= push; b.y += push;
                    } else {
                        a.y += push; b.y -= push;
                    }
                }
                moved = true;
            }
        }

        for (const o of obstacles) {
            o.x = clamp(o.x, edgePad, gridWidth - o.w - edgePad);
            o.y = clamp(o.y, edgePad, gridHeight - o.h - edgePad);
        }

        if (!moved) break;
    }
}

// Pick a random component kind and stamp it at the given scale. The kind is
// decided once at generation time so the buffer, pin-seed list, and drawing
// branch all see the same answer.
function makeObstacle(x, y, scale) {
    const kinds = listPaletteKinds();
    const kind = kinds[rndInt(kinds.length)];
    const w = Math.max(2, Math.round(kind.w * scale));
    const h = Math.max(2, Math.round(kind.h * scale));
    return { x, y, w, h, kind: kind.id, qfp: kind.id === 'qfp', rot: 0 };
}

// Corner resize: drag a handle to change w/h (and x/y for nw/ne/sw as needed).
export function resizeObstacle(o, corner, gx, gy) {
    const minSize = 2;
    const right = o.x + o.w;
    const bottom = o.y + o.h;
    const maxGx = obstacleGridWidth - 1;
    const maxGy = obstacleGridHeight - 1;

    gx = clamp(gx, 0, maxGx);
    gy = clamp(gy, 0, maxGy);

    if (corner === 'se') {
        o.w = clamp(gx - o.x + 1, minSize, maxGx - o.x + 1);
        o.h = clamp(gy - o.y + 1, minSize, maxGy - o.y + 1);
    } else if (corner === 'nw') {
        const newX = clamp(gx, 0, right - minSize);
        const newY = clamp(gy, 0, bottom - minSize);
        o.w = right - newX;
        o.h = bottom - newY;
        o.x = newX;
        o.y = newY;
    } else if (corner === 'ne') {
        const newY = clamp(gy, 0, bottom - minSize);
        o.w = clamp(gx - o.x + 1, minSize, maxGx - o.x + 1);
        o.h = bottom - newY;
        o.y = newY;
    } else if (corner === 'sw') {
        const newX = clamp(gx, 0, right - minSize);
        o.x = newX;
        o.w = right - newX;
        o.h = clamp(gy - o.y + 1, minSize, maxGy - o.y + 1);
    }

    if (o.qfp) {
        const side = Math.max(minSize, Math.min(o.w, o.h));
        if (corner === 'se') {
            o.w = side;
            o.h = side;
        } else if (corner === 'nw') {
            o.x = right - side;
            o.y = bottom - side;
            o.w = side;
            o.h = side;
        } else if (corner === 'ne') {
            o.y = bottom - side;
            o.w = side;
            o.h = side;
        } else if (corner === 'sw') {
            o.x = right - side;
            o.w = side;
            o.h = side;
        }
    }
}

export function hitTestCorner(px, py, canvas) {
    if (!obstacles.length || !params.obstaclesEnabled) return null;
    const { cw, ch } = gridMetrics(canvas);
    const hitR = Math.max(10, Math.min(cw, ch) * 0.45);

    for (const o of obstacles) {
        const corners = obstacleCornerPixels(o, cw, ch);
        for (const c of corners) {
            if (Math.hypot(px - c.px, py - c.py) <= hitR) {
                return { obstacle: o, corner: c.corner };
            }
        }
    }
    return null;
}

export function hitTestCenter(px, py, canvas) {
    if (!obstacles.length || !params.obstaclesEnabled) return null;
    const { cw, ch } = gridMetrics(canvas);
    const hitR = Math.max(12, Math.min(cw, ch) * 0.5);

    for (const o of obstacles) {
        const cx = (o.x + o.w / 2) * cw;
        const cy = (o.y + o.h / 2) * ch;
        if (Math.hypot(px - cx, py - cy) <= hitR) {
            const { gx, gy } = pixelToGrid(px, py, canvas);
            return {
                obstacle: o,
                originX: o.x,
                originY: o.y,
                startGx: gx,
                startGy: gy,
            };
        }
    }
    return null;
}

export function moveObstacle(o, gx, gy, originX, originY, startGx, startGy) {
    const dx = gx - startGx;
    const dy = gy - startGy;
    const edgePad = 0;
    const maxX = obstacleGridWidth - o.w - edgePad;
    const maxY = obstacleGridHeight - o.h - edgePad;
    o.x = clamp(Math.round(originX + dx), edgePad, maxX);
    o.y = clamp(Math.round(originY + dy), edgePad, maxY);
}

function obstacleCornerPixels(o, cw, ch) {
    return [
        { corner: 'nw', px: o.x * cw, py: o.y * ch },
        { corner: 'ne', px: (o.x + o.w) * cw, py: o.y * ch },
        { corner: 'sw', px: o.x * cw, py: (o.y + o.h) * ch },
        { corner: 'se', px: (o.x + o.w) * cw, py: (o.y + o.h) * ch },
    ];
}

export function drawObstacleHandles(canvas, ctx) {
    if (!params.editObstacles || !params.obstaclesEnabled || !obstacles.length) return;

    const { cw, ch } = gridMetrics(canvas);
    const r = Math.max(5, Math.min(cw, ch) * 0.22);
    ctx.fillStyle = params.fgColor;
    ctx.strokeStyle = params.bgColor;
    ctx.lineWidth = Math.max(1, r * 0.35);

    const centerR = Math.max(6, Math.min(cw, ch) * 0.28);
    for (const o of obstacles) {
        for (const c of obstacleCornerPixels(o, cw, ch)) {
            ctx.beginPath();
            ctx.arc(c.px, c.py, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }
        const cx = (o.x + o.w / 2) * cw;
        const cy = (o.y + o.h / 2) * ch;
        ctx.fillStyle = params.bgColor;
        ctx.strokeStyle = params.fgColor;
        ctx.beginPath();
        ctx.rect(cx - centerR, cy - centerR, centerR * 2, centerR * 2);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = params.fgColor;
    }
}

function overlapsAny(rect, list, spacing) {
    for (const o of list) {
        if (
            rect.x < o.x + o.w + spacing &&
            rect.x + rect.w + spacing > o.x &&
            rect.y < o.y + o.h + spacing &&
            rect.y + rect.h + spacing > o.y
        ) return true;
    }
    return false;
}

function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
function lerp(a, b, t) { return a + (b - a) * t; }

export function applyObstaclesToGrid(grid, gridWidth, gridHeight) {
    // Per obstacle: QFP pins are supposed to touch the body, so QFP obstacles
    // skip the keep-out buffer. Block obstacles keep the buffer for the gap
    // the wires preserve around them.
    const blockBuffer = Math.max(0, params.obstacleKeepOut | 0);
    for (const o of obstacles) {
        const buffer = hasPins(o) ? 0 : blockBuffer;
        for (let x = o.x - buffer; x < o.x + o.w + buffer; x++) {
            for (let y = o.y - buffer; y < o.y + o.h + buffer; y++) {
                if (x < 0 || y < 0 || x >= gridWidth || y >= gridHeight) continue;
                grid[x][y].available = false;
            }
        }
    }
}

// Cells (and outward headings) where wires should be seeded for pinned meshes.
// ICs emit full pin rows; aux meshes emit their small aesthetic pin pairs.
// `heading` is a DIRS index (see wire.js): 1 = up, 3 = right, 5 = down, 7 = left.
// Each pin cell is one step OUTSIDE the chip boundary on its side, and its wire
// is told to grow further outward; the matching pin tab in drawChip fills the
// half-cell gap from the chip body edge to that pin cell center.
export function getQFPPinSeeds(gridWidth, gridHeight) {
    const seeds = [];
    if (!params.qfpStyle) return seeds;
    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const inBounds = (x, y) => x >= 0 && y >= 0 && x < gridWidth && y < gridHeight;

    for (const o of obstacles) {
        for (const group of pinGroups(o)) {
            if (group.side === 'top') {
                for (const i of pinCellOffsets(o.w, group, spacing)) {
                    const x = o.x + i, y = o.y - 1;
                    if (inBounds(x, y)) seeds.push({ x, y, heading: 1 }); // up
                }
            } else if (group.side === 'right') {
                for (const j of pinCellOffsets(o.h, group, spacing)) {
                    const x = o.x + o.w, y = o.y + j;
                    if (inBounds(x, y)) seeds.push({ x, y, heading: 3 }); // right
                }
            } else if (group.side === 'bottom') {
                for (const i of pinCellOffsets(o.w, group, spacing)) {
                    const x = o.x + i, y = o.y + o.h;
                    if (inBounds(x, y)) seeds.push({ x, y, heading: 5 }); // down
                }
            } else if (group.side === 'left') {
                for (const j of pinCellOffsets(o.h, group, spacing)) {
                    const x = o.x - 1, y = o.y + j;
                    if (inBounds(x, y)) seeds.push({ x, y, heading: 7 }); // left
                }
            }
        }
    }
    return seeds;
}

export function drawObstacles(canvas, ctx, gridWidth, gridHeight) {
    if (!obstacles.length) return;

    const cw = canvas.width / gridWidth;
    const ch = canvas.height / gridHeight;

    for (const o of obstacles) {
        const kind = resolveKind(o);
        const ox = o.x * cw;
        const oy = o.y * ch;
        if (!(o.rot || 0)) {
            drawComponent(ctx, kind, { ox, oy, cols: o.w, rows: o.h, cw, ch }, o);
            continue;
        }
        const geom = obstacleDrawGeom(o, kind, cw, ch);
        const mx = ox + o.w * cw / 2;
        const my = oy + o.h * ch / 2;
        ctx.save();
        ctx.translate(mx, my);
        ctx.rotate(geom.rot * Math.PI / 2);
        drawComponent(ctx, kind, geom, o);
        ctx.restore();
    }
}
