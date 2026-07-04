import type { ReactNode } from "react";
import { useEffect, useMemo } from "react";
import { contact } from "../data/resume";
import {
  BOOT_TOTAL_MS,
  bootPanelStartMs,
  bootSkipped,
  panelPulseDelayForCell,
  startBootClock,
  type PanelBoot,
} from "../lib/bootSequence";
import { useBootClock } from "../stores/bootClock";
import {
  availableColumnHeight,
  availableWidth,
  dockMinimizedCells,
  solveWall,
  wallToCylinder,
  type Cell,
  type CellId,
  type WallSize,
} from "../lib/panelWall";
import { useDeskLayout } from "../stores/deskLayout";
import {
  ContactHeaderIcons,
  EducationPanel,
  ExperiencePanel,
  FeaturedPanel,
  ProfilePanel,
  SkillsPanel,
} from "./deskPanelContent";
import HudScreen, { type ResizeHandle } from "./HudScreen";

// Must match HudScreen's WORLD_PER_CSS_PX so px sizes and px positions share
// one scale.
const WORLD_PER_CSS_PX = 0.002;

// Gap between adjacent cells on the flat wall, in CSS px.
const WALL_GAP_PX = 28;

type CellMeta = {
  title: string;
  tag: string;
  content?: ReactNode;
  headerAside?: ReactNode;
  headerLinks?: { href: string; label: string }[];
  /** Title row only — no body slot (contact strip). */
  headerOnly?: boolean;
  hideHeader?: boolean;
  /** Tighter inset so short strips (contact) don't clip their content. */
  compactPadding?: boolean;
};

const CELL_META: Record<CellId, CellMeta> = {
  profile: { title: "Profile", tag: "01", content: <ProfilePanel /> },
  skills: { title: "Skills", tag: "02", content: <SkillsPanel /> },
  featured: {
    title: "Projects",
    tag: "03",
    content: <FeaturedPanel />,
  },
  education: { title: "Education", tag: "04", content: <EducationPanel /> },
  experience: { title: "Experiences", tag: "05", content: <ExperiencePanel /> },
  contact: {
    title: "Contact",
    tag: "06",
    headerAside: <ContactHeaderIcons />,
    headerOnly: true,
    headerLinks: contact.map((c) => ({ href: c.href, label: c.label })),
  },
};

type EdgeRules = {
  left?: (frac: number) => void;
  right?: (frac: number) => void;
  top?: (frac: number) => void;
  bottom?: (frac: number) => void;
};

// Deterministic flicker seeds so each screen blinks to its own rhythm.
const BOOT_SEEDS: Record<CellId, number> = {
  profile: 1,
  skills: 2,
  featured: 3,
  education: 4,
  experience: 5,
  contact: 6,
};

// True from mount until the boot sequence has fully played out. Arms the
// shared clock (WebGL envelopes + CSS delays measure from the same commit)
// and tears all boot scaffolding down after BOOT_TOTAL_MS.
function useBootActive(): boolean {
  const elapsedMs = useBootClock((s) => s.elapsedMs);
  const paused = useBootClock((s) => s.paused);
  const scrubbing = useBootClock((s) => s.scrubbing);

  useEffect(() => {
    if (bootSkipped()) return;
    startBootClock();
  }, []);

  if (bootSkipped()) return false;
  if (paused || scrubbing) return true;
  return elapsedMs < BOOT_TOTAL_MS;
}

function handleEdges(handle: ResizeHandle): {
  h?: "left" | "right";
  v?: "top" | "bottom";
} {
  switch (handle) {
    case "tl":
      return { h: "left", v: "top" };
    case "tr":
      return { h: "right", v: "top" };
    case "bl":
      return { h: "left", v: "bottom" };
    case "br":
      return { h: "right", v: "bottom" };
    case "left":
      return { h: "left" };
    case "right":
      return { h: "right" };
    case "top":
      return { v: "top" };
    case "bottom":
      return { v: "bottom" };
  }
}

export default function DeskPanels() {
  const curveRadiusPx = useDeskLayout((s) => s.curveRadiusPx);
  const bgOpacity = useDeskLayout((s) => s.bgOpacity);
  const bgBlur = useDeskLayout((s) => s.bgBlur);
  const headerFontPx = useDeskLayout((s) => s.headerFontPx);
  const wallAnchor = useDeskLayout((s) => s.wallAnchor);
  const wallWidthPx = useDeskLayout((s) => s.wallWidthPx);
  const wallHeightPx = useDeskLayout((s) => s.wallHeightPx);
  const colFrac = useDeskLayout((s) => s.colFrac);
  const leftSplit = useDeskLayout((s) => s.leftSplit);
  const rightSplit = useDeskLayout((s) => s.rightSplit);
  const contactHeightPx = useDeskLayout((s) => s.contactHeightPx);
  const minimizedPanels = useDeskLayout((s) => s.minimizedPanels);

  const bootActive = useBootActive();

  const adjustColBoundary = useDeskLayout((s) => s.adjustColBoundary);
  const adjustLeftSplit = useDeskLayout((s) => s.adjustLeftSplit);
  const adjustRightSplit = useDeskLayout((s) => s.adjustRightSplit);

  const wall = useMemo<WallSize>(
    () => ({ width: wallWidthPx, height: wallHeightPx, gap: WALL_GAP_PX }),
    [wallWidthPx, wallHeightPx],
  );

  const fractions = useMemo(
    () => ({ colFrac, leftSplit, rightSplit, contactHeightPx }),
    [colFrac, leftSplit, rightSplit, contactHeightPx],
  );

  const cells = useMemo(
    () => solveWall(fractions, wall, minimizedPanels),
    [fractions, wall, minimizedPanels],
  );

  const dockCells = useMemo(
    () => dockMinimizedCells(fractions, wall, minimizedPanels),
    [fractions, wall, minimizedPanels],
  );

  const availW = availableWidth(wall);
  const availH = availableColumnHeight(wall);

  const edgeRules: Record<CellId, EdgeRules> = useMemo(
    () => ({
      profile: {
        right: (f) => adjustColBoundary(0, f),
        bottom: (f) => adjustLeftSplit(f),
      },
      skills: {
        right: (f) => adjustColBoundary(0, f),
        top: (f) => adjustLeftSplit(-f),
      },
      featured: {
        left: (f) => adjustColBoundary(0, -f),
        right: (f) => adjustColBoundary(1, f),
      },
      education: {
        left: (f) => adjustColBoundary(1, -f),
        bottom: (f) => adjustRightSplit(f),
      },
      experience: {
        left: (f) => adjustColBoundary(1, -f),
        top: (f) => adjustRightSplit(-f),
      },
      contact: {
        left: (f) => adjustColBoundary(1, -f),
      },
    }),
    [adjustColBoundary, adjustLeftSplit, adjustRightSplit],
  );

  const onResize =
    (id: CellId) => (handle: ResizeHandle, dW: number, dH: number) => {
      const { h, v } = handleEdges(handle);
      const rules = edgeRules[id];
      if (h && rules[h]) rules[h]!(dW / availW);
      if (v && rules[v]) rules[v]!(dH / availH);
    };

  const renderPanel = (cell: Cell, dockIcon: boolean) => {
    const bent = wallToCylinder(cell.x, cell.y, curveRadiusPx);
    const position: [number, number, number] = [
      bent.position[0] * WORLD_PER_CSS_PX,
      bent.position[1] * WORLD_PER_CSS_PX,
      bent.position[2] * WORLD_PER_CSS_PX,
    ];
    const meta = CELL_META[cell.id];
    // Staggered power-on per panel; the final pulse sweeps the wall left →
    // right, so its delay follows the cell's horizontal position.
    const boot: PanelBoot | undefined =
      bootActive && !dockIcon
        ? {
            startMs: bootPanelStartMs(cell.id),
            pulseDelayMs: panelPulseDelayForCell(cell.x, wallWidthPx),
            seed: BOOT_SEEDS[cell.id],
          }
        : undefined;
    return (
      <HudScreen
        key={dockIcon ? `dock-${cell.id}` : cell.id}
        position={position}
        yaw={bent.yaw}
        widthPx={cell.width}
        heightPx={cell.height}
        title={meta.title}
        tag={meta.tag}
        curveRadiusPx={curveRadiusPx}
        bgOpacity={bgOpacity}
        bgBlur={bgBlur}
        headerFontPx={headerFontPx}
        hideHeader={meta.hideHeader}
        headerAside={dockIcon ? undefined : meta.headerAside}
        headerLinks={dockIcon ? undefined : meta.headerLinks}
        headerOnly={dockIcon ? false : meta.headerOnly}
        compactPadding={meta.compactPadding}
        dockIcon={dockIcon}
        boot={boot}
        onResizeDelta={dockIcon ? undefined : onResize(cell.id)}
      >
        {meta.content ?? null}
      </HudScreen>
    );
  };

  return (
    <group position={[wallAnchor.x, wallAnchor.y, wallAnchor.z]}>
      {cells.map((cell) => renderPanel(cell, false))}
      {dockCells.map((cell) => renderPanel(cell, true))}
    </group>
  );
}
