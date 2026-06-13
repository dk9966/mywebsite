// Cell + Wire: greedy random walk that picks the next direction biased toward
// "go straight" (params.straightness) and toward whatever has been painted into
// the flow grid (params.flowInfluence). Obstacles are handled outside by simply
// marking their cells as unavailable; this module doesn't need to know about them.

import { rnd, rndInt } from './rng.js';
import { mapDirection8ToFlow4, getFlowStrength } from './flowGrid.js';
import { params } from './params.js';
import {
    chamferDirsForCorner, directionBetween, isSharpCorner,
} from './pathfindCore.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

// Even DIRS indices (0,2,4,6) are the four diagonals; odd are cardinals.
const isDiagonal = (dirIndex) => (dirIndex & 1) === 0;

// True if this candidate diagonal step should be vetoed under the current
// params.diagonalChance. Single source of truth, used both for the initial
// heading and for every step.
function diagonalVetoed(dirIndex) {
    return isDiagonal(dirIndex) && rnd() >= params.diagonalChance;
}

// +1 for horizontal cardinals, -1 for vertical cardinals, 0 for everything
// else. Used by the directionality layer to score candidate directions.
function horizontalScore(dirIndex) {
    if (dirIndex === 3 || dirIndex === 7) return 1;
    if (dirIndex === 1 || dirIndex === 5) return -1;
    return 0;
}

export class Cell {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.available = true;
        // DIRS index of the wire that claimed this cell, or -1 if empty.
        // Used by the collectiveness pick so new wires can detect which way
        // neighboring traces are heading and run parallel to them.
        this.heading = -1;
    }
}

export class Wire {
    constructor(start, grid, gridWidth, gridHeight, initialHeading = null) {
        this.cells = [start];
        this.grid = grid;
        this.gridWidth = gridWidth;
        this.gridHeight = gridHeight;
        // `last` is the DIRS index of the wire's most recent move (i.e. the
        // forward heading). modifier = 0 keeps that heading, ±1 turns 45°.
        // Callers that seed a wire (QFP pins) pass the direction they want
        // the wire to grow toward.
        this.last = initialHeading !== null
            ? initialHeading
            : findRandomAvailableDirection(start.x, start.y, grid, gridWidth, gridHeight);
        // Wires born as QFP pin stubs always render, regardless of cutOffLength
        // and prioritizeLongWires. The flag is set by the caller after build.
        this.isQFPPin = false;
        // Bus lines (bus.js) are straight parallel traces with 45 degree tails,
        // built by setting .cells directly. They render as continuous traces
        // with no end pads.
        this.isBus = false;
        // Greedy random-walk fill (main.js when Show Buses is off).
        this.isGreedy = false;
        // Router routes (router.js): A* paths between anchors. They always
        // render (no cutOffLength gating), carry no end pads
        // (noPads), and may set strokeScale for the length-based taper.
        this.isRoute = false;
        this.noPads = false;
        // When set, overrides the default stroke width as a fraction of
        // cellSize. null falls back to the default 0.25.
        this.strokeScale = null;
        // Manual-edit override. When non-null it's a sparse polyline of
        // {x, y} grid-float corner points (see wireEdit.js) and becomes the
        // source of truth for rendering -- the dense `cells` list is only used
        // until the user grabs a joint. Null means "render straight from cells".
        this.points = null;
        // User-drawn or snapshot-restored trace; always visible when circuits on.
        this.manual = false;
    }

    generate() {
        // Track this wire's own cells so the walk can't curl back adjacent to
        // its own body. A loop can only close by touching an earlier segment,
        // so vetoing self-contact (beyond the last two cells -- see touchesSelf)
        // prevents loops by construction instead of relying on straightness,
        // which can't help once a turn is geometrically forced. Skipped cells
        // stay free for other wires, so the board still fills with no gaps.
        const keyOf = (c) => c.x * this.gridHeight + c.y;
        const own = new Set(this.cells.map(keyOf));

        while (this.cells.length < params.wireLength) {
            const current = this.cells[this.cells.length - 1];
            // Modifier semantics: 0 = keep heading, ±1 = 45° turn. 90° (±2) is never used.
            const directionModifiers = rnd() > 0.5 ? [0, 1, -1] : [0, -1, 1];

            const flowBiases = [];
            let totalFlowBias = 0;
            for (let i = 0; i < 8; i++) {
                // mapDirection8ToFlow4 collapses opposite directions into the
                // same bucket, so the offset here only needs to enumerate all
                // 8 directions; the exact phase doesn't affect flowDir.
                const relative = (this.last + i + 8) % 8;
                const flowDir = mapDirection8ToFlow4(relative);
                const strength = getFlowStrength(current.x, current.y, flowDir);
                flowBiases.push(strength);
                totalFlowBias += strength;
            }

            const attemptedFlowChoices = new Set();
            let foundValidCell = false;
            let attempts = 0;
            const maxAttempts = 50;

            while (directionModifiers.length && !foundValidCell && attempts < maxAttempts) {
                attempts++;
                let directionChoice;
                let useFlow = totalFlowBias > 0 && rnd() < params.flowInfluence;

                if (useFlow) {
                    directionChoice = pickFlowDirection(flowBiases, attemptedFlowChoices);
                    if (directionChoice === null) useFlow = false;
                }

                if (!useFlow) {
                    const idx = pickModifierIndex(
                        directionModifiers, this.last, current, this.grid,
                    );
                    directionChoice = directionModifiers.splice(idx, 1)[0];
                }

                const directionIndex = (this.last + directionChoice + 8) % 8;
                if (diagonalVetoed(directionIndex)) continue;
                if (isSharpCorner(this.last, directionIndex)) continue;
                const [dx, dy] = DIRS[directionIndex];
                const nx = current.x + dx;
                const ny = current.y + dy;

                if (nx <= 0 || nx >= this.gridWidth - 1 || ny <= 0 || ny >= this.gridHeight - 1) continue;

                const next = this.grid[nx][ny];
                if (!next.available) continue;
                if (!isValidDiagonalMove(directionIndex, nx, ny, this.grid)) continue;
                if (this.touchesSelf(next, own, keyOf)) continue;

                this.cells.push(next);
                own.add(keyOf(next));
                next.available = false;
                next.heading = directionIndex;
                foundValidCell = true;
                this.last = (this.last + directionChoice + 8) % 8;
            }

            if (!foundValidCell) break;
        }

        sanitizePathRightAngles(this.cells, this.grid, this.gridWidth, this.gridHeight);
    }

    // True if `next` would sit 8-adjacent to part of this wire other than its
    // last two cells. The head (current) is always adjacent to `next`, and the
    // cell before it must stay legal too -- otherwise staircases and gentle
    // bends would be rejected. Contact with anything further back means the
    // trace is bending around to meet itself, i.e. forming a loop, so we veto.
    touchesSelf(next, own, keyOf) {
        const n = this.cells.length;
        const exemptHead = keyOf(this.cells[n - 1]);
        const exemptPrev = n >= 2 ? keyOf(this.cells[n - 2]) : -1;
        for (let i = 0; i < 8; i++) {
            const [dx, dy] = DIRS[i];
            const col = this.grid[next.x + dx];
            if (!col) continue;
            const nb = col[next.y + dy];
            if (!nb) continue;
            const k = keyOf(nb);
            if (k === exemptHead || k === exemptPrev) continue;
            if (own.has(k)) return true;
        }
        return false;
    }

    render(canvas, ctx) {
        const cw = canvas.width / this.gridWidth;
        const ch = canvas.height / this.gridHeight;
        const r = params.cellSize / 4;

        // A user-edited wire renders from its sparse corner polyline; everyone
        // else renders the dense per-cell path. Both are just lists of grid
        // coordinates, so the draw loop is identical.
        const pts = this.points || this.cells;

        ctx.beginPath();
        ctx.strokeStyle = params.fgColor;
        ctx.lineWidth = params.cellSize * (this.strokeScale ?? 0.25);
        ctx.fillStyle = 'transparent';
        for (let i = 0; i < pts.length; i++) {
            const c = pts[i];
            const x = (c.x + 0.5) * cw;
            const y = (c.y + 0.5) * ch;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        ctx.fillStyle = params.bgColor;
        ctx.strokeStyle = params.fgColor;
        ctx.lineWidth = params.cellSize / 6;

        const drawPad = (cell) => {
            const x = (cell.x + 0.5) * cw;
            const y = (cell.y + 0.5) * ch;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2, false);
            ctx.fill();
            ctx.stroke();
        };
        // QFP pin wires inherit their visual endpoint from the pin tab on the
        // chip body, so a pad at the start would just create a donut between
        // the tab and the trace. Bus / router traces terminate off the canvas or
        // merge into a channel, so a pad on either end would read as "this is a
        // via" rather than "this wire continues". Everyone else gets pads at both ends.
        const noPads = this.noPads || this.isBus;
        if (!noPads && !this.isQFPPin) drawPad(pts[0]);
        if (!noPads) drawPad(pts[pts.length - 1]);
    }
}

// Reserve a straight run of cells starting at (and including) `start`, stepping
// in DIRS direction `heading` for up to `maxLen` further cells. Each reserved
// cell is marked unavailable so nothing else can claim it. Stops at the first
// out-of-bounds or already-occupied cell. Returns the run (always at least
// `[start]`).
//
// Used to give every QFP pin a guaranteed escape lead before any wire is grown,
// so a sibling pin's wandering trace can't starve the corridor a later pin needs
// to reach the board -- which is what otherwise leaves pins stranded as a bare
// pad against the chip body.
function directionBetweenCells(a, b) {
    const dx = Math.sign(b.x - a.x);
    const dy = Math.sign(b.y - a.y);
    for (let d = 0; d < 8; d++) {
        if (DIRS[d][0] === dx && DIRS[d][1] === dy) return d;
    }
    return 1;
}

function cellStepAdjacent(ax, ay, bx, by) {
    const dx = Math.abs(ax - bx);
    const dy = Math.abs(ay - by);
    return (dx === 1 || dy === 1) && dx <= 1 && dy <= 1 && (dx + dy) > 0;
}

function cellOnWire(x, y, cells) {
    return cells.some((c) => c.x === x && c.y === y);
}

function cellUsableForWire(x, y, grid, gridWidth, gridHeight, cells) {
    if (x <= 0 || x >= gridWidth - 1 || y <= 0 || y >= gridHeight - 1) return false;
    const cell = grid[x][y];
    return cell.available || cellOnWire(x, y, cells);
}

// Short BFS detour (obtuse corners only) when a one-step chamfer cell is blocked.
function microPathChamfer(cur, next, fromDir, grid, gridWidth, gridHeight, cells) {
    const maxDepth = 4;
    const queue = [{ x: cur.x, y: cur.y, dir: fromDir, path: [] }];
    const seen = new Set();

    while (queue.length > 0) {
        const node = queue.shift();
        const key = `${node.x},${node.y},${node.dir},${node.path.length}`;
        if (seen.has(key)) continue;
        seen.add(key);

        if (node.path.length > maxDepth) continue;

        for (let i = 0; i < 8; i++) {
            if (node.path.length === 0) {
                if (isSharpCorner(node.dir, i)) continue;
            } else {
                const inDir = node.path[node.path.length - 1].stepDir;
                if (isSharpCorner(inDir, i)) continue;
            }

            const nx = node.x + DIRS[i][0];
            const ny = node.y + DIRS[i][1];
            if (!cellUsableForWire(nx, ny, grid, gridWidth, gridHeight, cells)) continue;

            const step = { x: nx, y: ny, stepDir: i };
            const path = node.path.concat(step);

            if (cellStepAdjacent(nx, ny, next.x, next.y)) {
                const outDir = directionBetween(step, next);
                if (!isSharpCorner(i, outDir)) {
                    return path.map((p) => ({
                        cell: grid[p.x][p.y],
                        stepDir: p.stepDir,
                        inPath: cellOnWire(p.x, p.y, cells),
                    }));
                }
            }

            queue.push({ x: nx, y: ny, dir: i, path });
        }
    }
    return null;
}

// Build 1–2 insert cells between cur and next that chamfer a sharp corner; null if blocked.
function chamferInsertCells(cur, next, fromDir, toDir, grid, gridWidth, gridHeight, cells) {
    const steps = chamferDirsForCorner(fromDir, toDir);
    if (!steps.length) return null;

    const chain = [{ x: cur.x, y: cur.y }];
    for (const stepDir of steps) {
        const tail = chain[chain.length - 1];
        const x = tail.x + DIRS[stepDir][0];
        const y = tail.y + DIRS[stepDir][1];
        if (x <= 0 || x >= gridWidth - 1 || y <= 0 || y >= gridHeight - 1) return null;
        chain.push({ x, y, stepDir });
    }

    const last = chain[chain.length - 1];
    if (!cellStepAdjacent(last.x, last.y, next.x, next.y)) return null;

    const outDir = directionBetween(last, next);
    const lastStepDir = steps[steps.length - 1];
    if (isSharpCorner(lastStepDir, outDir)) return null;

    for (let k = 1; k < chain.length; k++) {
        const a = chain[k - 1];
        const b = chain[k];
        if (!cellStepAdjacent(a.x, a.y, b.x, b.y)) return null;
    }

    const out = [];
    for (let k = 1; k < chain.length; k++) {
        const { x, y, stepDir } = chain[k];
        const cell = grid[x][y];
        const inPath = cellOnWire(x, y, cells);
        if (!cell.available && !inPath) return null;
        out.push({ cell, stepDir, inPath });
    }
    return out;
}

function tryBothChamfers(cur, next, fromDir, toDir, grid, gridWidth, gridHeight, cells) {
    const insert = chamferInsertCells(
        cur, next, fromDir, toDir, grid, gridWidth, gridHeight, cells,
    );
    if (insert?.length) return insert;
    return microPathChamfer(cur, next, fromDir, grid, gridWidth, gridHeight, cells);
}

// BFS from prev to next, obtuse corners only, when a single chamfer insert is blocked.
function obtuseBridgePrevNext(prev, next, inDir, grid, gridWidth, gridHeight, cells, avoid) {
    const maxDepth = 10;
    const queue = [{ x: prev.x, y: prev.y, dir: inDir, path: [] }];
    const seen = new Set();

    while (queue.length > 0) {
        const node = queue.shift();
        const key = `${node.x},${node.y},${node.dir},${node.path.length}`;
        if (seen.has(key)) continue;
        seen.add(key);

        if (node.path.length > maxDepth) continue;

        for (let i = 0; i < 8; i++) {
            const stepDir = node.path.length === 0
                ? i
                : node.path[node.path.length - 1].stepDir;
            const from = node.path.length === 0 ? node.dir : stepDir;
            if (from >= 0 && isSharpCorner(from, i)) continue;

            const nx = node.x + DIRS[i][0];
            const ny = node.y + DIRS[i][1];
            if (avoid && nx === avoid.x && ny === avoid.y) continue;
            if (!cellUsableForWire(nx, ny, grid, gridWidth, gridHeight, cells)) continue;

            const step = { x: nx, y: ny, stepDir: i };
            const path = node.path.concat(step);

            if (cellStepAdjacent(nx, ny, next.x, next.y)) {
                const outDir = directionBetween(step, next);
                if (!isSharpCorner(i, outDir)) {
                    return path.map((p) => ({
                        cell: grid[p.x][p.y],
                        stepDir: p.stepDir,
                        inPath: cellOnWire(p.x, p.y, cells),
                    }));
                }
            }

            queue.push({ x: nx, y: ny, dir: i, path });
        }
    }
    return null;
}

function applyInsertCells(cells, index, insert) {
    for (let j = 0; j < insert.length; j++) {
        const { cell, stepDir, inPath } = insert[j];
        cells.splice(index + 1 + j, 0, cell);
        if (!inPath) {
            cell.available = false;
            cell.heading = stepDir;
        }
    }
}

// Replace corners ≤ 90° with 45° chamfer steps when a valid local detour exists.
export function sanitizePathRightAngles(cells, grid, gridWidth, gridHeight) {
    if (cells.length < 3) return cells;

    let i = 1;
    let guard = 0;
    const guardMax = cells.length * 16;
    while (i < cells.length - 1 && guard++ < guardMax) {
        const prev = cells[i - 1];
        const cur = cells[i];
        const next = cells[i + 1];
        if (prev.x === cur.x && prev.y === cur.y) {
            cells.splice(i, 1);
            continue;
        }
        if (cur.x === next.x && cur.y === next.y) {
            cells.splice(i + 1, 1);
            continue;
        }

        const fromDir = directionBetweenCells(prev, cur);
        const toDir = directionBetweenCells(cur, next);
        if (!isSharpCorner(fromDir, toDir)) {
            i++;
            continue;
        }

        const insert = tryBothChamfers(
            cur, next, fromDir, toDir, grid, gridWidth, gridHeight, cells,
        );
        if (insert?.length) {
            applyInsertCells(cells, i, insert);
            continue;
        }

        const inDir = i >= 2 ? directionBetweenCells(cells[i - 2], prev) : -1;
        const bridge = obtuseBridgePrevNext(
            prev, next, inDir, grid, gridWidth, gridHeight, cells, cur,
        );
        if (bridge?.length) {
            cells.splice(i, 1, ...bridge.map((b) => b.cell));
            for (const { cell, stepDir, inPath } of bridge) {
                if (!inPath) {
                    cell.available = false;
                    cell.heading = stepDir;
                }
            }
            continue;
        }

        if (cellStepAdjacent(prev.x, prev.y, next.x, next.y)) {
            const skipDir = directionBetweenCells(prev, next);
            const outDir = i + 2 < cells.length
                ? directionBetweenCells(next, cells[i + 2])
                : -1;
            const inOk = inDir < 0 || !isSharpCorner(inDir, skipDir);
            const outOk = outDir < 0 || !isSharpCorner(skipDir, outDir);
            if (inOk && outOk) {
                cells.splice(i, 1);
                continue;
            }
        }

        i++;
    }

    return cells;
}

// 45° step along the chip edge toward the partner (NE/NW on top edge, etc.).
export function edgeFanDir(pinHeading, tipX, tipY, towardX, towardY) {
    const dx = towardX - tipX;
    const dy = towardY - tipY;
    if (pinHeading === 1) return dx > 0 ? 2 : 0;
    if (pinHeading === 5) return dx > 0 ? 4 : 6;
    if (pinHeading === 3) return dy > 0 ? 4 : 2;
    if (pinHeading === 7) return dy > 0 ? 6 : 0;
    return pinHeading;
}

export function leadExitDir(lead) {
    if (lead.length < 2) return -1;
    return directionBetweenCells(lead[lead.length - 2], lead[lead.length - 1]);
}

// Straight escape stub, then one 45° fan step along the bus when that step is ±45° from the stub.
export function carveLeadWithFan(start, heading, maxLen, towardX, towardY, grid, gridWidth, gridHeight) {
    const lead = carveLead(start, heading, maxLen, grid, gridWidth, gridHeight);
    if (lead.length < 2) return lead;

    const tip = lead[lead.length - 1];
    const fanDir = edgeFanDir(heading, tip.x, tip.y, towardX, towardY);
    const delta = (fanDir - heading + 8) % 8;
    if (delta !== 1 && delta !== 7) return lead;

    const [dx, dy] = DIRS[fanDir];
    const nx = tip.x + dx;
    const ny = tip.y + dy;
    if (nx <= 0 || nx >= gridWidth - 1 || ny <= 0 || ny >= gridHeight - 1) return lead;

    const fanCell = grid[nx][ny];
    if (!fanCell.available) return lead;

    fanCell.available = false;
    fanCell.heading = fanDir;
    lead.push(fanCell);
    return lead;
}

export function carveLead(start, heading, maxLen, grid, gridWidth, gridHeight) {
    const cells = [start];
    let cur = start;
    for (let i = 0; i < maxLen; i++) {
        const [dx, dy] = DIRS[heading];
        const nx = cur.x + dx;
        const ny = cur.y + dy;
        if (nx <= 0 || nx >= gridWidth - 1 || ny <= 0 || ny >= gridHeight - 1) break;
        const next = grid[nx][ny];
        if (!next.available) break;
        next.available = false;
        next.heading = heading;
        cells.push(next);
        cur = next;
    }
    return cells;
}

// Cardinally-adjacent endpoints from two fill wires get fused into a single
// longer wire, repeatedly, until no more joins are possible. QFP pin wires are
// left alone -- their endpoint semantics are load-bearing.
//
// Cardinal-only adjacency keeps the merge guaranteed-safe: the new segment is
// always one full step along a grid axis, which can never visually slice across
// a third wire (the way a diagonal merge could).
export function joinAdjacentWires(wires) {
    let changed = true;
    while (changed) {
        changed = false;
        outer: for (let i = 0; i < wires.length; i++) {
            const a = wires[i];
            if (a.isQFPPin) continue;
            for (let j = 0; j < wires.length; j++) {
                if (i === j) continue;
                const b = wires[j];
                if (b.isQFPPin) continue;

                const merged = tryMergeCells(
                    a.cells, b.cells, a.grid, a.gridWidth, a.gridHeight,
                );
                if (merged) {
                    a.cells = merged;
                    wires.splice(j, 1);
                    changed = true;
                    break outer;
                }
            }
        }
    }
}

function tryMergeCells(aCells, bCells, grid, gridWidth, gridHeight) {
    const aStart = aCells[0];
    const aEnd = aCells[aCells.length - 1];
    const bStart = bCells[0];
    const bEnd = bCells[bCells.length - 1];
    let merged = null;
    if (cardinalAdjacent(aEnd, bStart)) merged = aCells.concat(bCells);
    else if (cardinalAdjacent(aEnd, bEnd)) merged = aCells.concat(bCells.slice().reverse());
    else if (cardinalAdjacent(aStart, bStart)) merged = aCells.slice().reverse().concat(bCells);
    else if (cardinalAdjacent(aStart, bEnd)) merged = bCells.concat(aCells);
    if (!merged) return null;
    sanitizePathRightAngles(merged, grid, gridWidth, gridHeight);
    return merged;
}

function cardinalAdjacent(c1, c2) {
    return Math.abs(c1.x - c2.x) + Math.abs(c1.y - c2.y) === 1;
}

// Decide which entry of `directionModifiers` to consume. With probability
// `params.collectiveness`, prefer the modifier whose resulting direction is
// most represented among the current cell's occupied neighbors (i.e. the
// direction local traces are already flowing in) -- this is what gives the
// bus-following look. Otherwise fall back to the original straightness pick.
function pickModifierIndex(directionModifiers, last, current, grid) {
    const len = directionModifiers.length;

    // Layer 1: collectiveness (local context wins when it has something to say)
    if (params.collectiveness > 0 && rnd() < params.collectiveness) {
        let bestCount = 0;
        const bestIdxs = [];
        for (let i = 0; i < len; i++) {
            const dirIdx = (last + directionModifiers[i] + 8) % 8;
            const matches = countNeighborsWithHeading(grid, current, dirIdx);
            if (matches > bestCount) {
                bestCount = matches;
                bestIdxs.length = 0;
                bestIdxs.push(i);
            } else if (matches === bestCount && matches > 0) {
                bestIdxs.push(i);
            }
        }
        if (bestCount > 0) return bestIdxs[rndInt(bestIdxs.length)];
    }

    // Layer 2: directionality (global axis bias)
    const dirBias = params.directionality;
    if (dirBias !== 0 && rnd() < Math.abs(dirBias)) {
        const wantSign = dirBias > 0 ? 1 : -1;
        const matching = [];
        for (let i = 0; i < len; i++) {
            const dirIdx = (last + directionModifiers[i] + 8) % 8;
            if (horizontalScore(dirIdx) === wantSign) matching.push(i);
        }
        if (matching.length) return matching[rndInt(matching.length)];
    }

    // Layer 3: straightness (default)
    return Math.floor(Math.pow(rnd(), params.straightness) * len);
}

function countNeighborsWithHeading(grid, current, heading) {
    let count = 0;
    for (let i = 0; i < 8; i++) {
        const [dx, dy] = DIRS[i];
        const col = grid[current.x + dx];
        if (!col) continue;
        const n = col[current.y + dy];
        if (n && !n.available && n.heading === heading) count++;
    }
    return count;
}

function pickFlowDirection(flowBiases, attemptedFlowChoices) {
    const validBiases = [];
    const validChoices = [];
    let validTotal = 0;
    for (let i = 0; i < 8; i++) {
        const modifier = i - 4;
        const key = String(modifier);
        if (attemptedFlowChoices.has(key)) continue;
        validBiases.push(flowBiases[i]);
        validChoices.push(modifier);
        validTotal += flowBiases[i];
    }
    if (validTotal === 0) return null;

    const r = rndInt(validTotal);
    let acc = 0;
    for (let i = 0; i < validChoices.length; i++) {
        acc += validBiases[i];
        if (r < acc) {
            const choice = validChoices[i];
            attemptedFlowChoices.add(String(choice));
            return choice;
        }
    }
    return null;
}

// Diagonal moves are only allowed when one of the two orthogonal cells they
// "cut across" is still free — otherwise the diagonal would visually cross
// another wire.
function isValidDiagonalMove(directionIndex, x, y, grid) {
    if (directionIndex === 0) return grid[x + 1][y].available || grid[x][y + 1].available;
    if (directionIndex === 2) return grid[x - 1][y].available || grid[x][y + 1].available;
    if (directionIndex === 4) return grid[x - 1][y].available || grid[x][y - 1].available;
    if (directionIndex === 6) return grid[x + 1][y].available || grid[x][y - 1].available;
    return true;
}

function findRandomAvailableDirection(x, y, grid, gridWidth, gridHeight) {
    const dirBias = params.directionality;
    const biased = dirBias !== 0 && rnd() < Math.abs(dirBias);

    if (biased) {
        const wantSign = dirBias > 0 ? 1 : -1;
        const preferred = [0, 1, 2, 3, 4, 5, 6, 7].filter(
            (d) => horizontalScore(d) === wantSign,
        );
        const found = tryDirectionList(preferred, x, y, grid, gridWidth, gridHeight);
        if (found !== -1) return found;
    }

    const all = [0, 1, 2, 3, 4, 5, 6, 7];
    const found = tryDirectionList(all, x, y, grid, gridWidth, gridHeight);
    return found !== -1 ? found : 1;
}

function tryDirectionList(candidates, x, y, grid, gridWidth, gridHeight) {
    const list = candidates.slice();
    while (list.length) {
        const idx = rndInt(list.length);
        const directionIndex = list.splice(idx, 1)[0];
        if (diagonalVetoed(directionIndex)) continue;
        const [dx, dy] = DIRS[directionIndex];
        const nx = x + dx;
        const ny = y + dy;
        if (nx > 0 && nx < gridWidth - 1 && ny > 0 && ny < gridHeight - 1 && grid[nx][ny].available) {
            return directionIndex;
        }
    }
    return -1;
}
