import { create } from "zustand";

const KEY = "station-square-panel-corners-v2";
function savedCorners() {
  try { return localStorage.getItem(KEY) !== "false"; } catch { return true; }
}

const WIDTH_KEY = "station-panel-border-thickness";
function savedThickness() {
  try {
    const value = Number(localStorage.getItem(WIDTH_KEY) ?? 1);
    return Number.isFinite(value) ? Math.max(0.01, Math.min(2, value)) : 1;
  } catch { return 1; }
}

export const usePanelBorder = create<{ thickness: number; setThickness: (value: number) => void }>((set) => ({
  thickness: savedThickness(),
  setThickness: (value) => {
    if (!Number.isFinite(value)) return;
    const thickness = Math.max(0.01, Math.min(2, value));
    try { localStorage.setItem(WIDTH_KEY, String(thickness)); } catch { /* Optional storage. */ }
    set({ thickness });
  },
}));

export const usePanelCorners = create<{ square: boolean; toggle: () => void }>((set) => ({
  square: savedCorners(),
  toggle: () => set((state) => {
    const square = !state.square;
    try { localStorage.setItem(KEY, String(square)); } catch { /* Optional storage. */ }
    return { square };
  }),
}));
