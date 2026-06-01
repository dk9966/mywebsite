// Obstacles ("meshes") that wires must avoid.
//
// The trick: this module doesn't change the routing algorithm at all. It just
// marks obstacle cells (plus a keep-out buffer around them) as unavailable on
// the same grid the wire generator already consults. The buffer is what gives
// the visible gap so wires never touch a mesh edge.

import { rnd, rndInt } from './rng.js';
import { params } from './params.js';

let obstacles = [];
let obstacleGridWidth = 0;
let obstacleGridHeight = 0;

export function getObstacles() {
    return obstacles;
}

// Replace the obstacles array wholesale. Used when loading snapshots.
export function setObstacles(next) {
    obstacles = Array.isArray(next) ? next.map((o) => ({
        x: o.x | 0,
        y: o.y | 0,
        w: Math.max(2, o.w | 0),
        h: Math.max(2, o.h | 0),
        qfp: !!o.qfp,
    })) : [];
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
    const sx = (1 + canvas.width / params.cellSize) / obstacleGridWidth;
    const sy = (1 + canvas.height / params.cellSize) / obstacleGridHeight;
    return {
        cw: params.cellSize * sx,
        ch: params.cellSize * sy,
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

    const count = Math.max(0, params.obstacleCount | 0);
    if (count === 0) return;

    const baseSize = Math.max(1, params.obstacleSize | 0);
    const sizeRand = clamp01(params.obstacleSizeRandomness ?? 0);
    const { minDim, maxDim } = obstacleSizeRange(baseSize, sizeRand);
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
                const candidate = makeObstacle(x, y, baseSize, sizeRand);
                if (!overlapsAny(candidate, obstacles, minSeparation)) {
                    chosen = candidate;
                    break;
                }
            }
            if (!chosen) {
                const x = clamp(Math.round(anchorX), minX, maxX);
                const y = clamp(Math.round(anchorY), minY, maxY);
                const candidate = makeObstacle(x, y, baseSize, sizeRand);
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

function obstacleSizeRange(baseSize, sizeRand) {
    if (sizeRand <= 0) return { minDim: baseSize, maxDim: baseSize };
    const spread = Math.max(1, Math.round(baseSize * sizeRand));
    return {
        minDim: Math.max(2, baseSize - spread),
        maxDim: baseSize + spread,
    };
}

function randomObstacleDimensions(baseSize, sizeRand) {
    const { minDim, maxDim } = obstacleSizeRange(baseSize, sizeRand);
    if (minDim === maxDim) return { w: baseSize, h: baseSize };
    return {
        w: minDim + rndInt(maxDim - minDim + 1),
        h: minDim + rndInt(maxDim - minDim + 1),
    };
}

// Per-obstacle qfp tag is decided once at generation time, so the buffer,
// pin-seed list, and drawing branch all see the same answer.
function makeObstacle(x, y, baseSize, sizeRand) {
    const qfp = params.qfpStyle && rnd() < clamp01(params.qfpFraction ?? 0);
    const { w, h } = randomObstacleDimensions(baseSize, sizeRand);
    return { x, y, w, h, qfp };
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

    for (const o of obstacles) {
        for (const c of obstacleCornerPixels(o, cw, ch)) {
            ctx.beginPath();
            ctx.arc(c.px, c.py, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }
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
        const buffer = o.qfp ? 0 : blockBuffer;
        for (let x = o.x - buffer; x < o.x + o.w + buffer; x++) {
            for (let y = o.y - buffer; y < o.y + o.h + buffer; y++) {
                if (x < 0 || y < 0 || x >= gridWidth || y >= gridHeight) continue;
                grid[x][y].available = false;
            }
        }
    }
}

// Cells (and outward headings) where wires should be seeded for QFP obstacles.
// Only obstacles tagged .qfp emit pins; block obstacles emit nothing.
// `heading` is a DIRS index (see wire.js): 1 = up, 3 = right, 5 = down, 7 = left.
// Each pin cell is one step OUTSIDE the chip boundary on its side, and its wire
// is told to grow further outward; the matching pin tab in drawQFP fills the
// half-cell gap from the chip body edge to that pin cell center.
export function getQFPPinSeeds(gridWidth, gridHeight) {
    const seeds = [];
    if (!params.qfpStyle) return seeds;
    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const inBounds = (x, y) => x >= 0 && y >= 0 && x < gridWidth && y < gridHeight;

    for (const o of obstacles) {
        if (!o.qfp) continue;
        for (let i = 0; i < o.w; i += spacing) {
            const x = o.x + i, y = o.y - 1;
            if (inBounds(x, y)) seeds.push({ x, y, heading: 1 }); // up
        }
        for (let j = 0; j < o.h; j += spacing) {
            const x = o.x + o.w, y = o.y + j;
            if (inBounds(x, y)) seeds.push({ x, y, heading: 3 }); // right
        }
        for (let i = 0; i < o.w; i += spacing) {
            const x = o.x + i, y = o.y + o.h;
            if (inBounds(x, y)) seeds.push({ x, y, heading: 5 }); // down
        }
        for (let j = 0; j < o.h; j += spacing) {
            const x = o.x - 1, y = o.y + j;
            if (inBounds(x, y)) seeds.push({ x, y, heading: 7 }); // left
        }
    }
    return seeds;
}

export function drawObstacles(canvas, ctx, gridWidth, gridHeight) {
    if (!obstacles.length) return;

    const sx = (1 + canvas.width / params.cellSize) / gridWidth;
    const sy = (1 + canvas.height / params.cellSize) / gridHeight;
    const cw = params.cellSize * sx;
    const ch = params.cellSize * sy;

    for (const o of obstacles) {
        if (o.qfp) drawQFP(ctx, o, cw, ch);
        else drawBlock(ctx, o, cw, ch);
    }
}

function drawBlock(ctx, o, cw, ch) {
    const inset = Math.min(cw, ch) * 0.15;
    const padRadius = Math.min(cw, ch) * 0.22;
    const x = o.x * cw + inset;
    const y = o.y * ch + inset;
    const w = o.w * cw - inset * 2;
    const h = o.h * ch - inset * 2;

    ctx.lineWidth = Math.max(1, params.cellSize / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = params.fgColor;
    for (const [cx, cy] of cornerPoints(x, y, w, h)) {
        ctx.beginPath();
        ctx.arc(cx, cy, padRadius, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawQFP(ctx, o, cw, ch) {
    // Each pin tab bridges the chip body and the wire trace that starts at
    // the adjacent pin cell. Two rules:
    //   * width matches the wire stroke (params.cellSize / 4) so the seam
    //     between tab and trace is invisible -- one continuous line, not a
    //     "pin lead followed by thinner wire".
    //   * length reaches the pin cell center plus a tiny overlap so canvas
    //     pixel rounding can't open a gap.
    const cellMin = Math.min(cw, ch);
    const bodyInset = cellMin * 0.5;
    const pinWid = params.cellSize / 4;
    const pinOverlap = cellMin * 0.1;
    const spacing = Math.max(1, params.qfpPinSpacing | 0);

    const bx = o.x * cw + bodyInset;
    const by = o.y * ch + bodyInset;
    const bw = o.w * cw - bodyInset * 2;
    const bh = o.h * ch - bodyInset * 2;

    ctx.fillStyle = params.fgColor;

    // Top + bottom pins
    for (let i = 0; i < o.w; i += spacing) {
        const cx = (o.x + i + 0.5) * cw;
        // Top: from pin cell center DOWN to body top.
        const topY = (o.y - 0.5) * ch - pinOverlap;
        ctx.fillRect(cx - pinWid / 2, topY, pinWid, by - topY);
        // Bottom: from body bottom DOWN to pin cell center.
        const botEnd = (o.y + o.h + 0.5) * ch + pinOverlap;
        ctx.fillRect(cx - pinWid / 2, by + bh, pinWid, botEnd - (by + bh));
    }
    // Left + right pins
    for (let j = 0; j < o.h; j += spacing) {
        const cy = (o.y + j + 0.5) * ch;
        const leftX = (o.x - 0.5) * cw - pinOverlap;
        ctx.fillRect(leftX, cy - pinWid / 2, bx - leftX, pinWid);
        const rightEnd = (o.x + o.w + 0.5) * cw + pinOverlap;
        ctx.fillRect(bx + bw, cy - pinWid / 2, rightEnd - (bx + bw), pinWid);
    }

    // Body on top of the tab roots so the chip case looks solid.
    ctx.lineWidth = Math.max(1, params.cellSize / 5);
    ctx.fillStyle = params.bgColor;
    ctx.strokeStyle = params.fgColor;
    ctx.fillRect(bx, by, bw, bh);
    ctx.strokeRect(bx, by, bw, bh);

    // Pin-1 dot so the chip reads as a chip.
    const dotR = Math.min(bw, bh) * 0.06;
    if (dotR > 0.5) {
        ctx.fillStyle = params.fgColor;
        ctx.beginPath();
        ctx.arc(bx + dotR * 2.8, by + dotR * 2.8, dotR, 0, Math.PI * 2);
        ctx.fill();
    }
}

function cornerPoints(x, y, w, h) {
    return [
        [x, y],
        [x + w, y],
        [x, y + h],
        [x + w, y + h],
    ];
}
