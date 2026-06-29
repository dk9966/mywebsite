// Pure layout math for the desk HUD. Two responsibilities, no React:
//
//   solveWall      grid fractions -> 5 flat panel rects (in wall CSS px)
//   wallToCylinder a flat point   -> a 3D position + yaw on a vertical cylinder
//
// Keeping these pure makes the reflow easy to reason about and test: the
// store owns the fractions, this turns them into geometry, and the curvature
// slider just feeds a different radius into wallToCylinder.

export type CellId =
  | "profile"
  | "skills"
  | "featured"
  | "experience"
  | "contact";

export interface WallFractions {
  /** Column widths as fractions of the available width; must sum to 1. */
  colFrac: [number, number, number];
  /** Fraction of the left column's height given to its top cell. */
  leftSplit: number;
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

export function solveWall(f: WallFractions, size: WallSize): Cell[] {
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

  const leftTopH = f.leftSplit * availH;
  const leftBottomH = availH - leftTopH;
  const rightBottomH = Math.min(f.contactHeightPx, availH - availH * 0.22);
  const rightTopH = availH - rightBottomH;

  // Stacked cells: top cell sits in the upper half, bottom in the lower.
  const topCy = (h: number) => size.height / 2 - h / 2;
  const bottomCy = (h: number) => -size.height / 2 + h / 2;

  return [
    { id: "profile", x: cx0, y: topCy(leftTopH), width: w0, height: leftTopH },
    {
      id: "skills",
      x: cx0,
      y: bottomCy(leftBottomH),
      width: w0,
      height: leftBottomH,
    },
    { id: "featured", x: cx1, y: 0, width: w1, height: size.height },
    {
      id: "experience",
      x: cx2,
      y: topCy(rightTopH),
      width: w2,
      height: rightTopH,
    },
    {
      id: "contact",
      x: cx2,
      y: bottomCy(rightBottomH),
      width: w2,
      height: rightBottomH,
    },
  ];
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
