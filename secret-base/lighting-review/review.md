Station lighting review, 2026-09-11

Experience now uses the Project architectural rig fitted to its exported deck size and position. The rig includes rune and floor lights, broad shaft lighting, environment areas, and lights centered on the actual lantern bulbs. Ambient light is applied once. Desk, machinery, hub and holographic panels are not copied.

Blender source: `../match_station_lighting.py`; browser rig: `../components/scene/stationLights.tsx`. Final Blender render: `iteration-3.png`. Scene saved to `../base.blend` and exported to `../models/pillar.glb`. Pre-change scene snapshot: `before-lighting.blend`.

Independent reviewers compared the final render with the live 5174 browser:

- Lighting reviewer: structural parity 9/10; reference similarity 8.2/10.
- Visual reviewer: structural parity 9/10; reference similarity 8.1/10.

Iteration 1 was too saturated and dark (reference scores 6 and 6.8). Iteration 2 used paler emitter colors and stronger shaft lighting. Iteration 3 matched the browser's shadow-free broad lights and improved floor illumination. Remaining difference: Blender's lower shaft surfaces are somewhat darker than the browser.

Validation: dedicated station TypeScript check; live-browser visual inspection; three Blender renders. Whole-repository TypeScript check has unrelated existing errors in circuit/desk components.
