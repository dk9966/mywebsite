# Procedural PCB Generator

Procedurally generated wireframe PCBs in a Tron-blue aesthetic. Builds a
catalog of ~150 distinct component variations across 8 families, then packs
them onto a board with a grid-based layout algorithm that supports per-family
counts and spatial distribution constraints.

```
pcb_export/
├── README.md                        you are here
├── components/
│   ├── component_builders.py        the 8 families + ~150 builder lambdas
│   └── build_reference_sheet.py     render the full catalog as a GLB grid
├── layout/
│   ├── pcb_layout.py                planner (pure logic, no 3D deps)
│   ├── mesh_builder.py              materializes plan -> trimesh scene
│   └── build_random_pcb.py          main driver — configure & run
├── docs/
│   ├── ALGORITHM.md                 deep-dive on the layout algorithm
│   ├── COMPONENT_CATALOG.md         list of every variation
│   └── EXTENDING.md                 how to add a new family or variation
└── outputs/                         generated GLBs land here
```

## Quick start

```bash
pip install trimesh numpy

# Build the component reference sheet (8x20 grid of all variations)
cd components
python build_reference_sheet.py
# -> outputs/component_reference.glb

# Build a random PCB layout
cd ../layout
python build_random_pcb.py
# -> outputs/random_pcb.glb
```

Open the GLBs in any glTF viewer (Blender, three.js, model-viewer, VSCode glTF
extension).

## What's in here

**Component builders** (`components/component_builders.py`) — a single Python
module that defines 8 families of components, each with 14-20 distinct
procedural variations. Every builder is a function returning a list of
`trimesh.Trimesh` objects. The module also exports a `ROWS` list pairing
each family name with its list of builder lambdas, which the layout planner
samples from.

**Layout planner** (`layout/pcb_layout.py`) — pure logic, no 3D dependencies.
Takes a dict of `FamilySpec` objects (count, footprint, distribution
constraints) and outputs a `LayoutReport` containing exact placements:

```python
families = {
    'qfp':      FamilySpec(count=18, footprint=(2,2), distributed=True,
                            regions=(3, 2)),
    'heatsink': FamilySpec(count=8,  footprint=(2,2), distributed=True,
                            regions=(2, 2)),
    'dip':      FamilySpec(count=25, footprint=(2,1), allow_rotation=True),
    # ...
}
planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
report = planner.plan(families, seed=42, filler_family='smd')
```

**Mesh builder** (`layout/mesh_builder.py`) — the only module that imports
trimesh. Consumes a `LayoutReport`, places each component's mesh at its world
position, optionally extracts wireframe outline edges, and exports a GLB.

**Driver** (`layout/build_random_pcb.py`) — the file you'll mostly edit. Set
counts and parameters at the top, run, get a GLB.

## Visual style notes

The aesthetic is Tron-blue wireframe on a near-black board. Implementation:

- Components have a desaturated industrial palette (steel grays, matte
  metallics, no bright colors) but you barely see this in the final render
  because the wireframe step dominates.
- The wireframe is rendered as cyan-blue **emissive** cylinders. In renderers
  with bloom (Three.js with `UnrealBloomPass`, Blender with bloom enabled),
  these will produce a true neon glow halo. Without bloom they still read as
  clean solid blue outlines.
- Only **outline edges** are drawn, not triangulation edges. See
  `docs/ALGORITHM.md` for the dihedral-angle filtering algorithm.

## Key design choices

**Component builders are stateless lambdas.** Each one returns a fresh list
of `trimesh.Trimesh` objects centered at the world origin. The planner picks
which builder to call for each placement, then the mesh builder translates
the parts to the right grid cell. This keeps the catalog independent of any
layout logic.

**The layout planner has zero 3D dependencies.** It only knows about grid
cells and footprints. This means:

  - You can serialize a layout plan to JSON and render in any engine
    (Three.js, Unity, Houdini, Blender)
  - You can test the planner without ever creating a mesh
  - You can swap the entire mesh library (e.g., move from trimesh to
    pyvista) without touching layout logic

**Family weights are HARD COUNTS, not soft weights.** The previous (bad)
algorithm I tried first used probabilistic sampling — `FamilySpec(count=18,
weight=5)` meant "weight 5 in a probability distribution." That fails because
when a 2×2 chip gets rejected from a tight spot, the sampler picks something
else and the 2×2 quota goes unfilled. The current algorithm places by exact
count, largest-first, so you always get what you asked for if it physically
fits.

**Distribution is enforced via region quotas.** `distributed=True,
regions=(3, 2)` divides the board into 6 sections; each section gets at
least `count // 6` items of that family. This is how QFPs end up visible in
every part of the board instead of clustering in one corner.

## What's NOT in here

- **Circuit trace routing.** I built this earlier and it got abandoned —
  the algorithm I had didn't match the reference aesthetic well enough.
  If you want to revisit it, the right approach is octilinear (45° angles)
  fanouts from pins, not 90° L-bends in channels. See `docs/ALGORITHM.md`
  for notes on what was tried and what didn't work.
- **PBR textures or normal maps.** All materials are simple PBR with base
  color + metallic + roughness + emissive. Good enough for the wireframe
  look but if you want photoreal you'll want to add textures.
- **Animation.** Everything is static geometry.

## See also

- `docs/ALGORITHM.md` — deep dive on the layout algorithm and wireframe
  extraction
- `docs/COMPONENT_CATALOG.md` — complete list of every variation
- `docs/EXTENDING.md` — how to add new component types or families
