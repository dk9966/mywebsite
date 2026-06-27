export function modelToSvg(model, config, options = {}) {
    const styleName = options.style ?? config.defaultStyle;
    const style = config.styles[styleName] ?? config.styles[config.defaultStyle];
    const glowId = `roadGlow-${styleName}`;
    const traceEls = model.traces.map((trace) => tracePath(trace, style, glowId)).join('\n');
    const viaEls = model.vias.map((via) => viaShape(via, config, style, glowId)).join('\n');
    const partEls = model.parts.map((part) => partShape(part, style, glowId)).join('\n');

    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${model.width}" height="${model.height}" viewBox="0 0 ${model.width} ${model.height}">
  <defs>
    <filter id="${glowId}" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="${style.glowBlur}" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="${style.bg}"/>
  <g filter="url(#${glowId})" stroke-linecap="round" stroke-linejoin="round">
${traceEls}
${viaEls}
${partEls}
  </g>
</svg>
`;
}

function tracePath(trace, style) {
    const d = trace.points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${fmt(point.x)} ${fmt(point.y)}`).join(' ');
    const width = trace.kind === 'bus' ? style.traceWidth : style.traceWidth * 0.86;
    return `    <path d="${d}" fill="none" stroke="${style.fg}" stroke-width="${width}"/>`;
}

function viaShape(via, config, style) {
    return [
        `    <circle cx="${fmt(via.x)}" cy="${fmt(via.y)}" r="${config.vias.ringR}" fill="${style.bg}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`,
        `    <circle cx="${fmt(via.x)}" cy="${fmt(via.y)}" r="${config.vias.dotR}" fill="${style.fg}" opacity="0.72"/>`,
    ].join('\n');
}

function partShape(part, style) {
    if (part.kind === 'qfp') return qfpShape(part, style);
    if (part.kind === 'ic') return icShape(part, style);
    if (part.kind === 'busBlock') return busBlockShape(part, style);
    if (part.kind === 'padCluster') return padClusterShape(part, style);
    return passiveShape(part, style);
}

function qfpShape(part, style) {
    return [
        haloShape(part, style, 14, 18),
        pinsShape(part, style),
        outlineRect(part, style, 4),
        `    <rect x="${fmt(part.x + 14)}" y="${fmt(part.y + 14)}" width="${fmt(part.w - 28)}" height="${fmt(part.h - 28)}" fill="${style.bg}" stroke="${style.fg}" stroke-width="${style.partWidth * 0.8}" rx="3"/>`,
    ].join('\n');
}

function icShape(part, style) {
    return [
        haloShape(part, style, 10, 14),
        pinsShape(part, style),
        outlineRect(part, style, 8),
        `    <line x1="${fmt(part.x + 10)}" y1="${fmt(part.y + 10)}" x2="${fmt(part.x + part.w - 10)}" y2="${fmt(part.y + 10)}" stroke="${style.dim}" stroke-width="${style.pinWidth}"/>`,
    ].join('\n');
}

function busBlockShape(part, style) {
    const lines = [haloShape(part, style, 10, 12), pinsShape(part, style), outlineRect(part, style, 2)];
    const count = part.lanes ?? 7;
    for (let i = 1; i <= count; i++) {
        const t = i / (count + 1);
        if (part.vertical) {
            lines.push(`    <line x1="${fmt(part.x + part.w * t)}" y1="${fmt(part.y + 10)}" x2="${fmt(part.x + part.w * t)}" y2="${fmt(part.y + part.h - 10)}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`);
        } else {
            lines.push(`    <line x1="${fmt(part.x + 10)}" y1="${fmt(part.y + part.h * t)}" x2="${fmt(part.x + part.w - 10)}" y2="${fmt(part.y + part.h * t)}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`);
        }
    }
    return lines.join('\n');
}

function padClusterShape(part, style) {
    const lines = [haloShape(part, style, 9, 12), outlineRect(part, style, 8)];
    for (const pin of part.pins) {
        lines.push(`    <circle cx="${fmt(pin.x)}" cy="${fmt(pin.y)}" r="10" fill="${style.bg}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`);
        lines.push(`    <circle cx="${fmt(pin.x)}" cy="${fmt(pin.y)}" r="3" fill="${style.fg}" opacity="0.66"/>`);
    }
    return lines.join('\n');
}

function passiveShape(part, style) {
    const lines = [pinsShape(part, style)];
    lines.push(outlineRect(part, style, part.kind === 'capacitor' ? 10 : 3));
    if (part.kind === 'resistor') {
        lines.push(`    <line x1="${fmt(part.x + 5)}" y1="${fmt(part.y + part.h / 2)}" x2="${fmt(part.x + part.w - 5)}" y2="${fmt(part.y + part.h / 2)}" stroke="${style.dim}" stroke-width="${style.pinWidth}"/>`);
    }
    return lines.join('\n');
}

function outlineRect(part, style, radius) {
    return `    <rect x="${fmt(part.x)}" y="${fmt(part.y)}" width="${fmt(part.w)}" height="${fmt(part.h)}" fill="${style.bg}" stroke="${style.fg}" stroke-width="${style.partWidth}" rx="${radius}"/>`;
}

function haloShape(part, style, offset, corner) {
    const x = part.x - offset;
    const y = part.y - offset;
    const w = part.w + offset * 2;
    const h = part.h + offset * 2;
    const c = Math.min(corner, w / 3, h / 3);
    const d = [
        `M ${fmt(x + c)} ${fmt(y)}`,
        `L ${fmt(x + w - c)} ${fmt(y)}`,
        `L ${fmt(x + w)} ${fmt(y + c)}`,
        `L ${fmt(x + w)} ${fmt(y + h - c)}`,
        `L ${fmt(x + w - c)} ${fmt(y + h)}`,
        `L ${fmt(x + c)} ${fmt(y + h)}`,
        `L ${fmt(x)} ${fmt(y + h - c)}`,
        `L ${fmt(x)} ${fmt(y + c)}`,
        'Z',
    ].join(' ');
    return `    <path d="${d}" fill="none" stroke="${style.fg}" stroke-width="${style.traceWidth * 0.9}"/>`;
}

function pinsShape(part, style) {
    return part.pins.map((pin) => {
        if (pin.side === 'top' || pin.side === 'bottom') {
            const y2 = pin.side === 'top' ? part.y : part.y + part.h;
            return `    <line x1="${fmt(pin.x)}" y1="${fmt(pin.y)}" x2="${fmt(pin.x)}" y2="${fmt(y2)}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`;
        }
        if (pin.side === 'left' || pin.side === 'right') {
            const x2 = pin.side === 'left' ? part.x : part.x + part.w;
            return `    <line x1="${fmt(pin.x)}" y1="${fmt(pin.y)}" x2="${fmt(x2)}" y2="${fmt(pin.y)}" stroke="${style.fg}" stroke-width="${style.pinWidth}"/>`;
        }
        return '';
    }).filter(Boolean).join('\n');
}

function fmt(value) {
    return Number(value.toFixed(2));
}

