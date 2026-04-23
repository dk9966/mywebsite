# Stroke drain animation for any font — execution plan

A future agent should be able to read this end-to-end and start working without re-deriving anything. Update the relevant section as each phase ships.

---

## TL;DR

The drain animation draws each letter down its **spine** (centerline / medial axis), not around its outline. We need this to work for any TTF font, not just hand-coded glyphs. The whole problem reduces to one function:

```ts
extractCenterlines(font: Font, char: string): Stroke[]
```

where `Stroke = [number, number][]`. Once that exists, the rest is wiring.

**Outline tracing is forbidden.** See `.cursor/rules/no-outline-mode.mdc`. Don't propose it, don't reason about it.

---

## Mental model

A glyph from `opentype.js` is a closed shape (a polygon, possibly with holes for letters like O, P, A). Its medial axis is the curve through the middle of every stroke of the letter. If we extract that curve as ordered polylines, the existing `stroke-dashoffset` drain animation works on any font.

We compute the medial axis by **rasterize → thin → vectorize**:

1. Fill the glyph onto a high-res bitmap.
2. Iteratively erode it to a 1-pixel-wide skeleton (Zhang–Suen thinning).
3. Walk that skeleton as a graph, splitting at junctions and pruning short spurs.
4. Simplify each polyline (Ramer–Douglas–Peucker).

We picked raster thinning over geometric approaches (straight skeleton, Voronoi medial axis) because it works on every font, handles holes natively, has mature JS implementations, and quality scales with raster resolution.

---

## Current state of the codebase

- `src/components/DrainText.tsx` — the component. **Phase 3 shipped.** Renders each glyph as N animated `<path>` elements (one per `DrainStroke`), drained via `stroke-dashoffset`. Calls `getCenterlineDrain(font, char)` per glyph; layout/projection/timeline are all driven from `DrainPlan`.
- `src/components/DrainText.css` — styles. Mode-toggle styles already removed.
- `src/lib/centerline.ts` — **Phases 1 + 2 + 4 ship.** `extractCenterlines(font, char, opts?) → { strokes, bbox, elapsedMs }` (Phase 1: rasterize + Zhang–Suen thinning + RDP, em-units Y-up). `planLiquidDrain(strokes, opts?) → { strokes: DrainStroke[], totalDistance, hole }` (Phase 2: graph build + drain hole + Dijkstra + virtual zero-weight bridges across disconnected components). `getCenterlineDrain(font, char, opts?) → { extract, plan }` (Phase 4: module-level `Map` cache keyed on `${family}:${char}`). All pure / referentially transparent given the cache is module-scoped.
- ~~`src/lib/svgPaths.ts`, `src/lib/strokeFont.ts`~~ — both deleted in Phase 3. Centerline extraction replaced the hand-coded `STROKE_FONT`, and the renderer no longer needs `commandsToD`/`DrainDirection`.
- `src/types/opentype.d.ts` — extended with `Path.toPathData`, `Glyph.path`, `Glyph.getBoundingBox`, `Font.names`. Extend further if you need more fields.
- `src/types/skeleton-tracing-js.d.ts` — type shim for the tracer.
- `plans/centerline-debug.html` + `plans/centerline-debug.ts` — visual harness. Open `/plans/centerline-debug.html` in dev. Switch fonts at the top. Six columns: pure / skeleton / overlay / per-stroke / drain plan / meta. The drain-plan column colors strokes blue (drains first) -> red (drains last) and marks the chosen drain hole with a white ring. **Use this to validate Phase 5 tuning.**
- `public/fonts/VT323-Regular.ttf`, `JetBrainsMono-Regular.ttf` — the two test fonts.
- `plans/font-picks.html` — gallery of candidate fonts. Use it to pick more test fonts.
- `.cursor/rules/no-outline-mode.mdc` — the outline-mode ban. Always applied.

Libraries installed: `opentype.js`, `gsap`, `skeleton-tracing-js`. Add new deps with `pnpm`.

---

## Execution loop

For every phase below, follow this loop:

1. **Decide if plan mode is needed.** Trigger: *are there ≥2 reasonable ways to do this with different downstream consequences?* If yes, switch to plan mode. If no, just build.
2. **Implement.**
3. **Validate against the phase's success criteria.**
4. **Update this file.** Mark the phase done. Note any decisions that surprised you. Adjust later phases if needed.
5. **Commit** (only when explicitly asked by the user).

### Plan mode strategy across phases

- **Phase 1 → plan mode.** Real architecture choices (library vs hand-roll, raster res, output shape, hole handling, spur pruning).
- **Phases 2 + 3 + 4 → one plan mode session, ship together.** Once strokes exist, ordering, rendering, and caching all hang off the same data structure. One session is plenty.
- **Phase 5 → no plan mode.** Empirical tuning. Iterate live.
- **Phase 6 → plan mode if pursued.** Real direction change (ribbon polygons instead of stroked paths).

---

## Phase 1 — Centerline extractor [DONE]

**Goal.** Implement `extractCenterlines(font, char): ExtractResult` in `src/lib/centerline.ts`.

**Locked decisions.**
- Library: `skeleton-tracing-js` (LingDong, MIT, zero deps, ~5 KB). Does Zhang–Suen thinning + polyline tracing in one pass. We added our own RDP simplify + minimum-length cull on top so Phase 5 still has knobs.
- Output coord space: glyph-local em units, same convention as opentype.js `glyph.path` (Y up). Cache key in Phase 4 stays `${family}:${char}` — no `FONT_SIZE`. `DrainText` will need a Y-flip when rendering (see "Coordinate gotcha" below).
- Holes (O, P, A, 0, 8): handled automatically by filling with the **even-odd** rule on canvas. No special code needed.

**Final constants** (in `src/lib/centerline.ts` — `DEFAULTS`):
- `RASTER_RES = 512` px/em.
- `SIMPLIFY_EPS = 0.01` (em-relative; ≈ 10 em units at 1000 unitsPerEm).
- `MIN_STROKE_LEN = 0.03` (em-relative; ≈ 30 em units).
- `RASTER_PAD = 4` px.

**Output shape.** `extractCenterlines` returns `{ strokes: Stroke[]; bbox; elapsedMs }`. `Stroke = [number, number][]`. Returning bbox + elapsed lets callers position glyphs and lets the debug page show timings without re-querying.

**Coordinate gotcha (read this before Phase 3).** opentype.js's `glyph.path` is in typographic coords (Y points up; an "A" has its apex at NEGATIVE Y values relative to the baseline). SVG is Y-down. The debug page wraps everything in `<g transform="scale(1 -1)">` and shifts viewBox accordingly. `DrainText` must do the same — or use `glyph.getPath(x, baseline, fontSize)` and feed those coords into a separate path-projection helper. The extractor itself does NOT flip; its output stays in the source font's native coord space so Phase 4 caching is portable.

**Files shipped.**
- `src/lib/centerline.ts` — pipeline + RDP + length filter.
- `src/types/skeleton-tracing-js.d.ts` — type shim for the library.
- `src/types/opentype.d.ts` — extended with `Path.toPathData`, `Glyph.path`, `Glyph.getBoundingBox`, `Font.names`.
- `plans/centerline-debug.html` + `plans/centerline-debug.ts` — five-column debug grid (pure / skeleton / overlay / per-stroke colored / meta) for uppercase, lowercase, digits, and common symbols. Switch fonts at the top.
- `vite.config.ts` — added `plans/centerline-debug.html` as a `rollupOptions.input` entry. Reachable in dev at `/plans/centerline-debug.html`.
- `package.json` — added `skeleton-tracing-js` dep.

**Validation results (against the success criteria).**
- **VT323**: every uppercase + lowercase + digit + symbol produces a recognizable spine. Holes resolve as loops. Periods, commas, colons, apostrophes survive as short polylines (single pixel after thinning, which the tracer still emits).
- **JetBrainsMono**: clean spines across the whole grid. No missing strokes, no major spurs.
- **Performance**: ~18 ms per glyph average at 512 px/em (whole 81-glyph grid renders + extracts in ~1.5 s in dev). Comfortably under the 50 ms target.
- **Purity**: same input → same output. No global state, no random seeds.

**Where the output diverges from `STROKE_FONT`.** STROKE_FONT was hand-coded with "logical" strokes (A = V + crossbar = 2 strokes). The extractor returns "true" topology, splitting at every junction (A = 4–6 segments: each leg of the V split at the crossbar, plus serif feet on monospace fonts as their own short strokes). Phase 2's geodesic-from-hole approach makes this a non-issue: adjacent collinear segments share an endpoint, their drain windows abut exactly, and the front speed matches across the boundary, so the drain reads as continuous regardless of how many sub-segments the extractor produced.

**Tricky glyphs / known weaknesses.**
- Serif feet on JetBrainsMono show up as short orange spurs branching off the main spines. They're above `MIN_STROKE_LEN` so they're kept. Phase 5 may want to bump that threshold per font.
- VT323's blocky terminals create small spur loops at stroke ends because the rasterized pixel-edge becomes a tiny ring after thinning. Visible in the per-stroke column as small orange/red bits at letter terminals.
- Glyphs with two disconnected components (lowercase i, j, !, ?, :, ;) produce one polyline per component as expected. The dot survives because skeleton-tracing-js's chunk tracer still emits a fragment for a 1-pixel residue.

**No changes made to** `DrainText.tsx`, `svgPaths.ts`, or `strokeFont.ts`. Phase 1 is purely additive.

---

## Phase 2 — Liquid-drain ordering [DONE]

**Goal.** Make each glyph drain like one continuous stroke, not N independent fades. The line of text should feel like a single fluid being emptied to the right, glyph after glyph.

**Mental model.** Imagine the centerline network as a system of pipes filled with liquid. There is a single drain hole on the right side of each glyph. Gravity pulls right. As the liquid empties through the hole, the part of the network *farthest* from the hole runs dry first; the part *nearest* the hole runs dry last. The drain front sweeps inward through the network at a constant speed measured in arc length, and naturally splits at junctions.

Worked example, capital "A" with the hole at the bottom-right tip:
- Bottom-left tip is the farthest point (geodesic = right diagonal + left diagonal). It empties first.
- Drain front climbs up the left diagonal toward the apex.
- The moment the front passes the left junction of the crossbar, the crossbar starts draining from its left end toward its right end.
- Front reaches the apex, then descends the right diagonal toward the hole.
- Bottom-right tip empties last.

Notice this gives one visually continuous sweep rather than "stroke 1, then stroke 2, then stroke 3."

**Approach.**

1. **Build the stroke graph.** Nodes = stroke endpoints, snapped to a small spatial tolerance (~`SIMPLIFY_EPS`) so endpoints that the extractor emitted as separate-but-coincident actually merge. Edges = the strokes themselves, weighted by polyline arc length.
2. **Pick the drain hole.**
   - Prefer degree-1 nodes (terminals). Score them by `x` (rightmost wins), tiebreak by `-y` (bottom-most wins, in Y-up em coords).
   - If there are no terminals (closed shape: O, a loop), pick the rightmost point on any edge and split that edge at that point to introduce a virtual terminal.
3. **Geodesic distance from the hole.** Run Dijkstra from the hole node to every other node. Result: `dist[node]` = shortest path length through the network back to the hole.
4. **Orient and schedule each stroke.** For an edge with endpoints `u`, `v`:
   - `dFar  = max(dist[u], dist[v])`, `dNear = min(dist[u], dist[v])`.
   - Reverse the polyline if needed so it runs FAR → NEAR. SVG `stroke-dashoffset` animating `0 → L` then erases the far side first.
   - Compute the stroke's drain window in glyph-normalized time `t ∈ [0, 1]`:
     - `Dmax = max over all nodes of dist[node]`
     - `tStart = 1 - dFar  / Dmax` (front first touches this stroke)
     - `tEnd   = 1 - dNear / Dmax` (front leaves this stroke)
   - Because the front speed is constant in arc length, each stroke's drain duration `tEnd - tStart` is proportional to its own length. Junction overlap (two branches draining at the same time) falls out for free.
5. **Disconnected components** (`i`, `j`, `!`, `?`, `:`, `;`). Run the algorithm per component but normalize all components against the GLYPH's `Dmax`, not their own. The dot of an `i` is small and far-right of nothing, so its component's local `Dmax` would be ~0 and it would drain instantly. Sharing `Dmax` makes the dot drain at the right moment relative to the stem.

**Output shape.** The simple "sorted array" idea no longer fits because junctions create parallel drain windows. Replace it with a richer plan:

```ts
type DrainStroke = {
  points: Stroke;   // oriented FAR -> NEAR
  length: number;   // arc length, for stroke-dasharray
  tStart: number;   // [0, 1] within this glyph's drain
  tEnd: number;     // [0, 1], > tStart
};

type DrainPlan = {
  strokes: DrainStroke[];
  totalDistance: number;   // Dmax, useful for cross-glyph pacing
  hole: [number, number];  // for debug overlay
};

planLiquidDrain(strokes: Stroke[], opts?: { snapTol?: number }): DrainPlan
```

The old `DrainDirection`-projection idea drops out entirely. The drain "direction" is now encoded in the choice of hole. If we ever want left-drain instead, swap the hole picker (leftmost terminal) and Dijkstra recomputes everything.

**Junction merging — punt.** The Phase 1 open question (merge colinear degree-2 chains) becomes less important here. The geodesic timing already makes adjacent collinear pieces visually continuous: they share an endpoint, their `t` windows abut exactly, and the front speed matches across the boundary. Revisit only if junctions show visible stutter on real fonts.

**Files.**
- Add to `src/lib/centerline.ts`: `buildStrokeGraph`, `pickDrainHole`, `planLiquidDrain`. Keep them pure and exportable so the debug page can render the intermediate graph.
- Extend `plans/centerline-debug.html` with a "drain plan" column: color each stroke by `tStart` on a blue→red ramp (blue = drains first, red = drains last) and mark the chosen hole with a dot. This is how you'll validate the algorithm before Phase 3.

**Success criteria.**
- "A": bottom-left first, apex mid-drain, bottom-right last. Crossbar starts the moment the front passes its left junction.
- "O": one continuous loop drain. Front splits at the point opposite the hole and the two halves meet at the hole.
- "H": both verticals drain in whichever direction the geodesic implies (the one nearest to the chosen rightmost terminal drains last). Crossbar drain direction follows naturally.
- "i": the dot finishes draining around the same time as the top of the stem, not instantly at `t=0`.
- No visible "pop" at junctions — the drain front speed is the same on either side of every junction.

**Cross-glyph orchestration (called out here, implemented in Phase 3).** The "line of text drained as one continuous stroke" feel comes from chaining glyph drains left-to-right. Simplest scheme: glyph N+1 starts at `(glyph N's tEnd) - overlap` so the leftmost stroke of N+1 begins while the rightmost (last) stroke of N is still finishing. Use each glyph's `totalDistance` to scale per-glyph drain duration so wider glyphs take proportionally longer — that keeps front speed constant across the whole line, not just within a glyph.

**What shipped.**

- `planLiquidDrain(strokes, opts?) -> DrainPlan` in [src/lib/centerline.ts](../src/lib/centerline.ts). Pure function; no DOM, no font dep. Output shape matches the plan: `DrainStroke { points (FAR -> NEAR), length, tStart, tEnd }`, `totalDistance`, `hole`.
- Helpers: `buildStrokeGraph` (spatial-hash endpoint snap + BFS components), `pickDrainHole`, `splitEdgeAtVertex` (closed-loop fallback), `bridgeComponents`, `dijkstra` (linear-scan PQ — graphs are <100 nodes).
- Debug column added to [plans/centerline-debug.ts](centerline-debug.ts) and grid widened to 6 columns in [centerline-debug.html](centerline-debug.html). Each stroke colored by `tStart` on a blue (drains first) -> red (drains last) HSL ramp; near end has a colored dot; chosen drain hole gets a white ring; meta cell shows `Dmax` in em.

**Decisions resolved during implementation.**

- **`snapTol` default = `0.5%` of input bbox diagonal**, with floor of `1e-6`. Using a fraction of the bbox keeps the tolerance scale-invariant across fonts with different `unitsPerEm` (1000 vs 2048). At default, snaps anything within ~5 em-units for a typical glyph — generous enough to absorb sub-pixel rounding from the rasterizer, tight enough not to merge real distinct nodes.
- **Drain hole picker = nearest terminal to the middle of the bbox right edge (Y-up euclidean)**, not the plain rightmost-then-bottommost lex sort the plan originally proposed. The lex sort fails when the dot of an `i` extends even 1 unit further right than the stem (the dot wins, which is wrong); also, anchoring at the right-edge midpoint produces a roughly horizontal drain sweep rather than a gravitational pull toward the bottom-right corner. Closed-loop fallback is the same scheme — rightmost polyline vertex closest to mid-Y.
- **Disconnected components are linked by virtual euclidean bridges (MST over components) with weight = 0**, then a single Dijkstra runs from the hole through the augmented graph. The plan's original prescription (each component dijkstras locally, all divide by global Dmax) put the dot of an `i` at the END of the drain (`t≈1`), which contradicted the success criterion. Bridges with **zero** weight specifically (rather than the actual euclidean distance) make the front pass between components instantaneously — `dot.tEnd === stem-top.tStart` exactly, no visible pause. The bridges are skipped when emitting `DrainStroke`s.

**Validation results.**

Numeric validation against hand-crafted topologies for `A`, `O`, `H`, `i`:

- `A` (bbox 0..700 × 0..700, hole at (700, 0)): bot-left tip drains at `t=0`; both upper-leg halves at `[0.179, 0.318]` and `[0.179, 0.682]` (front splits at apex); crossbar `[0.318, 0.682]` (matches the boundaries of the legs); bot-right last at `t=1`. Crossbar oriented left -> right. PASS.
- `O` (closed ellipse, no terminals — fell back to splitting at the rightmost vertex): hole at `(650, 350)`, antipode at `(50, 350)` drains at `t=0` running both directions, meets at the hole at `t=1`. PASS.
- `H`: hole at `(600, 0)`, both `(0, 0)` and `(0, 700)` drain at `t=0` simultaneously (the front splits both ways up the left vertical). Crossbar fills `[0.269, 0.731]`. PASS.
- `i`: hole at stem bottom `(300, 0)`, `Dmax = 553.9`. Dot drains in `[0, 0.097]`, stem starts immediately at `0.097` and finishes at `1`. **Continuous front, zero gap.** PASS.

Visual validation in `/plans/centerline-debug.html`: page renders both fonts cleanly, no console errors, ~1.6 s per font for the 81-glyph grid (includes both extraction and planning). The drain-plan column shows the expected blue->red gradient with hole markers in the right place across uppercase, lowercase, digits, and symbols.

**Known quirks / things to watch in Phase 3.**

- The colinear-merge punt (Phase 1 open question about merging degree-2 chains) holds up. The `tStart`/`tEnd` windows of split-but-collinear chains abut exactly — the front speed is consistent across the boundary, so visually it reads as a single continuous stroke.
- For glyphs with more than one component (`i`, `j`, `!`, `?`, `:`, `;`), the bridge picker chooses the closest node-pair across components. For typical fonts this lands sensibly (dot bottom -> stem top). If a font has an unusual layout (e.g. a `j` where the dot is offset such that the closest stem node is mid-stem rather than top-of-stem), the front would jump to mid-stem and skip the upper portion. Haven't seen this in the test fonts — flag it if it appears.
- Closed-loop split (`O`, `Q`, `0`, `8`) introduces a fresh node mid-edge. The two replacement edges share the new node and are emitted as separate strokes in the output. The `t` windows abut exactly at the split point, so this is visually invisible.
- `splitEdgeAtVertex` marks the original edge with `removed: true` rather than re-indexing the edges array, so adjacency lists and edge ids stay stable. `planLiquidDrain` filters by `removed` and `virtual` when emitting strokes.

---

## Phase 3 — Wire into DrainText [DONE]

**Goal.** Replace the clip-rect wipe in `DrainText.tsx` with real centerline rendering.

**Approach (as built).**
- Removed `clipPath` + `<rect>` + filled `<path>` + `drainEndAttrs` + `DRAIN_DIRECTIONS`. Component renders one `<path>` per `DrainStroke`, oriented FAR -> NEAR.
- Coordinate handling: project each centerline point from em/Y-up to SVG/Y-down at the point level (`sx = cursorX + ex * fontScale`, `sy = baseline - ey * fontScale`) instead of wrapping each glyph in a flipped `<g>`. Keeps `stroke-dasharray` in plain pixel units and avoids the `vector-effect: non-scaling-stroke` dasharray-in-user-units pitfall.
- Each path gets `stroke-dasharray = "${pixelLength} ${pixelLength + STROKE_WIDTH * 4}"` (single dash followed by an explicit large gap) and animates `stroke-dashoffset` from `0` to `pixelLength + STROKE_WIDTH * 2`. The wide gap prevents the dash pattern from wrapping back into a visible residue at the path's NEAR end after overshoot — without it, a small fragment of the next dash bleeds in once the offset crosses the path length.
- GSAP timeline: per-glyph `subDuration = DRAIN_DURATION * (g.totalDistanceEm / referenceDistanceEm)` where `referenceDistanceEm = max(g.totalDistanceEm)` over the word. Each stroke runs `tl.to(path, { attr: { 'stroke-dashoffset': pixelLength + STROKE_WIDTH * 2 }, duration: subDuration * (tEnd - tStart), ease: 'none' }, glyphStart + tStart * subDuration)`. Linear ease is by design — any other warps the front speed across junctions and across glyphs.
- Glyph sub-timelines are positioned left-to-right with `glyphStart[N] = glyphStart[N-1] + subDuration[N-1] * (1 - LETTER_OVERLAP)`. `LETTER_OVERLAP = 0.6` gave a continuous liquid front across both rows of the test word.

**Final constants** in [src/components/DrainText.tsx](../src/components/DrainText.tsx):
- `STROKE_COLOR = "#00dffc"`
- `STROKE_WIDTH = 4` (px in SVG user units)
- `HOLD_BEFORE_DRAIN = 0.5` s
- `DRAIN_DURATION = 1.5` s — time the widest glyph in the word takes to drain
- `LETTER_OVERLAP = 0.6` — fraction of previous glyph drain that the next overlaps

**Renderer-level filter.** Strokes with `pixelLength < STROKE_WIDTH` are dropped before render. They come from RDP residues and junction-split fragments where a 1–2 em sub-stroke renders as a stuck dot (`stroke-dasharray = 0` falls back to "no dashing" in the SVG spec, leaving the round line cap as a permanent dot). Their drain timing windows are sub-perceptual anyway.

**Files touched.**
- [src/components/DrainText.tsx](../src/components/DrainText.tsx) — rewritten around `getCenterlineDrain` + per-stroke dashoffset animation.
- [src/lib/strokeFont.ts](../src/lib/strokeFont.ts) — deleted. The extractor replaces it.
- [src/lib/svgPaths.ts](../src/lib/svgPaths.ts) — deleted. `commandsToD` and `DrainDirection` were the only exports and both are gone.
- [src/components/DrainText.css](../src/components/DrainText.css) — unchanged.
- [plans/centerline-debug.html](centerline-debug.html) + [plans/centerline-debug.ts](centerline-debug.ts) — added a 7th `rendered` column that mirrors `DrainText`'s renderer at `FONT_SIZE = 120` (same `STROKE_WIDTH`, gap-padded `stroke-dasharray`, post-filter strokes only). The meta column gained a `rendered N -K` line — `N` is how many strokes survive the renderer-level filter, `K` is how many got dropped (in orange when non-zero). Use this column to spot fonts where the `pixelLength < STROKE_WIDTH` cull eats perceptually significant strokes.

**Validation results.**
- Test word `ABCDEFGHIJKLM\nNOPQRSTUVWXYZ` at `FONT_SIZE = 120` (VT323): full drain runs ~10.4 s, end-state is fully empty (no residual dots), drain front sweeps left-to-right across both rows continuously without per-letter "pulses".
- Scrubber, play/pause, time readout still work — they were already generic over `tlRef.current`.
- `rg 'clipPath|drainEndAttrs|STROKE_FONT|commandsToD|DrainDirection|svgPaths|strokeFont|rectRefs|DRAIN_DIRECTIONS' src/` returns nothing.

---

## Phase 4 — Caching [DONE]

**Goal.** Don't re-extract the same glyph twice.

**Surface.** [src/lib/centerline.ts](../src/lib/centerline.ts) gained:
- `getCenterlineDrain(font, char, opts?) -> { extract: ExtractResult; plan: DrainPlan }` — memoised wrapper around `extractCenterlines + planLiquidDrain`. Key: `${font.names?.fontFamily?.en ?? 'unknown'}:${char}`.
- `clearCenterlineCache()` — used by the debug page so the meta column reflects real wall time on each render rather than ~0 ms cache hits.
- `centerlineCacheSize()` — for ad-hoc instrumentation.

Both `extract` and `plan` live in one entry: they always travel together at call sites and `planLiquidDrain` is sub-ms, so a single Map and a single lookup is simpler than two layers of caching. `FONT_SIZE` is **not** in the key — centerlines stay in em units, projection happens at render time, so the same entry serves any size.

Both call sites updated:
- [src/components/DrainText.tsx](../src/components/DrainText.tsx) — calls `getCenterlineDrain(font, char)` instead of the two-step pipeline.
- [plans/centerline-debug.ts](centerline-debug.ts) — same, with a `clearCenterlineCache()` before each grid render so timings stay honest.

**Validation results.**
- Boots clean, end-to-end drain renders correctly through the cached path.
- Re-rendering the same word does zero extraction work after warmup (verified by inspection of the trivial `Map.get -> return` early-out).

---

## Phase 5 — Per-font tuning

**Goal.** Visual quality across the picked fonts.

**Approach.** No plan mode. Open `plans/centerline-debug.html`, eyeball each font, tune the four constants in `centerline.ts`'s `DEFAULTS` per font preset:
- `rasterRes` (px/em) — current default 512
- `simplifyEps` (em-relative RDP tolerance) — current default 0.01
- `minStrokeLen` (em-relative) — current default 0.03; bump to ~0.06 to drop serif feet on JetBrainsMono
- `rasterPad` (px) — current default 4

Store as a small `Record<fontFamily, ExtractOpts>` with `DEFAULTS` as fallback. Look up via `font.names?.fontFamily?.en`.

**Known issues from Phase 1 to address here.**
- VT323's blocky terminals produce small spur loops. Try bumping `minStrokeLen` to ~0.05 for VT323.
- JetBrainsMono's serif feet show as short branches. Bumping `minStrokeLen` will help; alternatively rely on the Phase 2 colinear-merge to absorb them.

**Success criteria.** Every font we plan to use looks clean. Document any font that resists tuning so we can drop it.

---

## Phase 6 (optional) — Tapered strokes

Pursue only if constant-width centerlines feel too uniform across fonts with strong weight contrast (Orbitron, Major Mono).

**Goal.** Strokes that match the source font's weight variation.

**Approach.** During thinning, record the distance from each skeleton pixel to the nearest outline pixel (this is the local stroke radius). Render each polyline as a polygon ribbon (build left/right offset polygons from the centerline using those radii) instead of using SVG `stroke`.

This is its own plan mode session if pursued.

---

## Status

- [x] Phase 0: remove outline mode, add project rule
- [x] Phase 1: centerline extractor (skeleton-tracing-js + RDP, em-unit output, debug grid at `plans/centerline-debug.html`)
- [x] Phase 2: liquid-drain ordering (Dijkstra from mid-right-nearest terminal; zero-weight bridges across disconnected components)
- [x] Phase 3: integrate into DrainText (per-stroke `<path>` + `stroke-dashoffset`, point-level Y-flip projection, gap-padded dasharray to dodge wrap-around residue, `LETTER_OVERLAP = 0.6`)
- [x] Phase 4: caching (`getCenterlineDrain` in `src/lib/centerline.ts`, keyed on `${family}:${char}`, holds `{ extract, plan }`)
- [ ] Phase 5: per-font tuning
- [ ] Phase 6: tapered strokes (optional)
