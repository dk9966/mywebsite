# Video temporal frames -- examples

## Fixed-rate extraction (default)

4 fps, 640px wide:

```bash
pnpm exec tsx scripts/extract-video-frames.ts \
  --input "plans/clips/06 - Futuristic Rider Transformation - Screen Recording 2026-04-07 at 3.47.39 PM.mov"
```

Output folder: `plans/clips/06 - Futuristic Rider Transformation - Screen Recording 2026-04-07 at 3.47.39 PM/`

## Scene-based extraction

For clips with distinct cuts or long holds where fixed fps would over-sample:

```bash
pnpm exec tsx scripts/extract-video-frames.ts \
  --input "plans/clips/07 - Futuristic Neon Arena Transition - Screen Recording 2026-04-07 at 3.57.58 PM.mov" \
  --mode scene \
  --scene-threshold 0.04
```

## Higher density for fast motion

```bash
pnpm exec tsx scripts/extract-video-frames.ts \
  --input "plans/clips/02 - Tron Lines - Screen Recording 2026-04-07 at 2.15.37 PM.mov" \
  --fps 6 \
  --scale 960
```

## Lower density for slow scenes

```bash
pnpm exec tsx scripts/extract-video-frames.ts \
  --input "plans/clips/03 - Young Man Pauses Movie - Screen Recording 2026-04-07 at 3.25.14 PM.mov" \
  --fps 2
```

## Agent workflow walkthrough

After extraction, the agent follows these steps (abbreviated):

**1. Read manifest:**
```json
{
  "source": "plans/clips/06 - Futuristic Rider Transformation.mov",
  "mode": "fps",
  "fps": 4,
  "scale": 640,
  "frameCount": 12,
  "durationSeconds": 2.75,
  "frames": [
    { "file": "T00_0.00s.png", "timestamp": 0 },
    { "file": "T01_0.25s.png", "timestamp": 0.25 },
    ...
  ]
}
```

**2. Attach all frame images with the temporal contract prompt.**

**3. Frame-pair deltas (example output):**
```
T00 (0.00s) -> T01 (0.25s):
  - Rider figure shifts +40px right, slight downward tilt
  - Neon glow intensifies on suit edges (blue -> bright cyan)
  - Background: static grid, no camera movement
  - Easing: appears to accelerate (ease-in)

T01 (0.25s) -> T02 (0.50s):
  - Rider continues rightward, velocity increasing
  - Light trail begins forming behind figure
  - Camera: subtle zoom-in (~2%)
  ...
```

**4. Motion model (example output):**
```
Objects:
  - rider: humanoid figure, neon-edged suit
  - trail: light streak behind rider
  - grid: static background plane

State variables:
  - rider.x: 0 -> 1 over 2.75s, ease-in-out
  - rider.rotation: 0deg -> -15deg, linear
  - trail.opacity: 0 -> 1 over first 0.5s, then hold
  - trail.length: 0 -> 200px, proportional to rider.x velocity

Key transitions:
  - T04 (1.00s): peak velocity, trail fully visible
  - T08 (2.00s): deceleration begins
  - T11 (2.75s): settle to rest
```

**5. Code generation** targeting the requested framework.
