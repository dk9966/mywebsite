# Coarse rock around the upper gallery and lower workshop

Saved in `../platform-controls/cave-platform-sliders.blend` and copied to
`snug-low-poly-platform-surrounds.blend`. `before-terrain-cull.blend` preserves
the live scene before this work, including unsaved edits.

The dense local patch drops from **48,884 to 912 triangles (98.1% fewer)**.
The complete terrain evaluates to **30,346 triangles**, down from 82,334.
Typical edges in the edited patch are 0.72 m. The original sculpt, nine shape
keys, and procedural slate material remain available. Visible stone detail
comes from the existing material instead of extra tessellation.

Concealed rock fits close to the backs of the wall panels and the deck
undersides. A hidden Geometry Nodes target follows the native architecture;
it does not render. The snug region retains a tiny amount of depth variation
to prevent coincident, collapsed faces. Sampled backing vertices have a median
gap of 16 mm and a 95th-percentile gap of 45 mm. The coarse continuous backing
prevents holes when the controls move.

The remaining dense band around the lower roof receives its own local
reduction. A native clearance field keeps those broad triangles above the
adjustable circular light without adding geometry. Both viewport and render
use the same modifier stack.

`verification.json` records one connected component, no loose edges,
nonmanifold junctions, or degenerate faces, and 14,665 outside vertices retained
exactly. Four light height/radius settings pass walking-area and light
clearance checks; the original 0.81 m height and 0.93 m radius are restored.
Walking-area checks account for the sloped opaque wall panels and channel ribs
in front of the snug backing. The reported source-to-result distance includes
the requested inward movement of previously separated hidden rock.

This work writes only to the terrain and its new hidden fitting helper.
`Middle back | upper octagon` changed independently during the live session;
its current state is retained in the saved scene.

The stage scripts are `simplify.py`, `snug.py`, `reduce_dense_strip.py`, and
`finish_clearance.py`; they retain the source mesh and use reversible native
modifiers. `verify.py` checks the final scene, and `capture.py` produces the
wireframe and material previews without changing the scene camera.
