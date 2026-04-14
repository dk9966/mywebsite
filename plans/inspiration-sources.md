# Inspiration Sources

## Underrated portfolio / web sources

- **Three.js Journey showcase** (threejs-journey.com) - Student final projects. Raw, experimental work before it gets polished into agency pieces. Good for ideas nobody else is using yet.

https://threejs-journey.com/selection/the-anomaly

- i love how it has a galaxy background behind the low poly base
  https://threejs-journey.com/selection/bluebox-design-intro
- i like the ocean split into grid style
  https://threejs-journey.com/selection/merouane-bali-portfolio

- i love the initializezation animation and also the zooming in nd out of certain sections, as well as the black and white

https://threejs-journey.com/selection/soo-ah-room-folio

- i like the very cute desk setup and also i lvoe generation animation of items

https://www.teahu-experience.com/

- i like the pretty smooth first person style world
  https://threejs-journey.com/selection/studio-carto-urban-project- a good example of a nice map
  https://threejs-journey.com/selection/84-24

- i love the integration of 3d models inside a text file

https://threejs-journey.com/selection/mike-fernandez-portfolio#

- a good example of low poly rpg style navigation

https://threejs-journey.com/selection/simon-tessier-portfolio#

- around 56 seconds theres a cool like cinema style rotation view of pages

https://threejs-journey.com/selection/outer-wilds-planetary

- i like the planet design

https://threejs-journey.com/selection/impossible-box

- i love the use of rotation to introduce different scenes

https://threejs-journey.com/selection/unknown-pleasures-an-audio-visualizer-with-webgl

- interesting audio visualizer

https://threejs-journey.com/selection/loic-nas-de-tourris-portfolio

- i like the item disection transitions

https://tenor.com/view/initializing-ai-hud-scifi-futuristic-gif-5518067686875592350

- initialization animation

- **Codrops** (tympanus.com/codrops) - Their demos section specifically. Prototypes interaction patterns and transitions that are years ahead of what most sites ship.

https://tympanus.net/Development/ScanEffect/effect1/

- scannign effect is cool

https://tympanus.net/Tutorials/Voxelizer/

- nice animation for models

https://tympanus.net/Tutorials/webcam-audio-visualizer/index.html

- i love audio visualizers

https://artefakt.mov/

- cool text generation

- **Aristide Benoist's site** - Tasteful 3D on the web without gimmicks.
- good animations for files

- **Shaderpark gallery** - Procedural materials and effects. Good for texture and background ideas.
- the galazy background was not bad
- mostly just shapes with random shaders

- **Hic et Nunc / fxhash archives** - Generative art platforms. Artists think in visual systems, not pages. Useful for thinking about how elements behave, not just how they look.
- some weird art

- **Lusion.co** - Lab section has experimental WebGL work that matches the Tron/Iron Man vibe.
- loading screen is great
- about page zoom in and out is fire
- hologram face is prety fire

- cards is cool, maybe gambit style animation

## Movie / visual scene mining

- **Art of the Title** (artofthetitle.com) - Title sequences. Bourne credits, Westworld, Severance, Halt and Catch Fire, Ghost in the Shell.

- **Territory Studio showreel** - Holograms in Blade Runner 2049, HUDs in Avengers, UI in Ghost in the Shell. Same family as Iron Man 2.

- **Oblivion Sky Tower interior** - Clean white UI mixed with analog elements. Strong contrast.

- **The Matrix Resurrections** - Green code with particle effects. Pairs with the 2d to 3d projection idea.

- **Akira Neo-Tokyo cityscapes** - Light trails and neon. Pairs with Tron references.

## Less obvious sources

- **Shadertoy** (shadertoy.com) - Music visualizers and audio-reactive shaders. Search for audio-reactive. Directly relevant to the animation-at-each-beat idea.

- **Demoscene archives** (pouet.net) - Real-time graphics since the 90s. Constraint-driven creativity.

- **Vinyl Zoetrope records** (YouTube) - Analog-to-digital loop concept. Could work for a loading state.

- **Japanese train station departure boards** - Split-flap mechanical aesthetic. Fits GTA transition idea but grounded in reality.

- **Fighting game select screens** - Street Fighter, Tekken, Guilty Gear. Energy, character presentation, state transitions. Underused in web design. Fits Ben 10 / gaming references.

## For specific ideas from style-inspiration.md

- **Spider-Verse upside-down transition** - Zach Lieberman's openFrameworks work. Gravity-defying perspective shifts in real-time.

- **Iron Man HUD** - Search "FUI design" (Fantasy User Interface). Mark Coleran is the godfather.

- **Music-reactive node animation** - Matt DesLauriers (mattdesl on GitHub). Generative, audio-driven line work.

## Music visualization — curated board (HTML + GIFs)

- **`plans/music-visualization-inspiration.html`** — Open locally in a browser (not markdown preview) to see inline GIFs. Pulls together **non-fractal-mush** references: Patatap / Typatone, Audiograph, Chrome Spectrogram, Radio Garden, a public Three.js audio demo, Artefakt capture, Inside Music + Soundwaves (links only), Macronaut / SonoMorphis bookmarks, and **Blender** music-video / geometry-nodes talks (OK Go, Mike Hodgetts BConf 2024, etc.).
- **Done this phase:** parallel `capture-site-gif` runs per site; **`scripts/capture-site-gif.ts`** temp file is now `*.part-<pid>.gif` so FFmpeg always gets a `.gif` muxer (parallel batches were failing before).
- **Next:** optional second pass — capture **Soundwaves** or **g.co/insidemusic** if you want GIFs despite weight/VR; add any new Journey picks (e.g. “Unknown Pleasures” visualizer) as duplicate links here if you fold them into the board.

## Tympanus / Codrops board (HTML + GIFs)

- **`plans/tympanus-reference.html`** — Open locally in a browser to see inline GIF clips focused on your current direction: scan/HUD language, matrix-like particle flow, and perspective/page transition patterns.
- **Captured demos:** `ScanEffect/effect1`, `Tutorials/MatrixSentinels`, `PerspectivePageViewNavigation`, `PageTransitions`, and `TextureTransition`.
- **Done this phase:** used parallel subagent scouting on `tympanus.net` and parallel `capture-site-gif` runs to speed up discovery + capture.
- **Next:** pick 1-2 motion systems from this board as your default interaction grammar (startup scan + one transition family), then prototype those directly in your `src/components/Scene/` work.
