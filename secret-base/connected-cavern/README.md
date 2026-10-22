# Cave interior — corrected surface-only version

**Current file: `connected-cavern.blend`.** Reopen this file in Blender to load the saved revision.

The thick enclosing shell has been removed. The missing walls are now one inward-facing open surface: no outside skin, thickness, caps, remeshing, beveling, or smoothing modifiers. Its stepped ledges use the original pillar field mesher, with flat faces and the original rock material.

The scene starts again from `../right-cave-bays/central-pillar-right-cave-bays.blend`, restoring the original rock meshes and materials. The one scoped terrain edit is a cut at the upper-right entrance to remove its hanging lip. The central pillar, decks, lower bay, bridge, supports, and their materials are preserved. The upper bay gains brushed-metal portal trim, inset lights, a layered balcony fascia, warm lamps matching the center, booth window mullions, and a small rear cabinet bank.

## Current renders

- `interior-overview.png`
- `interior-upper-bay.png`
- `interior-reverse.png`
- `interior-surface-plan.png` — the narrow wall profile confirms there is no outer shell.

The older `cavern-*.png` images show the rejected thick-shell version. Files prefixed `preview-` are ignored iteration artifacts.

## Rebuild

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/connected-cavern/build_interior_cavern.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/connected-cavern/verify_connected_cavern.py
```

`build_connected_cavern.py` delegates to the current generator. The generator is also embedded in the Blender file. `interior-preservation.json` describes the scoped upper-mouth cut. `saved-file-verification.json` checks original mesh/material preservation, rock samples outside that cut, single-surface connectivity, open boundaries, bridge clearance, enclosure coverage, and support contacts.
