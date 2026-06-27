import { create } from "zustand";

const DEFAULT_DURATION = 20;

interface ClockStore {
  time: number;
  duration: number;
  paused: boolean;
  tick: (delta: number) => void;
  seek: (time: number) => void;
  setDuration: (duration: number) => void;
  restart: () => void;
  togglePause: () => void;
}

export const useClock = create<ClockStore>((set, get) => ({
  time: 0,
  duration: DEFAULT_DURATION,
  paused: false,
  tick: (delta) => {
    if (!get().paused) set({ time: get().time + delta });
  },
  seek: (time) => {
    const duration = get().duration;
    set({ time: Math.max(0, Math.min(time, duration)) });
  },
  setDuration: (duration) => {
    const next = Math.max(0.1, duration);
    const time = Math.min(get().time, next);
    set({ duration: next, time });
  },
  restart: () => set({ time: 0 }),
  togglePause: () => set({ paused: !get().paused }),
}));
