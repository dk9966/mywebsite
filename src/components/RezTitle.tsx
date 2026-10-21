import { useLayoutEffect, useRef } from "react";
import { bootElapsedMs, bootSkipped, type PanelBoot } from "../lib/bootSequence";
import {
  ghostTextShadow,
  letterCatch,
  neonTextShadow,
  outlineBloomFilter,
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
  const tubeMode = useTitleFlicker((s) => s.tubeMode);
  const tubeLights = useTitleFlicker((s) => s.tubeLights);
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
      // Bloom is a separate emissive layer; the foreground stroke stays sharp.
      const outlinePower = tubeMode
        ? (tubeLights && aspects.outline && aspects.glow ? tuning.outlineBloom * tuning.glowStrength : 0)
        : (c.outline ? c.glow : 0);
      el.style.setProperty("--outline-spill", String(1 - Math.exp(-0.65 * outlinePower)));
      el.style.setProperty("--outline-spill-width", `${typography.outlineWidth}px`);
      if (tubeMode) {
        // Visible tube outlines are already illuminated. Only their fill
        // follows the catch clock; outline bloom does not wait for ignition.
        el.style.opacity = "1";
        el.style.transform = "none";
        el.style.color = "inherit";
        el.style.webkitTextFillColor = "";
        el.style.webkitTextStroke = "";
        el.style.textShadow = "none";
        el.style.filter = "none";
        el.style.setProperty("--tube-radius", `${Math.max(1.5, typography.outlineWidth * 1.6)}px`);
        el.style.setProperty("--tube-power", String(tubeLights ? (aspects.outline ? 1 : c.opacity) : 0));
        el.style.setProperty("--tube-core", c.hot ? "#ffffff" : "#b9ffff");
        const tubeFilters = [
          ...(c.ghost ? ["drop-shadow(0.09em 0.03em rgba(110,226,255,0.4))", "drop-shadow(-0.06em 0 rgba(110,226,255,0.25))"] : []),
          outlineBloomFilter(aspects.glow ? tuning.outlineBloom * tuning.glowStrength : 0),
        ].filter(Boolean).join(" ");
        el.style.setProperty("--tube-bloom", tubeLights ? tubeFilters || "none" : "none");
        el.style.setProperty("--tube-jump", `${c.x.toFixed(3)}em`);
        el.style.setProperty("--fill-power", String(c.outline ? 0 : c.opacity));
        el.style.setProperty("--fill-glow", c.ghost ? ghostTextShadow(c.glow) : neonTextShadow(c.glow, c.hot));
        el.style.setProperty("--fill-color", c.hot ? "#ffffff" : "#b9f5ff");
        el.style.setProperty("--fill-stroke", `${typography.thickness}px`);
        el.dataset.phase = c.opacity === 0 ? "dark" : c.outline ? "outline" : "filled";
        return;
      }
      el.style.opacity = String(c.opacity);
      el.style.transform = c.x ? `translateX(${c.x.toFixed(3)}em)` : "none";
      el.style.color = c.hot ? "#ffffff" : c.ghost ? "rgba(170,240,255,0.7)" : c.outline ? "#edf7ff" : "#b9f5ff";
      el.style.webkitTextFillColor = c.outline ? "transparent" : "currentColor";
      el.style.webkitTextStroke = `${c.outline ? typography.outlineWidth : typography.thickness}px currentColor`;
      el.dataset.phase = c.opacity === 0 ? "dark" : c.outline ? "outline" : "filled";
      // Text shadows paint solid glyphs, so hollow letters use drop shadows
      // of the stroke itself to keep their centers empty, including doubles.
      el.style.textShadow = c.outline ? "none" : c.ghost ? ghostTextShadow(c.glow) : neonTextShadow(c.glow, c.hot);
      const outlineFilters = [
        ...(c.ghost ? ["drop-shadow(0.09em 0.03em rgba(110,226,255,0.4))", "drop-shadow(-0.06em 0 rgba(110,226,255,0.25))"] : []),

      ];
      el.style.filter = c.outline ? outlineFilters.join(" ") || "none" : c.ghost ? "blur(0.6px)" : "none";
    });
  }, [
    tubeMode,
    tubeLights,
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
          className={`neon-title__letter${tubeMode ? " neon-title__letter--tube" : ""}`}
          data-glyph={ch}
          aria-hidden
        >
          {tubeMode ? <>
            <span className="neon-tube__measure">{ch}</span>
            <span className="neon-tube__depth">{ch}</span>
            <span className="neon-tube__glass">{ch}</span>
            <span className="neon-tube__rim">{ch}</span>
            <span className="neon-tube__reflection">{ch}</span>
            <span className="neon-tube__light">{ch}</span>
            <span className="neon-tube__fill">{ch}</span>
          </> : ch}
        </span>
      ))}
    </span>
  );
}
