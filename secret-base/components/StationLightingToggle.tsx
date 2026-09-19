import { useStationLightingMode } from "./scene/stationLightingMode";
import "./station-lighting-toggle.css";

export function StationLightingToggle() {
  const { mode, setMode } = useStationLightingMode();
  return (
    <div className="station-lighting-toggle" role="group" aria-label="Compare lighting">
      <span>Lighting</span>
      {(["original", "optimized"] as const).map((option) => (
        <button key={option} type="button" aria-pressed={mode === option}
          onClick={() => setMode(option)}>
          {option === "original" ? "Original" : "Optimized"}
        </button>
      ))}
    </div>
  );
}
