# Scene assembly

Places the `meshes/` kit into the hub-and-spokes world from
`ideation/overall.png`.

```
python assemble.py       # layout.json -> instances.json
python render_world.py   # instances.json -> world_preview.png
```

## What this is (and isn't)

`instances.json` is an **instance list**: which model, at which transform.
Nothing is merged into a combined GLB. Each model file is loaded once and drawn
many times — for this scene that is 214 instances from **5 files**. Baking the
same world into a single GLB would store every copy again: ~27.7 MB versus
~3.9 MB.

That also means editing a mesh updates every instance of it. Rebuild
`island_pillar_huge.glb`, re-run nothing, refresh — the central pillar changes.
Only the *layout* needs `assemble.py` re-run.

`instances.json` is the file the three.js side should read.

## Layout

Island positions come from `secret-base/components/scene/layout.ts`, which
already encodes the concept art's topology, scaled by two factors:

- **0.44** — the old layout's radii were deck radii of the rough-draft islands
  (2.6–5.5). Our pillar top platforms are smaller, so the spacing was scaled to
  match. Each island's radius now lands within a few percent of the top platform
  of the variant assigned to it.
- **2.5 (`pillar_scale`)** — the bridge kit is authored at a fixed size (4x2
  deck, 0.48 railings) and the pillars came out too small against it: a 2-wide
  bridge landing on a 1.93-wide platform. Scaling the pillars fixes the
  relationship. It is a *uniform* scale, so unlike the width/height stretch in
  the pillar generator it does not disturb the edge lines.
- **1.58 (`spacing_scale`)** — solved, not chosen. Every bridged pair must have
  5 units of clear air between plinths; the tightest pair (experiences→contact)
  had 0.48 and set the factor. Re-run the solve if you move islands.

Pillar assignment is by island size: `projects` is the central island so it gets
`huge`; `contact` and `garage` get `small`; the rest `large`.

## Bridges

Spans are computed rim to rim at deck height, so they always land on the
platform edge rather than at the island centre. Two details that are easy to get
wrong:

- The bridge is **repeated, not stretched**. Plank spacing stays constant
  whatever the gap; only the module length is nudged to divide the span evenly.
  Stretching one module over a 20-unit gap gives visibly smeared planks.
- `bridge.glb` spans y 0..0.3, so its walking surface is 0.3 **above** its
  origin. Placing the origin at deck height leaves the bridge floating by that
  much — `bridge_drop()` subtracts it.

Railings are laid as 1-unit modules down both edges, inset 0.9 from the
centreline, with `Rail_End` capping each run and `Rail_Lamp` every 4th module.

## Files

| file | role |
| --- | --- |
| `layout.json` | islands, which pillar each uses, which pairs are bridged |
| `assemble.py` | layout -> instance list; computes bridge and railing transforms |
| `instances.json` | generated; the thing to load from three.js |
| `render_world.py` | draws the instance list with the software rasteriser |
| `world_preview.png` | generated preview |

## Note on the preview renderer

`render_world.py` loads each model once and re-uses it across instances, and
applies the inverse transpose to normals when an instance is scaled. That is the
same thing three.js does with a shared geometry and per-instance matrices, so
the preview is a fair check of the layout rather than a separate pipeline.
