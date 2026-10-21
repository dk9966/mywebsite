import { bootNoise } from "./bootSequence";

/** One sample of the panel flicker. Matches `bootNoise`. */
const STEP_MS = 33;

export interface TitleFlickerAspects {
  /** Each letter catches on its own, in random order. Off: the word catches as one. */
  letters: boolean;
  /** Hollow glyphs catch first, then fill at lock. */
  outline: boolean;
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
  outline: true,
  ghost: true,
  scatter: true,
  whiteHot: true,
  glow: true,
};

export interface TitleFlickerTuning {
  catchSpread: number;
  flickerHz: number;
  ghostOpacity: number;
  jumpEm: number;
  flashMs: number;
  glowStrength: number;
  outlineBloom: number;
  settledBloom: number;
}

export const DEFAULT_TITLE_FLICKER_TUNING: TitleFlickerTuning = {
  catchSpread: 0.15,
  flickerHz: 30,
  ghostOpacity: 0.38,
  jumpEm: 0.25,
  flashMs: 65,
  glowStrength: 1,
  outlineBloom: 1,
  settledBloom: 1.5,
};

export interface LetterCatch {
  opacity: number;
  outline: boolean;
  /** Sideways jump, em. */
  x: number;
  ghost: boolean;
  hot: boolean;
  /** 0 = no halo, 1 = resting neon, higher = the white flash. */
  glow: number;
}

const DARK: LetterCatch = { opacity: 0, outline: false, x: 0, ghost: false, hot: false, glow: 0 };

function hash01(n: number): number {
  const s = Math.sin(n * 91.3 + 47.9) * 43758.5453123;
  return s - Math.floor(s);
}

/**
 * One letter of a title, in the rhythm of the "Walt Disney" type in the
 * TRON: Legacy ident: letters blink on in random order, show as faint
 * doubled ghosts, jump a little, and fill in three groups with two brief bloom pulses, then hold steady.
 */
export function letterCatch(
  elapsedMs: number,
  startMs: number,
  durationMs: number,
  seed: number,
  index: number,
  aspects: TitleFlickerAspects,
  tuning: TitleFlickerTuning = DEFAULT_TITLE_FLICKER_TUNING,
): LetterCatch {
  const t = elapsedMs - startMs;
  if (t < 0) return DARK;

  const dur = Math.max(STEP_MS * 4, durationMs);
  const glowOf = (amount: number) => (aspects.glow ? amount * tuning.glowStrength : 0);
  const key = aspects.letters ? seed * 13.7 + index * 3.17 : seed * 13.7;
  // Three shared catch groups rather than a distinct lock for every letter.
  const group = aspects.letters ? Math.floor(hash01(key + 0.5) * 3) : 0;
  const offset = dur * tuning.catchSpread * group / 2;
  const local = t - offset;
  const lockMs = dur * 0.72;
  const pulse = (local >= dur * 0.38 && local < dur * 0.45)
    || (local >= dur * 0.54 && local < dur * 0.61);
  const locked = local >= lockMs;
  const flashing = pulse || (locked && local - lockMs < tuning.flashMs);

  if (pulse || locked) {
    return {
      opacity: 1,
      outline: false,
      x: 0,
      ghost: false,
      hot: aspects.whiteHot && flashing,
      glow: glowOf(flashing ? 2.2 : tuning.settledBloom),
    };
  }

  const step = Math.floor(t * tuning.flickerHz / 1000);
  const n = bootNoise(step * STEP_MS, key);
  const ghost = aspects.ghost && local < dur * 0.3 && n > 0.76;
  const x = aspects.scatter && ghost
    ? (hash01(step * 1.31 + key) - 0.5) * tuning.jumpEm
    : 0;

  if (!aspects.outline) return DARK;

  // A readable, softly blooming outline holds between the two fill flashes.
  return {
    opacity: ghost ? 0.5 + tuning.ghostOpacity * 0.4 : 0.85,
    outline: aspects.outline,
    x,
    ghost,
    hot: false,
    glow: glowOf(tuning.outlineBloom),
  };
}

/** Stacked halo. `glow` is 0..2.2 from `letterCatch`. */
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
