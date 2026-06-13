// Procedural layout inspired by pcb-circuits/images/thin-pcb.png.
// Grid is ~177×61 at the default 1600×550 / cellSize 9 viewport.

import { randomAuxPinPlacement } from '../components.js';

export const THIN_PCB_PARAMS = {
    seed: 42,
    mapWidth: 1600,
    mapHeight: 550,
    showBuses: true,
    showGreedyCircuits: false,
    thinPcbProcedural: true,
    generatorChipsOnly: true,
    busMode: false,
    pinBusWireCount: 4,
    pinBusSlantLength: 6,
    pinBusStraightMax: 14,
    routeClearanceTarget: 4,
    routeClearanceBias: 0.75,
    pinBusRouteMargin: 16,
    pinBusMaxDetourRatio: 1.75,
    pinBusCorridorWeight: 0.24,
    pinBusSpineRatio: 0.52,
    obstacleMinSpacing: 1,
    obstacleKeepOut: 1,
    directionality: 0.8,
    wireLength: 28,
    joinEndpoints: true,
    bgColor: 'rgba(1, 8, 12, 1)',
    fgColor: 'rgba(43, 238, 235, 1)',
};

export function generateThinPcbLayout(seed, gridWidth, gridHeight) {
    const rng = makeRng(seed);
    const obstacles = [];
    const routeHints = {
        spineY: clamp(Math.round(gridHeight * 0.52), 8, gridHeight - 9),
        spineBand: null,
        majorComponents: [],
        endpoints: [],
    };
    routeHints.spineBand = {
        minY: Math.max(1, routeHints.spineY - 4),
        maxY: Math.min(gridHeight - 2, routeHints.spineY + 4),
    };

    const upperY = Math.max(3, routeHints.spineY - 15);
    const midUpperY = Math.max(3, routeHints.spineY - 9);
    const midLowerY = Math.min(gridHeight - 16, routeHints.spineY + 4);
    const lowerY = Math.min(gridHeight - 14, routeHints.spineY + 11);

    const place = (candidate, spacing = 1) => {
        const o = normalizeObstacle(candidate, gridWidth, gridHeight);
        if (!fits(o, gridWidth, gridHeight)) return null;
        if (overlapsAny(o, obstacles, spacing)) return null;
        obstacles.push(o);
        return o;
    };

    const placeNear = (base, spec, spacing = 1) => {
        const x = base.x + spec.dx + jitter(rng, spec.jx ?? 1);
        const y = base.y + spec.dy + jitter(rng, spec.jy ?? 1);
        return place({ ...spec, x, y }, spacing);
    };

    const majorSpecs = [
        { x: ratioX(gridWidth, 0.11), y: midUpperY, w: 14, h: 14, kind: 'qfp' },
        { x: ratioX(gridWidth, 0.33), y: upperY, w: 14, h: 14, kind: 'qfp' },
        { x: ratioX(gridWidth, 0.51), y: lowerY, w: 12, h: 6, kind: 'soic', rot: 0 },
        { x: ratioX(gridWidth, 0.70), y: midLowerY, w: 14, h: 14, kind: 'qfp' },
        { x: ratioX(gridWidth, 0.88), y: midUpperY, w: 14, h: 14, kind: 'qfp' },
    ];

    for (const spec of majorSpecs) {
        const major = place({
            ...spec,
            x: spec.x + jitter(rng, 3),
            y: spec.y + jitter(rng, 2),
        }, 3);
        if (major) routeHints.majorComponents.push(centerOf(major));
    }

    const modules = [
        { x: ratioX(gridWidth, 0.24), y: upperY + 4, w: 12, h: 5, kind: 'connector', auxPinSide: 'bottom' },
        { x: ratioX(gridWidth, 0.43), y: routeHints.spineY - 4, w: 11, h: 4, kind: 'header', auxPinSide: 'bottom' },
        { x: ratioX(gridWidth, 0.62), y: lowerY + 2, w: 12, h: 5, kind: 'connector', auxPinSide: 'top' },
        { x: ratioX(gridWidth, 0.58), y: upperY - 2, w: 12, h: 9, kind: 'heatsink', ...randomHeatsinkPins(rng, 12, 9) },
    ];
    for (const spec of modules) place({ ...spec, x: spec.x + jitter(rng, 2), y: spec.y + jitter(rng, 1) }, 2);

    place({ x: 2, y: routeHints.spineY - 6, w: 4, h: 11, kind: 'header', rot: 1, auxPinSide: 'right' }, 1);

    const anchors = obstacles.filter((o) => o.kind === 'qfp' || o.kind === 'soic');
    for (const o of anchors) {
        const above = o.y > routeHints.spineY;
        const detailSpecs = [
            { kind: 'smd', w: 6, h: 4, dx: -8, dy: above ? -8 : o.h + 4, auxPinSide: 'right' },
            { kind: 'smd', w: 6, h: 4, dx: o.w + 3, dy: above ? -5 : o.h + 3, auxPinSide: 'left' },
            { kind: 'via', w: 3, h: 3, dx: -5, dy: Math.round(o.h / 2), auxPinSide: 'right' },
            { kind: 'pad', w: 3, h: 3, dx: o.w + 4, dy: Math.round(o.h / 2), auxPinSide: 'left' },
            { kind: 'capacitor', w: 6, h: 6, dx: Math.round(o.w / 2) - 3, dy: above ? -9 : o.h + 5, auxPinSide: above ? 'bottom' : 'top' },
        ];
        for (const spec of detailSpecs) {
            const detail = placeNear(o, spec, 1);
            if (detail && (detail.kind === 'pad' || detail.kind === 'via')) {
                routeHints.endpoints.push(centerOf(detail));
            }
        }
    }

    for (let i = 0; i < 18; i++) {
        const leftBias = i < 4 ? 0.04 : i > 13 ? 0.86 : 0.12;
        const rightBias = i < 4 ? 0.2 : i > 13 ? 0.96 : 0.84;
        const t = i < 4 ? rand(rng, leftBias, rightBias) : rand(rng, 0.08, 0.94);
        const yBand = i % 3 === 0 ? upperY : i % 3 === 1 ? lowerY : routeHints.spineY;
        const kind = i % 4 === 0 ? 'via' : 'pad';
        const endpoint = place({
            x: ratioX(gridWidth, t) + jitter(rng, 4),
            y: yBand + jitter(rng, 5),
            w: 3,
            h: 3,
            kind,
            auxPinSide: randSideTowardSpine(yBand, routeHints.spineY),
        }, 1);
        if (endpoint) routeHints.endpoints.push(centerOf(endpoint));
    }

    return { obstacles, routeHints };
}

export function generateThinPcbObstacles(seed, gridWidth, gridHeight) {
    return generateThinPcbLayout(seed, gridWidth, gridHeight).obstacles;
}

export const THIN_PCB_OBSTACLES = [
    // Four main QFP spine chips — staggered to leave routing corridors
    { x: 10, y: 20, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 46, y: 4, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 68, y: 38, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 136, y: 18, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },

    // Striped multi-pin blocks (connectors in the reference)
    { x: 30, y: 2, w: 12, h: 5, kind: 'connector', rot: 0 },
    { x: 104, y: 48, w: 12, h: 5, kind: 'connector', rot: 0 },

    // SOIC with left/right pins (rotated)
    { x: 36, y: 44, w: 6, h: 12, kind: 'soic', rot: 1 },

    // Left entry header
    { x: 2, y: 22, w: 4, h: 11, kind: 'header', rot: 1 },

    // Hex/octagonal pads
    { x: 28, y: 8, w: 8, h: 8, kind: 'drum', rot: 0 },
    { x: 78, y: 24, w: 8, h: 8, kind: 'drum', rot: 0 },
    { x: 118, y: 8, w: 8, h: 8, kind: 'drum', rot: 0 },
    { x: 148, y: 42, w: 8, h: 8, kind: 'drum', rot: 0 },

    // Capacitors
    { x: 18, y: 40, w: 6, h: 6, kind: 'capacitor', rot: 0 },
    { x: 48, y: 48, w: 6, h: 6, kind: 'capacitor', rot: 0 },
    { x: 88, y: 6, w: 6, h: 6, kind: 'capacitor', rot: 0 },
    { x: 124, y: 38, w: 6, h: 6, kind: 'capacitor', rot: 0 },

    // SMD discretes
    { x: 8, y: 14, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 8, y: 48, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 26, y: 48, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 72, y: 48, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 92, y: 38, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 108, y: 22, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 142, y: 8, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 158, y: 28, w: 6, h: 4, kind: 'smd', rot: 0 },
    { x: 158, y: 48, w: 6, h: 4, kind: 'smd', rot: 0 },

    // Finned block (upper corridor)
    { x: 94, y: 2, w: 12, h: 9, kind: 'heatsink', rot: 0, auxPinSide: 'left', auxPinOffsets: [2, 7] },

    // Horizontal header strip between left chips
    { x: 44, y: 20, w: 11, h: 4, kind: 'header', rot: 0 },
];

export const THIN_PCB_SNAPSHOT_NAME = 'Thin PCB';

function normalizeObstacle(o, gridWidth, gridHeight) {
    const w = Math.max(2, o.w | 0);
    const h = Math.max(2, o.h | 0);
    const x = clamp(Math.round(o.x), 1, Math.max(1, gridWidth - w - 2));
    const y = clamp(Math.round(o.y), 1, Math.max(1, gridHeight - h - 2));
    const kind = o.kind || 'block';
    return {
        x,
        y,
        w,
        h,
        kind,
        qfp: kind === 'qfp',
        rot: (o.rot | 0) % 4,
        ...(o.auxPinSide ? { auxPinSide: o.auxPinSide } : {}),
        ...(o.auxPinOffsets?.length ? { auxPinOffsets: o.auxPinOffsets.slice() } : {}),
    };
}

function randomHeatsinkPins(rng, w, h) {
    return randomAuxPinPlacement(rng, w, h, 2);
}

function fits(o, gridWidth, gridHeight) {
    return o.x >= 1 && o.y >= 1 && o.x + o.w < gridWidth - 1 && o.y + o.h < gridHeight - 1;
}

function overlapsAny(o, obstacles, spacing) {
    return obstacles.some((other) => (
        o.x < other.x + other.w + spacing
        && o.x + o.w + spacing > other.x
        && o.y < other.y + other.h + spacing
        && o.y + o.h + spacing > other.y
    ));
}

function centerOf(o) {
    return { x: o.x + o.w / 2, y: o.y + o.h / 2 };
}

function ratioX(gridWidth, ratio) {
    return Math.round(gridWidth * ratio);
}

function rand(rng, min, max) {
    return min + rng() * (max - min);
}

function jitter(rng, amount) {
    return Math.round(rand(rng, -amount, amount));
}

function randSideTowardSpine(y, spineY) {
    return y < spineY ? 'bottom' : 'top';
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function makeRng(seed) {
    let h = 2166136261;
    const text = String(seed ?? 'thin-pcb');
    for (let i = 0; i < text.length; i++) {
        h ^= text.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return () => {
        h += 0x6D2B79F5;
        let t = h;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
