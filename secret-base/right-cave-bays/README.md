# Central pillar with two recessed right cave bays

`central-pillar-right-cave-bays.blend` is the editable scene. `right-bays-overview.png` shows the calibrated wide view; `right-bays-detail.png` is a native Blender crop of the right-hand architecture at the same angle. `right-bays-supports.png` shows the lower garage brackets and rock anchors from below.

The finished middle island comes from `../central-metal-platform/central-metal-platform.blend`. Its rock, deck, console, materials, and transforms are preserved. The only geometric change to the middle island is an opening in the right fence for the short connecting bridge.

The lower garage and upper hangar use the platform footprints, projected angles, and relative positions in `../../design-references/misty-abyss/right-cave-bays-reference.png`. The camera uses a 32 mm lens on a 36 mm sensor (58.72° horizontal field of view). The hangar is both higher and farther back than the lower bay. Both rooms are excavated into full 3D rock volumes; they are not freestanding roofed islands. The wall reuses the approved pillar's connected outcrop mesh and stone material, stacked at a comparable vertical fracture scale and shaped with editable Boolean cutters.

The lower apron has a flush circular turntable, service benches, cabinets, tool boards, and railings that terminate against the forward right cave wall. Its rock face is advanced locally beneath the deck, with six steel cantilever brackets comprising I-section joists and diagonals, gussets, hex bolts, bearing plates, and embedded grout seats. The original upper rock and middle island are preserved. The upper bay has a recessed flight deck, small control tower, balcony, and service gantry. **There are no vehicles, stairs, or water.** Cool practical lights, warm central lamps, and restrained dry haze provide the cave lighting.

## Rebuild

From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-cave-bays/build_right_bays.py -- --final --samples 64 --width 2000
```

Validate the saved file independently:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-cave-bays/build_right_bays.py -- --verify
```

`preservation.json` records the source-mesh fingerprint check, bridge passage checks against evaluated rail and rock geometry, upper-balcony visibility, and absence of vehicle or stair objects. `right-bays-audit.json` records camera, platform, and bridge coordinates. Both the main generator and `refine_platform_supports.py` are embedded as Blender text blocks. The latter performs the local rock adjustment and bracket construction; the main rebuild command runs it automatically. `support-connections.json` records the measured rock anchors, and validation checks their positions against the saved rock geometry.

Preview files are exploratory iterations and are ignored by Git. Earlier previews may contain vehicle props; they are absent from the delivered scene and from the final generator.

## Visual review

Two independent visual critics reviewed the iterations. The final geometry received **9/10 for spatial layout** and **8/10 for visual integration**, with no remaining must-fix findings. See `review.json`. The cliff deliberately retains the approved central pillar rock style instead of reproducing the reference rock texture.

The subsequent rock/support revision received **8.5/10** from the visual critic, with no visible must-fix connection or shape defects. Cave Boolean results are baked to editable meshes before the local rock deformation; the generator retains the complete construction process.
