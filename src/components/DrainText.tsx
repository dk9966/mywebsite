import {
  useRef,
  useEffect,
  useState,
  useLayoutEffect,
  useMemo,
  useCallback,
} from "react";
import { load, type Font } from "opentype.js";
import gsap from "gsap";
import {
  commandsToD,
  reindexForDirection,
  splitSubpaths,
  type DrainDirection,
} from "../lib/svgPaths";
import { STROKE_FONT, CELL_W, CELL_H } from "../lib/strokeFont";
import "./DrainText.css";

const FONT_URL = "/fonts/JetBrainsMono-Regular.ttf";
const FONT_SIZE = 120;
const STROKE_COLOR = "#00dffc";
const OUTLINE_WIDTH = 2;
const STROKE_WIDTH = 8;

const LETTER_GAP = 0.1;
const SUBPATH_STAGGER = 0.15;
const DRAW_DURATION = 1.5;

export type DrainMode = "outline" | "stroke";

const DRAIN_DIRECTIONS: Record<string, DrainDirection> = {
  B: "top-left",
  D: "top-left",
  O: "top-left",
  P: "top-left",
  Q: "top-left",
  R: "top-left",
};

interface SubpathInfo {
  d: string;
  glyphIdx: number;
  subpathIdx: number;
}

interface LayoutResult {
  subpaths: SubpathInfo[];
  viewBox: string;
  strokeWidth: number;
}

function polylineToD(pts: [number, number][]): string {
  return "M" + pts.map(([x, y]) => `${x} ${y}`).join("L");
}

function computeLayout(font: Font, text: string, mode: DrainMode): LayoutResult {
  const fontScale = FONT_SIZE / font.unitsPerEm;
  const lineHeight = (font.ascender - font.descender) * fontScale * 1.15;
  const cellScale = (font.ascender * fontScale) / CELL_H;
  const lines = text.split("\n");

  const subpaths: SubpathInfo[] = [];
  let glyphIdx = 0;
  let maxWidth = 0;

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx];
    let x = 0;
    const baseline = FONT_SIZE + lineIdx * lineHeight;

    for (const char of line) {
      const glyph = font.charToGlyph(char);
      const advance = glyph.advanceWidth * fontScale;

      if (char !== " ") {
        if (mode === "outline") {
          const path = glyph.getPath(x, baseline, FONT_SIZE);
          const direction = DRAIN_DIRECTIONS[char.toUpperCase()] ?? "left";
          const reindexed = reindexForDirection(path.commands, direction);
          const parts = splitSubpaths(reindexed);

          for (let si = 0; si < parts.length; si++) {
            subpaths.push({
              d: commandsToD(parts[si]),
              glyphIdx,
              subpathIdx: si,
            });
          }
        } else {
          const strokes = STROKE_FONT[char.toUpperCase()];
          if (strokes) {
            const strokeVisualW = CELL_W * cellScale;
            const xOff = x + (advance - strokeVisualW) / 2;
            const yOff = baseline - font.ascender * fontScale;

            for (let si = 0; si < strokes.length; si++) {
              const scaled = strokes[si].map(
                ([gx, gy]) =>
                  [xOff + gx * cellScale, yOff + gy * cellScale] as [number, number],
              );
              subpaths.push({
                d: polylineToD(scaled),
                glyphIdx,
                subpathIdx: si,
              });
            }
          }
        }
        glyphIdx++;
      }

      x += advance;
    }

    if (x > maxWidth) maxWidth = x;
  }

  const ascent = font.ascender * fontScale;
  const descent = Math.abs(font.descender * fontScale);
  const totalHeight = (lines.length - 1) * lineHeight + ascent + descent;
  const yMin = FONT_SIZE - ascent;
  const pad = 10;

  const viewBox = `${-pad} ${yMin - pad} ${maxWidth + pad * 2} ${totalHeight + pad * 2}`;
  return {
    subpaths,
    viewBox,
    strokeWidth: mode === "stroke" ? STROKE_WIDTH : OUTLINE_WIDTH,
  };
}

function formatTime(seconds: number): string {
  return seconds.toFixed(1) + "s";
}

interface DrainTextProps {
  text: string;
}

export default function DrainText({ text }: DrainTextProps) {
  const pathRefs = useRef<(SVGPathElement | null)[]>([]);
  const tlRef = useRef<gsap.core.Timeline | null>(null);
  const scrubberRef = useRef<HTMLInputElement>(null);
  const timeRef = useRef<HTMLSpanElement>(null);
  const [font, setFont] = useState<Font | null>(null);
  const [playing, setPlaying] = useState(true);
  const [mode, setMode] = useState<DrainMode>("outline");

  useEffect(() => {
    load(FONT_URL, (err, f) => {
      if (err || !f) {
        console.error("Font load failed:", err);
        return;
      }
      setFont(f);
    });
  }, []);

  const layout = useMemo(() => {
    if (!font) return null;
    return computeLayout(font, text, mode);
  }, [font, text, mode]);

  useLayoutEffect(() => {
    if (!layout) return;

    const paths = pathRefs.current.filter(Boolean) as SVGPathElement[];
    if (paths.length === 0) return;

    const sw = layout.strokeWidth;
    for (const el of paths) {
      const len = el.getTotalLength();
      el.style.strokeDasharray = `${len} ${len + sw * 2}`;
      el.style.strokeDashoffset = `${len + sw}`;
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

    const maxSubpathByGlyph = new Map<number, number>();
    for (const sp of layout.subpaths) {
      const prev = maxSubpathByGlyph.get(sp.glyphIdx);
      if (prev === undefined || sp.subpathIdx > prev) {
        maxSubpathByGlyph.set(sp.glyphIdx, sp.subpathIdx);
      }
    }

    const letterStart = new Map<number, number>();
    let cursor = 0;
    const glyphIndices = [...maxSubpathByGlyph.keys()].sort((a, b) => a - b);
    for (const idx of glyphIndices) {
      letterStart.set(idx, cursor);
      const glyphDuration = DRAW_DURATION + maxSubpathByGlyph.get(idx)! * SUBPATH_STAGGER;
      cursor += glyphDuration + LETTER_GAP;
    }

    for (let i = 0; i < layout.subpaths.length; i++) {
      const el = pathRefs.current[i];
      if (!el) continue;

      const info = layout.subpaths[i];
      const offset = letterStart.get(info.glyphIdx)! + info.subpathIdx * SUBPATH_STAGGER;

      tl.to(
        el,
        {
          strokeDashoffset: 0,
          duration: DRAW_DURATION,
          ease: "power2.inOut",
        },
        offset,
      );
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

  const handleScrub = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const tl = tlRef.current;
      if (!tl) return;

      const value = parseFloat(e.target.value);
      tl.pause();
      tl.progress(value);
      setPlaying(false);
    },
    [],
  );

  if (!layout) return null;

  return (
    <div className="drain-text">
      <svg
        className="drain-text__svg"
        viewBox={layout.viewBox}
        xmlns="http://www.w3.org/2000/svg"
      >
        {layout.subpaths.map((sp, i) => (
          <path
            key={`${mode}-${sp.glyphIdx}-${sp.subpathIdx}`}
            ref={(el) => {
              pathRefs.current[i] = el;
            }}
            d={sp.d}
            fill="none"
            stroke={STROKE_COLOR}
            strokeWidth={layout.strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
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
        <div className="drain-text__mode-toggle">
          <button
            className={`drain-text__mode-btn ${mode === "outline" ? "drain-text__mode-btn--active" : ""}`}
            onClick={() => setMode("outline")}
          >
            OUTLINE
          </button>
          <button
            className={`drain-text__mode-btn ${mode === "stroke" ? "drain-text__mode-btn--active" : ""}`}
            onClick={() => setMode("stroke")}
          >
            STROKE
          </button>
        </div>
        <span ref={timeRef} className="drain-text__time">
          0.0s / 0.0s
        </span>
      </div>
    </div>
  );
}
