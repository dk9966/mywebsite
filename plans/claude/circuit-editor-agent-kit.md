# Circuit editor agent kit

Everything an agent (e.g. Fable 5) needs to draw circuit lines and place components
in the Tron circuits editor by editing JSON directly — no clicking the UI.

## The idea in one paragraph

The editor's whole board is described by one JSON file: traces (metal lines) live
under `topology`, and components (chips, caps, heatsinks) live under `meshEdits`.
The rest (`circuits-traced.json` + a GLB) is the fixed baseline the file layers on
top of. To change the board you edit that JSON, then load it in the editor. The
hard part for an agent is *spatial awareness* — knowing where things are and how
they relate — so we generate a read-only `board-spatial.json` that lays out every
component box, every trace segment, where lines meet, and which gaps are open.

## Step 1 — generate the spatial map

```bash
pnpm run export-board-spatial                 # from committed circuits-tuning.json
pnpm run export-board-spatial -- --version 2  # from src/data/circuit-versions/2.json
```

Writes `src/data/board-spatial.json`. This is **read-only** — it never changes the
editor or the tuning file. Regenerate it after edits to see the new state.

### What's in it

| Section | Meaning |
|---------|---------|
| `board` | XZ bounds + `traceY` + axis legend (+X east, +Z south, Y up) |
| `components[]` | Each part: `id`, `kind`, `bbox`, `center`, `size`, `edges{north,south,east,west}` |
| `traces[]` | Each line segment: `id`, `chain`, `start`, `end`, `angleDeg`, `length` |
| `junctions[]` | Points where 2+ segments share a vertex (continuity) |
| `attachments[]` | Trace endpoints landing on a component edge (which comp, which side) |
| `corridors[]` | Open channels between two components: `gap`, `center`, `span`, `axis` |
| `anomalies[]` | Components with out-of-range coords (corrupt data to ignore/fix) |

## Step 2 — coordinate cheat sheet

- Board plane is **XZ** (horizontal). **Y is height** and stays flat.
- Trace height `Y ≈ 0.003` (use `board.traceY` from the manifest).
- `+X` = east/right, `+Z` = south/down in the editor's top view.
- A segment is `{ start: [x, y, z], end: [x, y, z] }`.
- Component ids: `comp-N` (baseline) and `mesh-user-N` (added in editor).
- Trace ids: `trace-N-seg-M` (baseline) and `user-N` (hand-drawn).

## Step 3 — the two data buckets to edit

Both live in the tuning JSON (`circuits-tuning.json` or a version file).

### Mesh variant catalog (palette labels → ids)

The 3D editor palette ("QFP 3", "SOIC 5", …) maps to stable variant ids in
`qfp-variants.glb`. An agent should **not** guess ids from the build script.

```bash
pnpm run export-mesh-variant-catalog   # writes src/data/mesh-variant-catalog.json
```

Read `src/data/mesh-variant-catalog.json`:

| Field | Meaning |
|-------|---------|
| `lookup` | `"QFP 3"` → `"q3-plain-prism"` (also maps ids to themselves) |
| `variants[]` | Full list: `id`, `label`, `kind`, `placeSize`, `natural` |
| `defaultMeshSize` | Fallback footprint per kind when no variant is set |
| `meshEditsExample` | Copy-paste shape for a new `meshEdits.added` entry |

**Quick insert (preferred for agents):**

```bash
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --version 2
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --dry-run
```

This resolves the label, picks the next `mesh-user-N` id, appends to
`meshEdits.added`, and warns on bbox overlap with existing added meshes.

**Manual insert:** use `lookup` + `placeSize` to build the entry below.

### Traces → `topology`

```jsonc
"topology": {
  "geometry": {                 // authoritative positions; wins over `added`
    "user-40": { "start": [-10, 0.003, 5], "end": [-5, 0.003, 5] }
  },
  "added": [                    // new lines must ALSO be listed here
    { "id": "user-40", "start": [-10, 0.003, 5], "end": [-5, 0.003, 5] }
  ],
  "deleted": ["trace-7-seg-0"]  // hide a baseline segment
}
```

Rules for a new line:
1. Pick a fresh `user-N` id (higher than any existing `user-*`).
2. Add the same geometry to **both** `geometry` and `added`.
3. Keep it **straight** (2 points), **flat** (same Y on both ends = `traceY`),
   and on the **45° grid** (angle 0/45/90/135). Chain multiple segments at
   junctions instead of bending one line.
4. To connect to a component, land the endpoint on a `bbox` edge (use the
   `edges` values from the manifest). Endpoints within 0.35 world units snap on.

### Components → `meshEdits`

```jsonc
"meshEdits": {
  "geometry": {                 // resize/move an existing mesh by id
    "comp-0": { "minX": -0.03, "maxX": 2.9, "minZ": 7.57, "maxZ": 10.29 }
  },
  "added": [                    // place a new component
    { "id": "mesh-user-40", "kind": "qfp",
      "minX": 20, "maxX": 23.5, "minZ": 2, "maxZ": 5.5,
      "variant": "q6-connected-ring" }
  ],
  "deleted": ["comp-3"]         // remove a baseline component
}
```

- `kind` is one of: `qfp, soic, capacitor, heatsink, drum, header, connector,
  smd, pad, via, cpu, io, dimm, pcie, vrm`.
- A box is just `minX/maxX/minZ/maxZ`; center and size are derived.
- New ids use `mesh-user-N`; never reuse a `deleted` id.
- `variant` is optional but **required for real 3D outlines** from the palette.
  Resolve labels via `mesh-variant-catalog.json` (`"QFP 3"` → `q3-plain-prism`).
  Omit `variant` for a plain labeled box (2D editor style).

## Step 4 — routing intent

Follow `plans/chatgpt/circuit-lines-gen-rules.md`:
- Route through the open `corridors`, never over component bboxes.
- Mostly 45° runs; no crossings; no curves; no vias.
- Denser near large ICs, lighter in open areas; backbone/medium/thin hierarchy.
- Traces meet component edges, they don't float nearby.

## Step 5 — validate

```bash
pnpm run check-circuit-line-geometry
```

Confirms every editable line is flat, straight, and on the 45° grid. Fix anything
it flags, then regenerate the spatial map and (optionally) reload the version in
the editor to see the result.

## Suggested workflow for a version

1. In the editor (dev server on `5174`), create/select version `2`.
2. `pnpm run export-board-spatial -- --version 2`
3. Read `board-spatial.json` for open corridors; pick a placement center.
4. Insert a mesh: `pnpm run insert-circuit-mesh -- --variant "QFP 3" --at cx,cz --version 2`
   (or edit `meshEdits` manually using `mesh-variant-catalog.json`).
5. `pnpm run export-board-spatial -- --version 2` to refresh the spatial map.
6. `pnpm run check-circuit-line-geometry` if you also edited traces.
7. Reload version `2` in the editor to view; iterate.

## Files

| File | Role |
|------|------|
| `scripts/export-board-spatial.ts` | Generates the read-only spatial map |
| `src/data/board-spatial.json` | The generated map (regenerate after edits) |
| `scripts/export-mesh-variant-catalog.ts` | Generates palette label → id manifest |
| `src/data/mesh-variant-catalog.json` | Variant lookup for agents (`QFP 3` → `q3-plain-prism`) |
| `scripts/insert-circuit-mesh.ts` | CLI to append a palette mesh to meshEdits |
| `src/data/circuits-tuning.json` | Committed board (traces + components) |
| `src/data/circuit-versions/*.json` | Named snapshots to edit safely |
| `scripts/check-circuit-line-geometry.ts` | Geometry validator |
| `plans/chatgpt/circuit-lines-gen-rules.md` | Routing/style rules |
