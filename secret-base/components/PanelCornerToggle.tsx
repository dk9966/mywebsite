import { usePanelBorder, usePanelCorners } from "./scene/panelCornerStore";
import "./panel-corner-toggle.css";

export function PanelCornerToggle() {
  const { square, toggle } = usePanelCorners();
  const { thickness, setThickness } = usePanelBorder();
  return (
    <aside className="panel-shape-controls" aria-label="Screen borders">
    <button className="panel-corner-toggle" type="button" aria-label={`Panel corners: ${square ? "Unbeveled" : "Beveled"}. Switch to ${square ? "beveled" : "unbeveled"}`} aria-pressed={!square} onClick={toggle}>
      Panel corners <span>{square ? "Unbeveled" : "Beveled"}</span>
    </button>
      <div className="panel-border-label">
        <label htmlFor="panel-border-thickness">Border thickness</label>
        <output htmlFor="panel-border-thickness">{thickness.toFixed(2)}×</output>
      </div>
      <input id="panel-border-thickness" type="range" min={0.01} max={2} step={0.01}
        value={thickness} aria-valuetext={`${thickness.toFixed(2)} times original thickness`}
        onChange={(event) => setThickness(Number(event.target.value))} />
    </aside>
  );
}
