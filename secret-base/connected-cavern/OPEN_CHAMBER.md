# Central island in a wider cave

Open `connected-cavern-open-chamber.blend` for the revision removing the entire right side. The preceding Blender files are retained as earlier versions.

Both right platforms, their equipment, supports, bridge, and excavation geometry have been removed. The replacement cave is one connected interior surface, open at its top and bottom, with no thickness, exterior shell, or modifiers. It uses the existing basalt material and the original pillar mesher's broad stepped surface pattern.

The cave is wider around the central island. The nearest measured distance from the platform geometry to the wall is approximately 5.19 scene units. There is extra space toward the front. The 237 central rock, console, and deck meshes are unchanged; the full original 164-mesh perimeter railing is restored to close the former bridge opening.

Renders:

- `open-chamber-overview.png`: primary interior view.
- `open-chamber-reverse.png`: view from behind the console.
- `open-chamber-plan.png`: overhead view showing the clear spacing and single wall surface.

`open-chamber-verification.json` records connectivity, the two open boundary loops, clearance measurements, 1,800 enclosure ray probes, central geometry preservation, and saved-file verification. The saved file uses the overview camera and Cycles. Temporary Workbench display changes for the overhead render are not saved.

Regenerate headlessly from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/connected-cavern/build_open_chamber.py -- --final
```
