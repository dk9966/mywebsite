import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const outPath = path.join(root, 'plans', 'circuit-painter-obstacles.jpg');
const url = 'http://localhost:5173/circuit-painter/obstacle-sheet.html';

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(500);
const canvas = await page.$('canvas');
await canvas.screenshot({ path: outPath, type: 'jpeg', quality: 92 });
await browser.close();
console.log(outPath);
