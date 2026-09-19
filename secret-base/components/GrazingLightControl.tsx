import { GRAZING_DEFAULT, GRAZING_MAX, useGrazingLight } from "./scene/grazingLightStore";
import "./grazing-light-control.css";

export function GrazingLightControl() {
  const { strength, setStrength } = useGrazingLight();
  return (
    <aside className="grazing-light-control" aria-label="Pillar lighting">
      <div className="grazing-light-label">
        <label htmlFor="grazing-strength">Pillar grazing light</label>
        <output htmlFor="grazing-strength">{strength.toFixed(1)}×</output>
      </div>
      <input id="grazing-strength" type="range" min={0} max={GRAZING_MAX} step={0.1}
        value={strength} aria-valuetext={`${strength.toFixed(1)} times original strength`}
        onChange={(event) => setStrength(Number(event.target.value))} />
      <div className="grazing-light-footer">
        <span>0× – {GRAZING_MAX}×</span>
        <button type="button" onClick={() => setStrength(GRAZING_DEFAULT)}>Reset to {GRAZING_DEFAULT}×</button>
      </div>
    </aside>
  );
}
