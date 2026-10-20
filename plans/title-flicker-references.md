# Title text: appear from blank, then sit still

Two separate problems for the panel titles (Profile, Skills, Projects, Education, Experiences, Contact).

The titles today are Inter, weight 600, uppercase, tracked at `0.18em`, color `#aeeaee`. Default size is 38px (`headerFontPx` in `src/stores/deskLayout.ts`). The entrance is `boot-text-in` in `src/components/BootFx.css`: the whole word wipes in from the left, blinks opacity several times, and shifts a few pixels. The `01`–`06` tags exist on each panel in `src/components/DeskPanels.tsx` and are dropped in `HudScreen` (`tag: _tag`).

## 1. Examples of the flicker-on

The motion to match is the whole word blinking on. It is blank, then the finished word flashes a few uneven times, then it holds. Letters do not decode, type on, or rise out of a mask.

That is already the family of `boot-text-in` and `boot-diag` on the desk panels. `boot-diag` is the cleaner version of it: stepped opacity, no sideways wipe. The title version adds a left-to-right clip and a small shake, which is the part that feels off. There is no separate panels page under a projects folder in this repo. The still of these panels once the text has caught is `plans/desk-hud-reference.png`.

Open these and watch the first second. Replay if the page loops.

- [CodeFronts, neon power-on](https://codefronts.com/motion/css-text-animations/css-neon-glow-text-animation/). The diner sign. Each word ignites, stutters, then holds a steady glow. The cocktail sign above it is the other version: one letter keeps buzzing after the rest is on. The diner is the one.
- [shadcn Neon Text](https://www.shadcn.io/text/neon-text). On load, four to six blinks in under 600ms, then the word stays lit. That timing is the right length for "Experiences".
- [CrazyGL Flicker Text](https://crazygl.com/hero/flicker-text). A heading with three patterns: every letter together, letters in order, or letters at random. Styles are neon, LED, CRT, and electric. Set it to play once (`transition`, not a loop). Sequential on a short uppercase word is the closest to a panel label catching.
- [Animista, flicker-in](https://animista.net/play/entrances/flicker-in). Plays once. Useful for feeling the rhythm. The default runs long and blinks too evenly. Shorten it and make the gaps uneven.
- [GSAPify, Neon Flicker](https://gsapify.com/gsap-text-animations). Opacity jumps, then a glow. Same page has CRT Boot, which opens the whole line like a monitor. The panel glass can do that. The word itself is the neon flicker.

Clips already listed in `plans/clips-reference.html`:

- 01, Tron Title Disney Intro. Flashing lights and flickering.
- 11, Futuristic Digital Credits Reveal. Neon circuit text on black with glitch.

Film versions of the same blink, if the web demos feel too much like a diner sign:

- The TRON: Legacy trailer title flickers on. Noted in [this After Effects roundup](http://aeportal.blogspot.com/2011/01/few-tron-titles-in-after-effects.html), which also links Nick Khoo's [TRON title tutorials](https://lesterbanks.com/2011/01/creating-tron-legacy-style-titles-in-after-effects/). The useful part of those is the blink, not the 3D extrusion.
- A fan recreation of the TRON credits flicker: [youtu.be/VCfpEvZoc6c](https://youtu.be/VCfpEvZoc6c).
- Iron Man 2, the garage waking up (`plans/daddyshome.png` is the settled frame). The screens strobe on before the labels sit. Search `Iron Man 2 garage HUD wakeup`.

These look related and are a different motion. Skip them for this title:

- Letter scramble and decrypt ([GSAP ScrambleText](https://demos.gsap.com/demo/text-scrambling/), [React Bits Decrypted Text](https://reactbits.dev/text-animations/decrypted-text)).
- A typewriter that grows the string ([Motion typewriter](https://examples.motion.dev/react/typewriter)).
- Letters rising out of a clip ([Codrops stagger reveal](https://tympanus.net/codrops/2020/06/17/making-stagger-reveal-animations-for-text/)).
- A neon sign that never stops buzzing ([Silvia O'Dwyer](https://codepen.io/silvia-odwyer/pen/yLgKePK)). The title has to catch and stay.

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
