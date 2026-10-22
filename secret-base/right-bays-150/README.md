# Fresh 150-degree right-side bays

This rebuild starts from `../connected-cavern/connected-cavern-open-chamber.blend`, before either right platform existed. It does not load the rejected right-bay file or import its architecture builder. New floors, openings, room fittings, supports, bridge, and lighting are constructed in `build_bays_150.py`.

The approved middle island's rock, console, and metal deck are preserved. The bridge has a new opening in the middle railing; preservation checks intentionally distinguish this opening from the 237 protected meshes.

## Geometry

- Lower floor: one polygonal prism uniting a regular octagon with a rectangular left wing. Ring and overhead lamp share the octagon's center. The apron projects forward of the cliff mouth, keeping the full ring visible from the main camera.
- Upper floor: six-sided rectangle with two equal 45-degree front corner cuts. Its left edge extends to local x=-4.15; the right edge remains at x=2.2.
- The assembly presents its front at approximately 59 degrees to the main camera, corresponding to the reference sheet's 150-degree view. Its broad near/right return partly conceals the room edges.
- Both rooms occupy one connected inside cave surface. There is no second exterior shell, cave ceiling, floor, water, vehicle, or detached stair.
- The terrain uses the original pillar's shared-edge step mesher and a new cliff contour with irregular faceted strata. The new right cliff has a separate copy of the basalt shader with stronger fracture relief and varied roughness, plus small one-facet edge chips. The middle island's material is unchanged.

## Reproduction

From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-150/build_bays_150.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-150/verify_bays_150.py -- bays-150
```

The final file is `bays-150.blend`; final images use the `bays-150-` prefix. `--blockout` omits room fittings for silhouette review. Running without arguments produces a detailed preview. Metal Cycles rendering falls back to CPU if unavailable.

## Review and checks

Two fresh-context critics independently compared the new blockout and revisions to the 150-degree structural reference and the wider cave reference. Their first review drove the forward apron, visible left wing, front bridge landing, and shorter openings. The second review accepted their layout and identified the overly regular rock edges and low suspended light frame for further refinement.

The saved-file checker reopens the result and compares protected center meshes, samples floor headroom and camera visibility, and tests bridge passage against evaluated rail geometry. The generator also checks wall connectivity, invalid edges, and support contact. These checks are targeted rather than exhaustive collision analysis. The accepted terrain style remains more block-like than the natural rock of the photographic cave reference.

The final geometry review found no material structural blocker: the oblique rooms, right cheek, lower apron, wing, bridge, and rock-mounted lamp were coherent with the 150-degree reference. The visual review accepted geometry and lighting but requested stronger surface relief on the right cliff; the final material and edge pass addresses that specific remaining issue.

After inspecting the final overview and detail renders, the visual critic found the fracture relief and chipped edges sufficient to resolve the remaining material concern and recommended delivery. The remaining difference is a stylized large-facet geology rather than the reference's densely irregular stone. Final saved-file checks pass: one wall component, no invalid wall edges, no sampled standing-space intrusions, no tested landmark occlusion, no bridge railing obstruction, and no changes to the 237 protected central meshes.
