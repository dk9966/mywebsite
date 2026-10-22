# Lower-left platform wall and supports

Installed in the live Blender session, but saving the live file was blocked
because of concurrent unrelated stair edits. `left-platform-fitted.blend` is the
saved task-only result, assembled from the initial backup plus this rock sculpt
and its new supports. The active live scene was not reloaded or overwritten.
`before-left-fit.blend` preserves the complete live state before editing,
including unsaved user changes.

The existing continuous cave wall now follows the platform's long outside edge.
A flat rock bearing shelf contacts the slab underside, with a tapered foundation
and relaxed transitions into the surrounding cliff. The sculpt is reversible
through the rock's `Left landing | fitted wall and bearing shoulder` shape key.
The original rock mesh is also retained with a fake user.

Eight splayed diagonal steel braces use the lower-right platform's structural
steel material, beam dimensions, bevels and rock anchor shoe style. Four paired
brackets connect embedded rock shoes to underside cross bearers and the perimeter
frame; the end pairs follow the slab's clipped corners. New parts are in
`167 | Left platform cliff supports` and are parented to the landing.

`verification.json` records wall contact, 150 rock bearing samples, clear walking
surface, eight brace connections, closed new steel meshes, unchanged existing
boundary components in the cave, and the original camera. The initial preservation check passed for every unrelated
object. Later concurrent edits to stairs and entrance fixtures were detected and
preserved; the final sculpt refinement changes only the cave mesh.

To reproduce from the backup, run `sculpt_and_support.py`, then
`finish_sculpt.py`. `verify.py` compares the saved preview against the backup.
`render_inspection.py` isolates the landing, stairs and nearby rock in a separate
background process, using temporary inspection lights. It never saves those
isolation or lighting changes. The inspection PNGs show those isolated views.
