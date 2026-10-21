import { useLayoutEffect, useRef, type ReactNode } from "react";
import { bootElapsedMs, type PanelBoot } from "../lib/bootSequence";
import { titleCatch } from "../lib/titleFlicker";
import { useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";
import { useTitleFlicker } from "../stores/titleFlicker";

/**
 * Panel title that rezzes with the glass. The word stays put, and its
 * brightness follows the same stepped noise as the panel fill.
 *
 * The title lives in drei's HTML overlay, which is a separate React root.
 * The boot clock store is what moves this; a private animation frame was
 * getting cancelled when that overlay reconciled.
 */
export default function RezTitle({
  boot,
  title,
  headerFontPx,
  children,
}: {
  boot: PanelBoot;
  title: string;
  headerFontPx: number;
  children?: ReactNode;
}) {
  const handleRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLSpanElement>(null);
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const scrubbing = useBootClock((s) => s.scrubbing);
  const delayMs = useBootTuning((s) => s.parts.titleReveal.delayMs);
  const durationMs = useTitleFlicker((s) => s.durationMs);
  const aspects = useTitleFlicker((s) => s.aspects);

  useLayoutEffect(() => {
    const handle = handleRef.current;
    const el = titleRef.current;
    if (!handle || !el) return;

    const elapsed = paused || scrubbing ? elapsedMs : bootElapsedMs();
    const start = boot.startMs + delayMs;
    if (elapsed < start) {
      handle.style.opacity = "0";
      el.style.opacity = "0";
      el.style.transform = "none";
      el.style.color = "";
      el.style.filter = "none";
      el.style.textShadow = "";
      return;
    }

    handle.style.opacity = "1";
    const caught = titleCatch(elapsed, start, durationMs, boot.seed, aspects);
    el.style.opacity = String(caught.opacity);
    el.style.transform = caught.x ? `translateX(${caught.x}px)` : "none";
    el.style.color = caught.hot ? "#f4feff" : "";
    el.style.filter = caught.hot ? "brightness(1.65)" : "none";
    el.style.textShadow = caught.hot
      ? "0 0 8px rgba(244, 254, 255, 0.85)"
      : "";
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
    <div
      ref={handleRef}
      className="hud-screen__handle hud-screen__handle--rez"
      style={{ fontSize: `${headerFontPx}px` }}
    >
      <span ref={titleRef} className="hud-screen__handle-title">
        {title}
      </span>
      {children}
    </div>
  );
}
