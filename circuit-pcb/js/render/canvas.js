// Canvas renderer mirroring render/svg.js: same draw order, same primitives,
// same fillet radii (via ctx.arcTo). Intended for live website backgrounds.

export function render(ctx, model, config, { style: styleName } = {}) {
    const style = config.styles[styleName ?? config.defaultStyle];

    ctx.save();
    ctx.fillStyle = style.bg;
    ctx.fillRect(0, 0, model.width, model.height);

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.traceWidth;
    if (style.glowBlur > 0) {
        ctx.shadowColor = style.fg;
        ctx.shadowBlur = style.glowBlur * 2;
    }
    for (const t of model.traces) strokeTrace(ctx, t);

    for (const part of model.parts) {
        for (const p of part.prims) drawPrim(ctx, p, style);
    }

    for (const via of model.vias) {
        ctx.beginPath();
        if (via.ring) {
            ctx.arc(via.x, via.y, config.vias.ringR, 0, Math.PI * 2);
            ctx.fillStyle = style.bg;
            ctx.fill();
            ctx.lineWidth = 1.4;
            ctx.strokeStyle = style.fg;
            ctx.stroke();
        } else {
            ctx.arc(via.x, via.y, config.vias.dotR, 0, Math.PI * 2);
            ctx.fillStyle = style.fg;
            ctx.fill();
        }
    }
    ctx.restore();
}

function strokeTrace(ctx, t) {
    const pts = t.points;
    if (pts.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i + 1 < pts.length; i++) {
        const r = t.fillets[i];
        if (r > 0.1) ctx.arcTo(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], r);
        else ctx.lineTo(pts[i][0], pts[i][1]);
    }
    ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
    ctx.stroke();
}

function drawPrim(ctx, p, style) {
    ctx.beginPath();
    switch (p.t) {
        case 'rect':
            if (p.rx) ctx.roundRect(p.x, p.y, p.w, p.h, p.rx);
            else ctx.rect(p.x, p.y, p.w, p.h);
            break;
        case 'circle':
            ctx.arc(p.cx, p.cy, p.r, 0, Math.PI * 2);
            break;
        case 'line':
            ctx.moveTo(p.x1, p.y1);
            ctx.lineTo(p.x2, p.y2);
            ctx.lineWidth = p.sw;
            ctx.strokeStyle = style.fg;
            ctx.stroke();
            return;
        case 'poly':
            ctx.moveTo(p.pts[0][0], p.pts[0][1]);
            for (let i = 1; i < p.pts.length; i++) ctx.lineTo(p.pts[i][0], p.pts[i][1]);
            ctx.closePath();
            break;
        default:
            return;
    }
    if (p.fill) {
        ctx.fillStyle = style[p.fill];
        ctx.fill();
    }
    if (p.stroke) {
        ctx.lineWidth = p.sw;
        ctx.strokeStyle = style[p.stroke];
        ctx.stroke();
    }
}
