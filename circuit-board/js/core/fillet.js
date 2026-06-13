// Corner rounding for trace polylines. filletRadii computes a clamped arc
// radius per vertex (0 at endpoints and straight-through vertices); pathData
// turns points + radii into an SVG path string. The canvas renderer consumes
// the same radii via ctx.arcTo, so both backends draw identical geometry.

export function filletRadii(points, maxRadius) {
    const radii = points.map(() => 0);
    for (let i = 1; i + 1 < points.length; i++) {
        const t = tangentLength(points[i - 1], points[i], points[i + 1], maxRadius);
        if (t === null) continue;
        const phi = interiorAngle(points[i - 1], points[i], points[i + 1]);
        radii[i] = t * Math.tan(phi / 2);
    }
    return radii;
}

// Distance from the corner vertex to each arc tangent point, clamped so
// neighbouring fillets sharing a segment never overlap.
function tangentLength(a, v, b, maxRadius) {
    const phi = interiorAngle(a, v, b);
    if (phi > Math.PI - 1e-3 || phi < 1e-3) return null; // straight or reversal
    const t = maxRadius / Math.tan(phi / 2);
    const lenA = Math.hypot(v[0] - a[0], v[1] - a[1]);
    const lenB = Math.hypot(b[0] - v[0], b[1] - v[1]);
    return Math.min(t, lenA * 0.5, lenB * 0.5);
}

function interiorAngle(a, v, b) {
    const a1 = Math.atan2(a[1] - v[1], a[0] - v[0]);
    const a2 = Math.atan2(b[1] - v[1], b[0] - v[0]);
    let d = Math.abs(a1 - a2);
    if (d > Math.PI) d = 2 * Math.PI - d;
    return d;
}

const fmt = (n) => Math.round(n * 10) / 10;

export function pathData(points, radii) {
    if (points.length < 2) return '';
    let d = `M${fmt(points[0][0])} ${fmt(points[0][1])}`;
    for (let i = 1; i < points.length; i++) {
        const r = i + 1 < points.length ? radii[i] : 0;
        if (r <= 0.1) {
            d += `L${fmt(points[i][0])} ${fmt(points[i][1])}`;
            continue;
        }
        const a = points[i - 1];
        const v = points[i];
        const b = points[i + 1];
        const phi = interiorAngle(a, v, b);
        const t = r / Math.tan(phi / 2);
        const p1 = offsetToward(v, a, t);
        const p2 = offsetToward(v, b, t);
        const cross = (v[0] - a[0]) * (b[1] - v[1]) - (v[1] - a[1]) * (b[0] - v[0]);
        const sweep = cross > 0 ? 1 : 0;
        d += `L${fmt(p1[0])} ${fmt(p1[1])}`
            + `A${fmt(r)} ${fmt(r)} 0 0 ${sweep} ${fmt(p2[0])} ${fmt(p2[1])}`;
    }
    return d;
}

function offsetToward(from, to, dist) {
    const dx = to[0] - from[0];
    const dy = to[1] - from[1];
    const len = Math.hypot(dx, dy);
    return [from[0] + (dx / len) * dist, from[1] + (dy / len) * dist];
}
