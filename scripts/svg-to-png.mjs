/** Rasterize an SVG via headless Chromium: node scripts/svg-to-png.mjs in.svg out.png */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const [svgPath, pngPath] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(`file://${svgPath}`);
const dim = await page.evaluate(() => {
    const svg = document.querySelector('svg');
    return { w: +svg.getAttribute('width'), h: +svg.getAttribute('height') };
});
await page.setViewportSize({ width: dim.w, height: dim.h });
await page.screenshot({ path: pngPath });
await browser.close();
console.log(pngPath);
