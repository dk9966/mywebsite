# Left platform railings

Saved in `../platform-controls/cave-platform-sliders.blend`.

The five exposed sides of the bottom-left landing now have continuous,
mitered dark-steel upper and middle rails, 44 slender posts with alloy feet,
and a matching low curb. Dimensions and materials match the lower-right
platform. The rails follow the current clipped corners and are parented to
the landing. The wall side stays open, and the stair landing remains clear.

`before-railings.blend` preserves the live scene before this addition,
including unsaved user edits. `verification.json` records the dimensions
and confirms all 44 feet are seated and all 1,551 pre-existing object meshes
and transforms are unchanged. The nearest new railing is 4.21 m from the
center of the final stair tread.

`add_railings.py` builds the addition in the original scene; it refuses to
duplicate an existing railing collection. `render_preview.py` renders an
inspection image in a separate Blender process without saving camera or
lighting changes.
