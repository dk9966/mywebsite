import { bootNoise } from "./bootSequence";

/** One sample of the panel flicker. Matches `bootNoise`. */
const STEP_MS = 33;

export interface TitleFlickerAspects {
  /** Dim line drawing between flashes, the castle before the light holds. */
  faintWire: boolean;
  /** Uneven on/off samples. Off, the word stays dim until it locks. */
  flicker: boolean;
  /** The brightest sample goes white-hot, then back to the resting cyan. */
  whiteHot: boolean;
  /** A single sample shifts the word 1px, then it snaps back. */
  tear: boolean;
  /** One dip after the word has caught, then it holds. */
  lateDropout: boolean;
}

export const DEFAULT_TITLE_FLICKER_ASPECTS: TitleFlickerAspects = {
  faintWire: true,
  flicker: true,
  whiteHot: true,
  tear: true,
  lateDropout: true,
};

export interface TitleCatch {
  opacity: number;
  /** Horizontal tear, CSS px. */
  x: number;
  hot: boolean;
}

const HELD: TitleCatch = { opacity: 1, x: 0, hot: false };
const DARK: TitleCatch = { opacity: 0, x: 0, hot: false };

/**
 * Disney-castle rez for a panel title.
 *
 * The word already owns its box. During the catch it samples the same
 * stepped noise as the glass (`bootNoise`), so the letters flash on the
 * frames the panel flashes. After `durationMs` the word is on and still.
 *
 * `elapsedMs` is the shared boot clock. `startMs` is when this panel's
 * title catch begins.
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

  const dur = Math.max(STEP_MS, durationMs);
  if (t >= dur) return HELD;

  const n = bootNoise(elapsedMs, seed);
  const step = Math.floor(elapsedMs / STEP_MS);
  const tearStep = Math.floor((startMs + dur * 0.46) / STEP_MS);
  const hotStep = Math.floor((startMs + dur * 0.58) / STEP_MS);
  const tearing = aspects.tear && step === tearStep;
  const dropoutAt = dur * 0.82;

  let opacity = aspects.faintWire ? 0.08 : 0;
  let hot = false;

  if (aspects.flicker) {
    if (n > 0.82) {
      opacity = 1;
      hot = aspects.whiteHot && n > 0.93;
    } else if (n > 0.6) {
      opacity = 0.38;
    }
  }

  if (aspects.whiteHot && step === hotStep) {
    opacity = 1;
    hot = true;
  }

  if (tearing) opacity = 1;

  if (t >= dropoutAt) {
    const dipping =
      aspects.lateDropout && t < dropoutAt + STEP_MS * 2;
    opacity = dipping ? 0.22 : 1;
    hot = false;
  }

  return { opacity, x: tearing ? 1 : 0, hot };
}
