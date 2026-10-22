// Screenshot /cave at the Blender render size for comparison.
//   node secret-base/cave-web/capture.mjs [out.png] [extra query, e.g. "&nohaze"]
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] ?? path.join(here, 'reference', 'three-camera.png');
const extra = process.argv[3] ?? '';
const browser = await chromium.launch({
  headless: true,
  args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1200, height: 662 }, deviceScaleFactor: 1 });
page.on('console', (m) => { if (m.type() === 'error' || m.text().startsWith('[cave]') || m.text().startsWith('[voxels]')) console.log('[page]', m.text()); });
await page.goto(`http://localhost:5174/cave?locked${extra}`);
await page.waitForFunction(() => window.__cave, null, { timeout: 60000 });
await page.waitForTimeout(Number(process.env.SETTLE ?? 6000));
await page.screenshot({ path: out });
const renderer = await page.evaluate(() => {
  const gl = document.createElement('canvas').getContext('webgl2');
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unknown';
});
console.log('captured', out, renderer);
await browser.close();
