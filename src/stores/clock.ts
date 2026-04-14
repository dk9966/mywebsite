import { create } from "zustand";

interface ClockStore {
  time: number;
  paused: boolean;
  tick: (delta: number) => void;
  seek: (time: number) => void;
  restart: () => void;
  togglePause: () => void;
}

export const useClock = create<ClockStore>((set, get) => ({
  time: 0,
  paused: false,
  tick: (delta) => {
    if (!get().paused) set({ time: get().time + delta });
  },
  seek: (time) => set({ time }),
  restart: () => set({ time: 0 }),
  togglePause: () => set({ paused: !get().paused }),
}));
