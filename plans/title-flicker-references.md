# Current Disney title animation

The supplied screen recording's title catch is around 17–19s (the recording includes player lead-in). In the 17.0–17.25s pair, faint central letter copies blink; 17.25–17.5s introduces displaced individual letters; 17.5–17.75s spreads those letters across the title; 17.75–18s starts filling separate letters; 18–18.25s adds more bright catches; 18.25–18.5s retains a mixture of faint doubles and solid letters; 18.5–18.75s locks the word; subsequent pairs through 19.75s hold the title while the castle lighting continues. Letter changes snap rather than ease. The camera and castle stay behind the fixed title area.

`/cave-title` is a black-background preview of all six titles with the Titles controls, without the table, panels, or scene hints. It uses independent, deterministic letter catches, ghost doubles, small horizontal offsets, brief white lock flashes, and a steady cyan finish. It does not trace glyph outlines. `/cave` shares the animation without controls; `/` keeps its original title wipe and HUD tuner.

The Titles panel provides playback/restart/scrub plus Length, Catch spread, Flicker rate, Ghost strength, Jump distance, Flash length, and Glow strength sliders. Five aspect checkboxes disable letter independence, ghosts, jumps, flashes, or glow; associated sliders disable without losing their values. Reset restores all animation defaults. Values are session-only.

Browser validation: scrub back to the same time produces identical letter states; disabling letter independence synchronizes each word; disabling jumps removes offsets; disabling ghosts and glow removes shadows; the settled title remains unchanged. All three routes retain their intended controls.

The older exploration below is historical; the current per-letter behavior above supersedes its whole-word proposal.

---

# Title text: appear from blank, then sit still

Two separate problems for the panel titles (Profile, Skills, Projects, Education, Experiences, Contact).

The titles today are Inter, weight 600, uppercase, tracked at `0.18em`, color `#aeeaee`. Default size is 38px (`headerFontPx` in `src/stores/deskLayout.ts`). The entrance is `boot-text-in` in `src/components/BootFx.css`: the whole word wipes in from the left, blinks opacity several times, and shifts a few pixels. The `01`–`06` tags exist on each panel in `src/components/DeskPanels.tsx` and are dropped in `HudScreen` (`tag: _tag`).

## The Disney intro, on these panels

Clip 01 in `plans/clips-reference.html` is the TRON: Legacy Disney castle. Prologue made it (Danny Yount, castle design by Daniel Klöhn, animation including Eric Demeusy). It is not a title that types on. The castle is already the castle. Light fails to hold, catches, drops out, and then the drawing stays lit. People describe that as the castle rezzing up.

The desk panels already rez. During `flickerFill`, `panelBootVisual` in `src/lib/bootSequence.ts` samples `bootNoise` about every 33ms. Most samples leave the glass nearly dark. A sample above 0.66 flashes the fill. A sample above 0.78 flashes the edge. When the window ends, the glass eases up and holds. Each panel has its own seed, so they do not blink together. That is the projects-panel version of the same catch.

The title should be one more thing on that catch, not its own wipe.

1. The word is in its final place the whole time. No clip, no tracking change, no per-letter scramble. A faint copy (opacity around 0.08) can sit there first, the way the castle is a line drawing before the light holds.
2. While that panel is inside `flickerFill`, the title opacity comes from the same `bootNoise(elapsed, seed)` as the glass. Dim by default. A high sample snaps it to full, one sample even brighter than the resting color (near white), then it drops out again.
3. One sample in that window may shift the word 1px sideways. One sample. Then it is back. That is the tear in the castle's light, not a shake loop.
4. When `flickerFill` ends, opacity is 1 and the offset is 0. A single late dropout is allowed while the bezel draws (`n > 0.92` already does this to the bezel). After that, the word does not move.
5. Do not run this on a second clock. If the glass flashes and the word flashes on different frames, it reads as two effects. `BootClockDriver` already publishes `--boot-elapsed`. The title can read the same noise in that driver instead of the hand-authored blinks inside `boot-text-in`.

`boot-text-in` is the part to replace. It wipes from the left and eases between blinks. The castle and the glass both hold a state until the next sample. `steps()` on the keyframes, or writing opacity from `bootNoise`, is the rendition. A new CSS animation with eased fades is the diner sign, which is a cousin, not this.

## Watch the castle, then the cousins

The ident itself:

- [Disney Castle, TRON Legacy intro](https://www.youtube.com/watch?v=lNXFJXmkLJ0). The clip the page is named after.
- [Ident Gallery, Walt Disney / Tron Legacy (2010)](https://theident.gallery/player.php/FILM-VIDEO-ID-DISNEY-2010-TRONLEGACY-1). About 24 seconds.
- [Eric Demeusy, castle stills](http://www.ericdemeusy.com/tronlegacy). He animated it. The line "the castle rezzes up" is quoted on that page.
- [OTAS, Disney castle](https://otas.tv/work/tronlegacy/). Same Prologue sequence, plus the end credits.
- [Danny Yount on the castle and the type](https://www.artofvfx.com/tron-legacy-prologue-films/). The castle was pushed from the normal flying Disney logo into a Tron drawing. The end credits were supposed to be type only, and Klöhn's type was built to feel like the Grid.
- [Daniel Klöhn, TRON Legacy](https://cargocollective.com/danielkloehn/TRON-LEGACY). The end-credit type. Letters behave like light on the Grid, which is the text version of the castle.
- [Prologue, Tron Legacy](https://prologue.com/portfolio-item/tron-legacy/).

Same catch, other films and clips:

- [GMUNK, TRON opening titles](https://gmunk.com/TRON-Opening-Titles). Not the castle. Light walls resolving into a city. Same rule: the drawing is decided, the light is what arrives.
- Clip 11 in `plans/clips-reference.html`, Futuristic Digital Credits Reveal.
- Rinzler at the end of the film: the red lights go out, then the white lights flicker back on. Written up in the [scene notes](https://tron.popapostle.com/html/episodes/Legacy.htm). A program catching, then holding.
- Iron Man 2 garage (`plans/daddyshome.png`). Prologue was on those holograms in the same year. The screens strobe, then the labels are just there.
- A fan TRON credits flicker: [youtu.be/VCfpEvZoc6c](https://youtu.be/VCfpEvZoc6c). Nick Khoo's [title tutorials](https://lesterbanks.com/2011/01/creating-tron-legacy-style-titles-in-after-effects/) are the homemade version. Use the blink. Leave the extruded 3D letters.

Flat type that ignites and then holds. Useful for timing, softer than the castle:

- [CodeFronts, diner power-on](https://codefronts.com/motion/css-text-animations/css-neon-glow-text-animation/). Words stutter, then a steady glow. The cocktail sign above it keeps buzzing. That buzz is the failure mode.
- [shadcn Neon Text](https://www.shadcn.io/text/neon-text). A handful of blinks, under 600ms, then lit.
- [CrazyGL Flicker Text](https://crazygl.com/hero/flicker-text). Play once, all letters together.
- [Animista, flicker-in](https://animista.net/play/entrances/flicker-in). The default is too even. The castle's gaps are irregular, which is what `bootNoise` already is.
- [GSAPify, Neon Flicker](https://gsapify.com/gsap-text-animations).

Skip for this rendition: scramble and decrypt, a typewriter that grows the string, letters rising out of a mask, and any neon that never stops buzzing ([this pen](https://codepen.io/silvia-odwyer/pen/yLgKePK) is the loop). A sliced RGB glitch that keeps running ([Codrops](https://tympanus.net/codrops/2017/12/21/css-glitch-effect/)) is a broken signal. The castle finishes resolving.

## 2. How the title looks after it appears

Once the blinks stop, nothing on the word moves. No scanline, no glow pulse, no chromatic fringe. The panel can keep breathing. The title is a label that has finished its job. The settled frame to match is `plans/desk-hud-reference.png`: small uppercase, wide tracking, cyan, sitting in the top of the glass.

### The row

```
05   EXPERIENCES
     ▔▔▔▔▔▔▔▔▔▔▔
```

- Index, then the word. The index is the same face, tabular numbers, dimmer (around half the title color). The tags `01`–`06` are already in the panel data. They are the index. They are not rendered.
- The word is uppercase. Sentence case turns it into a website heading.
- A 1px hairline under the word only, in the title color at low opacity. It does not run the full panel width. Corner brackets stay on the panel, not on the word.
- The title is the brightest text on the glass. Body copy stays the quieter `#cfe8ec`. The title stays near `#aeeaee`. Pure `#00ffff` plus a fat text-shadow blooms into a neon sign at 38px. If it needs glow, one soft shadow in the same hue is enough, and it does not animate.

### The face

Inter is a UI body face. It is a good choice for the panel copy and a soft choice for the label. Film and game labels use a squared or condensed sans, medium weight, so the letters look machined and still read at a glance.

What the references actually set:

- The sci-fi default since *2001* is Eurostile Bold Extended, or its uppercase parent Microgramma. [Typeset in the Future](https://typesetinthefuture.com/2014/01/31/2001-a-space-odyssey/) and the [trope page](https://tvtropes.org/pmwiki/pmwiki.php/Main/TypesetInTheFuture) track it through HAL, Moon, Star Trek markings. It is wide. At 38px with `0.18em` tracking it will feel like a poster, not a label. If the face is extended, pull tracking down toward `0.06em`–`0.1em`.
- Oblivion did not put Eurostile on the screens. The UI face is Blender (Nick Thoenen). Titles, ship livery, and the light table use DC TET, drawn by Dianne Chadwick and [Jens Gehlhaar](https://jensgehlhaar.com/Oblivion-Custom-typeface-design-for-Joseph-Kosinski-s-science-fiction). Gehlhaar aimed it at Aldo Novarese's Stop and the NASA worm, not at Eurostile. [Interface Love's UI review](https://ilikeinterfaces.com/2015/04/21/ui-review-oblivion/) is the still gallery: thin rules, a grid, desaturated blue and orange, saturated color only for warnings. GMUNK's brief, quoted in the [ProVideo write-up](https://www.provideocoalition.com/hud-and-gui-graphics-in-oblivion/), was function and a palette that works on both a dark and a bright ground. That is the settled look to copy: a label you can read, not a glowing sign.
- Cyberpunk 2077 sets almost the entire UI in Rajdhani (Regular through Bold) and uses Orbitron only as a secondary accent. [Fonts In Use](https://fontsinuse.com/uses/60926/cyberpunk-2077-video-game). Rajdhani is the one to steal for a narrow panel. Orbitron is the one to leave for a single display word, if at all. Its shapes are slow to read.

Free faces that hold up as a short uppercase label:

- [Chakra Petch](https://freefont.now/font/chakra-petch). Squared, chamfered, full weights. The usable Eurostile-like. Medium or SemiBold. Tracking about `0.08em`–`0.12em` at 38px, because the face is already wide.
- Rajdhani Medium or SemiBold. Condensed, so "Experiences" fits a narrow panel. Tracking can stay closer to `0.12em`–`0.16em`. This is the practical pick if the header has to share the row with the minimize control.
- Barlow Condensed SemiBold. Quieter, DIN-like, more instrument than game logo. Same tracking note as Rajdhani.
- Share Tech Mono only if the title should look like a terminal readout. Monospace plus `0.18em` is very wide and starts to look like a costume. Mono is the right face for the index and for any ticking numbers, not automatically for the word.

Weight stays 500–600. Black weights close the counters. Below about 13px, condensed all-caps gets hard to read, so if the header is scaled down in the tuner, ease the tracking back toward `0.08em`.

### Settled-label stills

Motion sites will not show this. These will:

- [Interface Love, Oblivion](https://ilikeinterfaces.com/2015/04/21/ui-review-oblivion/). Typography section. Look at how little the labels do after they are on.
- [Jens Gehlhaar, DC TET](https://jensgehlhaar.com/Oblivion-Custom-typeface-design-for-Joseph-Kosinski-s-science-fiction). The title face, and why a "future" font that fights the set design gets thrown out.
- [HUDS+GUIS](https://www.hudsandguis.com/). TRON Legacy, Ghost in the Shell, Andor, Silo. Read the labels, ignore the frames.
- [Interface In Game](https://interfaceingame.com/). Filter Overlay, Loading, Stats. How a one-line header is set: index, tracking, a hairline.
- [smui](https://smui.statico.io/). The label recipe there is uppercase, about 11px, tracking `1.5px`, weight 400–600, hard edges. Small, but the hierarchy is right: the label is quieter than the stat.
- [Muriel, FUI grammar](https://muriel.mindbendingpixels.com/vocabularies/fui/). One face, tabular numbers, glow as punctuation. The failure list matches the current title: mushy type, and contrast that dips while the opacity animation is running.
- [usva Section Label](https://usva.build/docs/components/section-label). Not sci-fi. It is the row: mono index, title, hairline, trailing aside. That is the structure, without the costume.

## What to ignore for these two questions

- Panel boot clips (radar, hologram frames, visor arcs). They show a screen turning on. They do not show the word.
- Godly, Land-book, Refero, Mobbin. Product-page stills. Mobbin's motion search needs a paid plan.
- Awwwards marquees and scroll type. [Infinite Field](https://www.awwwards.com/inspiration/decoding-the-signal-text-scramble-sequence-infinite-field) and [Monospace hover scramble](https://www.awwwards.com/inspiration/scramble-text-on-hover-monospace) are the exceptions, and they are decode-on-hover, not a label settling.
- Envato and Motion Array "sci-fi HUD intro" logo stings. Particle circles. The Tracking and Opacity preset above is the useful Motion Array page.

## Searches

For the entrance:

- `text animator opacity range selector`
- `HUD label text reveal characters`
- `scramble text fixed width monospace`
- `typewriter reveal from empty string cursor`

For the settled label:

- `Eurostile HUD label`
- `Oblivion Blender DC TET typography`
- `Rajdhani UI uppercase tracking`
- `FUI section label index hairline`
