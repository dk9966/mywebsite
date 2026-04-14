import { create } from "zustand";

export interface LineConfig {
  lineColor: string;
  lineOpacity: number;
  glowColor: string;
  glowOpacity: number;
  tipColor: string;
  tipPointCount: number;
  tipLength: number;
  tipWidth: number;
  tipOpacity: number;
  cursorSpeed: number;
  gridColor: string;
  gridOpacity: number;
  bloomIntensity: number;
  bloomThreshold: number;
  bloomSmoothing: number;
}

export const DEFAULTS: LineConfig = {
  lineColor: "#e0ffff",
  lineOpacity: 1.0,
  glowColor: "#00d4ff",
  glowOpacity: 0.5,
  tipColor: "#ffffff",
  tipPointCount: 6,
  tipLength: 0.5,
  tipWidth: 0.1,
  tipOpacity: 0.9,
  cursorSpeed: 8,
  gridColor: "#003040",
  gridOpacity: 0.06,
  bloomIntensity: 2.5,
  bloomThreshold: 0.05,
  bloomSmoothing: 0.5,
};

interface LineConfigStore {
  config: LineConfig;
  set: (patch: Partial<LineConfig>) => void;
  reset: () => void;
}

export const useLineConfig = create<LineConfigStore>((set) => ({
  config: { ...DEFAULTS },
  set: (patch) =>
    set((s) => ({ config: { ...s.config, ...patch } })),
  reset: () => set({ config: { ...DEFAULTS } }),
}));
