import { create } from "zustand";
import {
  DEFAULT_TITLE_FLICKER_ASPECTS,
  DEFAULT_TITLE_FLICKER_TUNING,
  type TitleFlickerTuning,
  type TitleFlickerAspects,
} from "../lib/titleFlicker";

const STEP_FLOOR = 80;

export const TITLE_FONTS = [
  { label: "Chakra Petch", family: '"Chakra Petch", sans-serif', weight: 600 },
  { label: "Rajdhani", family: '"Rajdhani", sans-serif', weight: 400 },
  { label: "JetBrains Mono", family: '"Title JetBrains Mono", monospace', weight: 400 },
  { label: "Varela Round", family: '"Varela Round", sans-serif', weight: 400 },
];

export const DEFAULT_TITLE_TYPE = {
  size: 100,
  weight: 600,
  thickness: 0,
  spacing: 0.01,
  width: 100,
  slant: 0,
  outlineWidth: 1,
};

export type TitleType = typeof DEFAULT_TITLE_TYPE;

export const TITLE_TYPE_SLIDERS: {
  id: keyof TitleType;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
}[] = [
  { id: "size", label: "Size", min: 50, max: 200, step: 1, unit: "%" },
  { id: "weight", label: "Weight", min: 300, max: 700, step: 100, unit: "" },
  { id: "thickness", label: "Thickness", min: 0, max: 3, step: 0.1, unit: "px" },
  { id: "spacing", label: "Letter spacing", min: -0.05, max: 0.3, step: 0.01, unit: "em" },
  { id: "width", label: "Width", min: 60, max: 150, step: 1, unit: "%" },
  { id: "slant", label: "Slant", min: -20, max: 20, step: 1, unit: "°" },
  { id: "outlineWidth", label: "Outline width", min: 0.25, max: 3, step: 0.25, unit: "px" },
];

export const TITLE_FLICKER_ASPECTS: {
  id: keyof TitleFlickerAspects;
  label: string;
}[] = [
  { id: "outline", label: "Outline before fill" },
  { id: "letters", label: "Letter by letter" },
  { id: "ghost", label: "Ghost doubles" },
  { id: "scatter", label: "Letter jump" },
  { id: "whiteHot", label: "White flash on lock" },
  { id: "glow", label: "Neon glow" },
];

export const TITLE_FLICKER_SLIDERS: {
  id: keyof TitleFlickerTuning;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  aspect?: keyof TitleFlickerAspects;
}[] = [
  { id: "catchSpread", label: "Catch spread", min: 0, max: 0.9, step: 0.05, unit: "", aspect: "letters" },
  { id: "flickerHz", label: "Flicker rate", min: 5, max: 30, step: 1, unit: "Hz" },
  { id: "ghostOpacity", label: "Ghost strength", min: 0, max: 0.8, step: 0.01, unit: "", aspect: "ghost" },
  { id: "jumpEm", label: "Jump distance", min: 0, max: 0.5, step: 0.01, unit: "em", aspect: "scatter" },
  { id: "flashMs", label: "Flash length", min: 0, max: 200, step: 5, unit: "ms", aspect: "whiteHot" },
  { id: "glowStrength", label: "Glow strength", min: 0, max: 2, step: 0.05, unit: "", aspect: "glow" },
];

/** Compact outline → two fill flashes → grouped lock. */
const DEFAULT_DURATION_MS = 1000;

interface TitleFlickerStore {
  fontIndex: number;
  typography: TitleType;
  setTypography: (id: keyof TitleType, value: number) => void;
  resetTypography: () => void;
  cycleFont: (direction: -1 | 1) => void;
  durationMs: number;
  aspects: TitleFlickerAspects;
  tuning: TitleFlickerTuning;
  setTuning: (id: keyof TitleFlickerTuning, value: number) => void;
  setDuration: (ms: number) => void;
  setAspect: (id: keyof TitleFlickerAspects, on: boolean) => void;
  reset: () => void;
}

export const useTitleFlicker = create<TitleFlickerStore>((set) => ({
  fontIndex: 0,
  typography: { ...DEFAULT_TITLE_TYPE },
  setTypography: (id, value) => {
    if (!Number.isFinite(value)) return;
    const slider = TITLE_TYPE_SLIDERS.find((item) => item.id === id)!;
    set((s) => ({ typography: {
      ...s.typography,
      [id]: Math.max(slider.min, Math.min(slider.max, value)),
    } }));
  },
  resetTypography: () => set({ typography: { ...DEFAULT_TITLE_TYPE } }),
  cycleFont: (direction) => set((s) => ({
    fontIndex: (s.fontIndex + direction + TITLE_FONTS.length) % TITLE_FONTS.length,
  })),
  durationMs: DEFAULT_DURATION_MS,
  aspects: { ...DEFAULT_TITLE_FLICKER_ASPECTS },
  tuning: { ...DEFAULT_TITLE_FLICKER_TUNING },

  setTuning: (id, value) => {
    const slider = TITLE_FLICKER_SLIDERS.find((item) => item.id === id)!;
    if (!Number.isFinite(value)) return;
    set((s) => ({ tuning: { ...s.tuning, [id]: Math.max(slider.min, Math.min(slider.max, value)) } }));
  },

  setDuration: (ms) => set({ durationMs: Math.max(STEP_FLOOR, Math.round(ms)) }),

  setAspect: (id, on) =>
    set((s) => ({ aspects: { ...s.aspects, [id]: on } })),

  reset: () =>
    set({
      fontIndex: 0,
      typography: { ...DEFAULT_TITLE_TYPE },
      durationMs: DEFAULT_DURATION_MS,
      aspects: { ...DEFAULT_TITLE_FLICKER_ASPECTS },
      tuning: { ...DEFAULT_TITLE_FLICKER_TUNING },
    }),
}));
