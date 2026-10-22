# Blender scene + Voxelize integration plan

Date: 2026-09-29  
Status: proposed architecture and visual exploration; not implemented.

## Goal and visual priority

Add an interactive Minecraft-style voxel area behind the central command platform of the existing cave website. The supplied Blender-style reference is the visual target. Adapt the playable area to the established architecture, camera composition, materials, and lighting.

Reference: [batcave-empty-platform-v4.png](../images/batcave-empty-platform-v4.png).

Current zoning follows the user's latest red-outlined scope guide in the conversation. Voxel terrain occupies only the bounded rear interior: the waterfall recess, central cave, and both stacked right laboratory interiors. Preserve the surrounding natural terrain frame, including the organic outer roof arch, its stalactites, side buttresses and front ledge lips. Recess the voxel scenery behind that original frame; do not expand it across the ceiling, side rock masses or below the marked boundary. Keep the foreground purple screens non-voxel. Preserve the upper-left workshop, command platform, long foreground bridge, lower-left platform and dock, empty right landing platform and aircraft hangar. A [saved unmarked close-up](voxelize-layouts-v4/section-reference-unmarked.png) provides composition context; the red boundary and yellow bridge mark are in the user's conversation image.

Revision history: round 1 encroached on the workshop; round 2 kept the voxel area too narrow; round 3 overextended the block scenery and replaced too much natural framing. Revision 4 follows the marked limit, retains the terrain frame and adds the explicitly requested half-metal/half-voxel bridge. Prior images remain available for comparison.

The yellow-circled bridge is the short diagonal rear-right pedestrian bridge from the central command platform to the lower former laboratory. Preserve its position, width and route. The half nearest the command deck remains Blender-style steel grating with thin metal railings; the half nearest the voxel cave is built from voxel slabs and square posts. The material change occurs at the midpoint along the bridge's length, not across its width. Both halves meet flush at a readable structural joint, with continuous walking height and no gap. This does not apply to the long foreground bridge or the connection to the large right circular platform.

This is a Minecraft-style experience built with Voxelize, not the complete Minecraft game. Specific mechanics remain application work.

## Core decision

Build permanent architecture in Blender. Store editable terrain as voxel data. Render both in one browser environment, then transition the camera and controls when the visitor enters the game.

The browser does not run Blender's renderer. GLB assets carry geometry and supported material data; the exact appearance of a Blender render requires deliberate browser lighting, material work, baked lighting, and postprocessing.

Using a Voxelize World as a scene container does not require adopting the demo's sky, daylight, or color palette. Preserve the website's art direction.

## Rendering architecture

Target: one WebGL renderer, a shared camera and depth buffer, one coordinated frame loop, and a controlled final output pipeline.

- Blender supplies the original natural terrain frame, permanent architecture outside the bounded rear interior, the workshop, command deck and screens, and the near half of the specified entry bridge.
- Voxelize supplies the bounded rear interior behind that frame, biome terrain/features, and the far half of the entry bridge, plus players and game state. Protect structural boundary blocks and the bridge connection where needed; a voxel appearance does not require every boundary block to be breakable.
- The integration adapter updates Voxelize from the existing React Three Fiber lifecycle.
- Shared depth gives correct occlusion between architecture and blocks.
- Match material output and color spaces before applying the final bloom and tone mapping once.
- Shadows, reflections, and bounced light across the boundary need explicit integration; they are not guaranteed by putting objects in the same scene.

A useful prototype is a Voxelize World as the actual render root with the Blender content added beneath it. Verify React Three Fiber lifecycle, scene hooks, asset loading, and postprocessing before committing to the production structure. Do not assume that nesting a Voxelize Scene as an ordinary child preserves all scene-level hooks.

Keep the present scene appearance as the baseline. Its station path already uses custom area/point lights, ambient occlusion, bloom, and AgX. First adjust voxel textures and shading locally. Do not change global exposure just to compensate for a mismatched voxel section.

If isolation later becomes necessary, a separate offscreen scene and render target can share the renderer, but compositing correct depth and color adds complexity. A true portal is appropriate only if the intended world extends beyond the physical bay or needs a fundamentally separate environment.

## Preserving the Blender look

For permanent architecture, bake suitable static illumination and ambient occlusion into textures/lightmaps where that gives a closer, cheaper match. Keep emissive accents and appropriate reflections under deliberate runtime control. Configure material and lightmap loading explicitly.

Baking is not a guarantee of an exact offline image from every camera angle. Reflections and other view-dependent effects need separate treatment.

Do not bake lighting that depends on editable terrain into permanent assets. A removable tree must not leave a permanent painted shadow. Live voxel geometry needs shading that updates when blocks change.

Customize the voxel palette, textures, ambient level, fog, and shader parameters to fit the cave. Do not assume ordinary Three.js area lights illuminate Voxelize's custom materials identically. Prototype opaque terrain first, then add water, transparent blocks, and more advanced shadows.

If exact pixels of a fixed Blender render ever become the requirement, use a fixed-camera prerender plus matched live compositing and depth masks. That would require a transition to a real-time version for free movement. The current recommendation remains real 3D architecture plus live terrain.

## Blender authoring and export

1. Block out the continuous rear bay and entry threshold before polishing details.
2. Choose block scale and playable extents against the actual imported scene.
3. Add named markers: voxel origin, playable bounds, player spawn, entrance camera, return camera, and protected entrance.
4. Export those markers with the permanent architecture.
5. Update the exporter's selected hierarchies so the new rear collection is included.
6. Resolve marker transforms after GLB axis conversion and the station's runtime recentering.
7. Keep the voxel grid axis-aligned for the first implementation and avoid arbitrary parent scaling/rotation of the physics world.

Use a simple consistent scale, initially one scene unit per voxel block if it fits the measured bay. If it does not fit, settle the unit mapping before detailing architecture. Do not shrink only rendered terrain while leaving collision and networking coordinates unchanged.

Blender can contain a rough terrain placeholder for composition. A precise reference mesh should be generated from the voxel data. A custom Blender-to-block exporter is an optional later tool; a GLB alone does not become editable block data.

## Terrain ownership and layout

Voxel data is the source of truth for the editable world. Do not maintain an independently hand-modeled detailed terrain duplicate in Blender.

Start with a bounded terrain region, a protected spawn/threshold, and clear paths. Permanent architecture stays outside the editable volume. Any lightweight browsing preview should be derived from a known voxel snapshot, with a deliberate refresh strategy so it does not contradict the live world.

Visual concepts are alternatives, not a requirement to implement all five. The chosen composition should leave enough negative space for the central command platform and keep the playable entrance legible.

## Interaction and loading

Use explicit states: browse → approach/load → ready → play → pause → return. Include loading-error and reconnect paths.

- Browse: existing website controls; a static snapshot or intentionally scheduled live preview.
- Approach: preload the game bundle, connect, and request chunks around the entrance. Do not use only the distant overview camera as the loading center.
- Ready: wait for the spawn's geometry, collision data, and required assets.
- Enter: an explicit visitor click requests pointer lock and enables game controls.
- Play: only gameplay controls own the camera; disable website orbit and cinematic camera writers.
- Pause: Escape releases pointer lock and presents a menu. Clear held inputs when focus is lost.
- Return: restore the saved camera pose, lens, orbit target, and site controls. Release or reduce game resources according to the preview mode.

Pointer lock must follow a browser-permitted user gesture. Do not rely on requesting it after an asynchronous loading or camera-animation sequence. Gate the current Escape handler and Blender lens updates so they do not fight game controls.

## Collision and block interaction

Imported Blender geometry is not automatically part of Voxelize collision.

For the first version, use voxel-based walking surfaces in the game area and a protected entry landing. Add deliberately supported collision proxies for any architecture that must be walkable or block movement, with a consistent representation on the server where relevant.

Server rules enforce the editable region, protected entrance, placement reach, and allowed changes. Interaction raycasts must respect intervening architecture; players must not edit blocks through solid walls.

Include a safe respawn location and fall recovery. Keep the original cavern outside the required walking area until traversal there is intentionally implemented.

## Game scope, multiplayer, and persistence

First release:
- One bounded creative sandbox.
- Walking, jumping, placing and removing blocks.
- A small curated block palette.
- Shared player visibility and synchronized edits.
- Protected spawn and architectural boundaries.
- Saved terrain, reconnect behavior, and a restore/reset path.

Voxelize provides a TypeScript/Three.js client and Rust server foundation. Run the game on a long-lived service with durable world storage and secure WebSocket access. Keep the website deployment workflow separate from the game process.

Application responsibilities include access rules, edit limits, world backup/restore, connection limits, and deployment configuration. Browsing visitors should not automatically be represented as active game avatars.

Crafting, survival, enemies, complex items, and large/infinite terrain are later scope.

## Performance and lifecycle

The current station uses on-demand rendering. Gameplay requires continuous frame updates. Animated live previews need an intentional update schedule; a static preview can stay on demand.

Lazy-load expensive game code, limit chunk radius, cap pixel density according to measurements, and assess the existing ambient-occlusion/bloom cost with terrain present. Suspend unnecessary rendering when hidden and resume safely without a giant physics timestep.

Clean up network connections, workers, controls, event listeners, and owned GPU resources when appropriate. Test repeated entry/exit and development remounts for duplicate connections or leaked resources.

Mobile viewing should preserve the scene with a lighter preview. Full mobile play requires deliberately designed touch controls and performance validation.

## Existing integration points

- [App.tsx](../secret-base/App.tsx): renderer, frame scheduling, postprocessing, visibility behavior.
- [PortfolioWorld.tsx](../secret-base/components/scene/PortfolioWorld.tsx): environment assembly.
- [ImportedPillar.tsx](../secret-base/components/scene/ImportedPillar.tsx): loaded assets and recentering.
- [CameraRig.tsx](../secret-base/components/scene/CameraRig.tsx): orbit, lens, camera transitions, Escape behavior.
- [MinecraftIsland.tsx](../secret-base/components/scene/MinecraftIsland.tsx): existing decorative voxel island, not a playable integration.
- [export_pillar.py](../secret-base/export_pillar.py): export selection and marker inclusion.

At the earlier inspection, the website declared Three.js ^0.183.2 and Voxelize main declared ^0.183.0. Pin a tested Voxelize revision, verify current dependencies, and deduplicate Three.js. Compatible version ranges are only an initial signal; the integration still needs testing.

## Implementation sequence and acceptance

1. Rendering proof: one small live terrain patch and a simple Blender bay in the existing composition. Confirm alignment, occlusion, color handling, and acceptable frame time.
2. Interaction proof: enter, walk, jump, edit, pause, and return with no camera/control conflict.
3. Shared-world proof: two clients observe the same changes; edits survive reconnect and a server restart.
4. Art pass: choose a rear-cavern concept and refine Blender assets, textures, lighting, and camera paths against the reference.
5. Production pass: measure performance and resource lifetime; test slow loading, server failure, resizing, focus changes, repeated visits, and mobile viewing.

The first deliverable is a small playable patch behind the center platform. A visitor can remove a block, turn around, and still see the original architecture occupying the same 3D space. Preserve the chosen reference composition before expanding scope.

## Current visual direction: Minecraft materials and a heavier rock border

Revision 7 supersedes revision 6's realistic voxel styling and retained rear waterfall/elevator. Remove the waterfall and elevator immediately left of the rear playable area; fill their space with natural cave framing. Retain more solid organic rock on the right. Use unmistakable Minecraft-style unit cubes, pixel textures and block vegetation within the recess. Achieve visual integration through lighting, depth, shadows and framing rather than realistic voxel materials. Keep the short rear-right bridge half steel and half voxel along its length, and preserve the workshop and full purple screen array.

[Five revision 7 concepts](voxelize-layouts-v7/README.md): lush cave, ancient city, Nether, End and villager village. [Exact prompts](voxelize-layouts-v7/prompts.md).

## Previous visual direction: revision 6

Revision 6 supersedes the broader revision 4–5 boundary. Keep the left natural waterfall and its rock/elevator pillar outside the voxel area. Retain thicker organic roof, stalactites, right shoulder, ledges and rock rims between the former lab openings. Voxel terrain sits deeper inside the center and two right alcoves. Match dark stone hues and cool ambient light; use foreground rock overlap, contact shadows, mist and restrained vegetation to soften the material boundary. Preserve the half-metal/half-voxel short rear-right bridge.

[Five revision 6 concepts](voxelize-layouts-v6/README.md): mossy ravine, drowned ruins, abandoned mine, obsidian rift and moonlit crystal garden. [Exact prompts](voxelize-layouts-v6/prompts.md).

## Previous visual alternatives: revision 5

Revision 4's boundaries and bridge layout are approved. Revision 5 changes the terrain shapes, focal structures and routes within that same frame, avoiding repeated arch-and-staircase compositions.

1. [Flooded jungle sinkhole](voxelize-layouts-v5/01-jungle-sinkhole.png).
2. [Buried desert temple](voxelize-layouts-v5/02-buried-desert-temple.png).
3. [Amethyst ice grotto](voxelize-layouts-v5/03-amethyst-ice-grotto.png).
4. [Volcanic forge](voxelize-layouts-v5/04-volcanic-forge.png).
5. [Giant mushroom forest](voxelize-layouts-v5/05-mushroom-forest.png).

[Revision 5 gallery](voxelize-layouts-v5/README.md) · [Exact revision 5 prompts](voxelize-layouts-v5/prompts.md) · [Screen restoration prompt](voxelize-layouts-v5/screen-restoration-prompt.md).

## Approved boundary and hybrid bridge layout: revision 4

1. [Framed lush cave](voxelize-layouts-v4/01-lush-cave.png).
2. [Framed ancient city](voxelize-layouts-v4/02-ancient-city.png).
3. [Framed mining cave](voxelize-layouts-v4/03-classic-mining-cave.png).
4. [Framed Nether cave](voxelize-layouts-v4/04-nether-basalt.png).
5. [Framed mixed-biome cave](voxelize-layouts-v4/05-layered-biomes.png).

[Revision 4 gallery](voxelize-layouts-v4/README.md) · [Exact revision 4 prompts](voxelize-layouts-v4/prompts.md).

## Previous visual layout alternatives: superseded overextended rear section

1. [Full lush cavern](voxelize-layouts-v3/01-lush-cave.png).
2. [Full ancient city](voxelize-layouts-v3/02-ancient-city.png).
3. [Full mining cavern](voxelize-layouts-v3/03-classic-mining-cave.png).
4. [Full Nether cavern](voxelize-layouts-v3/04-nether-basalt.png).
5. [Full connected biome landscape](voxelize-layouts-v3/05-layered-biomes.png).

[Revision 3 gallery](voxelize-layouts-v3/README.md) · [Exact revision 3 prompts](voxelize-layouts-v3/prompts.md).

## Previous visual layout alternatives: superseded narrow middle cave

1. [Lush cave + robotics workshop](voxelize-layouts-v2/01-lush-cave.png).
2. [Ancient city + precision workshop](voxelize-layouts-v2/02-ancient-city.png).
3. [Mining cave + fabrication workshop](voxelize-layouts-v2/03-classic-mining-cave.png).
4. [Nether cave + materials workshop](voxelize-layouts-v2/04-nether-basalt.png).
5. [Layered biomes + maker workshop](voxelize-layouts-v2/05-layered-biomes.png).

[Revision 2 gallery](voxelize-layouts-v2/README.md) · [Exact revision 2 prompts](voxelize-layouts-v2/prompts.md).

## Previous visual layout alternatives: superseded wider rear cavern

1. [Lush cave amphitheater](voxelize-layouts/01-lush-cave.png): moss terraces, a turquoise pool and clear winding paths.
2. [Ancient city excavation](voxelize-layouts/02-ancient-city.png): a deep avenue, sunken court, stepped ruins and restrained cyan light.
3. [Classic mining cavern](voxelize-layouts/03-classic-mining-cave.png): a diagonal ravine, timber crossing, mine terraces and ore seams.
4. [Nether basalt causeway](voxelize-layouts/04-nether-basalt.png): a raised route over a recessed lava basin.
5. [Layered biome cavern](voxelize-layouts/05-layered-biomes.png): connected lush upper terraces, ancient middle ruins and a lower volcanic fissure.

These are image-generated composition studies, not screenshots of an implemented engine or final Blender assets. Exact generation prompts and provenance are saved in [voxelize-layouts/prompts.md](voxelize-layouts/prompts.md).

## Sources

Technical research from the preceding planning discussion; recheck APIs against the revision selected for implementation.

- [Voxelize repository](https://github.com/voxelize/voxelize)
- [Client rendering architecture](https://docs.voxelize.io/tutorials/basics/create-the-client)
- [World implementation](https://github.com/voxelize/voxelize/blob/main/packages/core/src/core/world/index.ts)
- [World rendering options](https://github.com/voxelize/voxelize/blob/main/packages/core/src/core/world/world-options.ts)
- [Player controls](https://docs.voxelize.io/tutorials/basics/player-control)
- [Multiplayer](https://docs.voxelize.io/tutorials/basics/multiplayer)
- [Three.js material/lightmap documentation](https://threejs.org/docs/pages/MeshStandardMaterial.html)
- [Browser pointer lock](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_Lock_API)
