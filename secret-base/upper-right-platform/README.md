# Upper-right square platform

Saved in `../platform-controls/cave-platform-sliders.blend`.
`upper-right-platform-finished.blend` is a matching edit snapshot.
`before-upper-right-platform.blend` preserves the scene before this work.

The former regular octagon is now a 6.125 m square with four short 0.30 m
corner bevels. Its principal edges follow the lower platform exactly; both
floor planes are horizontal. The original slab is retained in the hidden
`Archive | upper right octagon` collection.

The floor has satin blue-gray steel panels, a subtly darker square service
zone, muted brass registration lines, two drainage strips, a machined rim,
cool white fascia diffusers, and slender steel guardrails matching the scene.

The existing continuous wall forms a locally tapered rock shoulder beneath
the deck and a square recess above. `Upper-right | fitted shoulder and square
recess` is an additive shape key; earlier sculpt keys are retained. The
original terrain mesh is retained through the object's `before_upper_right_mesh`
property. The upper bearing region is excluded from the separate lower
workshop roof-height mask so that the lower light control cannot pull it away
from the platform.

`verification.json` records 625 bearing samples, all within 13 mm of the slab
underside; no obstructions in 1.5 m above the sampled walking area; exact edge
alignment; and one connected terrain component with no loose edges or
nonmanifold junctions. Three existing zero-area evaluated faces are outside
this edit's upper support region. Other left-side work was being edited
concurrently; the recorded unrelated-object differences are retained.

`upper-right-detail.png` uses the unchanged scene camera and lighting.
`after.png` is an intermediate inspection render with temporary fill lights
and a local terrain cutaway, not a saved scene configuration.

Construction scripts are embedded in the Blender file. For a fresh rebuild,
run `build_platform.py`, then `finish_platform.py`, then `verify_platform.py`
against the pre-edit scene. `refine_terrain.py` is the terrain-only iteration
script. Temporary inspection settings do not alter the live camera or lights.
