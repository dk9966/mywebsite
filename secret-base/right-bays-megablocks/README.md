# Basalt bays and forward bridge

Open `basalt-bays.blend` for this revision. The earlier `right-bays-150/bays-150.blend` is preserved.

Both right bays slide 2.4 scene units deeper along the wall, retaining their accepted oblique orientation. The central platform's bridge attachment is now at 125 degrees, measured clockwise from the back (+Y). Its other end lands at the middle of the lower octagon's straight front edge, with a small overlap into the floor. The old wing opening is closed, and the central guardrail opening follows the new bridge.

The lower floor remains a single octagon joined to a rectangular left wing. Its marking and overhead lamp stay centered on the octagonal portion. The upper floor remains the six-sided extended rectangle with two 45-degree front corner clips.

The connected cave surface now uses long, staggered basalt megablocks with shallow rectangular extrusions and occasional smaller attached shoulders. Broad faces dominate over narrow vertical strips. The original pillar step mesher generates the surface, with restrained weathering and defined edges. The approved central rock, console, and machined deck are preserved.

## Outputs

- `basalt-bays-overview.png`: final scene view, 2400 × 1344.
- `basalt-bays-detail.png`: close view of both bays and the bridge.
- `basalt-bays-plan.png`: top-down arrangement.
- `basalt-bays-lower-footprint.png` and `basalt-bays-upper-footprint.png`: isolated floor boundaries.
- `basalt-bays-checks.json`: construction and preservation checks.
- `basalt-bays-saved-checks.json`: independent checks after reopening the saved file.

## Reproduce

From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-megablocks/build_basalt_bays.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-megablocks/verify_basalt_bays.py -- basalt-bays
```

The generator loads `connected-cavern/connected-cavern-open-chamber.blend` and uses the shared pillar mesher at `meshes/pillars/island_pillar_src/shape.py`. Its source is also embedded in the output blend file.

Verification covers 237 preserved central meshes, a single connected cave wall, invalid edges, support anchors, standing clearance, key floor visibility, bridge railing clearance, the 125-degree attachment bearing, and the octagon landing position. Two fresh-context critics separately reviewed placement and the basalt surface; both accepted the final preview.
