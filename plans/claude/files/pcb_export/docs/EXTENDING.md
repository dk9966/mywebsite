# Extending the catalog

## Adding a new variation to an existing family

1. Open `components/component_builders.py`.
2. Write a function `make_my_thing(...)` that returns a list of
   `trimesh.Trimesh` objects, positioned with their AABB centered at the
   world origin, sitting on the board (bottom at `y=0`, board top at
   `y=BOARD_T/2`).
3. Find the `ROWS` definition at the bottom of the file (look for the
   `("QFP / chip ICs", [...])` style entries).
4. Add `lambda: make_my_thing(...)` to the appropriate row's list.

Example: adding a new QFP variant.

```python
def make_qfp_with_my_marking(w, d, h=0.34, pins_per_side=12):
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side,
                     top_marking='square')
    # add a custom detail on top
    extra = creation.box(extents=[w*0.3, 0.02, d*0.1])
    _vis(extra, LABEL_MAT)
    extra.apply_translation([0, h + BOARD_T/2 + 0.012, d*0.25])
    parts.append(extra)
    return parts

# Then in ROWS:
ROWS = [
    ("QFP / chip ICs", [
        # ... existing lambdas ...
        lambda: make_qfp_with_my_marking(2.0, 2.0, h=0.34, pins_per_side=13),
    ]),
    # ...
]
```

Run `build_reference_sheet.py` to see your new variation in the catalog
sheet. It should appear at the rightmost column of the QFP row.

## Adding a brand new family

1. Add a new entry to `ROWS`:
   ```python
   ROWS = [
       # ... existing ...
       ("Crystal oscillators", [
           lambda: make_xtal_can(0.8, 0.4, 0.3),
           lambda: make_xtal_can(0.9, 0.5, 0.35, with_label=True),
           # at least 6-10 builders to fill the reference sheet column
       ]),
   ]
   ```
2. In `mesh_builder.py`, add to `FAMILY_BUILDERS`:
   ```python
   FAMILY_BUILDERS = {
       # ... existing ...
       'xtal':  dict(ROWS)['Crystal oscillators'],
   }
   ```
3. In your driver (`build_random_pcb.py`), add a `FamilySpec`:
   ```python
   FAMILIES = {
       # ...
       'xtal': FamilySpec(count=6, footprint=(1, 1)),
   }
   ```

## Pin extraction (for future trace routing)

If you build a new component and want it to be compatible with a future
trace router, follow this convention:

- The component has ONE main "body" part (the largest part by volume).
- Pin parts are small, positioned with their centroids *outside* the body's
  XZ bbox.

This way, the pin-finder algorithm (in `trace_router_v2/v3` if you bring
that back) can identify pins by:

```python
body_idx = argmax([part.volume for part in parts])
for i, p in enumerate(parts):
    if i == body_idx: continue
    centroid_xz = p.centroid[[0, 2]]
    if centroid_xz outside body's xz bbox:
        # this is a pin
        ...
```

So as long as you build the body as a single trimesh and the pins as
separate small parts protruding outside the body's footprint, pin
discovery will work.

## Material conventions

Use the materials defined at the top of `component_builders.py`. They're
deliberately desaturated and metallic:

| Material         | Use case                          |
|------------------|-----------------------------------|
| `CHIP_MAT`       | dark chip bodies (default)        |
| `CHIP_LIGHT_MAT` | slightly lighter chip bodies      |
| `CERAMIC_MAT`    | tan ceramic packages              |
| `PIN_MAT`        | silver-tone metal pins            |
| `PIN_GOLD_MAT`   | gold-tone metal pins (premium)    |
| `CAP_MAT`        | dark capacitor sleeves            |
| `HEATSINK_MAT`   | brushed aluminum heatsinks        |
| `HEATSINK_DARK`  | dark anodized heatsinks           |
| `SCREW_MAT`      | screw heads, small metal bits     |
| `LABEL_MAT`      | label markings, stripes           |
| `SHIELD_MAT`     | shielded cans, port shells        |
| `PLASTIC_WHITE`  | white plastic (JST etc.)          |
| `PLASTIC_BLUE`   | blue plastic                      |
| `PLASTIC_GREEN`  | green plastic (terminal blocks)   |

Don't add bright-saturated colors — the whole aesthetic is industrial gray.
Color comes from the wireframe emissive edges, not from the underlying mesh.

## Performance tips when adding parts

- Prefer `creation.box`, `creation.cylinder` with low `sections` (8-12).
  Anything more is overkill at typical zoom levels.
- Avoid `creation.icosphere(subdivisions>2)` — explodes triangle count.
- A complex variant of ~30 parts is fine; ~100 parts will make the
  reference sheet GLB > 10 MB.

## Testing your changes

```bash
cd components
python build_reference_sheet.py
# Open the GLB and visually check your new variation
```

Or render just one component to a quick test GLB:

```python
import trimesh
from component_builders import make_my_thing
parts = make_my_thing(...)
trimesh.Scene(parts).export('/tmp/test.glb')
```
