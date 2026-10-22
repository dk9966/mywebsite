# Octagon wall alignment

The active session is `../platform-controls/cave-platform-sliders.blend`.
The verified changes are saved in `aligned-walls.blend`; `aligned-walls.png` is
the rendered check. Overwriting the shared active file was blocked by automatic
approval review because the change includes the local rock recess. The active
session still contains the edits, but the separate checkpoint is the saved result.

Collection `162 | Octagon aligned workshop walls` contains two equal, coplanar
rear bays and one 45-degree corner bay. Their bases are taken directly from the
current symmetric octagon. All uprights are vertical; panel grids, roof edges,
and light bars follow the same wall planes. The earlier camera-fitted walls
remain hidden in collection 160. Its overhead hood and broad lights are retained.

The existing connected cave surface is locally recessed to expose the corrected
architecture. Earlier terrain meshes are retained as Blender datablocks. The
floor, concentric rings, bridge, and rails were preserved for their concurrent
editing tasks. `before-wall-alignment.blend` captures the earlier session; do not
reload it over later floor or bridge work.

The scripts run in order: `align_walls.py`, `fit_rock_recess.py`,
`clear_corner_view.py`. They are also embedded as Blender text blocks.
`verification.json` records wall-to-edge parallelism, verticality, planarity,
and the rock surface's lack of loose edges or non-manifold junctions.
