# Circular workshop roof light

The live scene is saved in `../platform-controls/cave-platform-sliders.blend`.
`circular-roof-light.blend` is a matching copy of this change.

In Blender, use **SCENE SLIDERS → Modifiers → Scene Sliders → Light height above walls (m)**.
The default is **1.15 m**, with a **0.35–2.10 m** range that fits below the upper platform.

The dark circular fixture is centered on the lower platform's actual footprint.
Twelve segmented white rim lights and underside lenses surround its recessed base.
Four planar roof slopes connect the four wall directions to the fixture. The smaller
coplanar wall bays share a single roof plane. Height changes move the fixture, its
area light, roof seams and roof ends together while keeping every wall anchor fixed.

All controls are native Geometry Nodes inputs and drivers; no add-on, handler or
Python autorun is required. The previous overhead hood is hidden and retained.
The obstructing cave overhang is locally recessed, with the original terrain mesh
retained in the file. Other existing meshes and transforms are preserved.

`before-circular-roof-light.blend` preserves the complete scene before this change.
`verification.json` records the height, planarity, manifold and preservation checks.
`circular-roof-preview.png` shows a rendered close-up.

Scripts are intended for the checkpoint scene: run `build_light.py`, then
`fit_ceiling.py`, then `verify_light.py`. They guard against accidental repeat runs.
