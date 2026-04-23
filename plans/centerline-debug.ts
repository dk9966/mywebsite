import { load, type Font } from "opentype.js";
import {
  clearCenterlineCache,
  getCenterlineDrain,
  planLiquidDrain,
  type Stroke,
} from "../src/lib/centerline";
import { SECTIONS } from "../src/lib/debugCharset";

interface FontEntry {
  label: string;
  url: string;
  font?: Font;
}

const FONTS: FontEntry[] = [
  { label: "VT323", url: "/fonts/VT323-Regular.ttf" },
  { label: "JetBrainsMono", url: "/fonts/JetBrainsMono-Regular.ttf" },
];

const STROKE_PALETTE = [
  "#00dffc",
  "#ff6b6b",
  "#ffd93d",
  "#6bff8a",
  "#c084fc",
  "#fb923c",
  "#22d3ee",
  "#f472b6",
];

const COLUMNS = [
  "pure",
  "skeleton",
  "overlay",
  "per-stroke",
  "drain plan",
  "rendered",
  "meta",
] as const;

/**
 * Mirror of DrainText's render-time constants. The "rendered" column shows
 * each glyph as production does at timeline t=0: filled outline masked by
 * the same white base + black dashed eraser strokes (see DrainText.tsx).
 * That matches the "pure" fill visually, modulo dropped strokes in the mask.
 */
const RENDER_FONT_SIZE = 120;
const RENDER_STROKE_COLOR = "#00dffc";
const RENDER_STROKE_WIDTH_PX = 4;
/** Same as DrainText — mask eraser stroke width in pixels. */
const ERASER_WIDTH_PX = 28;

let debugMaskIdSeq = 0;
function nextMaskId(): string {
  return `cl-dbg-mask-${debugMaskIdSeq++}`;
}

function loadFont(entry: FontEntry): Promise<Font> {
  return new Promise((resolve, reject) => {
    load(entry.url, (err, f) => {
      if (err || !f) reject(err ?? new Error("font load failed: " + entry.url));
      else resolve(f);
    });
  });
}

/**
 * opentype.js's `glyph.path` is in typographic coords (Y up). SVG is Y down,
 * so wrap content in a flip group and shift the viewBox to match.
 */
function svg(viewBox: string, inner: string, extraAttrs = ""): string {
  return `<svg viewBox="${viewBox}" xmlns="http://www.w3.org/2000/svg" ${extraAttrs}><g transform="scale(1 -1)">${inner}</g></svg>`;
}

function strokesToPathD(strokes: Stroke[]): string[] {
  return strokes.map((stroke) => {
    if (stroke.length === 0) return "";
    const [first, ...rest] = stroke;
    const parts = [`M${first[0]} ${first[1]}`];
    for (const p of rest) parts.push(`L${p[0]} ${p[1]}`);
    return parts.join(" ");
  });
}

function buildCells(
  font: Font,
  char: string,
): { html: string[]; ms: number; strokeCount: number } {
  const glyph = font.charToGlyph(char);
  const { extract, plan } = getCenterlineDrain(font, char);
  const { strokes, bbox, elapsedMs } = extract;

  const bw = bbox.x2 - bbox.x1;
  const bh = bbox.y2 - bbox.y1;
  const pad = font.unitsPerEm * 0.05;
  const vbW = Math.max(bw, font.unitsPerEm * 0.4) + pad * 2;
  const vbH = Math.max(bh, font.unitsPerEm * 0.6) + pad * 2;
  const vbX = bbox.x1 - (vbW - bw) / 2;
  // After the scale(1 -1) flip, Y range becomes [-bbox.y2, -bbox.y1].
  const vbY = -bbox.y2 - (vbH - bh) / 2;
  const viewBox = `${vbX} ${vbY} ${vbW} ${vbH}`;

  const glyphPathD = glyph.path.toPathData(2);
  const strokeWidth = font.unitsPerEm * 0.025;
  const strokePaths = strokesToPathD(strokes);

  const pure = svg(
    viewBox,
    `<path d="${glyphPathD}" fill="#00dffc" fill-rule="evenodd"/>`,
  );

  const skeleton = svg(
    viewBox,
    strokePaths
      .map(
        (d) =>
          `<path d="${d}" stroke="#00dffc" stroke-width="${strokeWidth}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
      )
      .join(""),
  );

  const overlay = svg(
    viewBox,
    `<path d="${glyphPathD}" fill="#00dffc" fill-rule="evenodd" opacity="0.3"/>` +
      strokePaths
        .map(
          (d) =>
            `<path d="${d}" stroke="#ff4d4d" stroke-width="${strokeWidth}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
        )
        .join("") +
      strokes
        .flatMap((s) => [s[0], s[s.length - 1]])
        .map(
          (p) =>
            `<circle cx="${p[0]}" cy="${p[1]}" r="${strokeWidth * 1.2}" fill="#ff4d4d"/>`,
        )
        .join(""),
  );

  const perStroke = svg(
    viewBox,
    strokePaths
      .map(
        (d, i) =>
          `<path d="${d}" stroke="${STROKE_PALETTE[i % STROKE_PALETTE.length]}" stroke-width="${strokeWidth}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
      )
      .join(""),
  );

  const drainSvg = renderDrainPlan(plan, viewBox, strokeWidth);

  const {
    svg: renderedSvg,
    kept,
    dropped,
  } = renderProduction(plan, font, viewBox, glyphPathD, nextMaskId());

  const totalLen = strokes.reduce((sum, s) => sum + polylineLen(s), 0);
  const totalLenEm = (totalLen / font.unitsPerEm).toFixed(2);
  const dmaxEm = (plan.totalDistance / font.unitsPerEm).toFixed(2);

  const warnClass = strokes.length === 0 ? "err" : elapsedMs > 50 ? "warn" : "";
  const dropClass = dropped > 0 ? "warn" : "";

  const meta = `
    <b>${strokes.length}</b> stroke${strokes.length === 1 ? "" : "s"}<br/>
    rendered <b>${kept}</b><span class="${dropClass}"> -${dropped}</span><br/>
    len <b>${totalLenEm}</b> em<br/>
    Dmax <b>${dmaxEm}</b> em<br/>
    <span class="${warnClass}">${elapsedMs.toFixed(1)} ms</span>
  `;

  return {
    html: [
      `<div class="cell">${pure}</div>`,
      `<div class="cell">${skeleton}</div>`,
      `<div class="cell">${overlay}</div>`,
      `<div class="cell">${perStroke}</div>`,
      `<div class="cell">${drainSvg}</div>`,
      `<div class="cell">${renderedSvg}</div>`,
      `<div class="cell meta">${meta}</div>`,
    ],
    ms: elapsedMs,
    strokeCount: strokes.length,
  };
}

/**
 * Filled glyph + SVG mask matching DrainText's initial frame: white
 * `fillD`, black dashed eraser paths with width ERASER_WIDTH in px mapped
 * to glyph units, dashoffset = length + 2*eraser so nothing is erased yet.
 * Strokes with pixelLength < STROKE_WIDTH are omitted from the mask like
 * production.
 */
function renderProduction(
  plan: ReturnType<typeof planLiquidDrain>,
  font: Font,
  viewBox: string,
  glyphPathD: string,
  maskId: string,
): { svg: string; kept: number; dropped: number } {
  const fontScale = RENDER_FONT_SIZE / font.unitsPerEm;
  const minLenGlyph = RENDER_STROKE_WIDTH_PX / fontScale;
  const eraserGlyph = ERASER_WIDTH_PX / fontScale;

  let kept = 0;
  let dropped = 0;
  const erasers: string[] = [];
  for (const ds of plan.strokes) {
    if (ds.length < minLenGlyph) {
      dropped++;
      continue;
    }
    kept++;
    const d = strokeToPathD(ds.points);
    if (!d) continue;
    const dasharray = `${ds.length} ${ds.length + eraserGlyph * 4}`;
    const dashoffset = ds.length + eraserGlyph * 2;
    erasers.push(
      `<path d="${d}" fill="none" stroke="black" stroke-width="${eraserGlyph}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="${dasharray}" stroke-dashoffset="${dashoffset}"/>`,
    );
  }

  const inner =
    `<defs><mask id="${maskId}" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse">` +
    `<path fill="white" fill-rule="evenodd" d="${glyphPathD}"/>` +
    erasers.join("") +
    `</mask></defs>` +
    `<path fill="${RENDER_STROKE_COLOR}" fill-rule="evenodd" d="${glyphPathD}" mask="url(#${maskId})"/>`;

  return { svg: svg(viewBox, inner), kept, dropped };
}

/**
 * Color each drain stroke by tStart on a blue (drains first) -> red
 * (drains last) HSL ramp. NEAR endpoint gets a small filled marker;
 * the chosen drain hole gets an open ring.
 */
function renderDrainPlan(
  plan: ReturnType<typeof planLiquidDrain>,
  viewBox: string,
  strokeWidth: number,
): string {
  if (plan.strokes.length === 0) return svg(viewBox, "");

  const strokePieces: string[] = [];
  const markerPieces: string[] = [];

  for (const ds of plan.strokes) {
    const d = strokeToPathD(ds.points);
    if (!d) continue;
    const hue = 240 - 240 * ds.tStart;
    const color = `hsl(${hue.toFixed(0)} 80% 55%)`;
    strokePieces.push(
      `<path d="${d}" stroke="${color}" stroke-width="${strokeWidth}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
    );
    const near = ds.points[ds.points.length - 1];
    markerPieces.push(
      `<circle cx="${near[0]}" cy="${near[1]}" r="${strokeWidth * 0.9}" fill="${color}"/>`,
    );
  }

  const [hx, hy] = plan.hole;
  const holeMarker = `<circle cx="${hx}" cy="${hy}" r="${strokeWidth * 2.2}" fill="none" stroke="#fff" stroke-width="${strokeWidth * 0.6}"/>`;

  return svg(
    viewBox,
    strokePieces.join("") + markerPieces.join("") + holeMarker,
  );
}

function strokeToPathD(stroke: Stroke): string {
  if (stroke.length === 0) return "";
  const [first, ...rest] = stroke;
  const parts = [`M${first[0]} ${first[1]}`];
  for (const p of rest) parts.push(`L${p[0]} ${p[1]}`);
  return parts.join(" ");
}

function polylineLen(pts: Stroke): number {
  let len = 0;
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0];
    const dy = pts[i][1] - pts[i - 1][1];
    len += Math.hypot(dx, dy);
  }
  return len;
}

function escapeChar(ch: string): string {
  if (ch === "<") return "&lt;";
  if (ch === ">") return "&gt;";
  if (ch === "&") return "&amp;";
  if (ch === '"') return "&quot;";
  return ch;
}

function renderGrid(font: Font): string {
  const headerRow = `
    <div class="grid-header">
      <div></div>
      ${COLUMNS.map((c) => `<div>${c}</div>`).join("")}
    </div>
  `;

  const sections = SECTIONS.map((section) => {
    const rows = section.chars
      .map((ch) => {
        const { html } = buildCells(font, ch);
        return `<div class="row"><div class="char">${escapeChar(ch)}</div>${html.join("")}</div>`;
      })
      .join("");
    return `<div class="section-label">${section.label}</div>${rows}`;
  }).join("");

  return `<div class="grid">${headerRow}${sections}</div>`;
}

function renderSwitch(active: number, onPick: (i: number) => void): void {
  const el = document.getElementById("font-switch");
  if (!el) return;
  el.innerHTML = "";
  for (let i = 0; i < FONTS.length; i++) {
    const btn = document.createElement("button");
    btn.textContent = FONTS[i].label;
    if (i === active) btn.classList.add("active");
    btn.addEventListener("click", () => onPick(i));
    el.appendChild(btn);
  }
}

async function main(): Promise<void> {
  const status = document.getElementById("status");
  const root = document.getElementById("root");
  if (!root || !status) return;

  try {
    const fonts = await Promise.all(FONTS.map(loadFont));
    fonts.forEach((f, i) => {
      FONTS[i].font = f;
    });
  } catch (e) {
    status.textContent = "Font load failed: " + (e as Error).message;
    return;
  }

  status.style.display = "none";

  let active = 0;
  const draw = () => {
    const f = FONTS[active].font!;
    renderSwitch(active, (i) => {
      active = i;
      draw();
    });
    // Drop cached extracts so the meta column reflects real wall time
    // rather than ~0 ms cache hits on re-render.
    clearCenterlineCache();
    const t0 = performance.now();
    root.innerHTML = renderGrid(f);
    const total = performance.now() - t0;
    console.log(
      `[centerline-debug] ${FONTS[active].label}: rendered grid in ${total.toFixed(1)}ms`,
    );
  };

  draw();
}

main();
