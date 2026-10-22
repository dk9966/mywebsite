/**
 * 16×16 Minecraft-style block textures, generated in code so the voxel box
 * needs no texture pack. Each recipe is a palette plus a pattern; a seeded
 * hash keeps every block identical between page loads.
 */
type Recipe = {
  palette: string[];
  pattern?: "noise" | "ore" | "log-side" | "log-top" | "planks" | "grass-side" | "leaves" | "lamp" | "plant" | "orchid";
  ore?: string[];
  seed: number;
  /** Light-emitting block: keeps full brightness under the exposure scale. */
  glow?: boolean;
};

function rand(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const cache = new Map<string, string>();
const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toSrgb = (c: number) => (c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055);

/** `exposure` scales the albedo in linear light; lamp blocks use `glowExposure`. */
export function blockTexture(recipe: Recipe, exposure = 1, glowExposure = 1): string {
  const scale = recipe.glow ? glowExposure : exposure;
  const key = `${recipe.seed}:${scale}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 16;
  // Read back below (exposure scaling): a CPU canvas avoids a GPU readback per texture.
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  const r = rand(recipe.seed);
  const pick = (palette: string[]) => palette[Math.floor(r() * palette.length)];
  const px = (x: number, y: number, c: string) => {
    ctx.fillStyle = c;
    ctx.fillRect(x, y, 1, 1);
  };
  const p = recipe.palette;
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) px(x, y, pick(p));

  switch (recipe.pattern) {
    case "ore":
      for (let i = 0; i < 5; i++) {
        const cx = 2 + Math.floor(r() * 12);
        const cy = 2 + Math.floor(r() * 12);
        for (let j = 0; j < 4; j++) px(cx + Math.floor(r() * 3) - 1, cy + Math.floor(r() * 3) - 1, pick(recipe.ore!));
      }
      break;
    case "grass-side":
      for (let x = 0; x < 16; x++) {
        const depth = 3 + Math.floor(r() * 3);
        for (let y = 0; y < depth; y++) px(x, y, pick(recipe.ore!));
      }
      break;
    case "log-side":
      for (let x = 0; x < 16; x += 4) for (let y = 0; y < 16; y++) if (r() < 0.6) px(x + Math.floor(r() * 2), y, p[0]);
      break;
    case "log-top":
      for (let y = 0; y < 16; y++)
        for (let x = 0; x < 16; x++) {
          const d = Math.max(Math.abs(x - 7.5), Math.abs(y - 7.5));
          px(x, y, d > 6.5 ? p[0] : Math.floor(d) % 2 ? recipe.ore![0] : recipe.ore![1]);
        }
      break;
    case "planks":
      for (let y = 0; y < 16; y += 4) for (let x = 0; x < 16; x++) px(x, y + 3, p[0]);
      for (let y = 0; y < 16; y += 4) px((y * 5 + 3) % 16, y + 1, p[0]);
      break;
    case "leaves":
      ctx.clearRect(0, 0, 16, 16);
      for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) if (r() < 0.78) px(x, y, pick(p));
      break;
    case "lamp":
      for (let y = 0; y < 16; y++)
        for (let x = 0; x < 16; x++) {
          const edge = x === 0 || y === 0 || x === 15 || y === 15 || ((x === 7 || x === 8) && (y === 7 || y === 8));
          if (edge) px(x, y, recipe.ore![0]);
        }
      break;
    case "plant":
    case "orchid": {
      ctx.clearRect(0, 0, 16, 16);
      for (let i = 0; i < 9; i++) {
        let x = 2 + Math.floor(r() * 12);
        const h = 5 + Math.floor(r() * 9);
        for (let y = 15; y > 15 - h; y--) {
          px(x, y, pick(p));
          if (r() < 0.25) x = Math.min(15, Math.max(0, x + (r() < 0.5 ? -1 : 1)));
        }
        if (recipe.pattern === "orchid") {
          px(x, 15 - h, pick(recipe.ore!));
          px(x + 1, 15 - h, pick(recipe.ore!));
          px(x, 14 - h, pick(recipe.ore!));
        }
      }
      break;
    }
  }
  if (scale !== 1) {
    const image = ctx.getImageData(0, 0, 16, 16);
    for (let i = 0; i < image.data.length; i += 4) {
      for (let c = 0; c < 3; c++) {
        image.data[i + c] = Math.round(toSrgb(toLinear(image.data[i + c] / 255) * scale) * 255);
      }
    }
    ctx.putImageData(image, 0, 0);
  }
  const url = canvas.toDataURL();
  cache.set(key, url);
  return url;
}

const STONE = ["#5d5f63", "#6c6e72", "#787a7e", "#636569", "#56585c"];
const DEEPSLATE = ["#3a3a40", "#45454b", "#2f2f35", "#4d4d53"];
const DIRT = ["#6b4a32", "#7a5638", "#5e402b", "#86603f"];
const GRASS = ["#5f8f3a", "#6a9c40", "#567f34", "#73a646"];
const MOSS = ["#4f7a2a", "#5a8a30", "#466b25", "#628f36"];

/** Face groups: "all", or comma-separated Voxelize face names. */
export const BLOCK_TEXTURES: Record<string, Record<string, Recipe>> = {
  Stone: { all: { palette: STONE, seed: 1 } },
  Deepslate: { all: { palette: DEEPSLATE, seed: 2 } },
  Cobblestone: { all: { palette: ["#545454", "#6e6e6e", "#7f7f7f", "#3f3f3f", "#626262"], seed: 3 } },
  Dirt: { all: { palette: DIRT, seed: 4 } },
  "Grass Block": {
    all: { palette: DIRT, pattern: "grass-side", ore: GRASS, seed: 5 },
    py: { palette: GRASS, seed: 6 },
    ny: { palette: DIRT, seed: 7 },
  },
  "Moss Block": { all: { palette: MOSS, seed: 8 } },
  "Coal Ore": { all: { palette: STONE, pattern: "ore", ore: ["#1c1c1c", "#2b2b2b"], seed: 9 } },
  "Iron Ore": { all: { palette: STONE, pattern: "ore", ore: ["#d8af93", "#c49a7e", "#e6c4aa"], seed: 10 } },
  "Diamond Ore": { all: { palette: STONE, pattern: "ore", ore: ["#5decf5", "#2fc9d4", "#a5f7fb"], seed: 11 } },
  "Oak Log": {
    all: { palette: ["#3d2c19", "#5a4024", "#674a2b", "#4e3820"], pattern: "log-side", seed: 12 },
    "py,ny": { palette: ["#5a4024"], pattern: "log-top", ore: ["#9c7a48", "#b48e57"], seed: 13 },
  },
  "Oak Leaves": { all: { palette: ["#3f7a24", "#356a1e", "#4a8a2b", "#2d5c19"], pattern: "leaves", seed: 14 } },
  "Oak Planks": { all: { palette: ["#7a5d34", "#a2824e", "#ae8d57", "#9a7a46", "#b8975f"], pattern: "planks", seed: 15 } },
  "Sea Lantern": { all: { palette: ["#cfe6ee", "#e2f2f6", "#b8d6e0", "#f2fbfd"], pattern: "lamp", ore: ["#86aebd"], seed: 16, glow: true } },
  Glowstone: { all: { palette: ["#ffd88a", "#e8b860", "#fbe7a8", "#c9934a", "#ffcf6e"], seed: 17, glow: true } },
  "Short Grass": { all: { palette: GRASS, pattern: "plant", seed: 18 } },
  "Blue Orchid": { all: { palette: ["#3f7a24", "#4a8a2b"], pattern: "orchid", ore: ["#2fa8e6", "#5ec4f2"], seed: 19 } },
};
