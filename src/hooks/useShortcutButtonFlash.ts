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
} as const;

export type ShortcutButtonId = (typeof SHORTCUT_BTN)[keyof typeof SHORTCUT_BTN];

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

  return { flash, btnClass };
}
