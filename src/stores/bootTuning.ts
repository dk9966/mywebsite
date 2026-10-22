import { create } from "zustand";
import {
  BOOT_PARTS,
  DEFAULT_PANEL_START_MS,
  bootPartCssVars,
  bootScaleMs,
  type BootPanelId,
  type BootPartId,
} from "../lib/bootParts";

export interface BootPartState {
  visible: boolean;
  delayMs: number;
  durationMs: number;
}

function defaultParts(): Record<BootPartId, BootPartState> {
  const out = {} as Record<BootPartId, BootPartState>;
  for (const def of BOOT_PARTS) {
    out[def.id] = {
      visible: def.defaultVisible ?? true,
      delayMs: def.defaultDelayMs,
      durationMs: def.defaultDurationMs,
    };
  }
  return out;
}

interface BootTuningStore {
  parts: Record<BootPartId, BootPartState>;
  panelStartMs: Record<BootPanelId, number>;
  stabilizeMs: number;

  setPartVisible: (id: BootPartId, visible: boolean) => void;
  setAllPartsVisible: (visible: boolean) => void;
  setPartDelay: (id: BootPartId, delayMs: number) => void;
  setPartDuration: (id: BootPartId, durationMs: number) => void;
  setPanelStart: (id: BootPanelId, ms: number) => void;
  setStabilizeMs: (ms: number) => void;
  reset: () => void;
  cssVars: () => Record<string, string>;
}

const DEFAULT_STABILIZE_MS = bootScaleMs(2900);

export const useBootTuning = create<BootTuningStore>((set, get) => ({
  parts: defaultParts(),
  panelStartMs: { ...DEFAULT_PANEL_START_MS },
  stabilizeMs: DEFAULT_STABILIZE_MS,

  setPartVisible: (id, visible) =>
    set((s) => ({
      parts: { ...s.parts, [id]: { ...s.parts[id], visible } },
    })),

  setAllPartsVisible: (visible) =>
    set((s) => {
      const parts = { ...s.parts };
      for (const def of BOOT_PARTS) {
        if (def.hideCheckbox) continue;
        parts[def.id] = { ...parts[def.id], visible };
      }
      return { parts };
    }),

  setPartDelay: (id, delayMs) =>
    set((s) => ({
      parts: {
        ...s.parts,
        [id]: { ...s.parts[id], delayMs: Math.max(0, delayMs) },
      },
    })),

  setPartDuration: (id, durationMs) =>
    set((s) => ({
      parts: {
        ...s.parts,
        [id]: { ...s.parts[id], durationMs: Math.max(1, durationMs) },
      },
    })),

  setPanelStart: (id, ms) =>
    set((s) => ({
      panelStartMs: { ...s.panelStartMs, [id]: Math.max(0, ms) },
    })),

  setStabilizeMs: (ms) => set({ stabilizeMs: Math.max(0, ms) }),

  reset: () =>
    set({
      parts: defaultParts(),
      panelStartMs: { ...DEFAULT_PANEL_START_MS },
      stabilizeMs: DEFAULT_STABILIZE_MS,
    }),

  cssVars: () => {
    const s = get();
    const timing = {} as Record<
      BootPartId,
      { delayMs: number; durationMs: number }
    >;
    for (const def of BOOT_PARTS) {
      timing[def.id] = {
        delayMs: s.parts[def.id].delayMs,
        durationMs: s.parts[def.id].durationMs,
      };
    }
    return {
      ...bootPartCssVars(timing),
      "--boot-stabilize-ms": `${s.stabilizeMs}ms`,
    };
  },
}));

export function isBootPartVisible(id: BootPartId): boolean {
  return useBootTuning.getState().parts[id].visible;
}

export function bootPartScale(id: BootPartId): number {
  return isBootPartVisible(id) ? 1 : 0;
}
