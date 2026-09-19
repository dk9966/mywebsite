# Central platform rock mound

The new mound reuses `mesh_field`, `Surface`, and the topology audit from
`meshes/pillars/island_pillar_src/shape.py`, the original pillar-side generator.
It replaces persistent rib/channel groups with overlapping regions on a
two-dimensional angular/height field. Extrusions span multiple angular columns;
the mound is one connected solid. The resulting field is shaped into unequal
stepped shoulders, with medium-scale fractures and restrained chipped surfaces.

`base.blend` is the input and is never saved over. Its initial SHA-256 is in
`source-sha256.txt`.

## Deliverables

- `central-platform-rock-mound.blend`: final scene, including the original layout
  with its central support replaced, a separate platform close-up scene, and a
  rock-only inspection scene. The generator and original mesher are embedded as
  text blocks. Modifiers remain editable.
- `final-hero.png`: close-up with the original platform and short bridge context.
- `final-context.png`: all original platforms with the new central mound.
- `final-rock-only.png` and `final-reverse.png`: unobstructed geometry views.
- `final-audit.json`: source and evaluated-mesh topology checks.
- `build_mound.py`: reproducible headless build and render script.

## Independent criticism

Two critics were spawned with fresh context, given the target reference and
candidate images, and asked to judge the mound rather than unrelated architecture.
Neither critic read the generator or edited the output. They regraded each pass.

- Iteration 01: overall 5.0/10 and 6.5/10. Too square, a constructed-looking foot
  and horizontal shelf bands, excessive cobblestone texture.
- Iteration 02: overall 6.5/10 and 7.3/10. Improved silhouette and dark material;
  broad faces still too monolithic, with stretched surface ripples.
- Iteration 03: overall 7.3/10 and 7.7/10. Connected rock and medium-scale fractures
  improved; thin shelf projections and excessive erosion remained.
- Iteration 04, final geometry: overall 7.8/10 and 8.1/10. Both critics found no
  major geometry blocker. Unequal shoulders, thicker projections, recessed
  corners and reduced displacement improved the reference match.

Final critic A: silhouette 7.8, cross-column continuity 8.0, rock plausibility 7.5.
Final critic B: silhouette 8.2, stepped geology 8.1, connectedness 8.3.

Both noted the broad lower-left face could benefit from one additional restrained
fracture as optional polish. The final is a reference-inspired geometry study,
not an exact reconstruction of the entire cavern scene.

## Validation

The evaluated mesh, including all modifiers, has 61,267 vertices and 122,530
triangles. It has exactly one connected component, zero boundary edges, and zero
non-manifold edges. The underlying procedural field also passes its closed-mesh
audit. The source `base.blend` SHA-256 was checked after the final build and is
unchanged.

## Rebuild

From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python secret-base/mound-study/build_mound.py -- --iteration 4 --final
```

Historical `generator-01.py` through `generator-04.py`, `.blend` snapshots and
renders preserve the actual iterations. The final uses Cycles with 88 samples,
denoising, and packed assets. No Blender UI or website export is required.
