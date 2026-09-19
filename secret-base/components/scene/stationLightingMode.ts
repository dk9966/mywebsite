import { create } from "zustand";

type LightingMode = "original" | "optimized";

export const useStationLightingMode = create<{
  mode: LightingMode;
  setMode: (mode: LightingMode) => void;
}>((set) => ({
  mode: "optimized",
  setMode: (mode) => set({ mode }),
}));
