# Bounded voxel interior + preserved rock frame + half-and-half bridge — revision 4

Tool: built-in imagegen edits. Five independent concepts, plus a targeted correction to the lush concept's bridge placement.

The final lush image also uses this [exact bridge correction prompt](bridge-correction-prompt.md).

Inputs supplied through recent conversation images: the user's red-outlined/yellow-circled scope guide, the [unmarked close-up](section-reference-unmarked.png), and the [full-frame revision 2 ancient-city scene](../voxelize-layouts-v2/02-ancient-city.png). The annotated image is in the conversation; the saved close-up does not include the markup. Ignore screenshot editing UI.

Scope: voxel terrain stays inside the red boundary and behind the original natural rock frame. The short diagonal rear-right bridge keeps its near half as Blender-style metal and its far half as biome-appropriate voxel construction, meeting at the midpoint along its length. Other bridges remain unchanged.

## Framed lush cave

Output: [01-lush-cave.png](01-lush-cave.png)

```text
Use case: precise-object-edit.
Asset type: cinematic full-frame 3D website environment concept, revision 4.

INPUT ROLES: The WIDE full-scene image is the EDIT TARGET. The CLOSE-UP WITH A RED OUTLINE AND YELLOW OVAL is the user's exact spatial boundary and bridge guide. The unmarked close-up is a supporting detail reference. Output the full wide composition, not the crop. Remove all screenshot UI, markup lines and annotation colors from the finished result.

TOP PRIORITY — RESPECT THE RED OUTLINE AND KEEP THE NATURAL TERRAIN FRAME:
Only replace the scene INSIDE the user's red outline: the recessed rear waterfall area, central rear game cave, and the interiors/contents of BOTH small stacked right lab alcoves. Transform that interior into one connected Minecraft/Voxelize environment. Do NOT extend it upward, sideways, or down beyond the red boundary. In the wide image this is the bounded rear bay between the upper-left workshop and the right-side hangar/landing-pad rock mass.
Preserve the ORIGINAL NATURAL ROCK FRAME around this bay: the thick irregular outer roof arch, hanging natural stalactites at its mouth, side buttresses, and the front rocky ledge lips. Keep their organic non-voxel surfaces and their exact original silhouette. The new block-built scenery must sit recessed BEHIND this frame like an environment inside an existing cave, not replace the frame with a giant rectangular block wall or expand across the rear ceiling. Keep a visible natural-rock border around the opening. The former right laboratories become biome terraces within their existing bounded volume, not terrain spreading onto the jet hangar or large empty right platform. Remove their modern lab furniture and equipment. Inside the framed recess, terrain can connect across those former room levels. Preserve the purple screens in front.

SECOND TOP PRIORITY — THE YELLOW-CIRCLED BRIDGE MUST BE HALF METAL / HALF VOXEL:
Identify the SHORT DIAGONAL REAR-RIGHT pedestrian bridge from the CENTRAL COMMAND PLATFORM to the LOWER former right laboratory alcove. It is behind the small right-side purple screens. This is NOT the long bridge coming toward the camera and NOT the bridge to the large empty circular right platform.
Keep this short bridge in its original position, width, and path. Its first HALF, starting at the central command platform, stays the original realistic Blender-style dark steel: thin metal railings, narrow posts, metal grating. At EXACTLY THE MIDPOINT ALONG ITS LENGTH, change to a visibly block-built Minecraft bridge for the second HALF entering the voxel cave: cubic stone or biome-appropriate slabs, chunky square posts, and block-built parapets. This is a LENGTHWISE progression, not left/right halves of the bridge's width. Both halves meet flush at one clear, structurally believable midpoint seam with continuous walking height and no gap. Make the metal-to-block material change readable at this camera angle; do not hide it behind added scenery and do not turn the entire bridge into either material.

PRESERVE OUTSIDE THE EDIT: the upper-left workshop and its furniture, floor, entire broad stairs and enclosure; central command deck, all purple displays and their mounts, emblem and furniture; long foreground bridge; lower-left landing/stairs/dock/boat; empty large circular right landing pad and its industrial back wall; aircraft hangar, aircraft and surrounding rock. Keep all positions, camera perspective and framing unchanged. The purple monitor array must remain non-voxel and recognizable. Keep the foreground abyss and waterfalls OUTSIDE the selected rear recess.

VISUAL STYLE: same sophisticated cool dark-blue cave rendering and realistic metal architecture as the full reference. Local Minecraft-style cube terrain, pixel-textured materials and controlled biome lighting only INSIDE the bounded rear recess. Match perspective, scale, occlusion and atmosphere. No new characters or creatures. No portals, display screens, glass tanks or murals substituting for the real playable area. No labels, arrows, circles, red outlines, title text, editing toolbar, watermark or game UI. ONE finished full-frame image.

Biome: LUSH CAVE. Inside the original preserved natural rock frame, create mossy stepped cubic terraces, a small blue-green pool, a block waterfall in the former waterfall recess, hanging glow-berry vines and restrained azalea foliage. Replace both right lab interiors with connected planted stone ledges and narrow block stairs contained inside the original outer cliff outline. Leave the entrance spacious and do not cover the screens. Lush foliage should stop before the natural frame edges. For the yellow-circled short bridge: near half dark steel grating and thin rails, far half mossy stone blocks with squared stone posts, meeting exactly at the midpoint. Keep a crisp visible seam, not a full moss-covered bridge.
```

## Framed ancient city

Output: [02-ancient-city.png](02-ancient-city.png)

```text
Use case: precise-object-edit.
Asset type: cinematic full-frame 3D website environment concept, revision 4.

INPUT ROLES: The WIDE full-scene image is the EDIT TARGET. The CLOSE-UP WITH A RED OUTLINE AND YELLOW OVAL is the user's exact spatial boundary and bridge guide. The unmarked close-up is a supporting detail reference. Output the full wide composition, not the crop. Remove all screenshot UI, markup lines and annotation colors from the finished result.

TOP PRIORITY — RESPECT THE RED OUTLINE AND KEEP THE NATURAL TERRAIN FRAME:
Only replace the scene INSIDE the user's red outline: the recessed rear waterfall area, central rear game cave, and the interiors/contents of BOTH small stacked right lab alcoves. Transform that interior into one connected Minecraft/Voxelize environment. Do NOT extend it upward, sideways, or down beyond the red boundary. In the wide image this is the bounded rear bay between the upper-left workshop and the right-side hangar/landing-pad rock mass.
Preserve the ORIGINAL NATURAL ROCK FRAME around this bay: the thick irregular outer roof arch, hanging natural stalactites at its mouth, side buttresses, and the front rocky ledge lips. Keep their organic non-voxel surfaces and their exact original silhouette. The new block-built scenery must sit recessed BEHIND this frame like an environment inside an existing cave, not replace the frame with a giant rectangular block wall or expand across the rear ceiling. Keep a visible natural-rock border around the opening. The former right laboratories become biome terraces within their existing bounded volume, not terrain spreading onto the jet hangar or large empty right platform. Remove their modern lab furniture and equipment. Inside the framed recess, terrain can connect across those former room levels. Preserve the purple screens in front.

SECOND TOP PRIORITY — THE YELLOW-CIRCLED BRIDGE MUST BE HALF METAL / HALF VOXEL:
Identify the SHORT DIAGONAL REAR-RIGHT pedestrian bridge from the CENTRAL COMMAND PLATFORM to the LOWER former right laboratory alcove. It is behind the small right-side purple screens. This is NOT the long bridge coming toward the camera and NOT the bridge to the large empty circular right platform.
Keep this short bridge in its original position, width, and path. Its first HALF, starting at the central command platform, stays the original realistic Blender-style dark steel: thin metal railings, narrow posts, metal grating. At EXACTLY THE MIDPOINT ALONG ITS LENGTH, change to a visibly block-built Minecraft bridge for the second HALF entering the voxel cave: cubic stone or biome-appropriate slabs, chunky square posts, and block-built parapets. This is a LENGTHWISE progression, not left/right halves of the bridge's width. Both halves meet flush at one clear, structurally believable midpoint seam with continuous walking height and no gap. Make the metal-to-block material change readable at this camera angle; do not hide it behind added scenery and do not turn the entire bridge into either material.

PRESERVE OUTSIDE THE EDIT: the upper-left workshop and its furniture, floor, entire broad stairs and enclosure; central command deck, all purple displays and their mounts, emblem and furniture; long foreground bridge; lower-left landing/stairs/dock/boat; empty large circular right landing pad and its industrial back wall; aircraft hangar, aircraft and surrounding rock. Keep all positions, camera perspective and framing unchanged. The purple monitor array must remain non-voxel and recognizable. Keep the foreground abyss and waterfalls OUTSIDE the selected rear recess.

VISUAL STYLE: same sophisticated cool dark-blue cave rendering and realistic metal architecture as the full reference. Local Minecraft-style cube terrain, pixel-textured materials and controlled biome lighting only INSIDE the bounded rear recess. Match perspective, scale, occlusion and atmosphere. No new characters or creatures. No portals, display screens, glass tanks or murals substituting for the real playable area. No labels, arrows, circles, red outlines, title text, editing toolbar, watermark or game UI. ONE finished full-frame image.

Biome: ANCIENT CITY. Retain the handsome central broken block arch and develop a bounded deepslate ruin courtyard behind the original organic cave frame. Cyan sculk-like growth and sparse soul-lantern-like lights define cubic stairs and low ruins. Both former right laboratory interiors become recessed upper/lower archaeological terraces linked to the central route; keep them within the existing natural rock perimeter. Use a small cyan cascade in the rear waterfall recess. Preserve plenty of dark space around the ruin silhouettes so this is not a giant block facade. The short circled bridge has exactly its near half in original steel and its far half in charcoal block slabs with square cyan-lantern stone posts. The midpoint joint is obvious and flush. No glowing portal.
```

## Framed mining cave

Output: [03-classic-mining-cave.png](03-classic-mining-cave.png)

```text
Use case: precise-object-edit.
Asset type: cinematic full-frame 3D website environment concept, revision 4.

INPUT ROLES: The WIDE full-scene image is the EDIT TARGET. The CLOSE-UP WITH A RED OUTLINE AND YELLOW OVAL is the user's exact spatial boundary and bridge guide. The unmarked close-up is a supporting detail reference. Output the full wide composition, not the crop. Remove all screenshot UI, markup lines and annotation colors from the finished result.

TOP PRIORITY — RESPECT THE RED OUTLINE AND KEEP THE NATURAL TERRAIN FRAME:
Only replace the scene INSIDE the user's red outline: the recessed rear waterfall area, central rear game cave, and the interiors/contents of BOTH small stacked right lab alcoves. Transform that interior into one connected Minecraft/Voxelize environment. Do NOT extend it upward, sideways, or down beyond the red boundary. In the wide image this is the bounded rear bay between the upper-left workshop and the right-side hangar/landing-pad rock mass.
Preserve the ORIGINAL NATURAL ROCK FRAME around this bay: the thick irregular outer roof arch, hanging natural stalactites at its mouth, side buttresses, and the front rocky ledge lips. Keep their organic non-voxel surfaces and their exact original silhouette. The new block-built scenery must sit recessed BEHIND this frame like an environment inside an existing cave, not replace the frame with a giant rectangular block wall or expand across the rear ceiling. Keep a visible natural-rock border around the opening. The former right laboratories become biome terraces within their existing bounded volume, not terrain spreading onto the jet hangar or large empty right platform. Remove their modern lab furniture and equipment. Inside the framed recess, terrain can connect across those former room levels. Preserve the purple screens in front.

SECOND TOP PRIORITY — THE YELLOW-CIRCLED BRIDGE MUST BE HALF METAL / HALF VOXEL:
Identify the SHORT DIAGONAL REAR-RIGHT pedestrian bridge from the CENTRAL COMMAND PLATFORM to the LOWER former right laboratory alcove. It is behind the small right-side purple screens. This is NOT the long bridge coming toward the camera and NOT the bridge to the large empty circular right platform.
Keep this short bridge in its original position, width, and path. Its first HALF, starting at the central command platform, stays the original realistic Blender-style dark steel: thin metal railings, narrow posts, metal grating. At EXACTLY THE MIDPOINT ALONG ITS LENGTH, change to a visibly block-built Minecraft bridge for the second HALF entering the voxel cave: cubic stone or biome-appropriate slabs, chunky square posts, and block-built parapets. This is a LENGTHWISE progression, not left/right halves of the bridge's width. Both halves meet flush at one clear, structurally believable midpoint seam with continuous walking height and no gap. Make the metal-to-block material change readable at this camera angle; do not hide it behind added scenery and do not turn the entire bridge into either material.

PRESERVE OUTSIDE THE EDIT: the upper-left workshop and its furniture, floor, entire broad stairs and enclosure; central command deck, all purple displays and their mounts, emblem and furniture; long foreground bridge; lower-left landing/stairs/dock/boat; empty large circular right landing pad and its industrial back wall; aircraft hangar, aircraft and surrounding rock. Keep all positions, camera perspective and framing unchanged. The purple monitor array must remain non-voxel and recognizable. Keep the foreground abyss and waterfalls OUTSIDE the selected rear recess.

VISUAL STYLE: same sophisticated cool dark-blue cave rendering and realistic metal architecture as the full reference. Local Minecraft-style cube terrain, pixel-textured materials and controlled biome lighting only INSIDE the bounded rear recess. Match perspective, scale, occlusion and atmosphere. No new characters or creatures. No portals, display screens, glass tanks or murals substituting for the real playable area. No labels, arrows, circles, red outlines, title text, editing toolbar, watermark or game UI. ONE finished full-frame image.

Biome: CLASSIC MINING CAVE. Within the preserved natural rock frame, use cubic gray-stone ledges, a narrow blue stream, small ore seams, one timber trestle and a mine tunnel receding into the central depth. The two former right lab interiors become connected mine ledges with timber supports, all recessed behind the original cliff boundary. A modest Minecraft-like block waterfall occupies the old waterfall recess without altering the outer arch. Keep warm torches sparse against the cool blue cave. The short circled entry bridge stays thin steel grating/railings for its first half from the command platform, then changes at its midpoint to visibly cubic oak plank blocks, blocky log posts and a chunky squared wooden rail for the second half. This half-and-half bridge must remain distinct from any separate trestle deeper in the mine.
```

## Framed Nether cave

Output: [04-nether-basalt.png](04-nether-basalt.png)

```text
Use case: precise-object-edit.
Asset type: cinematic full-frame 3D website environment concept, revision 4.

INPUT ROLES: The WIDE full-scene image is the EDIT TARGET. The CLOSE-UP WITH A RED OUTLINE AND YELLOW OVAL is the user's exact spatial boundary and bridge guide. The unmarked close-up is a supporting detail reference. Output the full wide composition, not the crop. Remove all screenshot UI, markup lines and annotation colors from the finished result.

TOP PRIORITY — RESPECT THE RED OUTLINE AND KEEP THE NATURAL TERRAIN FRAME:
Only replace the scene INSIDE the user's red outline: the recessed rear waterfall area, central rear game cave, and the interiors/contents of BOTH small stacked right lab alcoves. Transform that interior into one connected Minecraft/Voxelize environment. Do NOT extend it upward, sideways, or down beyond the red boundary. In the wide image this is the bounded rear bay between the upper-left workshop and the right-side hangar/landing-pad rock mass.
Preserve the ORIGINAL NATURAL ROCK FRAME around this bay: the thick irregular outer roof arch, hanging natural stalactites at its mouth, side buttresses, and the front rocky ledge lips. Keep their organic non-voxel surfaces and their exact original silhouette. The new block-built scenery must sit recessed BEHIND this frame like an environment inside an existing cave, not replace the frame with a giant rectangular block wall or expand across the rear ceiling. Keep a visible natural-rock border around the opening. The former right laboratories become biome terraces within their existing bounded volume, not terrain spreading onto the jet hangar or large empty right platform. Remove their modern lab furniture and equipment. Inside the framed recess, terrain can connect across those former room levels. Preserve the purple screens in front.

SECOND TOP PRIORITY — THE YELLOW-CIRCLED BRIDGE MUST BE HALF METAL / HALF VOXEL:
Identify the SHORT DIAGONAL REAR-RIGHT pedestrian bridge from the CENTRAL COMMAND PLATFORM to the LOWER former right laboratory alcove. It is behind the small right-side purple screens. This is NOT the long bridge coming toward the camera and NOT the bridge to the large empty circular right platform.
Keep this short bridge in its original position, width, and path. Its first HALF, starting at the central command platform, stays the original realistic Blender-style dark steel: thin metal railings, narrow posts, metal grating. At EXACTLY THE MIDPOINT ALONG ITS LENGTH, change to a visibly block-built Minecraft bridge for the second HALF entering the voxel cave: cubic stone or biome-appropriate slabs, chunky square posts, and block-built parapets. This is a LENGTHWISE progression, not left/right halves of the bridge's width. Both halves meet flush at one clear, structurally believable midpoint seam with continuous walking height and no gap. Make the metal-to-block material change readable at this camera angle; do not hide it behind added scenery and do not turn the entire bridge into either material.

PRESERVE OUTSIDE THE EDIT: the upper-left workshop and its furniture, floor, entire broad stairs and enclosure; central command deck, all purple displays and their mounts, emblem and furniture; long foreground bridge; lower-left landing/stairs/dock/boat; empty large circular right landing pad and its industrial back wall; aircraft hangar, aircraft and surrounding rock. Keep all positions, camera perspective and framing unchanged. The purple monitor array must remain non-voxel and recognizable. Keep the foreground abyss and waterfalls OUTSIDE the selected rear recess.

VISUAL STYLE: same sophisticated cool dark-blue cave rendering and realistic metal architecture as the full reference. Local Minecraft-style cube terrain, pixel-textured materials and controlled biome lighting only INSIDE the bounded rear recess. Match perspective, scale, occlusion and atmosphere. No new characters or creatures. No portals, display screens, glass tanks or murals substituting for the real playable area. No labels, arrows, circles, red outlines, title text, editing toolbar, watermark or game UI. ONE finished full-frame image.

Biome: NETHER BASALT. Make a contained volcanic scene recessed BEHIND the existing natural cave arch and sidewalls. Use stepped basalt formations, a narrow lavafall in the former waterfall recess, a small recessed lava channel, dark blackstone terraces and restrained crimson fungus. Both former right laboratories become two connected basalt ledges inside their old bounded volume. Do not create a huge lava wall or spread block ceiling beyond the natural frame. Preserve the surrounding blue architecture and leave the realistic outer rock frame clearly visible and cool. The yellow-circled short diagonal bridge remains dark realistic metal for the half closest to the command platform and becomes chunky blackstone block slabs and squared block parapets for the far half. Make the midpoint seam readable with a slightly lighter top face on the blackstone blocks. Keep lava below the far landing and away from the steel half.
```

## Framed mixed-biome cave

Output: [05-layered-biomes.png](05-layered-biomes.png)

```text
Use case: precise-object-edit.
Asset type: cinematic full-frame 3D website environment concept, revision 4.

INPUT ROLES: The WIDE full-scene image is the EDIT TARGET. The CLOSE-UP WITH A RED OUTLINE AND YELLOW OVAL is the user's exact spatial boundary and bridge guide. The unmarked close-up is a supporting detail reference. Output the full wide composition, not the crop. Remove all screenshot UI, markup lines and annotation colors from the finished result.

TOP PRIORITY — RESPECT THE RED OUTLINE AND KEEP THE NATURAL TERRAIN FRAME:
Only replace the scene INSIDE the user's red outline: the recessed rear waterfall area, central rear game cave, and the interiors/contents of BOTH small stacked right lab alcoves. Transform that interior into one connected Minecraft/Voxelize environment. Do NOT extend it upward, sideways, or down beyond the red boundary. In the wide image this is the bounded rear bay between the upper-left workshop and the right-side hangar/landing-pad rock mass.
Preserve the ORIGINAL NATURAL ROCK FRAME around this bay: the thick irregular outer roof arch, hanging natural stalactites at its mouth, side buttresses, and the front rocky ledge lips. Keep their organic non-voxel surfaces and their exact original silhouette. The new block-built scenery must sit recessed BEHIND this frame like an environment inside an existing cave, not replace the frame with a giant rectangular block wall or expand across the rear ceiling. Keep a visible natural-rock border around the opening. The former right laboratories become biome terraces within their existing bounded volume, not terrain spreading onto the jet hangar or large empty right platform. Remove their modern lab furniture and equipment. Inside the framed recess, terrain can connect across those former room levels. Preserve the purple screens in front.

SECOND TOP PRIORITY — THE YELLOW-CIRCLED BRIDGE MUST BE HALF METAL / HALF VOXEL:
Identify the SHORT DIAGONAL REAR-RIGHT pedestrian bridge from the CENTRAL COMMAND PLATFORM to the LOWER former right laboratory alcove. It is behind the small right-side purple screens. This is NOT the long bridge coming toward the camera and NOT the bridge to the large empty circular right platform.
Keep this short bridge in its original position, width, and path. Its first HALF, starting at the central command platform, stays the original realistic Blender-style dark steel: thin metal railings, narrow posts, metal grating. At EXACTLY THE MIDPOINT ALONG ITS LENGTH, change to a visibly block-built Minecraft bridge for the second HALF entering the voxel cave: cubic stone or biome-appropriate slabs, chunky square posts, and block-built parapets. This is a LENGTHWISE progression, not left/right halves of the bridge's width. Both halves meet flush at one clear, structurally believable midpoint seam with continuous walking height and no gap. Make the metal-to-block material change readable at this camera angle; do not hide it behind added scenery and do not turn the entire bridge into either material.

PRESERVE OUTSIDE THE EDIT: the upper-left workshop and its furniture, floor, entire broad stairs and enclosure; central command deck, all purple displays and their mounts, emblem and furniture; long foreground bridge; lower-left landing/stairs/dock/boat; empty large circular right landing pad and its industrial back wall; aircraft hangar, aircraft and surrounding rock. Keep all positions, camera perspective and framing unchanged. The purple monitor array must remain non-voxel and recognizable. Keep the foreground abyss and waterfalls OUTSIDE the selected rear recess.

VISUAL STYLE: same sophisticated cool dark-blue cave rendering and realistic metal architecture as the full reference. Local Minecraft-style cube terrain, pixel-textured materials and controlled biome lighting only INSIDE the bounded rear recess. Match perspective, scale, occlusion and atmosphere. No new characters or creatures. No portals, display screens, glass tanks or murals substituting for the real playable area. No labels, arrows, circles, red outlines, title text, editing toolbar, watermark or game UI. ONE finished full-frame image.

Biome: CONNECTED MIXED CAVE. Compose a contained landscape inside the intact organic terrain frame: upper-left mossy block terraces feed a short waterfall, the central route crosses cyan-lit deepslate ruins, and the former lower-right lab volume becomes a small basalt fissure with restrained orange lava. The former upper-right lab becomes an overgrown ruined ledge. Link them with compact block stairs without extending outside the red boundary. Keep water and lava separated by stone and keep the foreground monitors unobstructed. This is one framed cave interior with varied terrain, not a sprawling panorama across the whole ceiling. The circled short rear-right bridge is exactly half realistic metal at the command-platform end and half pale-gray weathered voxel stone at the cave end, with squared posts, a little moss on the far section and a distinct flush joint at the midpoint.
```
