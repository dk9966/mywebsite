# Left platform stair connection

The live scene is saved in `../platform-controls/cave-platform-sliders.blend`.
`before-stairs.blend` preserves the complete live scene before this change,
including the user's unsaved work.

The original upper stair entrance now connects through two 0.56 m open-grating
bridge panels, a 14-step descending steel flight, a square landing at half the
total height, and a second 14-step flight after a 90-degree right turn. The final
treads meet the existing lower-left platform at its actual current elevation.
Framed grating, slender double rails, stringers, landing supports and warm marker
lights follow the supplied reference and the existing bridge materials.

The landing has four corner supports, and the bottom flight is parallel to the
lower platform's long side. The upper approach now leaves the center platform
radially, perpendicular to its rim, and meets a triangular grating extension
attached to the square landing. The triangular extension is about 0.27 m deep.
The square landing, its supports and railings, and the full lower flight retain
their exact meshes and transforms from the aligned scene.

`before-four-supports-alignment.blend` preserves the earlier support layout;
`before-radial-triangle.blend` preserves the scene before the radial approach.

New objects are in `166 | Left bridge and right-turn steel stairs`. The old
stairs and obstructing entrance fixtures remain in the disabled collection
`Archive | front-left straight stair blockout`. The center platform guardrails
have a reversible Boolean opening. Original meshes and object transforms were
verified unchanged; 22 floor probes verify all four support footprints and the
lower stair foot, and the measured parallel-alignment error is zero degrees.

To reproduce from the original blockout, run `build_stairs.py` followed by
`refine_radial_entry.py`. The latter changes only the upper approach and adds
the triangle. `radial-entry-report.json` records the perpendicularity check and
the preservation of all 119 protected objects. `render_preview.py`
creates an inspection render in a separate Blender process and never changes the
saved camera or scene lighting. `build-report.json` and `verification.json`
record dimensions and geometric checks.
