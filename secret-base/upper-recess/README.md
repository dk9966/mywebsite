# Clean upper cave recess

Open **`upper-recess.blend`** for this revision. This is a separate scene file; an already-open older Blender scene will not refresh automatically.

The upper right bay is rebuilt as a coherent three-dimensional alcove, shifted 1.13 units right and 0.77 units back from the old balcony center and turned toward the chamber. It contains a seated steel platform, guardrails with connected side returns, a continuous mitered entrance frame, and one overhead light. The old tower, cabinets, gantry, extra lamps, and loose arch segments are removed.

The old upper excavation was projected from a single camera. The generator restores the original pillar-derived terrain above the upper bay's base, then cuts a single polygonal recess in its own coordinate frame. The new reveal is an inward-facing surface. Original rock and material geometry below that level, the middle island, lower platform, bridge, supports, and the surrounding interior wall are preserved.

## Renders

- `upper-recess-overview.png` — full scene, original overview camera
- `upper-recess-front.png` — front inspection
- `upper-recess-left.png` — left oblique inspection
- `upper-recess-right.png` — close right oblique inspection

## Rebuild

The script uses `preview-source.blend`, a snapshot of the accepted connected-cavern scene, so later changes in other scene files do not silently alter this result. `preview-original-upper-rock.blend` is an optional geometry cache; if absent it is regenerated from the original pillar mesh and original wall shaping code.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/upper-recess/build_upper_recess.py -- --final
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python secret-base/upper-recess/verify_upper_recess.py
```

`verification.json` records saved-file checks for preservation, clear standing space, a single closed entrance frame, physical railing connections, and absence of upper props. This revision adds no vehicles, water, cave ceiling, or floor.
