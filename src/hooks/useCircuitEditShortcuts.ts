import { useEffect } from "react";
import { useCircuitTuning } from "../stores/circuitTuning";
import {
  SHORTCUT_BTN,
  flashShortcutButton,
} from "./useShortcutButtonFlash";

/** Global edit shortcuts: undo, redo, delete, copy/paste, cancel tool. */
export function useCircuitEditShortcuts() {
  const undo = useCircuitTuning((s) => s.undo);
  const redo = useCircuitTuning((s) => s.redo);
  const deleteSelection = useCircuitTuning((s) => s.deleteSelection);
  const copySelectedLines = useCircuitTuning((s) => s.copySelectedLines);
  const pasteLines = useCircuitTuning((s) => s.pasteLines);
  const cancelEditTool = useCircuitTuning((s) => s.cancelEditTool);
  const editTool = useCircuitTuning((s) => s.editTool);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const selectedMeshIds = useCircuitTuning((s) => s.selectedMeshIds);
  const hasSelection =
    selectedLineIds.length > 0 || selectedMeshIds.length > 0;

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      if (e.key === "Escape") {
        if (editTool !== "select") {
          e.preventDefault();
          cancelEditTool();
          flashShortcutButton(
            editTool === "addLine" ? SHORTCUT_BTN.addLine : SHORTCUT_BTN.select,
          );
        }
        return;
      }

      const mod = e.metaKey || e.ctrlKey;
      if (!mod) {
        if (e.key === "Delete" || e.key === "Backspace") {
          if (!hasSelection) return;
          e.preventDefault();
          deleteSelection();
          flashShortcutButton(SHORTCUT_BTN.delete);
        }
        return;
      }

      if (e.key === "z" || e.key === "Z") {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
          flashShortcutButton(SHORTCUT_BTN.redo);
        } else {
          undo();
          flashShortcutButton(SHORTCUT_BTN.undo);
        }
      } else if (e.key === "y" || e.key === "Y") {
        e.preventDefault();
        redo();
        flashShortcutButton(SHORTCUT_BTN.redo);
      } else if (e.key === "c" || e.key === "C") {
        if (copySelectedLines()) {
          e.preventDefault();
          flashShortcutButton(SHORTCUT_BTN.copy);
        }
      } else if (e.key === "v" || e.key === "V") {
        if (pasteLines()) {
          e.preventDefault();
          flashShortcutButton(SHORTCUT_BTN.paste);
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    undo,
    redo,
    deleteSelection,
    copySelectedLines,
    pasteLines,
    cancelEditTool,
    editTool,
    hasSelection,
  ]);
}
