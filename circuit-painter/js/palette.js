// Component palette: the row of draggable shapes at the top of the page. Each
// thumbnail is drawn with the same routine that renders placed obstacles, so
// what you drag is exactly what lands on the board. Dropping is handled by the
// canvas (see main.js); this module only builds the drag sources.

import { PALETTE_KINDS, getKind, drawComponent } from './components.js';

export const DRAG_MIME = 'text/component-kind';

const THUMB_W = 64;
const THUMB_H = 52;

// The kind currently being dragged. dataTransfer is the canonical channel, but
// some browsers forbid reading its data during dragover (only on drop), so the
// drop target also consults this to decide whether to accept the drag.
let draggingKind = null;

export function getDraggingKind() {
    return draggingKind;
}

export function initPalette() {
    const bar = document.createElement('div');
    bar.className = 'component-palette';

    for (const id of PALETTE_KINDS) {
        const kind = getKind(id);
        const item = document.createElement('div');
        item.className = 'component-palette__item';
        item.draggable = true;
        item.title = `Drag ${kind.label} onto the board`;
        item.dataset.kind = id;
        item.setAttribute('role', 'button');
        item.setAttribute('aria-label', `${kind.label} component`);

        const canvas = makeThumb(kind);
        canvas.className = 'component-palette__thumb';

        const label = document.createElement('span');
        label.className = 'component-palette__label';
        label.textContent = kind.label;

        item.append(canvas, label);
        item.addEventListener('dragstart', (e) => {
            draggingKind = id;
            e.dataTransfer.setData(DRAG_MIME, id);
            e.dataTransfer.effectAllowed = 'copy';
            e.dataTransfer.setDragImage(canvas, THUMB_W / 2, THUMB_H / 2);
        });
        item.addEventListener('dragend', () => { draggingKind = null; });
        bar.appendChild(item);
    }

    document.body.appendChild(bar);
}

function makeThumb(kind) {
    const dpr = window.devicePixelRatio || 1;
    const canvas = document.createElement('canvas');
    canvas.width = THUMB_W * dpr;
    canvas.height = THUMB_H * dpr;
    canvas.style.width = `${THUMB_W}px`;
    canvas.style.height = `${THUMB_H}px`;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    // Fit the footprint (plus a margin for pin overhang) inside the thumbnail,
    // keeping a single square cell size so proportions stay true.
    const pad = 8;
    const span = Math.max(kind.w, kind.h) + 1.6;
    const unit = Math.min(THUMB_W - pad * 2, THUMB_H - pad * 2) / span;
    const ox = (THUMB_W - kind.w * unit) / 2;
    const oy = (THUMB_H - kind.h * unit) / 2;

    drawComponent(ctx, kind, { ox, oy, cols: kind.w, rows: kind.h, cw: unit, ch: unit });
    return canvas;
}
