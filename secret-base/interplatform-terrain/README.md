# Connected terrain between the platforms

Working file: `../platform-controls/cave-platform-sliders.blend`.
Finished snapshot: `connected-natural-terrain.blend`.
Before-edit checkpoint, including the existing upper corner control:
`before-refinement-with-controls.blend`.

The existing cave surface is relaxed into a broader, irregular shoulder between
the upper platform and the lower workshop. The lower edge meets all four roof
sections. A small natural arch clears the circular light. Native Geometry Nodes
keep this fit responsive to the existing light height and radius controls.

The terrain evaluates to **48,378 triangles**, down from **72,208** (33.0% fewer).
The reduction is restricted to the local rock band, with the upper platform's
bearing surface protected. Shallow facets blend together while sharper rock
breaks retain their edges. Original sculpt keys and the upper corner driver remain
available, alongside the new reversible `Between platforms | natural connected
rock` key and two named simplification/shading modifiers. The original terrain
mesh and roof node group remain stored in the Blender file.

`verification.json` records one connected component, no loose edges or internal
nonmanifold junctions, no degenerate faces in the edited region, roof contact,
and zero light intrusions or unsupported upper-platform samples across four
height/radius combinations. `preservation-live.json` records unchanged geometry,
transforms, and visibility for all 2,691 pre-existing non-terrain objects. New
objects and controls added concurrently in the live scene are preserved.

`after.png` is a close-up render from a temporary inspection camera; the working
scene camera and render settings are unchanged. `refine_terrain.py` rebuilds the
edit from its retained source mesh. `verify_terrain.py` checks a saved snapshot.
