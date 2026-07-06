import { create } from "zustand";
import type { CellId } from "../lib/panelWall";
import committedDefaults from "../data/desk-layout-defaults.json";

// Shared source of truth for the desk HUD: camera, the global panel
// curvature + glass look, and the flat-wall grid fractions that the layout
// solver turns into 6 panel rects. The 3D resize drags and the HTML slider
// overlay both read/write here so they stay in sync.

export interface DeskCamera {
  x: number;
  y: number;
  z: number;
  fov: number;
}

export interface DeskPoint3 {
  x: number;
  y: number;
  z: number;
}

export interface DeskLayoutDefaults {
  camera: DeskCamera;
  lookAt: DeskPoint3;
  wallAnchor: DeskPoint3;
  wallWidthPx: number;
  wallHeightPx: number;
  curveRadiusPx: number;
  bgOpacity: number;
  bgBlur: number;
  bezelEmission: number;
  bezelLineWidth: number;
  bezelOpacity: number;
  bloomIntensity: number;
  bloomThreshold: number;
  bloomRadius: number;
  bloomSmoothing: number;
  headerFontPx: number;
  /** Inset between panel bezel and title/body content, CSS px. */
  contentPaddingPx: number;
  /** Fixed contact strip height in CSS px. */
  contactHeightPx: number;
  /** Contact social icon size in CSS px. */
  contactIconSizePx: number;
  colFrac: [number, number, number];
  leftSplit: number;
  rightSplit: number;
  /** Timeline body base size in CSS px — Education panel. */
  eduBaseFontPx: number;
  eduDegreeEm: number;
  eduDateEm: number;
  eduSchoolEm: number;
  /** Timeline body base size in CSS px — Experience panel. */
  expBaseFontPx: number;
  expRoleEm: number;
  expDateEm: number;
  expOrgEm: number;
}

const MIN_TIMELINE_FONT_PX = 10;
export const MAX_TIMELINE_FONT_PX = 36;
const MIN_TYPE_EM = 0.6;
export const MAX_TYPE_EM = 1.6;

const FACTORY_DEFAULTS: DeskLayoutDefaults = {
  camera: { x: 0, y: 2.15, z: 2.8, fov: 40 },
  lookAt: { x: 0, y: 2.0, z: -1.05 },
  wallAnchor: { x: 0, y: 2.05, z: -1.85 },
  wallWidthPx: 2050,
  wallHeightPx: 1010,
  curveRadiusPx: 1425,
  bgOpacity: 0.5,
  bgBlur: 3,
  bezelEmission: 1.4,
  bezelLineWidth: 1.3,
  bezelOpacity: 1,
  bloomIntensity: 3.45,
  bloomThreshold: 0.82,
  bloomRadius: 0.75,
  bloomSmoothing: 0.63,
  headerFontPx: 38,
  contentPaddingPx: 39,
  contactHeightPx: 96,
  contactIconSizePx: 40,
  colFrac: [0.3, 0.35, 0.35],
  leftSplit: 0.56,
  rightSplit: 0.44,
  eduBaseFontPx: 22,
  eduDegreeEm: 1.05,
  eduDateEm: 0.82,
  eduSchoolEm: 0.94,
  expBaseFontPx: 20,
  expRoleEm: 1.12,
  expDateEm: 0.82,
  expOrgEm: 0.94,
};

// Dev route backed by src/data/desk-layout-defaults.json (see
// scripts/vite-json-file-save.ts). "Set as default" POSTs the live values here
// so they're committed to source and shared across browsers, instead of living
// in one browser's localStorage.
const SAVE_ROUTE = "/__save-desk-layout";

// Minimum share of the wall a column / stacked cell may keep, so reflow
// never collapses a panel to nothing.
const MIN_HEADER_FONT_PX = 9;
export const MAX_HEADER_FONT_PX = 56;
const MIN_SPLIT = 0.22;
export const MIN_PANEL_SPLIT = MIN_SPLIT;
export const MAX_PANEL_SPLIT = 1 - MIN_SPLIT;
export const MIN_CONTACT_HEIGHT_PX = 64;
export const MAX_CONTACT_HEIGHT_PX = 160;
export const MIN_COL_FRAC = MIN_SPLIT;
export const MAX_COL_FRAC = 1 - 2 * MIN_COL_FRAC;

const clampContactHeightPx = (px: number, wallHeightPx: number) => {
  const availH = wallHeightPx - 28;
  const max = Math.min(MAX_CONTACT_HEIGHT_PX, availH - availH * MIN_SPLIT);
  return clamp(px, MIN_CONTACT_HEIGHT_PX, Math.max(MIN_CONTACT_HEIGHT_PX, max));
};

const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));

function cloneDefaults(d: DeskLayoutDefaults): DeskLayoutDefaults {
  return {
    ...d,
    camera: { ...d.camera },
    lookAt: { ...d.lookAt },
    wallAnchor: { ...d.wallAnchor },
    colFrac: [...d.colFrac] as [number, number, number],
  };
}

function normalizeLayoutDefaults(
  d: DeskLayoutDefaults & { contactHeightFrac?: number; rightSplit?: number },
): DeskLayoutDefaults {
  const wallHeightPx = d.wallHeightPx ?? FACTORY_DEFAULTS.wallHeightPx;
  let contactHeightPx = d.contactHeightPx;
  if (contactHeightPx == null && d.contactHeightFrac != null) {
    contactHeightPx = Math.round((wallHeightPx - 28) * d.contactHeightFrac);
  }
  return {
    ...cloneDefaults(d),
    rightSplit: d.rightSplit ?? FACTORY_DEFAULTS.rightSplit,
    eduBaseFontPx: d.eduBaseFontPx ?? FACTORY_DEFAULTS.eduBaseFontPx,
    eduDegreeEm: d.eduDegreeEm ?? FACTORY_DEFAULTS.eduDegreeEm,
    eduDateEm: d.eduDateEm ?? FACTORY_DEFAULTS.eduDateEm,
    eduSchoolEm: d.eduSchoolEm ?? FACTORY_DEFAULTS.eduSchoolEm,
    expBaseFontPx: d.expBaseFontPx ?? FACTORY_DEFAULTS.expBaseFontPx,
    expRoleEm: d.expRoleEm ?? FACTORY_DEFAULTS.expRoleEm,
    expDateEm: d.expDateEm ?? FACTORY_DEFAULTS.expDateEm,
    expOrgEm: d.expOrgEm ?? FACTORY_DEFAULTS.expOrgEm,
    contactHeightPx: clampContactHeightPx(
      contactHeightPx ?? FACTORY_DEFAULTS.contactHeightPx,
      wallHeightPx,
    ),
  };
}

// Committed baseline, bundled from the JSON file at build time and re-read on
// every full page reload in dev — so localhost effectively serves whatever was
// last saved. Factory values fill any gaps if the file is partial/older.
const PUBLISHED: DeskLayoutDefaults = normalizeLayoutDefaults({
  ...FACTORY_DEFAULTS,
  ...(committedDefaults as Partial<DeskLayoutDefaults>),
});

function snapshotDefaults(state: DeskLayoutStore): DeskLayoutDefaults {
  return cloneDefaults({
    camera: state.camera,
    lookAt: state.lookAt,
    wallAnchor: state.wallAnchor,
    wallWidthPx: state.wallWidthPx,
    wallHeightPx: state.wallHeightPx,
    curveRadiusPx: state.curveRadiusPx,
    bgOpacity: state.bgOpacity,
    bgBlur: state.bgBlur,
    bezelEmission: state.bezelEmission,
    bezelLineWidth: state.bezelLineWidth,
    bezelOpacity: state.bezelOpacity,
    bloomIntensity: state.bloomIntensity,
    bloomThreshold: state.bloomThreshold,
    bloomRadius: state.bloomRadius,
    bloomSmoothing: state.bloomSmoothing,
    headerFontPx: state.headerFontPx,
    contentPaddingPx: state.contentPaddingPx,
    contactHeightPx: state.contactHeightPx,
    contactIconSizePx: state.contactIconSizePx,
    colFrac: state.colFrac,
    leftSplit: state.leftSplit,
    rightSplit: state.rightSplit,
    eduBaseFontPx: state.eduBaseFontPx,
    eduDegreeEm: state.eduDegreeEm,
    eduDateEm: state.eduDateEm,
    eduSchoolEm: state.eduSchoolEm,
    expBaseFontPx: state.expBaseFontPx,
    expRoleEm: state.expRoleEm,
    expDateEm: state.expDateEm,
    expOrgEm: state.expOrgEm,
  });
}

// What Reset restores to. Starts at the committed file; a successful save or a
// disk fetch updates it so Reset tracks the newest default.
let savedDefaults: DeskLayoutDefaults = cloneDefaults(PUBLISHED);

/**
 * Read the committed file straight off disk via the dev server. The bundled
 * `PUBLISHED` import is a snapshot from when the server started, and the file is
 * intentionally hidden from the HMR watcher, so a save isn't reflected by the
 * import on reload. Fetching is what makes a reload — and other browsers — see
 * the latest "Set as default".
 */
async function fetchCommittedFromDisk(): Promise<DeskLayoutDefaults | null> {
  if (typeof window === "undefined") return null;
  try {
    const res = await fetch(SAVE_ROUTE, {
      headers: { "Cache-Control": "no-store" },
    });
    if (!res.ok) return null;
    const json = (await res.json()) as Partial<DeskLayoutDefaults>;
    return normalizeLayoutDefaults({ ...FACTORY_DEFAULTS, ...json });
  } catch {
    return null;
  }
}

interface DeskLayoutStore extends DeskLayoutDefaults {
  /** Panels collapsed to letter icons in the dock below contact. */
  minimizedPanels: CellId[];
  togglePanelMinimized: (id: CellId) => void;

  setCamera: (patch: Partial<DeskCamera>) => void;
  setLookAt: (patch: Partial<DeskPoint3>) => void;
  setWallAnchor: (patch: Partial<DeskPoint3>) => void;
  setWallWidthPx: (v: number) => void;
  setWallHeightPx: (v: number) => void;
  setCurveRadiusPx: (v: number) => void;
  setBgOpacity: (v: number) => void;
  setBgBlur: (v: number) => void;
  setBezelEmission: (v: number) => void;
  setBezelLineWidth: (v: number) => void;
  setBezelOpacity: (v: number) => void;
  setBloomIntensity: (v: number) => void;
  setBloomThreshold: (v: number) => void;
  setBloomRadius: (v: number) => void;
  setBloomSmoothing: (v: number) => void;
  setHeaderFontPx: (v: number) => void;
  setContentPaddingPx: (v: number) => void;
  setContactHeightPx: (v: number) => void;
  setContactIconSizePx: (v: number) => void;
  setEduBaseFontPx: (v: number) => void;
  setEduDegreeEm: (v: number) => void;
  setEduDateEm: (v: number) => void;
  setEduSchoolEm: (v: number) => void;
  setExpBaseFontPx: (v: number) => void;
  setExpRoleEm: (v: number) => void;
  setExpDateEm: (v: number) => void;
  setExpOrgEm: (v: number) => void;

  // Move the shared boundary between two adjacent columns. boundary 0 sits
  // between col 0 and col 1, boundary 1 between col 1 and col 2. A positive
  // delta grows the left column at the expense of the right one; the total
  // width never changes.
  adjustColBoundary: (boundary: 0 | 1, deltaFrac: number) => void;
  /** Set one column's width fraction; an adjacent column absorbs the delta. */
  setColFrac: (column: 0 | 1 | 2, frac: number) => void;
  // Move the horizontal splitter inside the left / right column. A positive
  // delta grows the top cell at the expense of the bottom one.
  adjustLeftSplit: (deltaFrac: number) => void;
  adjustRightSplit: (deltaFrac: number) => void;
  setRightSplit: (v: number) => void;

  /** Restore the committed defaults, re-fetched from disk when the dev server is up. */
  reset: () => Promise<void>;
  /**
   * Write the live values to the committed defaults file via the dev server, so
   * every browser sees them after a reload. Resolves true on success; on failure
   * (e.g. no dev server) it downloads the JSON to commit by hand and resolves
   * false.
   */
  saveAsDefault: () => Promise<boolean>;
}

export const useDeskLayout = create<DeskLayoutStore>((set, get) => ({
  ...cloneDefaults(savedDefaults),
  minimizedPanels: [],

  togglePanelMinimized: (id) =>
    set((state) => {
      const on = state.minimizedPanels.includes(id);
      return {
        minimizedPanels: on
          ? state.minimizedPanels.filter((p) => p !== id)
          : [...state.minimizedPanels, id],
      };
    }),

  setCamera: (patch) => set({ camera: { ...get().camera, ...patch } }),
  setLookAt: (patch) => set({ lookAt: { ...get().lookAt, ...patch } }),
  setWallAnchor: (patch) =>
    set({ wallAnchor: { ...get().wallAnchor, ...patch } }),
  setWallWidthPx: (v) => set({ wallWidthPx: clamp(v, 800, 2400) }),
  setWallHeightPx: (v) => {
    const wallHeightPx = clamp(v, 300, 1800);
    set({
      wallHeightPx,
      contactHeightPx: clampContactHeightPx(
        get().contactHeightPx,
        wallHeightPx,
      ),
    });
  },
  setCurveRadiusPx: (v) => set({ curveRadiusPx: clamp(v, 500, 1500) }),
  setBgOpacity: (v) => set({ bgOpacity: clamp(v, 0, 1) }),
  setBgBlur: (v) => set({ bgBlur: Math.max(0, v) }),
  setBezelEmission: (v) => set({ bezelEmission: clamp(v, 0.5, 6) }),
  setBezelLineWidth: (v) => set({ bezelLineWidth: clamp(v, 0.5, 6) }),
  setBezelOpacity: (v) => set({ bezelOpacity: clamp(v, 0, 1) }),
  setBloomIntensity: (v) => set({ bloomIntensity: clamp(v, 0, 4) }),
  setBloomThreshold: (v) => set({ bloomThreshold: clamp(v, 0, 1) }),
  setBloomRadius: (v) => set({ bloomRadius: clamp(v, 0, 1.5) }),
  setBloomSmoothing: (v) => set({ bloomSmoothing: clamp(v, 0, 1) }),
  setHeaderFontPx: (v) =>
    set({ headerFontPx: clamp(v, MIN_HEADER_FONT_PX, MAX_HEADER_FONT_PX) }),
  setContentPaddingPx: (v) => set({ contentPaddingPx: clamp(v, 4, 56) }),
  setContactHeightPx: (v) =>
    set({
      contactHeightPx: clampContactHeightPx(v, get().wallHeightPx),
    }),
  setContactIconSizePx: (v) => set({ contactIconSizePx: clamp(v, 20, 72) }),

  setEduBaseFontPx: (v) =>
    set({
      eduBaseFontPx: clamp(v, MIN_TIMELINE_FONT_PX, MAX_TIMELINE_FONT_PX),
    }),
  setEduDegreeEm: (v) =>
    set({ eduDegreeEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),
  setEduDateEm: (v) => set({ eduDateEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),
  setEduSchoolEm: (v) =>
    set({ eduSchoolEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),
  setExpBaseFontPx: (v) =>
    set({
      expBaseFontPx: clamp(v, MIN_TIMELINE_FONT_PX, MAX_TIMELINE_FONT_PX),
    }),
  setExpRoleEm: (v) => set({ expRoleEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),
  setExpDateEm: (v) => set({ expDateEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),
  setExpOrgEm: (v) => set({ expOrgEm: clamp(v, MIN_TYPE_EM, MAX_TYPE_EM) }),

  adjustColBoundary: (boundary, delta) => {
    const f = [...get().colFrac] as [number, number, number];
    const a = boundary;
    const b = boundary + 1;
    let na = f[a] + delta;
    let nb = f[b] - delta;
    // Trade the overshoot back so neither side dips under the minimum while
    // their sum stays fixed.
    if (na < MIN_COL_FRAC) {
      nb -= MIN_COL_FRAC - na;
      na = MIN_COL_FRAC;
    }
    if (nb < MIN_COL_FRAC) {
      na -= MIN_COL_FRAC - nb;
      nb = MIN_COL_FRAC;
    }
    f[a] = na;
    f[b] = nb;
    set({ colFrac: f });
  },

  setColFrac: (column, frac) => {
    frac = clamp(frac, MIN_COL_FRAC, MAX_COL_FRAC);
    const f = get().colFrac;
    const delta = frac - f[column];
    if (Math.abs(delta) < 1e-6) return;
    if (column === 0) {
      get().adjustColBoundary(0, delta);
    } else if (column === 1) {
      if (delta > 0) get().adjustColBoundary(1, delta);
      else get().adjustColBoundary(0, delta);
    } else {
      get().adjustColBoundary(1, -delta);
    }
  },

  adjustLeftSplit: (delta) =>
    set({
      leftSplit: clamp(get().leftSplit + delta, MIN_SPLIT, 1 - MIN_SPLIT),
    }),

  adjustRightSplit: (delta) =>
    set({
      rightSplit: clamp(get().rightSplit + delta, MIN_SPLIT, 1 - MIN_SPLIT),
    }),

  setRightSplit: (v) =>
    set({ rightSplit: clamp(v, MIN_PANEL_SPLIT, MAX_PANEL_SPLIT) }),

  reset: async () => {
    // Prefer the live file (reflects saves from any browser); fall back to the
    // session baseline if the dev route is unavailable.
    const fromDisk = await fetchCommittedFromDisk();
    if (fromDisk) savedDefaults = fromDisk;
    set({ ...cloneDefaults(savedDefaults), minimizedPanels: [] });
  },

  saveAsDefault: async () => {
    const snap = normalizeLayoutDefaults(snapshotDefaults(get()));
    const body = JSON.stringify(snap, null, 2);
    try {
      const res = await fetch(SAVE_ROUTE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      if (!res.ok) throw new Error("save failed");
      savedDefaults = snap;
      return true;
    } catch {
      downloadDefaults(body);
      return false;
    }
  },
}));

/** Fallback when the dev route is unavailable: hand back the file to commit. */
function downloadDefaults(body: string): void {
  if (typeof document === "undefined") return;
  const blob = new Blob([`${body.trimEnd()}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "desk-layout-defaults.json";
  a.click();
  URL.revokeObjectURL(url);
}

// On load, pull the committed file from disk so a reload reflects the latest
// "Set as default" instead of the stale bundled import. Only hydrate while the
// state still matches the bundle, so a late fetch never clobbers edits the user
// already started making this session.
if (typeof window !== "undefined") {
  const bundled = JSON.stringify(PUBLISHED);
  void fetchCommittedFromDisk().then((fromDisk) => {
    if (!fromDisk) return;
    savedDefaults = fromDisk;
    const current = JSON.stringify(
      normalizeLayoutDefaults(snapshotDefaults(useDeskLayout.getState())),
    );
    if (current === bundled) {
      useDeskLayout.setState(cloneDefaults(fromDisk));
    }
  });
}
