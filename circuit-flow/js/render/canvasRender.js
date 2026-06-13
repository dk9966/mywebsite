// Canvas renderer for a generated model: { chips, traces }. Pure with respect
// to its inputs -- main.js owns the canvas element, this just draws one frame.

function strokePolyline(ctx, points) {
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i][0], points[i][1]);
    ctx.stroke();
}

function chipColor(style, chip) {
    return chip.color === 'pink' ? style.chipPink : style.chipGreen;
}

function drawChip(ctx, style, chip) {
    ctx.strokeStyle = chipColor(style, chip);
    ctx.lineWidth = style.chipWidth;
    ctx.shadowColor = chipColor(style, chip);
    ctx.shadowBlur = 10;
    ctx.strokeRect(chip.x, chip.y, chip.w, chip.h);
    ctx.shadowBlur = 0;
}

function drawPins(ctx, style, chip) {
    ctx.strokeStyle = style.trace;
    ctx.lineWidth = style.traceWidth * 0.7;
    ctx.beginPath();
    for (const y of chip.pins.left) {
        ctx.moveTo(chip.x, y);
        ctx.lineTo(chip.x - style.pinLength, y);
    }
    for (const y of chip.pins.right) {
        ctx.moveTo(chip.x + chip.w, y);
        ctx.lineTo(chip.x + chip.w + style.pinLength, y);
    }
    ctx.stroke();
}

export function render(ctx, model, config) {
    const { style, board } = config;
    ctx.fillStyle = style.bg;
    ctx.fillRect(0, 0, board.width, board.height);

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Glow pass first so bright cores sit on top of every halo.
    ctx.strokeStyle = style.glow;
    ctx.lineWidth = style.glowWidth;
    for (const t of model.traces) strokePolyline(ctx, t.points);

    ctx.strokeStyle = style.trace;
    ctx.lineWidth = style.traceWidth;
    for (const t of model.traces) strokePolyline(ctx, t.points);

    for (const chip of model.chips) {
        drawPins(ctx, style, chip);
        drawChip(ctx, style, chip);
    }
}
