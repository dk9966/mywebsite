# Algorithm notes

This document explains the non-obvious algorithms used in the pipeline,
plus notes on what was tried and abandoned.

## 1. Layout: grid-based bin packing with quotas and regions

### Problem statement

Place N component types on a grid such that:
- Each type gets *exactly* its requested count (or as many as physically fit)
- Some types must be spread across the board (not clustered)
- Some types are larger than others (multi-cell footprints)
- The board has limited cell budget

### Algorithm

```
1. Sort families by priority (default: largest footprint first)
2. For each family in priority order:
     a. If distributed=True:
          - Divide board into (regions[0] x regions[1]) sections
          - Compute per-region quota: count // n_regions + remainder
            distributed randomly to some regions
          - For each region, try to place its quota using only that
            region's cells
          - Second pass: any shortfall from full regions retries the
            entire board
     b. If not distributed:
          - Try to place count items in any random free cell
3. Optionally fill remaining cells with filler_family
```

### Why largest-first matters

A 2×2 QFP can only fit in `(cols-1)*(rows-1)` positions. If the board is
already full of 1×1 SMDs, there's nowhere for it. Placing big things first
while the board is empty guarantees they fit.

### Why region quotas are necessary

Pure random placement clusters big chips by chance. The reference image shows
QFPs distributed across every visible section. By dividing the board into 6
regions (3 wide × 2 tall) and giving each region a quota of 3 QFPs,
clustering is impossible.

This is the same idea as "stratified sampling" in statistics — instead of
drawing N samples from one distribution and hoping for spread, you draw N/k
samples from each of k strata.

### Alternative approaches I tried and rejected

**Probabilistic weights.** Each family has a "weight" in a sampling
distribution; for each cell, sample a family. *This fails because rejection
sampling (the family doesn't fit here, try another) breaks the weights.* Big
chips get systematically under-placed.

**Bin-packing with backtracking.** Like a SAT solver — if a placement leaves
no room for a required QFP, undo and try elsewhere. *This works but is slow
and overkill.* The current largest-first heuristic gets 100% of requested
counts in practice.

## 2. Wireframe extraction by dihedral angle

### Problem statement

Given a trimesh `Trimesh` object, extract only the **outline** edges — the
visible geometric creases like the 12 edges of a cube — not the internal
diagonals that come from triangulation.

### The naive approach fails

`mesh.edges_unique` returns every unique edge in the triangle mesh. For a
rectangular face (= 2 triangles meeting at a diagonal), this includes that
diagonal. For an octagonal prism cap (= 8 triangles fanning from center),
it includes 8 fan-cut lines plus the 8 rim edges. The result looks like a
mess of internal triangulation noise.

### The fix: filter by dihedral angle

`mesh.face_adjacency_angles` returns the angle between the normals of each
pair of adjacent triangles. Two triangles meeting at a diagonal of a flat
rectangular face are **coplanar** — their normals are parallel — so the
angle is near zero. Two triangles meeting at the *edge* of a cube have
normals at 90° to each other.

So: keep edges where `angle > threshold` (default 15°), drop the rest.

```python
def extract_crease_edges(mesh, angle_threshold_deg=15):
    angles = mesh.face_adjacency_angles
    adj_edges = mesh.face_adjacency_edges
    crease_mask = angles > np.radians(angle_threshold_deg)
    return mesh.vertices[adj_edges[crease_mask]]
```

### Verification

For an octagonal prism (`creation.cylinder(sections=8)`):
- Total unique edges: 48 (rim edges + cap fan-cuts + body diagonals)
- After crease filter: **24** (8 top rim + 8 bottom rim + 8 vertical)

This matches the geometric expectation perfectly.

### Boundary edges as a safety net

For open meshes (not closed solids), `face_adjacency` doesn't cover every
edge — some edges belong to only one triangle. We add these "boundary" edges
unconditionally:

```python
boundary_idx = mesh.edges[trimesh.grouping.group_rows(
    np.sort(mesh.edges, axis=1), require_count=1)]
```

This handles any meshes that aren't watertight.

### Dedupe across parts

A component is composed of multiple parts (a QFP = body + 50 pins). Adjacent
parts often share faces (the bottom of the chip body touches the top of the
pin row). After extracting edges from each part and concatenating, we dedupe
by quantizing endpoint coordinates to a small tolerance. This drops the
shared edges so the wireframe doesn't have double-lines.

## 3. Wireframe rendering: emissive tube cylinders

### Why not lines?

GLB doesn't have a portable "glowing line" primitive. The only thing every
viewer renders consistently is **geometry with an emissive material**. So
we render each edge as a thin cylinder.

### Materials

```python
EDGE_MAT = mat(
    [0.35, 0.55, 1.0, 1.0],      # base color: blue-with-tint-of-cyan
    metallic=0.0,
    roughness=0.2,                # shiny so it picks up subtle reflections
    emissive=[0.5, 0.75, 1.0]     # the actual "glow" channel
)
```

The `emissiveFactor` field of glTF PBR is what creates the glow effect. In
renderers without bloom postprocessing it just looks like a solid blue line.
With bloom (Three.js `UnrealBloomPass`, Blender bloom node), it produces a
true neon halo.

### Cheap cylinders

Each edge cylinder uses **3 sections** (triangular prism) instead of the
default 32. Half the polygon count of a 4-section square prism, and visually
identical at typical zoom levels. A typical PCB layout has ~30,000 edges,
so this matters.

## 4. What was tried for circuit traces (and abandoned)

Several routing algorithms were attempted:

### Manhattan A* routing

Pick a pin pair, A* through a coarse occupancy grid avoiding components,
output a 90° bent path. **Result:** random-looking zigzags that didn't match
the parallel-bus aesthetic of a real PCB.

### Channel-track reservation with 90° corners

Identify channels between component rows. Allocate parallel "tracks" within
each channel. Route each trace through the channel graph reserving one
track per channel.

**Result:** long continuous traces with proper parallel bundles, but the
90° L-bends looked mechanical and didn't match the reference's 45° aesthetic.

### Octilinear (45°) routing

Same as above but with 45° mitered corners and pin-fan-out sprays.

**Result:** captured more of the visual gestalt but still didn't quite match
the reference. The reference has true PCB routing with bundled merges and
hierarchical taper that's surprisingly hard to procedurally generate.

### What would actually work

A real PCB autorouter (FreeRouting, etc.) does this for real. The aesthetic
gap between "geometric procedural traces" and "actual PCB autorouted traces"
is real — autorouters use cost-based search with electrical, thermal, and
manufacturability constraints that produce the organic-looking flow.

If you want to revisit this:

1. Use an existing PCB autorouter as a backend (e.g., generate a virtual
   netlist from your placed components, run it through FreeRouting, parse
   the output back into your render pipeline)
2. Or treat traces as an art problem: hand-author a few "templates" of
   trace patterns and procedurally tile them around components

## 5. Performance notes

| Component                              | Cost                |
|----------------------------------------|---------------------|
| Component builders (per call)          | <1ms                |
| Layout planning (200 components)       | <100ms              |
| Wireframe extraction (per component)   | 1-5ms               |
| Edge cylinder concatenation            | dominant cost       |
| GLB export                             | proportional to tri count |

The wireframe scene for a 180-component PCB is ~325k triangles and ~8 MB. If
you need to scale up:

- Drop cylinder sections from 3 to 2 (degenerate quad)
- Skip very short edges (length < threshold)
- Use a line-rendering technique in your engine instead of cylinders (engine-
  specific; not portable through GLB)

## 6. Coordinate conventions

- World units are arbitrary but components are sized in ~1-2 unit range
- Y axis is **up** (board sits at y=0, top of board at y=BOARD_T/2)
- X is right, Z is forward (into screen)
- Grid cells: cell (col=0, row=0) is at world position
  `((-cols/2 + 0.5) * cell, 0, (-rows/2 + 0.5) * cell)`
  (i.e., grid is centered at world origin)
