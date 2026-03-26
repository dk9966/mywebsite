# Project Structure

## Stack

| Layer | Tool | Version |
|---|---|---|
| Meta-framework | Astro | v5 |
| 3D engine | Three.js | WebGPURenderer |
| 3D integration | React Three Fiber + Drei | latest |
| Animation | GSAP + ScrollTrigger | v3 |
| Smooth scroll | Lenis | latest |
| Styling | SCSS (BEM) | -- |
| 3D assets | Blender -> glTF/GLB | -- |
| Package manager | pnpm | -- |
| Deploy | Vercel | -- |

## Directory Layout

```
mywebsite/
├── public/
│   ├── models/              # .glb files (Blender exports, Draco compressed)
│   ├── textures/            # KTX2 compressed textures
│   ├── audio/               # background music, sfx
│   └── fonts/               # self-hosted fonts
│
├── src/
│   ├── assets/              # images, svgs processed by Astro
│   │
│   ├── components/          # non-3D UI components (Astro + React)
│   │   ├── Header.astro
│   │   ├── Footer.astro
│   │   ├── Navigation.astro
│   │   └── ProjectCard.astro
│   │
│   ├── components/three/    # React Three Fiber components (loaded as islands)
│   │   ├── Canvas.tsx        # shared R3F canvas wrapper with WebGPURenderer
│   │   ├── scenes/
│   │   │   ├── HeroScene.tsx         # landing 3D scene (Tron grid, light lines)
│   │   │   ├── TransitionScene.tsx   # between-section transitions
│   │   │   └── ProjectScene.tsx      # 3D scene for project showcases
│   │   ├── objects/
│   │   │   ├── TronBike.tsx          # Blender model loader + runtime behavior
│   │   │   ├── GridLines.tsx         # procedural Tron-style grid
│   │   │   ├── NodeNetwork.tsx       # line intersection -> node beat animation
│   │   │   └── HyperdriveTrail.tsx   # Star Wars hyperdrive particle effect
│   │   ├── effects/
│   │   │   ├── PostProcessing.tsx    # bloom, chromatic aberration, etc.
│   │   │   └── Particles.tsx         # GPU instanced particle system
│   │   └── helpers/
│   │       ├── useScrollAnimation.ts # connects GSAP ScrollTrigger to R3F
│   │       └── useAudioSync.ts       # beat detection for node animations
│   │
│   ├── animations/          # GSAP timeline definitions (non-3D)
│   │   ├── transitions.ts   # page/section transition animations
│   │   ├── reveals.ts       # scroll-triggered element reveals
│   │   └── scroll.ts        # Lenis + ScrollTrigger setup
│   │
│   ├── layouts/
│   │   └── BaseLayout.astro  # html head, font loading, analytics
│   │
│   ├── pages/
│   │   ├── index.astro       # home -- hero scene, about, featured projects
│   │   ├── projects/
│   │   │   ├── index.astro   # project grid (Minecraft inventory style?)
│   │   │   └── [slug].astro  # individual project detail
│   │   └── 404.astro
│   │
│   ├── styles/
│   │   ├── _variables.scss   # colors, spacing, breakpoints
│   │   ├── _mixins.scss      # responsive, typography mixins
│   │   ├── _reset.scss       # CSS reset / normalize
│   │   ├── _typography.scss  # font-face, type scale
│   │   └── global.scss       # imports all partials
│   │
│   ├── content/             # Astro content collections
│   │   ├── config.ts        # schema definitions
│   │   └── projects/        # markdown files for each project
│   │       ├── project-one.md
│   │       └── project-two.md
│   │
│   └── lib/                 # shared utilities
│       ├── constants.ts     # site-wide constants
│       └── utils.ts         # general helpers
│
├── blender/                 # Blender source files (not deployed)
│   ├── tron-bike.blend
│   ├── supernatural-car.blend
│   ├── duncan-shield.blend
│   └── exports/             # raw exports before compression
│
├── scripts/                 # build/dev scripts
│   └── compress-models.ts   # gltf-transform pipeline: Draco + KTX2
│
├── plans/                   # planning docs (this file lives here)
│   ├── style-inspiration.md
│   └── project-structure.md
│
├── astro.config.mjs
├── tsconfig.json
├── package.json
├── .gitignore
└── pnpm-lock.yaml
```

## Key Decisions

### Island hydration strategy

3D scenes use `client:idle` so they hydrate after the browser's main thread is free.
Non-critical interactive bits (theme toggle, nav menu) use `client:visible`.
Everything else is static HTML.

```astro
---
import HeroScene from '../components/three/scenes/HeroScene.tsx'
---
<HeroScene client:idle />
```

### WebGPU with fallback

The shared Canvas wrapper initializes `WebGPURenderer` and falls back to WebGL 2 automatically.
No feature detection code needed -- Three.js r171+ handles this.

### Asset pipeline

1. Model in Blender
2. Export as .glb to `blender/exports/`
3. Run `pnpm run compress-models` (gltf-transform: Draco mesh compression + KTX2 texture compression)
4. Output lands in `public/models/`
5. Load in R3F with `useGLTF` from drei (supports Draco out of the box)

### Scroll architecture

Lenis owns the scroll. GSAP ScrollTrigger is configured to read from Lenis instead of native scroll.
3D scenes receive normalized scroll progress (0-1) via a custom `useScrollAnimation` hook.

```
Lenis (smooth scroll) -> ScrollTrigger (scroll position) -> useScrollAnimation (hook) -> R3F scene
```

### Animation layering

Three layers of animation, kept separate:

1. **3D scene animation** -- R3F useFrame loop, driven by scroll progress or time
2. **DOM animation** -- GSAP timelines for HTML elements (text reveals, section transitions)
3. **Transition animation** -- coordinated handoffs between DOM and 3D (e.g. Spider-Verse flip)

### Blender vs code decision rule

- If you can describe it as math (grid, particles, lines, waves) -> procedural in Three.js
- If you'd need to "sculpt" it (bike, car, shield, characters) -> Blender
- If it needs to react to user input in real time -> Three.js even if complex
- If it's a pre-baked cinematic sequence -> Blender animation exported as glTF

## Dependencies (package.json outline)

```json
{
  "dependencies": {
    "astro": "^5",
    "@astrojs/react": "latest",
    "react": "^19",
    "react-dom": "^19",
    "three": "latest",
    "@react-three/fiber": "latest",
    "@react-three/drei": "latest",
    "@react-three/postprocessing": "latest",
    "gsap": "latest",
    "lenis": "latest"
  },
  "devDependencies": {
    "sass": "latest",
    "@gltf-transform/core": "latest",
    "@gltf-transform/extensions": "latest",
    "@gltf-transform/cli": "latest"
  }
}
```

## Next Steps

1. `pnpm create astro@latest` and configure with React + SCSS
2. Set up the directory structure
3. Get a basic R3F canvas rendering with WebGPURenderer inside an Astro island
4. Wire up Lenis + GSAP ScrollTrigger
5. Build the hero scene (Tron grid + light lines) as the first visual proof of concept
6. Start modeling assets in Blender
