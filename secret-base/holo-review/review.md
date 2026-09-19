Holo table review — 2026-09-11

Added to the center of deck_floor_about in base.blend; exported through export_pillar.py to models/pillar.glb. Rebuild script: ../build_about_holo.py. Backup: before-holo.blend.

Iteration 1, independent visual reviews of iteration-1.png against the user reference:
- judge_one: 8.3/10. Centered convincingly, good clearance and pedestal height; segmented metal and controls match the architecture. No must-fix issues.
- judge_two: 8.4/10. Reference silhouette is clear; materials, bevels and lights fit the scene. No change necessary to pass 8/10.

Both suggested optional variation across the projection surface. Kept the clean geometric surface to match the existing scene and preserve reliable glTF material export. First iteration met the requested threshold.

Validation: GLB parsed successfully, batching preserved triangle count and world bounds, cleanup and repeated batching checks passed (803 to 93 draw calls for the complete station).

Browser screenshot verification could not complete: screenshots timed out. Visual approval is based on the Blender render, not browser appearance.

Iteration 2 — user requested a significantly shorter neck and thinner tabletop.
Matched the Projects worktop height above its deck: 0.484021 units. Reduced vertical dimensions by 44.97%; preserved diameter and centered placement. Exported GLB verification: holo surface height 0.484021138, Projects height 0.484021524, drum thickness 0.137584, neck height 0.269665. Both surfaces agree within 0.000001 units.
Independent revised reviews: judge_one 8.5/10, judge_two 8.6/10. Both confirm the lower profile is coherent and requires no further visual changes. Render: iteration-2.png.
