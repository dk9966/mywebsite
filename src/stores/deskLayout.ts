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

const DEFAULT_CAMERA: DeskCamera = { x: 0, y: 2.15, z: 2.8, fov: 40 };
const DEFAULT_LOOK_AT: DeskPoint3 = { x: 0, y: 2.0, z: -1.05 };
const DEFAULT_WALL_ANCHOR: DeskPoint3 = { x: 0, y: 2.05, z: -1.85 };
const DEFAULT_CURVE_RADIUS_PX = 880;
const DEFAULT_WALL_WIDTH_PX = 2050;
const DEFAULT_WALL_HEIGHT_PX = 1010;
const DEFAULT_HEADER_FONT_PX = 28;
const DEFAULT_BG_OPACITY = 0.5;
const DEFAULT_BG_BLUR = 3;
const DEFAULT_COL_FRAC: [number, number, number] = [0.3, 0.4, 0.3];
const DEFAULT_LEFT_SPLIT = 0.56;
const DEFAULT_RIGHT_SPLIT = 0.62;

// Minimum share of the wall a column / stacked cell may keep, so reflow
// never collapses a panel to nothing.
const MIN_HEADER_FONT_PX = 9;
export const MAX_HEADER_FONT_PX = 56;
const MIN_SPLIT = 0.22;

const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));

interface DeskLayoutStore {
  camera: DeskCamera;
  lookAt: DeskPoint3;
  wallAnchor: DeskPoint3;
  wallWidthPx: number;
  wallHeightPx: number;
  curveRadiusPx: number;
  bgOpacity: number;
  bgBlur: number;
  headerFontPx: number;
  colFrac: [number, number, number];
  leftSplit: number;
  rightSplit: number;

  setCamera: (patch: Partial<DeskCamera>) => void;
  setLookAt: (patch: Partial<DeskPoint3>) => void;
  setWallAnchor: (patch: Partial<DeskPoint3>) => void;
  setWallWidthPx: (v: number) => void;
  setWallHeightPx: (v: number) => void;
  setCurveRadiusPx: (v: number) => void;
  setBgOpacity: (v: number) => void;
  setBgBlur: (v: number) => void;
  setHeaderFontPx: (v: number) => void;

  // Move the shared boundary between two adjacent columns. boundary 0 sits
  // between col 0 and col 1, boundary 1 between col 1 and col 2. A positive
  // delta grows the left column at the expense of the right one; the total
  // width never changes.
  adjustColBoundary: (boundary: 0 | 1, deltaFrac: number) => void;
  // Move the horizontal splitter inside the left / right column. A positive
  // delta grows the top cell at the expense of the bottom one.
  adjustLeftSplit: (deltaFrac: number) => void;
  adjustRightSplit: (deltaFrac: number) => void;

  reset: () => void;
}

export const useDeskLayout = create<DeskLayoutStore>((set, get) => ({
  camera: DEFAULT_CAMERA,
  lookAt: DEFAULT_LOOK_AT,
  wallAnchor: DEFAULT_WALL_ANCHOR,
  wallWidthPx: DEFAULT_WALL_WIDTH_PX,
  wallHeightPx: DEFAULT_WALL_HEIGHT_PX,
  curveRadiusPx: DEFAULT_CURVE_RADIUS_PX,
  bgOpacity: DEFAULT_BG_OPACITY,
  bgBlur: DEFAULT_BG_BLUR,
  headerFontPx: DEFAULT_HEADER_FONT_PX,
  colFrac: DEFAULT_COL_FRAC,
  leftSplit: DEFAULT_LEFT_SPLIT,
  rightSplit: DEFAULT_RIGHT_SPLIT,

  setCamera: (patch) => set({ camera: { ...get().camera, ...patch } }),
  setLookAt: (patch) => set({ lookAt: { ...get().lookAt, ...patch } }),
  setWallAnchor: (patch) => set({ wallAnchor: { ...get().wallAnchor, ...patch } }),
  setWallWidthPx: (v) => set({ wallWidthPx: clamp(v, 800, 2400) }),
  setWallHeightPx: (v) => set({ wallHeightPx: clamp(v, 300, 1800) }),
  setCurveRadiusPx: (v) => set({ curveRadiusPx: clamp(v, 500, 1500) }),
  setBgOpacity: (v) => set({ bgOpacity: clamp(v, 0, 1) }),
  setBgBlur: (v) => set({ bgBlur: Math.max(0, v) }),
  setHeaderFontPx: (v) =>
    set({ headerFontPx: clamp(v, MIN_HEADER_FONT_PX, MAX_HEADER_FONT_PX) }),

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
  adjustRightSplit: (delta) =>
    set({
      rightSplit: clamp(get().rightSplit + delta, MIN_SPLIT, 1 - MIN_SPLIT),
    }),

  reset: () =>
    set({
      camera: DEFAULT_CAMERA,
      lookAt: DEFAULT_LOOK_AT,
      wallAnchor: DEFAULT_WALL_ANCHOR,
      wallWidthPx: DEFAULT_WALL_WIDTH_PX,
      wallHeightPx: DEFAULT_WALL_HEIGHT_PX,
      curveRadiusPx: DEFAULT_CURVE_RADIUS_PX,
      bgOpacity: DEFAULT_BG_OPACITY,
      bgBlur: DEFAULT_BG_BLUR,
      headerFontPx: DEFAULT_HEADER_FONT_PX,
      colFrac: DEFAULT_COL_FRAC,
      leftSplit: DEFAULT_LEFT_SPLIT,
      rightSplit: DEFAULT_RIGHT_SPLIT,
    }),
}));
