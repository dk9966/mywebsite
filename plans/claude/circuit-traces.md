# Claude PCB — procedural circuit traces

## What this is

Phase 2 adds **traces only** (no vias, no new components) to `random_pcb.glb`, matching [`plans/chatgpt/circuit-lines-gen-rules.md`](../chatgpt/circuit-lines-gen-rules.md) and the visual target in [`refined lines`](../chatgpt/refined%20lines%20-%20ChatGPT%20Image%20May%2023,%202026,%2009_26_21%20PM.png).

## Blender scene

| Item | Value |
|------|--------|
| Scene | **Claude PCB** |
| Components | `ClaudePCB_Components` ← `plans/claude/files/random_pcb.glb` |
| Traces | `ClaudePCB_Traces` → `claude_trace_all` |
| Saved in | `blender/main.blend` |

## Run (procedural A* router)

```bash
SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \
  --background blender/main.blend \
  --python blender/build_claude_circuit_traces.py
```

Standalone SVG/JSON export (no Blender):

```bash
python3 plans/claude/files/pcb_export/trace/build_traces.py
```

Writes `plans/claude/outputs/random_pcb_traces.svg` and `.json`.

## Architecture

| Module | Role |
|--------|------|
| `plans/claude/files/pcb_export/trace/models.py` | `PlacedComponent`, `Pin`, `TracePath`, clearances/widths |
| `trace/scene.py` | Layout report → world XZ footprints + keepouts |
| `trace/pins.py` | QFP / SOIC / SMD / block pin + fanout stubs |
| `trace/planner_grid.py` | 5× subcells per planner cell; gutters stay routable |
| `trace/grid.py` | 8-connected occupancy + edge reservation |
| `trace/router.py` | A* (turn penalty, parallel bonus), buses, pairing, salvage |
| `trace/export.py` | Editable SVG + JSON polylines |
| `blender/circuit_trace_router.py` | Blender adapter → `TraceSegment` meshes |

## Algorithm — circuit-board-painter port

Based on [ArtBIT/circuitboard-painter](https://github.com/ArtBIT/circuitboard-painter). One pass, no A*:

1. **Grid** — planner-aligned `subdiv` (default 14) subcells per planner cell. Each placement's inner core is blocked; a per-family `gutter` (IC 4 cells, SMD 2 cells) leaves a routable border around every component so wires can pass without touching the mesh.
2. **Pin seeds** — every QFP / SOIC / SMD / block pin produces a `PinSeed` (anchor cell + outward 8-direction). Anchor cells fall on the placement's free border.
3. **Wire growth** — each seed grows up to `wire_length` cells. At every step the next cell is chosen from `{forward, +45°, -45°}` with probability `r ** straightness`; high straightness ⇒ long straight runs with the occasional 45° kink. Anti-crossover check on diagonals so two diagonal wires can't share an X.
4. **Gap fill** — after pin seeds, every still-free cell in the grid is shuffled into a pool; each one tries to start a new wire. Pool keeps shrinking as wires claim cells until every gap is filled.
5. **Cut-off** — wires shorter than `cut_off_cells` are dropped.
6. **Tiering** — world-length sorts each wire into backbone (`0.035`), medium (`0.022`), thin (`0.012`).
7. **Style** — emissive cyan `ClaudePCB_TraceEmissive`, uniform opacity, no vias, no curves.

## Tuning knobs (`route_layout` kwargs)

| Param | Default | Effect |
|-------|---------|--------|
| `subdiv` | 14 | Subcells per planner cell — higher = finer pitch |
| `gutter_ic` / `gutter_smd` | 4 / 2 | Cells of clearance between mesh and wires |
| `wire_length` | 260 | Max cells per wire — higher = longer runs |
| `straightness` | 14.0 | `r ** straightness` bias toward forward |
| `cut_off_cells` | 1 | Drop wires with fewer cells than this |

## Modules

| File | Role |
|------|------|
| `trace/painter.py` | Wire-growth algorithm (ArtBIT port) |
| `trace/planner_grid.py` | Subdivided grid with per-family gutters |
| `trace/pins.py` | Pin anchors for every component family |
| `trace/router.py` | Glue: seeds → painter → `RouteReport` polylines |
| `trace/path_style.py` | Collinear merge + micro-jog cleanup |
| `trace/export.py` | SVG + JSON |

## Phase status

| Step | Status |
|------|--------|
| Import `random_pcb.glb` | Done |
| Painter trace layer | Done — 5k+ wires, 45° turns, gap-filled |
| SVG / JSON export | Done |
| Blender verify + renders | `blender/build_claude_circuit_traces.py` |
| Image-derived overlay (optional) | `blender/build_traces_from_image.py` |
