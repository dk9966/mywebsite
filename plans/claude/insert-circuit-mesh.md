# Insert a palette mesh (agent guide)

Use this when the task is only **place a component from the editor mesh column**
(e.g. **QFP 3**) onto the board. Do not click the UI — edit JSON or run the insert
script.

For routing traces, moving parts, or full board editing, see
`plans/claude/circuit-editor-agent-kit.md`.

---

## What you are doing

The 3D editor mesh column shows labels like **QFP 3**. That label maps to a
variant id (`q3-plain-prism`) and a footprint size. You append one object to
`meshEdits.added` in the tuning JSON. The editor loads that file and draws the
real 3D outline.

You need two inputs:

1. **Which mesh** — palette label (`"QFP 3"`) or variant id (`q3-plain-prism`)
2. **Where** — center point `(cx, cz)` on the board plane (XZ)

---

## Files to read

| File | Why |
|------|-----|
| `src/data/mesh-variant-catalog.json` | Label → id lookup, footprint sizes |
| `src/data/board-spatial.json` | Where existing parts are, open corridors |
| `src/data/circuits-tuning.json` | Main board (or use a version file below) |
| `src/data/circuit-versions/N.json` | Named snapshot if editing version `N` |

Regenerate spatial map before picking a spot:

```bash
pnpm run export-board-spatial                 # main board
pnpm run export-board-spatial -- --version 2  # version 2
```

In `board-spatial.json`, use **`corridors[]`** to find open gaps. Each corridor has
a **`center: { x, z }`** — that is a good `--at` value. Avoid overlapping
`components[].bbox`.

---

## Method A — insert script (preferred)

Run this. It resolves the label, assigns the next `mesh-user-N` id, and appends
to `meshEdits.added`.

```bash
# Preview first (no file write)
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --dry-run

# Write to main board
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6

# Write to a version snapshot
pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --version 2
```

Replace `"QFP 3"` with any palette label or variant id from the catalog.
Replace `12,6` with your chosen center from `board-spatial.json`.

If the script prints an **overlap warning**, pick a different `--at` from a
corridor center and run again.

Then refresh the spatial map:

```bash
pnpm run export-board-spatial -- --version 2   # omit --version for main board
```

Reload the board in the editor at `http://localhost:5174/` (select the same
version if you edited one).

---

## Method B — edit JSON by hand

Use this only if you cannot run the script.

### 1. Resolve the label

Open `src/data/mesh-variant-catalog.json`:

```json
"lookup": {
  "QFP 3": "q3-plain-prism"
}
```

For **QFP 3** you get:

- `variant`: `"q3-plain-prism"`
- `kind`: `"qfp"`
- `placeSize`: `{ "w": 3.5, "h": 3.5 }`

Do **not** invent variant ids. Always use `lookup` or `variants[]`.

### 2. Compute the bounding box

Given center `(cx, cz)` and `placeSize` `{ w, h }`:

```
minX = cx - w/2
maxX = cx + w/2
minZ = cz - h/2
maxZ = cz + h/2
```

Example: center `(12, 6)`, footprint 3.5×3.5 →
`minX=10.25, maxX=13.75, minZ=4.25, maxZ=7.75`.

### 3. Pick a new id

Scan `meshEdits.added` and `meshEdits.deleted` in the target tuning file. Use the
next unused `mesh-user-N` (e.g. if highest is `mesh-user-34`, use `mesh-user-35`).

**Never reuse an id listed in `deleted`.**

### 4. Append to `meshEdits.added`

In `src/data/circuits-tuning.json` or `src/data/circuit-versions/N.json`:

```json
{
  "id": "mesh-user-35",
  "kind": "qfp",
  "minX": 10.25,
  "maxX": 13.75,
  "minZ": 4.25,
  "maxZ": 7.75,
  "variant": "q3-plain-prism"
}
```

Required fields for a palette mesh:

| Field | Value |
|-------|-------|
| `id` | New `mesh-user-N` |
| `kind` | From catalog (`qfp`, `soic`, `cpu`, …) |
| `minX`, `maxX`, `minZ`, `maxZ` | Footprint on the XZ plane |
| `variant` | Catalog id — **required** for the real 3D outline |

You do **not** need to duplicate this into `meshEdits.geometry`. Only append to
`added`.

---

## Checklist

- [ ] Read `mesh-variant-catalog.json` — label resolves (e.g. `"QFP 3"` → `q3-plain-prism`)
- [ ] Read `board-spatial.json` — placement does not overlap existing bboxes
- [ ] Insert via script **or** append one entry to `meshEdits.added`
- [ ] Run `export-board-spatial` to confirm the new component appears
- [ ] Reload the editor to view

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using `"QFP 3"` as the `variant` value | Use `q3-plain-prism` from `lookup` |
| Guessing variant ids from Python build scripts | Use `mesh-variant-catalog.json` only |
| Reusing a `mesh-user-N` from `deleted` | Pick a higher unused number |
| Editing `circuits-tuning.json` while viewing version `2` | Edit `circuit-versions/2.json` instead |
| Omitting `variant` | Mesh shows as a plain box, not the palette outline |

---

## Example: full agent run for QFP 3 on version 2

```bash
pnpm run export-board-spatial -- --version 2
# Read src/data/board-spatial.json → corridors[0].center → e.g. x=12, z=6

pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --version 2

pnpm run export-board-spatial -- --version 2
# Confirm new entry in components[] with variant q3-plain-prism
```

Done. The mesh is in the scene when version `2` is loaded in the editor.

---

## Reference

| Command | Purpose |
|---------|---------|
| `pnpm run export-board-spatial` | Spatial map for placement |
| `pnpm run insert-circuit-mesh` | Append mesh to tuning JSON |
| `pnpm run export-mesh-variant-catalog` | Regenerate catalog after GLB changes |

| Path | Purpose |
|------|---------|
| `scripts/insert-circuit-mesh.ts` | Insert script source |
| `src/lib/meshVariantManifest.ts` | Label resolution helpers |
| `public/models/qfp-variants.glb` | 3D outline geometry (referenced by `variant`) |
