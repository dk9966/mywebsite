import { bootNoise } from "./bootSequence";

/** One sample of the panel flicker. Matches `bootNoise`. */
const STEP_MS = 33;

export interface TitleFlickerAspects {
  /** Each letter catches on its own, in random order. Off: the word catches as one. */
  letters: boolean;
  /** A faint doubled letter shows before it catches. */
  ghost: boolean;
  /** Letters that have not caught jump sideways between frames. */
  scatter: boolean;
  /** A letter blows out white on the frame it locks. */
  whiteHot: boolean;
  /** Cyan halo around the lit letters. */
  glow: boolean;
}

export const DEFAULT_TITLE_FLICKER_ASPECTS: TitleFlickerAspects = {
  letters: true,
  ghost: true,
  scatter: true,
  whiteHot: true,
  glow: true,
};

export interface LetterCatch {
  opacity: number;
  /** Sideways jump, em. */
  x: number;
  ghost: boolean;
  hot: boolean;
  /** 0 = no halo, 1 = resting neon, higher = the white flash. */
  glow: number;
}

const DARK: LetterCatch = { opacity: 0, x: 0, ghost: false, hot: false, glow: 0 };

function hash01(n: number): number {
  const s = Math.sin(n * 91.3 + 47.9) * 43758.5453123;
  return s - Math.floor(s);
}

/**
 * One letter of a title, in the rhythm of the "Walt Disney" type in the
 * TRON: Legacy ident: letters blink on in random order, show as faint
 * doubled ghosts, jump a little, and lock one by one into a steady glow.
 */
export function letterCatch(
  elapsedMs: number,
  startMs: number,
  durationMs: number,
  seed: number,
  index: number,
  aspects: TitleFlickerAspects,
): LetterCatch {
  const t = elapsedMs - startMs;
  if (t < 0) return DARK;

  const dur = Math.max(STEP_MS * 4, durationMs);
  const glowOf = (amount: number) => (aspects.glow ? amount : 0);
  const key = aspects.letters ? seed * 13.7 + index * 3.17 : seed * 13.7;
  const lockFrac = aspects.letters ? 0.45 + 0.5 * hash01(key + 0.5) : 0.85;
  const lockMs = dur * lockFrac;

  if (t >= lockMs) {
    const lockStep = Math.floor((startMs + lockMs) / STEP_MS);
    const flashing =
      aspects.whiteHot && Math.floor(elapsedMs / STEP_MS) <= lockStep + 1;
    return {
      opacity: 1,
      x: 0,
      ghost: false,
      hot: flashing,
      glow: glowOf(flashing ? 1.7 : 1),
    };
  }

  const p = t / lockMs;
  const n = bootNoise(elapsedMs, key);
  const onAbove = 0.9 - 0.4 * p;
  const step = Math.floor(elapsedMs / STEP_MS);
  const x = aspects.scatter
    ? (hash01(step * 1.31 + key) - 0.5) * 0.5 * (1 - p * 0.6)
    : 0;

  if (n > onAbove) {
    return { opacity: 0.9, x, ghost: false, hot: false, glow: glowOf(0.8) };
  }
  if (aspects.ghost && n > onAbove - 0.32) {
    return { opacity: 0.38, x, ghost: true, hot: false, glow: glowOf(0.35) };
  }
  return DARK;
}

/** Stacked halo. `glow` is 0..~1.7 from `letterCatch`. */
export function neonTextShadow(glow: number, hot: boolean): string {
  if (glow <= 0) return "none";
  const g = glow * (hot ? 1.3 : 1);
  return [
    `0 0 2px rgba(255,255,255,${hot ? 1 : 0.9})`,
    `0 0 ${Math.round(6 * g)}px rgba(200,248,255,0.9)`,
    `0 0 ${Math.round(14 * g)}px rgba(120,228,255,0.8)`,
    `0 0 ${Math.round(28 * g)}px rgba(60,196,255,0.65)`,
    `0 0 ${Math.round(52 * g)}px rgba(30,150,255,0.4)`,
  ].join(", ");
}

/** The doubled, smeared copy a letter shows before it catches. */
export function ghostTextShadow(glow: number): string {
  const halo = glow > 0 ? `, 0 0 ${Math.round(10 * glow + 4)}px rgba(90,210,255,0.5)` : "";
  return `0.09em 0.03em 0 rgba(110,226,255,0.55), -0.06em 0 1px rgba(110,226,255,0.35)${halo}`;
}
