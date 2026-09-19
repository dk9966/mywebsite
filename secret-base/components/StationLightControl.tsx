import { useStationLightColor } from "./scene/stationLightColor";
import "./grazing-light-control.css";

export function StationLightControl() {
  const { hue, tint, change } = useStationLightColor();
  return (
    <aside className="grazing-light-control" aria-label="Station blue lighting">
      <div className="grazing-light-label">
        <label htmlFor="station-light-hue">Light blue</label>
        <output htmlFor="station-light-hue">{hue}%</output>
      </div>
      <input id="station-light-hue" type="range" min={0} max={100} step={1} value={hue}
        aria-valuetext={`${hue} percent blue; deck huge trim blue at 50 percent`}
        onChange={(event) => change("hue", Number(event.target.value))} />
      <div className="grazing-light-footer"><span>Pale cyan</span><span>Deck blue · 50</span><span>Deep blue</span></div>
      <div className="grazing-light-label" style={{ marginTop: 18 }}>
        <label htmlFor="station-light-tint">Blue tint</label>
        <output htmlFor="station-light-tint">{tint > 0 ? "+" : ""}{tint}%</output>
      </div>
      <input id="station-light-tint" type="range" min={-100} max={100} step={1} value={tint}
        aria-valuetext={tint < 0 ? `${-tint} percent paler` : `${tint} percent richer blue`}
        onChange={(event) => change("tint", Number(event.target.value))} />
      <div className="grazing-light-footer"><span>Icy white</span><span>Neutral · 0</span><span>Rich blue</span></div>
      <div className="grazing-light-footer" style={{ marginTop: 12 }}>
        <span>Lanterns stay warm</span>
        <button type="button" onClick={() => { change("hue", 50); change("tint", 0); }}>Deck blue</button>
      </div>
    </aside>
  );
}
