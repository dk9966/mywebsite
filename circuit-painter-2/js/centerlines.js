// Medial-axis centerlines — rendering wrapper around shared corridorGeom.

import { params } from './params.js';
import { getObstacles } from './obstacles.js';
import { computeCenterlinePolylines } from '../../circuit-painter/js/corridorGeom.js';

function corridorCfg() {
    return {
        obstacles: getObstacles(),
        obstaclesEnabled: params.obstaclesEnabled,
        obstacleKeepOut: params.obstacleKeepOut,
        centerlineMinLength: params.centerlineMinLength,
        centerlineSimplify: params.centerlineSimplify,
    };
}

export function computeCenterlines(gridWidth, gridHeight) {
    return computeCenterlinePolylines(gridWidth, gridHeight, corridorCfg());
}

// Faint dashed guide so the medial axis is distinguishable from the traces
// it shapes when both are shown at once.
export function drawCenterlines(canvas, ctx, gridWidth, gridHeight, polylines) {
    if (!polylines.length) return;

    const sx = (1 + canvas.width / params.cellSize) / gridWidth;
    const sy = (1 + canvas.height / params.cellSize) / gridHeight;
    const cw = params.cellSize * sx;
    const ch = params.cellSize * sy;

    ctx.save();
    ctx.beginPath();
    ctx.strokeStyle = params.fgColor;
    ctx.globalAlpha = 0.4;
    ctx.lineWidth = Math.max(1, params.cellSize / 8);
    ctx.setLineDash([params.cellSize * 0.6, params.cellSize * 0.6]);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    for (const poly of polylines) {
        for (let i = 0; i < poly.length; i++) {
            const x = (poly[i][0] + 0.5) * cw;
            const y = (poly[i][1] + 0.5) * ch;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    ctx.restore();
}
