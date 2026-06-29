import { useState, useCallback, useRef, useEffect } from "react";
import { useLineConfig, type LineConfig } from "../stores/lineConfig";
import { useClock } from "../stores/clock";
import { useCircuitTuning } from "../stores/circuitTuning";
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
  const clamped = Math.max(0, t);
  const whole = Math.floor(clamped);
  const s = whole % 60;
  const m = Math.floor(whole / 60);
  const ms = Math.floor((clamped % 1) * 10);
  if (m > 0) return `${m}:${String(s).padStart(2, "0")}.${ms}s`;
  return `${s}.${ms}s`;
}

export type ControlsCameraProps = {
  topView: boolean;
  onTopViewChange: (value: boolean) => void;
  fov: number;
  onFovChange: (value: number) => void;
};

type ControlsProps = {
  camera?: ControlsCameraProps;
};

export default function Controls({ camera }: ControlsProps = {}) {
  const cfg = useLineConfig((s) => s.config);
  const set = useLineConfig((s) => s.set);
  const resetConfig = useLineConfig((s) => s.reset);

  const time = useClock((s) => s.time);
  const duration = useClock((s) => s.duration);
  const paused = useClock((s) => s.paused);
  const seek = useClock((s) => s.seek);
  const restart = useClock((s) => s.restart);
  const togglePause = useClock((s) => s.togglePause);

  const topViewCamera = useCircuitTuning((s) => s.topViewCamera);
  const setTopViewCamera = useCircuitTuning((s) => s.setTopViewCamera);

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
              <span className="controls__time">{formatTime(time)} / {formatTime(duration)}</span>
            </div>
            <input
              className="controls__slider controls__slider--time"
              type="range"
              min={0}
              max={duration}
              step={0.05}
              value={Math.min(time, duration)}
              onChange={(e) => seek(Number(e.target.value))}
            />
          </section>

          {camera ? (
            <>
              <hr className="controls__divider" />

              <section className="controls__group">
                <h4 className="controls__group-title">Camera</h4>
                <label className="controls__checkbox-field">
                  <input
                    className="controls__checkbox"
                    type="checkbox"
                    checked={camera.topView}
                    onChange={(e) => camera.onTopViewChange(e.target.checked)}
                  />
                  <span className="controls__checkbox-label">Top view on appear</span>
                </label>
                <Slider
                  label="FOV"
                  value={camera.fov}
                  min={15}
                  max={90}
                  step={1}
                  onChange={camera.onFovChange}
                />
                <h5 className="controls__subgroup-title">Top view scan</h5>
                <Slider
                  label="Height"
                  value={topViewCamera.heightFactor}
                  min={0.05}
                  max={0.35}
                  step={0.01}
                  onChange={(v) => setTopViewCamera({ heightFactor: v })}
                />
                <Slider
                  label="Front lag"
                  value={topViewCamera.frontLagSec}
                  min={0}
                  max={5}
                  step={0.1}
                  onChange={(v) => setTopViewCamera({ frontLagSec: v })}
                />
                <Slider
                  label="Offset X"
                  value={topViewCamera.offset[0]}
                  min={-20}
                  max={20}
                  step={0.5}
                  onChange={(v) =>
                    setTopViewCamera({
                      offset: [v, topViewCamera.offset[1], topViewCamera.offset[2]],
                    })
                  }
                />
                <Slider
                  label="Offset Y"
                  value={topViewCamera.offset[1]}
                  min={-20}
                  max={20}
                  step={0.5}
                  onChange={(v) =>
                    setTopViewCamera({
                      offset: [
                        topViewCamera.offset[0],
                        v,
                        topViewCamera.offset[2],
                      ],
                    })
                  }
                />
                <Slider
                  label="Offset Z"
                  value={topViewCamera.offset[2]}
                  min={-20}
                  max={20}
                  step={0.5}
                  onChange={(v) =>
                    setTopViewCamera({
                      offset: [
                        topViewCamera.offset[0],
                        topViewCamera.offset[1],
                        v,
                      ],
                    })
                  }
                />
              </section>
            </>
          ) : null}

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Colors</h4>
            <ColorRow label="Line" value={cfg.lineColor} onChange={patch("lineColor")} />
            <ColorRow label="Tip" value={cfg.tipColor} onChange={patch("tipColor")} />
            <ColorRow label="Grid" value={cfg.gridColor} onChange={patch("gridColor")} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Opacity</h4>
            <Slider label="Line" value={cfg.lineOpacity} min={0} max={1} step={0.01} onChange={patch("lineOpacity") as (v: number) => void} />
            <Slider label="Tip" value={cfg.tipOpacity} min={0} max={1} step={0.01} onChange={patch("tipOpacity") as (v: number) => void} />
            <Slider label="Grid" value={cfg.gridOpacity} min={0} max={0.3} step={0.005} onChange={patch("gridOpacity") as (v: number) => void} />
            <Slider label="Spacing" value={cfg.gridSpacing} min={0.5} max={4} step={0.25} onChange={patch("gridSpacing") as (v: number) => void} />
          </section>

          <hr className="controls__divider" />

          <section className="controls__group">
            <h4 className="controls__group-title">Line</h4>
            <Slider label="Width" value={cfg.lineWidth} min={0.005} max={0.15} step={0.005} onChange={patch("lineWidth") as (v: number) => void} />
            <Slider label="Emission" value={cfg.lineEmission} min={0.5} max={8} step={0.1} onChange={patch("lineEmission") as (v: number) => void} />
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
            <Slider label="Radius" value={cfg.bloomRadius} min={0} max={1.5} step={0.05} onChange={patch("bloomRadius") as (v: number) => void} />
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
