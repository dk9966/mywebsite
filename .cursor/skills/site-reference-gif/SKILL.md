---
name: site-reference-gif
description: >-
  Captures a configurable-length silent GIF from any URL with headless Chromium
  (Playwright) and ffmpeg, then embeds it in a small standalone HTML reference
  page next to notes. Use when building inspiration assets, reference boards,
  parallel batch captures of many sites, or when the user asks for site GIFs,
  motion captures, or HTML embeds for local previews.
---

# Site reference GIF + HTML companion

## Prerequisites

- **pnpm** (this repo): `playwright` and **system `ffmpeg`** on `PATH`.
- One-time Chromium: `pnpm exec playwright install chromium`
- Heavy or streaming pages: try `--wait-until domcontentloaded` and tune `--settle-ms`.

## Capture (CLI)

Run from repo root:

```bash
pnpm run capture-site-gif -- --url "https://example.com/" --out "plans/assets/example-capture.gif" --seconds 3
```

Omit `--out` to write `plans/assets/<host-slug>-capture.gif` (derived from the URL).

Useful flags: `--seconds`, `--settle-ms`, `--fps`, `--viewport-w`, `--viewport-h`, `--gif-width`, `--wait-until`, `--frames-dir`. See full list:

```bash
pnpm exec tsx scripts/capture-site-gif.ts --help
```

### Parallel / many sites

Each run allocates its **own** frames directory under `plans/assets/.tmp-site-gif-*` and deletes it after ffmpeg. Safe to run many captures **at once** as long as each process uses a **distinct `--out`** path.

Example:

```bash
pnpm exec tsx scripts/capture-site-gif.ts --url "https://a.example/" --out plans/assets/a-capture.gif &
pnpm exec tsx scripts/capture-site-gif.ts --url "https://b.example/" --out plans/assets/b-capture.gif &
wait
```

Optional: fixed `--frames-dir` for debugging (avoid parallel reuse of the same dir).

## HTML companion (embed + text)

1. Put the GIF under `plans/assets/` (or a subfolder). Keep the HTML under `plans/` so a relative `src` like `assets/<name>.gif` resolves.
2. Use **BEM** class names for page layout (e.g. `site-ref`, `site-ref__title`, `site-ref__meta`, `site-ref__shot`, `site-ref__caption`).
3. Inline **critical** copy in the HTML (title, URL, bullets, how the clip was captured). Link the live site with `https://`.
4. In `site-ref__caption`, note the GIF path, optional still frame, and the exact regenerate command.

Template:

```html
<!-- plans/<slug>-reference.html — open in a browser for inline GIF -->
<img class="site-ref__shot" src="assets/<slug>-capture.gif" alt="<short description>">
```

Markdown preview in editors often blocks local media; the HTML file is the reliable **inline** view.

## Conventions in this repo

- GIF output: `plans/assets/<slug>-capture.gif`
- Optional still: `plans/assets/<slug>-screenshot.png` (separate process / manual)
- Ephemeral frames are gitignored: `plans/assets/.tmp-site-gif-*/`
- Preset: `pnpm run capture-artefakt-gif` fixes URL + `plans/assets/artefakt-mov-capture.gif` for quick regenerates.

## Tradeoffs

- **GIF size**: lower `--gif-width` or `--fps` if files are too large.
- **Faithfulness**: headless output can differ from a user’s real browser; note that in the HTML caption when it matters.

## Examples

See [examples.md](examples.md).
