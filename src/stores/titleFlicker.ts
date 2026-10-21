import { create } from "zustand";
import {
  DEFAULT_TITLE_FLICKER_ASPECTS,
  DEFAULT_TITLE_FLICKER_TUNING,
  type TitleFlickerTuning,
  type TitleFlickerAspects,
} from "../lib/titleFlicker";

const STEP_FLOOR = 80;

export const TITLE_FLICKER_ASPECTS: {
  id: keyof TitleFlickerAspects;
  label: string;
}[] = [
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

/** The "Walt Disney" line takes about 1.5s to lock in the ident. */
const DEFAULT_DURATION_MS = 1500;

interface TitleFlickerStore {
  durationMs: number;
  aspects: TitleFlickerAspects;
  tuning: TitleFlickerTuning;
  setTuning: (id: keyof TitleFlickerTuning, value: number) => void;
  setDuration: (ms: number) => void;
  setAspect: (id: keyof TitleFlickerAspects, on: boolean) => void;
  reset: () => void;
}

export const useTitleFlicker = create<TitleFlickerStore>((set) => ({
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
      durationMs: DEFAULT_DURATION_MS,
      aspects: { ...DEFAULT_TITLE_FLICKER_ASPECTS },
      tuning: { ...DEFAULT_TITLE_FLICKER_TUNING },
    }),
}));
