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
    }

    generate() {
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
                const [dx, dy] = DIRS[directionIndex];
                const nx = current.x + dx;
                const ny = current.y + dy;

                if (nx <= 0 || nx >= this.gridWidth - 1 || ny <= 0 || ny >= this.gridHeight - 1) continue;

                const next = this.grid[nx][ny];
                if (!next.available) continue;
                if (!isValidDiagonalMove(directionIndex, nx, ny, this.grid)) continue;

                this.cells.push(next);
                next.available = false;
                next.heading = directionIndex;
                foundValidCell = true;
                this.last = (this.last + directionChoice + 8) % 8;
            }

            if (!foundValidCell) break;
        }
    }

    render(canvas, ctx) {
        const sx = (1 + canvas.width / params.cellSize) / this.gridWidth;
        const sy = (1 + canvas.height / params.cellSize) / this.gridHeight;
        const cw = params.cellSize * sx;
        const ch = params.cellSize * sy;
        const r = params.cellSize / 4;

        ctx.beginPath();
        ctx.strokeStyle = params.fgColor;
        ctx.lineWidth = params.cellSize / 4;
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
        // the tab and the trace. Skip it for those; everyone else gets pads at
        // both ends.
        if (!this.isQFPPin) drawPad(this.cells[0]);
        drawPad(this.cells[this.cells.length - 1]);
    }
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
