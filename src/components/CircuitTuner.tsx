import { useCallback, useMemo, useRef, useState } from "react";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import { useCircuitTuning } from "../stores/circuitTuning";
import {
  SHORTCUT_BTN,
  useShortcutButtonFlash,
} from "../hooks/useShortcutButtonFlash";
import "./CircuitTuner.css";

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}

function Slider({ label, value, min, max, step, onChange }: SliderProps) {
  return (
    <div className="tuner__field">
      <span className="tuner__label">{label}</span>
      <input
        className="tuner__slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="tuner__value">{value.toFixed(step < 1 ? 2 : 0)}</span>
    </div>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  step?: number;
  onChange: (v: number) => void;
}

function NumberField({ label, value, step = 0.1, onChange }: NumberFieldProps) {
  return (
    <div className="tuner__number-field">
      <span className="tuner__label">{label}</span>
      <input
        className="tuner__number-input"
        type="number"
        step={step}
        value={Number.isFinite(value) ? Number(value.toFixed(3)) : 0}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (Number.isFinite(v)) onChange(v);
        }}
      />
    </div>
  );
}

function Vec3Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: Vec3;
  onChange: (v: Vec3) => void;
}) {
  return (
    <div className="tuner__vec3">
      <span className="tuner__label">{label}</span>
      <div className="tuner__vec3-inputs">
        {(["x", "y", "z"] as const).map((axis, i) => (
          <input
            key={axis}
            className="tuner__number-input tuner__number-input--compact"
            type="number"
            step={0.1}
            value={Number(value[i].toFixed(3))}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!Number.isFinite(v)) return;
              const next: Vec3 = [...value];
              next[i] = v;
              onChange(next);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function downloadJSON(text: string) {
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "circuits-tuning.json";
  a.click();
  URL.revokeObjectURL(url);
}

export default function CircuitTuner({ paths }: { paths: GridPath[] }) {
  const timing = useCircuitTuning((s) => s.timing);
  const transform = useCircuitTuning((s) => s.transform);
  const overrides = useCircuitTuning((s) => s.overrides);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedId = selectedLineIds[0] ?? null;

  const select = useCircuitTuning((s) => s.select);
  const setTiming = useCircuitTuning((s) => s.setTiming);
  const setTransform = useCircuitTuning((s) => s.setTransform);
  const setOverride = useCircuitTuning((s) => s.setOverride);
  const clearOverride = useCircuitTuning((s) => s.clearOverride);
  const deleteSelectedSegment = useCircuitTuning(
    (s) => s.deleteSelectedSegment,
  );
  const setEditTool = useCircuitTuning((s) => s.setEditTool);
  const cancelEditTool = useCircuitTuning((s) => s.cancelEditTool);
  const editTool = useCircuitTuning((s) => s.editTool);
  const addLineStart = useCircuitTuning((s) => s.addLineStart);
  const undo = useCircuitTuning((s) => s.undo);
  const redo = useCircuitTuning((s) => s.redo);
  const undoStack = useCircuitTuning((s) => s.undoStack);
  const redoStack = useCircuitTuning((s) => s.redoStack);
  const bakeFromBaseline = useCircuitTuning((s) => s.bakeFromBaseline);
  const resetAll = useCircuitTuning((s) => s.resetAll);
  const exportJSON = useCircuitTuning((s) => s.exportJSON);
  const importJSON = useCircuitTuning((s) => s.importJSON);
  const { btnClass, btnTitle } = useShortcutButtonFlash();
  const saveAsDefault = useCircuitTuning((s) => s.saveAsDefault);

  const [minimized, setMinimized] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const selectedPath = useMemo(
    () => paths.find((p) => p.id === selectedId) ?? null,
    [paths, selectedId],
  );
  const selectedOverride = selectedId ? overrides[selectedId] : undefined;

  const onBake = useCallback(() => {
    const baseline: Record<string, { spawnTime: number; cursorSpeed: number }> =
      {};
    for (const p of paths) {
      if (!p.id) continue;
      baseline[p.id] = {
        spawnTime: p.spawnTime,
        cursorSpeed: p.cursorSpeed ?? 0,
      };
    }
    bakeFromBaseline(baseline);
  }, [paths, bakeFromBaseline]);

  const onImportFile = useCallback(
    (file: File) => {
      file.text().then((text) => {
        if (!importJSON(text)) {
          // Keep current state on parse failure; nothing destructive happens.
          console.warn("[CircuitTuner] could not parse tuning file");
        }
      });
    },
    [importJSON],
  );

  const effectiveSpawn =
    selectedOverride?.spawnTime ?? selectedPath?.spawnTime ?? 0;
  const effectiveSpeed =
    selectedOverride?.cursorSpeed ?? selectedPath?.cursorSpeed ?? 0;
  const selectedOffset: Vec3 = selectedOverride?.offset ?? [0, 0, 0];

  return (
    <aside className={`tuner ${minimized ? "tuner--minimized" : ""}`}>
      <div className="tuner__header">
        <h3 className="tuner__title">Circuit Tuner</h3>
        <button
          className="tuner__btn"
          type="button"
          onClick={() => setMinimized(!minimized)}
          title={minimized ? "Expand" : "Minimize"}
        >
          {minimized ? "+" : "-"}
        </button>
      </div>

      {!minimized && (
        <>
          <section className="tuner__group">
            <h4 className="tuner__group-title">Timing</h4>
            <Slider
              label="Pan speed"
              value={timing.panSpeed}
              min={0.2}
              max={6}
              step={0.1}
              onChange={(v) => setTiming({ panSpeed: v })}
            />
            <Slider
              label="Draw window"
              value={timing.drawFraction}
              min={0.3}
              max={1}
              step={0.01}
              onChange={(v) => setTiming({ drawFraction: v })}
            />
            <Slider
              label="Speed scale"
              value={timing.speedScale}
              min={0.2}
              max={3}
              step={0.05}
              onChange={(v) => setTiming({ speedScale: v })}
            />
            <Slider
              label="Start delay"
              value={timing.startTime}
              min={0}
              max={5}
              step={0.1}
              onChange={(v) => setTiming({ startTime: v })}
            />
            <button
              className="tuner__btn tuner__btn--wide"
              type="button"
              onClick={onBake}
              title="Pin current auto spawn/speed onto every line"
            >
              Bake scan times
            </button>
          </section>

          <hr className="tuner__divider" />

          <section className="tuner__group">
            <h4 className="tuner__group-title">Placement (board)</h4>
            <Vec3Field
              label="Offset"
              value={transform.offset}
              onChange={(v) => setTransform({ offset: v })}
            />
            <Slider
              label="Rotate Y"
              value={transform.rotationYDeg}
              min={-180}
              max={180}
              step={1}
              onChange={(v) => setTransform({ rotationYDeg: v })}
            />
            <Slider
              label="Scale"
              value={transform.scale}
              min={0.2}
              max={3}
              step={0.02}
              onChange={(v) => setTransform({ scale: v })}
            />
          </section>

          <hr className="tuner__divider" />

          <section className="tuner__group">
            <h4 className="tuner__group-title">Selected line</h4>
            {selectedId && selectedPath ? (
              <>
                <div className="tuner__selected-id">{selectedId}</div>
                <p className="tuner__hint tuner__hint--spawn">
                  Drag a handle to slide along that segment&apos;s axis. Release
                  near another line to join or split it. Yellow = spawn start,
                  gray = draw end.
                </p>
                <NumberField
                  label="Spawn (s)"
                  value={effectiveSpawn}
                  step={0.05}
                  onChange={(v) => setOverride(selectedId, { spawnTime: v })}
                />
                <NumberField
                  label="Speed (u/s)"
                  value={effectiveSpeed}
                  step={0.1}
                  onChange={(v) => setOverride(selectedId, { cursorSpeed: v })}
                />
                <Vec3Field
                  label="Offset"
                  value={selectedOffset}
                  onChange={(v) => setOverride(selectedId, { offset: v })}
                />
                <button
                  className="tuner__btn tuner__btn--wide"
                  type="button"
                  onClick={() =>
                    setOverride(selectedId, {
                      reversed: !(selectedOverride?.reversed ?? false),
                    })
                  }
                >
                  {selectedOverride?.reversed
                    ? "Direction: reversed"
                    : "Flip draw direction"}
                </button>
                <label className="tuner__checkbox-field">
                  <input
                    className="tuner__checkbox"
                    type="checkbox"
                    checked={selectedOverride?.hidden ?? false}
                    onChange={(e) =>
                      setOverride(selectedId, { hidden: e.target.checked })
                    }
                  />
                  <span>Hidden</span>
                </label>
                <button
                  className={btnClass(
                    SHORTCUT_BTN.delete,
                    "tuner__btn tuner__btn--wide",
                  )}
                  type="button"
                  title={btnTitle(SHORTCUT_BTN.delete)}
                  onClick={() => deleteSelectedSegment()}
                >
                  Delete line
                </button>
                <button
                  className="tuner__btn tuner__btn--wide"
                  type="button"
                  onClick={() => clearOverride(selectedId)}
                >
                  Clear overrides
                </button>
              </>
            ) : (
              <p className="tuner__hint">
                Click a line, then drag its vertex handles to edit.
              </p>
            )}
          </section>

          <hr className="tuner__divider" />

          <section className="tuner__group">
            <h4 className="tuner__group-title">Edit</h4>
            <p className="tuner__hint tuner__hint--spawn">
              Add line: click start, then end on the board. Split: select a line,
              then click it where you want the break. Join: drag a handle onto
              another line. Esc cancels the active tool.
            </p>
            <div className="tuner__edit-row">
              <button
                className={btnClass(
                  SHORTCUT_BTN.addLine,
                  `tuner__btn ${editTool === "addLine" ? "tuner__btn--active" : ""}`,
                )}
                type="button"
                title={btnTitle(SHORTCUT_BTN.addLine)}
                onClick={() =>
                  editTool === "addLine"
                    ? cancelEditTool()
                    : setEditTool("addLine")
                }
              >
                {editTool === "addLine" ? "Cancel add" : "Add line"}
              </button>
              <button
                className={`tuner__btn ${editTool === "split" ? "tuner__btn--active" : ""}`}
                type="button"
                disabled={!selectedId && editTool !== "split"}
                onClick={() =>
                  setEditTool(editTool === "split" ? "select" : "split")
                }
              >
                Split
              </button>
            </div>
            {editTool === "addLine" ? (
              <p className="tuner__hint">
                {addLineStart
                  ? "Click to place the next point. Esc cancels."
                  : "Click the first point on the board."}
              </p>
            ) : null}
            {editTool === "split" ? (
              <p className="tuner__hint">
                Click the highlighted line where you want to split it. Esc
                cancels.
              </p>
            ) : null}
            <p className="tuner__hint tuner__hint--spawn">
              Delete / Backspace removes the selected line. Ctrl+Z undo,
              Ctrl+Shift+Z redo.
            </p>
            <div className="tuner__edit-row">
              <button
                className={btnClass(SHORTCUT_BTN.undo, "tuner__btn")}
                type="button"
                title={btnTitle(SHORTCUT_BTN.undo)}
                onClick={undo}
                disabled={undoStack.length === 0}
              >
                Undo
              </button>
              <button
                className={btnClass(SHORTCUT_BTN.redo, "tuner__btn")}
                type="button"
                title={btnTitle(SHORTCUT_BTN.redo)}
                onClick={redo}
                disabled={redoStack.length === 0}
              >
                Redo
              </button>
            </div>
          </section>

          <hr className="tuner__divider" />

          <section className="tuner__group">
            <h4 className="tuner__group-title">Lines ({paths.length})</h4>
            <div className="tuner__list">
              {paths.map((p) => {
                if (!p.id) return null;
                const ov = overrides[p.id];
                const tuned =
                  ov &&
                  (ov.spawnTime !== undefined ||
                    ov.cursorSpeed !== undefined ||
                    ov.offset !== undefined ||
                    ov.reversed);
                return (
                  <button
                    key={p.id}
                    type="button"
                    className={`tuner__list-item ${p.id === selectedId ? "tuner__list-item--active" : ""}`}
                    onClick={() => select(p.id!)}
                  >
                    <span className="tuner__list-name">{p.id}</span>
                    {ov?.reversed ? (
                      <span className="tuner__badge tuner__badge--reversed">
                        rev
                      </span>
                    ) : null}
                    {ov?.hidden ? (
                      <span className="tuner__badge tuner__badge--hidden">
                        hidden
                      </span>
                    ) : null}
                    {tuned ? <span className="tuner__badge">tuned</span> : null}
                  </button>
                );
              })}
            </div>
          </section>

          <hr className="tuner__divider" />

          <section className="tuner__group tuner__actions">
            <button
              className="tuner__btn tuner__btn--wide tuner__btn--save-default"
              type="button"
              onClick={async () => {
                const ok = await saveAsDefault();
                setSaveStatus(
                  ok
                    ? "Saved to src/data/circuits-tuning.json — reload page"
                    : "Downloaded — place in src/data/ and reload",
                );
                window.setTimeout(() => setSaveStatus(null), 4000);
              }}
            >
              Save as default
            </button>
            {saveStatus ? (
              <p className="tuner__hint tuner__hint--status">{saveStatus}</p>
            ) : null}
            <button
              className="tuner__btn tuner__btn--wide"
              type="button"
              onClick={() => downloadJSON(exportJSON())}
            >
              Export JSON
            </button>
            <button
              className="tuner__btn tuner__btn--wide"
              type="button"
              onClick={() => fileRef.current?.click()}
            >
              Import JSON
            </button>
            <input
              ref={fileRef}
              className="tuner__file-input"
              type="file"
              accept="application/json,.json"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onImportFile(file);
                e.target.value = "";
              }}
            />
            <button className="tuner__reset" type="button" onClick={resetAll}>
              Reset all
            </button>
          </section>
        </>
      )}
    </aside>
  );
}
