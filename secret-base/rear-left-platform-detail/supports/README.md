# Cliff support beneath the rear-left platform junction

Added to the active `../../platform-controls/cave-platform-sliders.blend`. The live scene before this change is retained in `before-supports.blend`; the completed support version is also saved as `rear-left-supported.blend`.

`172 | Rear-left cliff support brackets` contains two I-beam cantilevers, horizontal bearing arms, cliff spines, splayed wings under the T landing, transverse braces, gussets, and bolted rock anchors. All 42 parts follow the existing landing through parenting. The braces connect to the real deck underside and the current evaluated cliff surface.

The original 2,650 object transforms and base meshes, including the terrain shape keys, were preserved. Main beams and side wings were checked for clear paths to the rock anchors, bearing shoes overlap the deck/stringers, and every added mesh is closed with no zero-area faces. Measurements are in `verification.json`.

`build_supports.py` reproduces the structure from the before snapshot. `render_supports.py` creates inspection images using temporary lighting and a local cliff cutaway, without saving those presentation changes.
