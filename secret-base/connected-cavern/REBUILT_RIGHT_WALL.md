# Rebuilt right cave wall

Open `connected-cavern-right-wall-rebuilt.blend` for this revision. An already-open Blender file will not automatically reload this separate file.

The right terrain has been replaced with a continuous interior surface using the pillar surface mesher and the accepted left wall's broad stepped field. It retains the existing basalt material, uses defined flat-shaded edges, and has no outer skin, thickness, remeshing, or smoothing modifiers. Both platform recesses are incorporated into the same wall. The lower facade meets the six existing support anchors.

The middle pillar, platforms, bridge, props, and lighting are preserved from `connected-cavern-single-surface.blend`. The accepted left wall's surface is preserved to floating-point tolerance.

## Renders

- `right-wall-rebuilt-overview.png`: full interior and both recessed platforms.
- `right-wall-rebuilt-comparison.png`: central pillar beside the rebuilt right cliff.
- `right-wall-rebuilt-under-platform.png`: rock detail and support connections.
- `right-wall-rebuilt-plan.png`: overhead surface inspection, temporarily rendered in Workbench.

The saved scene uses the overview camera and Cycles. The inspection render's display changes are not saved.

## Verification

`right-wall-rebuilt-verification.json` records the saved-file checks and SHA-256:

- One connected wall mesh with 21,433 vertices and 37,364 faces.
- Two open boundary loops for the top and bottom; no loose edges, branching edges, or degenerate faces.
- All six support anchor distances are zero.
- No obstruction in the sampled bridge lanes or the 628 sampled standing-space locations across both platforms.
- No gaps in 1,800 enclosure ray probes.
- All 1,113 non-wall meshes and the original light settings match the source.
- Across 490 left-wall probes, maximum surface difference is 0.0000191 scene units.

These numerical checks supplement inspection of the four renders; clearance and gap probes are sampled checks.

## Reproduction

Run from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/connected-cavern/rebuild_right_wall.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/connected-cavern/verify_rebuilt_wall.py
```

The generator reads the preceding single-surface Blender file, the accepted enclosure field, the original pillar mesher, and the existing platform/support layout data. It saves a new Blender file rather than replacing the source.
