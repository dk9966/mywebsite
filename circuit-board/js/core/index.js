// Pipeline entry: a seed plus CONFIG fully determines the model. The model is
// pure data (parts with draw primitives, filleted traces, via terminators) so
// renderers stay thin and identical across SVG and canvas.

import { createRng } from '../rng.js';
import { placeParts } from './place.js';
import { buildNetlist } from './netlist.js';
import { routeAll } from './route.js';
import { filletRadii } from './fillet.js';

export function generate(seed, config) {
    const rng = createRng(seed);
    const parts = placeParts(rng, config);
    const nets = buildNetlist(rng, parts, config);
    const { traces, vias } = routeAll(rng, parts, nets, config);
    for (const t of traces) {
        t.fillets = filletRadii(t.points, config.fillet.radius);
    }
    return {
        width: config.board.width,
        height: config.board.height,
        parts: pruneUnconnectedParts(parts, traces),
        traces,
        vias,
    };
}

// Drop parts whose pins never land on a trace endpoint -- no orphan meshes.
function pruneUnconnectedParts(parts, traces) {
    const endpoints = new Set();
    for (const trace of traces) {
        for (const point of [trace.points[0], trace.points[trace.points.length - 1]]) {
            endpoints.add(`${Math.round(point[0])},${Math.round(point[1])}`);
        }
    }
    return parts.filter((part) => (
        part.pins.length > 0
        && part.pins.some((pin) => endpoints.has(`${Math.round(pin.x)},${Math.round(pin.y)}`))
    ));
}
