# HUD Clip Recreation Playbook (Three.js)

A deterministic pipeline for recreating short (<5s) HUD animation clips in Three.js.
Written for future agents. Follow it top-to-bottom. Stop at the checkpoints.

---

## Why this exists

"Recreate this HUD clip" almost always fails when you jump straight from `.mov` to
Three.js code. HUDs look improvised but aren't — they are a small vocabulary of
shapes, a small set of reusable motions, and an explicit timeline. If you guess all
three at once from a video, you end up with something that vaguely gestures at the
reference instead of matching it.

This playbook forces each layer to be written down as its own artifact, reviewed,
and only then rendered. The result is that recreation becomes mechanical: given
the same artifacts, any agent/run should produce the same scene.

---

## Assumptions

- Input clip is short: **≤ 5 seconds**, single coherent HUD moment (one reticle
  lock, one readout resolve, one ring build, etc.). Long clips should be split
  upstream before invoking this playbook.
- Target stack is the one in `plans/project-structure.md`: Three.js + R3F + drei
  + GSAP. Ortho camera for 2D HUDs unless the clip explicitly parallaxes.
- Tooling already present in this repo:
  - `scripts/extract-video-frames.ts` (ffmpeg wrapper)
  - `.cursor/skills/video-temporal-frames/SKILL.md`
- Package manager is **pnpm**.

---

## The seven stages

Each stage produces one artifact. Do not skip ahead. After stages 2, 3, and 4,
**stop and request human review** before continuing — those three are
interpretation-heavy and every downstream stage depends on them.

```
1. extract   → frames + manifest
2. inventory → elements.ts            [CHECKPOINT]
3. grammar   → behaviors.ts           [CHECKPOINT]
4. timeline  → timeline.ts            [CHECKPOINT]
5. primitives→ mapping notes
6. implement → one element at a time, in a scrubbable harness
7. diff      → record + compare frame-by-frame
```

---

## Folder layout (per clip)

Given an input file:

```
plans/clips/<clip-name>.mov
```

After stage 1 the extractor creates:

```
plans/clips/<clip-name>/
├── T00_0.00s.png
├── T01_0.25s.png
├── …
└── _manifest.json
```

All subsequent artifacts live in the same folder, so one clip = one directory:

```
plans/clips/<clip-name>/
├── T00_0.00s.png … _manifest.json   (stage 1)
├── elements.ts                       (stage 2)
├── behaviors.ts                      (stage 3)
├── timeline.ts                       (stage 4)
├── primitives.md                     (stage 5)
├── scene.tsx                         (stage 6, R3F)
└── diff/                             (stage 7)
    ├── recording.mov
    ├── T00_0.00s.png … (our frames)
    └── compare.html
```

---

## Stage 1 — Extract frames

Use the existing skill. Pick `scene` mode for HUDs — fixed fps floods context
with near-duplicate frames during long holds.

```bash
pnpm exec tsx scripts/extract-video-frames.ts \
  --input "plans/clips/<clip-name>.mov" \
  --mode scene \
  --scene-threshold 0.05 \
  --scale 640
```

Raise `--scene-threshold` (toward 0.1) if the clip has camera noise/grain causing
false scene hits. Drop it (toward 0.02) if a real state change is being missed.

For a 5s clip you want **8–16 frames**. If `scene` mode produces more, re-run
with higher threshold. If it produces fewer than 6, fall back to `--mode fps
--fps 4`.

Read `_manifest.json` after extraction. Note the duration and the timestamp of
every frame — all later artifacts reference these exact timestamps.

## Stage 2 — Element inventory  `[CHECKPOINT]`

Pick **one** representative frame — the most information-dense one, usually
mid-clip. Look at only that frame. List every distinct visual thing on screen.
Write them as data in `elements.ts`:

```ts
// plans/clips/<clip-name>/elements.ts
export type ElementKind =
  | 'ring' | 'arc' | 'tick-ring' | 'brackets' | 'crosshair'
  | 'reticle' | 'readout' | 'bar' | 'graph' | 'grid' | 'vignette';

export type Element = {
  id: string;                 // kebab-case, unique
  kind: ElementKind;
  anchor: [number, number];   // normalized viewport coords, -1..1 (0,0 = center)
  size: number;               // normalized, 1 = viewport half-height
  // kind-specific params flattened here, e.g.:
  thickness?: number;         // stroke width in normalized units
  dashed?: boolean;
  count?: number;             // tick-ring
  glyphs?: number;            // readout
  font?: 'mono' | 'sans';
  notes?: string;             // anything not captured by params
};

export const elements: Element[] = [
  { id: 'outer-ring',  kind: 'ring',      anchor: [0, 0], size: 0.42, thickness: 0.004, dashed: true  },
  { id: 'tick-dial',   kind: 'tick-ring', anchor: [0, 0], size: 0.36, count: 60                       },
  // …
];
```

**Rules for this stage:**

- Closed set. Every element must be on screen in the chosen frame. No "and
  probably some decorative glyphs."
- Use normalized coordinates, not pixels. This decouples the artifact from
  resolution.
- If you cannot classify something, add `kind: 'unknown'` and describe it in
  `notes`. Do NOT invent a primitive.

**Stop here.** Present the inventory to the human, ask them to correct labels,
anchors, and to flag anything missing. Do not proceed until confirmed.

## Stage 3 — Motion grammar  `[CHECKPOINT]`

For each *kind* in the inventory (not each element — each kind), define the
behaviors it performs in this clip. Derive durations and easings by looking at
adjacent frame pairs per the `video-temporal-frames` skill (step C: delta
reasoning).

```ts
// plans/clips/<clip-name>/behaviors.ts
export type Easing =
  | 'linear' | 'power2.out' | 'power3.out' | 'expo.out'
  | 'back.out(2)' | 'sine.inOut' | 'steps(n)';

export type Behavior = {
  id: string;                 // e.g. 'ring.sweep-in'
  duration: number;           // seconds
  easing: Easing;
  params: string[];           // arg names this behavior consumes
  description: string;        // 1 line, plain English
};

export const behaviors: Behavior[] = [
  {
    id: 'ring.sweep-in',
    duration: 0.45,
    easing: 'power3.out',
    params: ['from', 'to'],
    description: 'Arc stroke draws from `from` angle to `to` angle.',
  },
  // …
];
```

**Rules for this stage:**

- Duration estimates must come from *measured* frame deltas. If the ring is
  invisible at `T02 (0.50s)` and fully drawn at `T04 (1.00s)`, the sweep is
  500ms. Do not freehand the number.
- Easing is inferred from spacing. Equal motion per frame → `linear`. Motion
  starts fast then slows → `power3.out`. Overshoots then settles → `back.out`.
- Cite the frames you used in the `description` if the behavior is non-obvious,
  e.g. `description: 'Arc sweep — see T02→T04, settles by T05.'`

**Stop here.** Review with the human: are the durations plausible, are the
easings right, anything missing.

## Stage 4 — Timeline  `[CHECKPOINT]`

This is the single deterministic artifact. It binds elements + behaviors to
timestamps.

```ts
// plans/clips/<clip-name>/timeline.ts
export type Event = {
  t: number;                  // seconds from clip start
  el: string;                 // element id from elements.ts
  do: string;                 // behavior id from behaviors.ts
  args?: Record<string, unknown>;
};

export const duration = 3.2;  // from _manifest.json

export const timeline: Event[] = [
  { t: 0.00, el: 'outer-ring',      do: 'ring.sweep-in', args: { from: -90, to: 270 } },
  { t: 0.20, el: 'tick-dial',       do: 'ring.sweep-in', args: { from: 0,   to: 360 } },
  { t: 0.45, el: 'corner-brackets', do: 'brackets.snap'                                 },
  // …
];
```

**Rules for this stage:**

- Every `t` must be a real frame timestamp from `_manifest.json`. No "about 1s."
- Every `el` must exist in `elements.ts`. Every `do` must exist in `behaviors.ts`.
- Simultaneous events get the same `t`. Order within a tie is irrelevant.
- If an element does nothing in the clip (pure idle/static), it stays out of
  the timeline but stays in the inventory.

**Stop here.** Human reviews the event list. They can sanity-check it by reading
the timeline top-to-bottom as if narrating the clip.

## Stage 5 — Primitive mapping

For each element kind, pick the right Three.js primitive. Write the decisions
into `primitives.md` for this clip (so later agents know why a given class was
chosen). Default table:

| Kind                                           | Primitive                                                  | Notes                                                 |
| ---                                            | ---                                                        | ---                                                   |
| `ring`, `arc`, `tick-ring`, dashed/solid lines | `Line2` / `LineSegments2` (`three/examples/jsm/lines/*`)   | Pixel-accurate width; supports dashes + world units.  |
| `ring` with animated fill/erase                | SDF shader on a camera-facing plane, `uProgress` uniform    | Smoother than editing geometry each frame.            |
| `brackets`, `crosshair`, `reticle`             | SDF shader on a plane, OR `Line2` if arms animate separately | Single glyph → shader. Independent arms → Line2.      |
| `readout` (scrambling text)                    | `troika-three-text` / drei `<Text>` + per-frame string swap | Never build glyphs with geometry.                     |
| `tick-ring` dense counts, particle fields      | `InstancedMesh`                                            | 60+ ticks in one draw call.                           |
| `grid`                                         | Shader on a plane                                          | Cheap, infinite zoom, no mesh.                        |
| `vignette`, `scanlines`, `grain`, `glow`       | Post-process pass (`postprocessing` via drei `<EffectComposer>`) | Applied globally, not per-element.                    |

**Camera default:** `OrthographicCamera` fit to viewport, unit = viewport
half-height. HUDs are 2D; perspective is only justified if the clip visibly
parallaxes.

**Coordinate convention:** inventory uses normalized viewport coords (-1..1).
Convert to Three.js world units at scene construction time only.

## Stage 6 — Implement

Build bottom-up in a scrubbable harness. Never ship the composed scene first.

### 6a. Harness

Create a dev-only route (e.g. `src/pages/dev/hud-<clip-name>.astro`) with:

- An R3F `<Canvas>` with the ortho camera from stage 5.
- A GSAP timeline bound to a visible `<input type="range">` scrubber from `0`
  to `duration`.
- A "single element" mode query param so you can render one element in
  isolation (`?only=outer-ring`).
- A reference-frame overlay: load the stage-1 PNG that matches the current
  scrubber time and draw it at 50% opacity behind the canvas. This is the most
  valuable feedback surface — you can literally drag the scrubber and see your
  render drift away from the reference.

### 6b. Atoms

Implement one `Element` renderer per `kind`. Pure; no timeline knowledge. A
renderer takes `(element, state)` where `state` is whatever the behavior mutates
(progress, scale, opacity, etc.).

### 6c. Behaviors

Implement each `behavior.id` as a function that returns a GSAP tween against
the element's state. Pure; no timeline knowledge.

### 6d. Compose

The scene composer reads `timeline.ts` and builds one `gsap.timeline({ paused:
true })`:

```ts
const tl = gsap.timeline({ paused: true });
for (const ev of timeline) {
  tl.add(runBehavior(ev.el, ev.do, ev.args), ev.t);
}
```

`tl.time(t)` now fully determines the scene at time `t`. The harness scrubber
just calls `tl.time(scrubber.value)`.

### 6e. Order of work

1. Get the harness rendering a single empty ortho canvas with the reference
   overlay.
2. Implement the most prominent element first. Match its behavior against the
   matching reference frames. Iterate until it matches.
3. Add elements one at a time. After each, drag the scrubber across the full
   clip and check nothing regressed.
4. Wire the full timeline last. At this point each addition should Just Work
   because each atom and behavior was already matched in isolation.

## Stage 7 — Diff loop

Once the full timeline plays:

1. Screen-record the canvas at the clip's duration and a fixed framerate (60fps
   or whatever the reference is).
2. Run `scripts/extract-video-frames.ts` on the recording with the **same**
   `--mode scene --scene-threshold` used in stage 1, so the frame timestamps
   align.
3. Write `diff/compare.html`: two columns (reference, ours), one row per
   timestamp, source PNGs from stage 1 and stage 7.
4. Find the *single worst* element-level mismatch. Fix only that atom or
   behavior. Re-record. Repeat.

Do not rewrite the scene to fix a mismatch. The artifacts are the source of
truth; if an easing is wrong, the fix is in `behaviors.ts` and the tween, not
in the composer.

---

## When to stop vs keep iterating

Declare done when:

- Every frame in `diff/compare.html` matches the reference frame at the same
  timestamp to within: silhouette correct, motion phase within ~1 frame, stroke
  weights within ~20% of reference.
- No artifact contradicts another (element id referenced in timeline must exist
  in elements, etc.).

Good enough is good enough. HUDs have deliberately noisy decoration — do not
chase pixel-perfect reproduction of individual glyphs in a readout. Match the
*behavior*, not the specific characters.

---

## Anti-patterns (things that will make this fail)

- **Skipping checkpoints.** The inventory-behaviors-timeline review gates exist
  because every later stage compounds errors. A wrong `kind` at stage 2 silently
  poisons everything.
- **Generating code before the timeline exists.** Writing `scene.tsx` before
  `timeline.ts` means you're guessing the motion while trying to implement it.
- **Using `THREE.Line`.** It can't do pixel-accurate width. Always `Line2`.
- **Perspective camera without a reason.** HUDs are 2D. If you find yourself
  tuning FOV to make things look right, switch to ortho.
- **Per-frame geometry rebuilds.** For sweeps/fills, use a shader with a
  `uProgress` uniform. Rebuilding `BufferGeometry` each frame kills perf and
  introduces jitter.
- **Baking timing into `useFrame`.** All timing belongs in the GSAP timeline.
  `useFrame` only reads `tl.time()` (or scrubber position) and applies state.
- **Treating the whole clip as one unit.** If a clip has two distinct beats
  (e.g. reticle acquires, then a readout resolves), split it into two clips
  upstream and run the playbook twice.

---

## Handoff template

When a future agent picks this up, they should receive:

1. Path to the `.mov`.
2. Scope note: *"focus on X; ignore Y."* Even short clips have too many
   secondary elements to reproduce in one pass.
3. Any existing artifacts (`elements.ts`, etc.) from prior sessions.

The agent's first response should be stage 1 output (frames + manifest) and
nothing else, so the human can confirm the frames are sensible before any
interpretation work begins.
