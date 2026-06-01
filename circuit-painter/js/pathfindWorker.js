import { routePinBusCore } from './pinBusRouteCore.js';

self.onmessage = (event) => {
    const { id, available, headings, gridWidth, gridHeight, routes, routeParams } = event.data;

    try {
        const avail = available instanceof Uint8Array ? available.slice() : new Uint8Array(available);
        const head = headings instanceof Int8Array ? headings.slice() : new Int8Array(headings);
        const paths = routePinBusCore(avail, head, gridWidth, gridHeight, routes, routeParams);
        self.postMessage({ id, paths });
    } catch (error) {
        self.postMessage({ id, error: String(error) });
    }
};
