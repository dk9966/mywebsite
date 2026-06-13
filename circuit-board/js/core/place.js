// Component placement: large QFPs on a jittered grid, mid-size parts and
// mounting holes by rejection sampling, then a dart-throwing scatter of small
// parts. Output instances carry pixel-space pins and draw primitives plus the
// cell footprint the router blocks.

import { gridSize } from '../config.js';
import {
    SMALL_MAKERS, makeQfp, makeSoic, makeHeatsink, makeHeader, makeConnector,
} from './parts.js';

export function placeParts(rng, config) {
    const { gw, gh } = gridSize(config);
    const em = config.grid.edgeMargin + 1; // +1 keeps pin anchors inside bounds
    const margin = config.place.margin;
    const parts = [];
    const occupied = [];

    function tryPlace(spec, cellX, cellY, marginCells) {
        if (cellX < em || cellY < em) return false;
        if (cellX + spec.cols > gw - em || cellY + spec.rows > gh - em) return false;
        // Anchor ring: pins live one cell outside the footprint.
        const box = {
            x0: cellX - 1, y0: cellY - 1,
            x1: cellX + spec.cols + 1, y1: cellY + spec.rows + 1,
        };
        for (const o of occupied) {
            if (box.x0 - marginCells < o.x1 && box.x1 + marginCells > o.x0
                && box.y0 - marginCells < o.y1 && box.y1 + marginCells > o.y0) return false;
        }
        const part = buildInstance(spec, cellX, cellY, config);
        occupied.push(box);
        parts.push(part);
        return part;
    }

    function scatter(make, marginCells, tries) {
        for (let i = 0; i < tries; i++) {
            const spec = make(rng, config);
            const cellX = rng.int(em, gw - em - spec.cols);
            const cellY = rng.int(em, gh - em - spec.rows);
            if (tryPlace(spec, cellX, cellY, marginCells)) return true;
        }
        return false;
    }

    function scatterNear(make, anchors, marginCells, tries) {
        if (!anchors.length) return scatter(make, marginCells, tries);
        const [rMin, rMax] = config.place.satelliteRadius;
        for (let i = 0; i < tries; i++) {
            const spec = make(rng, config);
            const anchor = rng.pick(anchors);
            const angle = rng.range(0, Math.PI * 2);
            const dist = rng.range(rMin, rMax);
            const cellX = Math.round(anchor.cellX + anchor.cols / 2 + Math.cos(angle) * dist - spec.cols / 2);
            const cellY = Math.round(anchor.cellY + anchor.rows / 2 + Math.sin(angle) * dist - spec.rows / 2);
            if (tryPlace(spec, cellX, cellY, marginCells)) return true;
        }
        return scatter(make, marginCells, Math.ceil(tries / 3));
    }

    // 1. QFPs: one per jittered slot of a 3x2 grid.
    const slotsX = 3;
    const slotsY = 2;
    const slotW = (gw - 2 * em) / slotsX;
    const slotH = (gh - 2 * em) / slotsY;
    const slots = [];
    for (let sx = 0; sx < slotsX; sx++) {
        for (let sy = 0; sy < slotsY; sy++) slots.push([sx, sy]);
    }
    const qfpCount = rng.int(...config.place.qfp.count);
    for (const [sx, sy] of rng.shuffle(slots).slice(0, qfpCount)) {
        const spec = makeQfp(rng, config);
        let done = false;
        for (let i = 0; i < 10 && !done; i++) {
            const j = config.place.qfp.jitter;
            const cx = em + (sx + 0.5 + rng.range(-j, j)) * slotW;
            const cy = em + (sy + 0.5 + rng.range(-j, j)) * slotH;
            done = tryPlace(
                spec,
                Math.round(cx - spec.cols / 2),
                Math.round(cy - spec.rows / 2),
                margin.qfp,
            );
        }
        if (!done) scatter(() => spec, margin.qfp, 40);
    }

    // 2. Mid-size parts.
    const soicCount = rng.int(...config.place.soic.count);
    for (let i = 0; i < soicCount; i++) scatter(makeSoic, margin.mid, 60);
    const heatsinkCount = rng.int(...config.place.heatsink.count);
    for (let i = 0; i < heatsinkCount; i++) scatter(makeHeatsink, margin.mid, 80);
    const headerCount = rng.int(...config.place.header.count);
    for (let i = 0; i < headerCount; i++) scatter(makeHeader, margin.mid, 60);
    const connectorCount = rng.int(...config.place.connector.count);
    for (let i = 0; i < connectorCount; i++) scatter(makeConnector, margin.mid, 60);

    // 3. Small parts: bias density around routed anchors so empty space fills
    // with local circuitry instead of unrelated island traces.
    const anchors = parts.filter((p) => (
        p.kind === 'qfp'
        || p.kind === 'heatsink'
        || p.kind === 'soic'
    ));
    const smallCount = rng.int(...config.place.small.count);
    for (let i = 0; i < smallCount; i++) {
        const kind = rng.weighted(config.place.small.weights);
        scatterNear(SMALL_MAKERS[kind], anchors, margin.small, 42);
    }

    return parts;
}

let nextPartId = 0;

function buildInstance(spec, cellX, cellY, config) {
    const cell = config.grid.cell;
    const dx = cellX * cell;
    const dy = cellY * cell;
    const partId = nextPartId++;
    return {
        partId,
        kind: spec.kind,
        accent: spec.accent ?? null,
        pinRows: !!spec.pinRows,
        cellX,
        cellY,
        cols: spec.cols,
        rows: spec.rows,
        cx: (cellX + spec.cols / 2) * cell,
        cy: (cellY + spec.rows / 2) * cell,
        pins: spec.pins.map((p) => ({
            partId,
            partKind: spec.kind,
            cx: cellX + p.c,
            cy: cellY + p.r,
            x: (cellX + p.c + 0.5) * cell,
            y: (cellY + p.r + 0.5) * cell,
            dir: p.dir,
            side: p.side,
            used: false,
        })),
        prims: spec.prims.map((p) => translatePrim(p, dx, dy)),
    };
}

function translatePrim(p, dx, dy) {
    switch (p.t) {
        case 'rect': return { ...p, x: p.x + dx, y: p.y + dy };
        case 'circle': return { ...p, cx: p.cx + dx, cy: p.cy + dy };
        case 'line': return { ...p, x1: p.x1 + dx, y1: p.y1 + dy, x2: p.x2 + dx, y2: p.y2 + dy };
        case 'poly': return { ...p, pts: p.pts.map(([x, y]) => [x + dx, y + dy]) };
        default: return p;
    }
}
