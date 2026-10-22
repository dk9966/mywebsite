# Joined interior cave

Open `connected-cavern-single-surface.blend` for this revision. It is separate
from `connected-cavern.blend`, which remains the earlier upper-bay revision.

The former four solid right-wall masses and the surrounding interior wall are
now a single connected mesh: `Cavern | single connected interior surface` in
collection `13 | Joined interior cave surface`. Hidden exterior faces and
enclosed rock cavities were removed. The top and bottom remain open.

The integration intersects the existing polygons, retains their exposed
planes and folds, and joins the seams. It does not voxel-remesh, smooth, or
change the original rock shader. The center island, both bays, bridge,
engineered supports, upper-bay finish, and lighting are preserved.

Renders:

- `single-surface-overview.png`: interior overview.
- `single-surface-reverse.png`: reverse interior view.
- `single-surface-plan.png`: full overhead geometry inspection in studio shading.

`integrate_right_surface.py` builds the surface from the frozen
`preview-integration-source.blend` snapshot. This snapshot matches the
upper-bay revision with SHA-256
`4cfb3da0fbdd6c49bbc1443f64a434e7be94f69400aa27b183bed70bf0a9d382`.
`finalize_single_surface.py` saves the named deliverable and renders it.
Both scripts run with Blender 5.1 in background mode.

`verify_integrated_surface.py -- connected-cavern-single-surface.blend`
checks preservation of all 1,113 non-wall meshes and original lights, wall
connectivity, edge topology, sampled enclosure coverage, bridge clearance,
the six rock anchors, and open ceiling/floor. Results are saved in
`single-surface-verification.json`. Camera ray comparisons also record
differences caused by removing overlapping source surfaces and the old solid
wall's hidden cap faces.

An already open Blender window will not reload a headlessly saved file. Open
the new filename explicitly to see this revision.
