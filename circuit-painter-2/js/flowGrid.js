// Flow grid: 4 directions x 8 bits packed into one Uint32 per cell.
// 0 = vertical, 1 = horizontal, 2 = diagonal TL-BR, 3 = diagonal BL-TR.

let flowGrid = [];
let gridWidth = 0;
let gridHeight = 0;

// Map an 8-direction index to one of the 4 flow buckets above.
export function mapDirection8ToFlow4(dir8) {
    if (dir8 === 1 || dir8 === 5) return 0; // vertical
    if (dir8 === 3 || dir8 === 7) return 1; // horizontal
    if (dir8 === 0 || dir8 === 4) return 2; // TL-BR diagonal
    if (dir8 === 2 || dir8 === 6) return 3; // BL-TR diagonal
    return 0;
}

export function initFlowGrid(width, height) {
    const old = flowGrid;
    gridWidth = width;
    gridHeight = height;
    flowGrid = [];
    for (let x = 0; x < gridWidth; x++) {
        flowGrid[x] = [];
        for (let y = 0; y < gridHeight; y++) {
            flowGrid[x][y] = old[x] && old[x][y] !== undefined ? old[x][y] : 0;
        }
    }
}

export function resetFlowGrid() {
    for (let x = 0; x < gridWidth; x++) {
        if (!flowGrid[x]) continue;
        for (let y = 0; y < gridHeight; y++) flowGrid[x][y] = 0;
    }
}

export function getFlowStrength(x, y, flowDir) {
    if (!flowGrid[x] || flowGrid[x][y] === undefined) return 0;
    return (flowGrid[x][y] >> (flowDir * 8)) & 0xff;
}

export function addFlowStrength(x, y, flowDir, amount) {
    if (!flowGrid[x] || flowGrid[x][y] === undefined) flowGrid[x][y] = 0;
    const shift = flowDir * 8;
    const current = (flowGrid[x][y] >> shift) & 0xff;
    const next = Math.min(255, current + amount);
    flowGrid[x][y] = (flowGrid[x][y] & ~(0xff << shift)) | (next << shift);
}

export function subFlowStrength(x, y, flowDir, amount) {
    if (!flowGrid[x] || flowGrid[x][y] === undefined) return;
    const shift = flowDir * 8;
    const current = (flowGrid[x][y] >> shift) & 0xff;
    const next = Math.max(0, current - amount);
    flowGrid[x][y] = (flowGrid[x][y] & ~(0xff << shift)) | (next << shift);
}

export function drawFlowOverlay(canvas, ctx, params) {
    if (!params.showFlowField) return;

    const sx = (1 + canvas.width / params.cellSize) / gridWidth;
    const sy = (1 + canvas.height / params.cellSize) / gridHeight;
    const cw = params.cellSize * sx;
    const ch = params.cellSize * sy;

    for (let x = 0; x < gridWidth; x++) {
        for (let y = 0; y < gridHeight; y++) {
            const value = flowGrid[x] && flowGrid[x][y] !== undefined ? flowGrid[x][y] : 0;
            if (value === 0) continue;

            const cx = (x + 0.5) * cw;
            const cy = (y + 0.5) * ch;
            const len = params.cellSize * 0.8;

            for (let flowDir = 0; flowDir < 4; flowDir++) {
                const strength = (value >> (flowDir * 8)) & 0xff;
                if (strength === 0) continue;

                const opacity = strength / 255;
                ctx.strokeStyle = `rgba(204, 153, 153, ${opacity})`;
                ctx.lineWidth = opacity * 3 + 0.5;

                ctx.beginPath();
                if (flowDir === 0) {
                    ctx.moveTo(cx, cy - len / 2);
                    ctx.lineTo(cx, cy + len / 2);
                } else if (flowDir === 1) {
                    ctx.moveTo(cx - len / 2, cy);
                    ctx.lineTo(cx + len / 2, cy);
                } else {
                    const offset = (len / 2) * (Math.SQRT2 / 2);
                    if (flowDir === 2) {
                        ctx.moveTo(cx - offset, cy - offset);
                        ctx.lineTo(cx + offset, cy + offset);
                    } else {
                        ctx.moveTo(cx - offset, cy + offset);
                        ctx.lineTo(cx + offset, cy - offset);
                    }
                }
                ctx.stroke();
            }
        }
    }
}
