import { useEffect, useState, type ReactNode } from "react";
import { FONTS, type FontSpec } from "./fonts";
import { FILL_PRESETS, FILL_USES } from "./materials";
import {
  FILLS,
  WORD_IDS,
  WORD_LABEL,
  exportSettings,
  useTextLab,
  type FillId,
  type Layout,
  type Motion,
  type TextCase,
} from "./store";

// Small hand-rolled control kit (the repo has no GUI library); styled to
// match the desk controls' cyan-on-glass look.

function Section({ title, children, open = true }: { title: string; children: ReactNode; open?: boolean }) {
  const [isOpen, setOpen] = useState(open);
  return (
    <section className={`tl-section${isOpen ? " is-open" : ""}`}>
      <button type="button" className="tl-section__head" onClick={() => setOpen(!isOpen)}>
        <span>{title}</span>
        <span className="tl-section__chev">{isOpen ? "–" : "+"}</span>
      </button>
      {isOpen && <div className="tl-section__body">{children}</div>}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="tl-row">
      <span className="tl-row__label">{label}</span>
      <span className="tl-row__control">{children}</span>
    </label>
  );
}

function Select<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: readonly (readonly [T, string])[];
  onChange: (v: T) => void;
}) {
  return (
    <select className="tl-select" value={value} onChange={(e) => onChange(e.target.value as T)}>
      {options.map(([v, label]) => (
        <option key={v} value={v}>
          {label}
        </option>
      ))}
    </select>
  );
}

function FontSelect({
  value,
  fonts,
  onChange,
  extra,
}: {
  value: string;
  fonts: FontSpec[];
  onChange: (id: string) => void;
  extra?: [string, string];
}) {
  const groups = new Map<string, FontSpec[]>();
  for (const f of fonts) groups.set(f.category, [...(groups.get(f.category) ?? []), f]);
  return (
    <select
      className="tl-select"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {extra && <option value={extra[0]}>{extra[1]}</option>}
      {[...groups].map(([cat, list]) => (
        <optgroup key={cat} label={cat}>
          {list.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

function Range({
  value,
  min,
  max,
  step,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  const digits = step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
  return (
    <>
      <input
        className="tl-range"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="tl-value">{value.toFixed(digits)}</span>
    </>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      className={`tl-toggle${value ? " is-on" : ""}`}
      aria-pressed={value}
      onClick={() => onChange(!value)}
    >
      {value ? "On" : "Off"}
    </button>
  );
}

function ColorInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <>
      <input className="tl-color" type="color" value={value} onChange={(e) => onChange(e.target.value)} />
      <span className="tl-value">{value}</span>
    </>
  );
}

const CASES: [TextCase, string][] = [
  ["as-typed", "As typed"],
  ["upper", "UPPERCASE"],
  ["lower", "lowercase"],
];

const LAYOUTS: [Layout, string][] = [
  ["stack", "Stack"],
  ["row", "Row"],
  ["grid", "2 × 2 grid"],
  ["cascade", "Cascade (depth)"],
  ["ring", "Ring (orbit to read)"],
  ["gallery", "Font gallery"],
];

const MOTIONS: [Motion, string][] = [
  ["none", "Still"],
  ["float", "Float"],
  ["sway", "Sway"],
  ["spin", "Spin"],
];

const DISPLAY = FONTS.filter((f) => !f.bodyOnly);

/** Step a native <select> to its next/previous option (wrapping) and fire React's onChange. */
function stepSelect(el: HTMLSelectElement, dir: 1 | -1) {
  const n = el.options.length;
  for (let k = 1; k <= n; k++) {
    const opt = el.options[(el.selectedIndex + dir * k + n * k) % n];
    if (opt.disabled) continue;
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!.call(el, opt.value);
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }
}

/** Move the shared font one step through the dropdown order, wrapping around. */
function stepFont(dir: 1 | -1) {
  const { font, setFont } = useTextLab.getState();
  const i = DISPLAY.findIndex((f) => f.id === font);
  setFont(DISPLAY[(i + dir + DISPLAY.length) % DISPLAY.length].id);
}
// Body menu: body faces first, then every display face for contrast tests.
const BODY_MENU = [...FONTS.filter((f) => f.bodyOnly), ...DISPLAY];

export default function TextPanel() {
  const collapsed = !useTextLab((s) => s.panelOpen);
  const [copied, setCopied] = useState(false);
  const font = useTextLab((s) => s.font);
  const target = useTextLab((s) => s.target);
  const style = useTextLab((s) => s.words[s.target === "all" ? "project" : s.target]);
  const scene = useTextLab((s) => s.scene);
  const paragraph = useTextLab((s) => s.paragraph);
  const { setFont, setTarget, setWord, setScene, setParagraph, shuffleFont, shuffleFills, resetView, reset } =
    useTextLab.getState();
  const uses = FILL_USES[style.fill];

  // Left / right arrows step whichever dropdown has focus, and flip the
  // shared font when nothing else wants the keys. Typing fields keep theirs.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      const dir = e.key === "ArrowRight" ? 1 : -1;
      const el = e.target as HTMLElement;
      if (el instanceof HTMLSelectElement) {
        e.preventDefault();
        stepSelect(el, dir);
        return;
      }
      const textInput = el instanceof HTMLInputElement && !["range", "color", "checkbox"].includes(el.type);
      if (textInput || el instanceof HTMLTextAreaElement || el.isContentEditable) return;
      e.preventDefault();
      stepFont(dir);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(exportSettings());
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      // Clipboard denied — nothing useful to do from here.
    }
  };

  return (
    <aside className={`tl-panel${collapsed ? " is-collapsed" : ""}`}>
      <header className="tl-panel__header">
        <h2 className="tl-panel__title">Text lab</h2>
        <button type="button" className="tl-btn" onClick={() => useTextLab.getState().setPanelOpen(collapsed)}>
          {collapsed ? "Open" : "Hide"}
        </button>
      </header>
      {!collapsed && (
        <div className="tl-panel__scroll">
          <div className="tl-target">
            {(["all", ...WORD_IDS] as const).map((id) => (
              <button
                key={id}
                type="button"
                className={`tl-chip${target === id ? " is-on" : ""}`}
                onClick={() => setTarget(id)}
              >
                {id === "all" ? "All" : WORD_LABEL[id]}
              </button>
            ))}
          </div>
          <p className="tl-hint">
            {target === "all" ? "Edits apply to all four words." : `Editing “${WORD_LABEL[target]}” only.`}
          </p>
          <div className="tl-actions">
            <button type="button" className="tl-btn" onClick={shuffleFont}>
              Shuffle font
            </button>
            <button type="button" className="tl-btn" onClick={shuffleFills}>
              Shuffle fills
            </button>
          </div>

          <Section title="Type">
            {target !== "all" && (
              <Row label="Text">
                <input className="tl-text" value={style.text} onChange={(e) => setWord({ text: e.target.value })} />
              </Row>
            )}
            <Row label="Font (all)">
              <button type="button" className="tl-step" aria-label="Previous font" onClick={() => stepFont(-1)}>
                ‹
              </button>
              <FontSelect value={font} fonts={DISPLAY} onChange={setFont} />
              <button type="button" className="tl-step" aria-label="Next font" onClick={() => stepFont(1)}>
                ›
              </button>
            </Row>
            <Row label="Case">
              <Select value={style.textCase} options={CASES} onChange={(textCase) => setWord({ textCase })} />
            </Row>
            <Row label="Size">
              <Range value={style.size} min={0.3} max={2.5} step={0.05} onChange={(size) => setWord({ size })} />
            </Row>
            <Row label="Tracking">
              <Range
                value={style.letterSpacing}
                min={-0.1}
                max={0.6}
                step={0.01}
                onChange={(letterSpacing) => setWord({ letterSpacing })}
              />
            </Row>
            <Row label="Weight">
              <Range value={style.weight} min={-0.04} max={0.14} step={0.005} onChange={(weight) => setWord({ weight })} />
            </Row>
            <Row label="Depth (3D)">
              <Range value={style.depth} min={0.01} max={1.5} step={0.01} onChange={(depth) => setWord({ depth })} />
            </Row>
          </Section>

          <Section title="Fill">
            <Row label="Fill">
              <Select
                value={style.fill}
                options={FILLS}
                onChange={(fill: FillId) => setWord({ fill, ...FILL_PRESETS[fill] })}
              />
            </Row>
            <Row label="Face">
              <ColorInput value={style.faceColor} onChange={(faceColor) => setWord({ faceColor })} />
            </Row>
            <Row label="Sides">
              <ColorInput value={style.sideColor} onChange={(sideColor) => setWord({ sideColor })} />
            </Row>
            {uses.accent && (
              <Row label={uses.accent}>
                <ColorInput value={style.accentColor} onChange={(accentColor) => setWord({ accentColor })} />
              </Row>
            )}
            <Row label="Glow">
              <Range value={style.glow} min={0.2} max={8} step={0.1} onChange={(glow) => setWord({ glow })} />
            </Row>
            {uses.fx && (
              <>
                <Row label="Pattern scale">
                  <Range value={style.fxScale} min={0.2} max={4} step={0.05} onChange={(fxScale) => setWord({ fxScale })} />
                </Row>
                <Row label="Anim speed">
                  <Range value={style.fxSpeed} min={0} max={4} step={0.05} onChange={(fxSpeed) => setWord({ fxSpeed })} />
                </Row>
              </>
            )}
            {uses.tron && (
              <>
                <Row label="Fill letters">
                  <Toggle value={style.bodyFill} onChange={(bodyFill) => setWord({ bodyFill })} />
                </Row>
                {style.bodyFill && (
                  <>
                <Row label="Fill color">
                  <ColorInput value={style.bodyColor} onChange={(bodyColor) => setWord({ bodyColor })} />
                </Row>
                <Row label="Fill opacity">
                  <Range
                    value={style.bodyOpacity}
                    min={0}
                    max={1}
                    step={0.05}
                    onChange={(bodyOpacity) => setWord({ bodyOpacity })}
                  />
                </Row>
                  </>
                )}
              </>
            )}
            {!uses.tron && (
              <Row label="Edge lines">
                <Toggle value={style.edges} onChange={(edges) => setWord({ edges })} />
              </Row>
            )}
            {!uses.tron && style.edges && (
              <Row label="Edge color">
                <ColorInput value={style.edgeColor} onChange={(edgeColor) => setWord({ edgeColor })} />
              </Row>
            )}
            {(uses.tron || style.edges) && (
              <Row label="Line width">
                <Range value={style.lineWidth} min={0.5} max={12} step={0.1} onChange={(lineWidth) => setWord({ lineWidth })} />
              </Row>
            )}
          </Section>

          <Section title="Bevel" open={false}>
            <Row label="Bevel">
              <Toggle value={style.bevel} onChange={(bevel) => setWord({ bevel })} />
            </Row>
            {style.bevel && (
              <>
                <Row label="Thickness">
                  <Range
                    value={style.bevelThickness}
                    min={0}
                    max={0.2}
                    step={0.005}
                    onChange={(bevelThickness) => setWord({ bevelThickness })}
                  />
                </Row>
                <Row label="Size">
                  <Range value={style.bevelSize} min={0} max={0.1} step={0.005} onChange={(bevelSize) => setWord({ bevelSize })} />
                </Row>
                <Row label="Segments">
                  <Range
                    value={style.bevelSegments}
                    min={1}
                    max={10}
                    step={1}
                    onChange={(bevelSegments) => setWord({ bevelSegments })}
                  />
                </Row>
              </>
            )}
            <Row label="Curve detail">
              <Range
                value={style.curveSegments}
                min={1}
                max={24}
                step={1}
                onChange={(curveSegments) => setWord({ curveSegments })}
              />
            </Row>
          </Section>

          <Section title="Layout & motion">
            <Row label="Layout">
              <Select value={scene.layout} options={LAYOUTS} onChange={(layout) => setScene({ layout })} />
            </Row>
            {(scene.layout === "stack" || scene.layout === "grid" || scene.layout === "cascade") && (
              <Row label="Align">
                <Select
                  value={scene.align}
                  options={[
                    ["left", "Left"],
                    ["center", "Center"],
                    ["right", "Right"],
                  ]}
                  onChange={(align) => setScene({ align })}
                />
              </Row>
            )}
            <Row label="Gap">
              <Range value={scene.gap} min={0} max={2} step={0.05} onChange={(gap) => setScene({ gap })} />
            </Row>
            <Row label="Idle motion">
              <Select value={scene.motion} options={MOTIONS} onChange={(motion) => setScene({ motion })} />
            </Row>
            <Row label="Motion speed">
              <Range value={scene.motionSpeed} min={0.1} max={3} step={0.05} onChange={(motionSpeed) => setScene({ motionSpeed })} />
            </Row>
            <Row label="Orbit spin">
              <Toggle value={scene.autoRotate} onChange={(autoRotate) => setScene({ autoRotate })} />
            </Row>
            {scene.autoRotate && (
              <Row label="Orbit speed">
                <Range
                  value={scene.autoRotateSpeed}
                  min={-6}
                  max={6}
                  step={0.1}
                  onChange={(autoRotateSpeed) => setScene({ autoRotateSpeed })}
                />
              </Row>
            )}
            <Row label="View">
              <button type="button" className="tl-btn" onClick={resetView}>
                Reset view
              </button>
            </Row>
          </Section>

          <Section title="Bloom" open={false}>
            <Row label="Bloom">
              <Range value={scene.bloom} min={0} max={3} step={0.05} onChange={(bloom) => setScene({ bloom })} />
            </Row>
            <Row label="Bloom cutoff">
              <Range
                value={scene.bloomThreshold}
                min={0}
                max={1.5}
                step={0.01}
                onChange={(bloomThreshold) => setScene({ bloomThreshold })}
              />
            </Row>
          </Section>

          <Section title="Paragraph text">
            <Row label="Heading size">
              <Range
                value={paragraph.headingSize}
                min={18}
                max={96}
                step={1}
                onChange={(headingSize) => setParagraph({ headingSize })}
              />
            </Row>
            <Row label="Heading case">
              <Select value={paragraph.headingCase} options={CASES} onChange={(headingCase) => setParagraph({ headingCase })} />
            </Row>
            <Row label="Heading color">
              <ColorInput value={paragraph.headingColor} onChange={(headingColor) => setParagraph({ headingColor })} />
            </Row>
            <Row label="Body font">
              <FontSelect
                value={paragraph.bodyFont}
                fonts={BODY_MENU}
                extra={["match", "Same as titles"]}
                onChange={(bodyFont) => setParagraph({ bodyFont })}
              />
            </Row>
            <Row label="Body size">
              <Range value={paragraph.size} min={12} max={28} step={1} onChange={(size) => setParagraph({ size })} />
            </Row>
            <Row label="Line height">
              <Range
                value={paragraph.lineHeight}
                min={1}
                max={2.4}
                step={0.05}
                onChange={(lineHeight) => setParagraph({ lineHeight })}
              />
            </Row>
            <Row label="Tracking">
              <Range value={paragraph.tracking} min={-0.05} max={0.2} step={0.01} onChange={(tracking) => setParagraph({ tracking })} />
            </Row>
            <Row label="Body color">
              <ColorInput value={paragraph.color} onChange={(color) => setParagraph({ color })} />
            </Row>
            <Row label="Measure (ch)">
              <Range value={paragraph.measure} min={30} max={110} step={1} onChange={(measure) => setParagraph({ measure })} />
            </Row>
            <Row label="Align">
              <Select
                value={paragraph.align}
                options={[
                  ["left", "Left"],
                  ["center", "Center"],
                  ["justify", "Justify"],
                ]}
                onChange={(align) => setParagraph({ align })}
              />
            </Row>
          </Section>

          <div className="tl-actions">
            <button type="button" className="tl-btn" onClick={copy}>
              {copied ? "Copied" : "Copy settings JSON"}
            </button>
            <button type="button" className="tl-btn" onClick={reset}>
              Reset all
            </button>
          </div>
          <p className="tl-hint">
            Drag to rotate · right-drag or shift-drag to pan · wheel / pinch to zoom · ← → steps a focused dropdown (or the font).
            {scene.layout === "gallery" && " Click a tile to use that font."}
          </p>
        </div>
      )}
    </aside>
  );
}
