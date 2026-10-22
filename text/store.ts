import { create } from "zustand";
import { DISPLAY_FONTS } from "./fonts";
import { FILL_PRESETS } from "./materials";

export const WORD_IDS = ["project", "about", "experiences", "contact"] as const;
export type WordId = (typeof WORD_IDS)[number];

export const FILLS = [
  ["tron", "Tron lines"],
  ["scanline", "Hologram — scanlines"],
  ["rainbow", "Holo foil — rainbow"],
  ["prism", "Prism — thin film"],
  ["glitch", "Glitch hologram"],
  ["grid", "Wire grid"],
  ["ghost", "Ghost glass — sweep"],
  ["aurora", "Aurora flow"],
  ["datastream", "Data stream"],
  ["neon", "Neon glow"],
  ["wireframe", "Wireframe mesh"],
] as const;
export type FillId = (typeof FILLS)[number][0];

export type TextCase = "as-typed" | "upper" | "lower";

// Font is deliberately not in here: one font drives every word, heading and
// (by default) paragraph, so changing it changes all the text together.
export type WordStyle = {
  text: string;
  textCase: TextCase;
  size: number;
  letterSpacing: number;
  /** Stroke weight: grows (+) or shrinks (−) the letter outlines, in ems. */
  weight: number;
  depth: number;
  curveSegments: number;
  bevel: boolean;
  bevelThickness: number;
  bevelSize: number;
  bevelSegments: number;
  fill: FillId;
  faceColor: string;
  sideColor: string;
  accentColor: string;
  glow: number;
  /** Outline thickness in CSS pixels (Tron fill and edge lines). */
  lineWidth: number;
  /** Tron body opacity: 1 hides the back lines, 0 is fully see-through. */
  bodyOpacity: number;
  /** Tron: fill the letter interiors with bodyColor (off = black, hiding the back lines). */
  bodyFill: boolean;
  bodyColor: string;
  fxScale: number;
  fxSpeed: number;
  edges: boolean;
  edgeColor: string;
};

export type Layout = "stack" | "row" | "grid" | "cascade" | "ring" | "gallery";
export type Motion = "none" | "sway" | "spin" | "float";

export type SceneSettings = {
  layout: Layout;
  align: "left" | "center" | "right";
  gap: number;
  autoRotate: boolean;
  autoRotateSpeed: number;
  motion: Motion;
  motionSpeed: number;
  bloom: number;
  bloomThreshold: number;
};

export type ParagraphSettings = {
  /** "match" uses the shared font. */
  bodyFont: string;
  headingSize: number;
  headingCase: TextCase;
  headingColor: string;
  size: number;
  lineHeight: number;
  tracking: number;
  color: string;
  measure: number;
  align: "left" | "center" | "justify";
};

export type Target = WordId | "all";

const BASE_STYLE: Omit<WordStyle, "text"> = {
  textCase: "upper",
  size: 1,
  letterSpacing: 0.04,
  weight: 0,
  depth: 0.12,
  curveSegments: 8,
  bevel: false,
  bevelThickness: 0.03,
  bevelSize: 0.02,
  bevelSegments: 3,
  fill: "tron",
  ...FILL_PRESETS.tron,
  glow: 2.5,
  lineWidth: 2,
  bodyOpacity: 1,
  bodyFill: true,
  bodyColor: "#00b8ff",
  fxScale: 1,
  fxSpeed: 0.8,
  edges: false,
  edgeColor: "#66f0f0",
};

const DEFAULT_TEXT: Record<WordId, string> = {
  project: "Project",
  about: "About Me",
  experiences: "Experiences",
  contact: "Contact",
};

export const WORD_LABEL = DEFAULT_TEXT;

const defaultWords = (): Record<WordId, WordStyle> =>
  Object.fromEntries(WORD_IDS.map((id) => [id, { ...BASE_STYLE, text: DEFAULT_TEXT[id] }])) as Record<
    WordId,
    WordStyle
  >;

const DEFAULT_FONT = "orbitron-900";

const DEFAULT_SCENE: SceneSettings = {
  layout: "stack",
  align: "center",
  gap: 0.6,
  autoRotate: false,
  autoRotateSpeed: 0.8,
  motion: "none",
  motionSpeed: 0.6,
  bloom: 1.1,
  bloomThreshold: 0.3,
};

const DEFAULT_PARAGRAPH: ParagraphSettings = {
  bodyFont: "match",
  headingSize: 44,
  headingCase: "upper",
  headingColor: "#e8f6f8",
  size: 17,
  lineHeight: 1.65,
  tracking: 0,
  color: "#b9c7cb",
  measure: 68,
  align: "left",
};

type State = {
  font: string;
  words: Record<WordId, WordStyle>;
  target: Target;
  scene: SceneSettings;
  paragraph: ParagraphSettings;
  setFont: (font: string) => void;
  setTarget: (target: Target) => void;
  /** Applies to the targeted word, or to all four when the target is "all". */
  setWord: (patch: Partial<WordStyle>) => void;
  setScene: (patch: Partial<SceneSettings>) => void;
  setParagraph: (patch: Partial<ParagraphSettings>) => void;
  shuffleFont: () => void;
  shuffleFills: () => void;
  reset: () => void;
  /** UI-only: the 3D view re-centres into the space the panel leaves. */
  panelOpen: boolean;
  setPanelOpen: (open: boolean) => void;
  /** UI-only: bump to snap the camera back to the default framing. */
  viewNonce: number;
  resetView: () => void;
};

const STORAGE_KEY = "text-lab-v7";

type Saved = Pick<State, "font" | "words" | "target" | "scene" | "paragraph">;

function loadSaved(): Partial<Saved> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Partial<Saved>) : {};
  } catch {
    return {};
  }
}

function pickDistinct<T>(pool: readonly T[], n: number): T[] {
  const copy = [...pool];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy.slice(0, n);
}

const saved = loadSaved();
const savedWords = saved.words;

export const useTextLab = create<State>((set) => ({
  font: saved.font ?? DEFAULT_FONT,
  // Merge saved state over defaults so fields added later still get values.
  words: Object.fromEntries(
    WORD_IDS.map((id) => [id, { ...BASE_STYLE, text: DEFAULT_TEXT[id], ...savedWords?.[id] }]),
  ) as Record<WordId, WordStyle>,
  target: saved.target ?? "all",
  scene: { ...DEFAULT_SCENE, ...saved.scene },
  paragraph: { ...DEFAULT_PARAGRAPH, ...saved.paragraph },
  setFont: (font) => set({ font }),
  setTarget: (target) => set({ target }),
  panelOpen: true,
  setPanelOpen: (panelOpen) => set({ panelOpen }),
  viewNonce: 0,
  resetView: () => set((s) => ({ viewNonce: s.viewNonce + 1 })),
  setWord: (patch) =>
    set((s) => {
      const ids = s.target === "all" ? WORD_IDS : [s.target];
      const words = { ...s.words };
      for (const id of ids) words[id] = { ...words[id], ...patch };
      return { words };
    }),
  setScene: (patch) => set((s) => ({ scene: { ...s.scene, ...patch } })),
  setParagraph: (patch) => set((s) => ({ paragraph: { ...s.paragraph, ...patch } })),
  shuffleFont: () => set({ font: pickDistinct(DISPLAY_FONTS, 1)[0].id }),
  shuffleFills: () =>
    set((s) => {
      const fills = pickDistinct(FILLS, WORD_IDS.length);
      const words = { ...s.words };
      WORD_IDS.forEach((id, i) => {
        const fill = fills[i][0];
        words[id] = { ...words[id], fill, ...FILL_PRESETS[fill] };
      });
      return { words };
    }),
  reset: () =>
    set({
      font: DEFAULT_FONT,
      words: defaultWords(),
      target: "all",
      scene: DEFAULT_SCENE,
      paragraph: DEFAULT_PARAGRAPH,
    }),
}));

useTextLab.subscribe((s) => {
  try {
    const data: Saved = { font: s.font, words: s.words, target: s.target, scene: s.scene, paragraph: s.paragraph };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Storage blocked (private window etc.) — settings just won't persist.
  }
});

export function applyCase(text: string, c: TextCase) {
  if (c === "upper") return text.toUpperCase();
  if (c === "lower") return text.toLowerCase();
  return text;
}

export function exportSettings() {
  const { font, words, scene, paragraph } = useTextLab.getState();
  return JSON.stringify({ font, words, scene, paragraph }, null, 2);
}
