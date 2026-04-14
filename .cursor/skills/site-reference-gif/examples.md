# Site reference GIF — examples

## Single site (explicit output)

```bash
pnpm exec tsx scripts/capture-site-gif.ts \
  --url "https://artefakt.mov/" \
  --out "plans/assets/artefakt-mov-capture.gif" \
  --seconds 3 \
  --settle-ms 2500 \
  --fps 12 \
  --gif-width 960
```

## Default output path (slug from URL)

```bash
pnpm exec tsx scripts/capture-site-gif.ts --url "https://threejs-journey.com/"
```

Writes `plans/assets/threejs-journey.com-capture.gif`.

## Faster page load heuristic

```bash
pnpm exec tsx scripts/capture-site-gif.ts \
  --url "https://example.com/heavy" \
  --out "plans/assets/heavy-capture.gif" \
  --wait-until domcontentloaded \
  --settle-ms 4000
```

## Shorter / lighter file

```bash
pnpm exec tsx scripts/capture-site-gif.ts \
  --url "https://example.com/" \
  --out "plans/assets/example-capture.gif" \
  --seconds 2 \
  --fps 8 \
  --gif-width 640
```

## HTML snippet (body fragment)

```html
<article class="site-ref">
  <h1 class="site-ref__title">Example — reference</h1>
  <p class="site-ref__meta">
    <strong>Site:</strong> <a href="https://example.com/">https://example.com/</a><br>
    <strong>Motion:</strong> ~3&nbsp;s loop, captured via Playwright + ffmpeg.
  </p>
  <h2 class="site-ref__section-title">Clip</h2>
  <img
    class="site-ref__shot"
    src="assets/example-capture.gif"
    alt="Example.com — short motion capture"
  >
  <p class="site-ref__caption">
    Regenerate:
    <code>pnpm exec tsx scripts/capture-site-gif.ts --url "https://example.com/" --out plans/assets/example-capture.gif</code>
  </p>
</article>
```
