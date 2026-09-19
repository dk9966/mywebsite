import { STATION_FONTS, STATION_STYLES, useStationFont } from "./scene/stationFonts";
import "./station-font-picker.css";

export function StationFontPicker() {
  const { index, styleIndex, cycleFont, cycleStyle } = useStationFont();
  const font = STATION_FONTS[index];
  return (
    <aside className="station-font-picker" aria-label="Projects heading font">
      <span className="station-font-label">Heading font</span>
      <div className="station-picker-row">
        <button type="button" onClick={() => cycleFont(-1)} aria-label="Previous font">←</button>
        <span className="station-picker-value" aria-live="polite">{font.name}<span className="station-font-count">{index + 1} / {STATION_FONTS.length}</span></span>
        <button type="button" onClick={() => cycleFont(1)} aria-label="Next font">→</button>
      </div>
      <span className="station-font-vibe">{font.vibe}</span>
      <span className="station-font-label station-style-label">Text style</span>
      <div className="station-picker-row">
        <button type="button" onClick={() => cycleStyle(-1)} aria-label="Previous text style">←</button>
        <span className="station-picker-value" aria-live="polite">{STATION_STYLES[styleIndex]}<span className="station-font-count">{styleIndex + 1} / {STATION_STYLES.length}</span></span>
        <button type="button" onClick={() => cycleStyle(1)} aria-label="Next text style">→</button>
      </div>
    </aside>
  );
}
