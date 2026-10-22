# Expanded lower-left rock foundation

The changes are installed in the active Blender session. Automatic approval
review blocked overwriting the live file; the verified result is saved as
`expanded-foundation-preview.blend`.

The foundation is widened to approximately 70% of the platform footprint.
An independent 7,980-point sample measured 70.14% contact. The widened shelf
retains the wall seam and blends into the lower cliff through a tapered shoulder.

Eight long-edge braces now measure approximately 2.6–3.1 units, down from
5.4–6.1 units. Four new individual braces support the front short edge, with
rock-mounted shoes, underside bearers, and rim plates. Their mounting positions
follow the curved rock; their shafts remain outside the rock surface.

The earlier braces are retained in a hidden archive collection. The expanded
terrain is a reversible shape key. `before-expansion.blend` preserves the
entire saved scene from the start of this edit.

To reproduce, execute `expand_support.py`, `soften_transition.py`, then
`fit_front_braces.py` against the backup. The final saved preview is
`expanded-foundation-preview.blend`. `verification.json` records attachment,
mesh, clearance, and preservation checks; `final-live-check.json` records
independent coverage and unchanged unrelated live objects. Pre-existing rear
wall intersections are preserved and distinguished from newly introduced ones.

Inspection images isolate the platform and nearby cave in a background process;
inspection lights and the cutaway are not saved into the model.
