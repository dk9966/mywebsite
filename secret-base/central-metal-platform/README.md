# Isolated central pillar with a metal platform

`central-metal-platform.blend` contains one scene: the approved central rock pillar, its original console, and a new industrial metal platform. All surrounding islands, cavern walls, bridges, and bridge stubs are removed from this file.

The deck replaces the brick tiles with a four-part center plate, concentric machined rings, eight recessed open steel grates, alternating broad diagonal plates and narrow cardinal supports, and a deeper steel skirt. A continuous steel railing closes the former bridge openings. Eight inset amber lamps create small warm reflections on the satin gunmetal walkway.

The rock and seven console mesh objects retain their original geometry, transforms, and shader inputs from `../mound-study/central-platform-rock-mound-balanced.blend`. Presentation lighting is new. The source file is retained separately.

- `metal-hero.png`: complete pillar, 1500 × 1740.
- `metal-deck.png`: platform and console detail, 1800 × 1400.
- `metal-audit.json`: retained-object fingerprints and generated deck details.
- `preservation.json`: independent saved-file check of the eight original meshes and single-scene isolation.
- `review.json`: two fresh-context visual critiques and the resulting refinements.

The metal-platform reference is `../../design-references/misty-abyss/central-metal-platform-reference.png`. Preview files are ignored by Git. The generator source is embedded in the final Blender file.

Run from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/central-metal-platform/build_metal_platform.py -- --final --samples 96
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/central-metal-platform/build_metal_platform.py -- --verify
```
