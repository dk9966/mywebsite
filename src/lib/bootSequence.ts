import {
  armBootClock,
  bootAnchorElapsedMs,
  useBootClock,
} from "../stores/bootClock";
import { bootPartScale, useBootTuning } from "../stores/bootTuning";
import type { BootPanelId } from "./bootParts";
import { DEFAULT_PANEL_START_MS, bootScaleMs } from "./bootParts";
import type { CellId } from "./panelWall";

/** Per-panel power-on offsets (ms from mount). Deliberately not sorted
 *  left-to-right so the wall reads as independent screens syncing up. */
export function bootPanelStartMs(id: CellId): number {
  return useBootTuning.getState().panelStartMs[id as BootPanelId];
}

/** Every panel is sharp and steady at this global time. */
export function bootStabilizeMs(): number {
  return useBootTuning.getState().stabilizeMs;
}

/** The "system online" pulse starts here and staggers across the wall. */
export function bootPulseBaseMs(): number {
  return useBootTuning.getState().pulseBaseMs;
}

export const BOOT_PULSE_SWEEP_MS = 260;

export function bootPulseSweepMs(): number {
  return useBootTuning.getState().pulseSweepMs;
}

/** Boot scaffolding unmounts after this; everything must equal steady state. */
export { BOOT_TOTAL_MS } from "./bootParts";

export interface PanelBoot {
  /** This panel's power-on offset, ms from mount. */
  startMs: number;
  /** Absolute delay of the final sweep as it crosses this panel. */
  pulseDelayMs: number;
  /** Deterministic flicker seed so panels don't blink in unison. */
  seed: number;
}

/** Arms the global clock (idempotent — first caller wins). */
export function startBootClock(): void {
  const { elapsedMs } = useBootClock.getState();
  armBootClock(elapsedMs);
}

export function bootElapsedMs(): number {
  const { paused, scrubbing, elapsedMs } = useBootClock.getState();
  if (paused || scrubbing) return elapsedMs;
  return bootAnchorElapsedMs();
}

/** Skip the whole sequence for users who prefer reduced motion. */
export function bootSkipped(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}

function hash01(n: number): number {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453123;
  return s - Math.floor(s);
}

/** Stepped pseudo-random flicker (~30 Hz), deterministic per seed. */
export function bootNoise(tMs: number, seed: number): number {
  return hash01(Math.floor(tMs / 33) * 7.13 + seed * 57.31);
}

export interface BootVisual {
  /** Opacity multiplier for the faint full-outline glow line. */
  glow: number;
  /** 0..1 fraction of the bezel outline drawn in (dash sweep). */
  draw: number;
  /** Opacity multiplier for the drawing/steady bezel line. */
  drawOpacity: number;
  /** Opacity multiplier for the curved glass fill. */
  fill: number;
  /** Extra emission during the final online pulse (0..~0.9). */
  boost: number;
}

const DARK: BootVisual = {
  glow: 0,
  draw: 0,
  drawOpacity: 0,
  fill: 0,
  boost: 0,
};

function partEnd(
  id: "edgeGlow" | "flickerFill" | "bezelDraw" | "glassAssembly",
): number {
  const p = useBootTuning.getState().parts[id];
  return p.delayMs + p.durationMs;
}

export function panelBootVisual(
  elapsedMs: number,
  boot: PanelBoot,
): BootVisual {
  const stabilizeMs = bootStabilizeMs();
  const pulseDur = useBootTuning.getState().parts.onlinePulse.durationMs;

  let boost = 0;
  if (bootPartScale("onlinePulse") > 0) {
    const pt = elapsedMs - boot.pulseDelayMs;
    if (pt >= 0 && pt < pulseDur) {
      boost = Math.sin((pt / pulseDur) * Math.PI) * 0.9;
    }
  }

  if (elapsedMs >= stabilizeMs) {
    return {
      glow: 0,
      draw: 1,
      drawOpacity: 1,
      fill: 1,
      boost,
    };
  }

  const e = elapsedMs - boot.startMs;
  if (e < 0) return DARK;

  const n = bootNoise(elapsedMs, boot.seed);
  const glowEnd = partEnd("edgeGlow");
  const flickerEnd = partEnd("flickerFill");
  const frameEnd = partEnd("bezelDraw");
  const assemblyStart = useBootTuning.getState().parts.glassAssembly.delayMs;

  if (e < glowEnd) {
    if (bootPartScale("edgeGlow") === 0) return DARK;
    return {
      glow: (0.07 + 0.1 * n) * bootPartScale("edgeGlow"),
      draw: 0,
      drawOpacity: 0,
      fill: 0,
      boost: 0,
    };
  }

  if (e < flickerEnd) {
    if (bootPartScale("flickerFill") === 0) return DARK;
    const glow = n > 0.78 ? 0.85 : n > 0.5 ? 0.28 : 0.1;
    const fill =
      n > 0.66
        ? 0.05 + 0.28 * hash01(boot.seed + Math.floor(elapsedMs / 41))
        : 0.04;
    return {
      glow: glow * bootPartScale("edgeGlow"),
      draw: 0,
      drawOpacity: 0,
      fill: fill * bootPartScale("flickerFill"),
      boost: 0,
    };
  }

  if (e < frameEnd) {
    const frameScale = bootPartScale("bezelDraw");
    const p = (e - flickerEnd) / Math.max(1, frameEnd - flickerEnd);
    const eased = p * p * (3 - 2 * p);
    const dropout = n > 0.92 ? 0.4 : 1;
    return {
      glow: (0.16 + 0.18 * n) * bootPartScale("edgeGlow"),
      draw: eased * frameScale,
      drawOpacity: (0.55 + 0.45 * eased) * dropout * frameScale,
      fill: (0.15 + 0.4 * eased) * bootPartScale("flickerFill"),
      boost: 0,
    };
  }

  const span = Math.max(1, stabilizeMs - (boot.startMs + assemblyStart));
  const p = Math.min(1, (elapsedMs - (boot.startMs + assemblyStart)) / span);
  const assemblyScale = bootPartScale("glassAssembly");
  return {
    glow: 0.22 * bootPartScale("edgeGlow"),
    draw: 1,
    drawOpacity: (n > 0.94 ? 0.55 : 1) * bootPartScale("bezelDraw"),
    fill: (0.55 + 0.45 * p) * (n > 0.9 ? 0.8 : 1) * assemblyScale,
    boost: 0,
  };
}

/** Legacy export — prefer bootPanelStartMs() for live tuning values. */
export const BOOT_PANEL_START_MS: Record<CellId, number> =
  DEFAULT_PANEL_START_MS;

export const BOOT_STABILIZE_MS = bootScaleMs(2900);
export const BOOT_PULSE_DELAY_MS = bootScaleMs(3050);
export const BOOT_PULSE_DUR_MS = bootScaleMs(450);

export function panelPulseDelayForCell(
  cellX: number,
  wallWidthPx: number,
): number {
  const base = bootPulseBaseMs();
  const sweep = bootPulseSweepMs();
  return base + (cellX / wallWidthPx + 0.5) * sweep;
}
