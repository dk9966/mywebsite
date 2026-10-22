# Grating texture conversion

Updated the live `../platform-controls/cave-platform-sliders.blend` scene. The
complete pre-edit live state, including unsaved sculpt edits, is preserved in
`before-texture-conversion.blend`. The browser GLB exports have not been regenerated; this change is in the active Blender scene.

50 visible fine-grating objects now use alpha/normal textured surfaces. These
include the middle platform's eight recessed wedges, all three bridge routes,
the switchback stair treads and landing, and the narrow platform drain grilles.
Frames, railings, structural beams, deck trim, lights and terrain are unchanged.

The bake projects the actual source bars in their original fabrication axes.
Each middle-platform wedge uses its own radial/tangential UV frame, sharing a
single texture without stretching the pattern around the entire circle. The
original panel spacing, seams and pattern directions are retained. Bridge
endpoint weights, platform width drivers and circular-joint Boolean cutters
remain active. Closed sub-millimeter sheets are used only where the cutters
require manifold geometry. Three to five sparse textured sheets within the
original bar depth recover grazing-angle occlusion and shadows; this avoids the
overly transparent appearance of a single flat layer on the stairs.

Color/alpha textures preserve holes, while tangent-space normal maps reproduce
small edge highlights. Metal color, roughness and metallic values match the
original materials. All 20 images are packed into the Blender file; the ten
shared texture pairs total about 0.32 MB as PNGs and 5.58 million texels per map
set. Fully decoded color + normal maps require about 39 MB before renderer
overhead/mipmaps. A texture card does not reproduce each bar's sidewall at very
shallow viewing angles.

Evaluated grating triangles: **207,872 → 4,860**, a **97.66% reduction** for the
converted objects. This measures geometry, not an FPS or render-time guarantee.
Alpha surfaces trade geometry work for texture sampling and transparency work.
`verification.json` records per-object counts and verifies 3,158 unrelated
objects retained their transforms, mesh data and material assignments.

- `source-geometry.json`: source coordinates, fabrication topology and weights.
- `build_textures.py`: deterministic footprint/normal bake and surface creation.
- `apply_textures.py`: guarded live-scene replacement and preservation audit.
- `refine_depth.py`: shallow texture layers for depth and shadow fidelity.
- `verify_saved.py`: independently reloads the file and exercises the width slider.
- `render_review.py`: disposable background before/after review renders.
- `textures/`: portable copies of all packed maps.

To regenerate textures, run `python3 secret-base/grating-textures/build_textures.py`.
The apply script requires the original, unconverted live scene; its guard stops
accidental double application. Restore from the backup for a full rollback.

Validation: the saved file reloads with all 20 images packed. Width was tested at the current value and ±5%; all 50 objects retain UVs and valid evaluated surfaces, and returning the control restores the original counts and dimensions. Final review images are `final-scene.png`, `depth-center.png`, and `depth-stairs.png`.
