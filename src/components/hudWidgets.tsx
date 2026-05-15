import { useEffect, useMemo, useRef, useState } from "react";
import "./hudWidgets.css";

// Pure utilities --------------------------------------------------------------

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

// Mulberry32 — tiny deterministic PRNG so layouts like the radar contacts or
// network nodes don't reshuffle on every render.
function seededRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Clock + date ---------------------------------------------------------------

export function ClockWidget() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const hh = pad2(now.getHours());
  const mm = pad2(now.getMinutes());
  const ss = pad2(now.getSeconds());
  const date = now
    .toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "2-digit",
    })
    .toUpperCase();

  return (
    <div className="hud-clock">
      <div className="hud-clock__time">
        <span>{hh}</span>
        <span className="hud-clock__sep">:</span>
        <span>{mm}</span>
        <span className="hud-clock__sep hud-clock__sep--dim">:</span>
        <span className="hud-clock__seconds">{ss}</span>
      </div>
      <div className="hud-clock__date">{date}</div>
      <div className="hud-clock__meta">
        <span>UTC{-now.getTimezoneOffset() / 60 >= 0 ? "+" : ""}
          {(-now.getTimezoneOffset() / 60).toFixed(1)}
        </span>
        <span>SYNC OK</span>
      </div>
    </div>
  );
}

// System telemetry bars ------------------------------------------------------

const STAT_LABELS = ["CPU", "GPU", "MEM", "NET", "I/O"] as const;

export function TelemetryWidget() {
  const [values, setValues] = useState<number[]>(() => STAT_LABELS.map(() => rand(20, 80)));
  useEffect(() => {
    const id = window.setInterval(() => {
      setValues((prev) =>
        prev.map((v) => {
          // Slow drift + occasional spike, clamped.
          const drift = rand(-6, 6);
          const next = v + drift + (Math.random() < 0.08 ? rand(-15, 20) : 0);
          return Math.max(5, Math.min(98, next));
        }),
      );
    }, 320);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="hud-telemetry">
      {STAT_LABELS.map((label, i) => (
        <div className="hud-telemetry__row" key={label}>
          <span className="hud-telemetry__label">{label}</span>
          <div className="hud-telemetry__track">
            <div
              className="hud-telemetry__fill"
              style={{ width: `${values[i].toFixed(1)}%` }}
            />
          </div>
          <span className="hud-telemetry__value">{values[i].toFixed(0).padStart(2, "0")}%</span>
        </div>
      ))}
      <div className="hud-telemetry__footer">
        <span>SECTOR 07</span>
        <span>NOMINAL</span>
      </div>
    </div>
  );
}

// Terminal stream ------------------------------------------------------------

const TERMINAL_LINES = [
  "[grid] handshake 0x7a3 OK",
  "[mcp] yielding to user context",
  "[net] route +ENC tcp/443 → 10.0.4.7",
  "[lightcycle] derez sequence ARMED",
  "[recognizer] sweep pattern lambda-9",
  "[disk] read 4096 sectors @ 18.4 MB/s",
  "[auth] token TR0N-22f8 verified",
  "[sys] kernel watchdog ping 12ms",
  "[bios] post complete — entering ring 0",
  "[mcp] subroutine quorum 0xff",
  "[bus] arbitration won by node 03",
  "[fs] /usr/local/clu/identity.so loaded",
  "[xfer] uploading bit to recognizer queue",
  "[trace] tau-link held for 0.412s",
  "[grid] anomaly purged",
];

export function TerminalWidget() {
  const [lines, setLines] = useState<string[]>(() =>
    Array.from({ length: 7 }, () => TERMINAL_LINES[Math.floor(Math.random() * TERMINAL_LINES.length)]),
  );

  useEffect(() => {
    const id = window.setInterval(() => {
      setLines((prev) => {
        const next = prev.slice(1);
        next.push(TERMINAL_LINES[Math.floor(Math.random() * TERMINAL_LINES.length)]);
        return next;
      });
    }, 650);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="hud-terminal">
      {lines.map((line, i) => (
        <div
          className="hud-terminal__line"
          key={`${i}-${line}`}
          style={{ opacity: 0.35 + ((i + 1) / lines.length) * 0.65 }}
        >
          <span className="hud-terminal__prompt">{">"}</span>
          {line}
        </div>
      ))}
      <div className="hud-terminal__cursor" />
    </div>
  );
}

// Oscilloscope --------------------------------------------------------------

export function OscilloscopeWidget() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    let raf = 0;
    let phase = 0;
    const draw = () => {
      phase += 0.04;
      ctx.clearRect(0, 0, W, H);

      // Faint grid.
      ctx.strokeStyle = "rgba(102, 240, 240, 0.12)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x < W; x += W / 8) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
      }
      for (let y = 0; y < H; y += H / 4) {
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
      }
      ctx.stroke();

      // Waveform: layered sines for an organic feel.
      ctx.strokeStyle = "rgba(160, 240, 240, 0.9)";
      ctx.lineWidth = 1.5;
      ctx.shadowColor = "rgba(102, 240, 240, 0.7)";
      ctx.shadowBlur = 8;
      ctx.beginPath();
      for (let x = 0; x < W; x++) {
        const t = x / W;
        const y =
          H / 2 +
          Math.sin(t * 14 + phase) * (H * 0.18) +
          Math.sin(t * 32 + phase * 1.7) * (H * 0.07) +
          Math.sin(t * 71 - phase * 0.6) * (H * 0.03);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="hud-osc">
      <canvas ref={canvasRef} className="hud-osc__canvas" />
      <div className="hud-osc__legend">
        <span>CH1 — 4.2kHz</span>
        <span>±2.5V</span>
      </div>
    </div>
  );
}

// Radar sweep ---------------------------------------------------------------

type Contact = { angleDeg: number; r: number; size: number };

export function RadarWidget() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Contacts are stable for the lifetime of the widget so the radar feels
  // coherent — they only "light up" when the sweep passes them.
  const contacts = useMemo<Contact[]>(() => {
    const rng = seededRng(0x707);
    return Array.from({ length: 6 }, () => ({
      angleDeg: rng() * 360,
      r: 0.25 + rng() * 0.7,
      size: 2 + rng() * 2.5,
    }));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    const cx = W / 2;
    const cy = H / 2;
    const radius = Math.min(W, H) * 0.46;

    let raf = 0;
    let sweep = 0;
    const draw = () => {
      sweep = (sweep + 0.018) % (Math.PI * 2);
      ctx.clearRect(0, 0, W, H);

      // Rings.
      ctx.strokeStyle = "rgba(102, 240, 240, 0.35)";
      ctx.lineWidth = 1;
      for (let i = 1; i <= 3; i++) {
        ctx.beginPath();
        ctx.arc(cx, cy, (radius * i) / 3, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Crosshair.
      ctx.strokeStyle = "rgba(102, 240, 240, 0.22)";
      ctx.beginPath();
      ctx.moveTo(cx - radius, cy);
      ctx.lineTo(cx + radius, cy);
      ctx.moveTo(cx, cy - radius);
      ctx.lineTo(cx, cy + radius);
      ctx.stroke();

      // Sweep wedge (a small angular fan).
      const wedge = 0.55;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      grad.addColorStop(0, "rgba(102, 240, 240, 0.35)");
      grad.addColorStop(1, "rgba(102, 240, 240, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, sweep - wedge, sweep);
      ctx.closePath();
      ctx.fill();

      // Contacts — fade in when the sweep angle is recent.
      for (const c of contacts) {
        const ang = (c.angleDeg * Math.PI) / 180;
        const dx = Math.cos(ang) * radius * c.r;
        const dy = Math.sin(ang) * radius * c.r;
        const diff = ((sweep - ang) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
        const freshness = Math.max(0, 1 - diff / 1.6);
        const alpha = 0.18 + freshness * 0.82;
        ctx.fillStyle = `rgba(140, 250, 250, ${alpha.toFixed(3)})`;
        ctx.shadowColor = "rgba(102, 240, 240, 0.8)";
        ctx.shadowBlur = 8 * freshness;
        ctx.beginPath();
        ctx.arc(cx + dx, cy + dy, c.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [contacts]);

  return (
    <div className="hud-radar">
      <canvas ref={canvasRef} className="hud-radar__canvas" />
      <div className="hud-radar__readout">
        <div>BEARING 037°</div>
        <div>RANGE 4.2 KM</div>
      </div>
    </div>
  );
}

// Network mesh -------------------------------------------------------------

type Node = { x: number; y: number; r: number };
type Edge = [number, number];

export function NetworkWidget() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [pulseId, setPulseId] = useState(0);

  const { nodes, edges } = useMemo(() => {
    const rng = seededRng(0xfade);
    const n: Node[] = Array.from({ length: 9 }, () => ({
      x: 8 + rng() * 84,
      y: 8 + rng() * 84,
      r: 2.4 + rng() * 1.4,
    }));
    // Connect each node to its 2 nearest neighbors — produces an organic mesh.
    const e: Edge[] = [];
    const seen = new Set<string>();
    for (let i = 0; i < n.length; i++) {
      const order = n
        .map((p, j) => ({ j, d: (p.x - n[i].x) ** 2 + (p.y - n[i].y) ** 2 }))
        .filter((o) => o.j !== i)
        .sort((a, b) => a.d - b.d)
        .slice(0, 2);
      for (const { j } of order) {
        const key = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (seen.has(key)) continue;
        seen.add(key);
        e.push([i, j]);
      }
    }
    return { nodes: n, edges: e };
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setPulseId((x) => x + 1), 900);
    return () => window.clearInterval(id);
  }, []);

  const activeEdge = edges[pulseId % edges.length];

  return (
    <div className="hud-network">
      <svg ref={svgRef} viewBox="0 0 100 100" className="hud-network__svg">
        {edges.map(([a, b], i) => {
          const isActive = activeEdge && activeEdge[0] === a && activeEdge[1] === b;
          return (
            <line
              key={i}
              x1={nodes[a].x}
              y1={nodes[a].y}
              x2={nodes[b].x}
              y2={nodes[b].y}
              stroke={isActive ? "rgba(160, 250, 250, 0.95)" : "rgba(102, 240, 240, 0.28)"}
              strokeWidth={isActive ? 0.8 : 0.4}
            />
          );
        })}
        {nodes.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={p.r}
              fill="rgba(102, 240, 240, 0.18)"
              stroke="rgba(160, 240, 240, 0.85)"
              strokeWidth={0.5}
            />
            <circle cx={p.x} cy={p.y} r={p.r * 0.4} fill="#aef0f0" />
          </g>
        ))}
      </svg>
      <div className="hud-network__legend">
        <span>NODES {nodes.length.toString().padStart(2, "0")}</span>
        <span>LINK ↗</span>
      </div>
    </div>
  );
}
