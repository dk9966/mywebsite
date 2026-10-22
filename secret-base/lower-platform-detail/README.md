# Lower workshop architecture

The current Blender file is `../platform-controls/cave-platform-sliders.blend`.
`detailed-workshop.blend` is a separate copy; `before-detail.blend` preserves the
complete live session before this pass, including unsaved user changes.

Reference: `../../images/batcave-railings-no-car-v2.png`, already assigned to the
main camera. The reference overlay is hidden so the actual model is visible.

This pass adds four oblique wall bays, clipped jambs, a continuous stepped roof
and projecting light hood, architectural strip lights, a circular floor service
pad, welded perimeter rails, a mitered bridge with underside trusses, and cliff
anchored V supports. It retains the user's aligned front platform corners and
floor height. The connected cave mesh is locally fitted around the new room.
Furniture is intentionally absent. Existing central and other platform geometry
and the user's camera are preserved. New bridge and rail geometry follows the
existing middle width and railing height controls through native Geometry Nodes.

The previous loose slab and bridge are retained in a disabled archive collection.

To reproduce, open `before-detail.blend` and execute these scripts in order:

1. `build_detail.py`
2. `refine_terrain.py`
3. `finish_detail.py`
4. `connect_controls.py`

`verify_detail.py` independently opens the before and after files and checks
unaffected geometry, cave connectivity, floor clearance, the railing entrance,
the landing elevation and native drivers. `render_detail.py` renders the close-up
from the unchanged main camera.
