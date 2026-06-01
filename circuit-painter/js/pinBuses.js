// QFP pin buses (single-bus mode for now).
//
// We pick ONE source pin group (a run of adjacent pins on one chip edge) and
// connect it to the farthest QFP group on a *different* chip. Each pin is
// routed independently with A*, and every finished wire's cells are marked
// occupied before the next pin routes -- so a later wire physically cannot
// overlap an earlier one, and is instead pushed into the lane right beside it.
//
// A* runs in a Web Worker (pathfindClient.js) so slider-driven rebuilds don't
// freeze the UI. Geometry guarantee unchanged: only 8-adjacent steps.

import { params } from './params.js';
import {
    Wire, carveLeadWithFan, leadExitDir, sanitizePathRightAngles,
} from './wire.js';
import { getObstacles } from './obstacles.js';
import { serializeGrid, directionBetween } from './pathfindCore.js';
import { routePinBusCore } from './pinBusRouteCore.js';
import { routePinBusAsync } from './pathfindClient.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

const PIN_LEAD_LENGTH = 3;

export function generatePinBuses(grid, gridWidth, gridHeight) {
    const setup = preparePinBus(grid, gridWidth, gridHeight);
    if (!setup) return [];

    const { available, headings } = serializeGrid(grid, gridWidth, gridHeight);
    const paths = routePinBusCore(
        available,
        headings,
        gridWidth,
        gridHeight,
        setup.routes,
        setup.routeParams,
    );
    return buildWiresFromPaths(setup, paths, grid, gridWidth, gridHeight);
}

export async function generatePinBusesAsync(grid, gridWidth, gridHeight) {
    const setup = preparePinBus(grid, gridWidth, gridHeight);
    if (!setup) return [];

    const { available, headings } = serializeGrid(grid, gridWidth, gridHeight);
    const result = await routePinBusAsync({
        available,
        headings,
        gridWidth,
        gridHeight,
        routes: setup.routes,
        routeParams: setup.routeParams,
    });

    if (result.error) {
        const paths = routePinBusCore(
            available.slice(),
            headings.slice(),
            gridWidth,
            gridHeight,
            setup.routes,
            setup.routeParams,
        );
        return buildWiresFromPaths(setup, paths, grid, gridWidth, gridHeight);
    }

    return buildWiresFromPaths(setup, result.paths, grid, gridWidth, gridHeight);
}

function preparePinBus(grid, gridWidth, gridHeight) {
    const pins = collectQFPPins(grid, gridWidth, gridHeight);
    if (pins.length < 2) return null;

    const groups = buildPinGroups(pins);
    const pair = pickFarthestGroupPair(groups);
    if (!pair) return null;

    const wireCount = Math.max(1, params.pinBusWireCount | 0);
    const sourceCentroid = groupCentroid(pair.source);
    const targetCentroid = groupCentroid(pair.target);
    const srcPins = selectBusPins(pair.source, pins, targetCentroid, wireCount);
    const dstPins = selectBusPins(pair.target, pins, sourceCentroid, wireCount);

    for (const pin of srcPins) {
        pin.lead = carveLeadWithFan(
            pin.cell, pin.heading, PIN_LEAD_LENGTH,
            targetCentroid.x, targetCentroid.y,
            grid, gridWidth, gridHeight,
        );
        pin.tip = pin.lead[pin.lead.length - 1];
    }
    for (const pin of dstPins) {
        pin.lead = carveLeadWithFan(
            pin.cell, pin.heading, PIN_LEAD_LENGTH,
            sourceCentroid.x, sourceCentroid.y,
            grid, gridWidth, gridHeight,
        );
        pin.tip = pin.lead[pin.lead.length - 1];
    }

    const ux = targetCentroid.x - sourceCentroid.x;
    const uy = targetCentroid.y - sourceCentroid.y;
    const len = Math.hypot(ux, uy) || 1;
    const px = -uy / len;
    const py = ux / len;
    const across = (pin) => pin.tip.x * px + pin.tip.y * py;

    const src = srcPins.slice().sort((a, b) => across(a) - across(b));
    const dst = dstPins.slice().sort((a, b) => across(a) - across(b));
    const n = Math.min(src.length, dst.length);

    const routes = [];
    const wireMeta = [];
    for (let i = 0; i < n; i++) {
        const s = src[i];
        const d = dst[i];
        const exitDir = leadExitDir(s.lead);
        routes.push({
            srcTip: { x: s.tip.x, y: s.tip.y },
            dstTip: { x: d.tip.x, y: d.tip.y },
            startDir: exitDir >= 0 ? exitDir : s.heading,
        });
        wireMeta.push({ srcLead: s.lead, dstLead: d.lead });
    }

    return {
        routes,
        wireMeta,
        routeParams: {
            segMin: params.pinBusSlantLength,
            segMax: params.pinBusStraightMax,
            turnSmoothness: params.turnSmoothness,
            diagonalChance: params.diagonalChance,
        },
    };
}

function buildWiresFromPaths(setup, paths, grid, gridWidth, gridHeight) {
    const wires = [];
    for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        if (!path || path.length < 2) continue;

        const { srcLead, dstLead } = setup.wireMeta[i];
        applyPathToGrid(grid, path);
        const dstLeadInward = dstLead.slice().reverse();
        const cells = [
            ...srcLead,
            ...path.slice(1).map(({ x, y }) => grid[x][y]),
            ...dstLeadInward.slice(1),
        ];
        sanitizePathRightAngles(cells, grid, gridWidth, gridHeight);
        wires.push(makePinWire(cells, grid, gridWidth, gridHeight));
    }
    return wires;
}

function applyPathToGrid(grid, path) {
    for (let i = 1; i < path.length; i++) {
        const c = grid[path[i].x][path[i].y];
        c.available = false;
        c.heading = directionBetween(path[i - 1], path[i]);
    }
}

function selectBusPins(group, allPins, partnerCentroid, count) {
    const chosen = group.pins.slice();
    if (chosen.length < count) {
        const inBus = new Set(chosen);
        const extras = allPins
            .filter((p) => p.chipIndex === group.chipIndex && !inBus.has(p))
            .sort((a, b) => dist2(a, partnerCentroid) - dist2(b, partnerCentroid));
        for (const p of extras) {
            chosen.push(p);
            if (chosen.length >= count) break;
        }
    }
    return chosen.slice(0, count);
}

function dist2(pin, c) {
    const dx = pin.x - c.x;
    const dy = pin.y - c.y;
    return dx * dx + dy * dy;
}

function collectQFPPins(grid, gridWidth, gridHeight) {
    const pins = [];
    if (!params.qfpStyle) return pins;

    const obstacles = getObstacles();
    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const inBounds = (x, y) => x >= 0 && y >= 0 && x < gridWidth && y < gridHeight;

    for (let chipIndex = 0; chipIndex < obstacles.length; chipIndex++) {
        const o = obstacles[chipIndex];
        if (!o.qfp) continue;

        const add = (x, y, heading) => {
            if (!inBounds(x, y)) return;
            pins.push({ x, y, heading, chipIndex, cell: grid[x][y], lead: null, tip: null });
        };

        for (let i = 0; i < o.w; i += spacing) add(o.x + i, o.y - 1, 1);
        for (let j = 0; j < o.h; j += spacing) add(o.x + o.w, o.y + j, 3);
        for (let i = 0; i < o.w; i += spacing) add(o.x + i, o.y + o.h, 5);
        for (let j = 0; j < o.h; j += spacing) add(o.x - 1, o.y + j, 7);
    }

    for (const pin of pins) {
        pin.cell.available = false;
        pin.cell.heading = pin.heading;
    }

    return pins;
}

function buildPinGroups(pins) {
    const bySide = new Map();
    for (const pin of pins) {
        const key = `${pin.chipIndex}:${pin.heading}`;
        if (!bySide.has(key)) bySide.set(key, []);
        bySide.get(key).push(pin);
    }

    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const groups = [];

    for (const sidePins of bySide.values()) {
        sortPinsAlongEdge(sidePins);
        let run = [sidePins[0]];
        for (let i = 1; i < sidePins.length; i++) {
            if (edgeGap(sidePins[i - 1], sidePins[i]) <= spacing) {
                run.push(sidePins[i]);
            } else {
                groups.push(makeGroup(run));
                run = [sidePins[i]];
            }
        }
        groups.push(makeGroup(run));
    }

    return groups;
}

function makeGroup(pins) {
    return { chipIndex: pins[0].chipIndex, heading: pins[0].heading, pins };
}

function sortPinsAlongEdge(pins) {
    const h = pins[0].heading;
    if (h === 1 || h === 5) pins.sort((a, b) => a.x - b.x);
    else pins.sort((a, b) => a.y - b.y);
}

function edgeGap(a, b) {
    if (a.heading === 1 || a.heading === 5) return Math.abs(a.x - b.x);
    return Math.abs(a.y - b.y);
}

function pickFarthestGroupPair(groups) {
    let facing = null;
    let facingDist = -1;
    let any = null;
    let anyDist = -1;

    for (let i = 0; i < groups.length; i++) {
        for (let j = i + 1; j < groups.length; j++) {
            const a = groups[i];
            const b = groups[j];
            if (a.chipIndex === b.chipIndex) continue;
            if (a.pins.length < 2 || b.pins.length < 2) continue;

            const ca = groupCentroid(a);
            const cb = groupCentroid(b);
            const abx = cb.x - ca.x;
            const aby = cb.y - ca.y;
            const dist = Math.hypot(abx, aby);
            if (dist === 0) continue;

            const pair = a.pins.length >= b.pins.length
                ? { source: a, target: b }
                : { source: b, target: a };

            if (dist > anyDist) { anyDist = dist; any = pair; }

            const aTowardB = (DIRS[a.heading][0] * abx + DIRS[a.heading][1] * aby);
            const bTowardA = (DIRS[b.heading][0] * -abx + DIRS[b.heading][1] * -aby);
            if (aTowardB > 0 && bTowardA > 0 && dist > facingDist) {
                facingDist = dist;
                facing = pair;
            }
        }
    }

    return facing || any;
}

function groupCentroid(group) {
    let sx = 0;
    let sy = 0;
    for (const p of group.pins) { sx += p.x; sy += p.y; }
    return { x: sx / group.pins.length, y: sy / group.pins.length };
}

function makePinWire(cells, grid, gridWidth, gridHeight) {
    const wire = new Wire(cells[0], grid, gridWidth, gridHeight);
    wire.cells = cells;
    wire.isBus = true;
    wire.isQFPPin = true;
    return wire;
}
