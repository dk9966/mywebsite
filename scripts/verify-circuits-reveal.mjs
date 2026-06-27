/**
 * Capture the circuits-outline reveal at fixed timeline positions so we can
 * eyeball whether meshes only light up after a circuit reaches them.
 *
 *   node scripts/verify-circuits-reveal.mjs [baseUrl]
 */
import { mkdirSync } from "fs";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const baseUrl = process.argv[2] ?? "http://localhost:5174";
const url = `${baseUrl}/tron-circuits-outline.html`;
const outDir = fileURLToPath(new URL("../plans/circuit design/reveal-check/", import.meta.url));
mkdirSync(outDir, { recursive: true });

const times = [6, 11, 13, 16, 20, 26, 34];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

// Enable the scan camera (Top view on appear) so we see the panning framing.
const topView = page.locator("input.controls__checkbox").first();
if ((await topView.count()) && !(await topView.isChecked())) await topView.click();

// Pause playback so seeks hold still.
const pauseBtn = page.locator('button[title="Pause"]');
if (await pauseBtn.count()) await pauseBtn.first().click();

async function seek(t) {
  await page.evaluate((value) => {
    const el = document.querySelector(".controls__slider--time");
    if (!el) throw new Error("time slider not found");
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value",
    ).set;
    setter.call(el, String(value));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, t);
  await page.waitForTimeout(400);
}

for (const t of times) {
  await seek(t);
  const path = `${outDir}t-${String(t).padStart(2, "0")}s.png`;
  await page.screenshot({ path, timeout: 8000 });
  console.log(`wrote ${path}`);
}

await browser.close();
console.log("done");
