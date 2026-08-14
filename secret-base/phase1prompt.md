# Phase 1 Fable 5 Prompt — Three.js Portfolio Cave Hub

Build the first version of a **Three.js / React Three Fiber portfolio hub scene** based on the attached reference image.

The scene should be a **low-poly futuristic cave portfolio world** with six floating pillar islands connected by bridges. The goal of this phase is **clean structure, modular geometry, editability, and performance**, not final cinematic detail.

Use the attached image as the main visual reference for the camera angle, general composition, lighting mood, and island arrangement. Keep the scene recognizable as the same kind of hub: a central Projects island connected to About Me, Experiences, Contact, Workshop, and Minecraft islands.

---

## Overall Concept

Create a stylized low-poly cave environment with multiple floating/pillar islands connected by walkable bridges.

The six required islands are:

1. **Projects** — central main hub  
2. **About Me** — upper/back-left island  
3. **Workshop** — lower/front-left island  
4. **Experiences** — upper/back-right island  
5. **Contact** — far-right smaller communication island  
6. **Minecraft** — lower/front-right voxel island made of blocky Minecraft-like cubes  

The scene should feel like a **portfolio website navigation world**, not just a decorative render. Each island should be a clearly readable section.

Keep the visual style:

- low-poly cave
- futuristic sci-fi platforms
- dark graphite / blue-gray materials
- cyan neon accents
- warm lamp accents
- modular bridges
- clean silhouettes
- simplified geometry
- feasible for a real-time Three.js website

Do **not** make it overly organic or overly detailed. Make it more like a clean game environment or modular website scene.

---

## Camera and Composition

Use a fixed cinematic/isometric front three-quarter camera similar to the reference image.

Camera goal:

```txt
Fixed isometric / front three-quarter view
Orthographic or low-FOV perspective
Camera position approximately [10, 8, 12]
Look at [0, 0, 0]
Do not create free orbit controls in Phase 1
```

The layout should read clearly from this single hero angle.

Composition should roughly follow:

```txt
                 [ABOUT ME]          [EXPERIENCES]

                         \          /
                          \        /
             [WORKSHOP] -- [PROJECTS] -- [CONTACT]
                              |
                              |
                         [MINECRAFT]
```

More specific spatial plan:

```txt
ABOUT ME: back-left, medium height
WORKSHOP: front-left, lower height
PROJECTS: center, highest/main hub
EXPERIENCES: back-right, medium-high
CONTACT: far-right, smaller platform
MINECRAFT: front-right, separate voxel island
Main entrance bridge: foreground center into PROJECTS
```

Use an asymmetrical but balanced layout. It should not feel perfectly circular or mechanically even. The bridge paths should feel natural and aesthetic, but still modular and easy to build.

---

## Approximate Island Coordinates

Use these as rough starting positions. Adjust slightly if needed for composition, but keep the general arrangement.

```js
const islandLayout = {
  projects: {
    position: [0, 0, 0],
    radius: 5.5,
    height: 8
  },

  about: {
    position: [-7, 1.5, -3],
    radius: 3.2,
    height: 6
  },

  workshop: {
    position: [-8, -1, 3.5],
    radius: 3.8,
    height: 4.5
  },

  experiences: {
    position: [7, 1.5, -3],
    radius: 4.2,
    height: 6
  },

  contact: {
    position: [10, 0, 1.5],
    radius: 2.8,
    height: 5
  },

  minecraft: {
    position: [6.5, -1.2, 4.5],
    radius: 3.5,
    height: 3.5
  }
}
```

Use these coordinates to create clear height variation and depth.

---

## Required Phase 1 Objects

Only build the core scene. Keep props simplified.

Required objects:

```txt
- 6 platform islands
- 6 pillar bases
- 7 bridges
- 6 readable signs
- 1 central crystal on Projects
- 2 large screens on Projects
- 1 avatar/profile screen on About Me
- 1 timeline/card wall on Experiences
- 1 antenna + terminal on Contact
- 1 workbench + simple robot arm on Workshop
- 1 voxel terrain chunk + waterfall on Minecraft
- simple cave shell
- simple lighting
- simple fog/depth
```

The scene should already feel complete as a blockout, but it should not be final-art dense.

---

## Bridge Connection Plan

Create these bridge connections:

```txt
- foreground entrance bridge → Projects
- Projects → About Me
- Projects → Workshop
- Projects → Experiences
- Projects → Contact
- Projects → Minecraft
- optional Workshop → About Me side bridge
- optional Experiences → Contact short bridge
```

Bridge style:

```txt
Bridges should be modular:
- repeated floor segments/planks
- simple railings
- cyan emissive edge strips
- occasional square lamp posts
- simple supports where needed
- no overly complex trusses yet
```

The bridges should look walkable and practical.

---

## Island Design Requirements

### Projects Island

Projects is the centerpiece.

It should include:

```txt
- large circular or octagonal platform
- stacked ring base
- central glowing crystal
- two large screen panels
- one large readable PROJECTS sign
- simple console blocks
- cyan neon trim
- simple railings
```

Keep it clean and modular. Do not add too many screens or tiny props yet.

### About Me Island

Should include:

```txt
- readable ABOUT ME sign
- simple avatar/profile screen
- small desk or console
- 1 or 2 small lamps
- simple platform steps
```

### Workshop Island

Should include:

```txt
- readable WORKSHOP sign
- simple workbench
- simple robotic arm or crane
- a few crates/tool blocks
- warm practical lighting
```

### Experiences Island

Should include:

```txt
- readable EXPERIENCES sign
- wall with 4–5 simplified cards
- simple timeline line with circular nodes
- small console/table
```

### Contact Island

Should include:

```txt
- readable CONTACT sign
- terminal with envelope icon
- small antenna or communication tower
- one simple screen
```

### Minecraft Island

Should be visibly different from the other islands.

Use:

```txt
- cube-based terrain
- grass cubes
- dirt/stone cubes
- simple blocky trees
- small cube waterfall
- readable MINECRAFT sign
```

Keep it blocky and voxel-like. Do not make it too organic.

---

## Materials

Use a small material palette:

```txt
dark graphite metal:
- roughness around 0.45
- metalness around 0.3–0.5
- used for platforms, bridges, rails, consoles

low-poly cave rock:
- dark blue-gray
- flat shaded
- broad faceted surfaces
- not overly detailed

cyan emissive strips:
- used for bridge edges, platform trims, signs, pillar seams
- bloom-ready but not excessive

warm lamps:
- small amber emissive cubes or cylinders
- used sparingly for contrast

screen blue:
- emissive blue planes with simple UI-like lines

minecraft grass/dirt/stone:
- flat-color voxel cubes
- no complex textures in Phase 1
```

Keep materials simple and reusable.

---

## Cave and Background

Create a simplified low-poly cave shell.

The cave should have:

```txt
- large faceted wall shapes
- broad cave openings
- simplified stalactites
- deep blue fog
- a sense of vertical depth
- maybe simple distant pillars
```

Do not create a highly detailed organic cave. Use broad modular faceted geometry.

The lower section beneath the islands should be simple:

```txt
- dark blue void or chasm
- fog
- a few distant pillar silhouettes
- optional faint cyan vertical light strips
```

No heavy particle effects or complex water simulation yet.

---

## Code Structure

Organize the scene into clean React Three Fiber components.

Suggested structure:

```txt
/components/scene/
  PortfolioWorld.tsx
  CaveShell.tsx
  IslandBase.tsx
  Bridge.tsx
  Sign.tsx
  NeonStrip.tsx
  ProjectsIsland.tsx
  AboutIsland.tsx
  ExperiencesIsland.tsx
  ContactIsland.tsx
  WorkshopIsland.tsx
  MinecraftIsland.tsx
  Lighting.tsx
  CameraRig.tsx
```

Each island should be a separate `<group>` so it can later become clickable.

Use group names like:

```tsx
<group name="projectsIsland">
<group name="aboutIsland">
<group name="workshopIsland">
<group name="experiencesIsland">
<group name="contactIsland">
<group name="minecraftIsland">
```

Do not put the entire scene into one giant component.

---

## Interaction Preparation

Do not build full interactions in Phase 1.

But prepare the structure so interactions can be added later:

```txt
- each island should be its own group
- signs should be separate objects
- bridges should be reusable components
- props should be grouped by island
- camera should be fixed for now
```

Later phases will add hover, click, and camera movement.

---

## Do Not Include Yet

Do not add these in Phase 1:

```txt
- dense props
- hundreds of small rocks
- complex foliage
- realistic water simulation
- animated characters
- detailed vehicles
- suit bays
- complex textures
- excessive particle effects
- complex UI interactions
- dozens of small monitors
- detailed cave clutter
```

Keep this as a clean structural version.

---

## Performance Requirements

Build as if this needs to run in a real portfolio website.

Prioritize:

```txt
- low-poly geometry
- reusable components
- instanced/repeated simple meshes where useful
- simple materials
- limited lights
- no expensive shadows everywhere
- clean scene graph
- easy-to-edit props
```

Use placeholder geometry now. Final detail comes later.

---

## Phase 1 Success Checklist

Phase 1 is successful if:

```txt
- all 6 islands are present and labeled
- layout matches the reference image broadly
- Projects is clearly the central hub
- bridges connect logically
- the scene reads well from the fixed camera angle
- geometry is modular and editable
- cave shell exists but is simplified
- props are simple placeholders
- there is no dense detail yet
- the result feels feasible for a Three.js website
```

Do not chase final render quality in this phase. The goal is a strong, clean, modular base scene.

---

## Optional Extra Reference Guidance

For Phase 1, the front-view reference image is enough **if** the top-down layout and coordinates above are provided.

If an additional reference is supplied, prioritize a rough top-down map over another cinematic render.

Example top-down rough map:

```txt
           ABOUT ME              EXPERIENCES
              \                    /
               \                  /
                \                /
 WORKSHOP ------- PROJECTS ------- CONTACT
                   |
                   |
                MINECRAFT

Foreground entrance bridge comes from bottom center into Projects.
```

Optional side-view height plan:

```txt
highest: Projects
medium-high: About Me, Experiences
medium: Contact
lower: Workshop
lowest/separate: Minecraft
```

Multiple rendered angles are not required for Phase 1. They become more useful later, when refining exact island shapes, hidden sides, bridge slopes, and cave wraparound.
