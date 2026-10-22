# Terrain fitted to the user's platform layout

Result: `coherent-bays.blend`.

The input is `user-layout-snapshot.blend`, a copy of the user's unsaved Blender session. It preserves their chosen lower bay location and their raised, shifted upper bay. Terrain recesses and the lower rock foundation are fitted to these measured positions. The selected left shoulder beside the lower bay extends outward as part of the connected wall.

Several floor plates and ring surfaces had not followed the user's move. Those pieces are aligned to the moved railings, props, and lights. The bridge is fitted to the new lower landing and the metal support shoes are seated on the new rock. The center island and 377 user-positioned platform meshes are checked for preservation.

`coherent-bays-overview.png`, `coherent-bays-detail.png`, and `coherent-bays-foundation.png` show the result. The two JSON check files record wall connectivity, clear floor space, preserved positions, bridge clearance, and rock beneath the deck.

Rebuild from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-user-fit/fit_user_layout.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/right-bays-user-fit/verify_fit.py
```

The generator reuses the previous basalt meshing code only for the terrain, then installs that terrain into the user snapshot. It does not regenerate the user's platforms or furnishings.
