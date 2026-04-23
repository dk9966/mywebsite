import { StrictMode, useState, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import DrainText from "../src/components/DrainText";

const FONT_OPTIONS: { label: string; url: string }[] = [
  { label: "JetBrains Mono Thin", url: "/fonts/JetBrainsMono-Thin.ttf" },
  { label: "JetBrains Mono", url: "/fonts/JetBrainsMono-Regular.ttf" },
  { label: "VT323", url: "/fonts/VT323-Regular.ttf" },
];

/** Sample string: multiple glyphs and a second line for layout coverage. */
const SAMPLE_TEXT = "DRAIN\nTYPE";

export function DrainExampleApp(): ReactElement {
  const [fontUrl, setFontUrl] = useState(FONT_OPTIONS[0].url);

  return (
    <>
      <div className="drain-example__toolbar">
        <span className="drain-example__label">Font</span>
        <div className="drain-example__font-switch" role="group" aria-label="Font">
          {FONT_OPTIONS.map((opt) => (
            <button
              key={opt.url}
              type="button"
              className={
                "drain-example__font-btn" +
                (opt.url === fontUrl ? " drain-example__font-btn--active" : "")
              }
              onClick={() => setFontUrl(opt.url)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="drain-example__stage">
        <DrainText key={fontUrl} text={SAMPLE_TEXT} fontUrl={fontUrl} />
      </div>
    </>
  );
}

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(
    <StrictMode>
      <DrainExampleApp />
    </StrictMode>,
  );
}
