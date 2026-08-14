// Exports the procedural secret-base world (islands + bridges, no cave
// background) to secret-base/models/world.glb.
//
// Usage: start the dev server (`pnpm dev`), then `npm run export-secret-base-world`.
// The GLB is what the site renders by default and what you edit in Blender.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const URL =
  process.env.EXPORT_URL || "http://localhost:5174/secret-base/?procedural";
const OUT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../models/world.glb",
);

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForFunction(() => typeof window.__exportWorld === "function", {
    timeout: 30000,
  });
  // let a few frames render so instanced meshes have their matrices set
  await page.waitForTimeout(2500);
  const b64 = await page.evaluate(() => window.__exportWorld());
  if (!b64) throw new Error("__exportWorld returned nothing (no 'world' group?)");
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, Buffer.from(b64, "base64"));
  const kb = (fs.statSync(OUT).size / 1024).toFixed(0);
  console.log(`wrote ${OUT} (${kb} kB)`);
} finally {
  await browser.close();
}
