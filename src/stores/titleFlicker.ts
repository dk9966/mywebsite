import { create } from "zustand";
import { bootScaleMs } from "../lib/bootParts";
import {
  DEFAULT_TITLE_FLICKER_ASPECTS,
  type TitleFlickerAspects,
} from "../lib/titleFlicker";

const STEP_FLOOR = 80;

export const TITLE_FLICKER_ASPECTS: {
  id: keyof TitleFlickerAspects;
  label: string;
}[] = [
  { id: "glow", label: "Neon glow" },
  { id: "flicker", label: "Flicker" },
  { id: "whiteHot", label: "White flash" },
  { id: "dimTube", label: "Dim tube" },
  { id: "dropout", label: "Dropout" },
];

const DEFAULT_DURATION_MS = bootScaleMs(980);

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
