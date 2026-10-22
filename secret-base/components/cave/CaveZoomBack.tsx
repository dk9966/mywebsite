import { useCaveZoom } from "./caveZoom";

/** Shown while zoomed in on a platform: back out to the whole cave (Esc does the same). */
export function CaveZoomBack() {
  const platform = useCaveZoom((s) => s.platform);
  const zoomTo = useCaveZoom((s) => s.zoomTo);
  const shown = platform !== null;
  return (
    <button
      type="button"
      onClick={() => zoomTo(null)}
      aria-hidden={!shown}
      tabIndex={shown ? 0 : -1}
      style={{
        position: "absolute",
        left: 20,
        top: 18,
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "9px 14px 9px 12px",
        borderRadius: 8,
        background: "rgba(5, 12, 16, 0.72)",
        border: "1px solid rgba(156, 248, 248, 0.3)",
        color: "rgba(174, 234, 238, 0.9)",
        font: "11px ui-monospace, 'SF Mono', Menlo, monospace",
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        cursor: "pointer",
        backdropFilter: "blur(6px)",
        opacity: shown ? 1 : 0,
        transform: shown ? "translateX(0)" : "translateX(-8px)",
        pointerEvents: shown ? "auto" : "none",
        transition: "opacity 240ms ease, transform 240ms ease",
      }}
    >
      <span aria-hidden style={{ fontSize: 14, lineHeight: 1 }}>←</span>
      Back
      <span style={{ opacity: 0.5, letterSpacing: "0.08em" }}>Esc</span>
    </button>
  );
}
