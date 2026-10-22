# Rounded roof ends and adjustable light radius

Saved scene: `../platform-controls/cave-platform-sliders.blend`.
Matching snapshot: `rounded-roof-light.blend`.
Checkpoint before this refinement: `before-rounded-roof.blend`.

In **SCENE SLIDERS → Modifiers → Scene Sliders**:

- **Light height above walls (m)**: 0.35–2.10 m. The user's 1.49 m setting is retained.
- **Light radius (m)**: 0.85–2.10 m. The existing 1.46 m radius is retained.

Four roof panels now have circular inner edges that meet the light housing.
Their slopes ease into a horizontal tangent at the rim. Both sliders update
the fixture, its actual area light, curved slab ends, ribs, and nearby cave
overhang. The wall ends remain fixed. All controls use native nodes/drivers.

The sculpted terrain is reduced from **175,365 to 43,302 triangles** (75.3%
fewer). Larger facets replace the dense triangulation, with enough local
vertices retained to keep the curved roof fit accurate. The overhang follows
the roof with a nominal 0.20 m clearance and shallow natural variation.
The source sculpt and its original modifier settings are retained in the file.

`verification.json` records nine height/radius combinations, fixed wall
anchors, circular joins, sampled terrain clearance, closed fixture/roof meshes,
and valid native drivers. `verify_refinement.py` can also run after reopening.
`circular-roof-preview.png` is the rendered close-up.

Rebuild from the checkpoint by running `round_roof.py`, `simplify_terrain.py`,
and `refine_clearance.py`, in that order. These scripts guard against repeats.
