import { useMemo, type CSSProperties } from "react";
import { useBootTuning } from "../stores/bootTuning";
import type { BootPartId } from "../lib/bootParts";
import "./BootFx.css";

// Boot-phase scaffolding overlaid on each HUD panel: power-flash, static
// bursts, scanline sweeps, a grid that snaps on, cascading diagnostic text,
// arc reticles that draw themselves in, and readout bars. Everything is
// timed in CSS off --boot-delay (set on the panel face) and the whole layer
// fades at the global stabilize mark, then unmounts when boot ends.
//
// Rendered inside every curved slice of a panel; slices mount in the same
// commit so their animation clocks agree and the copies line up seamlessly.

const DIAG_POOL = [
  "SYS CHECK 0x2F41 ......... OK",
  "PWR RAIL 3.3V ........ LOCK",
  "LINK 04 :: SYNC",
  "MEM MAP 82% ........... OK",
  "IO BUS INIT ......... 0x1A",
  "CAL GRID Δ 0.02",
  "THERM ......... NOMINAL",
  "NET HANDSHAKE ........ ACK",
  "GFX CTX 07 ............ UP",
  "SENSOR ARRAY ....... ONLINE",
  "CRC PASS 0xB77E",
  "CLK SYNC ± 4ns",
];

function pickDiagLines(seed: number, count: number): string[] {
  const out: string[] = [];
  for (let i = 0; i < count; i++) {
    out.push(DIAG_POOL[(seed * 3 + i * 5) % DIAG_POOL.length]);
  }
  return out;
}

export function BootFx({
  seed,
  compact = false,
}: {
  seed: number;
  /** Short strips (contact) skip the large scaffolding elements. */
  compact?: boolean;
}) {
  const parts = useBootTuning((s) => s.parts);
  const partOn = (id: BootPartId) =>
    parts[id].visible ? "boot-fx__part--on" : "";
  const scaffoldFade = parts.scaffoldFade.visible;

  const lines = useMemo(
    () => pickDiagLines(seed, compact ? 3 : 7),
    [seed, compact],
  );

  return (
    <div
      className={[
        "boot-fx",
        scaffoldFade ? "boot-fx--scaffold-fade" : "",
      ]
        .join(" ")
        .trim()}
      aria-hidden="true"
    >
      <div className={`boot-fx__flash ${partOn("powerFlash")}`} />
      <div className={`boot-fx__noise ${partOn("staticNoise")}`} />
      <div className={`boot-fx__scan boot-fx__scan--a ${partOn("scanA")}`} />
      <div className={`boot-fx__scan boot-fx__scan--b ${partOn("scanB")}`} />
      {!compact ? (
        <div className={`boot-fx__grid ${partOn("alignGrid")}`} />
      ) : null}
      <div
        className={[
          compact ? "boot-fx__diag boot-fx__diag--compact" : "boot-fx__diag",
          partOn("diagText"),
        ]
          .join(" ")
          .trim()}
      >
        {lines.map((line, i) => (
          <span
            className="boot-fx__diag-line"
            style={{ "--i": i } as CSSProperties}
            key={`${line}-${i}`}
          >
            {line}
          </span>
        ))}
      </div>
      {!compact ? (
        <svg
          className={`boot-fx__reticle ${partOn("reticle")}`}
          viewBox="0 0 120 120"
        >
          <circle className="boot-fx__arc boot-fx__arc--outer" cx="60" cy="60" r="52" pathLength={100} />
          <circle className="boot-fx__arc boot-fx__arc--mid" cx="60" cy="60" r="38" pathLength={100} />
          <circle className="boot-fx__arc boot-fx__arc--inner" cx="60" cy="60" r="24" pathLength={100} />
        </svg>
      ) : null}
      {!compact ? (
        <div className={`boot-fx__readout ${partOn("readoutBars")}`}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span
              className="boot-fx__bar"
              style={{ "--i": i } as CSSProperties}
              key={i}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** The "system online" sweep — separate from .boot-fx so it survives the
 *  stabilize fade-out. Delay comes from --pulse-delay on the panel face. */
export function BootPulse() {
  const visible = useBootTuning((s) => s.parts.onlinePulse.visible);
  return (
    <div
      className={`boot-fx-pulse ${visible ? "boot-fx__part--on" : ""}`}
      aria-hidden="true"
    />
  );
}
