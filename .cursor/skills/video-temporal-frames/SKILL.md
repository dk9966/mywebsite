---
name: video-temporal-frames
description: >-
  Extracts sparse, timestamped frames from a video clip and guides the agent
  through temporal reasoning to understand motion, animation, and camera work.
  Use when analyzing video clips, reproducing motion from reference footage,
  understanding animation timing, or when the user mentions video analysis,
  clip understanding, temporal reasoning, or animation from video.
---

# Video temporal frame extraction + reasoning

## Prerequisites

- **ffmpeg** on `PATH`
- **tsx** (dev dependency in this repo)

## 1. Extract frames (CLI)

```bash
pnpm exec tsx scripts/extract-video-frames.ts --input "path/to/clip.mov"
```

Options:

| Flag                | Default | Description                                      |
|---------------------|---------|--------------------------------------------------|
| `--input`           | —       | Path to video file (required)                    |
| `--fps`             | 4       | Frames per second (1–30)                         |
| `--mode`            | fps     | `fps` (fixed rate) or `scene` (keyframe detect)  |
| `--scene-threshold` | 0.03    | Scene change sensitivity for scene mode (0–1)    |
| `--scale`           | 640     | Output width in pixels, height auto-scaled       |

Output goes to a folder next to the input file, named after it (without extension).
Each frame is named `T00_0.00s.png`, `T01_0.25s.png`, etc.
A `_manifest.json` is written with structured metadata.

### Which mode to use

- **fps** — good default. Use 3–6 fps for most clips. Lower fps for slow/static scenes, higher for fast motion.
- **scene** — better for clips with distinct cuts, transitions, or long static holds. Avoids redundant frames.

## 2. Agent workflow (after extraction)

After running the script, follow these steps **in order**. Do not skip ahead to code generation.

### Step A — Read the manifest

Read `_manifest.json` in the output folder. Note the frame count, timestamps, and duration. This tells you what you are working with.

### Step B — Attach frames with the temporal contract

Read all frame images (using the Read tool on each `.png`). Before reasoning about them, establish this context:

```
These images are an ORDERED SEQUENCE OF FRAMES extracted from a short video clip.

Rules:
- Frames are temporally ordered. Timestamps are in each filename.
- Each frame represents a continuous motion trajectory.
- Assume linear interpolation between adjacent frames unless contradicted.
- Motion, deformation, camera movement, and timing are critical.
- Treat this as a video, not independent images.
```

### Step C — Frame-pair delta reasoning

For each adjacent frame pair (T_i to T_{i+1}), describe:

- **What moved** — direction, magnitude, which objects
- **Acceleration / easing** — constant velocity, ease-in, ease-out, snap
- **Invariants** — what stayed the same (background, color, composition)
- **Camera** — any pan, zoom, rotation, or cut

Do NOT summarize the clip as a whole yet. Build understanding bottom-up from deltas.

### Step D — Unified motion model

After all pairs are analyzed, synthesize into:

- **Objects** — distinct visual elements and their roles
- **State variables** — position, scale, opacity, color, rotation, etc.
- **Time functions** — how each variable changes over the clip duration (linear, eased, stepped)
- **Key transitions** — moments where behavior changes (apex, contact, settle)

Tag key moments explicitly, e.g.:
```
Frame T04 (1.00s) = apex of arc
Frame T07 (1.75s) = contact / impact
Frame T10 (2.50s) = settle to rest
```

### Step E — Code generation (only now)

With the motion model established, generate code targeting the requested framework (Three.js, GSAP, CSS, shaders, p5.js, etc.).

The code should reproduce the observed motion, not just the static appearance.

## 3. Handling longer clips (>20 frames)

If extraction produces more than ~20 frames:

1. Process in sliding windows of 8–12 frames with 2-frame overlap.
2. Complete steps B–D for each window.
3. After all windows, merge the per-window motion models with continuity constraints:
   ```
   Assume this window continues the same motion model from the previous window
   unless the delta analysis contradicts it.
   ```
4. Then proceed to step E with the merged model.

## Common pitfalls

- Do NOT dump frames at high fps (>10). It floods context and kills reasoning.
- Do NOT skip the delta reasoning step. Jumping straight to "describe this video" produces vague summaries.
- Do NOT treat frames as independent images. The temporal contract matters.
- Do NOT generate code before building the motion model.

## Examples

See [examples.md](examples.md).
