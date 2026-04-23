/**
 * Optional fixed graph-node positions for `getCenterlineDrain` (glyph-local em
 * coords, opentype Y-down). Endpoints of extracted skeleton strokes snap to
 * the nearest entry within `snapTol` when building the drain graph.
 *
 * Keys are single characters. Omitted characters use only automatic snapping.
 * See `planLiquidDrain` / `PlanOpts.manualNodes` in `centerline.ts`.
 */
export const DRAIN_MANUAL_NODES_BY_CHAR: Partial<
  Record<string, [number, number][]>
> = {};
