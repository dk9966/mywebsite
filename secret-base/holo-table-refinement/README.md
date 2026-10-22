# Holographic table refinement

Updated the live table in `../platform-controls/cave-platform-sliders.blend`.

- Armor radius: 0.825 m → 1.2375 m (1.5×). Optical field and pedestal enlarged horizontally about the same center.
- Sixteen armor sectors have a rounded sloped upper shoulder and rounded tapered underside.
- Eight tilted dark control cassettes have beveled ivory and cyan keys, blue readouts, and red status indicators.
- Eight inward-facing projector strips and framed white fascia lamps follow the new rim.
- Follow-up: middle fascia height doubled from 0.065 m to 0.130 m; the top, controls, and optical assembly rise together. Radius stays 1.2375 m. `thicken_middle_band.py` and `middle-band-audit.json` record this edit; `before-middle-band-thickness.blend` is its backup.
- Original glass shading retained. No changes to the other 2,906 scene objects during the geometry pass.

`before-holo-table-refinement.blend` preserves the complete live scene before this edit, including unsaved work. Replaced original controls also remain in the hidden collection `175a | Original holo controls - hidden backup`.

`refine_holo_table.py` is embedded in the working blend. Run it only against the pre-edit scene; it guards against repeated scaling. `table-preview.blend` contains the refined collection for isolated review. `render_preview.py` generates `table-preview.png` and `rim-profile.png` from those actual meshes.

`audit.json` records dimensions and preservation checks. `clearance.json` records sampled scene-clearance checks; seven old wall objects produced no evaluated mesh and were skipped. The final table was also visually checked on its platform in the full scene.
