import { create } from "zustand";

export const STATION_FONTS = [
  { name: "Chakra Petch", file: "chakra-petch", weight: 500, vibe: "Squared / industrial" },
  { name: "Michroma", file: "michroma", weight: 400, vibe: "Extended / aerospace" },
  { name: "Syncopate", file: "syncopate", weight: 400, vibe: "Wide / minimal geometry" },
  { name: "Space Grotesk", file: "space-grotesk", weight: 500, vibe: "Clean / modern technical" },
  { name: "Major Mono Display", file: "major-mono-display", weight: 400, vibe: "Monospaced / experimental" },
  { name: "Megrim", file: "megrim", weight: 400, vibe: "Linear / avant-garde" },
  { name: "Doto", file: "doto", weight: 600, vibe: "Dot matrix / digital" },
  { name: "Teko", file: "teko", weight: 400, vibe: "Tall / condensed" },
  { name: "Bruno Ace SC", file: "bruno-ace-sc", weight: 400, vibe: "Sculpted / futuristic" },
  { name: "Unica One", file: "unica-one", weight: 400, vibe: "Narrow / architectural" },
] as const;

export const STATION_STYLES = ["Solid", "Hollow", "Scanline"] as const;

const STORAGE_KEY = "station-projects-font";
function initialFont() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return Math.max(0, STATION_FONTS.findIndex((font) => font.name === saved));
  } catch { return 0; }
}

function initialStyle() {
  try {
    const saved = localStorage.getItem(`${STORAGE_KEY}-style`);
    const index = STATION_STYLES.findIndex((style) => style === saved);
    return index < 0 ? 1 : index;
  } catch { return 1; }
}

export const useStationFont = create<{
  index: number;
  styleIndex: number;
  cycleFont: (direction: -1 | 1) => void;
  cycleStyle: (direction: -1 | 1) => void;
}>((set) => ({
  index: initialFont(),
  styleIndex: initialStyle(),
  cycleFont: (direction) => set((state) => {
    const index = (state.index + direction + STATION_FONTS.length) % STATION_FONTS.length;
    try { localStorage.setItem(STORAGE_KEY, STATION_FONTS[index].name); } catch { /* Storage is optional. */ }
    return { index };
  }),
  cycleStyle: (direction) => set((state) => {
    const styleIndex = (state.styleIndex + direction + STATION_STYLES.length) % STATION_STYLES.length;
    try { localStorage.setItem(`${STORAGE_KEY}-style`, STATION_STYLES[styleIndex]); } catch { /* Storage is optional. */ }
    return { styleIndex };
  }),
}));

const fontLoads = new Map<string, Promise<FontFace>>();
export function loadStationFont(font: typeof STATION_FONTS[number]) {
  let load = fontLoads.get(font.name);
  if (!load) {
    const face = new FontFace(`Station ${font.name}`, `url(/fonts/station/${font.file}.ttf)`, {
      weight: String(font.weight),
    });
    load = face.load().then((loaded) => {
      document.fonts.add(loaded);
      return loaded;
    });
    void load.catch(() => fontLoads.delete(font.name));
    fontLoads.set(font.name, load);
  }
  return load;
}
