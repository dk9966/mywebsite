import { Font } from "three/addons/loaders/FontLoader.js";
import { TTFLoader } from "three/addons/loaders/TTFLoader.js";
import helvetikerBold from "three/examples/fonts/helvetiker_bold.typeface.json?url";
import helvetikerRegular from "three/examples/fonts/helvetiker_regular.typeface.json?url";
import optimerBold from "three/examples/fonts/optimer_bold.typeface.json?url";
import gentilisBold from "three/examples/fonts/gentilis_bold.typeface.json?url";
import droidSansBold from "three/examples/fonts/droid/droid_sans_bold.typeface.json?url";
import droidSerifBold from "three/examples/fonts/droid/droid_serif_bold.typeface.json?url";
import kenpixel from "three/examples/fonts/ttf/kenpixel.ttf?url";

// Font registry for the /text lab. Most faces stream from Fontsource on
// jsDelivr (latin subset WOFF — opentype.js parses WOFF, not WOFF2). The
// public/fonts/station TTFs are subset to the letters of "Projects" only, so
// they can't spell these words and aren't listed.

export type FontCategory = "Tech" | "Display" | "Sans" | "Serif" | "Script" | "Pixel / Mono" | "Body";

export type FontSpec = {
  id: string;
  label: string;
  category: FontCategory;
  /** typeface = three.js JSON (3D only, CSS falls back); outline = TTF/WOFF. */
  kind: "typeface" | "outline" | "system";
  url?: string;
  weight?: number;
  /** CSS fallback stack, also the whole family for system fonts. */
  fallback: string;
  /** Body-only faces stay out of the 3D font menu. */
  bodyOnly?: boolean;
};

const fs = (
  slug: string,
  label: string,
  category: FontCategory,
  weight = 400,
  fallback = "system-ui, sans-serif",
  bodyOnly = false,
): FontSpec => ({
  id: `${slug}-${weight}`,
  label,
  category,
  kind: "outline",
  url: `https://cdn.jsdelivr.net/fontsource/fonts/${slug}@latest/latin-${weight}-normal.woff`,
  weight,
  fallback,
  bodyOnly,
});

const SERIF = "Georgia, 'Times New Roman', serif";
const MONO = "ui-monospace, 'SF Mono', Menlo, monospace";

export const FONTS: FontSpec[] = [
  // Tech / sci-fi
  fs("orbitron", "Orbitron Black", "Tech", 900),
  fs("orbitron", "Orbitron Medium", "Tech", 500),
  fs("audiowide", "Audiowide", "Tech"),
  fs("bruno-ace-sc", "Bruno Ace SC", "Tech"),
  fs("michroma", "Michroma", "Tech"),
  fs("syncopate", "Syncopate Bold", "Tech", 700),
  fs("oxanium", "Oxanium Bold", "Tech", 700),
  fs("exo-2", "Exo 2 ExtraBold", "Tech", 800),
  fs("russo-one", "Russo One", "Tech"),
  fs("quantico", "Quantico Bold", "Tech", 700),
  fs("tektur", "Tektur Bold", "Tech", 700),
  fs("rajdhani", "Rajdhani Bold", "Tech", 700),
  fs("chakra-petch", "Chakra Petch Bold", "Tech", 700),
  fs("unica-one", "Unica One", "Tech"),
  fs("megrim", "Megrim", "Tech"),
  fs("teko", "Teko SemiBold", "Tech", 600),
  fs("major-mono-display", "Major Mono Display", "Tech", 400, MONO),
  // Display
  fs("bungee", "Bungee", "Display"),
  fs("bungee-outline", "Bungee Outline", "Display"),
  fs("bungee-shade", "Bungee Shade", "Display"),
  fs("monoton", "Monoton", "Display"),
  fs("righteous", "Righteous", "Display"),
  fs("rubik-mono-one", "Rubik Mono One", "Display"),
  fs("rubik-glitch", "Rubik Glitch", "Display"),
  fs("unbounded", "Unbounded Bold", "Display", 700),
  fs("syne", "Syne ExtraBold", "Display", 800),
  fs("archivo-black", "Archivo Black", "Display"),
  fs("anton", "Anton", "Display"),
  fs("bebas-neue", "Bebas Neue", "Display"),
  // Sans
  fs("inter", "Inter ExtraBold", "Sans", 800),
  fs("inter", "Inter Light", "Sans", 300),
  fs("space-grotesk", "Space Grotesk Bold", "Sans", 700),
  { id: "helvetiker-bold", label: "Helvetiker Bold", category: "Sans", kind: "typeface", url: helvetikerBold, fallback: "Helvetica, Arial, sans-serif" },
  { id: "helvetiker-regular", label: "Helvetiker", category: "Sans", kind: "typeface", url: helvetikerRegular, fallback: "Helvetica, Arial, sans-serif" },
  { id: "droid-sans-bold", label: "Droid Sans Bold", category: "Sans", kind: "typeface", url: droidSansBold, fallback: "system-ui, sans-serif" },
  // Serif
  fs("playfair-display", "Playfair Display Bold", "Serif", 700, SERIF),
  fs("cinzel", "Cinzel Bold", "Serif", 700, SERIF),
  fs("abril-fatface", "Abril Fatface", "Serif", 400, SERIF),
  fs("dm-serif-display", "DM Serif Display", "Serif", 400, SERIF),
  fs("bodoni-moda", "Bodoni Moda Bold", "Serif", 700, SERIF),
  fs("fraunces", "Fraunces Black", "Serif", 900, SERIF),
  { id: "optimer-bold", label: "Optimer Bold", category: "Serif", kind: "typeface", url: optimerBold, fallback: "Optima, Candara, sans-serif" },
  { id: "gentilis-bold", label: "Gentilis Bold", category: "Serif", kind: "typeface", url: gentilisBold, fallback: SERIF },
  { id: "droid-serif-bold", label: "Droid Serif Bold", category: "Serif", kind: "typeface", url: droidSerifBold, fallback: SERIF },
  // Script
  fs("pacifico", "Pacifico", "Script", 400, "cursive"),
  fs("lobster", "Lobster", "Script", 400, "cursive"),
  // Pixel / mono
  fs("press-start-2p", "Press Start 2P", "Pixel / Mono", 400, MONO),
  fs("silkscreen", "Silkscreen", "Pixel / Mono", 400, MONO),
  fs("doto", "Doto Bold", "Pixel / Mono", 700, MONO),
  fs("sixtyfour", "Sixtyfour", "Pixel / Mono", 400, MONO),
  fs("space-mono", "Space Mono Bold", "Pixel / Mono", 700, MONO),
  { id: "vt323", label: "VT323", category: "Pixel / Mono", kind: "outline", url: "/fonts/VT323-Regular.ttf", fallback: MONO },
  { id: "jetbrains-mono", label: "JetBrains Mono", category: "Pixel / Mono", kind: "outline", url: "/fonts/JetBrainsMono-Regular.ttf", fallback: MONO },
  { id: "jetbrains-mono-thin", label: "JetBrains Mono Thin", category: "Pixel / Mono", kind: "outline", url: "/fonts/JetBrainsMono-Thin.ttf", weight: 100, fallback: MONO },
  { id: "kenpixel", label: "Kenpixel", category: "Pixel / Mono", kind: "outline", url: kenpixel, fallback: MONO },
  // Body faces for the paragraph section.
  fs("inter", "Inter", "Body", 400, "system-ui, sans-serif", true),
  fs("ibm-plex-sans", "IBM Plex Sans", "Body", 400, "system-ui, sans-serif", true),
  fs("dm-sans", "DM Sans", "Body", 400, "system-ui, sans-serif", true),
  fs("manrope", "Manrope", "Body", 400, "system-ui, sans-serif", true),
  fs("source-serif-4", "Source Serif 4", "Body", 400, SERIF, true),
  fs("lora", "Lora", "Body", 400, SERIF, true),
  fs("eb-garamond", "EB Garamond", "Body", 400, SERIF, true),
  fs("newsreader", "Newsreader", "Body", 400, SERIF, true),
  fs("space-mono", "Space Mono", "Body", 400, MONO, true),
  { id: "system-sans", label: "System Sans", category: "Body", kind: "system", fallback: "system-ui, -apple-system, 'Segoe UI', sans-serif", bodyOnly: true },
  { id: "system-serif", label: "System Serif", category: "Body", kind: "system", fallback: SERIF, bodyOnly: true },
  { id: "system-mono", label: "System Mono", category: "Body", kind: "system", fallback: MONO, bodyOnly: true },
];

export const FONT_BY_ID = new Map(FONTS.map((f) => [f.id, f]));
export const DISPLAY_FONTS = FONTS.filter((f) => !f.bodyOnly);

export function fontLabel(id: string) {
  return FONT_BY_ID.get(id)?.label ?? id;
}

// 3D glyph data ---------------------------------------------------------------

const fontCache = new Map<string, Promise<Font>>();
const ttfLoader = new TTFLoader();

export function loadFont(id: string): Promise<Font> {
  let promise = fontCache.get(id);
  if (promise) return promise;
  const spec = FONT_BY_ID.get(id);
  if (!spec?.url || spec.kind === "system") {
    return Promise.reject(new Error(`No 3D outlines for font ${id}`));
  }
  const url = spec.url;
  promise = (async () => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} loading ${url}`);
    if (spec.kind === "typeface") return new Font(await res.json());
    return new Font(ttfLoader.parse(await res.arrayBuffer()));
  })();
  promise.catch(() => fontCache.delete(id));
  fontCache.set(id, promise);
  return promise;
}

// three's Font has no letter-spacing option; widen every glyph's advance
// instead. Spacing is in ems so it reads the same at every size.
const spacedCache = new WeakMap<Font, Map<number, Font>>();

export function withLetterSpacing(font: Font, em: number): Font {
  if (em === 0) return font;
  let byEm = spacedCache.get(font);
  if (!byEm) spacedCache.set(font, (byEm = new Map()));
  const hit = byEm.get(em);
  if (hit) return hit;
  const data = font.data as { resolution: number; glyphs: Record<string, { ha: number }> };
  const extra = em * data.resolution;
  const glyphs = Object.fromEntries(
    Object.entries(data.glyphs).map(([ch, g]) => [ch, { ...g, ha: g.ha + extra }]),
  );
  const spaced = new Font({ ...data, glyphs } as typeof font.data);
  byEm.set(em, spaced);
  return spaced;
}

/** Drop characters the font has no glyph for (three throws on them). */
export function printable(font: Font, text: string) {
  const glyphs = (font.data as { glyphs: Record<string, unknown> }).glyphs;
  return [...text].filter((ch) => ch === "\n" || glyphs[ch]).join("");
}

// CSS faces for the paragraph section ----------------------------------------

const cssLoaded = new Set<string>();

/** Registers the face with document.fonts on first use; returns a CSS family. */
export function cssFontFamily(id: string): string {
  const spec = FONT_BY_ID.get(id);
  if (!spec) return "system-ui, sans-serif";
  if (spec.kind !== "outline" || !spec.url) return spec.fallback;
  const family = `tl-${spec.id}`;
  if (!cssLoaded.has(family) && typeof FontFace !== "undefined") {
    cssLoaded.add(family);
    const face = new FontFace(family, `url(${spec.url})`, {
      weight: String(spec.weight ?? 400),
    });
    document.fonts.add(face);
    face.load().catch(() => cssLoaded.delete(family));
  }
  return `"${family}", ${spec.fallback}`;
}
