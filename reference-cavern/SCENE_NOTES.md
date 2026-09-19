# Reference cavern portfolio

Built from an empty Blender file. The supplied `reference.png` is the comparison target. All visible environment geometry is constructed in 3D; no reference-image planes or camera-projected backdrops are used.

## Reference analysis and initial scale plan

- Camera: elevated, nearly frontal view, with weak perspective and visible deck tops. A 23° elevated orthographic comparison camera approximates the concept's compressed perspective; 44.5 m horizontal frame. A 47 mm lens value is retained for perspective exploration. Exact original focal length cannot be recovered from a single concept image.
- Visual hierarchy: central Projects disc and blue monitor array; white Contact mast at upper left; warm Workshop at upper right; circular blue About Me table at lower right; two stepped Experiences galleries at lower left.
- Foreground: dark framing cliffs, Experiences fascia and support trusses, descending right-hand exit, water and isolated rock pinnacles.
- Midground: Projects at 7.3 m elevation, 10.7 m diameter; Experiences at 4.85 / 6.05 m; About Me at 6.9 m, 11.1 m diameter. These provide the primary scale relationships.
- Upper/back tier: Contact at 10.65 m, Workshop at 12.3 m, Minecraft at about 9.6 m. Contact supports the 6.85 m white communications tower and a 2.4 m concave dish.
- Connections: Projects branches to Experiences, Contact through two stair flights and a turn landing, and About Me. A rear route runs from Contact to the Minecraft shrine and Workshop. About Me has a descending foreground exit.
- Cavern silhouettes: fluted fractured walls, overhanging ceiling teeth, side buttresses, island foundations and layered blue distant ridges. The center is kept open to show vertical depth.
- Architectural modules: deck tiles, deep edge beams, radial skirt ribs, triangular support braces, bolted fittings, tubular guardrails, stair treads, cabinets and portal frames.
- Light families: broad blue daylight reflected through the chasm, cyan screens and table, white laboratory strips, amber edge lamps and warm workshop task lighting.
- Material families: faceted basalt, titanium deck panels, graphite steel, brushed aluminium, white ceramic antenna housings, emissive display glass, water, tan storage boxes, blocky moss and masonry.
- Secondary details: milestone terminals, tool-board instruments, drawer banks, parts shelving, robot arm, engine trolley, overhead cables, screen graphs, crate straps and safety markings.

## Original construction review (historical)

The original constructed file contained all six areas, both Experiences subsections, modeled communications antenna and concave dish, curved Projects workstation, circular display table, furnished Workshop, Minecraft shrine, connecting circulation, cavern geology and water. The camera transform and 44.5 m horizontal frame stayed unchanged across all eleven original construction comparison renders.

The final elevations are Projects 7.65 m, Education 6.35 m, Work 4.85 m, Contact 11.35 m, About Me 7.7 m, Workshop 11.45 m and Minecraft about 9.6 m. Projects is 11.56 m across; the About Me terrace spans about 12.54 m across its long axis. Water is at 0.9 m. Rotated side terraces and relocated hub positions are recorded in navigation empties and the runtime manifest.

Independent review improved from about 4.5/10 overall in pass 01 to about 6.5–7.5/10 in later passes. Further changes produced mixed or negligible gains. The requested 8/10 in every category was **not achieved**. Remaining differences are primarily the cavern's authored silhouette and material richness, exact apparent deck proportions, and the reference's more nuanced light distribution. Review reports are retained; no missing critic score is invented.

The last construction QA corrections completed floors beneath the rear alcoves, rounded terrace corners with matching guardrails, improved the display-table glow, and added named navigation anchors. `renders/qa-oblique.png` verifies another 3D viewpoint; it is not a reference-comparison image.

## Files and iteration

- `build_scene.py`: deterministic geometry builder and initial renderer.
- `cavern-portfolio.blend`: latest saved working scene.
- `checkpoint-XX.blend`: staged saved versions.
- `renders/pass-XX.png`: comparison renders.
- `reviews/`: independent visual evaluations.
- `scene-stats.json`: geometry and camera counts from the builder.
- `cavern-portfolio.glb`: runtime export with unique geometry batched by area and repeated meshes instanced.
- `runtime-manifest.json`: final counts, camera data and navigation anchors.
- `finalize.py`: pack assets and generate the runtime export without flattening the editable working scene.
- `verify_scene.py`: non-destructive oblique render check.

## Real-time design

Repeated manufactured components share mesh datablocks. Geometry uses low-segment cylinders and single-step bevels. Cavern surfaces and water use finite meshes; procedural bump is subtle and can be baked or replaced in Three.js. Emissive materials are separate from illumination lights, allowing the runtime to use a smaller active-light set. The comparison render's Cycles lighting and bloom are presentation features that require a corresponding runtime lighting setup.

Named collections separate the main areas, geology, water, circulation, hero assemblies, secondary props and camera. Text labels remain editable in the working file. The supplied GLB converts curves and text to meshes, batches unique geometry by area, and uses EXT_mesh_gpu_instancing for repeated modules. Render-time shader noise and the volume are not directly portable to glTF; the GLB uses the practical PBR material values and modeled water surface. Recreate blue fog, selected local lights, water-normal animation and restrained bloom in Three.js. The reference image and fonts are packed into the .blend; the reference is disabled as a camera overlay and is not rendered as geometry.

## Runtime loading and limits

The final GLB uses Draco geometry compression and EXT_mesh_gpu_instancing. Configure Three.js GLTFLoader with DRACOLoader; the standard loader supports the instancing extension. Navigation empties are exported as named `NAV | …` nodes. Instance group extras retain source object names for mapping instance IDs back to components.

The GLB is an asset handoff, not a completed website or a measured browser performance guarantee. Its Cycles look requires runtime lighting, fog and postprocessing work. Use the exported glTF camera for the comparison framing; manifest camera and anchor coordinates are explicitly Blender Z-up.

## Scoped atmosphere and geology revision (in progress)

The second supplied target is `atmosphere-review/target-atmosphere.png`. Its content and layout are deliberately not reconstruction requirements. The current revision preserves the original comparison camera, island anchors, circulation, architecture and hero assets, and changes only lighting, geological forms, material response, water and atmospheric depth.

The builder asserts unchanged architecture transforms, camera matrix and serialized area anchors before each save. `refine_atmosphere.py` starts from `atmosphere-review/before-atmosphere.blend`, a preserved copy of the constructed scene. Supporting scripts apply CC0 scanned surfaces, create connected geological masses and bake deck seam wear. Every pass is saved as a separate `.blend` and comparison PNG before the next revision.

From scoped pass 16 onward, each comparison is reviewed by three new fresh-context critics given only the atmosphere target, the current render and the scoped rubric. `atmosphere-review/critics-XX.md` records those independent scores. Pass 23 did not meet the requested threshold; subsequent revisions remain in progress. Original construction scores above are historical and do not describe the latest scoped appearance.

Rock and metal source authors, asset URLs and CC0 licensing are recorded in `textures/SOURCES.md`. Image textures, explicit UVs and the modeled geological forms are portable. Cycles light linking, procedural water normals and spatial volumes require baking or corresponding runtime implementation. `atmosphere-runtime.json` records light transforms, reference energies and receiver groups; these energies are not calibrated Three.js values.

The older exported GLB and runtime counts are pending regeneration after the scoped visual review. The editable `.blend` is saved regularly and is the current source of truth.
