# Lower-left display bay

Built in the live Blender scene and saved to `../platform-controls/cave-platform-sliders.blend`. `left-platform-display-bay.blend` is a separate saved copy; `before-display-bay.blend` preserves the initial live state including unsaved edits.

The addition lives in `169 | Left platform display bay`, with separate collections for supports, wall details, and flooring. All new parts follow the existing landing through parenting. The latest correction is saved in the live scene and `wall-fit/left-platform-wall-fit.blend`.

- Four 4.15 m tall armored supports, 0.70 m wide, with straight upper sections, outward-sloping lower feet, 0.20 m deep center channels, bolted anchors, and amber practical lights.
- Two supports sit behind the stairs; the third leaves a 5.95 m wide by 2.65 m high screen opening. The fourth faces across the platform on the perpendicular return. No screen or text was built.
- Low metal wall panels and a clipped metal floor grid fit the existing platform.
- Three cyan strips are each 5 m long, with 0.95 m equal center spacing, parallel to the platform's long edge. Their nearest extent is 0.718 m beyond the stair walking surfaces in plan.
- The cave wall is flattened and brought forward locally with the reversible `Left bay | flatter close wall and short anchors` shape key. The eight wall connections are now 0.285–0.344 m long. Existing upper-platform sculpt keys and unrelated objects are preserved.

`verification.json` records measurements, mesh closure checks, stair collision checks, and preservation signatures. All 1,788 pre-existing object signatures were unchanged immediately after the build. Later live terrain state changed independently; it was retained when saving, and all eight rock anchor contacts were rechecked against that current terrain. No support intersects the existing stair geometry.

`build_display_bay.py` reproduces the additions from the pre-build scene and refuses to duplicate an installed bay. `render_inspection.py` renders from a copy using temporary isolation and inspection lighting. It never saves those camera, lighting, or visibility changes. `perspective.png`, `top.png`, and `support-detail.png` show the inspected geometry.

Run `fit_wall_and_align_lines.py` after the initial build to apply the latest correction. It preserves a pre-edit backup in `wall-fit/before-wall-fit.blend`; `wall-fit/verification.json` and the three PNGs in that folder document the corrected wall, shortened ties, and aligned floor layout.
