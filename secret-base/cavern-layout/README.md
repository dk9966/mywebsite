# Cavern layout with the approved terrain

## Latest revision: recessed About Me bay

**`cavern-recessed-about.blend`** removes the entire Workshop station and its rear walkway. About Me is now an excavated alcove in the approved rock terrain, with a wider tiled forecourt, inset service walls, and rock overhead instead of a separate metal roof. The scene remains dry, with no car or water.

The straight About bridge leaves the front-right of the central island. Its ramp levels before reaching the bay, and its two guardrails join the receiving perimeter at separate, exact intersections. Slightly raised overlapping paving prevents coplanar floor artifacts. The central railing opening is relocated; 1,913 protected center and left-station objects retain their original geometry, transforms, and shader input values.

The actual original table assembly remains the basis of the table. Its control annulus slopes more steeply, while a hollow optical chamber, blue transparent shader, and faint submerged rings replace the bright reflective center. The dark alloy rim and restrained blue keys keep the table readable without a white glare hotspot.

- `recessed-overview.png`: complete scene, 2000 px wide.
- `recessed-about-bay.png`: recessed station and fitted landing, 1400 px square.
- `recessed-table-closeup.png`: sloped rim and blue optical center, 1400 px square.
- `recessed-audit.json`: removal, placement, route, gate-clearance, and rock-clearance results.
- `recessed-preservation.json`: independent comparison after reopening the saved output.
- `recessed-review.json`: two fresh-context visual critics and the resulting refinements.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/build_recessed_about.py -- --final --samples 96 --width 2000
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/build_recessed_about.py -- --verify
```

The source is `cavern-original-holo-table.blend`. The generator reuses the paving and walkway helpers in `harmonize_islands.py`, embeds its source in the output, and packs external resources. The two current reference images are `../../design-references/misty-abyss/recessed-about-bay-reference.png` and `../../design-references/misty-abyss/blue-translucent-holo-reference.png`.

## Previous revision: original hologram table

**`cavern-original-holo-table.blend`** restores the actual `about_holo_table` assembly from `../base.blend` in the About Me station. All 143 original mesh components, shader values, beveled edges, rim controls, and concentric display rings are imported intact. A uniform scale of approximately 1.354 fits the existing table footprint; its pedestal sits on the current platform floor.

The other islands, connected bridges, satin platform finishes, lighting, and dry terrain are retained. The original table's own materials are preserved rather than restyled.

- `holo-overview.png`: complete scene, 2000 px wide.
- `holo-workshop-about.png`: right-side stations, 1400 px square.
- `holo-table-closeup.png`: detailed original table, 1400 px square.
- `holo-audit.json`: source, scale, placement, and replaced objects.
- `holo-preservation.json`: saved-file comparison of imported source components and the surrounding scene.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/restore_original_holo.py -- --final --samples 96 --width 2000
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/restore_original_holo.py -- --verify
```

## Dry cavern with satin platforms

**`cavern-satin-lighting.blend`** adds a restrained satin finish and cool overhead reflections to the matched scene. Geometry, bridge connections, cameras, and terrain are retained. The center's platform finish is intentionally updated along with the others; its geometry and rock shaders remain unchanged. No water, waterfalls, or wet-rock materials are added.

- `satin-overview.png`: full scene, 2000 px wide.
- `satin-contact-experiences.png` and `satin-workshop-about.png`: detailed views, 1400 px square.
- `satin-audit.json`: material settings and light additions.
- `satin-preservation.json`: independent saved-file geometry, transform, and rock-shader comparison.
- `satin-review.json`: independent visual feedback and refinements.

Platform roughness is 0.42, with modest metallic response and a light clear coat. Roofs retain a matte powdercoat finish to keep attention on the platform surfaces. Cool reflected light, darker frontal fill, lighter haze, and a localized warm workshop take inspiration from `../../design-references/misty-abyss/dry-cavern-satin-lighting-reference.png`.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/refine_satin_lighting.py -- --final --pass 3 --samples 96 --width 2000
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/refine_satin_lighting.py -- --verify
```

## Matching islands and fitted bridges

**`cavern-matched-islands.blend`** is the input to the satin revision. The preceding `cavern-approved-terrain.blend` is retained as its reproducible input.

- `matched-overview.png`: complete revised scene, 2000 px wide.
- `matched-contact-experiences.png` and `matched-workshop-about.png`: detailed views, 1400 px square.
- `matched-audit.json`: shared materials, protected-center fingerprints, route endpoints, and entrance clearance checks.
- `cavern-matched-islands-preservation.json`: independent saved-file verification against the approved center.
- `matched-review.json`: the two independent visual critics' assessments.

The outer islands now use the center's exact slate, graphite, wood, and equipment material datablocks. Smaller staggered paving suits the rectangular terraces; About Me inherits the center's concentric floor mesh. Two thin timber rails, matching posts, restrained screen markings, and continuous skirts carry the center's style across the scene. The middle island, its contents, and its terrain remain unchanged.

Rebuilt bridges depart along the actual openings in the protected center railings and meet the receiving floors at their exact heights. Flat landing sections overlap the deck by 0.16 units. Receiving rails have deliberate openings and joined ends. The Experiences entrance is separated from its internal stairs. Workshop has an actual side doorway cut through its enclosure; nearby shelves and the Contact cabinet leave the walking paths clear.

Regenerate this revision after the original layout exists:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/harmonize_islands.py -- --final --pass 5 --samples 96 --width 2000
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/verify_preserved_center.py -- /Users/danielku/mywebsite/secret-base/cavern-layout/cavern-matched-islands.blend
```

The generator asserts center mesh preservation, rays through all three existing center railing openings, exact arrival heights, and body-clearance rays against the outer stations' evaluated prop and wall meshes. The independent saved-file verification additionally checks full material node graphs and modifier settings. These geometric checks complement inspection of all three rendered views.

## Original reference-layout version

`cavern-approved-terrain.blend` is a separate scene built around the unchanged center island from `../mound-study/central-platform-rock-mound-balanced.blend`.

## Deliverables

- `final-overview.png`: reference composition, 2000 px wide.
- `final-contact-experiences.png`: Contact antenna/dish and the two-tier Education/Work gallery.
- `final-workshop-about.png`: warm workshop, About Me laboratory, and exit stair.
- `final-audit.json`: source paths, object fingerprints, placement values, and bridge paths.
- `cavern-approved-terrain-preservation.json`: independent saved-file comparison of the center against the approved source.

The active scene is **Cavern | approved island and reference composition**. The protected central assembly, new bridges, approved-rock instances, lighting, cameras, and four surrounding stations have separate collections. Three presentation cameras are included. The prior source scenes remain available in the file.

## Design

The concept image guides station placement, outer deck shapes, props, paths, and lighting. Contact occupies the upper left; the Education/Work gallery occupies the lower left; the workshop occupies the upper right; About Me occupies the lower right. The center retains its existing desk, server equipment, flooring, rails, and rock geometry.

The outer foundations and cavern enclosure reuse the evaluated approved rock surface and material, with varied placement, scale, and rotation. They do not use the concept's individual block-column terrain. Surrounding architecture and props are reused from `../../reference-cavern/cavern-portfolio.blend`, repositioned and relit. The old source terrain is excluded.

The lighting combines cool localized ceiling pools and haze with a warm workshop task area, cyan equipment, and small walkway markers. Larger height changes use stairs; connecting ramps use continuous sloped decking. Seven passes refined the composition. Two independent fresh-context critics reviewed the composition and lighting; their feedback drove the clearance, lighting, bridge, and reflection revisions.

## Regenerate headlessly

Run from the repository root with Blender 5.1:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/build_reference_layout.py -- --final --pass 7 --samples 96 --width 2000
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/cavern-layout/verify_preserved_center.py
```

The generator embeds its source in the output blend and packs external resources. Original input files are opened read-only and never saved over. The independent check compares all 17 protected mesh objects' world transforms, vertex positions, topology, face material assignments, material node graphs/inputs, and modifier settings.
