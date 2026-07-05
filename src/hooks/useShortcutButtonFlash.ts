import { useCallback, useEffect, useRef, useState } from "react";

export const SHORTCUT_BTN = {
  select: "select",
  addLine: "addLine",
  snap45: "snap45",
  delete: "delete",
  top: "top",
  side: "side",
  lock: "lock",
  projection: "projection",
  undo: "undo",
  redo: "redo",
  copy: "copy",
  paste: "paste",
} as const;

export type ShortcutButtonId = (typeof SHORTCUT_BTN)[keyof typeof SHORTCUT_BTN];

/** Keyboard hints shown on toolbar button hover (Mac-style mod labels). */
export const SHORTCUT_HINTS: Record<ShortcutButtonId, string> = {
  select: "A",
  addLine: "A",
  snap45: "R",
  delete: "Del",
  top: "F",
  side: "F",
  lock: "L",
  projection: "O",
  undo: "⌘Z",
  redo: "⌘⇧Z",
  copy: "⌘C",
  paste: "⌘V",
};

export function shortcutButtonTitle(
  id: ShortcutButtonId,
  detail?: string,
): string {
  const hint = SHORTCUT_HINTS[id];
  if (detail && hint) return `${detail} (${hint})`;
  if (detail) return detail;
  return hint;
}

const FLASH_MS = 240;

type FlashListener = (id: ShortcutButtonId) => void;
const flashListeners = new Set<FlashListener>();

/** Notify mounted toolbars to briefly flash the button tied to a shortcut. */
export function flashShortcutButton(id: ShortcutButtonId) {
  for (const listener of flashListeners) listener(id);
}

export function useShortcutButtonFlash() {
  const [flashing, setFlashing] = useState<ReadonlySet<ShortcutButtonId>>(
    () => new Set(),
  );
  const timersRef = useRef<Map<ShortcutButtonId, number>>(new Map());

  useEffect(() => {
    const onFlash = (id: ShortcutButtonId) => {
      setFlashing((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
          requestAnimationFrame(() => {
            setFlashing((current) => new Set(current).add(id));
          });
          return next;
        }
        next.add(id);
        return next;
      });

      const existing = timersRef.current.get(id);
      if (existing !== undefined) window.clearTimeout(existing);
      timersRef.current.set(
        id,
        window.setTimeout(() => {
          setFlashing((prev) => {
            const next = new Set(prev);
            next.delete(id);
            return next;
          });
          timersRef.current.delete(id);
        }, FLASH_MS),
      );
    };

    flashListeners.add(onFlash);
    return () => {
      flashListeners.delete(onFlash);
      for (const timer of timersRef.current.values()) window.clearTimeout(timer);
      timersRef.current.clear();
    };
  }, []);

  const flash = useCallback((id: ShortcutButtonId) => {
    flashShortcutButton(id);
  }, []);

  const btnClass = useCallback(
    (id: ShortcutButtonId, base: string) =>
      flashing.has(id) ? `${base} ${base}--flash` : base,
    [flashing],
  );

  const btnTitle = useCallback(
    (id: ShortcutButtonId, detail?: string) => shortcutButtonTitle(id, detail),
    [],
  );

  return { flash, btnClass, btnTitle };
}
