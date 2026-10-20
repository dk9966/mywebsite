# Title flicker references

Sources for the panel titles (About me, Experiences, and the rest). The current reveal wipes the whole word in from the left, blinks its opacity several times, and nudges it sideways a few pixels. That reads as a lightbulb buzzing.

A panel label does one small event to the letters, then holds. The blink is the last beat, not the whole performance.

Direction to try after looking: a short decode on the letters, a single bright pass, and one opacity dip as it locks. Short words die if the scramble runs for seconds. Film labels are a few frames of noise, then still.

## Watch these first

### Letter lock

Random glyphs churn, then the real letters settle left to right. This is the motion that reads as a system naming the panel. Keep it short on a two-word title, or it turns into a loading gag. Monospace (or a fixed width) stops the word from reflowing while glyphs change.

- [GSAP text scrambling](https://demos.gsap.com/demo/text-scrambling/) and the [ScrambleText docs](https://gsap.com/docs/v3/Plugins/ScrambleTextPlugin/). The live demo is the cleanest version of the effect.
- [React Bits, Decrypted Text](https://reactbits.dev/text-animations/decrypted-text). Same idea, with a preview you can slow down.
- [React Bits, Glitch Text](https://reactbits.dev/text-animations/glitch-text). The RGB-split cousin. Useful as a one-frame hitch at the end, not as the reveal itself.
- [Infinite Field, "Decoding the Signal"](https://www.awwwards.com/inspiration/decoding-the-signal-text-scramble-sequence-infinite-field). Awwwards element page with the clip.
- [Monospace, scramble on hover](https://www.awwwards.com/inspiration/scramble-text-on-hover-monospace).
- [chaingpt.org](https://www.chaingpt.org/). The smooth hover version people keep citing. The type is Roboto Mono, so the width stays put.

### One scan, then a settle

A bright bar crosses the word and the letters are already there behind it. One brightness dip at the end, then still. This is the upgrade of the wipe already in `boot-text-in`.

- [velements HUD set](https://velements.store/transitions/hud). Open these and watch the first half-second of the label. Ignore the long loops.
  - HUD Callout: a label types out after a leader line.
  - Hologram Panel: the panel flickers on once.
  - Boot Sequence.
  - Target Lock.
- [VISAR Animation Lab](https://visar-animations-lab.vercel.app/). Boot lines, status checks, and a pulse. Each card has the source, so the timing is visible, not just the look.
- [Codrops CSS glitch](https://tympanus.net/codrops/2017/12/21/css-glitch-effect/). Sliced `clip-path` offsets. Used once, for about 80ms, it is a hitch. Left running, it is the cheap flicker.

### The line blooms open

The text starts as a hairline, opens, overshoots brightness, dips once, and holds. Closer to a CRT than to a strobe.

- [GSAPify text animations](https://gsapify.com/gsap-text-animations). On one page, Neon Flicker is the opacity strobe already in the titles. CRT Boot is the version where the screen opens and the text arrives once.
- [Animista, entrances](https://animista.net/play/entrances). Search flicker. Useful as a timing toy. The preset itself runs too long and blinks too often for a panel title.

## Film and game HUDs

Short labels in films almost never strobe the whole word. A rule or a set of brackets draws, the word resolves, and it sits.

- [HUDS+GUIS](https://www.hudsandguis.com/) is the archive. Start with [TRON Legacy](https://www.hudsandguis.com/home/2011/04/19/tron-legacy-ui), then Ghost in the Shell, Andor, and Silo. Newer posts are the restrained ones: type appears because a function turned on.
- Oblivion is the closest match to the glass panels.
  - [Joseph Chan's breakdown](https://cargocollective.com/josephchan/Oblivion)
  - [Drone HUD notes](https://scifiinterfaces.com/2015/02/24/the-drone/)
  - [GMUNK team write-up](https://www.provideocoalition.com/joseph-kosinskis-film-oblivion-showcases-elegant-effects-created-with-adobe/). Flat vectors in Illustrator and After Effects. Callouts pop on and stay readable.
- Iron Man's first HUD is the other pole: widgets that change mode, labels that exist because Tony looked at something. Cyan, functional. [Oral history on vfxblog](https://vfxblog.com/ironman/).
- [Interface In Game](https://interfaceingame.com/). Stills and some video. Filter Overlay, Loading, and Stats. Good for how a one-line label is set (tracking, a tag number, a hairline rule). Weak for timing.
- [Art of the Title, Westworld](https://www.artofthetitle.com/title/westworld/). Also TRON Legacy and Ghost in the Shell. These are sequences, not panel titles. Watch for the moment a word locks, then leave.

Paid, and worth it only for the craft behind the clips:

- [Ash Thorp, HUD Design](https://www.learnsquared.com/courses/hud-design)
- [Ryan Cashman, HUD Animation](https://www.learnsquared.com/courses/hud-animation)

Student boot studies from those courses show up on YouTube. Search `HUD boot sequence text` and `FUI text reveal`.

## Searches that hit

Paste these on YouTube and Vimeo:

- `FUI text reveal`
- `HUD callout label animation`
- `sci-fi UI boot sequence typography`
- `CRT text power on`
- `terminal decode text animation`

On Codrops, stay inside the [typography hub](https://tympanus.net/codrops/hub/tag/typography/) and the glitch tag.

## Skip for this

These will not show a Tron panel title coming online:

- Godly, Land-book, Refero, and Mobbin. Layout stills of real products. Mobbin's motion search needs a paid plan.
- Awwwards homepage collections. Scroll type and marquees. Use the element clips linked above.
- Magic UI text presets. Blur and slide.
- Envato and Motion Array "sci-fi HUD intro" templates. Particle logo stings. If a preview is open, only the first half-second of the label is useful.

## Where this sits in the boot

The title keyframes are `boot-text-in` in `src/components/BootFx.css`, driven by the `titleReveal` part in `src/lib/bootParts.ts`.
