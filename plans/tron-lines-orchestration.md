# Tron Lines Orchestration

How the lines in `plans/clips/02 - Tron Lines - ...` are timed, where they start, where they go, and how fast they move. Reference for implementing the same effect on the site mesh.

Source clip: 41.25s, 4fps extract in `plans/clips/02 - Tron Lines - .../`.

## The story in plain English

Pretend you are watching this clip cold. Here is what your eye actually sees, beat by beat.

1. Black for two seconds. Anticipation.
2. A faint scaffold of grey lines fades in. You barely notice it. It is the wireframe of a city the camera will eventually fly through, but for now it just looks like graph paper noise.
3. One bright cyan line darts out from the left edge. It is a single comet head dragging a glowing trail. It travels horizontally for a few seconds before turning a corner.
4. While the first line is still moving, a second short line pops in somewhere else on the screen. It also starts to extend. Then a third. Each one moves on its own path. They are not children of the first line. They are independent tracers.
5. Around `~12s` the count of active lines starts ramping fast. You stop following individuals and just watch a system fill itself in. Many of the lines run as twin parallels — two strokes very close together with a small staircase offset. That is the PCB look.
6. By `~18-20s` the wireframe is mostly populated. The lines have outlined rectangle frames, building edges, ledges, and channels. The faint background scaffold is now mostly painted over by bright traces.
7. Around `22s` the camera starts to swing into perspective. What looked like a flat 2D line drawing reveals itself as a 3D city. The same traces now hug edges of buildings receding into the distance.
8. From `~26s` to `~32s` the wireframe glows and then fades into a fully rendered night city. The camera dollies forward through the city.
9. The TRON logo flares on at `~34s`, holds for a few seconds, then warps into a hyperdrive swirl. End of clip.

The line-orchestration content the user actually cares about lives in the window `t = 4s` to `t = 22s`. Everything before is a black hold + scaffold reveal. Everything after is camera and title work.

## Zoom-in 1: timeline of beats

| Beat | Time | What happens |
|------|------|--------------|
| Black hold | `0.0–2.0s` | Pure black. No lines. |
| Scaffold fade-in | `2.0–4.0s` | Faint grid edges fade up to ~5–10% intensity. Static, no movement. |
| First leader fires | `~3.5–4.0s` | A short cyan stub appears on the left edge, mid-height. |
| Hero solo run | `4.0–7.0s` | One leader visible on screen, moving right at constant speed. |
| Second spawn | `~7.0s` | A short isolated vertical fragment pops in elsewhere. Proves "lines don't all start from one source." |
| First turn | `~7.5–8.0s` | Hero leader hits a junction and pivots 90°. |
| Multi-leader | `8–12s` | 2–4 leaders active. First twins (paired parallel strokes) appear. |
| Density ramp | `12–18s` | New leaders spawn every ~0.3s. Frame fills. |
| Peak density | `18–22s` | Hundreds of segments visible. Wireframe city architecture is now legible. |
| Perspective tilt | `22–26s` | Camera transitions from flat to perspective. Lines hug 3D edges. |
| Hand-off to render | `26–32s` | Cyan traces dim. Rendered night city fades up. Camera dollies forward. |
| Title | `34–40s` | TRON logo flares, holds, hyperdrive zoom. |

## Zoom-in 2: anatomy of one leader

A leader is a single moving line. Each one is fully described by these fields.

```ts
type Leader = {
  path: Edge[];          // ordered list of grid-aligned segments
  speed: number;         // units per second, roughly constant
  spawnTime: number;     // when the head appears
  trailFade: number;     // seconds for trail to decay to scaffold intensity
  isTwin?: boolean;      // if true, sibling leader runs on parallel offset
}
```

A leader is **not** a random walker. It is a pre-baked path that is revealed over time by an animated head. The head position at time `t` is just `path.advance((t - spawnTime) * speed)`.

### Path shape rules

- All segments are axis-aligned. Pure horizontal or pure vertical strokes only.
- Turns are always exactly 90°.
- A path is typically `2–6` segments long. Common shapes:
  - **Straight**: one long horizontal run (3–6 grid cells).
  - **L-bracket**: horizontal then vertical, or the mirror.
  - **U / Z stair**: horizontal, short vertical, horizontal again — the PCB step pattern.
  - **Frame**: traces three sides of a rectangle (an open box).
- Paths follow the same edges as the underlying wireframe mesh. They never cut across empty space.

### The "head + trail" look

The line is not a stamp. It is a moving comet head with a fading tail.

- **Head**: ~100% intensity, roughly 1 grid cell wide, slightly bloomed.
- **Near-trail**: 80% intensity for the most recent 1–2 cells behind the head.
- **Far-trail**: linearly fades from 80% to ~30% over the next 4–6 cells.
- **Settle**: after ~1.5–2s the trail asymptotes to scaffold intensity (~10%) and merges into the static background.

So the visible bright stretch behind a moving head is roughly `speed × trailFade ≈ a few hundred pixels`. Pick `trailFade ≈ 1.5s` as a starting point.

### Speed

Eyeballing the hero leader (`t = 4s` to `t = 12s`): the head covers about `60% of screen width` over `~6s`. That is `~10% screen-width per second`, i.e. a full-screen horizontal traversal would take about `10s`.

Three speed tiers actually appear in the clip:

- **Hero pace** (`~10% screen/s`): used by the very first leader so the audience can lock onto it.
- **Standard pace** (`~25% screen/s`): used by most leaders during the multi-leader and density-ramp phases.
- **Sweep pace** (`~50% screen/s`): used by very long traces that have to cross most of the frame during the dense phase, so they don't fall behind.

Speed is **constant per leader**, not eased. No ease-in, no ease-out, no snap. Each leader picks its tier at spawn time and holds it. Variation across leaders gives the orchestration its organic feel without any per-leader easing.

### Twins

About `30–40%` of leaders run as twin pairs. A twin is a sibling leader on the parallel grid edge one cell offset, with a short `staircase connector` (an L) just ahead of where their heads are. This is the PCB trace look:

```
═════════╗
═════════╝
         ═════
```

Twins share `speed`, `trailFade`, and `path` topology. Their offset is one grid cell perpendicular to the direction of travel. They can switch which one leads via the staircase connector.

## Zoom-in 3: spawn schedule (the orchestration)

This is the heart of the user's question. **How** are lines orchestrated over time?

### Density curve

The number of currently-moving leaders over time follows roughly:

```
active(t) ≈ 0                                  for t < 4s
active(t) ≈ floor((t - 4)^1.6)                 for 4s ≤ t < 18s
active(t) ≈ 12                                 for 18s ≤ t < 22s   (saturated)
active(t) ≈ 12 → 0  linear                     for 22s ≤ t < 28s
```

That is: **slow start**, **quadratic-ish ramp**, **saturate**, **dissolve**.

| Window  | Spawn rate (per second) | Intent                          |
|---------|-------------------------|----------------------------------|
| 0–4s    | 0                       | Black hold and scaffold reveal  |
| 4–7s    | ~0.3 (one every 3s)     | Hero solo run, audience locks on |
| 7–12s   | ~1                      | Multi-leader buildup             |
| 12–18s  | ~3                      | Density ramp                     |
| 18–22s  | ~5 (peaks)              | Saturation                       |
| 22–28s  | 0                       | Camera takes over, traces dim    |

### Spawn location strategy

Spawns are weighted across the wireframe edge graph, not random points:

- **Hero-edge boost**: long horizontal/vertical runs that span a big portion of the screen are ~3× more likely to host a spawn than short edges.
- **Visible-frustum filter**: never spawn on an edge that is currently off-screen or behind the camera.
- **Repulsion**: a new spawn is rejected if its starting node is within ~1 grid cell of an active leader's head, to avoid visual clumping.
- **Foreground bias** (after t=15s): once perspective starts kicking in, weight closer-camera edges more heavily so the dense phase reads.

### Path picking strategy

When a leader spawns at a node, it picks its path like this:

1. Pick a direction at random of the 4 cardinal options (filtered by which edges actually exist from that node).
2. Travel along that edge to the next junction.
3. At the junction, roll dice:
   - 50% continue straight if straight is available
   - 35% turn 90° (random of the two perpendicular options)
   - 15% terminate
4. Cap total path length at `~6–8 grid cells` so leaders don't outlive the density ramp.

This produces the same visual rhythm seen in the clip: long straight runs punctuated by 90° turns, occasionally branching, occasionally just stopping.

## Zoom-in 4: the static scaffold

The faint grey grid that fades in at `t = 2s` is just **the wireframe mesh itself rendered at low intensity**. It is not animated. It is the same edge graph the leaders trace, drawn with:

- color: same hue as leaders (cyan), but desaturated and dimmed (~`#1a3a40`)
- opacity: ~`0.08`
- line width: ~`1px`

Its purpose is twofold:
- It **previews** the world before the lines fill it in. The audience subliminally understands "there is a system here waiting to light up."
- It gives the leader heads something to **align to**. Without it, a stray bright stroke in empty black has no context. With it, every stroke clearly traces something.

When the dense phase saturates, the scaffold becomes invisible because the bright traces overpower it. That is fine.

## Zoom-in 5: camera

Camera arc, in three phases:

- **Locked flat** (`0–15s`): orthographic or near-orthographic projection facing the wireframe. Reads as 2D. Slight idle pan/breathing optional.
- **Perspective lerp** (`15–22s`): projection eases from orthographic toward a cinematic perspective. Or, equivalently, a 3D camera that was always perspective starts dollying forward and slightly tilting, revealing the depth that was always there.
- **Dolly forward** (`22s+`): full perspective, camera flies through the wireframe city, then through the rendered city.

The shift from "flat 2D line art" to "3D wireframe city" is not a cut. It is a smooth re-projection. Easy to do in Three.js by lerping `camera.position`, `camera.lookAt`, and (if needed) `camera.zoom` between two presets.

## Implementation sketch

A minimal orchestrator boils down to:

```ts
type Beat = { time: number; spawn: () => Leader };

const schedule: Beat[] = [
  { time: 4.0, spawn: () => makeLeader({ tier: 'hero', startEdge: heroEdges.pickRandom() }) },
  { time: 7.0, spawn: () => makeLeader({ tier: 'standard', startEdge: anyEdges.pickRandom() }) },
  // ...
];

// Or expressed as a density function the orchestrator polls each frame:
function expectedSpawnsPerSecond(t: number): number { /* see density curve */ }
```

Each frame:

1. Advance every active leader's head by `speed * dt`.
2. Tick the trail fade for every still-glowing edge.
3. Roll against `expectedSpawnsPerSecond(t)` to maybe spawn a new leader.
4. Render scaffold + all active and fading edges.

State is small. The expensive part is the edge graph (built once from the mesh) and the trail buffer (one float-per-edge for current intensity).

## Music sync (matches `style-inspiration.md`)

The note in `plans/style-inspiration.md` says:

> Animation idea: turn intersections of lines into nodes, at each beat of the music a line will start from a node

That is exactly the model in this clip, just unscored. To wire it to music:

- Replace the spawn-rate density curve with a beat callback.
- On each detected beat, spawn `N` new leaders where `N` scales with bass energy.
- Map a riser to the perspective-lerp phase and a drop to the dolly-forward phase.
- Map the kick drum specifically to twin spawns since they are visually thicker / heavier.

## Open questions for next pass

- Exact `units-per-second` values once the website mesh is in place (depends on grid cell size).
- Twin offset distance — is it always `1 grid cell` or does it sometimes use `0.5` for tighter PCB rhythm?
- Whether to terminate leaders by **dimming** (current model) or by **erasing the head** (so the trail snaps off cleanly). The clip seems to use dimming.
- Whether to ever **branch** a leader (one becomes two at a junction) vs always treat each spawn as independent. The clip is ambiguous; probably both happen but independent spawns are more common.
