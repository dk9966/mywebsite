import { useEffect } from "react";
import { BOOT_TOTAL_MS, bootElapsedMs, bootSkipped, startBootClock } from "../lib/bootSequence";
import { bootClockAnchor, useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";

/** Keeps ticking a little past the timeline's end so every closing frame lands. */
const SETTLE_MS = 1000;

/** A playing animation whose start time is further off than this gets re-pinned. */
const DRIFT_MS = 1;

function bootAnimations(): CSSAnimation[] {
  return document
    .getAnimations()
    .filter(
      (a): a is CSSAnimation =>
        a instanceof CSSAnimation && a.animationName.startsWith("boot-"),
    );
}

/** Puts every boot-* CSS animation on the shared clock. While live each one
 *  is pinned by startTime to the clock's anchor (document.timeline shares
 *  performance.now()'s origin) and then plays natively; the compositor carries
 *  opacity/transform, so a frame only touches animations that are new or were
 *  re-anchored. Pinning startTime rather than seeking currentTime also skips
 *  play()'s pending phase, which would otherwise read as drift and re-seek. */
function syncBootAnimations(): void {
  const { paused, scrubbing } = useBootClock.getState();
  const anchor = bootClockAnchor();
  const live = !paused && !scrubbing && anchor !== null;
  const elapsedMs = bootElapsedMs();
  for (const a of bootAnimations()) {
    if (!live) {
      if (a.playState !== "paused") a.pause();
      if (a.currentTime !== elapsedMs) a.currentTime = elapsedMs;
      continue;
    }
    if (
      a.playState !== "paused" &&
      a.startTime !== null &&
      Math.abs(Number(a.startTime) - anchor) <= DRIFT_MS
    ) {
      continue;
    }
    // play() takes over from the CSS play-state; setting startTime right
    // after cancels its pending task (and any rewind past the end).
    a.play();
    a.startTime = anchor;
  }
}

/** Drives the shared boot timeline and publishes timing vars on :root. */
export default function BootClockDriver() {
  const paused = useBootClock((s) => s.paused);
  const scrubbing = useBootClock((s) => s.scrubbing);
  const tick = useBootClock((s) => s.tick);
  const parts = useBootTuning((s) => s.parts);
  const stabilizeMs = useBootTuning((s) => s.stabilizeMs);

  useEffect(() => {
    if (bootSkipped()) return;
    startBootClock();
  }, []);

  // Timing vars only change when the tuning does; writing custom properties
  // on :root restyles the whole document, so never do it per frame.
  useEffect(() => {
    const root = document.documentElement;
    const vars = useBootTuning.getState().cssVars();
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
    for (const id of Object.keys(parts) as (keyof typeof parts)[]) {
      root.style.setProperty(
        `--boot-show-${id}`,
        parts[id].visible ? "1" : "0",
      );
    }
  }, [parts, stabilizeMs]);

  useEffect(() => {
    // Once the boot has played out every animation rests on its fill frame
    // and nothing needs driving. A restart or seek wakes the loop.
    const running = () => {
      const { paused, scrubbing } = useBootClock.getState();
      return !bootSkipped() && (paused || scrubbing || bootElapsedMs() < BOOT_TOTAL_MS + SETTLE_MS);
    };
    let id = 0;
    const loop = () => {
      if (!bootSkipped()) {
        tick();
        syncBootAnimations();
      }
      id = running() ? requestAnimationFrame(loop) : 0;
    };
    const wake = () => {
      if (!id && running()) id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop);
    const unsubscribe = useBootClock.subscribe(wake);
    return () => {
      cancelAnimationFrame(id);
      unsubscribe();
    };
  }, [tick, paused, scrubbing]);

  return null;
}
