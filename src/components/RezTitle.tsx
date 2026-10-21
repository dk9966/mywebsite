import { useLayoutEffect, useRef } from "react";
import { bootElapsedMs, bootSkipped, type PanelBoot } from "../lib/bootSequence";
import { neonTextShadow, titleCatch } from "../lib/titleFlicker";
import { useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";
import { useTitleFlicker } from "../stores/titleFlicker";

/**
 * One neon title for a panel. It sits on the flat handle layer so the halo
 * is a single glow, and it strobes with the boot clock.
 */
export default function RezTitle({
  boot,
  title,
  headerFontPx,
  padX,
  padY,
  center,
}: {
  boot: PanelBoot;
  title: string;
  headerFontPx: number;
  padX: number;
  padY: number;
  center: boolean;
}) {
  const titleRef = useRef<HTMLSpanElement>(null);
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const scrubbing = useBootClock((s) => s.scrubbing);
  const delayMs = useBootTuning((s) => s.parts.titleReveal.delayMs);
  const durationMs = useTitleFlicker((s) => s.durationMs);
  const aspects = useTitleFlicker((s) => s.aspects);

  useLayoutEffect(() => {
    const el = titleRef.current;
    if (!el) return;

    const paint = (opacity: number, glow: number, hot: boolean) => {
      el.style.opacity = String(opacity);
      el.style.color = hot ? "#ffffff" : "#f7feff";
      el.style.textShadow = neonTextShadow(glow, hot);
      el.style.filter =
        glow > 0
          ? `drop-shadow(0 0 ${Math.round(12 * glow)}px rgba(150, 236, 255, ${hot ? 0.95 : 0.8}))`
          : "none";
    };

    if (bootSkipped()) {
      paint(1, aspects.glow ? 1 : 0, false);
      return;
    }

    const elapsed = paused || scrubbing ? elapsedMs : bootElapsedMs();
    const start = boot.startMs + delayMs;
    if (elapsed < start) {
      paint(0, 0, false);
      return;
    }

    const caught = titleCatch(elapsed, start, durationMs, boot.seed, aspects);
    paint(caught.opacity, caught.glow, caught.hot);
  }, [
    aspects,
    boot.seed,
    boot.startMs,
    delayMs,
    durationMs,
    elapsedMs,
    paused,
    scrubbing,
  ]);

  return (
    <span
      ref={titleRef}
      className={center ? "neon-title neon-title--center" : "neon-title"}
      style={{
        fontSize: `${Math.round(headerFontPx * 1.35)}px`,
        left: `${padX}px`,
        top: center ? "50%" : `${padY}px`,
      }}
    >
      {title}
    </span>
  );
}
