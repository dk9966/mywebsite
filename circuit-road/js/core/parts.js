import { clamp, rectsOverlap, snap } from './geometry.js';

let nextPartId = 1;

export function placeParts(rng, config) {
    nextPartId = 1;
    const parts = [];
    const add = (part) => parts.push(part);

    for (let i = 0; i < config.place.largeChips; i++) {
        add(placeOne(rng, config, parts, () => makeQfp(rng, config)));
    }
    for (let i = 0; i < config.place.mediumIcs; i++) {
        add(placeOne(rng, config, parts, () => makeIc(rng, config)));
    }
    for (let i = 0; i < config.place.busBlocks; i++) {
        add(placeOne(rng, config, parts, () => makeBusBlock(rng, config)));
    }
    for (let i = 0; i < config.place.padClusters; i++) {
        add(placeOne(rng, config, parts, () => makePadCluster(rng, config)));
    }
    for (let i = 0; i < config.place.passives; i++) {
        const part = placeOne(rng, config, parts, () => makePassive(rng, config), 0.78);
        if (part) add(part);
    }

    return parts.filter(Boolean);
}

function placeOne(rng, config, parts, factory, strictness = 1) {
    const margin = config.grid.margin;
    const gap = config.place.gap * strictness;
    for (let i = 0; i < config.place.attempts; i++) {
        const part = factory();
        part.x = snap(rng.float(margin, config.board.width - margin - part.w), config.grid.cell);
        part.y = snap(rng.float(margin, config.board.height - margin - part.h), config.grid.cell);
        if (!parts.some((other) => rectsOverlap(part, other, gap))) {
            part.pins = buildPins(part, config).map((pin) => ({
                ...pin,
                x: snap(clamp(pin.x, config.grid.margin, config.board.width - config.grid.margin), config.grid.cell),
                y: snap(clamp(pin.y, config.grid.margin, config.board.height - config.grid.margin), config.grid.cell),
            }));
            return part;
        }
    }
    return null;
}

function makeBase(kind, w, h) {
    return {
        id: `part-${nextPartId++}`,
        kind,
        x: 0,
        y: 0,
        w,
        h,
        pins: [],
    };
}

function makeQfp(rng, config) {
    const size = snap(rng.float(96, 148), config.grid.cell);
    return {
        ...makeBase('qfp', size, size),
        pinPitch: 8,
        pinInset: 12,
    };
}

function makeIc(rng, config) {
    const vertical = rng.chance(0.45);
    const long = snap(rng.float(92, 154), config.grid.cell);
    const short = snap(rng.float(34, 58), config.grid.cell);
    return {
        ...makeBase('ic', vertical ? short : long, vertical ? long : short),
        pinPitch: 10,
        pinInset: 10,
        vertical,
    };
}

function makeBusBlock(rng, config) {
    const vertical = rng.chance(0.72);
    const w = vertical ? snap(rng.float(54, 78), config.grid.cell) : snap(rng.float(118, 180), config.grid.cell);
    const h = vertical ? snap(rng.float(160, 260), config.grid.cell) : snap(rng.float(48, 72), config.grid.cell);
    return {
        ...makeBase('busBlock', w, h),
        vertical,
        lanes: rng.int(6, 10),
        pinPitch: 12,
    };
}

function makePadCluster(rng, config) {
    const cols = rng.int(2, 3);
    const rows = rng.int(2, 3);
    return {
        ...makeBase('padCluster', cols * 32 + 18, rows * 32 + 18),
        cols,
        rows,
        pinPitch: 32,
    };
}

function makePassive(rng, config) {
    const vertical = rng.chance(0.52);
    const kind = rng.pick(['passive', 'resistor', 'capacitor']);
    const w = vertical ? snap(rng.float(12, 18), config.grid.cell) : snap(rng.float(30, 42), config.grid.cell);
    const h = vertical ? snap(rng.float(30, 42), config.grid.cell) : snap(rng.float(12, 18), config.grid.cell);
    return {
        ...makeBase(kind, w, h),
        vertical,
    };
}

function buildPins(part, config) {
    if (part.kind === 'qfp') return qfpPins(part);
    if (part.kind === 'ic') return icPins(part);
    if (part.kind === 'busBlock') return busPins(part);
    if (part.kind === 'padCluster') return clusterPins(part);
    return passivePins(part, config);
}

function qfpPins(part) {
    const pins = [];
    const addSide = (side, count) => {
        for (let i = 0; i < count; i++) {
            const t = (i + 1) / (count + 1);
            pins.push(pinOnSide(part, side, t));
        }
    };
    const count = clamp(Math.floor((part.w - part.pinInset * 2) / part.pinPitch), 8, 16);
    addSide('top', count);
    addSide('right', count);
    addSide('bottom', count);
    addSide('left', count);
    return pins;
}

function icPins(part) {
    const pins = [];
    const sides = part.vertical ? ['left', 'right'] : ['top', 'bottom'];
    const length = part.vertical ? part.h : part.w;
    const count = clamp(Math.floor((length - part.pinInset * 2) / part.pinPitch), 6, 18);
    for (const side of sides) {
        for (let i = 0; i < count; i++) pins.push(pinOnSide(part, side, (i + 1) / (count + 1)));
    }
    return pins;
}

function busPins(part) {
    const pins = [];
    const count = part.vertical ? part.lanes : Math.max(4, Math.floor(part.w / 18));
    const sides = part.vertical ? ['top', 'bottom'] : ['left', 'right'];
    for (const side of sides) {
        for (let i = 0; i < count; i++) pins.push(pinOnSide(part, side, (i + 1) / (count + 1)));
    }
    return pins;
}

function clusterPins(part) {
    const pins = [];
    for (let row = 0; row < part.rows; row++) {
        for (let col = 0; col < part.cols; col++) {
            pins.push({
                id: `${part.id}-p-${row}-${col}`,
                side: 'center',
                x: part.x + 25 + col * part.pinPitch,
                y: part.y + 25 + row * part.pinPitch,
            });
        }
    }
    return pins;
}

function passivePins(part, config) {
    const pad = config.grid.cell;
    if (part.vertical) {
        return [
            { id: `${part.id}-p-a`, side: 'top', x: part.x + part.w / 2, y: part.y - pad / 2 },
            { id: `${part.id}-p-b`, side: 'bottom', x: part.x + part.w / 2, y: part.y + part.h + pad / 2 },
        ];
    }
    return [
        { id: `${part.id}-p-a`, side: 'left', x: part.x - pad / 2, y: part.y + part.h / 2 },
        { id: `${part.id}-p-b`, side: 'right', x: part.x + part.w + pad / 2, y: part.y + part.h / 2 },
    ];
}

function pinOnSide(part, side, t) {
    const inset = 8;
    if (side === 'top') return { id: `${part.id}-${side}-${t}`, side, x: part.x + part.w * t, y: part.y - inset };
    if (side === 'bottom') return { id: `${part.id}-${side}-${t}`, side, x: part.x + part.w * t, y: part.y + part.h + inset };
    if (side === 'left') return { id: `${part.id}-${side}-${t}`, side, x: part.x - inset, y: part.y + part.h * t };
    return { id: `${part.id}-${side}-${t}`, side, x: part.x + part.w + inset, y: part.y + part.h * t };
}

