import { useState, type PointerEvent as ReactPointerEvent } from "react";
import { BOOT_TOTAL_MS } from "../lib/bootParts";
import { useBootClock } from "../stores/bootClock";
import {
  TITLE_FLICKER_ASPECTS,
  useTitleFlicker,
} from "../stores/titleFlicker";
import "./DeskControls.css";

function formatBootMs(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Tuner for the Disney title rez. Same chrome as the root HUD panel:
 * a time scrub, one slider for the catch, and a checkbox per aspect.
 */
export default function TitleFlickerControls() {
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const seek = useBootClock((s) => s.seek);
  const restart = useBootClock((s) => s.restart);
  const togglePause = useBootClock((s) => s.togglePause);
  const setScrubbing = useBootClock((s) => s.setScrubbing);

  const durationMs = useTitleFlicker((s) => s.durationMs);
  const setDuration = useTitleFlicker((s) => s.setDuration);
  const aspects = useTitleFlicker((s) => s.aspects);
  const setAspect = useTitleFlicker((s) => s.setAspect);
  const reset = useTitleFlicker((s) => s.reset);

  const [minimized, setMinimized] = useState(false);

  const stop = (e: ReactPointerEvent) => e.stopPropagation();

  return (
    <aside
      className={[
        "desk-controls",
        minimized ? "desk-controls--minimized" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ left: 12, top: 12 }}
      onPointerDown={stop}
    >
      <div className="desk-controls__header">
        <h3 className="desk-controls__title">Title rez</h3>
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
              onPointerDown={() => setScrubbing(true)}
              onPointerUp={() => setScrubbing(false)}
              onChange={(e) => seek(Number(e.target.value))}
            />
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
