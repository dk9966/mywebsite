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
import { TITLE_FONTS, useTitleFlicker } from "../stores/titleFlicker";

const HELD: LetterCatch = { opacity: 1, outline: false, x: 0, ghost: false, hot: false, glow: 1 };

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
  const fontIndex = useTitleFlicker((s) => s.fontIndex);
  const typography = useTitleFlicker((s) => s.typography);
  const tuning = useTitleFlicker((s) => s.tuning);
  const aspects = useTitleFlicker((s) => s.aspects);

  useLayoutEffect(() => {
    const elapsed = paused || scrubbing ? elapsedMs : bootElapsedMs();
    const start = boot.startMs + delayMs;

    letterRefs.current.forEach((el, i) => {
      if (!el) return;
      const c = bootSkipped()
        ? { ...HELD, glow: aspects.glow ? tuning.glowStrength * tuning.settledBloom : 0 }
        : letterCatch(elapsed, start, durationMs, boot.seed, i, aspects, tuning);
      el.style.opacity = String(c.opacity);
      el.style.transform = c.x ? `translateX(${c.x.toFixed(3)}em)` : "none";
      el.style.color = c.hot ? "#ffffff" : c.ghost ? "rgba(170,240,255,0.7)" : "#b9f5ff";
      el.style.webkitTextFillColor = c.outline ? "transparent" : "currentColor";
      el.style.webkitTextStroke = `${c.outline ? typography.outlineWidth : typography.thickness}px currentColor`;
      el.dataset.phase = c.opacity === 0 ? "dark" : c.outline ? "outline" : "filled";
      // Text shadows paint solid glyphs, so hollow letters use drop shadows
      // of the stroke itself to keep their centers empty, including doubles.
      el.style.textShadow = c.outline ? "none" : c.ghost ? ghostTextShadow(c.glow) : neonTextShadow(c.glow, c.hot);
      const outlineFilters = [
        ...(c.ghost ? ["drop-shadow(0.09em 0.03em rgba(110,226,255,0.4))", "drop-shadow(-0.06em 0 rgba(110,226,255,0.25))"] : []),
        ...(c.glow > 0 ? [`drop-shadow(0 0 ${4 * c.glow}px rgba(130,235,255,0.75))`, `drop-shadow(0 0 ${14 * c.glow}px rgba(60,190,255,0.45))`] : []),
      ];
      el.style.filter = c.outline ? outlineFilters.join(" ") || "none" : c.ghost ? "blur(0.6px)" : "none";
    });
  }, [
    aspects,
    tuning,
    typography,
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
        fontSize: `calc(var(--title-preview-font-size, ${Math.round(headerFontPx * 1.35)}px) * ${typography.size / 100})`,
        fontFamily: TITLE_FONTS[fontIndex].family,
        fontWeight: fontIndex === 0 ? typography.weight : TITLE_FONTS[fontIndex].weight,
        letterSpacing: `${typography.spacing}em`,
        transform: `${center ? "translateY(-50%) " : ""}scaleX(${typography.width / 100}) skewX(${-typography.slant}deg)`,
        transformOrigin: "var(--title-transform-origin, left center)",
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
