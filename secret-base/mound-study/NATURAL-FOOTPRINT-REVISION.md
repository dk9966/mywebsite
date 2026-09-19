# Less square footprint

This revision keeps the connected rock body from iteration 05 and changes its
footprint. The previous square projection is replaced by eight unequal angled
planes, clipping the dominant box corners. A small continuous lateral drift
breaks the straight outer walls without opening additional crevices.

The supported broad ledges, filled recesses, material and platform remain.
The previous connected version and source `base.blend` are preserved.

Two critics compared the previous and new renders against the user's request:

- Critic A: correction 8.5/10, retained solidity 9/10; no significant mismatch.
- Critic B: less square 8.5/10, retained solidity 9.2/10, correction fit 8.8/10;
  no substantial issue.

Deliverables:

- `central-platform-rock-mound-natural.blend`
- `natural-hero.png`, `natural-rock-only.png`, `natural-context.png`
- `natural-audit.json`
- `build_natural_mound.py`

The Blender file contains separate close-up, full-layout and rock-only scenes.
The generator and original pillar mesher are embedded as text blocks.

Rebuild from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python secret-base/mound-study/build_natural_mound.py -- --iteration 6 --final
```
