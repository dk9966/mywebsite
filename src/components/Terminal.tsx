import {
  useEffect,
  useReducer,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import audioUrl from "../../assets/End of Line (Remixed by Photek).mp3?url";
import "./Terminal.css";

const PROMPT = "guest@danielku.xyz \u279C  ~";
const INITIAL_INPUT = "website init";
const TICK_MS = 60;

const DOTLINE_HEIGHT = 6;
const DOTLINE_PAD = 2;
const DOTLINE_DOT_R = 1;
const DOTLINE_DOTS = 24;
const DOTLINE_GAP_MAX = 24;
const DOTLINE_LINE_TICKS = 34;
const DOTLINE_HOLD_TICKS = 22;
const DOTLINE_LINE_LOOP_GAP = 8;

/**
 * Smooth ease: starts fast (v0 = 3), settles into a decently fast steady glide (v1 = 0.5).
 * Continuous derivative, monotonic — no visible kink between burst and cruise.
 */
function dotlineBurstThenSteady(linear: number): number {
  const t = Math.min(1, Math.max(0, linear));
  const inv = 1 - t;
  return 0.5 * (1 - inv * inv * inv * inv * inv) + 0.5 * t;
}

const DOT_POSITIONS: number[] = (() => {
  const positions: number[] = [];
  let x = DOTLINE_PAD + DOTLINE_DOT_R;
  positions.push(x);
  for (let i = 0; i < DOTLINE_DOTS - 1; i++) {
    const t = i / (DOTLINE_DOTS - 2);
    const eased = t * t * t * (t * (t * 6 - 15) + 10);
    const gap = DOTLINE_GAP_MAX * (1 - eased) + 2 * DOTLINE_DOT_R * eased;
    x += gap;
    positions.push(x);
  }
  return positions;
})();

/**
 * SVG width ends exactly at the last dot's right edge so the bar rail picks up
 * with no gap. Trailing DOTLINE_PAD is intentionally omitted.
 */
const DOTLINE_DOTS_WIDTH =
  DOT_POSITIONS[DOT_POSITIONS.length - 1] + DOTLINE_DOT_R;

const DOT_DWELLS: number[] = DOT_POSITIONS.map((_, i) => Math.max(1, 5 - i));
const DOT_TOTAL_TICKS = DOT_DWELLS.reduce((a, b) => a + b, 0);
const DOTLINE_FIRST_RUN =
  DOT_TOTAL_TICKS + DOTLINE_LINE_TICKS + DOTLINE_HOLD_TICKS;
const DOTLINE_LINE_LOOP_PERIOD = DOTLINE_LINE_TICKS + DOTLINE_LINE_LOOP_GAP;

function DotsLineLoader() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let raf = 0;
    let prev = performance.now();
    const loop = (now: number) => {
      const dt = (now - prev) / TICK_MS;
      prev = now;
      setTick((t) => t + dt);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  const cy = DOTLINE_HEIGHT / 2;

  let visible = DOT_POSITIONS.length;
  let lineProgress = 0;

  if (tick < DOTLINE_FIRST_RUN) {
    const step = tick;

    let acc = 0;
    for (let i = 0; i < DOT_DWELLS.length; i++) {
      acc += DOT_DWELLS[i];
      if (step < acc) {
        visible = i + 1;
        break;
      }
    }

    const rawLine =
      step >= DOT_TOTAL_TICKS
        ? Math.min(1, (step - DOT_TOTAL_TICKS) / DOTLINE_LINE_TICKS)
        : 0;
    lineProgress = dotlineBurstThenSteady(rawLine);
  } else {
    const sub = (tick - DOTLINE_FIRST_RUN) % DOTLINE_LINE_LOOP_PERIOD;
    lineProgress =
      sub < DOTLINE_LINE_TICKS
        ? dotlineBurstThenSteady(sub / DOTLINE_LINE_TICKS)
        : 0;
  }

  return (
    <span className="terminal__dotline">
      <svg
        className="terminal__dotline-dots"
        width={DOTLINE_DOTS_WIDTH}
        height={DOTLINE_HEIGHT}
        viewBox={`0 0 ${DOTLINE_DOTS_WIDTH} ${DOTLINE_HEIGHT}`}
      >
        {DOT_POSITIONS.slice(0, visible).map((cx, i) => (
          <circle key={i} cx={cx} cy={cy} r={DOTLINE_DOT_R} fill="currentColor" />
        ))}
      </svg>
      <span className="terminal__dotline-rail" aria-hidden="true">
        <span
          className="terminal__dotline-bar"
          style={{ transform: `scaleX(${lineProgress})` }}
        />
      </span>
    </span>
  );
}

type Phase =
  | "idle"
  | "running"
  | "awaiting-audio"
  | "finishing"
  | "installing";

type LineKind = "command" | "system" | "error" | "prompt" | "blank";

type HistoryLine = { id: number; kind: LineKind; text: string };

type BootStep = { text: string; delay: number };

const BOOT_LINES: BootStep[] = [
  { text: "[boot] runtime v0.1.4", delay: 120 },
  { text: "[init] linking modules ........ ok", delay: 180 },
  { text: "[init] compiling shaders ....... ok", delay: 220 },
  { text: "[init] preloading typefaces .... ok", delay: 180 },
  { text: "[init] audio subsystem ready", delay: 140 },
];

const AUDIO_PROMPT_TEXT = "initialize audio subsystem? [y/n]";

const FINISH_LINES: BootStep[] = [
  { text: "[init] mounting scene graph .... ok", delay: 180 },
  { text: "[init] hydrating viewport ...... ok", delay: 180 },
];

const INSTALL_LINES: BootStep[] = [
  { text: "[pkg] fetching @core/runtime@0.1.4 ......... ok", delay: 220 },
  { text: "[pkg] fetching @ui/toolkit@2.3.0 ........... ok", delay: 180 },
  { text: "[pkg] fetching @type/lab@0.4.2 ............. ok", delay: 160 },
  { text: "[pkg] fetching @scene/assets@1.0.0 ......... ok", delay: 200 },
  { text: "[pkg] resolving 147 symbols ................ ok", delay: 160 },
  { text: "[pkg] linking binaries ..................... ok", delay: 140 },
  { text: "[done] installed 6 packages in 1.2s", delay: 240 },
  { text: "", delay: 120 },
  { text: "> session ready. type 'help' for commands.", delay: 160 },
];

const HELP_OUTPUT = [
  "available commands:",
  "  website init    boot the site",
  "  about           who made this",
  "  help            this message",
  "  clear           clear the screen",
];

const ABOUT_OUTPUT = [
  "daniel ku",
  "building things at the intersection of",
  "typography, audio, and motion.",
];

type State = {
  phase: Phase;
  history: HistoryLine[];
  inputValue: string;
  nextId: number;
};

type Action =
  | { type: "setInput"; value: string }
  | { type: "clearInput" }
  | { type: "addLine"; kind: LineKind; text: string }
  | { type: "addLines"; kind: LineKind; texts: string[] }
  | { type: "setPhase"; phase: Phase }
  | { type: "clearHistory" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "setInput":
      return { ...state, inputValue: action.value };
    case "clearInput":
      return { ...state, inputValue: "" };
    case "addLine":
      return {
        ...state,
        history: [
          ...state.history,
          { id: state.nextId, kind: action.kind, text: action.text },
        ],
        nextId: state.nextId + 1,
      };
    case "addLines": {
      const next = action.texts.map((text, i) => ({
        id: state.nextId + i,
        kind: action.kind,
        text,
      }));
      return {
        ...state,
        history: [...state.history, ...next],
        nextId: state.nextId + action.texts.length,
      };
    }
    case "setPhase":
      return { ...state, phase: action.phase };
    case "clearHistory":
      return { ...state, history: [] };
  }
}

const initialState: State = {
  phase: "idle",
  history: [],
  inputValue: INITIAL_INPUT,
  nextId: 0,
};

function useScriptedLines(
  active: boolean,
  lines: BootStep[],
  dispatch: React.Dispatch<Action>,
  onDone: () => void,
) {
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    let timeoutId: number | undefined;

    const runStep = (index: number) => {
      if (cancelled) return;
      if (index >= lines.length) {
        onDoneRef.current();
        return;
      }
      const step = lines[index];
      timeoutId = window.setTimeout(() => {
        if (cancelled) return;
        const kind: LineKind = step.text === "" ? "blank" : "system";
        dispatch({ type: "addLine", kind, text: step.text });
        runStep(index + 1);
      }, step.delay);
    };

    runStep(0);

    return () => {
      cancelled = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [active, lines, dispatch]);
}

export default function Terminal() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { phase, history, inputValue } = state;

  const inputRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [websiteInitComplete, setWebsiteInitComplete] = useState(false);

  useEffect(() => {
    const audio = new Audio(audioUrl);
    audio.loop = true;
    audio.volume = 0.6;
    audio.preload = "auto";
    audioRef.current = audio;
    return () => {
      audio.pause();
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (phase !== "idle") return;
    const el = inputRef.current;
    if (!el) return;
    el.focus();
    const end = el.value.length;
    el.setSelectionRange(end, end);
  }, [phase]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [history.length, phase]);

  useScriptedLines(phase === "running", BOOT_LINES, dispatch, () => {
    dispatch({ type: "addLine", kind: "prompt", text: AUDIO_PROMPT_TEXT });
    dispatch({ type: "setPhase", phase: "awaiting-audio" });
  });

  useScriptedLines(phase === "finishing", FINISH_LINES, dispatch, () => {
    dispatch({ type: "setPhase", phase: "installing" });
  });

  useScriptedLines(phase === "installing", INSTALL_LINES, dispatch, () => {
    setWebsiteInitComplete(true);
    dispatch({ type: "setPhase", phase: "idle" });
  });

  useEffect(() => {
    if (phase !== "awaiting-audio") return;

    const handler = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k !== "y" && k !== "n") return;
      e.preventDefault();

      if (k === "y") {
        const audio = audioRef.current;
        if (audio) {
          void audio.play().catch(() => {});
        }
        dispatch({
          type: "addLine",
          kind: "system",
          text: "[ok] audio stream attached \u2014 end of line (remixed by photek)",
        });
      } else {
        dispatch({
          type: "addLine",
          kind: "system",
          text: "[ok] audio subsystem muted",
        });
      }
      dispatch({ type: "setPhase", phase: "finishing" });
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [phase]);

  const runCommand = (raw: string) => {
    const trimmed = raw.trim();
    if (trimmed === "") return;

    switch (trimmed) {
      case "website init":
        dispatch({ type: "setPhase", phase: "running" });
        return;
      case "help":
        dispatch({ type: "addLines", kind: "system", texts: HELP_OUTPUT });
        return;
      case "about":
        dispatch({ type: "addLines", kind: "system", texts: ABOUT_OUTPUT });
        return;
      case "clear":
        dispatch({ type: "clearHistory" });
        return;
      default:
        dispatch({
          type: "addLine",
          kind: "error",
          text: `zsh: command not found: ${trimmed}`,
        });
    }
  };

  const handleInputKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "l" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      dispatch({ type: "clearHistory" });
      return;
    }
    if (e.key !== "Enter") return;
    e.preventDefault();

    const command = inputValue;
    dispatch({ type: "addLine", kind: "command", text: command });
    dispatch({ type: "clearInput" });
    runCommand(command);
  };

  const refocusInput = () => {
    if (phase !== "idle") return;
    inputRef.current?.focus();
  };

  return (
    <section
      ref={rootRef}
      className="terminal terminal--viewport"
      aria-label="terminal"
      onClick={refocusInput}
    >
      <div className="terminal__body">
        {history.map((line) => (
          <div
            key={line.id}
            className={`terminal__line terminal__line--${line.kind}`}
          >
            {line.kind === "command" && (
              <span className="terminal__prompt">{PROMPT}</span>
            )}
            <span className="terminal__line-text">
              {line.text === "" ? "\u00a0" : line.text}
            </span>
          </div>
        ))}

        {(phase === "installing" ||
          (phase === "idle" && websiteInitComplete)) && (
          <div className="terminal__loaders" aria-hidden="true">
            <span className="terminal__loader-label">
              [{phase === "installing" ? "installing" : "ready"}]
            </span>
            <span className="terminal__loader-frame">
              <DotsLineLoader />
            </span>
          </div>
        )}

        {phase === "idle" && (
          <div className="terminal__line terminal__line--active">
            <span className="terminal__prompt">{PROMPT}</span>
            <span className="terminal__input-wrap">
              <input
                ref={inputRef}
                className="terminal__input-hidden"
                value={inputValue}
                onChange={(e) =>
                  dispatch({ type: "setInput", value: e.target.value })
                }
                onKeyDown={handleInputKeyDown}
                autoFocus
                spellCheck={false}
                autoCapitalize="off"
                autoCorrect="off"
                aria-label="terminal input"
              />
              <span className="terminal__input-mirror">{inputValue}</span>
              <span className="terminal__cursor" aria-hidden="true" />
            </span>
          </div>
        )}

        {phase === "awaiting-audio" && (
          <div className="terminal__line terminal__line--active">
            <span className="terminal__cursor" aria-hidden="true" />
          </div>
        )}
      </div>
    </section>
  );
}
