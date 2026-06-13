export function rectsOverlap(a, b, gap = 0) {
    return !(
        a.x + a.w + gap < b.x
        || b.x + b.w + gap < a.x
        || a.y + a.h + gap < b.y
        || b.y + b.h + gap < a.y
    );
}

export function centerOf(part) {
    return {
        x: part.x + part.w / 2,
        y: part.y + part.h / 2,
    };
}

export function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

export function dist(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
}

export function snap(value, cell) {
    return Math.round(value / cell) * cell;
}

