# Upper-left stair platform rock support

Saved in the active scene, `../platform-controls/cave-platform-sliders.blend`.
The existing continuous cave wall is pulled inward beneath the rear-left upper
platform, broad stair flight, and lower landing. A wide, faceted rock shoulder
tapers into the lower cliff, following the support mass in the supplied v4 image.

The `Upper-left | broad inward rock support` shape key controls the sculpt.
Set it to zero to restore the previous shape; `before-upper-left-support.blend`
also preserves the full live scene before this edit. The original cave mesh is
retained as a separate datablock. Local subdivision and contour rows keep the
thin bearing surfaces fitted to the platform undersides.

Verification sampled 713 points beneath each of the three sections; all points
have supporting rock within 5.5 cm of the underside. No new walking-surface
intrusions were found. The cave remains one connected mesh with no loose edges,
nonmanifold junctions, or zero-area faces. All 1,996 unrelated objects retain
their geometry and transforms. Camera, lighting, and background were preserved.

`before-clay.png` and `after-clay.png` show the edit from the unchanged scene
camera with temporary inspection shading. The inspection settings are not saved.
`sculpt_support.py` reproduces the change from the backup, and
`verify_support.py` writes the geometric checks to `verification.json`.
