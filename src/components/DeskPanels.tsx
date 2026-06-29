import type { ReactNode } from "react";
import { useMemo } from "react";
import { contact } from "../data/resume";
import {
  availableColumnHeight,
  availableWidth,
  solveWall,
  wallToCylinder,
  type Cell,
  type CellId,
  type WallSize,
} from "../lib/panelWall";
import { useDeskLayout } from "../stores/deskLayout";
import {
  ContactHeaderIcons,
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
  experience: { title: "Experiences", tag: "04", content: <ExperiencePanel /> },
  contact: {
    title: "Contact",
    tag: "05",
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
  const contactHeightPx = useDeskLayout((s) => s.contactHeightPx);

  const adjustColBoundary = useDeskLayout((s) => s.adjustColBoundary);
  const adjustLeftSplit = useDeskLayout((s) => s.adjustLeftSplit);

  const wall = useMemo<WallSize>(
    () => ({ width: wallWidthPx, height: wallHeightPx, gap: WALL_GAP_PX }),
    [wallWidthPx, wallHeightPx],
  );

  const cells = useMemo(
    () => solveWall({ colFrac, leftSplit, contactHeightPx }, wall),
    [colFrac, leftSplit, contactHeightPx, wall],
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
      experience: {
        left: (f) => adjustColBoundary(1, -f),
      },
      contact: {
        left: (f) => adjustColBoundary(1, -f),
      },
    }),
    [adjustColBoundary, adjustLeftSplit],
  );

  const onResize =
    (id: CellId) => (handle: ResizeHandle, dW: number, dH: number) => {
      const { h, v } = handleEdges(handle);
      const rules = edgeRules[id];
      if (h && rules[h]) rules[h]!(dW / availW);
      if (v && rules[v]) rules[v]!(dH / availH);
    };

  return (
    <group position={[wallAnchor.x, wallAnchor.y, wallAnchor.z]}>
      {cells.map((cell: Cell) => {
        const bent = wallToCylinder(cell.x, cell.y, curveRadiusPx);
        const position: [number, number, number] = [
          bent.position[0] * WORLD_PER_CSS_PX,
          bent.position[1] * WORLD_PER_CSS_PX,
          bent.position[2] * WORLD_PER_CSS_PX,
        ];
        const meta = CELL_META[cell.id];
        return (
          <HudScreen
            key={cell.id}
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
            headerAside={meta.headerAside}
            headerLinks={meta.headerLinks}
            headerOnly={meta.headerOnly}
            compactPadding={meta.compactPadding}
            onResizeDelta={onResize(cell.id)}
          >
            {meta.content ?? null}
          </HudScreen>
        );
      })}
    </group>
  );
}
