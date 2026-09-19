# Irregular silhouette and modest lower widening

The new mound breaks the earlier cylinder/polygon outline with five different
asymmetric cross-sections, an offset crown and lower body, unequal shoulder
heights, and one broad setback above the lower right buttress. A 12% flare
factor at the foot fades toward the crown. The 36 shallow outcrops from the
accepted detailed version remain on a continuous rock body.

The generator still uses the original pillar generator's angular/height field
and exact step-wall mesher. Extrusions span neighboring columns rather than
forming independent ribs.

## Visual iteration

- Iteration 09 varied the cross-sections and widened the foot. Both independent
  critics rated its primary form 6.5/10: it remained too concentric.
- Iteration 10 offset the mass and staggered the shoulder heights. Grades rose
  to 7.8/10 and 7.3/10; one critic identified a remaining continuous taper.
- Iteration 11 adds a single broad right-side setback. Both critics selected
  this version and found no substantial remaining silhouette blocker.

Final image-based grades:

- Critic A: natural macroform 8.2/10, continuity 9/10, base flare 8.5/10.
- Critic B: natural macroform 8/10, continuity 8.8/10, base flare 8/10.

These are subjective visual assessments, separate from mesh validation.

## Deliverables

- `central-platform-rock-mound-organic.blend`
- `organic-hero.png`, `organic-context.png`
- `organic-rock-only.png`, `organic-reverse.png`
- `organic-audit.json`
- `build_organic_mound.py`

The Blender file contains platform close-up, full-layout and rock-only scenes.
The procedural source and original mesher are embedded. A hidden object keeps
the editable modifier stack; the displayed mesh has only sub-voxel processing
fragments removed. The final audit requires one connected component, no boundary
edges and no non-manifold edges. All previous versions and `base.blend` remain
preserved.

Rebuild from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python secret-base/mound-study/build_organic_mound.py -- --iteration 11 --final
```
