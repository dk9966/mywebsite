# Upright mound with a fuller upper section

The mound now follows a fixed vertical axis beneath the platform. The previous
sideways displacement, rotation drift, deep side setback and exaggerated
shoulder imbalance are removed. The upper support is fuller, blending smoothly
into the body; the restrained 12% lower flare is retained.

Eighteen shallow accents remain from the previous 36. Larger uninterrupted
faces alternate with more detailed regions. Two accent roots extend into the
underlying body, and geometric chips and fracture shading are quieter. This
combines the user's cleaner attached reference with the recent detailed rock.

The original pillar step-wall mesher still generates one filled surface whose
extrusions cross angular column divisions.

## Review

Two new fresh-context critics compared iteration 12 against the user's cleaner
reference and the previous detailed, leaning version. Their feedback prompted
iteration 13: another 6.5% smoothly blended upper widening and less isolated
relief roots.

Final image-based grades for iteration 13:

- Critic A: 8.6/10; no substantial blocker.
- Critic B: 9/10; no substantial blocker.

Both found the silhouette upright, the upper section fuller, and the mix of
clean faces and rock detail consistent with the current request. These are
subjective visual assessments, separate from mesh validation.

## Deliverables

- `central-platform-rock-mound-balanced.blend`
- `balanced-hero.png`, `balanced-context.png`
- `balanced-rock-only.png`, `balanced-reverse.png`
- `balanced-audit.json`
- `build_balanced_mound.py`

The new Blender file contains platform close-up, full-layout and rock-only
scenes. Materials and the modifier stack remain editable, and the generator
and original mesher are embedded. Final validation requires one connected
component, zero boundary edges and zero non-manifold edges. The original
`base.blend` and all previous variants are preserved.

Rebuild from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python secret-base/mound-study/build_balanced_mound.py -- --iteration 13 --final
```
