// Snapshot manager: save/load/delete views of the canvas to localStorage.
//
// A snapshot captures everything needed to reproduce the visible board:
//   - all serializable params (every non-function key except computed hex
//     getters, which are recomputed from bgColor/fgColor)
//   - the live obstacles array (with their x/y/w/h/qfp, since the user may
//     have hand-edited them via the corner-drag tool)
//   - a small canvas thumbnail for the UI list
//
// Wires: saved as sparse polylines when present (manual edits / drawn lines).
// Painted flow grid is NOT saved; document that limitation if it bites.

import { params } from './params.js';
import { getObstacles, setObstacles } from './obstacles.js';
import { getCanvas, getWires } from './canvas.js';
import { serializeWiresForSnapshot, setWireOverlay } from './wireEdit.js';

const PAINTER_STORAGE_KEY = 'circuit-painter:snapshots:v1';
const GENERATOR_STORAGE_KEY = 'circuit-generator:snapshots:v1';
let storageKey = PAINTER_STORAGE_KEY;
const THUMB_W = 90;
const THUMB_H = 54;

// dat.GUI hex getters are derived from bgColor/fgColor; don't store them.
const SKIP_PARAM_KEYS = new Set(['bgColorHex', 'fgColorHex']);

let onLoadCallback = null;
let datGui = null;

export function initSnapshots({
    gui,
    onLoad,
    seedUrls = [],
    storageKey: key = PAINTER_STORAGE_KEY,
}) {
    datGui = gui;
    onLoadCallback = onLoad;
    storageKey = key;
    renderPanel();
    if (seedUrls.length) ensureSeedSnapshots(seedUrls);
}

// === Storage ===============================================================

function readAll() {
    try {
        return JSON.parse(localStorage.getItem(storageKey) || '[]');
    } catch {
        return [];
    }
}

function writeAll(list) {
    try {
        localStorage.setItem(storageKey, JSON.stringify(list));
    } catch (err) {
        console.error('Snapshot save failed (storage full?):', err);
        alert('Could not save snapshot: localStorage is full or unavailable.');
    }
}

// === Capture / restore =====================================================

function paramsToPlain() {
    const out = {};
    for (const key of Object.keys(params)) {
        if (SKIP_PARAM_KEYS.has(key)) continue;
        const value = params[key];
        if (typeof value === 'function') continue;
        out[key] = value;
    }
    return out;
}

function makeThumbnail() {
    const canvas = getCanvas();
    const off = document.createElement('canvas');
    off.width = THUMB_W;
    off.height = THUMB_H;
    const ctx = off.getContext('2d');
    ctx.drawImage(canvas, 0, 0, THUMB_W, THUMB_H);
    return off.toDataURL('image/png');
}

export function captureSnapshot(name) {
    return {
        id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
        name,
        createdAt: Date.now(),
        thumbnail: makeThumbnail(),
        data: {
            params: paramsToPlain(),
            obstacles: getObstacles().map((o) => ({
                x: o.x, y: o.y, w: o.w, h: o.h, kind: o.kind, qfp: !!o.qfp,
                rot: o.rot | 0,
                ...(o.auxPinSide ? { auxPinSide: o.auxPinSide } : {}),
                ...(o.auxPinOffsets?.length ? { auxPinOffsets: o.auxPinOffsets.slice() } : {}),
            })),
            wires: serializeWiresForSnapshot(getWires()),
        },
    };
}

export function saveSnapshotNamed(name) {
    const all = readAll();
    all.push(captureSnapshot(name));
    writeAll(all);
    renderPanel();
}

function snapshotExists(name) {
    return readAll().some((s) => s.name === name);
}

export async function ensureSeedSnapshots(seedUrls) {
    let added = false;
    for (const url of seedUrls) {
        try {
            const snap = await fetch(url).then((r) => {
                if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
                return r.json();
            });
            if (snapshotExists(snap.name)) continue;
            const all = readAll();
            all.push(snap);
            writeAll(all);
            added = true;
        } catch (err) {
            console.warn('Seed snapshot failed:', url, err);
        }
    }
    if (added) renderPanel();
}

function applySnapshot(snap) {
    Object.assign(params, snap.data.params);
    setObstacles(snap.data.obstacles);
    setWireOverlay(snap.data.wires?.length ? snap.data.wires : null);
    refreshGuiControllers(datGui);
    if (onLoadCallback) onLoadCallback();
}

// Walk every controller in the dat.GUI tree and force a display refresh. We
// do this AFTER mutating params directly (instead of using controller.setValue)
// so onChange handlers don't fire during the bulk apply -- that would trigger
// a recreate per param, regenerating obstacles and stomping our restored ones.
function refreshGuiControllers(gui) {
    if (!gui) return;
    for (const c of gui.__controllers || []) {
        try { c.updateDisplay(); } catch { /* ignore */ }
    }
    for (const name of Object.keys(gui.__folders || {})) {
        refreshGuiControllers(gui.__folders[name]);
    }
}

// === Actions ===============================================================

function defaultName() {
    const all = readAll();
    return 'Snapshot ' + (all.length + 1);
}

function saveCurrent() {
    const raw = window.prompt('Name this snapshot:', defaultName());
    if (raw === null) return; // cancelled
    const name = raw.trim() || defaultName();
    const all = readAll();
    all.push(captureSnapshot(name));
    writeAll(all);
    renderPanel();
}

function deleteSnapshot(id) {
    const all = readAll().filter((s) => s.id !== id);
    writeAll(all);
    renderPanel();
}

function loadSnapshotById(id) {
    const snap = readAll().find((s) => s.id === id);
    if (snap) applySnapshot(snap);
}

// === UI ====================================================================

function renderPanel() {
    let panel = document.getElementById('snapshots-panel');
    const isFirstRender = !panel;
    const wasCollapsed = panel?.classList.contains('snapshots-panel--collapsed');

    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'snapshots-panel';
        panel.className = 'snapshots-panel';
        document.body.appendChild(panel);
    }

    const all = readAll();

    panel.innerHTML = `
        <div class="snapshots-panel__header" role="button">
            <span class="snapshots-panel__chevron"></span>
            <span class="snapshots-panel__title">Snapshots</span>
            <span class="snapshots-panel__count">${all.length}</span>
            <button class="snapshots-panel__save" title="Save current view">+ Save</button>
        </div>
        <ul class="snapshots-panel__list">
            ${all.length === 0
              ? '<li class="snapshots-panel__empty">No snapshots yet. Press + Save.</li>'
              : all.map(renderItemHtml).join('')
            }
        </ul>
    `;

    if (!isFirstRender && wasCollapsed) {
        panel.classList.add('snapshots-panel--collapsed');
    }

    wireUpEvents(panel);
}

function renderItemHtml(snap) {
    const date = new Date(snap.createdAt);
    const stamp = date.toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
    return `
        <li class="snapshots-panel__item" data-id="${snap.id}">
            <img class="snapshots-panel__thumb" src="${snap.thumbnail}" alt="" />
            <div class="snapshots-panel__meta">
                <span class="snapshots-panel__name">${escapeHtml(snap.name)}</span>
                <span class="snapshots-panel__date">${stamp}</span>
            </div>
            <button class="snapshots-panel__delete" title="Delete snapshot">&times;</button>
        </li>
    `;
}

function wireUpEvents(panel) {
    const header = panel.querySelector('.snapshots-panel__header');
    const saveBtn = panel.querySelector('.snapshots-panel__save');

    // Save button stops propagation so it doesn't also toggle the header.
    saveBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        saveCurrent();
    });

    header.addEventListener('click', () => {
        panel.classList.toggle('snapshots-panel--collapsed');
    });

    for (const item of panel.querySelectorAll('.snapshots-panel__item')) {
        const id = item.dataset.id;
        item.addEventListener('click', (e) => {
            if (e.target.closest('.snapshots-panel__delete')) return;
            loadSnapshotById(id);
        });
        item.querySelector('.snapshots-panel__delete').addEventListener('click', (e) => {
            e.stopPropagation();
            if (window.confirm('Delete this snapshot?')) deleteSnapshot(id);
        });
    }
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[m]));
}
