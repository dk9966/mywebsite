import { useState, useCallback, useRef, useEffect } from "react";
import { useLineConfig, type LineConfig } from "../stores/lineConfig";
import { useClock } from "../stores/clock";
import "./Controls.css";

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}

function Slider({ label, value, min, max, step, onChange }: SliderProps) {
  return (
    <div className="controls__field">
      <span className="controls__label">{label}</span>
      <input
        className="controls__slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="controls__value">{value.toFixed(step < 1 ? 2 : 0)}</span>
    </div>
  );
}

interface ColorRowProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
}

function ColorRow({ label, value, onChange }: ColorRowProps) {
  return (
    <div className="controls__color-field">
      <span className="controls__label">{label}</span>
      <input
        className="controls__color-input"
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className="controls__color-hex">{value}</span>
    </div>
  );
}

function formatTime(t: number): string {
  const s = Math.floor(t % 60);
  const ms = Math.floor((t % 1) * 10);
  return `${s}.${ms}s`;
}

export default function Controls() {
  const cfg = useLineConfig((s) => s.config);
  const set = useLineConfig((s) => s.set);
  const resetConfig = useLineConfig((s) => s.reset);

  const time = useClock((s) => s.time);
  const paused = useClock((s) => s.paused);
  const seek = useClock((s) => s.seek);
  const restart = useClock((s) => s.restart);
  const togglePause = useClock((s) => s.togglePause);

  const [minimized, setMinimized] = useState(false);
  const [width, setWidth] = useState(280);
  const [pos, setPos] = useState({ x: 12, y: 12 });

  const drag = useRef<{ mode: "move" | "resize"; originX: number; originY: number; startX: number; startY: number; startW: number } | null>(null);

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    drag.current = { mode: "move", originX: pos.x, originY: pos.y, startX: e.clientX, startY: e.clientY, startW: width };
  }, [pos, width]);

  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    drag.current = { mode: "resize", originX: pos.x, originY: pos.y, startX: e.clientX, startY: e.clientY, startW: width };
  }, [pos, width]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!drag.current) return;
      const dx = e.clientX - drag.current.startX;
      const dy = e.clientY - drag.current.startY;
      if (drag.current.mode === "move") {
        setPos({
          x: Math.max(0, drag.current.originX - dx),
          y: Math.max(0, drag.current.originY + dy),
        });
      } else {
        setWidth(Math.max(220, Math.min(480, drag.current.startW - dx)));
      }
    };
    const onUp = () => { drag.current = null; };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const patch = (key: keyof LineConfig) => (v: number | string) =>
    set({ [key]: v });

  return (
    <aside
      className={`controls ${minimized ? "controls--minimized" : ""}`}
      style={{ width: minimized ? undefined : width, right: pos.x, top: pos.y }}
    >
      <div className="controls__header" onMouseDown={onDragStart}>
        <h3 className="controls__title">Line Tuning</h3>
        <div className="controls__header-actions">
          <button
            className="controls__btn"
            type="button"
            onClick={() => setMinimized(!minimized)}
            title={minimized ? "Expand" : "Minimize"}
          >
            {minimized ? "+" : "-"}
          </button>
        </div>
      </div>

      {!minimized && (
        <>
          <section className="controls__group controls__playback">
            <div className="controls__playback-row">
              <button className="controls__btn" type="button" onClick={restart} title="Restart">
                {"<<"}
              </button>
              <button className="controls__btn" type="button" onClick={togglePause} title={paused ? "Play" : "Pause"}>
                {paused ? ">" : "||"}
              </button>
              <span className="controls__time">{formatTime(time)}</span>
            </div>
            <input
              className="controls__slider controls__slider--time"
              type="range"
              min={0}
              max={20}
              step={0.05}
              value={time}
              onChange={(e) => seek(Number(e.target.value))}
            />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Colors</h4>
            <ColorRow label="Line" value={cfg.lineColor} onChange={patch("lineColor")} />
            <ColorRow label="Glow" value={cfg.glowColor} onChange={patch("glowColor")} />
            <ColorRow label="Tip" value={cfg.tipColor} onChange={patch("tipColor")} />
            <ColorRow label="Grid" value={cfg.gridColor} onChange={patch("gridColor")} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Opacity</h4>
            <Slider label="Line" value={cfg.lineOpacity} min={0} max={1} step={0.01} onChange={patch("lineOpacity") as (v: number) => void} />
            <Slider label="Glow" value={cfg.glowOpacity} min={0} max={1} step={0.01} onChange={patch("glowOpacity") as (v: number) => void} />
            <Slider label="Tip" value={cfg.tipOpacity} min={0} max={1} step={0.01} onChange={patch("tipOpacity") as (v: number) => void} />
            <Slider label="Grid" value={cfg.gridOpacity} min={0} max={0.3} step={0.005} onChange={patch("gridOpacity") as (v: number) => void} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Tip shape</h4>
            <Slider label="Length" value={cfg.tipLength} min={0.05} max={2} step={0.05} onChange={patch("tipLength") as (v: number) => void} />
            <Slider label="Width" value={cfg.tipWidth} min={0.02} max={0.6} step={0.01} onChange={patch("tipWidth") as (v: number) => void} />
            <Slider label="Gradient" value={cfg.tipPointCount} min={1} max={20} step={1} onChange={patch("tipPointCount") as (v: number) => void} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Bloom</h4>
            <Slider label="Intensity" value={cfg.bloomIntensity} min={0} max={8} step={0.1} onChange={patch("bloomIntensity") as (v: number) => void} />
            <Slider label="Threshold" value={cfg.bloomThreshold} min={0} max={1} step={0.01} onChange={patch("bloomThreshold") as (v: number) => void} />
            <Slider label="Smoothing" value={cfg.bloomSmoothing} min={0} max={1} step={0.01} onChange={patch("bloomSmoothing") as (v: number) => void} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Animation</h4>
            <Slider label="Speed" value={cfg.cursorSpeed} min={1} max={30} step={0.5} onChange={patch("cursorSpeed") as (v: number) => void} />
          </section>

          <hr className="controls__divider" />

          <button className="controls__reset" type="button" onClick={resetConfig}>
            Reset defaults
          </button>

          <div className="controls__resize" onMouseDown={onResizeStart} />
        </>
      )}
    </aside>
  );
}
