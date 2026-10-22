import { useEffect, useRef, useState } from "react";
import { useThree } from "@react-three/fiber";
import { create } from "zustand";
import BootClockDriver from "../../../src/components/BootClockDriver";
import DeskPanels from "../../../src/components/DeskPanels";
import { BOOT_TOTAL_MS, bootElapsedMs, bootSkipped } from "../../../src/lib/bootSequence";
import { useDeskLayout } from "../../../src/stores/deskLayout";
import type { Vec3 } from "./caveAssets";
import layoutFile from "./panelLayout.json";

const SAVE_ROUTE = "/__save-cave-panels";
const MIN_SCALE = 0.25;
const MAX_SCALE = 3;

/** Must match DeskPanels / HudScreen: one CSS px of panel is this many metres. */
const WORLD_PER_CSS_PX = 0.002;

/**
 * The desk page's table (`/models/table.glb`, at the origin of `/`): the back
 * edge of its top, centred across its width, and that width.
 */
const DESK_BACK_EDGE: Vec3 = [0, 1.05, -1.65];
const DESK_WIDTH = 3.3;

/**
 * The central console ("Rig | table and machinery" in
 * platform-controls/cave-platform-sliders.blend), in glTF space: the back edge
 * of its desk top, centred across its width (rig origin + (-0.05, 1.24) in the
 * rig's ground plane, at the desk top, Blender z 7.21), the rig's yaw (its +Y,
 * away from the platform centre, is the desk's back) and the desk top's width.
 */
const CONSOLE_BACK_EDGE: Vec3 = [23.074, 7.21, -2.762];
const CONSOLE_YAW = -0.5633;
const CONSOLE_WIDTH = 2.59;

/** Root-scene metres → cave metres, so the wall keeps its size relative to the desk. */
const DESK_TO_CONSOLE = CONSOLE_WIDTH / DESK_WIDTH;

/**
 * The console's back edge sits this far from the rig origin (the `v` axis of
 * the profile below, which points away from the platform centre).
 */
const BACK_EDGE_V = 1.24;

/**
 * Front face of the machinery on the desk (everything above the desk's own
 * keys and screens, Blender z >= 7.3): per 0.15 m column across the desk
 * (offset from the desk's centre), the nearest distance from the rig origin.
 */
const MACHINERY_FRONT: [u: number, v: number][] = [
  [-1.35, 1.05], [-1.2, 0.845], [-1.05, 0.87], [-0.9, 0.944], [-0.75, 1.104], [-0.6, 1.182],
  [-0.45, 1.222], [-0.3, 1.193], [-0.15, 1.178], [0, 1.487], [0.15, 1.166], [0.3, 1.165],
  [0.45, 1.183], [0.6, 1.178], [0.75, 1.036], [0.9, 1.032], [1.05, 0.809], [1.2, 0.772], [1.35, 0.969],
];
/** Backdrop blur behind the glass, CSS px (the desk page uses 3): strong enough that the machinery only reads as a soft background. */
const PANEL_BLUR_PX = 14;
/** Gap kept between the bent glass and the nearest machinery, in cave metres. */
const MACHINERY_CLEARANCE = 0.12;
/** The wall's bottom edge floats this far above the desk top, clear of its keys and screens. */
const WALL_LIFT = 0.09;

/**
 * Distance of the wall's centre line from the rig origin that keeps the whole
 * bent wall in front of the machinery. The glass bows toward the viewer by
 * `R (1 - cos(u / R))` at `u` from its centre, so the binding point is
 * wherever the machinery comes forward most relative to that bow.
 */
function wallCentreV(radius: number): number {
  let v = Infinity;
  for (const [u, front] of MACHINERY_FRONT) {
    v = Math.min(v, front + radius * (1 - Math.cos(u / radius)) - MACHINERY_CLEARANCE);
  }
  return v;
}

/** Size of the whole panel wall, 1 = the desk page's proportions; saved to panelLayout.json. */
const useCavePanels = create<{ scale: number; setScale: (scale: number) => void }>((set) => ({
  scale: layoutFile.scale,
  setScale: (scale) => set({ scale: Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale)) }),
}));

/**
 * The cave renders on demand; keep frames coming while the panels power on so
 * their WebGL glass and bezels animate with the CSS boot effects.
 */
function BootFrames() {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    if (bootSkipped()) return;
    let id = 0;
    const loop = () => {
      invalidate();
      if (bootElapsedMs() < BOOT_TOTAL_MS) id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [invalidate]);
  return null;
}

/**
 * The desk page's HUD wall, standing on the central console's desk top with
 * the same proportions as on `/` (the desk's frame maps onto the console's,
 * scaled by their widths), but moved forward until the whole bent wall is clear
 * of the machinery, which then reads through its blurred glass. The size
 * slider scales the wall about its bottom centre and re-clears the machinery.
 */
export function CavePanels() {
  const scale = useCavePanels((s) => s.scale);
  const wallAnchor = useDeskLayout((s) => s.wallAnchor);
  const wallHeightPx = useDeskLayout((s) => s.wallHeightPx);
  const curveRadiusPx = useDeskLayout((s) => s.curveRadiusPx);
  useEffect(() => useDeskLayout.setState({ bgBlur: PANEL_BLUR_PX }), []);
  // The wall's own bottom-centre, in desk units; its depth is replaced below by
  // the machinery-clearing one, and it stands a little above the desk top.
  const pivot: Vec3 = [wallAnchor.x, wallAnchor.y - (wallHeightPx * WORLD_PER_CSS_PX) / 2, wallAnchor.z];
  const radius = curveRadiusPx * WORLD_PER_CSS_PX * DESK_TO_CONSOLE * scale;
  // Local +z is toward the platform centre, so a smaller distance from the rig is a larger z.
  const centreZ = (BACK_EDGE_V - wallCentreV(radius)) / DESK_TO_CONSOLE;

  return (
    <>
      <BootClockDriver />
      <BootFrames />
      <group position={CONSOLE_BACK_EDGE} rotation-y={CONSOLE_YAW} scale={DESK_TO_CONSOLE}>
        <group
          position={[pivot[0] - DESK_BACK_EDGE[0], pivot[1] - DESK_BACK_EDGE[1] + WALL_LIFT / DESK_TO_CONSOLE, centreZ]}
          scale={scale}
        >
          <group position={[-pivot[0], -pivot[1], -pivot[2]]}>
            <DeskPanels />
          </group>
        </group>
      </group>
    </>
  );
}

/** Dev only: the panel wall's size slider; changes save to panelLayout.json. */
export function CavePanelControls() {
  const scale = useCavePanels((s) => s.scale);
  const setScale = useCavePanels((s) => s.setScale);
  const [status, setStatus] = useState("");
  const saveTimer = useRef(0);

  // The JSON on disk may be newer than this bundle (Vite does not reload on save).
  useEffect(() => {
    let live = true;
    fetch(SAVE_ROUTE)
      .then((response) => (response.ok ? response.json() : null))
      .then((saved: { scale?: number } | null) => {
        if (live && typeof saved?.scale === "number") setScale(saved.scale);
      })
      .catch(() => {});
    return () => { live = false; };
  }, [setScale]);

  const change = (next: number) => {
    setScale(next);
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      const body = JSON.stringify({ scale: useCavePanels.getState().scale }, null, 2);
      try {
        const response = await fetch(SAVE_ROUTE, { method: "POST", headers: { "Content-Type": "application/json" }, body });
        setStatus(response.ok ? "saved" : "save failed");
      } catch {
        setStatus("save failed");
      }
    }, 300);
  };

  return (
    <label
      style={{
        position: "absolute",
        right: 16,
        bottom: 14,
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 12px",
        borderRadius: 8,
        background: "rgba(5, 12, 16, 0.72)",
        border: "1px solid rgba(156, 248, 248, 0.25)",
        color: "rgba(174, 234, 238, 0.85)",
        font: "11px ui-monospace, 'SF Mono', Menlo, monospace",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
      }}
    >
      Panel size
      <input
        type="range"
        min={MIN_SCALE}
        max={MAX_SCALE}
        step={0.01}
        value={scale}
        onChange={(e) => change(Number(e.target.value))}
        style={{ width: 160, accentColor: "#9cf8f8" }}
      />
      <span style={{ minWidth: 40, textAlign: "right" }}>{scale.toFixed(2)}×</span>
      <span style={{ minWidth: 48, opacity: 0.6 }}>{status}</span>
    </label>
  );
}
