# Secret Base — Blender workflow

The scene has two layers:

- **Background** (cave shell, fog, dust, lights, bloom, camera): always
  procedural, lives in `components/scene/`. Not part of the Blender pipeline.
- **World** (all 7 islands, pillars, bridges, signs, props): rendered from
  `secret-base/models/world.glb` by default. This is the file you edit
  in Blender.
- **Station** (`/secret-base/?station`): the workshop pillar exported from
  `base.blend` as `secret-base/models/pillar.glb`, with live holographic
  screens parented onto `holoLocator_*` empties.

Routes:

| URL | What renders |
| --- | --- |
| `/secret-base/` | Baked `world.glb` (your Blender edits) |
| `/secret-base/?procedural` | Code-generated world (source for the GLB) |
| `/secret-base/?station` | Workshop pillar from `base.blend` + live holos |

## Live station preview

Run these in two terminals from the project root:

```sh
npm run dev
npm run watch:blender
```

Open `http://localhost:5174/secret-base/?station`, edit `secret-base/base.blend`
in Blender, and save. The watcher also exports once when it starts. After a
save settles for one second, a separate Blender process exports the pillar
and its descendants (including applied modifiers), then atomically replaces
`models/pillar.glb`. The page checks every 1.5 seconds and replaces only the
model, preserving the camera. Failed exports/loads keep the last good model.
Unsaved edits are not exported; save after running a `bpy` modeling script too.

The station now shows `island_pillar_project`, `island_pillar_experience`, and
`island_pillar_about`. Other pillars are hidden in the viewport and render.
Both side islands reuse the Experience deck, curved bridge, fixtures, and lights.
Their bridges angle behind Projects and run radially from its circular rim,
perpendicular to the tangent at each entrance. `radial_bridges.py` reapplies
this layout; `align_bridges_to_table.py` is the superseded table-edge layout.
Labels are web-only, centered above the live deck bounds by
`StationIslandHeadings.tsx`; no title geometry is stored in Blender.

The exporter includes all three hierarchies and their visible bridge geometry.
Website architectural lights follow each island's exported rotation and scale;
lantern lights use the actual exported bulb positions. The default station
camera frames all three islands. `base.before-three-islands.blend` preserves
the scene before this layout change.
Stop the watcher with Ctrl+C. If Vite was already running when this feature
was added, restart it once to enable the polling endpoint.

The default Blender executable is `/Applications/Blender.app/Contents/MacOS/Blender`
on macOS, or `blender` elsewhere. Override with `BLENDER_BIN` if needed.
An alternate station source can be passed as `npm run watch:blender -- path/to/file.blend`;
it must contain the same station hierarchy and still exports to `pillar.glb`.
The world page also refreshes automatically when `world.glb` is exported,
but this watcher only builds the station.

To re-export the station pillar manually from Blender:

```python
exec(open("/Users/danielku/mywebsite/secret-base/export_pillar.py").read())
```

## 1. Get the GLB into Blender

`secret-base/models/world.glb` is already generated. In Blender:
**File → Import → glTF 2.0** and pick that file. You'll get the full island
hierarchy with named objects (`projectsIsland`, `bridge`, `pillar`, …) and
named materials (`graphite`, `neonCyan`, `lampWarm`, …).

Save your working file as `secret-base/blender/world.blend` (source of truth;
the GLB is a build artifact).

## 2. Edit rules

- **Units are meters**, 1 unit = 1 three.js unit. Decks are ~5–11 units wide.
- **Keep material names.** The app swaps materials by name at load time
  (`BakedWorld.tsx` ↔ `MATERIALS` in `materials.ts`), so emissive strength,
  bloom, and theming stay code-controlled. In Blender the materials are just
  placeholders — assign the right *name*, don't worry about its look there.
  Unknown material names pass through untouched (that's how the baked
  sign/screen textures work).
- **Keep island group names** (`projectsIsland` etc.) if you want them to stay
  individually addressable for click interactions later.
- The Minecraft island uses GPU instancing — Blender may flatten it on
  re-export. If you don't need to edit it, keep it in a collection you leave
  alone.

## 3. Export from Blender back to the site

**File → Export → glTF 2.0**, and overwrite
`secret-base/models/world.glb` with these settings:

- Format: **glTF Binary (.glb)**
- Include: selected objects **off** (export everything), cameras/lights **off**
- Transform: **+Y up** (default)
- Mesh: **Apply Modifiers on**
- Material: export, images **auto**

With the development server running, the world page automatically picks up
the completed export. Production builds load the bundled model once.

## 4. Regenerating the GLB from code

If you change the procedural components (layouts, new props, etc.) and want a
fresh baseline GLB:

```sh
pnpm dev                          # dev server on :5174
npm run export-secret-base-world  # writes secret-base/models/world.glb
```

The script opens `/secret-base/?procedural` headlessly and exports the `world`
group via three.js GLTFExporter. You can also do it manually: open that URL,
and in the devtools console run `__exportWorld({ download: true })`.

⚠️ Regenerating overwrites Blender edits — the code is the source in that
direction. Pick per asset which side owns it, and fold important Blender
changes back into code (or keep them in `world.blend`) before regenerating.
