// Cell + Wire: greedy random walk that picks the next direction biased toward
// "go straight" (params.straightness) and toward whatever has been painted into
// the flow grid (params.flowInfluence). Obstacles are handled outside by simply
// marking their cells as unavailable; this module doesn't need to know about them.

import { rnd, rndInt } from './rng.js';
import { mapDirection8ToFlow4, getFlowStrength } from './flowGrid.js';
import { params } from './params.js';

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

// Heading changes of two DIRS steps (in either rotational direction) are 90
// degree corners; one step is a 45 degree bend, zero is straight. params
// .turnSmoothness is the probability such a right-angle step gets vetoed, so
// the walker falls back to a gentler turn instead.
function rightAngleVetoed(fromDir, toDir) {
    const delta = (toDir - fromDir + 8) % 8;
    return (delta === 2 || delta === 6) && rnd() < params.turnSmoothness;
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
        // forward heading). modifier = 0 keeps that heading, ±1 turns 45°,
        // ±2 turns 90°. Callers that seed a wire (QFP pins) pass the direction
        // they want the wire to grow toward.
        this.last = initialHeading !== null
            ? initialHeading
            : findRandomAvailableDirection(start.x, start.y, grid, gridWidth, gridHeight);
        // Wires born as QFP pin stubs always render, regardless of cutOffLength
        // and prioritizeLongWires. The flag is set by the caller after build.
        this.isQFPPin = false;
        // Edge-to-edge "trunk" wires laid by pathfind.js. Both endpoints sit on
        // the canvas border, so we skip the end pads -- they should look like
        // traces running off the board, not terminating at a via.
        this.isTrunk = false;
        // Bus lines (bus.js) are straight parallel traces with 45 degree tails,
        // built by setting .cells directly. They render as continuous traces
        // with no end pads.
        this.isBus = false;
        // Router routes (router.js): A* paths between anchors. They always
        // render (no cutOffLength / trunksOnly gating), carry no end pads
        // (noPads), and may set strokeScale for the length-based taper.
        this.isRoute = false;
        this.noPads = false;
        // When set, overrides the default stroke width as a fraction of
        // cellSize. null falls back to the default 0.25.
        this.strokeScale = null;
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
            // Modifier semantics: 0 = keep heading, ±1 = 45° turn (flips
            // cardinal<->diagonal parity), ±2 = 90° turn (preserves parity).
            // The expanded set is required whenever diagonals are suppressed,
            // directionality is active, or this is a QFP pin wire that may
            // need a 90° swing to escape a chip's immediate neighborhood.
            const needsRightAngles = this.isQFPPin
                || params.diagonalChance < 1
                || params.directionality !== 0;
            const directionModifiers = needsRightAngles
                ? (rnd() > 0.5 ? [0, 1, -1, 2, -2] : [0, -1, 1, -2, 2])
                : (rnd() > 0.5 ? [0, 1, -1] : [0, -1, 1]);

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
                if (rightAngleVetoed(this.last, directionIndex)) continue;
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
        const sx = (1 + canvas.width / params.cellSize) / this.gridWidth;
        const sy = (1 + canvas.height / params.cellSize) / this.gridHeight;
        const cw = params.cellSize * sx;
        const ch = params.cellSize * sy;
        const r = params.cellSize / 4;

        ctx.beginPath();
        ctx.strokeStyle = params.fgColor;
        ctx.lineWidth = params.cellSize * (this.strokeScale ?? 0.25);
        ctx.fillStyle = 'transparent';
        for (let i = 0; i < this.cells.length; i++) {
            const c = this.cells[i];
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
        // the tab and the trace. Trunk / bus / router traces terminate off the
        // canvas or merge into a channel, so a pad on either end would read as
        // "this is a via" rather than "this wire continues". Everyone else gets
        // pads at both ends.
        const noPads = this.noPads || this.isTrunk || this.isBus;
        if (!noPads && !this.isQFPPin) drawPad(this.cells[0]);
        if (!noPads) drawPad(this.cells[this.cells.length - 1]);
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
// longer wire, repeatedly, until no more joins are possible. QFP pin wires and
// trunk wires are left alone -- their endpoint semantics are part of what makes
// them read as "pin" or "off-board trunk", and joining would erase that.
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
            if (a.isQFPPin || a.isTrunk) continue;
            for (let j = 0; j < wires.length; j++) {
                if (i === j) continue;
                const b = wires[j];
                if (b.isQFPPin || b.isTrunk) continue;

                const merged = tryMergeCells(a.cells, b.cells);
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

function tryMergeCells(aCells, bCells) {
    const aStart = aCells[0];
    const aEnd = aCells[aCells.length - 1];
    const bStart = bCells[0];
    const bEnd = bCells[bCells.length - 1];
    if (cardinalAdjacent(aEnd, bStart)) return aCells.concat(bCells);
    if (cardinalAdjacent(aEnd, bEnd)) return aCells.concat(bCells.slice().reverse());
    if (cardinalAdjacent(aStart, bStart)) return aCells.slice().reverse().concat(bCells);
    if (cardinalAdjacent(aStart, bEnd)) return bCells.concat(aCells);
    return null;
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
