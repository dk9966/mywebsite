import { useEffect } from "react";
import { bootElapsedMs, bootSkipped, startBootClock } from "../lib/bootSequence";
import { useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";

/** Drives the shared boot timeline and publishes CSS vars on :root. */
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

  useEffect(() => {
    const root = document.documentElement;
    const applyVars = () => {
      const vars = useBootTuning.getState().cssVars();
      for (const [key, value] of Object.entries(vars)) {
        root.style.setProperty(key, value);
      }
      root.style.setProperty("--boot-elapsed", `${bootElapsedMs()}ms`);
      for (const id of Object.keys(parts) as (keyof typeof parts)[]) {
        root.style.setProperty(
          `--boot-show-${id}`,
          parts[id].visible ? "1" : "0",
        );
      }
    };
    applyVars();
    let id = 0;
    const loop = () => {
      if (!bootSkipped()) {
        tick();
        applyVars();
      }
      id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [tick, parts, stabilizeMs, paused, scrubbing]);

  return null;
}
