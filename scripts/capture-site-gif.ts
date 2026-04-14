import { execFileSync } from "node:child_process";
import { mkdtemp, mkdir, rm, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, type WaitUntilState } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const ASSETS_DIR = path.join(ROOT, "plans", "assets");

type CliOptions = {
  url: string;
  outGif: string;
  seconds: number;
  settleMs: number;
  fps: number;
  viewportWidth: number;
  viewportHeight: number;
  gifWidth: number;
  waitUntil: WaitUntilState;
  /** If set, use this dir for PNG frames (caller must ensure uniqueness for parallel runs). */
  framesDir: string | null;
};

function printUsage(): void {
  console.error(`
Usage:
  pnpm exec tsx scripts/capture-site-gif.ts --url <https://...> [--out <path>] [options]

Required:
  --url              Page to capture

Optional:
  --out              Output .gif path (default: plans/assets/<host-slug>-capture.gif)
  --seconds          Clip length in seconds (default: 3)
  --settle-ms        Wait after load before first frame (default: 2500)
  --fps              Frames per second (default: 12)
  --viewport-w       Browser width (default: 1280)
  --viewport-h       Browser height (default: 720)
  --gif-width        Max GIF width; height scales (default: 960)
  --wait-until       load | domcontentloaded | commit (default: load)
  --frames-dir       Fixed frames directory (must not exist or be empty).
                     For parallel captures, omit this to auto-create a unique temp dir under plans/assets/.

Requires: playwright (Chromium), ffmpeg on PATH.
`);
}

function usage(code: number): never {
  printUsage();
  process.exit(code);
}

function parseArgs(argv: string[]): CliOptions {
  const args = argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    printUsage();
    process.exit(0);
  }
  if (args.length === 0) usage(1);

  let url = "";
  let outGif = "";
  let seconds = 3;
  let settleMs = 2500;
  let fps = 12;
  let viewportWidth = 1280;
  let viewportHeight = 720;
  let gifWidth = 960;
  let waitUntil: WaitUntilState = "load";
  let framesDir: string | null = null;

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const next = () => {
      const v = args[++i];
      if (v == null || v.startsWith("--")) usage(1);
      return v;
    };
    switch (a) {
      case "--url":
        url = next();
        break;
      case "--out":
        outGif = next();
        break;
      case "--seconds":
        seconds = Number(next());
        break;
      case "--settle-ms":
        settleMs = Number(next());
        break;
      case "--fps":
        fps = Number(next());
        break;
      case "--viewport-w":
        viewportWidth = Number(next());
        break;
      case "--viewport-h":
        viewportHeight = Number(next());
        break;
      case "--gif-width":
        gifWidth = Number(next());
        break;
      case "--wait-until": {
        const w = next();
        if (w !== "load" && w !== "domcontentloaded" && w !== "commit") usage(1);
        waitUntil = w;
        break;
      }
      case "--frames-dir":
        framesDir = path.resolve(ROOT, next());
        break;
      default:
        console.error("Unknown argument:", a);
        usage(1);
    }
  }

  if (!url) usage(1);
  try {
    new URL(url);
  } catch {
    console.error("Invalid --url");
    usage(1);
  }

  if (!outGif) {
    outGif = path.join(ASSETS_DIR, `${hostSlug(new URL(url))}-capture.gif`);
  } else {
    outGif = path.resolve(ROOT, outGif);
  }

  if (!Number.isFinite(seconds) || seconds <= 0) usage(1);
  if (!Number.isFinite(settleMs) || settleMs < 0) usage(1);
  if (!Number.isFinite(fps) || fps < 1) usage(1);
  if (!Number.isFinite(gifWidth) || gifWidth < 160) usage(1);

  return {
    url,
    outGif,
    seconds,
    settleMs,
    fps,
    viewportWidth,
    viewportHeight,
    gifWidth,
    waitUntil,
    framesDir,
  };
}

function hostSlug(url: URL): string {
  const host = url.hostname.replace(/^www\./i, "");
  const tail = url.pathname === "/" ? "" : url.pathname.replace(/\//g, "-");
  const raw = tail ? `${host}${tail}` : host;
  return raw
    .replace(/[^a-z0-9.-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 96) || "site";
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

async function main() {
  const opt = parseArgs(process.argv);

  await mkdir(ASSETS_DIR, { recursive: true });

  let framesDir = opt.framesDir;
  let ownTemp = false;
  if (!framesDir) {
    framesDir = await mkdtemp(path.join(ASSETS_DIR, ".tmp-site-gif-"));
    ownTemp = true;
  } else {
    await mkdir(framesDir, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: opt.viewportWidth, height: opt.viewportHeight },
  });

  try {
    await page.goto(opt.url, { waitUntil: opt.waitUntil, timeout: 90_000 });
    await sleep(opt.settleMs);

    const interval = 1000 / opt.fps;
    const frameCount = Math.max(2, Math.round(opt.seconds * opt.fps));

    for (let i = 0; i < frameCount; i++) {
      const file = path.join(framesDir!, `frame-${String(i).padStart(4, "0")}.png`);
      await page.screenshot({ path: file, type: "png" });
      await sleep(interval);
    }
  } finally {
    await browser.close();
  }

  await mkdir(path.dirname(opt.outGif), { recursive: true });

  const vf = [
    `fps=${opt.fps}`,
    `scale=${opt.gifWidth}:-1:flags=lanczos`,
    "split[s0][s1]",
    "[s0]palettegen=reserve_transparent=0:stats_mode=single[p]",
    "[s1][p]paletteuse=dither=bayer:bayer_scale=5",
  ].join(",");

  // FFmpeg infers the muxer from the file extension; `out.gif.part-123` breaks that.
  const tmpOut = `${opt.outGif}.part-${process.pid}.gif`;
  execFileSync(
    "ffmpeg",
    [
      "-y",
      "-framerate",
      String(opt.fps),
      "-i",
      path.join(framesDir!, "frame-%04d.png"),
      "-vf",
      vf,
      "-loop",
      "0",
      tmpOut,
    ],
    { stdio: "inherit", cwd: ROOT },
  );
  await rename(tmpOut, opt.outGif);

  if (ownTemp) await rm(framesDir!, { recursive: true, force: true });

  console.log("Wrote", path.relative(ROOT, opt.outGif));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
