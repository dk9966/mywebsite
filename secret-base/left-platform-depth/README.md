# Deeper left platform

Saved into `../platform-controls/cave-platform-sliders.blend` and `extended-platform.blend`.

The wall side is extended 1.5 m, approximately 1.12 times the 1.34 m middle stair landing. The platform depth is now 7.546 m. The stair assembly and original front edge remain fixed. Four armored supports, their fixtures and wall skirts move inward together. The cave deformation is the reversible shape key `Left bay | 1.5 m deeper platform recess`.

Both side rails and underside frames extend into the recess. Six matching posts and 28 deck panels fill the additional area. The return support's rock shoes and ties are fitted to the deformed wall.

`before-extension.blend` preserves the live scene, including unsaved edits, before this operation. `extend_depth.py` reproduces the geometry from that backup and refuses to apply it twice. Original mesh datablocks are retained. `verification.json` records 54 supported floor feet/anchors, all eight wall anchor contacts, and 2,056 unrelated objects unchanged. Perspective and top-down renders were inspected alongside the live viewport. `render_inspection.py` makes temporary cutaway/lighting changes in a separate Blender process and does not save them.
