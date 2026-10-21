import { useState, type PointerEvent as ReactPointerEvent } from "react";
import { BOOT_TOTAL_MS } from "../lib/bootParts";
import { useBootClock } from "../stores/bootClock";
import {
  TITLE_FONTS,
  TITLE_TYPE_SLIDERS,
  TITLE_FLICKER_ASPECTS,
  TITLE_FLICKER_SLIDERS,
  useTitleFlicker,
} from "../stores/titleFlicker";
import "./DeskControls.css";
import "./TitleFlickerControls.css";

function formatBootMs(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Tuner for the Disney title rez. Same chrome as the root HUD panel:
 * a time scrub, sliders for the catch, and a checkbox per aspect.
 */
export default function TitleFlickerControls() {
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const seek = useBootClock((s) => s.seek);
  const restart = useBootClock((s) => s.restart);
  const togglePause = useBootClock((s) => s.togglePause);
  const setScrubbing = useBootClock((s) => s.setScrubbing);

  const tubeMode = useTitleFlicker((s) => s.tubeMode);
  const tubeLights = useTitleFlicker((s) => s.tubeLights);
  const setTubeMode = useTitleFlicker((s) => s.setTubeMode);
  const setTubeLights = useTitleFlicker((s) => s.setTubeLights);
  const fontIndex = useTitleFlicker((s) => s.fontIndex);
  const cycleFont = useTitleFlicker((s) => s.cycleFont);
  const typography = useTitleFlicker((s) => s.typography);
  const setTypography = useTitleFlicker((s) => s.setTypography);
  const resetTypography = useTitleFlicker((s) => s.resetTypography);
  const durationMs = useTitleFlicker((s) => s.durationMs);
  const setDuration = useTitleFlicker((s) => s.setDuration);
  const tuning = useTitleFlicker((s) => s.tuning);
  const setTuning = useTitleFlicker((s) => s.setTuning);
  const aspects = useTitleFlicker((s) => s.aspects);
  const setAspect = useTitleFlicker((s) => s.setAspect);
  const reset = useTitleFlicker((s) => s.reset);

  const [minimized, setMinimized] = useState(false);

  const stop = (e: ReactPointerEvent) => e.stopPropagation();

  return (
    <aside
      className={[
        "desk-controls title-flicker-controls",
        minimized ? "desk-controls--minimized" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ left: 12, top: 12 }}
      onPointerDown={stop}
    >
      <div className="desk-controls__header">
        <h3 className="desk-controls__title">Titles</h3>
        <button
          className="desk-controls__btn"
          type="button"
          onClick={() => setMinimized(!minimized)}
          title={minimized ? "Expand" : "Minimize"}
        >
          {minimized ? "+" : "−"}
        </button>
      </div>

      {!minimized && (
        <>
          <section className="desk-controls__group desk-controls__playback">
            <h4 className="desk-controls__group-title">Playback</h4>
            <div className="desk-controls__playback-row">
              <button
                className="desk-controls__btn"
                type="button"
                onClick={restart}
                title="Restart"
              >
                {"<<"}
              </button>
              <button
                className="desk-controls__btn"
                type="button"
                onClick={togglePause}
                title={paused ? "Play" : "Pause"}
              >
                {paused ? ">" : "||"}
              </button>
              <span className="desk-controls__time">
                {formatBootMs(elapsedMs)} / {formatBootMs(BOOT_TOTAL_MS)}
              </span>
            </div>
            <input
              className="desk-controls__slider desk-controls__slider--time"
              type="range"
              min={0}
              max={BOOT_TOTAL_MS}
              step={10}
              value={Math.min(elapsedMs, BOOT_TOTAL_MS)}
              aria-label="Scrub title catch"
              onPointerDown={(e) => {
                e.currentTarget.setPointerCapture(e.pointerId);
                setScrubbing(true);
              }}
              onPointerUp={() => setScrubbing(false)}
              onPointerCancel={() => setScrubbing(false)}
              onLostPointerCapture={() => setScrubbing(false)}
              onChange={(e) => seek(Number(e.target.value))}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group" aria-label="Title font">
            <h4 className="desk-controls__group-title">Font</h4>
            <label className="desk-controls__checkbox-field">
              <input className="desk-controls__checkbox" type="checkbox" checked={tubeMode}
                onChange={(e) => setTubeMode(e.target.checked)} />
              <span className="desk-controls__checkbox-label">3D neon tubes</span>
            </label>
            {tubeMode && <label className="desk-controls__checkbox-field">
              <input className="desk-controls__checkbox" type="checkbox" checked={tubeLights}
                onChange={(e) => setTubeLights(e.target.checked)} />
              <span className="desk-controls__checkbox-label">Tube lights</span>
            </label>}
            <div className="title-flicker-controls__font">
              <button className="desk-controls__btn" type="button" aria-label="Previous font" onClick={() => cycleFont(-1)}>←</button>
              <span aria-live="polite">{TITLE_FONTS[fontIndex].label}</span>
              <button className="desk-controls__btn" type="button" aria-label="Next font" onClick={() => cycleFont(1)}>→</button>
            </div>
          </section>
          <hr className="desk-controls__divider" />

          <section className="desk-controls__group" aria-label="Typography">
            <h4 className="desk-controls__group-title">Typography</h4>
            {TITLE_TYPE_SLIDERS.map((slider) => (
              <label className="desk-controls__field" key={slider.id}
                title={slider.id === "weight" && fontIndex !== 0 ? "Weight variants are available for Chakra Petch; Thickness works with every font." : undefined}>
                <span className="desk-controls__label">{slider.label}</span>
                <input className="desk-controls__slider" type="range"
                  min={slider.min} max={slider.max} step={slider.step}
                  value={slider.id === "weight" && fontIndex !== 0 ? TITLE_FONTS[fontIndex].weight : typography[slider.id]}
                  disabled={slider.id === "weight" && fontIndex !== 0}
                  aria-label={`Font ${slider.label.toLowerCase()}`}
                  onChange={(e) => setTypography(slider.id, Number(e.target.value))} />
                <span className="desk-controls__value">
                  {Number((slider.id === "weight" && fontIndex !== 0 ? TITLE_FONTS[fontIndex].weight : typography[slider.id]).toFixed(2))}{slider.unit}
                </span>
              </label>
            ))}
            <button className="desk-controls__btn" type="button" onClick={resetTypography}>Reset typography</button>
          </section>
          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Catch</h4>
            <div className="desk-controls__field">
              <span className="desk-controls__label">Length</span>
              <input
                className="desk-controls__slider"
                type="range"
                min={80}
                max={2000}
                step={10}
                value={durationMs}
                aria-label="Title catch length"
                onChange={(e) => setDuration(Number(e.target.value))}
              />
              <span className="desk-controls__value">{durationMs}</span>
            </div>
            {TITLE_FLICKER_SLIDERS.map((slider) => (
              <label className="desk-controls__field" key={slider.id}>
                <span className="desk-controls__label">{slider.label}</span>
                <input
                  className="desk-controls__slider"
                  type="range"
                  min={slider.min}
                  max={slider.max}
                  step={slider.step}
                  value={tuning[slider.id]}
                  disabled={slider.aspect ? !aspects[slider.aspect] : false}
                  aria-label={slider.label}
                  onChange={(e) => setTuning(slider.id, Number(e.target.value))}
                />
                <span className="desk-controls__value">
                  {Number(tuning[slider.id].toFixed(2))}{slider.unit}
                </span>
              </label>
            ))}
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Aspects</h4>
            {TITLE_FLICKER_ASPECTS.map((aspect) => (
              <label className="desk-controls__checkbox-field" key={aspect.id}>
                <input
                  className="desk-controls__checkbox"
                  type="checkbox"
                  checked={aspects[aspect.id]}
                  onChange={(e) => setAspect(aspect.id, e.target.checked)}
                />
                <span className="desk-controls__checkbox-label">
                  {aspect.label}
                </span>
              </label>
            ))}
            <button
              className="desk-controls__btn"
              type="button"
              style={{ marginTop: 8 }}
              onClick={reset}
            >
              Reset
            </button>
          </section>
        </>
      )}
    </aside>
  );
}
