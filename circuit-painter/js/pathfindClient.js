// Thin client for the pathfind worker. Falls back to main-thread routing.

import { routePinBusCore } from './pinBusRouteCore.js';

let worker = null;
let nextId = 0;
const pending = new Map();

function getWorker() {
    if (worker) return worker;
    try {
        worker = new Worker(new URL('./pathfindWorker.js', import.meta.url), { type: 'module' });
        worker.onmessage = (event) => {
            const { id, paths, error } = event.data;
            const resolve = pending.get(id);
            if (!resolve) return;
            pending.delete(id);
            resolve(error ? { error } : { paths });
        };
        worker.onerror = () => {
            worker = null;
        };
    } catch {
        worker = null;
    }
    return worker;
}

export function routePinBusAsync(payload) {
    const w = getWorker();
    if (!w) {
        const avail = payload.available.slice();
        const head = payload.headings.slice();
        const paths = routePinBusCore(
            avail,
            head,
            payload.gridWidth,
            payload.gridHeight,
            payload.routes,
            payload.routeParams,
        );
        return Promise.resolve({ paths });
    }

    const available = payload.available.slice();
    const headings = payload.headings.slice();

    return new Promise((resolve) => {
        const id = nextId++;
        pending.set(id, resolve);
        w.postMessage({
            id,
            gridWidth: payload.gridWidth,
            gridHeight: payload.gridHeight,
            routes: payload.routes,
            routeParams: payload.routeParams,
            available,
            headings,
        }, [available.buffer, headings.buffer]);
    });
}

export function terminatePathfindWorker() {
    if (worker) {
        worker.terminate();
        worker = null;
    }
    pending.clear();
}
