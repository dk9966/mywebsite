# Secret Base — Blender workflow

The scene has two layers:

- **Background** (cave shell, fog, dust, lights, bloom, camera): always
  procedural, lives in `components/scene/`. Not part of the Blender pipeline.
- **World** (all 7 islands, pillars, bridges, signs, props): rendered from
  `secret-base/models/world.glb` by default. This is the file you edit
  in Blender.

Routes:

| URL | What renders |
| --- | --- |
| `/secret-base/` | Baked `world.glb` (your Blender edits) |
| `/secret-base/?procedural` | Code-generated world (source for the GLB) |

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

Tip: in Blender 4.x, set this up once as a **Collection Exporter** on your
root collection (Properties → Collection → Exporters) so every Ctrl+S
re-exports automatically.

Then just reload `http://localhost:5174/secret-base/` — Vite serves the new
file immediately (hard-refresh if the old GLB is cached).

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
