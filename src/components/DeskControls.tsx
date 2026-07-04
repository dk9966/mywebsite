import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import {
  BOOT_TOTAL_MS,
  BOOT_PARTS,
  BOOT_PANEL_LABELS,
  type BootPanelId,
  type BootPartId,
} from "../lib/bootParts";
import { useBootClock } from "../stores/bootClock";
import { useBootTuning } from "../stores/bootTuning";
import {
  useDeskLayout,
  MAX_HEADER_FONT_PX,
  MAX_TIMELINE_FONT_PX,
  MAX_TYPE_EM,
  MIN_CONTACT_HEIGHT_PX,
  MAX_CONTACT_HEIGHT_PX,
  MIN_COL_FRAC,
  MAX_COL_FRAC,
  MIN_PANEL_SPLIT,
  MAX_PANEL_SPLIT,
} from "../stores/deskLayout";
import "./DeskControls.css";

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  decimals?: number;
  onChange: (v: number) => void;
}

function Slider({ label, value, min, max, step, decimals = 0, onChange }: SliderProps) {
  const stopBubble = (e: React.PointerEvent) => e.stopPropagation();

  return (
    <div className="desk-controls__field">
      <span className="desk-controls__label">{label}</span>
      <input
        className="desk-controls__slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        onPointerDown={stopBubble}
        onPointerMove={stopBubble}
        onPointerUp={stopBubble}
      />
      <span className="desk-controls__value">{value.toFixed(decimals)}</span>
    </div>
  );
}

function formatBootMs(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

interface BootPartRowProps {
  index: number;
  id: BootPartId;
  label: string;
  scope: "panel" | "global";
  showCheckbox: boolean;
  visible: boolean;
  delayMs: number;
  durationMs: number;
  onVisible: (v: boolean) => void;
  onDelay: (v: number) => void;
  onDuration: (v: number) => void;
}

function BootPartRow({
  index,
  label,
  scope,
  showCheckbox,
  visible,
  delayMs,
  durationMs,
  onVisible,
  onDelay,
  onDuration,
}: BootPartRowProps) {
  const stopBubble = (e: ReactPointerEvent) => e.stopPropagation();
  const delayLabel = scope === "global" ? "Start ms" : "Delay ms";

  return (
    <div className="desk-controls__boot-part">
      {showCheckbox ? (
        <label className="desk-controls__checkbox-field">
          <input
            className="desk-controls__checkbox"
            type="checkbox"
            checked={visible}
            onChange={(e) => onVisible(e.target.checked)}
            onPointerDown={stopBubble}
          />
          <span className="desk-controls__checkbox-label">
            {index}. {label}
          </span>
        </label>
      ) : (
        <span className="desk-controls__boot-part-title">
          {index}. {label}
        </span>
      )}
      <Slider
        label={delayLabel}
        value={delayMs}
        min={0}
        max={BOOT_TOTAL_MS}
        step={10}
        onChange={onDelay}
      />
      <Slider
        label="Duration"
        value={durationMs}
        min={1}
        max={2000}
        step={10}
        onChange={onDuration}
      />
    </div>
  );
}

const DRAG_BLOCK =
  "input, button, label, textarea, select, option, a, .desk-controls__slider";

function isPanelDragTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return !target.closest(DRAG_BLOCK);
}

export default function DeskControls() {
  const camera = useDeskLayout((s) => s.camera);
  const setCamera = useDeskLayout((s) => s.setCamera);
  const lookAt = useDeskLayout((s) => s.lookAt);
  const setLookAt = useDeskLayout((s) => s.setLookAt);
  const wallAnchor = useDeskLayout((s) => s.wallAnchor);
  const setWallAnchor = useDeskLayout((s) => s.setWallAnchor);
  const wallWidthPx = useDeskLayout((s) => s.wallWidthPx);
  const setWallWidthPx = useDeskLayout((s) => s.setWallWidthPx);
  const wallHeightPx = useDeskLayout((s) => s.wallHeightPx);
  const setWallHeightPx = useDeskLayout((s) => s.setWallHeightPx);
  const curveRadiusPx = useDeskLayout((s) => s.curveRadiusPx);
  const setCurveRadiusPx = useDeskLayout((s) => s.setCurveRadiusPx);
  const bgOpacity = useDeskLayout((s) => s.bgOpacity);
  const setBgOpacity = useDeskLayout((s) => s.setBgOpacity);
  const bgBlur = useDeskLayout((s) => s.bgBlur);
  const setBgBlur = useDeskLayout((s) => s.setBgBlur);
  const bezelEmission = useDeskLayout((s) => s.bezelEmission);
  const setBezelEmission = useDeskLayout((s) => s.setBezelEmission);
  const bezelLineWidth = useDeskLayout((s) => s.bezelLineWidth);
  const setBezelLineWidth = useDeskLayout((s) => s.setBezelLineWidth);
  const bezelOpacity = useDeskLayout((s) => s.bezelOpacity);
  const setBezelOpacity = useDeskLayout((s) => s.setBezelOpacity);
  const bloomIntensity = useDeskLayout((s) => s.bloomIntensity);
  const setBloomIntensity = useDeskLayout((s) => s.setBloomIntensity);
  const bloomThreshold = useDeskLayout((s) => s.bloomThreshold);
  const setBloomThreshold = useDeskLayout((s) => s.setBloomThreshold);
  const bloomRadius = useDeskLayout((s) => s.bloomRadius);
  const setBloomRadius = useDeskLayout((s) => s.setBloomRadius);
  const bloomSmoothing = useDeskLayout((s) => s.bloomSmoothing);
  const setBloomSmoothing = useDeskLayout((s) => s.setBloomSmoothing);
  const headerFontPx = useDeskLayout((s) => s.headerFontPx);
  const setHeaderFontPx = useDeskLayout((s) => s.setHeaderFontPx);
  const contentPaddingPx = useDeskLayout((s) => s.contentPaddingPx);
  const setContentPaddingPx = useDeskLayout((s) => s.setContentPaddingPx);
  const contactHeightPx = useDeskLayout((s) => s.contactHeightPx);
  const setContactHeightPx = useDeskLayout((s) => s.setContactHeightPx);
  const contactIconSizePx = useDeskLayout((s) => s.contactIconSizePx);
  const setContactIconSizePx = useDeskLayout((s) => s.setContactIconSizePx);
  const eduBaseFontPx = useDeskLayout((s) => s.eduBaseFontPx);
  const setEduBaseFontPx = useDeskLayout((s) => s.setEduBaseFontPx);
  const eduDegreeEm = useDeskLayout((s) => s.eduDegreeEm);
  const setEduDegreeEm = useDeskLayout((s) => s.setEduDegreeEm);
  const eduDateEm = useDeskLayout((s) => s.eduDateEm);
  const setEduDateEm = useDeskLayout((s) => s.setEduDateEm);
  const eduSchoolEm = useDeskLayout((s) => s.eduSchoolEm);
  const setEduSchoolEm = useDeskLayout((s) => s.setEduSchoolEm);
  const expBaseFontPx = useDeskLayout((s) => s.expBaseFontPx);
  const setExpBaseFontPx = useDeskLayout((s) => s.setExpBaseFontPx);
  const expRoleEm = useDeskLayout((s) => s.expRoleEm);
  const setExpRoleEm = useDeskLayout((s) => s.setExpRoleEm);
  const expDateEm = useDeskLayout((s) => s.expDateEm);
  const setExpDateEm = useDeskLayout((s) => s.setExpDateEm);
  const expOrgEm = useDeskLayout((s) => s.expOrgEm);
  const setExpOrgEm = useDeskLayout((s) => s.setExpOrgEm);
  const colFrac = useDeskLayout((s) => s.colFrac);
  const setColFrac = useDeskLayout((s) => s.setColFrac);
  const rightSplit = useDeskLayout((s) => s.rightSplit);
  const setRightSplit = useDeskLayout((s) => s.setRightSplit);
  const reset = useDeskLayout((s) => s.reset);
  const saveAsDefault = useDeskLayout((s) => s.saveAsDefault);

  const bootElapsedMs = useBootClock((s) => s.elapsedMs);
  const bootPaused = useBootClock((s) => s.paused);
  const bootSeek = useBootClock((s) => s.seek);
  const bootRestart = useBootClock((s) => s.restart);
  const bootTogglePause = useBootClock((s) => s.togglePause);
  const setBootScrubbing = useBootClock((s) => s.setScrubbing);

  const bootParts = useBootTuning((s) => s.parts);
  const panelStartMs = useBootTuning((s) => s.panelStartMs);
  const stabilizeMs = useBootTuning((s) => s.stabilizeMs);
  const pulseBaseMs = useBootTuning((s) => s.pulseBaseMs);
  const pulseSweepMs = useBootTuning((s) => s.pulseSweepMs);
  const setPartVisible = useBootTuning((s) => s.setPartVisible);
  const setAllPartsVisible = useBootTuning((s) => s.setAllPartsVisible);
  const setPartDelay = useBootTuning((s) => s.setPartDelay);
  const setPartDuration = useBootTuning((s) => s.setPartDuration);
  const setPanelStart = useBootTuning((s) => s.setPanelStart);
  const setStabilizeMs = useBootTuning((s) => s.setStabilizeMs);
  const setPulseBaseMs = useBootTuning((s) => s.setPulseBaseMs);
  const setPulseSweepMs = useBootTuning((s) => s.setPulseSweepMs);
  const resetBootTuning = useBootTuning((s) => s.reset);

  const [minimized, setMinimized] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const [pos, setPos] = useState({ x: 12, y: 12 });
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const panelRef = useRef<HTMLElement>(null);

  const stopBubble = (e: ReactPointerEvent) => e.stopPropagation();

  const onPanelPointerDown = (e: ReactPointerEvent<HTMLElement>) => {
    stopBubble(e);
    if (e.button !== 0 || !isPanelDragTarget(e.target)) return;

    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      originX: pos.x,
      originY: pos.y,
    };
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onPanelPointerMove = (e: ReactPointerEvent<HTMLElement>) => {
    stopBubble(e);
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;

    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    const panel = panelRef.current;
    const maxX = panel
      ? Math.max(0, window.innerWidth - panel.offsetWidth)
      : window.innerWidth;
    const maxY = panel
      ? Math.max(0, window.innerHeight - panel.offsetHeight)
      : window.innerHeight;

    setPos({
      x: Math.max(0, Math.min(maxX, drag.originX + dx)),
      y: Math.max(0, Math.min(maxY, drag.originY + dy)),
    });
  };

  const endPanelDrag = (e: ReactPointerEvent<HTMLElement>) => {
    stopBubble(e);
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Pointer may already be released.
    }
  };

  const onSaveAsDefault = () => {
    saveAsDefault();
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1400);
  };

  return (
    <aside
      ref={panelRef}
      className={[
        "desk-controls",
        minimized ? "desk-controls--minimized" : "",
        dragging ? "desk-controls--dragging" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ left: pos.x, top: pos.y }}
      onPointerDown={onPanelPointerDown}
      onPointerMove={onPanelPointerMove}
      onPointerUp={endPanelDrag}
      onPointerCancel={endPanelDrag}
    >
      <div className="desk-controls__header">
        <h3 className="desk-controls__title">HUD Tuning</h3>
        <button
          className="desk-controls__btn"
          type="button"
          onClick={() => setMinimized(!minimized)}
          title={minimized ? "Expand" : "Minimize"}
        >
          {minimized ? "+" : "-"}
        </button>
      </div>

      {!minimized && (
        <>
          <section className="desk-controls__group desk-controls__playback">
            <h4 className="desk-controls__group-title">Boot sequence</h4>
            <div className="desk-controls__playback-row">
              <button
                className="desk-controls__btn"
                type="button"
                onClick={bootRestart}
                title="Restart boot"
              >
                {"<<"}
              </button>
              <button
                className="desk-controls__btn"
                type="button"
                onClick={bootTogglePause}
                title={bootPaused ? "Play" : "Pause"}
              >
                {bootPaused ? ">" : "||"}
              </button>
              <span className="desk-controls__time">
                {formatBootMs(bootElapsedMs)} / {formatBootMs(BOOT_TOTAL_MS)}
              </span>
            </div>
            <input
              className="desk-controls__slider desk-controls__slider--time"
              type="range"
              min={0}
              max={BOOT_TOTAL_MS}
              step={10}
              value={Math.min(bootElapsedMs, BOOT_TOTAL_MS)}
              onPointerDown={() => setBootScrubbing(true)}
              onPointerUp={() => setBootScrubbing(false)}
              onChange={(e) => bootSeek(Number(e.target.value))}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Panel power-on</h4>
            {(Object.keys(BOOT_PANEL_LABELS) as BootPanelId[]).map((id) => (
              <Slider
                key={id}
                label={BOOT_PANEL_LABELS[id]}
                value={panelStartMs[id]}
                min={0}
                max={2000}
                step={10}
                onChange={(v) => setPanelStart(id, v)}
              />
            ))}
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Global sync</h4>
            <Slider
              label="Stabilize"
              value={stabilizeMs}
              min={1500}
              max={BOOT_TOTAL_MS}
              step={10}
              onChange={setStabilizeMs}
            />
            <Slider
              label="Pulse base"
              value={pulseBaseMs}
              min={2000}
              max={BOOT_TOTAL_MS}
              step={10}
              onChange={setPulseBaseMs}
            />
            <Slider
              label="Pulse sweep"
              value={pulseSweepMs}
              min={0}
              max={800}
              step={10}
              onChange={setPulseSweepMs}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Boot stages</h4>
            <div className="desk-controls__boot-stage-actions">
              <button
                className="desk-controls__btn"
                type="button"
                onClick={() => setAllPartsVisible(true)}
              >
                Select all
              </button>
              <button
                className="desk-controls__btn"
                type="button"
                onClick={() => setAllPartsVisible(false)}
              >
                Deselect all
              </button>
            </div>
            {BOOT_PARTS.map((def, i) => (
              <BootPartRow
                key={def.id}
                index={i + 1}
                id={def.id}
                label={def.label}
                scope={def.scope}
                showCheckbox={!def.hideCheckbox}
                visible={bootParts[def.id].visible}
                delayMs={bootParts[def.id].delayMs}
                durationMs={bootParts[def.id].durationMs}
                onVisible={(v) => setPartVisible(def.id, v)}
                onDelay={(v) => setPartDelay(def.id, v)}
                onDuration={(v) => setPartDuration(def.id, v)}
              />
            ))}
            <button
              className="desk-controls__reset"
              type="button"
              onClick={resetBootTuning}
            >
              Reset boot timing
            </button>
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Camera</h4>
            <Slider label="Pos X" value={camera.x} min={-4} max={4} step={0.05} decimals={2} onChange={(v) => setCamera({ x: v })} />
            <Slider label="Pos Y" value={camera.y} min={0} max={4} step={0.05} decimals={2} onChange={(v) => setCamera({ y: v })} />
            <Slider label="Pos Z" value={camera.z} min={-2} max={5} step={0.05} decimals={2} onChange={(v) => setCamera({ z: v })} />
            <Slider label="FOV" value={camera.fov} min={25} max={90} step={1} onChange={(v) => setCamera({ fov: v })} />
            <Slider label="Look X" value={lookAt.x} min={-4} max={4} step={0.05} decimals={2} onChange={(v) => setLookAt({ x: v })} />
            <Slider label="Look Y" value={lookAt.y} min={0} max={4} step={0.05} decimals={2} onChange={(v) => setLookAt({ y: v })} />
            <Slider label="Look Z" value={lookAt.z} min={-4} max={4} step={0.05} decimals={2} onChange={(v) => setLookAt({ z: v })} />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Panels</h4>
            <Slider label="Wall X" value={wallAnchor.x} min={-4} max={4} step={0.05} decimals={2} onChange={(v) => setWallAnchor({ x: v })} />
            <Slider label="Wall Y" value={wallAnchor.y} min={0} max={4} step={0.05} decimals={2} onChange={(v) => setWallAnchor({ y: v })} />
            <Slider label="Wall Z" value={wallAnchor.z} min={-4} max={4} step={0.05} decimals={2} onChange={(v) => setWallAnchor({ z: v })} />
            <Slider label="Wall W" value={wallWidthPx} min={800} max={2400} step={10} onChange={setWallWidthPx} />
            <Slider label="Wall H" value={wallHeightPx} min={300} max={1800} step={10} onChange={setWallHeightPx} />
            <Slider label="Curvature" value={curveRadiusPx} min={500} max={1500} step={5} onChange={setCurveRadiusPx} />
            <Slider
              label="Profile W"
              value={colFrac[0]}
              min={MIN_COL_FRAC}
              max={MAX_COL_FRAC}
              step={0.01}
              decimals={2}
              onChange={(v) => setColFrac(0, v)}
            />
            <Slider
              label="Projects W"
              value={colFrac[1]}
              min={MIN_COL_FRAC}
              max={MAX_COL_FRAC}
              step={0.01}
              decimals={2}
              onChange={(v) => setColFrac(1, v)}
            />
            <Slider
              label="Right W"
              value={colFrac[2]}
              min={MIN_COL_FRAC}
              max={MAX_COL_FRAC}
              step={0.01}
              decimals={2}
              onChange={(v) => setColFrac(2, v)}
            />
            <Slider label="Header" value={headerFontPx} min={9} max={MAX_HEADER_FONT_PX} step={1} onChange={setHeaderFontPx} />
            <Slider label="Padding" value={contentPaddingPx} min={4} max={56} step={1} onChange={setContentPaddingPx} />
            <Slider label="BG opacity" value={bgOpacity} min={0} max={1} step={0.01} decimals={2} onChange={setBgOpacity} />
            <Slider label="BG blur" value={bgBlur} min={0} max={16} step={0.5} decimals={1} onChange={setBgBlur} />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Education text</h4>
            <Slider
              label="Panel H"
              value={rightSplit}
              min={MIN_PANEL_SPLIT}
              max={MAX_PANEL_SPLIT}
              step={0.01}
              decimals={2}
              onChange={setRightSplit}
            />
            <Slider
              label="Base px"
              value={eduBaseFontPx}
              min={10}
              max={MAX_TIMELINE_FONT_PX}
              step={1}
              onChange={setEduBaseFontPx}
            />
            <Slider
              label="Degree"
              value={eduDegreeEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setEduDegreeEm}
            />
            <Slider
              label="Date"
              value={eduDateEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setEduDateEm}
            />
            <Slider
              label="School"
              value={eduSchoolEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setEduSchoolEm}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Experience text</h4>
            <Slider
              label="Base px"
              value={expBaseFontPx}
              min={10}
              max={MAX_TIMELINE_FONT_PX}
              step={1}
              onChange={setExpBaseFontPx}
            />
            <Slider
              label="Role"
              value={expRoleEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setExpRoleEm}
            />
            <Slider
              label="Date"
              value={expDateEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setExpDateEm}
            />
            <Slider
              label="Org"
              value={expOrgEm}
              min={0.6}
              max={MAX_TYPE_EM}
              step={0.01}
              decimals={2}
              onChange={setExpOrgEm}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Contact</h4>
            <Slider
              label="Height px"
              value={contactHeightPx}
              min={MIN_CONTACT_HEIGHT_PX}
              max={MAX_CONTACT_HEIGHT_PX}
              step={1}
              onChange={setContactHeightPx}
            />
            <Slider
              label="Icon px"
              value={contactIconSizePx}
              min={20}
              max={72}
              step={1}
              onChange={setContactIconSizePx}
            />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Border</h4>
            <Slider label="Emission" value={bezelEmission} min={0.5} max={6} step={0.1} decimals={1} onChange={setBezelEmission} />
            <Slider label="Width" value={bezelLineWidth} min={0.5} max={6} step={0.1} decimals={1} onChange={setBezelLineWidth} />
            <Slider label="Opacity" value={bezelOpacity} min={0} max={1} step={0.01} decimals={2} onChange={setBezelOpacity} />
          </section>

          <hr className="desk-controls__divider" />

          <section className="desk-controls__group">
            <h4 className="desk-controls__group-title">Bloom</h4>
            <Slider label="Intensity" value={bloomIntensity} min={0} max={4} step={0.05} decimals={2} onChange={setBloomIntensity} />
            <Slider label="Threshold" value={bloomThreshold} min={0} max={1} step={0.01} decimals={2} onChange={setBloomThreshold} />
            <Slider label="Radius" value={bloomRadius} min={0} max={1.5} step={0.05} decimals={2} onChange={setBloomRadius} />
            <Slider label="Smoothing" value={bloomSmoothing} min={0} max={1} step={0.01} decimals={2} onChange={setBloomSmoothing} />
          </section>

          <hr className="desk-controls__divider" />

          <div className="desk-controls__actions">
            <button className="desk-controls__reset" type="button" onClick={reset}>
              Reset defaults
            </button>
            <button
              className={`desk-controls__save ${savedFlash ? "desk-controls__save--flash" : ""}`}
              type="button"
              onClick={onSaveAsDefault}
            >
              {savedFlash ? "Saved" : "Set as default"}
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
