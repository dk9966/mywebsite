# Platform surround and sculpt seam repair

The live cave edits are preserved in `before-seam-repair.blend`. The repair uses
local vertex groups and reversible modifiers on `150 | continuous cave with
oblique carved rooms`. Its original vertex positions, shape keys, and existing
architecture are retained.

The `Seam repair |` modifiers relax the pinched lower-roof seam and bring its
recess forward. The `Surround repair |` modifiers bring out the upper-right
shoulder, fit the stone to the evaluated upper roof/light height, extend the
rock above the lower light, preserve clearances, and restore flat face shading
in the edited region. Disable these modifiers to compare with the original.

`before.png` and `after.png` use the same view. `verification.json` records
connectivity, topology, and sampled platform/light clearances. These are
sampled checks at the recorded control settings, not a guarantee for every
possible slider combination.

## Manual sculpting method

Clear the `grab` filter in the sculpt brush shelf to see the other brushes.

- Use **Fill/Deepen** to raise a recessed groove toward the surrounding surface.
- Use **Clay Strips** or **Clay** to build the volume above/beside the light.
- Use a large **Grab** brush for broad repositioning. View from the side to
  control depth; Grab follows the screen plane.
- Hold **Shift** for short, gentle smoothing passes. Prolonged smoothing
  shrinks the form. Use **Scrape/Fill** or **Scrape Multiplane** to retain broad
  rock planes.
- Restore **Shade Flat** for visible triangle facets. Smooth geometry and
  smooth shading are different. Flat shading does not repair long, thin faces.
- For badly stretched faces, edit the local topology: subdivide oversized
  faces, relax the spacing, and triangulate. Match the surrounding face sizes.
  Avoid adding dense Dyntopo detail if the target is a coarse faceted style.

This cave has shape keys and modifiers which re-fit sculpted points. For free
manual sculpting, duplicate the terrain and convert the duplicate to Mesh,
retaining the procedural original separately. The converted copy freezes its
current evaluated appearance and will not keep following the original sliders.
Mask around roofs and fixtures before sculpting. For exact roof contact,
proportional vertex editing or a localized Shrinkwrap is more precise than
freehand brush strokes.

A real missing-face hole needs an Edit Mode fill/bridge, or a suitable remesh
on a closed solid. The sculpt Fill brush raises existing surface vertices; it
does not create a cap over empty space. Avoid voxel-remeshing this entire open
cave shell with its shape keys and controls.

References:
- https://docs.blender.org/manual/en/4.5/sculpt_paint/sculpting/brushes/grab.html
- https://docs.blender.org/manual/en/4.5/sculpt_paint/sculpting/brushes/brushes.html
- https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/face/shading.html
