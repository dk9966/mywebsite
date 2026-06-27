export function renderCanvas(canvas, model, config, options = {}) {
    const styleName = options.style ?? config.defaultStyle;
    const style = config.styles[styleName] ?? config.styles[config.defaultStyle];
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = model.width * dpr;
    canvas.height = model.height * dpr;
    canvas.style.aspectRatio = `${model.width} / ${model.height}`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = style.bg;
    ctx.fillRect(0, 0, model.width, model.height);
    ctx.shadowColor = style.fg;
    ctx.shadowBlur = style.glowBlur;

    for (const trace of model.traces) drawTrace(ctx, trace, style);
    for (const via of model.vias) drawVia(ctx, via, config, style);
    for (const part of model.parts) drawPart(ctx, part, style);
}

function drawTrace(ctx, trace, style) {
    if (trace.points.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(trace.points[0].x, trace.points[0].y);
    for (const point of trace.points.slice(1)) ctx.lineTo(point.x, point.y);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = trace.kind === 'bus' ? style.traceWidth : style.traceWidth * 0.86;
    ctx.stroke();
}

function drawVia(ctx, via, config, style) {
    ctx.fillStyle = style.bg;
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.pinWidth;
    ctx.beginPath();
    ctx.arc(via.x, via.y, config.vias.ringR, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = style.fg;
    ctx.globalAlpha = 0.72;
    ctx.beginPath();
    ctx.arc(via.x, via.y, config.vias.dotR, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
}

function drawPart(ctx, part, style) {
    if (['qfp', 'ic', 'busBlock', 'padCluster'].includes(part.kind)) {
        drawHalo(ctx, part, style);
    }
    drawPins(ctx, part, style);
    if (part.kind === 'padCluster') {
        drawRect(ctx, part, style, 8);
        for (const pin of part.pins) drawRoundPad(ctx, pin, style);
        return;
    }
    drawRect(ctx, part, style, part.kind === 'ic' ? 8 : part.kind === 'capacitor' ? 10 : 3);
    if (part.kind === 'qfp') {
        drawInsetRect(ctx, part, style);
    } else if (part.kind === 'busBlock') {
        drawBusLines(ctx, part, style);
    } else if (part.kind === 'resistor') {
        ctx.strokeStyle = style.dim;
        ctx.lineWidth = style.pinWidth;
        ctx.beginPath();
        ctx.moveTo(part.x + 5, part.y + part.h / 2);
        ctx.lineTo(part.x + part.w - 5, part.y + part.h / 2);
        ctx.stroke();
    }
}

function drawHalo(ctx, part, style) {
    const offset = part.kind === 'qfp' ? 14 : 10;
    const corner = part.kind === 'qfp' ? 18 : 12;
    const x = part.x - offset;
    const y = part.y - offset;
    const width = part.w + offset * 2;
    const height = part.h + offset * 2;
    const c = Math.min(corner, width / 3, height / 3);

    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.traceWidth * 0.9;
    ctx.beginPath();
    ctx.moveTo(x + c, y);
    ctx.lineTo(x + width - c, y);
    ctx.lineTo(x + width, y + c);
    ctx.lineTo(x + width, y + height - c);
    ctx.lineTo(x + width - c, y + height);
    ctx.lineTo(x + c, y + height);
    ctx.lineTo(x, y + height - c);
    ctx.lineTo(x, y + c);
    ctx.closePath();
    ctx.stroke();
}

function drawRect(ctx, part, style, radius) {
    ctx.fillStyle = style.bg;
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.partWidth;
    roundedRect(ctx, part.x, part.y, part.w, part.h, radius);
    ctx.fill();
    ctx.stroke();
}

function drawInsetRect(ctx, part, style) {
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.partWidth * 0.8;
    roundedRect(ctx, part.x + 14, part.y + 14, part.w - 28, part.h - 28, 3);
    ctx.stroke();
}

function drawBusLines(ctx, part, style) {
    const count = part.lanes ?? 7;
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.pinWidth;
    for (let i = 1; i <= count; i++) {
        const t = i / (count + 1);
        ctx.beginPath();
        if (part.vertical) {
            ctx.moveTo(part.x + part.w * t, part.y + 10);
            ctx.lineTo(part.x + part.w * t, part.y + part.h - 10);
        } else {
            ctx.moveTo(part.x + 10, part.y + part.h * t);
            ctx.lineTo(part.x + part.w - 10, part.y + part.h * t);
        }
        ctx.stroke();
    }
}

function drawRoundPad(ctx, pin, style) {
    ctx.fillStyle = style.bg;
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.pinWidth;
    ctx.beginPath();
    ctx.arc(pin.x, pin.y, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = style.fg;
    ctx.globalAlpha = 0.66;
    ctx.beginPath();
    ctx.arc(pin.x, pin.y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
}

function drawPins(ctx, part, style) {
    ctx.strokeStyle = style.fg;
    ctx.lineWidth = style.pinWidth;
    for (const pin of part.pins) {
        ctx.beginPath();
        ctx.moveTo(pin.x, pin.y);
        if (pin.side === 'top') ctx.lineTo(pin.x, part.y);
        else if (pin.side === 'bottom') ctx.lineTo(pin.x, part.y + part.h);
        else if (pin.side === 'left') ctx.lineTo(part.x, pin.y);
        else if (pin.side === 'right') ctx.lineTo(part.x + part.w, pin.y);
        else continue;
        ctx.stroke();
    }
}

function roundedRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
}

