# Reference lighting

The edited scene is `../platform-controls/cave-platform-sliders.blend`.
The original camera, modeled objects, surface materials, and platform controls are preserved.
A complete starting backup is `before-reference-lighting.blend`.

## Adjust the lighting in Blender

1. Select **LIGHTING CONTROLS** in the Outliner. It lives in **180 | Reference soft spotlight lighting**.
2. Open **Properties → Modifiers (wrench) → Reference Lighting**. The saved scene opens with this panel pinned.
3. Use **Numpad 0** in the 3D View for the camera, and **Z → Rendered** to see the lights. Use **F12** for a final camera render.

The sliders and light drivers are native Blender data. No add-on, custom Python panel, or automatic script execution is required.

### Main controls

- **Master brightness** scales all platform lighting together. Start with small changes, such as 0.8–1.2.
- **Center / Rear left / Front left / Upper right / Lower right platform** adjust one platform's complete lighting group. Each starts at 1.0; matching values preserve the calibrated balance, not identical wattage.
- **Spot edge softness** is the shared Spot Blend. The saved value is 0.92. Use 0.8–1.0 for the reference's feathered look; lower values make a harder cone edge.
- **Beam width** multiplies each platform's calibrated cone angle. 1.04 is the saved look. Increase slightly to spread a pool; decrease to focus it.
- **Shadow softness** scales the spot emitter radii. 1.0 is the saved look. Higher values soften shadows; this is separate from the cone edge.
- **Soft fill** controls the platform area lights and room bounce. The saved value is 1.08. Lower it for more contrast; raise it to show more floor and wall detail.
- **Cave ambience** adjusts the surrounding rock, bridge, railing, and support illumination separately from the spotlights. The saved value is 1.8. Try 1.4 for a darker cave or 2.2 for more environmental detail. This also controls the broad, symmetrical camera-side environment fills.
- **Haze density** controls the existing atmosphere volume. The saved value is 0.0045. Raise gently toward 0.006–0.008 for more visible shafts, or lower toward 0.002 for cleaner air. More haze also reduces contrast.
- **Beam visibility** controls additional soft local mist inside the light pools, without changing the lamps' surface power. The saved value is 0.9; try 0.5–1.5 first. This is the best first adjustment for a more or less pronounced soft spotlight look. The mist also follows Haze density, so setting Haze density to zero clears all atmosphere.
- **Warm accents** scales existing amber lamps. 0.5 keeps them small and subordinate to the cool lighting.
- **Cool light tint** changes the shared blue-white color of the platform lighting.

### Position or tune an individual light

Expand **180 | Reference soft spotlight lighting**. Every new light starts with **RL |**, followed by its platform and role.

- **soft overhead spot** creates the feathered light pool and atmospheric beam.
- **soft fill** creates broad, soft reflections on the metal floors.
- **wall bounce** makes the right-hand rooms readable.
- **stair spill** gently carries the rear-left light down the steps.
- **broad environment fill** softly illuminates the cave and connecting structures while preserving the brighter overhead pools.

Select a light and use **G** to move it or **R** to aim it; spotlights point along local **-Z**. The spot cones are enabled for visual aiming. Under **Object Properties → Custom Properties**, **Base power (W)** is an advanced brightness adjustment for that lamp. Keep matching `-1` and `+1` lamps at the same value to preserve symmetry. The shared brightness sliders multiply these base values.

Moving a **RL | … | move lighting group** parent moves that group's lights together. The upper- and lower-right group positions follow the existing ceiling-light fixtures, so use the existing fixture height controls for those rooms, or move an individual child light for a local offset.

Purple fields in Light Data Properties are driven by the shared sliders. Use **LIGHTING CONTROLS** to change them. For complete manual independence, right-click a purple field and choose **Delete Driver**, then edit it directly; doing so removes that field from the shared system.

The central reflection fills use light linking to illuminate the central deck, railings, and console without spilling onto the nearby cave or upper gallery. This is visible in **Object Properties → Shading → Light Linking**.

If another Properties panel appears stuck on the lighting controls, click its pin icon to unpin it before inspecting another object.

## What changed

The earlier broad lighting rigs are retained but disabled where they competed with the new lighting. All five platforms now use cool overhead spotlights with high edge blend and finite emitter radii, plus balanced area-light fill. The long front-left platform uses two identical overlapping spots along its centerline. Area-fill pairs are mirrored around their platform's local centerline. Powers and cone widths are calibrated for different ceiling heights and platform sizes. The existing cave haze was made lighter and more neutral blue; five softly faded local atmosphere volumes reveal the overhead cones, especially inside the low ceilings. These are volume-only lighting effects with no visible solid surfaces. Warm practicals were reduced.

No terrain, architecture, equipment, camera composition, or surface material roughness/base color was changed. Old lights remain in the file, and `previous-light-settings.json` records their starting values. Open the complete backup to return to the exact original lighting.

The environment revision adds two large, mirrored camera-side fill lights, raises cave bounce, feathers the spotlight edges further, and slightly reduces beam mist. This keeps the rest of the cave readable and blends the spotlit platforms into their surroundings. `before-environment-lift.blend` preserves the earlier, darker spotlight setup.

## Files

- `before.png`: original camera lighting.
- `final-camera.png`: final camera lighting.
- `verification.json`: independent saved-file checks, including preserved geometry/camera and working controls after reopening.
- `build_reference_lighting.py`, `refine_lighting.py`, `polish_lighting.py`, `finish_atmosphere.py`, `local_beam_mist.py`, `lift_environment.py`, `save_final.py`: the lighting construction and camera-review passes, applied in that order to the backup.
