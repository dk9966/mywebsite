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
import "./DrainText.css";

const FONT_URL = "/fonts/JetBrainsMono-Regular.ttf";
const FONT_SIZE = 120;
const STROKE_COLOR = "#00dffc";
const STROKE_WIDTH = 2;

const LETTER_STAGGER = 0.3;
const SUBPATH_STAGGER = 0.15;
const DRAW_DURATION = 1.5;

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

function computeLayout(font: Font, text: string) {
  const scale = FONT_SIZE / font.unitsPerEm;
  const lineHeight = (font.ascender - font.descender) * scale * 1.15;
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

      if (char !== " ") {
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
        glyphIdx++;
      }

      x += glyph.advanceWidth * scale;
    }

    if (x > maxWidth) maxWidth = x;
  }

  const ascent = font.ascender * scale;
  const descent = Math.abs(font.descender * scale);
  const totalHeight = (lines.length - 1) * lineHeight + ascent + descent;
  const yMin = FONT_SIZE - ascent;
  const pad = 10;

  const viewBox = `${-pad} ${yMin - pad} ${maxWidth + pad * 2} ${totalHeight + pad * 2}`;
  return { subpaths, viewBox };
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
    return computeLayout(font, text);
  }, [font, text]);

  useLayoutEffect(() => {
    if (!layout) return;

    const paths = pathRefs.current.filter(Boolean) as SVGPathElement[];
    if (paths.length === 0) return;

    for (const el of paths) {
      const len = el.getTotalLength();
      el.style.strokeDasharray = `${len}`;
      el.style.strokeDashoffset = `${len}`;
    }

    const tl = gsap.timeline({
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

    for (let i = 0; i < layout.subpaths.length; i++) {
      const el = pathRefs.current[i];
      if (!el) continue;

      const info = layout.subpaths[i];
      const letterDelay = info.glyphIdx * LETTER_STAGGER;
      const branchDelay = info.subpathIdx * SUBPATH_STAGGER;

      tl.to(
        el,
        {
          strokeDashoffset: 0,
          duration: DRAW_DURATION,
          ease: "power2.inOut",
        },
        letterDelay + branchDelay,
      );
    }

    tlRef.current = tl;
    setPlaying(true);

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
            key={`${sp.glyphIdx}-${sp.subpathIdx}`}
            ref={(el) => {
              pathRefs.current[i] = el;
            }}
            d={sp.d}
            fill="none"
            stroke={STROKE_COLOR}
            strokeWidth={STROKE_WIDTH}
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
        <span ref={timeRef} className="drain-text__time">
          0.0s / 0.0s
        </span>
      </div>
    </div>
  );
}
