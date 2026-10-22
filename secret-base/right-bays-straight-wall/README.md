# Forward bays with a straight cave wall

Open `straight-wall-bays.blend`. This adjusts the previous `right-bays-megablocks/basalt-bays.blend` result; that earlier file remains available.

- Both bays move 1.10 scene units toward the camera along the previous wall, reversing roughly half of the previous 2.40-unit move into the cave.
- Their shared facade rotates 12 degrees toward the camera, from -84 to -72 degrees in cave coordinates.
- The perpendicular return immediately beside the bays is removed. The facade and its foreground continuation are collinear, then join the front cave perimeter through shallow turns farther away.
- Basalt steps use the previous arc-length field and random seed. Existing wall sections away from the changed contour retain their block arrangement, shader, and sharp-edged treatment.
- The bridge retains its 125-degree central attachment. Its other end is trimmed to the octagon edge, with a railing gap calculated for the revised approach angle.
- The central rock, console, and machined deck remain preserved. Floor footprints, stacked bay heights, floor marking, centered lower lamp, and contents retain their accepted designs.

The saved scene has one connected inside wall, without a cave ceiling, cave floor, vehicles, or water. Main and close-up renders are 2400 × 1344; plan and isolated floor-footprint renders are also included. `straight-wall-bays-full-plan.png` shows the complete cave perimeter and its foreground joins.

## Reproduce

Run from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-straight-wall/build_straight_wall.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-straight-wall/verify_straight_wall.py -- straight-wall-bays
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-straight-wall/render_full_plan.py
```

The builder uses the original open chamber as its source and the original pillar step mesher. Its source is embedded in the saved blend.

`straight-wall-bays-checks.json` records construction checks. `straight-wall-bays-saved-checks.json` independently checks the reopened file for preservation of 237 central meshes, wall connectivity and invalid edges, floor standing clearance, camera visibility, bridge passage, the attachment bearing, the landing position, and collinearity across the removed corner.

Two fresh-context critics reviewed the preview against the user's marked plan and the previous scene. Both accepted the placement, wall continuation, and bridge connection.
