import { bootNoise } from "./bootSequence";

/** One sample of the panel flicker. Matches `bootNoise`. */
const STEP_MS = 33;

export interface TitleFlickerAspects {
  /** Cyan halo around the lit word. */
  glow: boolean;
  /** The tube strobes on and off before it holds. */
  flicker: boolean;
  /** One sample blows out white. */
  whiteHot: boolean;
  /** Between flashes the tube stays faintly lit. */
  dimTube: boolean;
  /** The word dies once after it has caught, then holds. */
  dropout: boolean;
}

export const DEFAULT_TITLE_FLICKER_ASPECTS: TitleFlickerAspects = {
  glow: true,
  flicker: true,
  whiteHot: true,
  dimTube: true,
  dropout: true,
};

export interface TitleCatch {
  opacity: number;
  /** 0 = no halo, 1 = the resting neon, higher = the white flash. */
  glow: number;
  hot: boolean;
}

const DARK: TitleCatch = { opacity: 0, glow: 0, hot: false };

/** Hard on/off beats, as fractions of the catch. */
const BEATS = [0.08, 0.18, 0.34, 0.46, 0.62];

/**
 * Neon title catch, in the rhythm of the TRON Disney ident.
 *
 * The word is a tube that is either dark, faintly lit, or fully on.
 * It strobes, blows out once, drops out, then holds a steady glow.
 */
export function titleCatch(
  elapsedMs: number,
  startMs: number,
  durationMs: number,
  seed: number,
  aspects: TitleFlickerAspects,
): TitleCatch {
  const t = elapsedMs - startMs;
  if (t < 0) return DARK;

  const dur = Math.max(STEP_MS * 4, durationMs);
  const glowOf = (amount: number) => (aspects.glow ? amount : 0);
  if (t >= dur) return { opacity: 1, glow: glowOf(1), hot: false };

  const n = bootNoise(elapsedMs, seed);
  const step = Math.floor(elapsedMs / STEP_MS);
  const hotStep = Math.floor((startMs + dur * 0.52) / STEP_MS);
  const onBeat =
    aspects.flicker &&
    BEATS.some((b) => step === Math.floor((startMs + dur * b) / STEP_MS));

  let opacity = 0;
  let glow = 0;
  let hot = false;

  if (aspects.dimTube && n > 0.42) {
    opacity = 0.55;
    glow = glowOf(0.45);
  }

  if (aspects.flicker && (onBeat || n > 0.74)) {
    opacity = 1;
    glow = glowOf(1);
    hot = aspects.whiteHot && n > 0.92;
  }

  if (aspects.whiteHot && step === hotStep) {
    opacity = 1;
    glow = glowOf(1.6);
    hot = true;
  }

  const dropoutAt = dur * 0.78;
  if (aspects.dropout && t >= dropoutAt && t < dropoutAt + STEP_MS * 3) {
    opacity = 0;
    glow = 0;
    hot = false;
  }

  return { opacity, glow, hot };
}

/** Stacked halo. `glow` is 0..~1.6 from `titleCatch`. */
export function neonTextShadow(glow: number, hot: boolean): string {
  if (glow <= 0) return "none";
  const g = glow * (hot ? 1.45 : 1);
  const core = hot ? 1 : 0.96;
  return [
    `0 0 2px rgba(255,255,255,${core})`,
    `0 0 ${Math.round(7 * g)}px rgba(214,251,255,0.95)`,
    `0 0 ${Math.round(16 * g)}px rgba(140,236,255,0.9)`,
    `0 0 ${Math.round(32 * g)}px rgba(70,206,255,0.8)`,
    `0 0 ${Math.round(58 * g)}px rgba(36,168,255,0.55)`,
    `0 0 ${Math.round(90 * g)}px rgba(16,120,255,0.28)`,
  ].join(", ");
}
