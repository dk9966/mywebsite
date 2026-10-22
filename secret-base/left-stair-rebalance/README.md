# Longer upper flight and shorter parallel lower flight

Saved in `../platform-controls/cave-platform-sliders.blend` and `rebalanced-stairs.blend`.

The square moves 1.505 m toward the wall supports, 0.310 m along the platform, and 1.238 m down. The upper flight increases from 14 to 22 steps (2.690 m to 4.226 m horizontal run). The lower flight decreases from 14 to six steps (3.060 m to 1.311 m run), remaining parallel to the platform's long edge. Original riser heights, tread goings, square dimensions, grating, two entrance bridge bays and radial upper alignment are retained.

Railings, stringers, marker lights, triangular infill, four landing legs and their braces follow the new stair geometry. Replaced parts remain in `Archive | stairs before longer upper flight`. `before-rebalance.blend` preserves the full live scene before editing, including unsaved changes.

`rebalance_stairs.py` reproduces this edit from the backup and refuses a duplicate application. `verification.json` records exact tread elevations, all four landing feet seated, no mesh collisions with the armored supports, the lower direction parallel to the platform, and 2,329 unrelated objects unchanged. Perspective and top-down inspection images were checked before the main scene was saved. Temporary render cameras, cutaways and inspection lighting are not saved in the model.
