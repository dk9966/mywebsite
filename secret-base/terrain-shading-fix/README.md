# Terrain shading repair

The active file is `../platform-controls/cave-platform-sliders.blend`. A separate repaired copy is `terrain-shading-fixed.blend`. `before-applying-fix.blend` preserves the complete live scene immediately before applying the repair; `before-terrain-shading-fix.blend` is the initial investigation snapshot.

## Findings and changes

- Every one of 235 camera-visible cave ray samples hit the back of the cave shell. Reverse the cave polygon winding so its normals face the cavity. The center pillar already had outward-facing normals. Vertex positions, topology, flat shading, and sculpt attributes are preserved.
- The local fog volumes masked the rear and left wall detail with bright clouds. A comparison render with only those volumes disabled confirmed their contribution. Reduce center/front-left local mist to 22% and the enclosed-room/rear-left mist to 60% of the previous density. Global haze and the Beam visibility control remain active.
- Reduce the rock's broad bump from strength 0.42/distance 0.21 to 0.16/0.045, and grain from 0.19/0.018 to 0.12/0.008. Roughness is 0.90 and specular level 0.18. This preserves the low-poly shape and stone color while reducing streaks and shading exaggeration.
- Move the two existing terrain-only lower bounce lights toward the camera side, enlarge them to 10 units, and set their base power to 500 W each. Their Cave ambience driver and receiver links remain intact. The wider, lower fill softens the under-deck rock shadow transition.

The platforms, architecture, camera, original rock shapes, and shared lighting slider values are preserved. `verification.json` records reopened-file checks. Final comparison images are `before.png` and `final-camera.png`.

`apply_fix.py` applies the changes once to the live scene and refuses to flip the cave normals a second time. The diagnostic scripts are investigation passes, not required when opening the repaired blend file.
