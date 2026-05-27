# Circuit Layout (ChatGPT reference)

Phase 1 builds full-density **components only** (no traces, no vias) in Blender scene **`Circuit Layout`**, matching:

- Reference: [`plans/chatgpt/no circuit no vias ChatGPT Image May 22, 2026, 10_12_57 AM.png`](chatgpt/no%20circuit%20no%20vias%20ChatGPT%20Image%20May%2022,%202026,%2010_12_57%20AM.png)
- Traces/vias (phase 2): [`plans/chatgpt/ChatGPT Image May 21 2026 Circuit Style Top View.png`](chatgpt/ChatGPT%20Image%20May%2021%202026%20Circuit%20Style%20Top%20View.png)

## Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| 1 — Component library + assembly | **Done** | `blender/build_circuit_layout.py`, Tripo-referenced (~57 placed, uniform scale) |
| 2 — Traces | **In progress (Claude PCB)** | See [`plans/claude/circuit-traces.md`](claude/circuit-traces.md) — octilinear router on `random_pcb.glb` |
| 3 — Vias | Pending | Hex/cylinder pads at trace nodes |
| 4 — Materials | Pending | Dark body + emissive cyan wireframe / bloom |

## Run

```bash
SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \
  --background blender/main.blend \
  --python blender/build_circuit_layout.py
```

Output:

- Scene: **Circuit Layout**
- Collections: `CircuitLayout` (board + assembly), `CircuitLayout_Parts` (33-variant library grid off-board)
- Renders (re-run script to refresh):
  - `circuit-layout-top.png` — ortho
  - `circuit-layout-ref.png` — primary reference angle (~52°)
  - `circuit-layout-ref-low.png`, `circuit-layout-ref-high.png`
  - `circuit-layout-from-left.png`, `from-right.png`, `from-front.png`
  - `circuit-layout-{nw,ne,sw,se}.png` — quadrant zooms
  - No `cl_asm_fill_*` objects (tiny greedy fillers removed)

## Zone map (board 520×380 mm, centered at origin)

```
        +Y (north)
          |
    NW    |    N     |    NE
  heatsink|  IC row  | connectors
          |          |
  --------+----------+--------  +X (east)
          |          |
    W     |    C     |    E
   caps   |  dense   |  BGA/IC
          |          |
    SW    |    SE    |
   oct    |  slots   |
          |
        -Y (south)
```

| Zone | Role | Example parts |
|------|------|----------------|
| NW | Hero heatsink + QFP cluster | `hsink/fins14`, `ic_sq/lqfp64_w` |
| N | North IC spine + socket | `socket/die`, `ic_sq/wide` |
| NE | Edge connectors | `conn_slot/wide`, `pcie`, `usb` |
| W | Cap clusters + DIP | `cap_cyl/2x2`, `dip/24` |
| C | Central mix + fin sink | `hsink/fins10`, QFP/SOIC grid |
| E | East BGAs + stepped sink | `bga/20`, `hsink/stepped` |
| SW | Octagon + cap row | `oct/medium`, `cap_cyl/row4` |
| SE | Bottom slots + tall caps | `conn_slot/slot3`, `cap_cyl/tall` |

SMD gaps are filled procedurally (capped at 42) in small rectangles inside **C**, **N**, **W**, **E**, **NW**, **SE**.

## Files

| File | Purpose |
|------|---------|
| [`blender/pcb_bmesh_lib.py`](../blender/pcb_bmesh_lib.py) | Shared box/leg/prism helpers |
| [`blender/build_circuit_layout.py`](../blender/build_circuit_layout.py) | Builders, `PARTS`, `PLACEMENTS`, assembly |

## Tripo reference alignment (May 22)

Circuit Layout placement is driven by **Tripo Layout** (`TripoLayout` collection in `main.blend`):

- Island centers and footprints sampled from `read_tripo_slots()` in `build_circuit_layout.py`
- `MESH_VISUAL_SCALE` normalizes library mesh size (max/median footprint ≈ 2.2×, Tripo ≈ 3.4×)
- Placement aisles use Tripo bbox half-extents + `GAP_MM=0.10`
- Zone landmarks: NW `hsink/fins14`, N `socket/die`, SW `oct/medium`, NE `conn_slot/wide`

Re-import Tripo GLB if the reference scene is empty::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/import_tripo_layout.py

## Verification (phase 1)

After run, expect console similar to:

```
[circuit_layout] tripo_slots=63
[circuit_layout] library=33 assembled=57 skipped=... overlaps=0
[circuit_layout] hero NW_heatsink: OK
...
```

- Object count in `CircuitLayout`: **58** (57 components + `cl_board`)
- Bbox roughly `x=-145..145`, `y=-110..110` (290×220 mm board, compressed coords)
- No overlap pairs reported (`overlaps=0`)
- Heroes present: NW `cl_hsink_fins14`, N `cl_socket_die`, SW `cl_oct_medium`, NE `cl_conn_wide` (+ NW `cl_conn_slot_slot3` via override when open)

## Phase 2 notes

- Trace width 0.15–0.35 mm, `z=0.05`, 90° paths only
- Keep aisles between existing `PLACEMENTS` footprints (use same AABB helper)
- Vias: short hex prisms on trace endpoints and under large ICs
