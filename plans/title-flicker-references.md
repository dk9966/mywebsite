# Title text: appear from blank, then sit still

Two separate problems for the panel titles (Profile, Skills, Projects, Education, Experiences, Contact).

The titles today are Inter, weight 600, uppercase, tracked at `0.18em`, color `#aeeaee`. Default size is 38px (`headerFontPx` in `src/stores/deskLayout.ts`). The entrance is `boot-text-in` in `src/components/BootFx.css`: the whole word wipes in from the left, blinks opacity several times, and shifts a few pixels. The `01`–`06` tags exist on each panel in `src/components/DeskPanels.tsx` and are dropped in `HudScreen` (`tag: _tag`).

## 1. How the title appears from blank

The letters should already own their final positions. The word does not grow, slide, or blink as one block. A caret walks left to right. Only the letter under the caret is unstable. Then the word holds.

That is the label reveal used on film HUDs. In After Effects it is an opacity animator driven by a range selector: opacity on the animator is 0, and the selector's end runs from 0% to 100%, so characters turn on in order. Adobe's own write-up of that setup is [Animating text in After Effects](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html). The short preset people copy is [Tracking and Opacity](https://blog.motionarray.com/learn/after-effects/free-after-effects-text-animation-presets/) (Motion Array). Use the opacity half. Leave tracking alone during the reveal, or the header width jumps while the panel is booting.

### The pass

1. The title is in the DOM at full size, final tracking, opacity 0 per character. Blank, but the slot is reserved, so nothing reflows when letters arrive.
2. A caret (a 1px bar, or the next glyph flashing) moves one character at a time.
3. The character under the caret gets one hitch: a single random glyph, or a brightness spike, for one or two frames. Then the real letter at full opacity.
4. Earlier letters stay still. They do not keep flickering.
5. When the last letter locks, the whole word dips once (about 0.7 opacity) and returns to 1. That dip is the only moment the finished word blinks.

Duration is per character, about 30–40ms. "Skills" is roughly a fifth of a second. "Experiences" is roughly 400ms. Cap the whole title near 450ms so a long word does not lag the boot. The charset for the hitch should be short and square: `01`, or a few block glyphs. A full alphabet makes the header look like a captcha.

### Where to watch this exact motion

These are text entrances from blank or from noise in the letter boxes. They are not panel boots.

- [Framer Scramble Label](https://www.framer.com/marketplace/components/scramble-label/). Each glyph is drawn on top of the letter it replaces, so the line never reflows and the end state is the typed word. Triggers include on load. This is the closest live control for "from blank, into the final boxes."
- [Motion scramble text](https://motion.dev/docs/text-animation) and the live [scramble example](https://examples.motion.dev/react/scramble-text-hover). Same docs page has the [typewriter](https://examples.motion.dev/react/typewriter), which appends characters onto an empty string. That grows the label. Fine for a terminal line. Wrong for a header that has to stay put.
- [Scrambl recipes](https://scrambl.vikingz.me/examples/recipes/). The typewriter recipe starts from an empty override and reveals left to right with a block cursor. The password-mask recipe reveals through a stand-in glyph. Both start from blank.
- [GSAP ScrambleText](https://gsap.com/docs/v3/Plugins/ScrambleTextPlugin/) and the [demo](https://demos.gsap.com/demo/text-scrambling/). Left-to-right lock. `revealDelay` is the beat of pure noise before letters commit. Keep that beat under ~80ms on a title or it becomes a loading gag. [React Bits Decrypted Text](https://reactbits.dev/text-animations/decrypted-text) is the same idea with a sequential, start-to-end mode you can slow down.
- [GSAPify, CRT Boot next to Neon Flicker](https://gsapify.com/gsap-text-animations). Neon Flicker is the opacity strobe already in `boot-text-in`. CRT Boot is a line opening once. Steal the single settle from CRT Boot, not the strobe.

### Entrances that are about text, and still the wrong text

- [Codrops stagger reveal](https://tympanus.net/codrops/2020/06/17/making-stagger-reveal-animations-for-text/) (the Dani Morales / Thibaud Allie letter rise). Letters clip up from a mask. That is an editorial about-page. It reads as a portfolio heading, not a system naming a panel.
- [Codrops kinetic type transition](https://tympanus.net/codrops/2021/09/29/kinetic-typography-page-transition/). Words rotate and scale. Too large for a 38px header.
- [React Bits Glitch Text](https://reactbits.dev/text-animations/glitch-text) and [Codrops CSS glitch](https://tympanus.net/codrops/2017/12/21/css-glitch-effect/). A one-frame RGB split on the caret is enough. A looping slice glitch is the cheap flicker.
- Magic UI blur and slide. Marketing entrance. The word is never blank in a mechanical sense. It is just out of focus.

## 2. How the title looks after it appears

Once the caret is gone, nothing on the word moves. No scanline, no glow pulse, no chromatic fringe. The panel can keep breathing. The title is a label that has finished its job.

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
