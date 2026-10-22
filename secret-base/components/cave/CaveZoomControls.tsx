import { useEffect, useRef, useState } from "react";
import { useCaveZoom, type Tuning } from "./caveZoom";

const SAVE_ROUTE = "/__save-cave-zoom";

type Slider = { key: keyof Tuning; label: string; min: number; max: number; step: number; format: (v: number) => string };

const degrees = (v: number) => `${v.toFixed(1)}°`;
const pan = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(3)}`;

/**
 * Dev only: once the camera rests on a platform, sliders move its final
 * camera live. Orbits (the side platforms) turn round the platform, tilt
 * and move in or out; the crop (Projects) zooms. Both pan the frame. Every
 * change is saved to zoomLayout.json, which the cave ships with.
 */
export function CaveZoomControls() {
  const shot = useCaveZoom((s) => s.shot);
  const tune = useCaveZoom((s) => s.tune);
  const loadTunings = useCaveZoom((s) => s.loadTunings);
  const [status, setStatus] = useState("");
  const saveTimer = useRef(0);

  // The JSON on disk may be newer than this bundle (Vite does not reload on save).
  useEffect(() => {
    let live = true;
    fetch(SAVE_ROUTE)
      .then((response) => (response.ok ? response.json() : null))
      .then((saved: Record<string, Tuning> | null) => {
        if (live && saved) loadTunings(saved);
      })
      .catch(() => {});
    return () => { live = false; };
  }, [loadTunings]);

  if (!shot) return null;

  const save = () => {
    setStatus("saving…");
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      const body = JSON.stringify(useCaveZoom.getState().tunings, (_, v) => (typeof v === "number" ? Math.round(v * 1000) / 1000 : v), 2);
      try {
        const response = await fetch(SAVE_ROUTE, { method: "POST", headers: { "Content-Type": "application/json" }, body });
        setStatus(response.ok ? "saved" : "save failed");
      } catch {
        setStatus("save failed");
      }
    }, 300);
  };

  const change = (patch: Tuning | null) => {
    tune(shot.platform, patch);
    save();
  };

  const { auto } = shot;
  const sliders: Slider[] =
    shot.kind === "orbit"
      ? [
          { key: "facing", label: "Turn", min: auto.facing - 120, max: auto.facing + 120, step: 0.5, format: degrees },
          { key: "elevation", label: "Height", min: -10, max: 80, step: 0.5, format: degrees },
          { key: "distance", label: "Distance", min: auto.distance * 0.3, max: auto.distance * 2.5, step: 0.05, format: (v) => `${v.toFixed(2)} m` },
          { key: "panX", label: "Pan ↔", min: -0.5, max: 0.5, step: 0.005, format: pan },
          { key: "panY", label: "Pan ↕", min: -0.5, max: 0.5, step: 0.005, format: pan },
        ]
      : [
          { key: "zoom", label: "Zoom", min: 1.05, max: 6, step: 0.01, format: (v) => `${v.toFixed(2)}×` },
          { key: "panX", label: "Pan ↔", min: -0.5, max: 0.5, step: 0.005, format: pan },
          { key: "panY", label: "Pan ↕", min: -0.5, max: 0.5, step: 0.005, format: pan },
        ];

  return (
    <div
      style={{
        position: "absolute",
        right: 16,
        top: 16,
        zIndex: 200,
        display: "grid",
        gridTemplateColumns: "auto 180px 64px",
        alignItems: "center",
        gap: "8px 10px",
        padding: "12px 14px",
        borderRadius: 8,
        background: "rgba(5, 12, 16, 0.78)",
        border: "1px solid rgba(156, 248, 248, 0.25)",
        color: "rgba(174, 234, 238, 0.85)",
        font: "11px ui-monospace, 'SF Mono', Menlo, monospace",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
      }}
    >
      <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "space-between", gap: 12, opacity: 0.9 }}>
        <span>{shot.platform} camera</span>
        <span style={{ opacity: 0.6 }}>{status}</span>
      </div>
      {sliders.map(({ key, label, min, max, step, format }) => {
        const value = shot.value[key];
        return (
          <label key={key} style={{ display: "contents" }}>
            <span>{label}</span>
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => change({ [key]: Number(e.target.value) })}
              style={{ width: "100%", accentColor: "#9cf8f8" }}
            />
            <span style={{ textAlign: "right", textTransform: "none" }}>{format(value)}</span>
          </label>
        );
      })}
      <button
        type="button"
        onClick={() => change(null)}
        style={{
          gridColumn: "1 / -1",
          justifySelf: "end",
          padding: "5px 10px",
          borderRadius: 6,
          background: "transparent",
          border: "1px solid rgba(156, 248, 248, 0.3)",
          color: "inherit",
          font: "inherit",
          letterSpacing: "inherit",
          textTransform: "inherit",
          cursor: "pointer",
        }}
      >
        Reset to auto
      </button>
    </div>
  );
}
