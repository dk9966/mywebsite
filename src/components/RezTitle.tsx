import { useLayoutEffect, useRef } from "react";
import { bootElapsedMs, bootSkipped, type PanelBoot } from "../lib/bootSequence";
import {
  ghostTextShadow,
  letterCatch,
  neonTextShadow,
  type LetterCatch,
} from "../lib/titleFlicker";
import { useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";
import { useTitleFlicker } from "../stores/titleFlicker";

const HELD: LetterCatch = { opacity: 1, x: 0, ghost: false, hot: false, glow: 1 };

/**
 * Neon panel title on the flat handle layer, so the halo is one glow. Each
 * letter catches on its own, the way "Walt Disney" does in the TRON ident.
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
  const letterRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const scrubbing = useBootClock((s) => s.scrubbing);
  const delayMs = useBootTuning((s) => s.parts.titleReveal.delayMs);
  const durationMs = useTitleFlicker((s) => s.durationMs);
  const tuning = useTitleFlicker((s) => s.tuning);
  const aspects = useTitleFlicker((s) => s.aspects);

  useLayoutEffect(() => {
    const elapsed = paused || scrubbing ? elapsedMs : bootElapsedMs();
    const start = boot.startMs + delayMs;

    letterRefs.current.forEach((el, i) => {
      if (!el) return;
      const c = bootSkipped()
        ? { ...HELD, glow: aspects.glow ? tuning.glowStrength : 0 }
        : letterCatch(elapsed, start, durationMs, boot.seed, i, aspects, tuning);
      el.style.opacity = String(c.opacity);
      el.style.transform = c.x ? `translateX(${c.x.toFixed(3)}em)` : "none";
      el.style.color = c.hot ? "#ffffff" : c.ghost ? "rgba(170,240,255,0.7)" : "#b9f5ff";
      el.style.textShadow = c.ghost ? ghostTextShadow(c.glow) : neonTextShadow(c.glow, c.hot);
      el.style.filter = c.ghost ? "blur(0.6px)" : "none";
    });
  }, [
    aspects,
    tuning,
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
      className={center ? "neon-title neon-title--center" : "neon-title"}
      aria-label={title}
      style={{
        fontSize: `${Math.round(headerFontPx * 1.35)}px`,
        left: `${padX}px`,
        top: center ? "50%" : `${padY}px`,
      }}
    >
      {[...title].map((ch, i) => (
        <span
          key={i}
          ref={(el) => {
            letterRefs.current[i] = el;
          }}
          className="neon-title__letter"
          aria-hidden
        >
          {ch}
        </span>
      ))}
    </span>
  );
}
