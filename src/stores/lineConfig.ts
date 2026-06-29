import { create } from "zustand";
import { GRID_SPACING } from "../lib/constants";

export interface LineConfig {
  lineColor: string;
  /** World-space stroke thickness (LineMaterial worldUnits). */
  lineWidth: number;
  /** Brightness multiplier before bloom; raises effective glow width. */
  lineEmission: number;
  lineOpacity: number;
  tipColor: string;
  tipPointCount: number;
  tipLength: number;
  tipWidth: number;
  tipOpacity: number;
  cursorSpeed: number;
  gridColor: string;
  /** World-space distance between background grid lines and path subdivisions. */
  gridSpacing: number;
  gridOpacity: number;
  bloomIntensity: number;
  bloomThreshold: number;
  bloomRadius: number;
  bloomSmoothing: number;
}

export const DEFAULTS: LineConfig = {
  lineColor: "#66f0f0",
  lineWidth: 0.04,
  lineEmission: 0.5,
  lineOpacity: 1.0,
  tipColor: "#66f0f0",
  tipPointCount: 6,
  tipLength: 0.5,
  tipWidth: 0.1,
  tipOpacity: 0.9,
  cursorSpeed: 8,
  gridColor: "#003040",
  gridSpacing: GRID_SPACING,
  gridOpacity: 0,
  bloomIntensity: 0.5,
  bloomThreshold: 0.05,
  bloomRadius: 0.5,
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
    set((s) => {
      const next = { ...s.config, ...patch };
      // Tip color follows line color until the user picks a different tip.
      const tipWasLinked = s.config.tipColor === s.config.lineColor;
      const tipUntouched = patch.tipColor === undefined;
      if (patch.lineColor !== undefined && tipWasLinked && tipUntouched) {
        next.tipColor = patch.lineColor;
      }
      return { config: next };
    }),
  reset: () => set({ config: { ...DEFAULTS } }),
}));
