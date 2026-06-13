// QFP pin buses: full-board connection planner.
//
// Chips are joined by sparse, face-to-face buses. The planner considers nearby
// chips in spanning-tree order, but it only accepts pin groups that point into a
// shared gap; if the clean gap is not there, the connection is skipped instead
// of wrapping around a component. Leftover pins only occasionally grow small
// stubs, matching the reference boards where many pins remain visually quiet.
//
// Each wire is routed independently with A*, and every finished wire's cells
// are marked occupied before the next pin routes -- so a later wire physically
// cannot overlap an earlier one, and is instead pushed into the lane right
// beside it. Corners ≤ 90° are forbidden in the search itself; only 45° bends
// (135° interior angles) exist.
//
// A* runs in a Web Worker (pathfindClient.js) so slider-driven rebuilds don't
// freeze the UI. Geometry guarantee unchanged: only 8-adjacent steps.

import { pinCellOffsets, pinGroups } from './components.js';
import { computeRoutingClearance } from './corridorGeom.js';
import { getObstacles } from './obstacles.js';
import { params } from './params.js';
import { routePinBusAsync } from './pathfindClient.js';
import {
    directionBetween, inRouteBounds,
    serializeGrid,
    turnDelta,
} from './pathfindCore.js';
import { routePinBusCore } from './pinBusRouteCore.js';
import { rnd, rndInt } from './rng.js';
import {
    Wire, carveLeadWithFan, leadExitDir, sanitizePathRightAngles,
} from './wire.js';

const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

const PIN_LEAD_LENGTH = 3;
const ACTIVE_LANE_CAP = 4;
const MIN_CLEARANCE_TARGET = 6;
const MIN_CLEARANCE_WEIGHT = 0.9;
const MIN_CORRIDOR_WEIGHT = 0.18;
const TAP_CORRIDOR_WEIGHT = 0.55;
const BACKBONE_LANES = 3;
const BACKBONE_LANE_SPACING = 2;
const BACKBONE_MIN_SEGMENT = 9;
const BACKBONE_MIN_CLEARANCE = 2;
const BACKBONE_SAMPLE_STEP = 14;
const BACKBONE_WAVE = 3;

// Chance an unused facing group pair gets a bonus bus beyond the MST. Kept low
// so the board reads like the reference: a few deliberate trunks, not every pin.
const EXTRA_BUS_CHANCE = 0.25;
// Leftover pins: a few wander off as longer meandering traces, more grow short
// stubs. Both are blind walks that stop when blocked (never A*), so they can
// never loop around obstacles into giant arcs.
const WANDER_CHANCE = 0.02;
const STUB_CHANCE = 0.12;

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

// === Planning ===============================================================

function preparePinBus(grid, gridWidth, gridHeight) {
    const pins = collectQFPPins(grid, gridWidth, gridHeight);
    if (!pins.length) return null;

    const groups = buildPinGroups(pins);
    const chips = collectChips(groups);

    const routes = [];
    const wireMeta = [];
    const usedPins = new Set();
    const backbone = buildBackboneWires(grid, gridWidth, gridHeight);
    const pairStartGroup = appendBackboneTapRoutes(
        chips, backbone.cells, grid, gridWidth, gridHeight, routes, wireMeta, usedPins,
    );

    // Generator boards route through the shared spine. Extra chip-to-chip MST
    // edges make small obstacle moves reshuffle the whole topology, which feels
    // like the lines jump violently instead of adapting locally.
    if (!params.generatorChipsOnly || !backbone.cells.length) {
        const plans = planConnections(chips);
        for (let p = 0; p < plans.length; p++) {
            appendBusRoutes(
                plans[p],
                pairStartGroup + p,
                grid,
                gridWidth,
                gridHeight,
                routes,
                wireMeta,
                usedPins,
            );
        }
    }

    const leftovers = pins.filter((p) => !usedPins.has(p));
    const stubPlans = [];
    for (const pin of leftovers) {
        const wanderChance = params.thinPcbProcedural ? 0.05 : WANDER_CHANCE;
        const stubChance = params.thinPcbProcedural ? 0.36 : STUB_CHANCE;
        const roll = rnd();
        if (roll < wanderChance) {
            stubPlans.push({ pin, segs: rollWanderSegments() });
        } else if (roll < wanderChance + stubChance) {
            stubPlans.push({ pin, segs: rollStubSegments() });
        }
    }

    const clearance = params.obstaclesEnabled
        ? computeRoutingClearance(gridWidth, gridHeight)
        : null;
    const clearanceTarget = Math.max(MIN_CLEARANCE_TARGET, params.routeClearanceTarget | 0);
    const clearanceWeight = clearance && clearanceTarget > 0
        ? Math.max(MIN_CLEARANCE_WEIGHT, params.routeClearanceBias)
        : 0;

    return {
        routes,
        wireMeta,
        backboneWires: backbone.wires,
        stubPlans,
        routeParams: {
            segMin: params.pinBusSlantLength,
            segMax: params.pinBusStraightMax,
            turnSmoothness: params.turnSmoothness,
            diagonalChance: params.diagonalChance,
            clearance,
            clearanceTarget,
            clearanceWeight,
            corridorWeight: Math.max(MIN_CORRIDOR_WEIGHT, params.pinBusCorridorWeight ?? 0),
            tapCorridorWeight: TAP_CORRIDOR_WEIGHT,
            maxDetourRatio: params.pinBusMaxDetourRatio,
            obstacles: getObstacles().map((o) => ({ x: o.x, y: o.y, w: o.w, h: o.h })),
        },
    };
}

// Chips that can anchor a bus: at least one pin group with 2+ pins.
function collectChips(groups) {
    const obstacles = getObstacles();
    const byChip = new Map();
    for (const g of groups) {
        if (g.pins.length < 2) continue;
        if (!byChip.has(g.chipIndex)) byChip.set(g.chipIndex, []);
        byChip.get(g.chipIndex).push(g);
    }

    const chips = [];
    for (const [chipIndex, chipGroups] of byChip) {
        const o = obstacles[chipIndex];
        chips.push({
            chipIndex,
            cx: o.x + o.w / 2,
            cy: o.y + o.h / 2,
            groups: chipGroups,
        });
    }
    return chips;
}

// Spanning-tree order gives each chip chances to join nearby neighbors; strict
// facing checks decide which links are actually drawn. Extra facing pairs add
// a little density. Plans are sorted by distance so short local buses route
// first and long links bend around them.
function planConnections(chips) {
    if (chips.length < 2) return [];

    const usedGroups = new Set();
    const plans = [];

    const tryPlan = (chipA, chipB, maxWires) => {
        const pair = bestGroupPair(chipA, chipB, usedGroups);
        if (!pair) return false;
        usedGroups.add(pair.source);
        usedGroups.add(pair.target);
        plans.push({ ...pair, maxWires });
        return true;
    };

    const dist = (a, b) => Math.hypot(a.cx - b.cx, a.cy - b.cy);
    const cap = Math.max(1, Math.min(ACTIVE_LANE_CAP, params.pinBusWireCount | 0));

    // Prim-style growth with repair: each new chip tries its nearest connected
    // chips first. If every possible edge faces the wrong way, we leave it quiet
    // rather than drawing a loop around another mesh.
    const connected = [chips[0]];
    const remaining = chips.slice(1);
    while (remaining.length) {
        let nearestIdx = 0;
        let nearestDist = Infinity;
        for (let r = 0; r < remaining.length; r++) {
            for (const c of connected) {
                const d = dist(remaining[r], c);
                if (d < nearestDist) {
                    nearestDist = d;
                    nearestIdx = r;
                }
            }
        }
        const [chip] = remaining.splice(nearestIdx, 1);
        const candidates = connected.slice().sort((a, b) => dist(chip, a) - dist(chip, b));
        for (const partner of candidates) {
            if (tryPlan(chip, partner, cap)) break;
        }
        connected.push(chip);
    }

    const extras = [];
    for (let i = 0; i < chips.length; i++) {
        for (let j = i + 1; j < chips.length; j++) {
            extras.push({ i, j, d: dist(chips[i], chips[j]) });
        }
    }
    extras.sort((a, b) => a.d - b.d);
    for (const { i, j } of extras) {
        if (rnd() >= EXTRA_BUS_CHANCE) continue;
        tryPlan(chips[i], chips[j], Math.min(cap, 2 + rndInt(3)));
    }

    plans.sort((a, b) => a.dist - b.dist);
    return plans;
}

// Pick the unused group on each chip whose outward normals point at each other
// the most. A group pointing away from the partner chip would force the bus to
// arc all the way around its own chip body (giant empty loops), so only pairs
// where both sides clearly point at each other are used.
function bestGroupPair(chipA, chipB, usedGroups) {
    let bestFacing = null;

    for (const ga of chipA.groups) {
        if (usedGroups.has(ga)) continue;
        for (const gb of chipB.groups) {
            if (usedGroups.has(gb)) continue;

            const ca = groupCentroid(ga);
            const cb = groupCentroid(gb);
            const dx = cb.x - ca.x;
            const dy = cb.y - ca.y;
            const dist = Math.hypot(dx, dy);
            if (dist === 0) continue;

            const fa = (DIRS[ga.heading][0] * dx + DIRS[ga.heading][1] * dy) / dist;
            const fb = -(DIRS[gb.heading][0] * dx + DIRS[gb.heading][1] * dy) / dist;
            if (Math.min(fa, fb) <= -0.05) continue;

            // Opposite-heading (parallel) edges pair lane-for-lane without the
            // 90° fan-around that perpendicular edges force in tight gaps.
            const parallel = gb.heading === (ga.heading + 4) % 8 ? 0.5 : 0;
            const score = fa + fb + parallel;
            const candidate = { source: ga, target: gb, dist, score };
            if (Math.min(fa, fb) > 0.1 && (!bestFacing || score > bestFacing.score)) {
                bestFacing = candidate;
            }
        }
    }

    return bestFacing || null;
}

// === Bus route construction =================================================

function appendBusRoutes(plan, group, grid, gridWidth, gridHeight, routes, wireMeta, usedPins) {
    const sourceCentroid = groupCentroid(plan.source);
    const targetCentroid = groupCentroid(plan.target);
    const availableSourcePins = plan.source.pins.filter((pin) => !usedPins.has(pin));
    const availableTargetPins = plan.target.pins.filter((pin) => !usedPins.has(pin));
    if (!availableSourcePins.length || !availableTargetPins.length) return;
    const sourceGroup = { ...plan.source, pins: availableSourcePins };
    const targetGroup = { ...plan.target, pins: availableTargetPins };
    // Tight gaps can't hold many parallel lanes: cap the lane count by the
    // distance the bus spans, so neighbors get 1-2 traces and far chips get
    // full buses.
    const count = Math.max(1, Math.min(
        plan.maxWires,
        sourceGroup.pins.length,
        targetGroup.pins.length,
        Math.round(plan.dist / 5),
    ));
    const srcPins = pickBusPins(sourceGroup, count, targetCentroid);
    const dstPins = pickBusPins(targetGroup, count, sourceCentroid);

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

    // Pair pins by their order across the bus axis so lanes never have to cross.
    const ux = targetCentroid.x - sourceCentroid.x;
    const uy = targetCentroid.y - sourceCentroid.y;
    const len = Math.hypot(ux, uy) || 1;
    const px = -uy / len;
    const py = ux / len;
    const across = (pin) => pin.tip.x * px + pin.tip.y * py;
    const centerCorridor = {
        ax: sourceCentroid.x,
        ay: sourceCentroid.y,
        bx: targetCentroid.x,
        by: targetCentroid.y,
        radius: Math.max(1, count / 2),
    };

    const src = srcPins.slice().sort((a, b) => across(a) - across(b));
    const dst = dstPins.slice().sort((a, b) => across(a) - across(b));
    const n = Math.min(src.length, dst.length);
    const laneSpread = Math.max(1, params.busLineSpacing | 0) + 1;

    const lanes = [];
    for (let i = 0; i < n; i++) {
        const s = src[i];
        const d = dst[i];
        usedPins.add(s);
        usedPins.add(d);
        const exitDir = leadExitDir(s.lead);
        let startDir = exitDir >= 0 ? exitDir : s.heading;
        // If the destination sits behind the lead's exit, forcing the exit
        // direction makes A* curl a tight 360° knot right at the pin. Free the
        // start instead; sanitizePathRightAngles smooths the joint.
        const desired = directionBetween(s.tip, d.tip);
        const delta = turnDelta(startDir, desired);
        if (delta >= 3 && delta <= 5) startDir = -1;
        // The wire continues from the dst tip backwards down the dst lead, so
        // the required arrival direction is the reverse of the lead's own exit
        // (which includes the 45° fan step) -- not the pin's axis.
        const dstExit = leadExitDir(d.lead);
        const endDir = ((dstExit >= 0 ? dstExit : d.heading) + 4) % 8;
        const laneOffset = i - (n - 1) / 2;
        lanes.push({
            route: {
                srcTip: { x: s.tip.x, y: s.tip.y },
                dstTip: { x: d.tip.x, y: d.tip.y },
                startDir,
                endDir,
                group,
                bounds: makeRouteBounds(s.tip, d.tip, gridWidth, gridHeight),
                corridor: {
                    ax: centerCorridor.ax + px * laneOffset * laneSpread,
                    ay: centerCorridor.ay + py * laneOffset * laneSpread,
                    bx: centerCorridor.bx + px * laneOffset * laneSpread,
                    by: centerCorridor.by + py * laneOffset * laneSpread,
                    radius: centerCorridor.radius,
                },
                sourceChipIndex: plan.source.chipIndex,
                targetChipIndex: plan.target.chipIndex,
            },
            meta: { srcLead: s.lead, dstLead: d.lead },
        });
    }

    // Route the longest lane first: it takes the outermost arc, and shorter
    // lanes nest inside it. Routing short lanes first lets their paths cut
    // between a pending tip and its destination, entombing the lane entirely.
    lanes.sort((a, b) => laneSpan(b.route) - laneSpan(a.route));
    for (const lane of lanes) {
        routes.push(lane.route);
        wireMeta.push(lane.meta);
    }
}

function makeRouteBounds(a, b, gridWidth, gridHeight) {
    const margin = Math.max(6, params.pinBusRouteMargin | 0);
    return {
        minX: Math.max(1, Math.min(a.x, b.x) - margin),
        minY: Math.max(1, Math.min(a.y, b.y) - margin),
        maxX: Math.min(gridWidth - 2, Math.max(a.x, b.x) + margin),
        maxY: Math.min(gridHeight - 2, Math.max(a.y, b.y) + margin),
    };
}

function laneSpan(route) {
    return Math.max(
        Math.abs(route.srcTip.x - route.dstTip.x),
        Math.abs(route.srcTip.y - route.dstTip.y),
    );
}

function appendBackboneTapRoutes(chips, backboneCells, grid, gridWidth, gridHeight, routes, wireMeta, usedPins) {
    if (!params.generatorChipsOnly || !backboneCells.length) return 0;

    const spineY = average(backboneCells.map((c) => c.y));
    const usedAnchors = new Set();
    let group = 0;
    for (const chip of chips) {
        const source = bestTapGroup(chip, spineY, usedPins);
        if (!source) continue;

        const sourceCentroid = groupCentroid(source);
        const count = Math.max(1, Math.min(
            source.kind === 'aux' ? 2 : 3,
            source.pins.length,
            Math.max(1, Math.round(params.pinBusWireCount / 2)),
        ));
        const srcPins = pickBusPins(source, count, { x: sourceCentroid.x, y: spineY });

        for (let i = 0; i < srcPins.length; i++) {
            const pin = srcPins[i];
            const anchor = aestheticBackboneAnchor(
                backboneCells, pin, sourceCentroid, spineY, i, srcPins.length, usedAnchors,
            );
            if (!anchor) continue;
            usedAnchors.add(`${anchor.x},${anchor.y}`);
            pin.lead = carveLeadWithFan(
                pin.cell, pin.heading, PIN_LEAD_LENGTH,
                anchor.x, anchor.y,
                grid, gridWidth, gridHeight,
            );
            pin.tip = pin.lead[pin.lead.length - 1];
            usedPins.add(pin);

            const exitDir = leadExitDir(pin.lead);
            const startDir = exitDir >= 0 ? exitDir : pin.heading;
            routes.push({
                srcTip: { x: pin.tip.x, y: pin.tip.y },
                dstTip: { x: anchor.x, y: anchor.y },
                startDir,
                endDir: anchor.heading >= 0 ? anchor.heading : -1,
                group,
                tap: true,
                bounds: makeTapRouteBounds(pin.tip, anchor, gridWidth, gridHeight),
                corridor: {
                    ax: sourceCentroid.x,
                    ay: sourceCentroid.y,
                    bx: anchor.x,
                    by: anchor.y,
                    radius: Math.max(1, count / 2),
                },
                sourceChipIndex: chip.chipIndex,
                targetChipIndex: -1,
            });
            wireMeta.push({ srcLead: pin.lead, dstLead: [grid[anchor.x][anchor.y]] });
        }
        group++;
    }

    return group;
}

function bestTapGroup(chip, spineY, usedPins) {
    let best = null;
    for (const group of chip.groups) {
        if (group.pins.every((p) => usedPins.has(p))) continue;
        const c = groupCentroid(group);
        const towardSpine = spineY >= c.y ? 5 : 1;
        const facing = group.heading === towardSpine ? 2 : 0;
        const distance = Math.abs(c.y - spineY);
        const auxBonus = group.kind === 'aux' ? 4 : 0;
        const score = facing + auxBonus - distance * 0.03;
        if (!best || score > best.score) best = { group, score };
    }
    return best?.group || null;
}

function aestheticBackboneAnchor(
    backboneCells, pin, sourceCentroid, spineY, laneIndex, laneCount, usedAnchors,
) {
    const side = Math.sign(sourceCentroid.x - pin.x) || 1;
    const stagger = laneIndex - (laneCount - 1) / 2;
    const targetX = pin.x + side * (5 + Math.abs(stagger) * 3);
    let best = null;
    let bestScore = Infinity;
    for (const cell of backboneCells) {
        const dx = cell.x - targetX;
        const dy = cell.y - pin.y;
        const sidePenalty = Math.sign(cell.x - pin.x) === side ? 0 : 18;
        const verticalBias = Math.abs(cell.y - spineY) * 0.8;
        const reusePenalty = usedAnchors?.has(`${cell.x},${cell.y}`) ? 800 : 0;
        const score = dx * dx + dy * dy * 0.35 + sidePenalty + verticalBias + reusePenalty;
        if (score < bestScore) {
            bestScore = score;
            best = cell;
        }
    }
    return best;
}

function average(values) {
    return values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length);
}

function makeTapRouteBounds(a, b, gridWidth, gridHeight) {
    const margin = Math.max(14, (params.pinBusRouteMargin | 0) + 8);
    return {
        minX: Math.max(1, Math.min(a.x, b.x) - margin),
        minY: Math.max(1, Math.min(a.y, b.y) - margin),
        maxX: Math.min(gridWidth - 2, Math.max(a.x, b.x) + margin),
        maxY: Math.min(gridHeight - 2, Math.max(a.y, b.y) + margin),
    };
}

// Contiguous run of `count` pins whose center sits closest to the partner
// group, so the bus leaves the edge nearest its destination.
function pickBusPins(group, count, toward) {
    const pins = group.pins.slice();
    sortPinsAlongEdge(pins);
    if (pins.length <= count) return pins;

    const horizontal = group.heading === 1 || group.heading === 5;
    const coord = (p) => (horizontal ? p.x : p.y);
    const target = horizontal ? toward.x : toward.y;

    let bestOffset = 0;
    let bestDelta = Infinity;
    for (let off = 0; off + count <= pins.length; off++) {
        const center = (coord(pins[off]) + coord(pins[off + count - 1])) / 2;
        const delta = Math.abs(center - target);
        if (delta < bestDelta) {
            bestDelta = delta;
            bestOffset = off;
        }
    }
    return pins.slice(bestOffset, bestOffset + count);
}

// === Stub / wander segment plans ============================================
//
// `segs` are heading offsets relative to the pin's outward direction plus a
// length; offsets are cumulative and only change by ±1 (45°) per segment, so a
// walked stub can never contain a corner sharper than 135°.

function rollStubSegments() {
    const segs = [{ off: 0, len: 1 + rndInt(4) }];
    if (rnd() < 0.55) {
        segs.push({ off: rnd() < 0.5 ? 1 : -1, len: 2 + rndInt(4) });
    }
    return segs;
}

function rollWanderSegments() {
    const sign = rnd() < 0.5 ? 1 : -1;
    const segs = [
        { off: 0, len: 2 + rndInt(5) },
        { off: sign, len: 2 + rndInt(6) },
    ];
    if (rnd() < 0.7) segs.push({ off: 0, len: 3 + rndInt(7) });
    if (rnd() < 0.4) segs.push({ off: -sign, len: 2 + rndInt(6) });
    return segs;
}

// === Wire assembly ==========================================================

function buildWiresFromPaths(setup, paths, grid, gridWidth, gridHeight) {
    const wires = setup.backboneWires.slice();
    const backboneKeys = backboneCellKeySet(setup.backboneWires);

    for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        const route = setup.routes[i];
        const { srcLead, dstLead } = setup.wireMeta[i];

        if (!path || path.length < 2) {
            // Routing failed: leave the pin visually quiet. The reference board
            // has many bare pins; drawing every failed lead as a dangling trace
            // makes the design look busy and implies a connection that was not
            // actually routed.
            continue;
        }

        const routed = route?.tap && backboneKeys.size
            ? trimPathBeforeBackbone(path, backboneKeys)
            : path;
        if (routed.length < 2) continue;

        applyPathToGrid(grid, routed);
        const dstLeadInward = route?.tap ? [] : dstLead.slice().reverse();
        const cells = [
            ...srcLead,
            ...routed.slice(1).map(({ x, y }) => grid[x][y]),
            ...dstLeadInward.slice(1),
        ];
        sanitizePathRightAngles(cells, grid, gridWidth, gridHeight);
        wires.push(makePinWire(spliceRevisitLoops(cells), grid, gridWidth, gridHeight));
    }

    for (const plan of setup.stubPlans) {
        const cells = growStub(plan, grid, gridWidth, gridHeight);
        if (cells.length >= 2) wires.push(makeStubWire(cells, grid, gridWidth, gridHeight));
    }

    return wires;
}

function buildBackboneWires(grid, gridWidth, gridHeight) {
    if (!params.generatorChipsOnly) return { wires: [], cells: [] };

    const obstacles = getObstacles();
    if (obstacles.length < 3) return { wires: [], cells: [] };

    const clearance = computeRoutingClearance(gridWidth, gridHeight);
    const y = chooseBackboneRow(obstacles, clearance, grid, gridWidth, gridHeight);
    if (y === null) return { wires: [], cells: [] };

    const minX = Math.max(1, Math.min(...obstacles.map((o) => o.x)) - 8);
    const maxX = Math.min(
        gridWidth - 2,
        Math.max(...obstacles.map((o) => o.x + o.w)) + 8,
    );
    const lanes = centeredLaneRows(y, gridHeight);
    const wires = [];
    const cells = [];

    for (const laneY of lanes) {
        const path = buildBackboneLane(minX, maxX, laneY, y, clearance, grid, gridWidth, gridHeight);
        for (const run of splitOpenRuns(path, grid, gridHeight, clearance)) {
            if (run.length < BACKBONE_MIN_SEGMENT) continue;
            sanitizePathRightAngles(run, grid, gridWidth, gridHeight);
            commitBackboneRun(run);
            wires.push(makeBackboneWire(run, grid, gridWidth, gridHeight));
            cells.push(...run);
        }
    }

    return { wires, cells };
}

function buildBackboneLane(minX, maxX, laneY, centerY, clearance, grid, gridWidth, gridHeight) {
    const anchors = [];
    for (let x = minX; x <= maxX; x += BACKBONE_SAMPLE_STEP) {
        anchors.push({ x, y: chooseLaneY(x, laneY, centerY, clearance, grid, gridWidth, gridHeight) });
    }
    if (anchors[anchors.length - 1]?.x !== maxX) {
        anchors.push({ x: maxX, y: chooseLaneY(maxX, laneY, centerY, clearance, grid, gridWidth, gridHeight) });
    }

    const path = [];
    for (let i = 1; i < anchors.length; i++) {
        const segment = walkBackboneSegment(anchors[i - 1], anchors[i]);
        if (!path.length) path.push(...segment);
        else path.push(...segment.slice(1));
    }
    return path;
}

function chooseLaneY(x, laneY, centerY, clearance, grid, gridWidth, gridHeight) {
    const wave = Math.round(Math.sin(x / 18) * BACKBONE_WAVE);
    const desired = laneY + wave;
    return clampBackboneY(desired, gridHeight);
}

function walkBackboneSegment(a, b) {
    const cells = [{ x: a.x, y: a.y }];
    let x = a.x;
    let y = a.y;
    while (x !== b.x || y !== b.y) {
        const dx = Math.sign(b.x - x);
        const dy = Math.sign(b.y - y);
        x += dx;
        y += dy;
        cells.push({ x, y });
    }
    return cells;
}

function splitOpenRuns(path, grid, gridHeight, clearance) {
    const runs = [];
    let run = [];
    const flush = () => {
        if (run.length) runs.push(run);
        run = [];
    };

    for (const p of path) {
        const c = grid[p.x]?.[p.y];
        const open = c?.available
            && clearance[flatIdx(p.x, p.y, gridHeight)] >= BACKBONE_MIN_CLEARANCE;
        if (!open || crossesBlockedDiagonal(run[run.length - 1], c, grid)) {
            flush();
        }
        if (open) run.push(c);
    }
    flush();
    return runs;
}

function crossesBlockedDiagonal(prev, next, grid) {
    if (!prev || !next) return false;
    const dx = next.x - prev.x;
    const dy = next.y - prev.y;
    if (Math.abs(dx) !== 1 || Math.abs(dy) !== 1) return false;
    return !grid[prev.x + dx][prev.y].available && !grid[prev.x][prev.y + dy].available;
}

function commitBackboneRun(run) {
    for (let i = 0; i < run.length; i++) {
        const cell = run[i];
        const prev = run[Math.max(0, i - 1)];
        const next = run[Math.min(run.length - 1, i + 1)];
        cell.available = false;
        cell.heading = directionBetween(prev, next);
    }
}

function clampBackboneY(y, gridHeight) {
    return Math.max(2, Math.min(gridHeight - 3, y));
}

function chooseBackboneRow(obstacles, clearance, grid, gridWidth, gridHeight) {
    const target = backboneTargetY(gridHeight);
    const minX = Math.max(1, Math.min(...obstacles.map((o) => o.x)) - 8);
    const maxX = Math.min(
        gridWidth - 2,
        Math.max(...obstacles.map((o) => o.x + o.w)) + 8,
    );
    const y0 = Math.max(2, Math.round(target - 5));
    const y1 = Math.min(gridHeight - 3, Math.round(target + 5));

    let bestY = null;
    let bestScore = -Infinity;
    for (let y = y0; y <= y1; y++) {
        let score = -Math.abs(y - target) * 12;
        let run = 0;
        let bestRun = 0;
        for (let x = minX; x <= maxX; x++) {
            const c = grid[x][y];
            const d = clearance[flatIdx(x, y, gridHeight)];
            if (c.available && d >= BACKBONE_MIN_CLEARANCE) {
                score += d;
                run++;
                bestRun = Math.max(bestRun, run);
            } else {
                score -= 4;
                run = 0;
            }
        }
        score += bestRun * 3;
        if (score > bestScore) {
            bestScore = score;
            bestY = y;
        }
    }
    return bestY;
}

function backboneTargetY(gridHeight) {
    const hintedY = params.thinPcbRouteHints?.spineY;
    if (Number.isFinite(hintedY)) return Math.max(2, Math.min(gridHeight - 3, hintedY));
    const ratio = params.pinBusSpineRatio ?? 0.52;
    return Math.max(2, Math.min(gridHeight - 3, gridHeight * ratio));
}

function centeredLaneRows(centerY, gridHeight) {
    const rows = [];
    for (let i = 0; i < BACKBONE_LANES; i++) {
        const offset = (i - (BACKBONE_LANES - 1) / 2) * BACKBONE_LANE_SPACING;
        const y = Math.round(centerY + offset);
        if (y > 1 && y < gridHeight - 2 && !rows.includes(y)) rows.push(y);
    }
    return rows;
}

function flatIdx(x, y, gridHeight) {
    return x * gridHeight + y;
}

// sanitizePathRightAngles may bridge a sharp joint back through cells the wire
// already occupies, which renders as a tiny knot. Cut the loop: keep the first
// visit of each cell and drop everything walked between the two visits.
function backboneCellKeySet(backboneWires) {
    const keys = new Set();
    for (const wire of backboneWires) {
        for (const cell of wire.cells) keys.add(`${cell.x},${cell.y}`);
    }
    return keys;
}

// Tap routes target a backbone cell, but the trunk wire already draws that
// segment. Stop the tap one cell short so junctions do not stack two strokes.
function trimPathBeforeBackbone(path, backboneKeys) {
    if (!path?.length) return path;
    const out = [path[0]];
    for (let i = 1; i < path.length; i++) {
        if (backboneKeys.has(`${path[i].x},${path[i].y}`)) break;
        out.push(path[i]);
    }
    return out.length >= 2 ? out : path;
}

function spliceRevisitLoops(cells) {
    const seen = new Map();
    const out = [];
    for (const c of cells) {
        const k = `${c.x},${c.y}`;
        const at = seen.get(k);
        if (at !== undefined) {
            for (let r = at + 1; r < out.length; r++) {
                seen.delete(`${out[r].x},${out[r].y}`);
            }
            out.length = at + 1;
        } else {
            seen.set(k, out.length);
            out.push(c);
        }
    }
    return out;
}

// Escape trace ending on a pad: blind walk through the pre-rolled segments,
// stopping at the first blocked cell. Randomness was pre-rolled into the plan
// so routing order can't perturb it.
function growStub(plan, grid, gridWidth, gridHeight) {
    const { pin, segs } = plan;
    const cells = [pin.cell];
    for (const seg of segs) {
        const before = cells.length;
        const dir = (pin.heading + seg.off + 8) % 8;
        walkStub(cells, dir, seg.len, grid, gridWidth, gridHeight);
        if (cells.length < before + seg.len) break;
    }
    return cells;
}

function walkStub(cells, dir, len, grid, gridWidth, gridHeight) {
    const [dx, dy] = DIRS[dir];
    const isDiag = dx !== 0 && dy !== 0;
    let cur = cells[cells.length - 1];

    for (let i = 0; i < len; i++) {
        const nx = cur.x + dx;
        const ny = cur.y + dy;
        if (!inRouteBounds(nx, ny, gridWidth, gridHeight)) break;
        const next = grid[nx][ny];
        if (!next.available) break;
        // A diagonal step needs one open orthogonal cell or it would visually
        // cross another trace.
        if (isDiag && !grid[cur.x + dx][cur.y].available && !grid[cur.x][cur.y + dy].available) break;
        next.available = false;
        next.heading = dir;
        cells.push(next);
        cur = next;
    }
}

function applyPathToGrid(grid, path) {
    for (let i = 1; i < path.length; i++) {
        const c = grid[path[i].x][path[i].y];
        c.available = false;
        c.heading = directionBetween(path[i - 1], path[i]);
    }
}

// === Pin collection =========================================================

function collectQFPPins(grid, gridWidth, gridHeight) {
    const pins = [];
    if (!params.qfpStyle) return pins;

    const obstacles = getObstacles();
    const spacing = Math.max(1, params.qfpPinSpacing | 0);
    const inBounds = (x, y) => x >= 0 && y >= 0 && x < gridWidth && y < gridHeight;

    for (let chipIndex = 0; chipIndex < obstacles.length; chipIndex++) {
        const o = obstacles[chipIndex];
        const groups = pinGroups(o);
        if (!groups.length) continue;

        const add = (x, y, heading, groupKind) => {
            if (!inBounds(x, y)) return;
            pins.push({
                x,
                y,
                heading,
                chipIndex,
                cell: grid[x][y],
                groupKind,
                lead: null,
                tip: null,
            });
        };

        for (const group of groups) {
            if (group.side === 'top') {
                for (const i of pinCellOffsets(o.w, group, spacing)) add(o.x + i, o.y - 1, 1, group.kind);
            } else if (group.side === 'right') {
                for (const j of pinCellOffsets(o.h, group, spacing)) add(o.x + o.w, o.y + j, 3, group.kind);
            } else if (group.side === 'bottom') {
                for (const i of pinCellOffsets(o.w, group, spacing)) add(o.x + i, o.y + o.h, 5, group.kind);
            } else if (group.side === 'left') {
                for (const j of pinCellOffsets(o.h, group, spacing)) add(o.x - 1, o.y + j, 7, group.kind);
            }
        }
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
    return {
        chipIndex: pins[0].chipIndex,
        heading: pins[0].heading,
        kind: pins[0].groupKind || 'row',
        pins,
    };
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

function makeBackboneWire(cells, grid, gridWidth, gridHeight) {
    const wire = new Wire(cells[0], grid, gridWidth, gridHeight);
    wire.cells = cells;
    wire.isBus = true;
    return wire;
}

// Stub / wander trace: starts at a pin tab (no start pad) and dead-ends on a
// round pad, like the short escape traces on the reference boards.
function makeStubWire(cells, grid, gridWidth, gridHeight) {
    const wire = new Wire(cells[0], grid, gridWidth, gridHeight);
    wire.cells = cells;
    wire.isQFPPin = true;
    return wire;
}
