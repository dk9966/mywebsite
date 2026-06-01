// Pin-bus routing on flat grid buffers. Used by the worker and as a main-thread
// fallback when the worker is unavailable.

import { aStarCore, directionBetween } from './pathfindCore.js';

const BUNDLE_BONUS = 0.7;

function idx(x, y, gridHeight) {
    return x * gridHeight + y;
}

function routeTraceCore(available, headings, gridWidth, gridHeight, srcTip, dstTip, startDir, routeParams) {
    const segMin = Math.max(1, routeParams.segMin | 0);
    const segMax = Math.max(segMin + 1, routeParams.segMax | 0);
    const cellCount = gridWidth * gridHeight;
    const base = {
        bundle: BUNDLE_BONUS,
        segMin,
        segMax,
        startDir,
        hardSegMin: true,
        turnSmoothness: routeParams.turnSmoothness,
        diagonalChance: routeParams.diagonalChance,
    };

    const attempts = [
        { onlyObtuse: true, maxExpansions: cellCount * 6 },
        { onlyObtuse: true, maxExpansions: cellCount * 12 },
        { onlyObtuse: true, maxExpansions: cellCount * 20 },
    ];
    for (const extra of attempts) {
        const path = aStarCore(available, headings, gridWidth, gridHeight, srcTip, dstTip, {
            ...base,
            ...extra,
        });
        if (path) return path;
    }
    return null;
}

function markPath(available, headings, gridHeight, path) {
    for (let i = 1; i < path.length; i++) {
        const c = path[i];
        const cellIdx = idx(c.x, c.y, gridHeight);
        available[cellIdx] = 0;
        headings[cellIdx] = directionBetween(path[i - 1], c);
    }
}

// `routes`: [{ srcTip, dstTip, startDir }] in bus order.
// Mutates `available`/`headings`. Returns paths aligned to `routes` (null = failed).
export function routePinBusCore(available, headings, gridWidth, gridHeight, routes, routeParams) {
    const paths = new Array(routes.length).fill(null);

    for (let i = 0; i < routes.length; i++) {
        const route = routes[i];
        const dstIdx = idx(route.dstTip.x, route.dstTip.y, gridHeight);
        const wasOpen = available[dstIdx];
        available[dstIdx] = 1;

        const path = routeTraceCore(
            available,
            headings,
            gridWidth,
            gridHeight,
            route.srcTip,
            route.dstTip,
            route.startDir,
            routeParams,
        );

        available[dstIdx] = wasOpen ? 1 : 0;

        if (!path || path.length < 2) continue;

        markPath(available, headings, gridHeight, path);
        paths[i] = path;
    }

    return paths;
}
