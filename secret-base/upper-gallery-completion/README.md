# Upper gallery roof and support completion

The active scene is `../platform-controls/cave-platform-sliders.blend`.
`before-completion.blend` preserves the complete live scene, including unsaved sculpting,
before this work. `completed-gallery.blend` contains the completed gallery.

The roof is a closed, continuous steel shell from the four wall crowns to the
light housing, with matching panel joints and capped ends. The light is now
3.70 m long; its 2.25 m depth and 2.25 m mounting height are retained. The roof
and light respond to the existing native Upper Platform Sliders.

Support numbering runs from left to right in the user's reference:

- 1 and 2 follow the first/rear wall.
- 3 and 4 follow the second/diagonal wall.
- 5 follows the third/side wall.
- 6 and 7 follow the fourth/diagonal wall.

All seven channels are 220 mm wide with a 104 mm recess. All footplates are
360 × 460 × 58 mm. Each foot includes the same seated socket, fasteners, lamp
housing, recessed gasket, and amber lens. The parts physically overlap through
the socket-to-lens chain; no locator lights float above the feet.

`complete_gallery.py` builds the geometry from the live scene. Existing meshes
are retained as datablocks, and the full checkpoint provides a direct rollback.
`verify_gallery.py` checks the 94 evaluated meshes for closed topology and
nonzero faces, all seven wall directions, equal footplate dimensions and channel
gaps, the connected lamp assemblies, and four native slider configurations.
Unrelated object and terrain geometry was preserved (2,793 objects checked).
Results are recorded in `build-report.json` and `verification.json`.

`render_gallery.py` renders the gallery and a support detail in a background
process. Its inspection camera and broad fill light are never saved to the scene.
