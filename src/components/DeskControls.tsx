import { useState, type PointerEvent as ReactPointerEvent } from "react";
import {
  useDeskLayout,
  MAX_HEADER_FONT_PX,
  MIN_CONTACT_HEIGHT_PX,
  MAX_CONTACT_HEIGHT_PX,
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
  const reset = useDeskLayout((s) => s.reset);
  const saveAsDefault = useDeskLayout((s) => s.saveAsDefault);

  const [minimized, setMinimized] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  const stopBubble = (e: ReactPointerEvent) => e.stopPropagation();

  const onSaveAsDefault = () => {
    saveAsDefault();
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1400);
  };

  return (
    <aside
      className={`desk-controls ${minimized ? "desk-controls--minimized" : ""}`}
      onPointerDown={stopBubble}
      onPointerMove={stopBubble}
      onPointerUp={stopBubble}
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
            <Slider label="Header" value={headerFontPx} min={9} max={MAX_HEADER_FONT_PX} step={1} onChange={setHeaderFontPx} />
            <Slider label="Padding" value={contentPaddingPx} min={4} max={56} step={1} onChange={setContentPaddingPx} />
            <Slider label="BG opacity" value={bgOpacity} min={0} max={1} step={0.01} decimals={2} onChange={setBgOpacity} />
            <Slider label="BG blur" value={bgBlur} min={0} max={16} step={0.5} decimals={1} onChange={setBgBlur} />
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
