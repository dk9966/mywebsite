# Consistent railing posts and feet

The edited live scene is saved in
`../platform-controls/cave-platform-sliders.blend`.

All 175 active guardrail posts now use a 28 mm square dark-steel section and
a compact 52 × 52 × 24 mm alloy foot. The 26 oversized center-platform
plates have been replaced with the small style. Stair feet retain their
existing mounting elevation. The 22 stair rail sections use the same
25 × 18 mm profile and dark-steel finish as the platform railings.

The center-platform supports are evenly spaced along the three arcs between
the bridge and stair openings. The short side of the front bridge now has three
equal bays. A single support centered on the short stair landing return
replaces the crowded pair there. The two clipped shoulders on the rear
platform use the same single-support treatment. Four redundant post-and-foot pairs are
preserved in the disabled collection
`Archive | railing spacing before consistency`.

`before-railing-consistency.blend` preserves the original live scene,
including its unsaved edits. `normalize_railings.py` applies the change to
that original scene. It verifies every evaluated foot's dimensions and
alignment, all post separations, driver validity, and the preservation of
unrelated object meshes, transforms, materials, and visibility.
`include_rear_bridge.py` brings the rear platform, which was added to the
live scene during this edit, into the same standard and adds its two missing
terminal feet. Six additional left-platform posts created during the edit
inherit the same compact geometry. `verify_final.py` checks all 175 evaluated assemblies,
including unclipped upright heights and contact with the top rails, then saves.
`connect_rear_returns.py` closes the four short rail gaps at the rear bridge
with matching metal elbows fitted to the existing rail ends.
`verification.json` records the checks. The closest remaining post centers
are 0.438 m apart.

`render_check.py` creates close-up inspection renders in a separate Blender
process and does not save camera, lighting, or visibility changes.
