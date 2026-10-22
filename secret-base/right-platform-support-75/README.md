# Lower-right platform: 75% rock support

The completed edit is installed in the live Blender scene and saved separately
as `right-platform-75-preview.blend`. The active file was not overwritten.
`before-right-75.blend` preserves the complete starting live scene.

A closed, tapered rock shoulder extends the existing cliff beneath the octagonal
platform. Its flat bearing surface intersects the slab underside by 0.014 units.
The lower and rear body is embedded in the existing rock. It shares the cave's
coordinate frame and existing slate material. This addition preserves the prior
cave mesh and all lower-left sculpt shape keys.

A stratified 26,795-point check measures 74.99% terrain support. Eight compact
steel braces now occupy six exposed edges: front, front-left corner, left,
rear-left corner, rear, and right. Braces are approximately 0.43–0.83 units long,
down from the former 2.84–4.27-unit front brackets. Each has a rock anchor shoe,
underside bearer, and rim attachment. Positions already occupied by the original
cliff do not receive buried braces.

The new parts are in `168 | Right platform rock shoulder and compact supports`.
The former long front supports remain in the hidden archive collection. The
platform, railings, architecture, bridge, camera, cave mesh, and earlier left
platform work are unchanged.

`build_foundation.py` reproduces the addition from the backup. `verification.json`
records closed meshes, clear brace centerlines, attachment contacts, no new
walking-surface intrusions, and unchanged original meshes/transforms/shape keys.
`contact-area-check.json` contains the final finer area measurement.

The inspection renders use temporary lights and a local cave cutaway in a
background process. Those camera, lighting, and visibility changes are never
saved to the scene.
