import { create } from "zustand";
import {
  DEFAULT_TITLE_FLICKER_ASPECTS,
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

/** The "Walt Disney" line takes about 1.5s to lock in the ident. */
const DEFAULT_DURATION_MS = 1500;

interface TitleFlickerStore {
  durationMs: number;
  aspects: TitleFlickerAspects;
  setDuration: (ms: number) => void;
  setAspect: (id: keyof TitleFlickerAspects, on: boolean) => void;
  reset: () => void;
}

export const useTitleFlicker = create<TitleFlickerStore>((set) => ({
  durationMs: DEFAULT_DURATION_MS,
  aspects: { ...DEFAULT_TITLE_FLICKER_ASPECTS },

  setDuration: (ms) => set({ durationMs: Math.max(STEP_FLOOR, Math.round(ms)) }),

  setAspect: (id, on) =>
    set((s) => ({ aspects: { ...s.aspects, [id]: on } })),

  reset: () =>
    set({
      durationMs: DEFAULT_DURATION_MS,
      aspects: { ...DEFAULT_TITLE_FLICKER_ASPECTS },
    }),
}));
