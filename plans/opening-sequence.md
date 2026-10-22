# Opening sequence plan

Date: 2026-10-04
Status: proposed; not implemented.

## Intent

The visitor first sees one window panel with intro text, framed so that it is the whole view. The camera then pulls back and the rest of the cave fades into view around it. When the move ends, the full scene is on screen and the visitor can navigate.

## Beats

| # | Beat | Approx. time | What the visitor sees |
|---|------|--------------|-----------------------|
| 0 | Hold | 0–0.6 s | Black. The panel glows faintly (fade-in). |
| 1 | Intro | 0.6–5 s | Only the window panel is visible and fills the frame, with the intro text. Everything else is black or heavily hazed. |
| 2 | Pull-back | after the intro text (a click or "continue" works as well as a timer) | The camera dollies back from the panel to the Blender scene camera. The ease is slow at the start and soft at the end. |
| 3 | Reveal | starts about 30% into the pull-back, runs about 2.5 s | The rest of the cave fades in, ordered by distance from the panel. |
| 4 | Handoff | at the end | The camera matches the manifest view exactly, `BlenderControls` turns on, the intro overlay is removed, and any normal UI appears. |

Total, excluding intro read time: about 4–5 s. Provide a Skip control (also Esc or click) that jumps straight to beat 4.

## Which panel

Decide which existing window panel opens the sequence. This is the first open question below. The sequence needs only the panel's world position and its outward normal, so the choice only changes two vectors.

## Implementation

Files involved: `secret-base/CaveApp.tsx`, `secret-base/components/cave/CaveScene.tsx` (camera rig and composer), `caveEffects.ts`, `caveFlags.ts`.

### 1. Sequence state

Add an `introPhase` state machine (`intro` → `pullback` → `done`) with a `progress` value from 0 to 1 for the pull-back. Keep it in a ref plus a tiny store, not React state, so frames do not re-render. Add `CAVE_FLAGS.skipIntro` for development, so URL hacking and `?intro=0` both bypass it.

### 2. Camera path

- Start pose: panel centre plus the normal times a distance chosen so the panel fills the viewport, looking at the panel centre.
- End pose: the manifest camera, exactly as `CameraFromBlender` sets it now.
- Interpolate position with a smooth ease. Interpolate orientation with a quaternion slerp. Interpolate FOV or lens if the start framing is tighter than the end. Do not interpolate `lookAt` targets directly, because that produces a swing.
- `LensShift` (the view offset) must ease from zero or a start value to the manifest shift, otherwise the framing jumps at the handoff.
- Keep `CaveControls` unmounted until `done` (it is already skipped when `CAVE_FLAGS.locked`).

### 3. Frame loop

The canvas uses `frameloop="demand"`. During the sequence, call `invalidate()` every frame, or switch to `always` until `done`, then return to `demand`. Check this carefully: it is the likeliest reason an animation would appear frozen.

### 4. Fade-in of the rest of the scene

Preferred approach: a reveal effect in the existing composer, driven by one uniform.

- Add a `RevealEffect` after the haze pass, before the view LUT. Input: world position (reconstructed from depth) or a screen-space radial mask centred on the panel.
- Uniform `uReveal` goes from 0 to 1. Pixels at distance `d` from the panel fade in when `uReveal * range > d`, with a soft edge. The result is a spread outward from the panel rather than a flat global fade.
- The panel itself is excluded from the mask, so it stays lit throughout.
- Alternative if that is awkward: one global opacity (multiply the colour by `uFade`) plus a haze density ramp. This is cheaper and likely good enough as a first pass.
- Ramp the lights and beams (`caveBeams.ts`, haze) up with the reveal so the amber light does not appear before the geometry does.

### 5. Intro panel text

- DOM overlay for the text, not 3D text, so it stays crisp and accessible: `aria-live` region, readable at any DPR.
- Alternatively draw the text onto the panel surface. That is better if the text should sit inside the scene, but it makes the pull-back sharper to read and harder to style. Start with the DOM overlay aligned to the panel's screen rectangle, projected each frame during beat 1.
- The overlay fades out as the camera leaves the panel (beat 2), so it never floats over the finished scene.
- Respect `prefers-reduced-motion`: show the panel, then crossfade straight to the final view without the dolly.

### 6. Loading

Do not start the timeline until assets are loaded (`loadCaveAssets`), the composer is built and the first frame has rendered. Otherwise the pull-back plays while textures pop in. Show the black hold in beat 0 until ready.

### 7. Performance

The full scene is heavy (55 lights, PCSS shadows, haze ray-march). While only the panel is in view, keep the shadow and haze passes on but consider skipping off-screen lights. Any change in cost at the handoff would show as a hitch. Check with the CDP-driven headless Chrome method already used for cave profiling; the Browser pane gives no rAF while hidden.

## Verification

1. Run with `?intro=1`. Confirm beats 0–4 in order and a clean handoff with no camera jump (compare the final matrix to the manifest camera).
2. Skip at each beat. The result must match the fully played end state.
3. Reduced-motion and a narrow (mobile) viewport: the panel must still fill the frame.
4. Profile the pull-back for dropped frames at dpr 1.5.
5. Reload several times. Confirm no pop-in and no flash of the full scene before the intro.

## Open questions

1. Which panel is the opening one?
2. Does the visitor advance by a click ("enter") or does the pull-back start on a timer?
3. Intro copy and typography (the station font picker already exists).
4. Should the sequence replay on every visit, or only the first (a session or localStorage flag)?
