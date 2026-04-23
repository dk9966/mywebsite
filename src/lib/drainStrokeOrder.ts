/**
 * Manual stroke play order for `DrainText`. Keys are single characters (`"A"`, `"7"`).
 *
 * Each value lists **indices** into that glyph’s stroke list **after** the
 * renderer drops strokes shorter than `STROKE_WIDTH` — the same order strokes
 * are built from `plan.strokes` in `DrainText`’s `computeLayout`. The array must
 * be a permutation of `0 … n-1` where `n` is that filtered count.
 *
 * When a key is present and valid, those strokes play **in that order**, one
 * after another with equal time per stroke. Omitted characters keep the
 * default liquid-drain order from `planLiquidDrain`.
 *
 * To pin junction positions in the drain graph, see `drainManualNodes.ts`
 * (`manualNodes` on `getCenterlineDrain`). To learn `n` and try orders, use
 * `plans/centerline-debug.html` (meta column stroke count) or log
 * `getCenterlineDrain(font, char).plan.strokes` filtered the same way as
 * `DrainText`.
 */
export const DRAIN_STROKE_INDEX_ORDER_BY_CHAR: Record<string, number[]> = {
  // Example — only applies if that letter has exactly 3 surviving strokes:
  // D: [2, 0, 1],
};
