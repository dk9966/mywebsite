# Bridge ends fitted to the circular platform

The live edited scene is `../platform-controls/cave-platform-sliders.blend`.

All three bridge entrances have a curved cut that follows the circular rim,
with a 1.2 mm fitting gap and a narrow steel end frame. The 25 affected deck,
grating, and support objects use editable Boolean modifiers. The cutter
inherits the rim's existing radius driver. Two overlapping threshold plates
are retained in a disabled archive collection.

The existing 2,854 objects retain their source meshes, transforms, and
materials. Railing assemblies are unchanged. The original live scene,
including unsaved changes, is preserved in `before-circle-fit.blend`.

- `fit_bridges.py` applies the change to the original scene.
- `verify_fit.py` checks evaluated clearance at the current radius and two
  nearby slider settings, plus driver validity, in an isolated scene copy.
- `render_check.py` renders each entrance without saving presentation changes.
- `final-front.png`, `final-stairs.png`, and `final-rear.png` show the result.

The Boolean self-intersection option is enabled for welded grating so all
crossing bars are correctly retained and trimmed.
