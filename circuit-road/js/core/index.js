import { createRng } from '../rng.js';
import { clamp, snap } from './geometry.js';
import { placeParts } from './parts.js';
import { buildRoadNetwork } from './route.js';

export function generate(seed, config) {
    const rng = createRng(seed);
    const parts = placeParts(rng, config);
    const { traces, vias } = buildRoadNetwork(rng, parts, config);

    return {
        seed,
        width: config.board.width,
        height: config.board.height,
        parts: pruneUnusedParts(parts, traces, config),
        traces,
        vias,
    };
}

function pruneUnusedParts(parts, traces, config) {
    const endpoints = new Set();
    for (const trace of traces) {
        for (const point of [trace.points[0], trace.points[trace.points.length - 1]]) {
            endpoints.add(`${Math.round(point.x)},${Math.round(point.y)}`);
        }
    }

    return parts.filter((part) => (
        part.pins.length > 0
        && part.pins.some((pin) => endpoints.has(anchorKey(pin, config)))
    ));
}

function anchorKey(pin, config) {
    const x = snap(clamp(pin.x, config.grid.margin, config.board.width - config.grid.margin), config.grid.cell);
    const y = snap(clamp(pin.y, config.grid.margin, config.board.height - config.grid.margin), config.grid.cell);
    return `${Math.round(x)},${Math.round(y)}`;
}

