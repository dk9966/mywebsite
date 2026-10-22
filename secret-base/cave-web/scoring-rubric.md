# Blender ↔ web comparison rubric

Two images of the same camera view, same size (1200 × 662):

- **Reference**: `reference/blender-camera.png`, the Cycles render of
  `platform-controls/cave-platform-sliders.blend` (compositor bloom + AgX).
- **Candidate**: the three.js page `/cave`, captured at the same camera.

Score each category from 0 to 10 for how closely the candidate matches the
reference. **Measure before asserting**: crop the same box from both images
and compare mean / 10th / 50th / 90th-percentile luminance and mean RGB (for
example with `node -e` and `sharp`, or Python + PIL). Do not report a
brightness or colour difference that you did not measure. Name the region,
the numbers, and the direction of each difference.

Deliberate differences that must **not** cost points:

1. The rear hole behind the central platform contains a Minecraft-style voxel
   room in the candidate (an intentional addition). Judge only whether it sits
   naturally in the scene (category 8). In the reference that hole is empty haze.
2. Fine noise or grain patterns differ (Cycles sampling vs baked textures).
3. Sub-pixel edge aliasing differences.

Categories:

1. **Framing & geometry**: same camera, objects in the same places and sizes.
2. **Global exposure & contrast**: overall brightness, black level, highlight roll-off.
3. **Colour & white balance**: the cool blue grade, warm accents.
4. **Cave rock lighting**: walls, roof, chasm and rock pillar brightness and gradients.
5. **Platform & metal surfaces**: decks, railings, stairs, rooms; reflections and sheen.
6. **Emissive fixtures & bloom**: amber lamps, white/cyan strips, holo table; halo size and strength.
7. **Atmosphere**: haze density, light-beam visibility, depth fade, mist under the decks.
8. **Voxel room integration**: placement in the hole, lighting consistent with the cave.

Return a table of the eight scores with a one-line measured justification each,
then up to five concrete, prioritised fixes (region, measured gap, suggested
direction).
