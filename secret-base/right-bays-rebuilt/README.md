# Recessed right cave bays

Open `reference-bays.blend` for this revision. The input scene, `../connected-cavern/connected-cavern-open-chamber.blend`, is preserved. An already-open copy of an earlier Blender file will not update automatically.

The lower deck is one continuous octagon-and-left-wing polygon. Its circular marking and overhead lamp share the octagon center. The upper deck has six sides: a long rectangle with two equal 45-degree front corner cuts; its left edge extends 1.4 scene units while its right edge remains at local x=2.2. The lower bay turns 35 degrees toward the camera; the upper bay uses a shallower 10-degree turn to follow the composition reference.

Both bays are recessed into a single connected interior cave surface. The bridge enters the short left edge of the lower wing through an open railing gate. Brackets terminate on the rock surface. No vehicles or water are included.

## Renders

- `reference-bays-overview.png`: composition and middle-island relationship.
- `reference-bays-close.png`: both recessed bays.
- `reference-bays-side.png`: alternate interior view.
- `reference-bays-plan.png`: overall plan inspection.
- `reference-bays-lower-footprint.png`: isolated lower floor polygon and centered ring.
- `reference-bays-upper-footprint.png`: isolated six-sided upper floor.

## Validation

`reference-bays-verification.json` records one wall component, no invalid mesh edges, no sampled rock intrusions into standing space, and all 12 support anchor points seated on the wall. All 237 protected middle-island rock, console, and deck meshes retain their source fingerprints. The central railing is opened only at the new bridge connection.

`reference-bays-saved-check.json` independently verifies the reopened final file: protected middle meshes unchanged, no cave-wall occlusion at the sampled floor/light landmarks from the overview and close cameras, and no railing blocking the bridge passage across three lanes at two heights. These are targeted geometry checks, not exhaustive collision testing.

## Independent critique

Two fresh-context subagents reviewed reference images, renders, floor plans, and the geometry checks through the preview iterations. Their final preview scores were **8.5/10 for geometry and placement** and **7.5/10 for overall visual match**. Both reported no remaining structural blockers. The final render pass then widened the detail framing, strengthened brackets and fixing plates, and reduced broad cave fill light.

Remaining visual differences: the broad rock band between bays is more architectural than the reference, and the cave lighting is more uniformly blue. The final detail views also crop some of the underside; the overview shows the lower support arrangement. These grades describe the last reviewed preview, not a separate review of the final renders.

## Reproduce

From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-rebuilt/build_reference_bays.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-rebuilt/verify_reference_bays.py -- --final
```

The generator uses the accepted cave field and pillar shaping code from this repository. It selects Cycles Metal when available and falls back to CPU. The final file uses the overview camera; the other inspection cameras remain in the scene.
