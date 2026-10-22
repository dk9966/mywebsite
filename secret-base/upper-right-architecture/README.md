# Upper gallery light and wall architecture

Live scene: `../platform-controls/cave-platform-sliders.blend`.
Rollback checkpoint: `before-architecture.blend`.
Finished snapshot: `architecture-candidate.blend`.

In **UPPER PLATFORM SLIDERS → Modifiers → Upper Platform Sliders**, use:

- **Upper light width (m)**: 2.4–4.5 m, initially 3.70 m.
- **Upper light depth (m)**: 1.4–3.1 m, initially 2.25 m.
- **Upper light height (m)**: 1.8–2.8 m above the upper platform, initially 2.25 m.
- **Upper light corner bevel (m)**: 0.30–0.65 m, initially 0.60 m.

The fixture has a clipped rectangular housing, dark recessed center,
segmented cool-white perimeter diffusers, a matching rectangular area light,
and two arms connecting it to the wall crowns. All follow the controls.

Seven bent channel ribs support six wall bays along the terrain-backed right
edge, right corners and the rear edge as far as local x = -1.25 m. Closed
steel panel courses fill the bays, including their angled upper portions.
The front, left, and open rear section retain matching slender railings.
The prior all-edge railings remain in a disabled archive collection.

Wall panels, ribs, and exposed rails follow **Upper corner bevel (m)**.
The user's existing 0.10 m platform-bevel setting was preserved.
The fixture bevel is independent of the platform bevel.

The small ceiling-clearance modifier runs after the terrain's existing
topology modifiers. It raises only the local headroom and makes a shallow
outward pocket behind the front-right wall return. The platform's supporting
rock and other platform controls remain intact. All controls use native
nodes and expression drivers; no Python autorun is required.

`verification.json` checks eight size/height/platform-bevel combinations,
actual fixture and area-light dimensions, ceiling clearance and driver
validity. All new meshes have closed manifold edges. `gallery-in-scene.png`
uses the existing camera and scene lighting; `gallery-detail.png` uses a
temporary inspection camera. Preview settings are never saved into the scene.

Construction order against the checkpoint: `build_architecture.py`,
`fit_ceiling.py`, then `finish_and_verify.py`. The initial shape-based ceiling
adjustment is superseded by the modifier in `fit_ceiling.py` so later shared
terrain mesh replacements retain the clearance behavior.

Performance fix: run `slider-performance/isolate_upper_controls.py` once after
construction. It moves the five upper-platform controls to a separate native
controller and retargets 425 drivers. Sharing the original controller caused
upper-light edits to invalidate unrelated bridge and railing booleans (one
grating boolean took about 5.9 seconds). Measured dependency updates dropped
from about 5.6 seconds to 0.11–0.13 seconds. All 2,376 existing rendered mesh
signatures and the user's current values were identical after the change.
The existing cave modifiers, lighting, and geometry are retained.
