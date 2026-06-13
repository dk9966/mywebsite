// SVG export of a generated model. Pure string building, no DOM -- the
// headless verification script imports this from node.

function polylinePoints(points) {
    return points.map(([x, y]) => `${Math.round(x * 10) / 10},${Math.round(y * 10) / 10}`).join(' ');
}

// `transpose` swaps the axes ((x, y) -> (y, x)) so a model generated with
// horizontal flow renders flowing vertically. Pure transform: the model
// stays in its own space.
export function modelToSvg(model, config, { transpose = false } = {}) {
    const { style, board } = config;
    const width = transpose ? board.height : board.width;
    const height = transpose ? board.width : board.height;
    const parts = [];

    parts.push(
        `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
        `<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">` +
            `<feGaussianBlur stdDeviation="${style.glowBlur ?? 3.5}" result="b"/>` +
            `<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>` +
            `</filter></defs>`,
        `<rect width="100%" height="100%" fill="${style.bg}"/>`,
        `<g filter="url(#glow)"${transpose ? ' transform="matrix(0 1 1 0 0 0)"' : ''}>`,
    );

    for (const t of model.traces) {
        parts.push(
            `<polyline points="${polylinePoints(t.points)}" fill="none" ` +
                `stroke="${style.trace}" stroke-width="${style.traceWidth}" ` +
                `stroke-linecap="round" stroke-linejoin="round"/>`,
        );
    }

    for (const chip of model.chips) {
        const color = chip.color === 'pink' ? style.chipPink : style.chipGreen;
        const pins = [];
        for (const y of chip.pins.left) pins.push(`M${chip.x},${y}h${-style.pinLength}`);
        for (const y of chip.pins.right) pins.push(`M${chip.x + chip.w},${y}h${style.pinLength}`);
        parts.push(
            `<path d="${pins.join('')}" stroke="${style.trace}" ` +
                `stroke-width="${style.traceWidth * 0.7}" fill="none"/>`,
            `<rect x="${chip.x}" y="${chip.y}" width="${chip.w}" height="${chip.h}" ` +
                `fill="none" stroke="${color}" stroke-width="${style.chipWidth}"/>`,
        );
    }

    parts.push(`</g>`, `</svg>`);
    return parts.join('\n');
}
