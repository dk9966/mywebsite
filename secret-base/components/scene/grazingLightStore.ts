import { create } from "zustand";

export const GRAZING_DEFAULT = 1.6;
export const GRAZING_MAX = 8;
const STORAGE_KEY = "station-grazing-strength";

function initialStrength() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const value = saved === null ? GRAZING_DEFAULT : Number(saved);
    return Number.isFinite(value) ? Math.min(GRAZING_MAX, Math.max(0, value)) : GRAZING_DEFAULT;
  } catch { return GRAZING_DEFAULT; }
}

export const useGrazingLight = create<{ strength: number; setStrength: (value: number) => void }>((set) => ({
  strength: initialStrength(),
  setStrength: (value) => {
    if (!Number.isFinite(value)) return;
    const strength = Math.min(GRAZING_MAX, Math.max(0, value));
    try { localStorage.setItem(STORAGE_KEY, String(strength)); } catch { /* Storage is optional. */ }
    set({ strength });
  },
}));
