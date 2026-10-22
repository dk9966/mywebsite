import { create } from "zustand";
import { BOOT_TOTAL_MS } from "../lib/bootParts";

let anchorAt: number | null = null;

function clampElapsed(ms: number): number {
  return Math.max(0, Math.min(ms, BOOT_TOTAL_MS));
}

/** Re-base performance.now() so bootElapsedMs() returns `elapsedMs`. */
export function armBootClock(elapsedMs: number): void {
  anchorAt = performance.now() - elapsedMs;
}

/** performance.now() at boot time 0, or null before the clock is armed. */
export function bootClockAnchor(): number | null {
  return anchorAt;
}

export function bootAnchorElapsedMs(): number {
  if (anchorAt === null) return useBootClock.getState().elapsedMs;
  return performance.now() - anchorAt;
}

interface BootClockStore {
  elapsedMs: number;
  paused: boolean;
  scrubbing: boolean;

  tick: () => void;
  seek: (ms: number) => void;
  setScrubbing: (scrubbing: boolean) => void;
  togglePause: () => void;
  restart: () => void;
  play: () => void;
  pause: () => void;
}

export const useBootClock = create<BootClockStore>((set, get) => ({
  elapsedMs: 0,
  paused: false,
  scrubbing: false,

  tick: () => {
    const { paused, scrubbing } = get();
    if (paused || scrubbing) return;
    const elapsedMs = clampElapsed(bootAnchorElapsedMs());
    set({ elapsedMs });
  },

  seek: (ms) => {
    const elapsedMs = clampElapsed(ms);
    armBootClock(elapsedMs);
    set({ elapsedMs });
  },

  setScrubbing: (scrubbing) => {
    if (scrubbing) {
      const elapsedMs = clampElapsed(bootAnchorElapsedMs());
      armBootClock(elapsedMs);
      set({ scrubbing: true, paused: true, elapsedMs });
      return;
    }
    set({ scrubbing: false });
  },

  togglePause: () => {
    const { paused, elapsedMs } = get();
    if (paused) {
      armBootClock(elapsedMs);
      set({ paused: false, scrubbing: false });
    } else {
      const live = clampElapsed(bootAnchorElapsedMs());
      armBootClock(live);
      set({ paused: true, elapsedMs: live });
    }
  },

  restart: () => {
    armBootClock(0);
    set({ elapsedMs: 0, paused: false, scrubbing: false });
  },

  play: () => {
    const elapsedMs = clampElapsed(get().elapsedMs);
    armBootClock(elapsedMs);
    set({ paused: false, scrubbing: false, elapsedMs });
  },

  pause: () => {
    const elapsedMs = clampElapsed(bootAnchorElapsedMs());
    armBootClock(elapsedMs);
    set({ paused: true, elapsedMs });
  },
}));
