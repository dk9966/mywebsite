// Re-encode the exported chunk atlases (PNG) as WebP and point the manifest
// at them. The light atlases hold log-encoded data and the detail atlases
// normals: near-lossless keeps their smooth gradients from turning into
// visible steps after decoding (detail's alpha holds metallic). Albedo is
// colour and takes lossy encoding; its alpha (coverage) stays lossless.
//   node secret-base/cave-web/encode_atlases.mjs [dir]
import sharp from 'sharp';
import { readFile, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const OPTIONS = {
  albedo: { quality: 90, alphaQuality: 100, smartSubsample: true, effort: 5 },
  detail: { nearLossless: true, quality: 60, alphaQuality: 100, effort: 5 },
  light: { nearLossless: true, quality: 60, effort: 5 },
};

const dir = process.argv[2] ?? path.join(path.dirname(fileURLToPath(import.meta.url)), '../models/cave');
const manifestPath = path.join(dir, 'manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
for (const atlas of manifest.atlases) {
  for (const [key, options] of Object.entries(OPTIONS)) {
    if (!atlas[key]?.endsWith('.png')) continue;
    const source = path.join(dir, atlas[key]);
    const file = atlas[key].replace(/\.png$/, '.webp');
    const info = await sharp(source).webp(options).toFile(path.join(dir, file));
    console.log(`${atlas[key]} -> ${file} (${(info.size / 1e6).toFixed(1)} MB)`);
    await rm(source);
    atlas[key] = file;
  }
}
await writeFile(manifestPath, JSON.stringify(manifest, null, 1));
