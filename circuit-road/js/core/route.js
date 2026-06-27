import { centerOf, clamp, dist, snap } from './geometry.js';

export function buildRoadNetwork(rng, parts, config) {
    const traces = [];
    const vias = [];
    const majorParts = parts.filter((part) => ['qfp', 'ic', 'busBlock', 'padCluster'].includes(part.kind));
    const smallParts = parts.filter((part) => !majorParts.includes(part));
    const usedPins = new Set();
    const corridors = buildCorridors(config);

    for (const [a, b] of nearestMajorPairs(majorParts, config.route.majorLinks)) {
        const lanes = rng.int(config.route.busLaneRange[0], config.route.busLaneRange[1]);
        const aPins = pinsFacing(a, b).filter((pin) => !usedPins.has(pin.id)).slice(0, lanes);
        const bPins = pinsFacing(b, a).filter((pin) => !usedPins.has(pin.id)).slice(0, lanes);
        const laneCount = Math.min(aPins.length, bPins.length);
        for (let i = 0; i < laneCount; i++) {
            const trace = makeTrace(rng, aPins[i], bPins[laneCount - 1 - i], config, corridors, 'bus', i);
            traces.push(trace);
            usedPins.add(aPins[i].id);
            usedPins.add(bPins[laneCount - 1 - i].id);
            maybeAddVia(rng, trace, vias, config.vias.traceChance);
        }
    }

    for (let i = 0; i < config.route.localLinks; i++) {
        const small = smallParts[i % smallParts.length];
        if (!small) break;
        const anchor = nearestPart(small, majorParts, config.route.localMaxDist);
        if (!anchor) continue;
        const openSmallPins = small.pins.filter((pin) => !usedPins.has(pin.id));
        const from = rng.pick(openSmallPins.length ? openSmallPins : small.pins);
        const to = closestFreePin(from, anchor.pins, usedPins) ?? rng.pick(anchor.pins);
        if (!from || !to) continue;
        traces.push(makeTrace(rng, from, to, config, corridors, 'local', i % 3));
        usedPins.add(from.id);
        usedPins.add(to.id);
    }

    for (let i = 0; i < config.route.branchLinks; i++) {
        const sourcePart = rng.pick(majorParts);
        const source = rng.pick(sourcePart.pins);
        const via = makeBranchVia(rng, source, config);
        vias.push(via);
        traces.push(makeTrace(rng, source, via, config, corridors, 'branch', i % 2));
    }

    for (let i = 0; i < config.route.edgeBranches; i++) {
        const sourcePart = rng.pick(majorParts);
        const source = rng.pick(sourcePart.pins);
        const via = makeEdgeVia(rng, source, config);
        vias.push(via);
        traces.push(makeTrace(rng, source, via, config, corridors, 'branch', i % 2));
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

function makeTrace(rng, from, to, config, corridors, kind, laneIndex = 0) {
    const points = corridorPath(rng, from, to, config, corridors, laneIndex, kind);
    return {
        kind,
        points,
        from: from.id,
        to: to.id,
    };
}

function buildCorridors(config) {
    const levels = [];
    const { margin } = config.grid;
    const { width, height } = config.board;
    const pitch = config.route.lanePitch;
    const gap = config.route.corridorGap;

    for (let y = margin + gap; y < height - margin; y += gap) {
        levels.push({ axis: 'h', value: snap(y, pitch) });
        levels.push({ axis: 'h', value: snap(y + pitch, pitch) });
    }
    for (let x = margin + gap; x < width - margin; x += gap) {
        levels.push({ axis: 'v', value: snap(x, pitch) });
        levels.push({ axis: 'v', value: snap(x + pitch, pitch) });
    }
    return levels;
}

function corridorPath(rng, from, to, config, corridors, laneIndex, kind) {
    const cell = config.grid.cell;
    const start = anchorPoint(from, config);
    const end = anchorPoint(to, config);
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const sx = Math.sign(dx) || (rng.chance(0.5) ? 1 : -1);
    const sy = Math.sign(dy) || (rng.chance(0.5) ? 1 : -1);
    const chamfer = Math.min(config.route.chamfer, Math.abs(dx) / 3, Math.abs(dy) / 3);
    const horizontalFirst = Math.abs(dx) >= Math.abs(dy);
    const laneOffset = (laneIndex - 1.5) * config.route.lanePitch;
    const points = [start];

    if (horizontalFirst) {
        const corridorY = nearestCorridor(corridors, 'h', (start.y + end.y) / 2 + laneOffset, config);
        const leadA = clamp(start.x + sx * leadLength(kind, rng, config), config.grid.margin, config.board.width - config.grid.margin);
        const leadB = clamp(end.x - sx * leadLength(kind, rng, config), config.grid.margin, config.board.width - config.grid.margin);
        points.push({ x: snap(leadA, cell), y: start.y });
        pushDiagonal(points, { x: snap(leadA, cell), y: corridorY }, chamfer, sx, Math.sign(corridorY - start.y) || sy);
        points.push({ x: snap(leadB, cell), y: corridorY });
        pushDiagonal(points, { x: snap(leadB, cell), y: end.y }, chamfer, sx, Math.sign(end.y - corridorY) || sy);
    } else {
        const corridorX = nearestCorridor(corridors, 'v', (start.x + end.x) / 2 + laneOffset, config);
        const leadA = clamp(start.y + sy * leadLength(kind, rng, config), config.grid.margin, config.board.height - config.grid.margin);
        const leadB = clamp(end.y - sy * leadLength(kind, rng, config), config.grid.margin, config.board.height - config.grid.margin);
        points.push({ x: start.x, y: snap(leadA, cell) });
        pushDiagonal(points, { x: corridorX, y: snap(leadA, cell) }, chamfer, Math.sign(corridorX - start.x) || sx, sy);
        points.push({ x: corridorX, y: snap(leadB, cell) });
        pushDiagonal(points, { x: end.x, y: snap(leadB, cell) }, chamfer, Math.sign(end.x - corridorX) || sx, sy);
    }

    points.push(end);
    return compactPoints(points);
}

function nearestCorridor(corridors, axis, target, config) {
    const candidates = corridors.filter((corridor) => corridor.axis === axis);
    const fallback = axis === 'h' ? config.board.height / 2 : config.board.width / 2;
    const best = candidates.sort((a, b) => Math.abs(a.value - target) - Math.abs(b.value - target))[0]?.value ?? fallback;
    const limit = axis === 'h' ? config.board.height : config.board.width;
    return snap(clamp(best, config.grid.margin, limit - config.grid.margin), config.grid.cell);
}

function leadLength(kind, rng, config) {
    if (kind === 'branch') return rng.float(18, 42);
    if (kind === 'local') return rng.float(22, 56);
    return rng.float(34, 76);
}

function pushDiagonal(points, target, chamfer, sx, sy) {
    const prev = points[points.length - 1];
    const dx = target.x - prev.x;
    const dy = target.y - prev.y;
    if (Math.abs(dx) <= chamfer || Math.abs(dy) <= chamfer) {
        points.push(target);
        return;
    }
    points.push({ x: target.x - sx * chamfer, y: prev.y });
    points.push({ x: target.x, y: prev.y + sy * chamfer });
    points.push(target);
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
    const length = rng.float(config.route.branchLength[0], config.route.branchLength[1]);
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

