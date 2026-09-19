# More extrusions and detail

This pass preserves the accepted irregular footprint and connected body, then
adds 36 shallow overlapping outcrops. Each adds stone to the existing surface;
there are no new carved recesses. Unequal caps, endpoints and widths interrupt
the larger faces. Finer geometric chips and slightly stronger fracture shading
add detail at smaller scales.

Iteration 07 used 48 additions with stepped borders. Both critics flagged the
repeated frames as artificial. Iteration 08 replaces those with single broad
outcrops and is the delivered geometry.

Final independent reviews:

- Critic A: requested improvement 8.5/10, continuity 9/10.
- Critic B: requested improvement 8.7/10, continuity 9/10.
- Both accepted the revision with no substantial blocker. Optional polish was
  to interrupt a few aligned horizontal ledges on the lower front.

Deliverables:

- `central-platform-rock-mound-detailed.blend`
- `detailed-hero.png`, `detailed-rock-only.png`, `detailed-context.png`
- `detailed-audit.json`
- `build_detailed_mound.py`

The Blender file contains close-up, full-layout and rock-only scenes. The visible
mesh is cleaned of a microscopic detached processing fragment; a hidden source
object retains the editable modifier stack. Materials remain editable and the
generator is embedded. The earlier natural/connected versions and the source
`base.blend` are preserved.

Rebuild from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python secret-base/mound-study/build_detailed_mound.py -- --iteration 8 --final
```
