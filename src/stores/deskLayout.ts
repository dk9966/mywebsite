import { create } from "zustand";

// Shared source of truth for the desk HUD: camera, the global panel
// curvature + glass look, and the flat-wall grid fractions that the layout
// solver turns into 5 panel rects. The 3D resize drags and the HTML slider
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
}

const FACTORY_DEFAULTS: DeskLayoutDefaults = {
  camera: { x: 0, y: 2.15, z: 2.8, fov: 40 },
  lookAt: { x: 0, y: 2.0, z: -1.05 },
  wallAnchor: { x: 0, y: 2.05, z: -1.85 },
  wallWidthPx: 2050,
  wallHeightPx: 1010,
  curveRadiusPx: 880,
  bgOpacity: 0.5,
  bgBlur: 3,
  bezelEmission: 2.4,
  bezelLineWidth: 2.6,
  bezelOpacity: 1,
  bloomIntensity: 1.1,
  bloomThreshold: 0.82,
  bloomRadius: 0.75,
  bloomSmoothing: 0.15,
  headerFontPx: 28,
  contentPaddingPx: 20,
  contactHeightPx: 96,
  contactIconSizePx: 40,
  colFrac: [0.3, 0.4, 0.3],
  leftSplit: 0.56,
};

const STORAGE_KEY = "desk-layout-defaults";

// Minimum share of the wall a column / stacked cell may keep, so reflow
// never collapses a panel to nothing.
const MIN_HEADER_FONT_PX = 9;
export const MAX_HEADER_FONT_PX = 56;
const MIN_SPLIT = 0.22;
export const MIN_CONTACT_HEIGHT_PX = 64;
export const MAX_CONTACT_HEIGHT_PX = 160;
const MIN_COL_FRAC = MIN_SPLIT;

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
    contactHeightPx: clampContactHeightPx(
      contactHeightPx ?? FACTORY_DEFAULTS.contactHeightPx,
      wallHeightPx,
    ),
  };
}

function loadSavedDefaults(): DeskLayoutDefaults | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DeskLayoutDefaults;
    if (!parsed || typeof parsed !== "object") return null;
    return normalizeLayoutDefaults({ ...FACTORY_DEFAULTS, ...parsed });
  } catch {
    return null;
  }
}

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
  });
}

let savedDefaults: DeskLayoutDefaults = normalizeLayoutDefaults(
  loadSavedDefaults() ?? FACTORY_DEFAULTS,
);

interface DeskLayoutStore extends DeskLayoutDefaults {
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

  // Move the shared boundary between two adjacent columns. boundary 0 sits
  // between col 0 and col 1, boundary 1 between col 1 and col 2. A positive
  // delta grows the left column at the expense of the right one; the total
  // width never changes.
  adjustColBoundary: (boundary: 0 | 1, deltaFrac: number) => void;
  // Move the horizontal splitter inside the left / right column. A positive
  // delta grows the top cell at the expense of the bottom one.
  adjustLeftSplit: (deltaFrac: number) => void;

  reset: () => void;
  /** Persist the live slider values as what "Reset defaults" restores to. */
  saveAsDefault: () => void;
}

export const useDeskLayout = create<DeskLayoutStore>((set, get) => ({
  ...cloneDefaults(savedDefaults),

  setCamera: (patch) => set({ camera: { ...get().camera, ...patch } }),
  setLookAt: (patch) => set({ lookAt: { ...get().lookAt, ...patch } }),
  setWallAnchor: (patch) => set({ wallAnchor: { ...get().wallAnchor, ...patch } }),
  setWallWidthPx: (v) => set({ wallWidthPx: clamp(v, 800, 2400) }),
  setWallHeightPx: (v) => {
    const wallHeightPx = clamp(v, 300, 1800);
    set({
      wallHeightPx,
      contactHeightPx: clampContactHeightPx(get().contactHeightPx, wallHeightPx),
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

  adjustLeftSplit: (delta) =>
    set({ leftSplit: clamp(get().leftSplit + delta, MIN_SPLIT, 1 - MIN_SPLIT) }),

  reset: () => set(cloneDefaults(savedDefaults)),

  saveAsDefault: () => {
    savedDefaults = normalizeLayoutDefaults(snapshotDefaults(get()));
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savedDefaults));
    } catch {
      // Quota or private browsing — in-memory save still works this session.
    }
  },
}));
