// Pure layout math for the desk HUD. Two responsibilities, no React:
//
//   solveWall      grid fractions -> 6 flat panel rects (in wall CSS px)
//   wallToCylinder a flat point   -> a 3D position + yaw on a vertical cylinder
//
// Keeping these pure makes the reflow easy to reason about and test: the
// store owns the fractions, this turns them into geometry, and the curvature
// slider just feeds a different radius into wallToCylinder.

export type CellId =
  | "profile"
  | "skills"
  | "featured"
  | "education"
  | "experience"
  | "contact";

/** Dock icon size when a panel is minimized. */
export const MINIMIZED_ICON_PX = 52;
export const MINIMIZED_ICON_GAP_PX = 10;

/** Stable order for stacking minimized icons below contact. */
export const CELL_ORDER: CellId[] = [
  "profile",
  "skills",
  "featured",
  "education",
  "experience",
  "contact",
];

export interface WallFractions {
  /** Column widths as fractions of the available width; must sum to 1. */
  colFrac: [number, number, number];
  /** Fraction of the left column's height given to its top cell. */
  leftSplit: number;
  /** Fraction of the education/experience stack given to education. */
  rightSplit: number;
  /** Fixed height of the contact strip in CSS px. */
  contactHeightPx: number;
}

export interface WallSize {
  /** Total wall width in CSS px. */
  width: number;
  /** Total wall height in CSS px. */
  height: number;
  /** Gap between adjacent cells in CSS px. */
  gap: number;
}

export interface Cell {
  id: CellId;
  /** Center X in wall px, 0 = wall center, +right. */
  x: number;
  /** Center Y in wall px, 0 = wall center, +up. */
  y: number;
  width: number;
  height: number;
}

/** Width available for the three columns after the two inter-column gaps. */
export function availableWidth(size: WallSize): number {
  return size.width - 2 * size.gap;
}

/** Height available for a split column's two cells after their one gap. */
export function availableColumnHeight(size: WallSize): number {
  return size.height - size.gap;
}

function isMinimized(minimized: CellId[] | undefined, id: CellId): boolean {
  return minimized?.includes(id) ?? false;
}

/** Where the contact strip sits — used as the dock anchor even when minimized. */
export function contactDockAnchor(
  f: WallFractions,
  size: WallSize,
): { x: number; bottomY: number; width: number } {
  const availW = availableWidth(size);
  const availH = availableColumnHeight(size);
  const w2 = f.colFrac[2] * availW;
  const left0 = -size.width / 2;
  const left1 = left0 + f.colFrac[0] * availW + size.gap;
  const left2 = left1 + f.colFrac[1] * availW + size.gap;
  const cx2 = left2 + w2 / 2;

  const rightBottomH = Math.min(f.contactHeightPx, availH - availH * 0.22);
  const bottomCy = (h: number) => -size.height / 2 + h / 2;
  const centerY = bottomCy(rightBottomH);

  return {
    x: cx2,
    bottomY: centerY - rightBottomH / 2,
    width: w2,
  };
}

/** Minimized panels become square icons stacked below the contact strip. */
export function dockMinimizedCells(
  f: WallFractions,
  size: WallSize,
  minimized: CellId[],
): Cell[] {
  const ordered = CELL_ORDER.filter((id) => minimized.includes(id));
  if (ordered.length === 0) return [];

  const anchor = contactDockAnchor(f, size);
  let cursorY = anchor.bottomY - MINIMIZED_ICON_GAP_PX;

  return ordered.map((id) => {
    cursorY -= MINIMIZED_ICON_PX / 2;
    const cell: Cell = {
      id,
      x: anchor.x,
      y: cursorY,
      width: MINIMIZED_ICON_PX,
      height: MINIMIZED_ICON_PX,
    };
    cursorY -= MINIMIZED_ICON_PX / 2 + MINIMIZED_ICON_GAP_PX;
    return cell;
  });
}

export function solveWall(
  f: WallFractions,
  size: WallSize,
  minimized: CellId[] = [],
): Cell[] {
  const availW = availableWidth(size);
  const availH = availableColumnHeight(size);

  const w0 = f.colFrac[0] * availW;
  const w1 = f.colFrac[1] * availW;
  const w2 = f.colFrac[2] * availW;

  // Column left edges, walking left -> right from the wall's left side.
  const left0 = -size.width / 2;
  const left1 = left0 + w0 + size.gap;
  const left2 = left1 + w1 + size.gap;

  const cx0 = left0 + w0 / 2;
  const cx1 = left1 + w1 / 2;
  const cx2 = left2 + w2 / 2;

  const profileMin = isMinimized(minimized, "profile");
  const skillsMin = isMinimized(minimized, "skills");
  const featuredMin = isMinimized(minimized, "featured");
  const educationMin = isMinimized(minimized, "education");
  const experienceMin = isMinimized(minimized, "experience");
  const contactMin = isMinimized(minimized, "contact");

  const leftTopH = f.leftSplit * availH;
  const leftBottomH = availH - leftTopH;
  const rightBottomH = Math.min(f.contactHeightPx, availH - availH * 0.22);

  // Stacked cells: top cell sits in the upper half, bottom in the lower.
  const topCy = (h: number) => size.height / 2 - h / 2;
  const bottomCy = (h: number) => -size.height / 2 + h / 2;

  const cells: Cell[] = [];

  if (!profileMin && !skillsMin) {
    cells.push(
      { id: "profile", x: cx0, y: topCy(leftTopH), width: w0, height: leftTopH },
      {
        id: "skills",
        x: cx0,
        y: bottomCy(leftBottomH),
        width: w0,
        height: leftBottomH,
      },
    );
  } else if (!profileMin) {
    cells.push({
      id: "profile",
      x: cx0,
      y: 0,
      width: w0,
      height: availH,
    });
  } else if (!skillsMin) {
    cells.push({
      id: "skills",
      x: cx0,
      y: 0,
      width: w0,
      height: availH,
    });
  }

  if (!featuredMin) {
    cells.push({ id: "featured", x: cx1, y: 0, width: w1, height: size.height });
  }

  const showEducation = !educationMin;
  const showExperience = !experienceMin;
  const showContact = !contactMin;
  const rightCount =
    Number(showEducation) + Number(showExperience) + Number(showContact);

  if (rightCount === 1) {
    if (showContact) {
      cells.push({
        id: "contact",
        x: cx2,
        y: bottomCy(rightBottomH),
        width: w2,
        height: rightBottomH,
      });
    } else if (showEducation) {
      cells.push({
        id: "education",
        x: cx2,
        y: 0,
        width: w2,
        height: availH,
      });
    } else {
      cells.push({
        id: "experience",
        x: cx2,
        y: 0,
        width: w2,
        height: availH,
      });
    }
  } else if (rightCount === 2) {
    if (showEducation && showExperience) {
      const topH = f.rightSplit * availH;
      const bottomH = availH - topH;
      cells.push(
        {
          id: "education",
          x: cx2,
          y: topCy(topH),
          width: w2,
          height: topH,
        },
        {
          id: "experience",
          x: cx2,
          y: bottomCy(bottomH),
          width: w2,
          height: bottomH,
        },
      );
    } else if (showEducation && showContact) {
      const eduH = size.height - rightBottomH - size.gap;
      cells.push(
        {
          id: "education",
          x: cx2,
          y: topCy(eduH),
          width: w2,
          height: eduH,
        },
        {
          id: "contact",
          x: cx2,
          y: bottomCy(rightBottomH),
          width: w2,
          height: rightBottomH,
        },
      );
    } else {
      const expH = availH - rightBottomH;
      cells.push(
        {
          id: "experience",
          x: cx2,
          y: topCy(expH),
          width: w2,
          height: expH,
        },
        {
          id: "contact",
          x: cx2,
          y: bottomCy(rightBottomH),
          width: w2,
          height: rightBottomH,
        },
      );
    }
  } else if (rightCount === 3) {
    const stackAvail = size.height - rightBottomH - 2 * size.gap;
    const eduH = f.rightSplit * stackAvail;
    const expH = stackAvail - eduH;
    cells.push(
      {
        id: "education",
        x: cx2,
        y: topCy(eduH),
        width: w2,
        height: eduH,
      },
      {
        id: "experience",
        x: cx2,
        y: size.height / 2 - eduH - size.gap - expH / 2,
        width: w2,
        height: expH,
      },
      {
        id: "contact",
        x: cx2,
        y: bottomCy(rightBottomH),
        width: w2,
        height: rightBottomH,
      },
    );
  }

  return cells;
}

export interface PanelTransform {
  /** Offset from the wall anchor in CSS px units (scale to world later). */
  position: [number, number, number];
  /** Rotation about the vertical axis, radians. */
  yaw: number;
}

// Map a point on the flat wall (u across, v up, CSS px) onto a vertical
// cylinder of radius R. Concave toward the seated viewer: the center sits
// furthest and the wings sweep forward (toward the camera, +Z) and angle
// inward — the same way the curved desk wraps around you. Large R → flat
// plane; small R → tight wrap. yaw is the tangent so panels stay flush.
export function wallToCylinder(u: number, v: number, R: number): PanelTransform {
  const theta = u / R;
  return {
    position: [R * Math.sin(theta), v, R * (1 - Math.cos(theta))],
    yaw: -theta,
  };
}
