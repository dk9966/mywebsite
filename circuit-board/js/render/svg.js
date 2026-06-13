// SVG export of a generated model. Pure string building, no DOM, so the
// headless render script can import it from node.

import { pathData } from '../core/fillet.js';

export function modelToSvg(model, config, { style: styleName } = {}) {
    const style = config.styles[styleName ?? config.defaultStyle];
    const parts = [];

    parts.push(
        `<svg xmlns="http://www.w3.org/2000/svg" width="${model.width}" height="${model.height}" viewBox="0 0 ${model.width} ${model.height}">`,
    );
    if (style.glowBlur > 0) {
        parts.push(
            `<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">` +
                `<feGaussianBlur stdDeviation="${style.glowBlur}" result="b"/>` +
                `<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>` +
                `</filter></defs>`,
        );
    }
    parts.push(
        `<rect width="100%" height="100%" fill="${style.bg}"/>`,
        `<g${style.glowBlur > 0 ? ' filter="url(#glow)"' : ''}>`,
    );

    for (const t of model.traces) {
        parts.push(
            `<path d="${pathData(t.points, t.fillets)}" fill="none" ` +
                `stroke="${style.fg}" stroke-width="${style.traceWidth}" stroke-linecap="round"/>`,
        );
    }

    for (const part of model.parts) {
        for (const p of part.prims) parts.push(primToSvg(p, part, style));
    }

    for (const via of model.vias) {
        parts.push(
            via.ring
                ? `<circle cx="${via.x}" cy="${via.y}" r="${config.vias.ringR}" ` +
                    `fill="${style.bg}" stroke="${style.fg}" stroke-width="1.6"/>`
                : `<circle cx="${via.x}" cy="${via.y}" r="${config.vias.dotR}" fill="${style.fg}"/>`,
        );
    }

    parts.push(`</g>`, `</svg>`);
    return parts.join('\n');
}

function paint(token, part, style) {
    if (!token) return 'none';
    if (token === 'accent') return style.accents[part.accent] ?? style.fg;
    return style[token];
}

function primToSvg(p, part, style) {
    const fill = `fill="${paint(p.fill, part, style)}"`;
    const stroke = p.stroke
        ? ` stroke="${paint(p.stroke, part, style)}" stroke-width="${p.sw}"`
        : '';
    switch (p.t) {
        case 'rect':
            return `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}"` +
                `${p.rx ? ` rx="${p.rx}"` : ''} ${fill}${stroke}/>`;
        case 'circle':
            return `<circle cx="${p.cx}" cy="${p.cy}" r="${p.r}" ${fill}${stroke}/>`;
        case 'line':
            return `<line x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" ` +
                `stroke="${style.fg}" stroke-width="${p.sw}"/>`;
        case 'poly':
            return `<polygon points="${p.pts.map(([x, y]) => `${x},${y}`).join(' ')}" ` +
                `${fill}${stroke}/>`;
        default:
            return '';
    }
}
