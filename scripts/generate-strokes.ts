import { createCanvas } from 'canvas';
import * as opentype from 'opentype.js';
import TraceSkeleton from 'skeleton-tracing-js';
import { writeFileSync, readFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

const FONT_PATH = resolve(ROOT, 'public/fonts/JetBrainsMono-Regular.ttf');
const OUTPUT_JSON = resolve(ROOT, 'src/data/strokeData.json');
const OUTPUT_DIR = resolve(ROOT, 'public/drainmaps');

const RENDER_SIZE = 200;
const PADDING = 20;
const STROKE_SPREAD = 0.35;
const STROKE_DRAIN = 0.65;

function getUniqueChars(): string[] {
  const src = readFileSync(resolve(ROOT, 'src/data/terminal.ts'), 'utf-8');
  const chars = new Set<string>();
  for (const match of src.matchAll(/text:\s*'([^']*)'/g)) {
    for (const c of match[1]) {
      if (c !== ' ') chars.add(c);
    }
  }
  chars.add('>');
  return Array.from(chars).sort();
}

function renderGlyph(font: opentype.Font, char: string) {
  const fontSize = RENDER_SIZE - PADDING * 2;
  const glyph = font.charToGlyph(char);
  const scale = fontSize / font.unitsPerEm;
  const advance = glyph.advanceWidth * scale;
  const w = Math.ceil(advance + PADDING * 2);
  const h = RENDER_SIZE;

  const canvas = createCanvas(w, h);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, w, h);

  const path = glyph.getPath(PADDING, RENDER_SIZE - PADDING - 10, fontSize);
  ctx.beginPath();
  for (const cmd of path.commands) {
    switch (cmd.type) {
      case 'M': ctx.moveTo(cmd.x, cmd.y); break;
      case 'L': ctx.lineTo(cmd.x, cmd.y); break;
      case 'Q': ctx.quadraticCurveTo(cmd.x1, cmd.y1, cmd.x, cmd.y); break;
      case 'C': ctx.bezierCurveTo(cmd.x1, cmd.y1, cmd.x2!, cmd.y2!, cmd.x, cmd.y); break;
      case 'Z': ctx.closePath(); break;
    }
  }
  ctx.fillStyle = '#fff';
  ctx.fill();

  const imageData = ctx.getImageData(0, 0, w, h);
  const mask = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) {
    mask[i] = imageData.data[i * 4] > 128 ? 1 : 0;
  }

  return { mask, w, h, advance: advance / w };
}

interface PreparedStroke {
  points: [number, number][];
  cumDists: number[];
  delay: number;
}

function traceAndPrepare(mask: Uint8Array, w: number, h: number): PreparedStroke[] {
  const intArr = Array.from(mask).map((v) => (v ? 1 : 0));
  const result = TraceSkeleton.fromBoolArray(intArr, w, h);

  let polylines = result.polylines
    .filter((pl: number[][]) => pl.length >= 2)
    .map((pl: number[][]) => {
      const pts = pl.map(([x, y]: number[]) => [x / w, y / h] as [number, number]);
      if (pts[0][1] > pts[pts.length - 1][1]) pts.reverse();
      return pts;
    });

  if (polylines.length === 0) {
    let cx = 0.5, cy = 0.5;
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++)
        if (mask[y * w + x]) { cx = x / w; cy = y / h; break; }
    polylines = [[[cx - 0.01, cy] as [number, number], [cx + 0.01, cy] as [number, number]]];
  }

  const sorted = [...polylines].sort(
    (a, b) => Math.min(...a.map(([, y]: [number, number]) => y)) - Math.min(...b.map(([, y]: [number, number]) => y)),
  );

  return sorted.map((pts, si) => {
    const cumDists = [0];
    for (let i = 1; i < pts.length; i++) {
      const dx = pts[i][0] - pts[i - 1][0];
      const dy = pts[i][1] - pts[i - 1][1];
      cumDists.push(cumDists[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    const total = cumDists[cumDists.length - 1] || 1;
    for (let i = 0; i < cumDists.length; i++) cumDists[i] /= total;

    const delay = sorted.length > 1
      ? (si / (sorted.length - 1)) * STROKE_SPREAD
      : 0;

    return { points: pts, cumDists, delay };
  });
}

function computeDrainMap(
  mask: Uint8Array,
  w: number,
  h: number,
  strokes: PreparedStroke[],
): Uint8Array {
  const drainMap = new Uint8Array(w * h);
  const rawTimes = new Float32Array(w * h);
  let maxTime = 0;

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = y * w + x;
      if (!mask[idx]) continue;

      const nx = x / w;
      const ny = y / h;

      let bestDist = Infinity;
      let bestTime = 0;

      for (const stroke of strokes) {
        for (let i = 0; i < stroke.points.length; i++) {
          const dx = nx - stroke.points[i][0];
          const dy = ny - stroke.points[i][1];
          const d = dx * dx + dy * dy;
          if (d < bestDist) {
            bestDist = d;
            bestTime = stroke.delay + stroke.cumDists[i] * STROKE_DRAIN;
          }
        }
      }

      rawTimes[idx] = bestTime;
      if (bestTime > maxTime) maxTime = bestTime;
    }
  }

  for (let i = 0; i < w * h; i++) {
    if (mask[i]) {
      drainMap[i] = Math.round((rawTimes[i] / (maxTime || 1)) * 255);
    }
  }

  return drainMap;
}

function saveDrainMapPng(
  drainMap: Uint8Array,
  mask: Uint8Array,
  w: number,
  h: number,
  filePath: string,
) {
  const canvas = createCanvas(w, h);
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(w, h);

  for (let i = 0; i < w * h; i++) {
    img.data[i * 4 + 0] = drainMap[i];
    img.data[i * 4 + 1] = drainMap[i];
    img.data[i * 4 + 2] = drainMap[i];
    img.data[i * 4 + 3] = mask[i] ? 255 : 0;
  }

  ctx.putImageData(img, 0, 0);
  writeFileSync(filePath, canvas.toBuffer('image/png'));
}

function main() {
  mkdirSync(OUTPUT_DIR, { recursive: true });

  console.log('Loading font...');
  const fontBuffer = readFileSync(FONT_PATH);
  const font = opentype.parse(fontBuffer.buffer as ArrayBuffer);

  const chars = getUniqueChars();
  console.log(`Processing ${chars.length} unique characters: ${chars.join('')}`);

  const jsonData: Record<string, { drainMap: string; advance: number; renderW: number; renderH: number }> = {};

  for (const char of chars) {
    const { mask, w, h, advance } = renderGlyph(font, char);
    const strokes = traceAndPrepare(mask, w, h);
    const drainMap = computeDrainMap(mask, w, h, strokes);

    const code = char.charCodeAt(0);
    const filename = `${code}.png`;
    saveDrainMapPng(drainMap, mask, w, h, resolve(OUTPUT_DIR, filename));

    jsonData[char] = {
      drainMap: `/drainmaps/${filename}`,
      advance,
      renderW: w,
      renderH: h,
    };

    console.log(`  '${char}' -> ${strokes.length} strokes, drain map ${w}x${h}`);
  }

  writeFileSync(OUTPUT_JSON, JSON.stringify(jsonData, null, 2));
  console.log(`\nWrote ${OUTPUT_JSON}`);
  console.log(`Drain map PNGs in ${OUTPUT_DIR}/`);
}

main();
