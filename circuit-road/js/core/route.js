import { centerOf, clamp, dist, snap } from './geometry.js';

export function buildRoadNetwork(rng, parts, config) {
    const traces = [];
    const vias = [];
    const majorParts = parts.filter((part) => ['qfp', 'ic', 'busBlock', 'padCluster'].includes(part.kind));
    const smallParts = parts.filter((part) => !majorParts.includes(part));
    const usedPins = new Set();

    for (const [a, b] of nearestMajorPairs(majorParts, config.route.majorLinks)) {
        const lanes = rng.int(config.route.busLaneRange[0], config.route.busLaneRange[1]);
        const aPins = pinsFacing(a, b).filter((pin) => !usedPins.has(pin.id)).slice(0, lanes);
        const bPins = pinsFacing(b, a).filter((pin) => !usedPins.has(pin.id)).slice(0, lanes);
        const laneCount = Math.min(aPins.length, bPins.length);
        for (let i = 0; i < laneCount; i++) {
            const trace = makeTrace(rng, aPins[i], bPins[laneCount - 1 - i], config, 'bus');
            traces.push(trace);
            usedPins.add(aPins[i].id);
            usedPins.add(bPins[laneCount - 1 - i].id);
            maybeAddVia(rng, trace, vias, config.vias.traceChance);
        }
    }

    for (let i = 0; i < config.route.localLinks; i++) {
        const small = smallParts[i % smallParts.length];
        if (!small) break;
        const anchor = nearestPart(small, majorParts, 360);
        if (!anchor) continue;
        const openSmallPins = small.pins.filter((pin) => !usedPins.has(pin.id));
        const from = rng.pick(openSmallPins.length ? openSmallPins : small.pins);
        const to = closestFreePin(from, anchor.pins, usedPins) ?? rng.pick(anchor.pins);
        if (!from || !to) continue;
        traces.push(makeTrace(rng, from, to, config, 'local'));
        usedPins.add(from.id);
        usedPins.add(to.id);
    }

    for (let i = 0; i < config.route.branchLinks; i++) {
        const sourcePart = rng.pick(majorParts);
        const source = rng.pick(sourcePart.pins);
        const via = makeBranchVia(rng, source, config);
        vias.push(via);
        traces.push(makeTrace(rng, source, via, config, 'branch'));
    }

    for (let i = 0; i < config.route.edgeBranches; i++) {
        const sourcePart = rng.pick(majorParts);
        const source = rng.pick(sourcePart.pins);
        const via = makeEdgeVia(rng, source, config);
        vias.push(via);
        traces.push(makeTrace(rng, source, via, config, 'branch'));
    }

    return { traces, vias: dedupeVias(vias, config) };
}

function nearestMajorPairs(parts, limit) {
    const pairs = [];
    for (let i = 0; i < parts.length; i++) {
        const ranked = parts
            .filter((_, index) => index !== i)
            .map((part) => ({ part, d: dist(centerOf(parts[i]), centerOf(part)) }))
            .sort((a, b) => a.d - b.d)
            .slice(0, 4);
        for (const entry of ranked) {
            const ids = [parts[i].id, entry.part.id].sort().join(':');
            if (!pairs.some((pair) => pair.ids === ids)) pairs.push({ ids, a: parts[i], b: entry.part, d: entry.d });
        }
    }
    return pairs.sort((a, b) => a.d - b.d).slice(0, limit).map((pair) => [pair.a, pair.b]);
}

function pinsFacing(part, target) {
    const a = centerOf(part);
    const b = centerOf(target);
    const horizontal = Math.abs(b.x - a.x) > Math.abs(b.y - a.y);
    const side = horizontal ? (b.x > a.x ? 'right' : 'left') : (b.y > a.y ? 'bottom' : 'top');
    const pins = part.pins.filter((pin) => pin.side === side);
    const sorted = pins.sort((p1, p2) => (horizontal ? p1.y - p2.y : p1.x - p2.x));
    return sorted.length ? sorted : part.pins;
}

function nearestPart(part, candidates, maxDistance) {
    const origin = centerOf(part);
    let best = null;
    for (const candidate of candidates) {
        const d = dist(origin, centerOf(candidate));
        if (d <= maxDistance && (!best || d < best.d)) best = { part: candidate, d };
    }
    return best?.part ?? null;
}

function closestFreePin(from, pins, usedPins) {
    return [...pins]
        .filter((pin) => !usedPins.has(pin.id))
        .sort((a, b) => dist(from, a) - dist(from, b))[0];
}

function makeTrace(rng, from, to, config, kind) {
    const points = octilinearPath(rng, from, to, config);
    return {
        kind,
        points,
        from: from.id,
        to: to.id,
    };
}

function octilinearPath(rng, from, to, config) {
    const cell = config.grid.cell;
    const start = anchorPoint(from, config);
    const end = anchorPoint(to, config);
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const sx = Math.sign(dx) || (rng.chance(0.5) ? 1 : -1);
    const sy = Math.sign(dy) || (rng.chance(0.5) ? 1 : -1);
    const chamfer = Math.min(config.route.chamfer, Math.abs(dx) / 2, Math.abs(dy) / 2);
    const horizontalFirst = Math.abs(dx) > Math.abs(dy) ? rng.chance(0.68) : rng.chance(0.32);
    const jitter = snap(rng.float(-config.route.bendJitter, config.route.bendJitter), cell);
    const points = [start];

    if (horizontalFirst) {
        const midX = clamp(snap(start.x + dx * rng.float(0.35, 0.65) + jitter, cell), config.grid.margin, config.board.width - config.grid.margin);
        points.push({ x: midX - sx * chamfer, y: start.y });
        points.push({ x: midX, y: start.y + sy * chamfer });
        points.push({ x: midX, y: end.y - sy * chamfer });
        points.push({ x: midX + sx * chamfer, y: end.y });
    } else {
        const midY = clamp(snap(start.y + dy * rng.float(0.35, 0.65) + jitter, cell), config.grid.margin, config.board.height - config.grid.margin);
        points.push({ x: start.x, y: midY - sy * chamfer });
        points.push({ x: start.x + sx * chamfer, y: midY });
        points.push({ x: end.x - sx * chamfer, y: midY });
        points.push({ x: end.x, y: midY + sy * chamfer });
    }

    points.push(end);
    return compactPoints(points);
}

function anchorPoint(point, config) {
    return {
        x: snap(clamp(point.x, config.grid.margin, config.board.width - config.grid.margin), config.grid.cell),
        y: snap(clamp(point.y, config.grid.margin, config.board.height - config.grid.margin), config.grid.cell),
    };
}

function compactPoints(points) {
    const compact = [points[0]];
    for (const point of points.slice(1, -1)) {
        const prev = compact[compact.length - 1];
        if (!prev || Math.hypot(prev.x - point.x, prev.y - point.y) > 2) compact.push(point);
    }
    compact.push(points[points.length - 1]);
    return compact;
}

function maybeAddVia(rng, trace, vias, chance) {
    if (!rng.chance(chance) || trace.points.length < 4) return;
    const point = trace.points[rng.int(1, trace.points.length - 2)];
    vias.push({ id: `via-${vias.length + 1}`, x: point.x, y: point.y });
}

function makeBranchVia(rng, source, config) {
    const length = rng.float(70, 220);
    const angle = rng.pick([0, Math.PI / 4, Math.PI / 2, 3 * Math.PI / 4, Math.PI, -3 * Math.PI / 4, -Math.PI / 2, -Math.PI / 4]);
    const x = snap(clamp(source.x + Math.cos(angle) * length, config.grid.margin, config.board.width - config.grid.margin), config.grid.cell);
    const y = snap(clamp(source.y + Math.sin(angle) * length, config.grid.margin, config.board.height - config.grid.margin), config.grid.cell);
    return {
        id: `via-branch-${source.id}-${Math.round(length)}`,
        x,
        y,
    };
}

function makeEdgeVia(rng, source, config) {
    const margin = config.grid.margin;
    const edge = rng.pick(['top', 'right', 'bottom', 'left']);
    const x = snap(clamp(source.x + rng.float(-120, 120), margin, config.board.width - margin), config.grid.cell);
    const y = snap(clamp(source.y + rng.float(-120, 120), margin, config.board.height - margin), config.grid.cell);
    if (edge === 'top') return { id: `via-edge-${source.id}`, x, y: margin };
    if (edge === 'right') return { id: `via-edge-${source.id}`, x: config.board.width - margin, y };
    if (edge === 'bottom') return { id: `via-edge-${source.id}`, x, y: config.board.height - margin };
    return { id: `via-edge-${source.id}`, x: margin, y };
}

function dedupeVias(vias, config) {
    const seen = new Set();
    return vias.filter((via) => {
        via.x = snap(clamp(via.x, config.grid.margin, config.board.width - config.grid.margin), config.grid.cell);
        via.y = snap(clamp(via.y, config.grid.margin, config.board.height - config.grid.margin), config.grid.cell);
        const key = `${Math.round(via.x)},${Math.round(via.y)}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

