import gsap from "gsap";
import { load, type Font } from "opentype.js";
import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { getCenterlineDrain } from "../lib/centerline";
import { DRAIN_MANUAL_NODES_BY_CHAR } from "../lib/drainManualNodes";
import { DRAIN_STROKE_INDEX_ORDER_BY_CHAR } from "../lib/drainStrokeOrder";
import "./DrainText.css";

/** Default TTF when `fontUrl` is omitted (site hero). */
export const DEFAULT_DRAIN_FONT_URL = "/fonts/VT323-Regular.ttf";
const FONT_SIZE = 120;
const STROKE_COLOR = "#00dffc";
const STROKE_WIDTH = 4;
/**
 * Mask eraser width (centerline stroke in mask). Wider than STROKE_WIDTH so
 * the sweep clears the filled glyph, not just a hairline.
 */
const ERASER_WIDTH = 28;

const HOLD_BEFORE_DRAIN = 0.5;
const DRAIN_DURATION = 1.5;
const LETTER_OVERLAP = 0.6;

interface ProjectedStroke {
  d: string;
  pixelLength: number;
  tStart: number;
  tEnd: number;
}

interface GlyphRender {
  glyphIdx: number;
  /** Filled outline path in SVG user space (matches opentype getPath). */
  fillD: string;
  strokes: ProjectedStroke[];
  totalDistanceEm: number;
}

interface LayoutResult {
  glyphs: GlyphRender[];
  viewBox: string;
  referenceDistanceEm: number;
}

function isValidStrokeIndexOrder(order: number[], n: number): boolean {
  if (order.length !== n || n === 0) return false;
  const sorted = [...order].sort((a, b) => a - b);
  for (let i = 0; i < n; i++) {
    if (sorted[i] !== i) return false;
  }
  return true;
}

/** Reorder strokes and assign sequential [tStart,tEnd] windows, or return as-is. */
function orderStrokesForGlyph(
  char: string,
  projected: ProjectedStroke[],
): ProjectedStroke[] {
  const order = DRAIN_STROKE_INDEX_ORDER_BY_CHAR[char];
  if (!order) return projected;

  if (!isValidStrokeIndexOrder(order, projected.length)) {
    console.warn(
      `[DrainText] Invalid DRAIN_STROKE_INDEX_ORDER_BY_CHAR["${char}"] ` +
        `(need ${projected.length} distinct indices 0..${
          projected.length - 1
        }); using liquid order.`,
    );
    return projected;
  }

  const n = order.length;
  return order.map((srcIndex, playIndex) => {
    const base = projected[srcIndex];
    return {
      ...base,
      tStart: playIndex / n,
      tEnd: (playIndex + 1) / n,
    };
  });
}

function computeLayout(font: Font, text: string): LayoutResult {
  const fontScale = FONT_SIZE / font.unitsPerEm;
  const lineHeight = (font.ascender - font.descender) * fontScale * 1.15;
  const lines = text.split("\n");

  const glyphs: GlyphRender[] = [];
  let glyphIdx = 0;
  let maxWidth = 0;

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx];
    let cursorX = 0;
    const baseline = FONT_SIZE + lineIdx * lineHeight;

    for (const char of line) {
      const glyph = font.charToGlyph(char);
      const advance = glyph.advanceWidth * fontScale;

      if (char !== " ") {
        const manualNodes = DRAIN_MANUAL_NODES_BY_CHAR[char];
        const { plan } = getCenterlineDrain(
          font,
          char,
          manualNodes?.length ? { manualNodes } : undefined,
        );
        const glyphPath = glyph.getPath(cursorX, baseline, FONT_SIZE);
        const fillD = glyphPath.toPathData(2);

        const projected: ProjectedStroke[] = [];
        for (const ds of plan.strokes) {
          const pixelLength = ds.length * fontScale;
          if (pixelLength < STROKE_WIDTH) continue;

          const pts = ds.points;
          const parts: string[] = [];
          for (let i = 0; i < pts.length; i++) {
            const sx = cursorX + pts[i][0] * fontScale;
            const sy = baseline - pts[i][1] * fontScale;
            parts.push(
              `${i === 0 ? "M" : "L"}${sx.toFixed(2)} ${sy.toFixed(2)}`,
            );
          }
          projected.push({
            d: parts.join(""),
            pixelLength,
            tStart: ds.tStart,
            tEnd: ds.tEnd,
          });
        }

        glyphs.push({
          glyphIdx,
          fillD,
          strokes: orderStrokesForGlyph(char, projected),
          totalDistanceEm: plan.totalDistance,
        });
        glyphIdx++;
      }

      cursorX += advance;
    }

    if (cursorX > maxWidth) maxWidth = cursorX;
  }

  const ascent = font.ascender * fontScale;
  const descent = Math.abs(font.descender * fontScale);
  const totalHeight = (lines.length - 1) * lineHeight + ascent + descent;
  const yMin = FONT_SIZE - ascent;
  const pad = 10;
  const viewBox = `${-pad} ${yMin - pad} ${maxWidth + pad * 2} ${totalHeight + pad * 2}`;

  let referenceDistanceEm = 1;
  for (const g of glyphs) {
    if (g.totalDistanceEm > referenceDistanceEm) {
      referenceDistanceEm = g.totalDistanceEm;
    }
  }

  return { glyphs, viewBox, referenceDistanceEm };
}

function formatTime(seconds: number): string {
  return seconds.toFixed(1) + "s";
}

interface DrainTextProps {
  text: string;
  /** Opentype.js fetches this URL (same-origin `/fonts/...` TTF or WOFF). */
  fontUrl?: string;
}

export default function DrainText({
  text,
  fontUrl = DEFAULT_DRAIN_FONT_URL,
}: DrainTextProps) {
  const maskPathRefs = useRef<(SVGPathElement | null)[][]>([]);
  const tlRef = useRef<gsap.core.Timeline | null>(null);
  const scrubberRef = useRef<HTMLInputElement>(null);
  const timeRef = useRef<HTMLSpanElement>(null);
  const [fontReady, setFontReady] = useState<{
    url: string;
    font: Font;
  } | null>(null);
  const [playing, setPlaying] = useState(true);
  const reactId = useId().replace(/:/g, "");

  useEffect(() => {
    let cancelled = false;
    load(fontUrl, (err, f) => {
      if (cancelled) return;
      if (err || !f) {
        console.error("Font load failed:", err);
        setFontReady(null);
        return;
      }
      setFontReady({ url: fontUrl, font: f });
    });
    return () => {
      cancelled = true;
    };
  }, [fontUrl]);

  const font = fontReady?.url === fontUrl ? fontReady.font : null;

  const layout = useMemo(() => {
    if (!font) return null;
    return computeLayout(font, text);
  }, [font, text]);

  useLayoutEffect(() => {
    if (!layout) return;

    const dashEnd = (s: ProjectedStroke) => s.pixelLength + ERASER_WIDTH * 2;

    for (let gi = 0; gi < layout.glyphs.length; gi++) {
      const g = layout.glyphs[gi];
      for (let si = 0; si < g.strokes.length; si++) {
        const path = maskPathRefs.current[gi]?.[si];
        if (path)
          path.setAttribute(
            "stroke-dashoffset",
            String(dashEnd(g.strokes[si])),
          );
      }
    }

    const tl = gsap.timeline({
      onStart: () => setPlaying(true),
      onUpdate: () => {
        if (scrubberRef.current) {
          scrubberRef.current.value = String(tl.progress());
        }
        if (timeRef.current) {
          timeRef.current.textContent =
            formatTime(tl.time()) + " / " + formatTime(tl.duration());
        }
      },
      onComplete: () => setPlaying(false),
    });

    let glyphStart = HOLD_BEFORE_DRAIN;
    for (let gi = 0; gi < layout.glyphs.length; gi++) {
      const g = layout.glyphs[gi];
      const subDuration =
        DRAIN_DURATION * (g.totalDistanceEm / layout.referenceDistanceEm);

      for (let si = 0; si < g.strokes.length; si++) {
        const path = maskPathRefs.current[gi]?.[si];
        if (!path) continue;
        const s = g.strokes[si];
        const dur = subDuration * (s.tEnd - s.tStart);
        const fromOff = dashEnd(s);
        tl.fromTo(
          path,
          { attr: { "stroke-dashoffset": fromOff } },
          {
            attr: { "stroke-dashoffset": 0 },
            duration: Math.max(dur, 0.0001),
            ease: "none",
          },
          glyphStart + s.tStart * subDuration,
        );
      }

      glyphStart += subDuration * (1 - LETTER_OVERLAP);
    }

    tlRef.current = tl;

    return () => {
      tl.kill();
      tlRef.current = null;
    };
  }, [layout]);

  const togglePlay = useCallback(() => {
    const tl = tlRef.current;
    if (!tl) return;

    if (tl.progress() >= 1) {
      tl.restart();
      setPlaying(true);
    } else if (tl.isActive()) {
      tl.pause();
      setPlaying(false);
    } else {
      tl.play();
      setPlaying(true);
    }
  }, []);

  const handleScrub = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const tl = tlRef.current;
    if (!tl) return;

    const value = parseFloat(e.target.value);
    tl.pause();
    tl.progress(value);
    setPlaying(false);
  }, []);

  if (!layout) {
    return (
      <div className="drain-text drain-text--loading" aria-busy="true">
        <p className="drain-text__loading">Loading font…</p>
      </div>
    );
  }

  return (
    <div className="drain-text">
      <svg
        className="drain-text__svg"
        viewBox={layout.viewBox}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {layout.glyphs.map((g, gi) => (
            <mask
              key={`mask-def-${g.glyphIdx}`}
              id={`${reactId}-mask-${g.glyphIdx}`}
              maskUnits="userSpaceOnUse"
              maskContentUnits="userSpaceOnUse"
            >
              <path fill="white" fillRule="evenodd" d={g.fillD} />
              {g.strokes.map((s, si) => (
                <path
                  key={`m-${g.glyphIdx}-${si}`}
                  ref={(el) => {
                    let row = maskPathRefs.current[gi];
                    if (!row) {
                      row = [];
                      maskPathRefs.current[gi] = row;
                    }
                    row[si] = el;
                  }}
                  d={s.d}
                  fill="none"
                  stroke="black"
                  strokeWidth={ERASER_WIDTH}
                  strokeLinecap="butt"
                  strokeLinejoin="round"
                  strokeDasharray={`${s.pixelLength} ${s.pixelLength + ERASER_WIDTH * 4}`}
                  strokeDashoffset={s.pixelLength + ERASER_WIDTH * 2}
                />
              ))}
            </mask>
          ))}
        </defs>

        {layout.glyphs.map((g) => (
          <path
            key={`fill-${g.glyphIdx}`}
            fill={STROKE_COLOR}
            fillRule="evenodd"
            d={g.fillD}
            mask={`url(#${reactId}-mask-${g.glyphIdx})`}
          />
        ))}
      </svg>

      <div className="drain-text__controls">
        <button
          className="drain-text__play-btn"
          onClick={togglePlay}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <svg viewBox="0 0 24 24" width="16" height="16">
              <rect x="5" y="4" width="4" height="16" fill="currentColor" />
              <rect x="15" y="4" width="4" height="16" fill="currentColor" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="16" height="16">
              <polygon points="6,4 20,12 6,20" fill="currentColor" />
            </svg>
          )}
        </button>
        <input
          ref={scrubberRef}
          className="drain-text__scrubber"
          type="range"
          min={0}
          max={1}
          step={0.001}
          defaultValue={0}
          onChange={handleScrub}
        />
        <span ref={timeRef} className="drain-text__time">
          0.0s / 0.0s
        </span>
      </div>
    </div>
  );
}
