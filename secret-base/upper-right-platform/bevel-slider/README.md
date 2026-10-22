# Upper platform corner slider

Open **SCENE SLIDERS → Modifiers (wrench) → Scene Sliders → Upper corner bevel (m)**.
The live file is `../../platform-controls/cave-platform-sliders.blend`.

- Original value: **0.30 m**. Try **0.80 m** for visibly longer corners.
- Range: **0.10–1.50 m**.
- This is the cutback along each square edge; the diagonal corner length is
  the value multiplied by √2.

The slab, floor perimeter, railing, rim, edge lamps, drains and rock bearing
follow through native shape keys and expression drivers. The inner floor
markings stay square. No startup script or Python autorun is needed.

`before-slider.blend` is the rollback checkpoint. `with-bevel-slider.blend`
is the saved scene with the control. `verification.json` checks four values
across the range: exact corner geometry, floor/rail containment, rock contact,
walking clearance and valid drivers. All checks pass; sampled rock contacts
remain within 13 mm of the underside.
