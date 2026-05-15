# Tron Lines on the Table

How animated Tron lines get applied to the Blender-authored table mesh. The seam between Blender (authorship) and JS (animation) is a single typed contract: `GridPath[]`.

## The story in plain English

Today's Tron lines come from hand-coded waypoint arrays in `src/lib/gridBuilder.ts`. They draw on a flat XY grid and have no idea the table exists.

To put the lines **on the table**, we have to give the same animator a new source of waypoints — waypoints that follow the table's real geometry. The cleanest place to author those waypoints is **Blender**, because:

- the table already lives there,
- you can vertex-snap the lines to actual edges/seams,
- taste decisions (which edges trace, how many, where they branch) belong with the modeler, not with code.

So the rule is:

> **Blender draws the lines. JS animates them. Neither side reaches into the other's job.**

The handoff is a `.glb` containing the table plus a `TronLines` collection of polylines. JS loads the `.glb`, pulls the polylines out by name, parses a spawn delay from each name, and feeds the result into the existing animator (`tickAnims` in `TronGrid.tsx`) as `GridPath[]` — the same shape `gridBuilder.buildScene` already returns.

That means **the animator does not change**. The only new code is a loader and a tiny rewire of `TronGrid` so it can accept paths from a GLB instead of (or in addition to) the hardcoded `buildScene`.

## Zoom-in 1: The contract

A "Tron line" is a **mesh edge-poly in Blender**, in a dedicated collection, named per a stable convention. No JSON sidecar, no custom properties. The name *is* the schema.

### Collection

```
Scene
├── Table              (your existing table objects, any structure)
└── TronLines          (one flat collection, one node per line)
    ├── TronLine_001_0.0
    ├── TronLine_002_1.5
    └── TronLine_003_2.0
```

### Name grammar

```
TronLine_<order>_<delaySec>[_<tag>...]
```

- `order` — zero-padded integer used as a sort key. Lower order draws first if everything else ties.
- `delaySec` — float seconds, becomes `GridPath.spawnTime`. Examples: `0.0`, `1.5`, `2.25`.
- `tag` — optional underscore-separated suffix tokens reserved for future orchestration metadata (e.g. `twin`, `hero`). Ignored by the loader today, but the loader will preserve them on the returned object so future code can read them without renaming everyone.

### Geometry shape

- One mesh per line, **edges only, no faces** — Blender's glTF "Loose Edges" exporter converts these to glTF `LINES` primitives, which Three.js loads as `THREE.LineSegments`.
- Edges must form a single connected **open polyline** (a chain of vertices `v0 - v1 - ... - vN`). No branching, no loops.
- The polyline has a direction of travel. The endpoint where you want the head to **start** must be the one with only one neighbor; the loader walks edges from there.
- Branches are **separate** `TronLine_*` entries that may share endpoints in space.

This is the load-bearing decision: a single open chain per line lets the JS loader recover travel order with a trivial adjacency walk, no full graph reconstruction. Authorship complexity is paid in Blender, not at runtime.

### Why edges and not curves / tubes

- glTF does not preserve Bezier curves.
- A tube/ribbon mesh would force JS to back out a centerline, which is fragile.
- Edge-only meshes survive the trip intact via the exporter's "Loose Edges" option.

## Zoom-in 2: Blender authoring recipe

1. Open the table `.blend`.
2. Right-click in the Outliner → **New Collection** → rename to `TronLines`. Keep it as a sibling of your table collection, not nested.
3. For each line:
   1. Either:
      - `Add → Curve → Bezier`, shape it, then `Object → Convert → Mesh`, **or**
      - `Add → Mesh → Plane`, delete all but one vertex, then `E` to extrude along edges/seams.
   2. Snap to the table's real geometry: `Shift+Tab` to toggle snap, set snap target to **Vertex** or **Edge**, then move/extrude with `G`.
   3. Walk the polyline in the **direction you want the leader to travel**. The first vertex is the head's birthplace.
   4. Rename per the convention. Example: `TronLine_001_0.0` for the hero line that fires at t=0.
4. Export:
   - `File → Export → glTF 2.0 (.glb/.gltf)`
   - Format: **glTF Binary (.glb)**
   - Include: **Visible Objects** (or **Selected Objects** if you only ship the table + TronLines collections).
   - Geometry: keep "Apply Modifiers" on. UVs/Normals on. Tangents only if you'll do normal mapping later.
   - **Geometry → check "Loose Edges"**. Without this, your TronLine meshes will be silently dropped because they have no faces.
   - Save to **`public/models/table.glb`**.
5. Verify before handing off (per `.cursor/rules/instructions-and-blender-verify.mdc`):
   - Drag the `.glb` into [https://gltf.report](https://gltf.report) (or re-import into a fresh Blender).
   - Confirm the `TronLines` nodes exist by name, the count matches, and each is a mesh with one open edge chain.

### Don't do this

- **Don't trace every edge of the table.** `plans/tron-base-mesh.md` calls for restraint. 3–5 hero lines beats 30 noisy ones.
- **Don't put orchestration in names.** Density curves, twin pairing, hero pacing live in JS per `plans/tron-lines-orchestration.md`. The name only carries identity + spawn delay.
- **Don't leave Bezier curves un-converted.** glTF will not export the table's lines as line geometry from a Curve object the way we want — Convert → Mesh first.
- **Don't close the polyline into a loop unless you actually want a closed trace.** The animator handles both, but loops are visually different.

## Zoom-in 3: JS side

### New file: `src/lib/tronLinesFromGLB.ts`

A pure function that takes a loaded GLTF root and returns `GridPath[]` in the existing shape.

```ts
import * as THREE from "three";
import type { GridPath, Vec3 } from "./gridBuilder";

export function tronLinesFromGLB(root: THREE.Object3D): GridPath[] {
  const paths: GridPath[] = [];

  root.traverse((obj) => {
    if (!obj.name.startsWith("TronLine_")) return;
    const mesh = obj as THREE.Mesh;
    if (!mesh.geometry) return;

    const parsed = parseTronLineName(obj.name);
    if (!parsed) return;

    const waypoints = extractOrderedWaypoints(mesh);
    if (waypoints.length < 2) return;

    paths.push({
      waypoints,
      spawnTime: parsed.delaySec,
    });
  });

  // Stable order so consumers can rely on it.
  paths.sort((a, b) => a.spawnTime - b.spawnTime);
  return paths;
}
```

Two helpers, both internal:

- `parseTronLineName(name)` — splits on `_`, validates `TronLine`, parses `order` (int) and `delaySec` (float). Returns null on mismatch so unknown nodes are silently skipped.
- `extractOrderedWaypoints(line)` — input is a `THREE.LineSegments` whose geometry has a position attribute and (typically) an index buffer of edge pairs `[a, b, c, d, ...]`. Builds an adjacency map, finds the endpoint with degree 1, walks the chain to the other endpoint, applies `mesh.matrixWorld`, returns `Vec3[]` in travel order.

Why adjacency, not "trust the index order": Blender's "Loose Edges" exporter writes edges sorted by their internal mesh-edge index, **not** by traversal order. Two users drawing the same polyline can get different index buffers. The adjacency walk normalizes that.

Edge cases handled now, not later:

- Node name doesn't parse: skip silently.
- No geometry / no position attribute: skip with a `console.warn`.
- Polyline has fewer than 2 vertices: skip with a warn.
- More than two endpoints (branching): warn, return the longest chain from one endpoint and ignore the rest.
- Zero endpoints (closed loop): warn, pick vertex 0 as start and walk one direction; user can re-author if it was unintended.

### Edit: `src/components/TronGrid.tsx`

Accept `paths` as an optional prop. If provided, use them. Otherwise fall back to `buildScene` so the standalone Tron page keeps working untouched.

```ts
type TronGridProps = {
  paths?: GridPath[];
};

export default function TronGrid({ paths }: TronGridProps = {}) {
  const gridPaths = useMemo(
    () => paths ?? buildScene(42),
    [paths],
  );
  // ...everything else unchanged
}
```

### New mount path (the table scene, separate from today's Tron grid demo)

The standalone `src/tron-lines-main.tsx` stays as-is — it remains the playground for the abstract grid. The **table** scene gets its own React entry (or component) that:

1. Loads `public/models/table.glb` via `useGLTF`.
2. Renders the table meshes from the GLB.
3. Calls `tronLinesFromGLB(scene)` to get `GridPath[]`.
4. Mounts `<TronGrid paths={paths} />` with the result.

If `public/models/table.glb` is missing or has no `TronLine_*` nodes (the day-zero state), the page just renders the existing grid demo behavior or an empty group. No crash.

## Zoom-in 4: Coexistence with existing systems

- `gridBuilder.buildScene` stays. It's the default for the abstract demo.
- `tickAnims`, `AnimatedLine`, color/tip logic — all untouched.
- `useLineConfig` (color, opacity, speed, bloom) applies identically to both sources.
- The orchestration ideas in `plans/tron-lines-orchestration.md` (density curves, twins, hero pacing) layer on **after** waypoint extraction. They modify `spawnTime` and bookkeeping; they do not touch the path source.

That's the proof that this seam is tasteful: **adding the table source did not require knowing anything about how lines animate, and adding orchestration later will not require knowing where lines came from.**

## Phase status

Done:

- Decided: Blender authors lines as named edge-meshes; JS loads via stable contract.
- Decision documented in this file.
- Loader implemented at `src/lib/tronLinesFromGLB.ts`. Walks any `THREE.Object3D` tree, finds `TronLine_<order>_<delaySec>[_<tag>...]` nodes, recovers travel order from the glTF `LINES` index buffer via adjacency walk, and returns `GridPath[]` in the existing shape. Skips malformed lines with `console.warn` instead of throwing.
- `TronGrid` now accepts an optional `paths?: GridPath[]` prop and falls back to `buildScene(42)` when omitted. Existing `src/tron-lines-main.tsx` continues to render the abstract grid unchanged.
- Blender authoring script landed at `blender/table/apply_tron_lines.py`. It creates a top-level `TronLines` collection in `Main Scene` and authors 5 hero polylines hand-routed against `build_table.py`'s geometry constants:
  - `TronLine_001_0.0` — outer arc of the top slab (49 verts), the hero sweep from +X tip via apex to -X tip.
  - `TronLine_002_1.0` — front-right chord pin (2 verts), inner to outer rim at angle 0.
  - `TronLine_003_1.4` — front-left chord pin (2 verts), mirror of `_002` at angle π.
  - `TronLine_004_2.0` — foot brace arc (49 verts), low slow counter-sweep at floor level, opposite direction.
  - `TronLine_005_2.5` — vertical climb (2 verts) along the radially-outward face of `Leg_1` (front-right leg at angle π/8).
- Script is idempotent: re-running clears any prior `TronLine_*` objects and regenerates. Run with `SAVE_BLEND_AFTER=1` to persist into `main.blend`.
- Exported to `public/models/table.glb` (~315 KB, 19 nodes). `use_active_scene=True` is required — without it the glTF exporter walks every scene in the file and pulls in stale cross-scene selections.
- GLB verified via direct binary parse: all 5 `TronLine_*` nodes present, `mode=1` (LINES), index buffers are sequential edge pairs, vertex positions match expected Z-up → Y-up converted coordinates.

Done (this phase):

- New mount: `tron-table.html` + `src/tron-table-main.tsx` (parallel to `tron-lines.html`). Wired into `vite.config.ts` as the `tronTable` entry.
- New component: `src/components/TronTable.tsx`. Loads `public/models/table.glb` via `useGLTF`, calls `tronLinesFromGLB(scene)` once to extract paths, and feeds them into `<TronGrid paths={paths} showBackgroundGrid={false} />`. **The GLB's meshes never enter the React scene graph** — the file is loaded only for its polyline data.
- New prop on `TronGrid`: `showBackgroundGrid?: boolean` (default `true`). The 80-unit gridlines made for the abstract demo are wrong at meter scale; the table mount opts out.
- Table-scale config overrides applied once on mount via `useLineConfig.set(...)`:
  - `cursorSpeed: 2.0` (was 8 for the 80-unit grid).
  - `tipLength: 0.08`, `tipWidth: 0.015`.
  - `bloomIntensity: 1.4`, `bloomThreshold: 0.1`.
  - `gridOpacity: 0` (the abstract grid is hidden anyway, but this guards the case where the user toggles it).
- Camera: position `[2.6, 1.6, -2.8]`, fov 38, target `(0, 0.4, -0.6)`. The arc bulges toward -Z (per `blender-table-front.mdc`), so the camera sits on -Z and looks back toward +Z to face the curved front.
- No lighting in the scene — there are no meshes to light, just animated `THREE.Line` geometries with bloom.
- GLB scope tightened in `apply_tron_lines.py`: only the desk itself (`Top`, `Skirt`, `Leg_1..4`, `FootBrace`) plus the `TronLine_*` lines. SuitPlatform and SuitDisplays were spatially related but conceptually separate scope — they belong to a later export.

## Outline-mode redesign

The first pass authored 5 hero lines as decoration on top of a visible (dim PBR) table. After feedback the design shifted to:

> All black at the start. The Tron lines trace the table's outline **bottom-up**. By the end the table reads as a complete cyan silhouette — no rendered mesh needed.

13 lines, 4 layers, light overlap between layers so it feels alive instead of strictly sequential. Total animation duration ~7s at `cursorSpeed = 2 m/s`.

| Order | Delay | Layer | Geometry |
|-------|-------|-------|----------|
| 001 | 0.0s  | 1. Floor | Foot brace outer arc (z=0.04, sweeps 0 → π) |
| 002 | 2.0s  | 2. Legs | Leg climb at π/8 (front-right) |
| 003 | 2.1s  | 2. Legs | Leg climb at 3π/8 |
| 004 | 2.2s  | 2. Legs | Leg climb at 5π/8 |
| 005 | 2.3s  | 2. Legs | Leg climb at 7π/8 (front-left) |
| 006 | 2.8s  | 3. Skirt | Skirt outer arc (z=0.91, outer rim) |
| 007 | 3.0s  | 3. Skirt | Skirt inner arc (z=0.91, counter-sweep) |
| 008 | 3.2s  | 3. Skirt | Skirt right chord pin |
| 009 | 3.4s  | 3. Skirt | Skirt left chord pin |
| 010 | 4.0s  | 4. Top  | Top slab outer arc (z=1.05) |
| 011 | 4.2s  | 4. Top  | Top slab inner arc (counter-sweep) |
| 012 | 4.4s  | 4. Top  | Top slab right chord pin |
| 013 | 4.6s  | 4. Top  | Top slab left chord pin |

Visually verified end-to-end via browser MCP:

- At ~t=2.5s: foot brace arc fully drawn, leg climbs spawning.
- At ~t=5.5s: foot brace + legs complete, skirt outline drawing.
- At ~t=18s (settled): full table silhouette traced in cyan on pure black.

Next:

- Optional: split per-line `cursorSpeed` so the floor arc can sweep slowly (drama) and the leg climbs can pop quickly (current uniform speed makes the legs draw in <0.5s — they read as instant flashes rather than climbs).
- Optional: a very faint scaffold of the table edges so the audience subliminally sees "structure waiting to light up" before the first line fires, per `plans/tron-lines-orchestration.md`'s scaffold concept.
- Decide what (if anything) shares the page with the table — the suit platform / display cases are still in `main.blend` and could become their own GLB / mount.

After that:

- Orchestration (`plans/tron-lines-orchestration.md`) lands on top: spawn density curves, twins, hero pacing. These layer onto the `GridPath[]` produced by `tronLinesFromGLB`; the loader and the authored Blender lines stay unchanged.

## Re-running the Blender step

To re-author lines (e.g. add more, tweak placements):

```bash
SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \
  --background blender/main.blend \
  --python blender/table/apply_tron_lines.py
```

The script saves `main.blend` and writes `public/models/table.glb` in one shot. Edit `apply_tron_lines.py`'s `lines = [...]` list to change which polylines are authored. Each entry is `(name, points)` where `name` follows the `TronLine_<order>_<delaySec>` grammar and `points` is a list of `(x, y, z)` in Blender's Z-up world space.

## Open questions for later

- **Twin pairs**: do we author both lanes in Blender (two named lines), or one lane + a `_twin` tag and JS synthesizes the offset? Lean toward the former — authorship is visual, taste is preserved, JS stays dumb.
- **Camera scene**: the current `tron-lines-main.tsx` camera is positioned for the abstract grid (`[42, 30, 46]`). The table scene will likely need its own camera preset.
- **Bloom / color tuning**: the table's dark material will change which `bloomThreshold` reads well. Expect to retune after the first visual pass.
- **Path direction reversal**: if a user accidentally drew a line backwards in Blender, do we ship a JS toggle or ask them to re-author? Probably the latter for now; cheap to flip vertex order in edit mode.
