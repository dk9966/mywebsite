# Rear-left platform details

Saved in the active `../platform-controls/cave-platform-sliders.blend`, with a separate `rear-left-platform-detailed.blend` copy. `before-platform-details.blend` preserves the full live scene before this edit, including unsaved changes.

The new parts are in `170 | Rear-left connected platform`. The four original blockouts are retained in a hidden archive collection.

- Flat, 1.18 m wide open-grating bridge aligned radially to the middle platform; curved threshold at the existing 6.87118 m walking height.
- Connected upper platform, 18-step stair flight, and one-piece lower landing. The broad arrangement remains in its original place. The lower landing height now meets the level bridge.
- Diagonal shoulders at both T-junction corners, with continuous steel guardrails, underdeck framing, and restrained amber edge markers.
- Inset metal floor panels with narrow seams and side grating strips.
- Existing terrain raised around the sides and rear through the reversible `Rear-left | raised enclosing rock walls` shape key. Existing sculpt keys remain active. The upper deck boundary was fitted to remove rock crossings.

`verification.json` records a radial dot product of 1, no rock crossings at 7,749 near-floor samples, no guardrail fragments across the bridge entrance, and closed main deck, stair, and threshold meshes with no non-manifold edges or zero-area faces. 1,992 unrelated pre-existing object transforms and base meshes were unchanged during the build; only the relevant center guardrails received a reversible entrance cutter.

`build_details.py` rebuilds from the before snapshot and uses `final-rock-deltas.json` for the inspected final sculpt. `verify_geometry.py` repeats the clearance and topology checks. `render_inspection.py` makes inspection-only renders using temporary lighting and a roof cutaway, without saving those changes to the scene.
