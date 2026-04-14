import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, readdir, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

type Mode = "fps" | "scene";

type CliOptions = {
  input: string;
  fps: number;
  mode: Mode;
  sceneThreshold: number;
  scale: number;
};

type FrameEntry = {
  file: string;
  timestamp: number;
};

function printUsage(): void {
  console.error(`
Usage:
  pnpm exec tsx scripts/extract-video-frames.ts --input <path> [options]

Required:
  --input            Path to video file (.mov, .mp4, etc.)

Optional:
  --fps              Frames per second (default: 4, max: 30)
  --mode             "fps" (fixed rate) or "scene" (keyframe detection) (default: fps)
  --scene-threshold  Scene change threshold 0–1 for scene mode (default: 0.03)
  --scale            Output frame width in pixels, height auto-scaled (default: 640)

Output:
  Frames are saved next to the input file in a folder named after it.
  Each frame: T00_0.00s.png, T01_0.25s.png, …
  A _manifest.json is written with frame metadata.

Requires: ffmpeg on PATH.
`);
}

function fail(msg: string): never {
  console.error(msg);
  printUsage();
  process.exit(1);
}

function parseArgs(argv: string[]): CliOptions {
  const args = argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    printUsage();
    process.exit(0);
  }
  if (args.length === 0) fail("No arguments provided.");

  let input = "";
  let fps = 4;
  let mode: Mode = "fps";
  let sceneThreshold = 0.03;
  let scale = 640;

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const next = () => {
      const v = args[++i];
      if (v == null || v.startsWith("--")) fail(`Missing value for ${a}`);
      return v;
    };
    switch (a) {
      case "--input":
        input = next();
        break;
      case "--fps":
        fps = Number(next());
        break;
      case "--mode": {
        const m = next();
        if (m !== "fps" && m !== "scene") fail(`--mode must be "fps" or "scene"`);
        mode = m as Mode;
        break;
      }
      case "--scene-threshold":
        sceneThreshold = Number(next());
        break;
      case "--scale":
        scale = Number(next());
        break;
      default:
        fail(`Unknown argument: ${a}`);
    }
  }

  if (!input) fail("--input is required.");
  input = path.resolve(input);
  if (!existsSync(input)) fail(`File not found: ${input}`);
  if (!Number.isFinite(fps) || fps < 1 || fps > 30) fail("--fps must be 1–30.");
  if (!Number.isFinite(sceneThreshold) || sceneThreshold <= 0 || sceneThreshold >= 1)
    fail("--scene-threshold must be between 0 and 1 (exclusive).");
  if (!Number.isFinite(scale) || scale < 160) fail("--scale must be >= 160.");

  return { input, fps, mode, sceneThreshold, scale };
}

function formatTs(seconds: number): string {
  return seconds.toFixed(2);
}

function frameName(index: number, timestamp: number, digits: number): string {
  return `T${String(index).padStart(digits, "0")}_${formatTs(timestamp)}s.png`;
}

async function cleanPreviousRun(dir: string): Promise<void> {
  if (!existsSync(dir)) return;
  const files = await readdir(dir);
  const stale = files.filter((f) => f.match(/^T\d+_[\d.]+s\.png$/) || f === "_manifest.json");
  for (const f of stale) await unlink(path.join(dir, f));
  if (stale.length) console.log(`Cleaned ${stale.length} files from previous run.`);
}

async function extractFps(opt: CliOptions, outDir: string): Promise<FrameEntry[]> {
  const tempPattern = path.join(outDir, "raw_%04d.png");

  execFileSync(
    "ffmpeg",
    ["-y", "-i", opt.input, "-vf", `fps=${opt.fps},scale=${opt.scale}:-1`, tempPattern],
    { stdio: ["ignore", "ignore", "inherit"] },
  );

  const rawFiles = (await readdir(outDir))
    .filter((f) => f.startsWith("raw_") && f.endsWith(".png"))
    .sort();

  const digits = Math.max(2, String(rawFiles.length - 1).length);
  const entries: FrameEntry[] = [];

  for (let i = 0; i < rawFiles.length; i++) {
    const timestamp = i / opt.fps;
    const newName = frameName(i, timestamp, digits);
    await rename(path.join(outDir, rawFiles[i]), path.join(outDir, newName));
    entries.push({ file: newName, timestamp });
  }

  return entries;
}

async function extractScene(opt: CliOptions, outDir: string): Promise<FrameEntry[]> {
  const tempPattern = path.join(outDir, "raw_%04d.png");
  const selectExpr = `gt(scene\\,${opt.sceneThreshold})+eq(n\\,0)`;

  const result = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-i",
      opt.input,
      "-vf",
      `select='${selectExpr}',showinfo,scale=${opt.scale}:-1`,
      "-vsync",
      "vfr",
      tempPattern,
    ],
    { encoding: "utf-8", maxBuffer: 50 * 1024 * 1024 },
  );

  if (result.status !== 0) {
    console.error(result.stderr?.slice(-800));
    process.exit(1);
  }

  const timestamps: number[] = [];
  const ptsRe = /pts_time:\s*([\d.]+)/g;
  let m: RegExpExecArray | null;
  while ((m = ptsRe.exec(result.stderr ?? "")) !== null) {
    timestamps.push(parseFloat(m[1]));
  }

  const rawFiles = (await readdir(outDir))
    .filter((f) => f.startsWith("raw_") && f.endsWith(".png"))
    .sort();

  const digits = Math.max(2, String(rawFiles.length - 1).length);
  const entries: FrameEntry[] = [];

  for (let i = 0; i < rawFiles.length; i++) {
    const ts = i < timestamps.length ? timestamps[i] : i;
    const newName = frameName(i, ts, digits);
    await rename(path.join(outDir, rawFiles[i]), path.join(outDir, newName));
    entries.push({ file: newName, timestamp: ts });
  }

  return entries;
}

async function main() {
  const opt = parseArgs(process.argv);

  const ext = path.extname(opt.input);
  const basename = path.basename(opt.input, ext);
  const outDir = path.join(path.dirname(opt.input), basename);

  await cleanPreviousRun(outDir);
  await mkdir(outDir, { recursive: true });

  console.log(`Input:  ${path.basename(opt.input)}`);
  console.log(`Mode:   ${opt.mode}${opt.mode === "fps" ? ` @ ${opt.fps} fps` : ` (threshold ${opt.sceneThreshold})`}`);
  console.log(`Scale:  ${opt.scale}px wide`);
  console.log(`Output: ${outDir}/\n`);

  const entries =
    opt.mode === "fps" ? await extractFps(opt, outDir) : await extractScene(opt, outDir);

  if (entries.length === 0) {
    console.error("No frames extracted. Try lowering --scene-threshold or check the input file.");
    process.exit(1);
  }

  const manifest = {
    source: opt.input,
    mode: opt.mode,
    ...(opt.mode === "fps" ? { fps: opt.fps } : { sceneThreshold: opt.sceneThreshold }),
    scale: opt.scale,
    frameCount: entries.length,
    durationSeconds: entries[entries.length - 1].timestamp,
    frames: entries,
  };

  await writeFile(path.join(outDir, "_manifest.json"), JSON.stringify(manifest, null, 2) + "\n");

  console.log(`Done: ${entries.length} frames, ${formatTs(manifest.durationSeconds)}s span.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
