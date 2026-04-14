import { execFileSync } from "node:child_process";
import { readdir, readFile, rename, stat, watch, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

type ClipMeta = {
  fileName: string;
  title: string;
  description: string;
};

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const CLIPS_DIR = path.join(ROOT, "plans", "clips");
const HTML_PATH = path.join(ROOT, "plans", "clips-reference.html");
const ENV_PATH = path.join(ROOT, ".env");
const OPENAI_ENDPOINT = "https://api.openai.com/v1/responses";
const MODEL = "gpt-4.1-mini";
const POLL_MS = 4000;
const RETRY_COOLDOWN_MS = 60_000;
const MAX_ATTEMPTS_PER_CLIP = 2; // first try + one retry
const FRAME_SAMPLES_PER_CLIP = 10;

async function loadEnvFromFile(): Promise<void> {
  let raw = "";
  try {
    raw = await readFile(ENV_PATH, "utf8");
  } catch {
    // It's fine if .env does not exist.
    return;
  }

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;
    const [, key, valueRaw] = match;
    let value = valueRaw.trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = value;
  }
}

function mustGetApiKey(): string {
  const apiKey = process.env.OPENAI_API_KEY?.trim();
  if (!apiKey) {
    throw new Error(
      "Missing OPENAI_API_KEY. Put it in .env at repo root: OPENAI_API_KEY=sk-...",
    );
  }
  return apiKey;
}

function parseClipsData(html: string): ClipMeta[] {
  const match = html.match(
    /<script id="clips-data" type="application\/json">([\s\S]*?)<\/script>/,
  );
  if (!match) {
    throw new Error(
      'Could not find <script id="clips-data" type="application/json"> in plans/clips-reference.html',
    );
  }

  const jsonText = match[1].trim();
  const parsed = JSON.parse(jsonText) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("clips-data must be a JSON array.");
  }

  return parsed.filter((item): item is ClipMeta => {
    if (!item || typeof item !== "object") return false;
    const candidate = item as Partial<ClipMeta>;
    return (
      typeof candidate.fileName === "string" &&
      typeof candidate.title === "string" &&
      typeof candidate.description === "string"
    );
  });
}

function renderClipsData(clips: ClipMeta[]): string {
  // Escape < so embedded JSON never accidentally closes the script tag.
  return JSON.stringify(clips, null, 2).replaceAll("<", "\\u003c");
}

function updateHtmlWithClips(html: string, clips: ClipMeta[]): string {
  const rendered = renderClipsData(clips);
  return html.replace(
    /<script id="clips-data" type="application\/json">([\s\S]*?)<\/script>/,
    `<script id="clips-data" type="application/json">\n${rendered}\n    </script>`,
  );
}

const VIDEO_EXTENSIONS = new Set([".mov", ".mp4"]);

function isVideoFile(name: string): boolean {
  return VIDEO_EXTENSIONS.has(path.extname(name).toLowerCase());
}

async function listVideoFiles(): Promise<string[]> {
  const entries = await readdir(CLIPS_DIR, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && isVideoFile(entry.name))
    .map((entry) => entry.name)
    .sort();
}

function getDurationSeconds(filePath: string): number {
  const output = execFileSync(
    "ffprobe",
    [
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=noprint_wrappers=1:nokey=1",
      filePath,
    ],
    { encoding: "utf8" },
  ).trim();
  const duration = Number(output);
  if (!Number.isFinite(duration) || duration <= 0) {
    throw new Error(`ffprobe returned invalid duration for ${path.basename(filePath)}: ${output}`);
  }
  return duration;
}

function extractFramePng(filePath: string, atSeconds: number): Buffer {
  const pngBuffer = execFileSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-ss",
      atSeconds.toFixed(2),
      "-i",
      filePath,
      "-frames:v",
      "1",
      "-f",
      "image2pipe",
      "-vcodec",
      "png",
      "pipe:1",
    ],
    { encoding: "buffer", maxBuffer: 20 * 1024 * 1024 },
  );
  if (!pngBuffer.length) {
    throw new Error(`Failed to extract frame for ${path.basename(filePath)} at ${atSeconds}s`);
  }
  return pngBuffer;
}

function evenlySampleTimes(duration: number, count: number): number[] {
  if (count <= 1) return [Math.max(0, duration * 0.5)];
  // Sample from the center of each segment for even coverage and stability.
  const segment = duration / count;
  return Array.from({ length: count }, (_, idx) =>
    Math.max(0, Math.min(duration, segment * (idx + 0.5))),
  );
}

function parseMetadataText(raw: string): { title: string; description: string } {
  const firstBrace = raw.indexOf("{");
  const lastBrace = raw.lastIndexOf("}");
  if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) {
    throw new Error(`Model response was not JSON: ${raw}`);
  }
  const jsonText = raw.slice(firstBrace, lastBrace + 1);
  const parsed = JSON.parse(jsonText) as Record<string, unknown>;
  const title = typeof parsed.title === "string" ? parsed.title.trim() : "";
  const description = typeof parsed.description === "string" ? parsed.description.trim() : "";
  if (!title || !description) {
    throw new Error(`Model returned invalid metadata JSON: ${jsonText}`);
  }
  return { title, description };
}

function extractResponseText(data: unknown): string {
  if (!data || typeof data !== "object") return "";
  const record = data as Record<string, unknown>;
  if (typeof record.output_text === "string" && record.output_text.trim()) {
    return record.output_text;
  }

  const output = record.output;
  if (!Array.isArray(output)) return "";

  const chunks: string[] = [];
  for (const item of output) {
    if (!item || typeof item !== "object") continue;
    const outputItem = item as Record<string, unknown>;
    const content = outputItem.content;
    if (!Array.isArray(content)) continue;
    for (const part of content) {
      if (!part || typeof part !== "object") continue;
      const contentPart = part as Record<string, unknown>;
      if (typeof contentPart.text === "string" && contentPart.text.trim()) {
        chunks.push(contentPart.text);
      }
    }
  }

  return chunks.join("\n").trim();
}

async function generateMetadataForClip(filePath: string, apiKey: string): Promise<ClipMeta> {
  const fileName = path.basename(filePath);
  const duration = getDurationSeconds(filePath);
  const sampleTimes = evenlySampleTimes(duration, FRAME_SAMPLES_PER_CLIP);
  const frames = sampleTimes.map((time) => extractFramePng(filePath, time));

  const prompt = [
    "You are naming short motion clips.",
    "Given 10 evenly spaced frames from the same clip, generate:",
    "- title: max 6 words",
    "- description: max 18 words",
    "Keep both specific and visual. Avoid generic labels like 'Screen Recording'.",
    "Return ONLY JSON with this exact shape:",
    '{"title":"...","description":"..."}',
  ].join("\n");

  const body = {
    model: MODEL,
    input: [
      {
        role: "user",
        content: [
          { type: "input_text", text: prompt },
          ...frames.map((frame) => ({
            type: "input_image" as const,
            image_url: `data:image/png;base64,${frame.toString("base64")}`,
          })),
        ],
      },
    ],
  };

  const response = await fetch(OPENAI_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI request failed (${response.status}): ${errorText}`);
  }

  const data = (await response.json()) as unknown;
  const outputText = extractResponseText(data);
  if (!outputText) {
    const debugSnippet = JSON.stringify(data).slice(0, 500);
    throw new Error(`Model returned no text content. Response snippet: ${debugSnippet}`);
  }
  const metadata = parseMetadataText(outputText);
  return { fileName, ...metadata };
}

function sanitizeForFilename(text: string): string {
  return text.replace(/[\/\\:*?"<>|]/g, "-").replace(/-{2,}/g, "-").trim();
}

async function appendClipToHtml(clip: ClipMeta): Promise<void> {
  const html = await readFile(HTML_PATH, "utf8");
  const clips = parseClipsData(html);
  const alreadyListed = clips.some((item) => item.fileName === clip.fileName);
  if (alreadyListed) return;

  const next = [...clips, clip].sort((a, b) => a.fileName.localeCompare(b.fileName));
  const updatedHtml = updateHtmlWithClips(html, next);
  await writeFile(HTML_PATH, updatedHtml, "utf8");
  console.log(`Added clip metadata to HTML: ${clip.fileName}`);
}

async function processSingleFile(fileName: string, apiKey: string): Promise<void> {
  const filePath = path.join(CLIPS_DIR, fileName);
  const fileStats = await stat(filePath);
  if (!fileStats.isFile()) return;

  console.log(`Generating title/description for ${fileName}...`);
  const clip = await generateMetadataForClip(filePath, apiKey);

  const html = await readFile(HTML_PATH, "utf8");
  const existingClips = parseClipsData(html);
  const orderNumber = existingClips.length + 1;
  const ext = path.extname(fileName);
  const base = path.basename(fileName, ext);
  const safeTitle = sanitizeForFilename(clip.title);
  const newFileName = `${String(orderNumber).padStart(2, "0")} - ${safeTitle} - ${base}${ext}`;
  const newFilePath = path.join(CLIPS_DIR, newFileName);

  await rename(filePath, newFilePath);
  clip.fileName = newFileName;
  console.log(`Renamed: ${fileName} -> ${newFileName}`);

  await appendClipToHtml(clip);
}

async function runWatcher(): Promise<void> {
  await loadEnvFromFile();
  const apiKey = mustGetApiKey();
  const inFlight = new Set<string>();
  const failedUntil = new Map<string, number>();
  const attemptsByFile = new Map<string, number>();
  const exhaustedFiles = new Set<string>();
  console.log(
    `Watching ${path.relative(ROOT, CLIPS_DIR)} and syncing any clips missing from HTML.`,
  );

  const maybeProcessNewFiles = async () => {
    let html = await readFile(HTML_PATH, "utf8");
    const listedClips = parseClipsData(html);
    const videoFiles = await listVideoFiles();
    const videoSet = new Set(videoFiles);
    const now = Date.now();

    const staleClips = listedClips.filter((clip) => !videoSet.has(clip.fileName));
    if (staleClips.length > 0) {
      const kept = listedClips.filter((clip) => videoSet.has(clip.fileName));
      html = updateHtmlWithClips(html, kept);
      await writeFile(HTML_PATH, html, "utf8");
      for (const clip of staleClips) {
        console.log(`Removed deleted clip from HTML: ${clip.fileName}`);
      }
    }

    const listedSet = new Set(listedClips.map((item) => item.fileName));
    for (const fileName of videoFiles) {
      const isListed = listedSet.has(fileName);
      const busy = inFlight.has(fileName);
      const cooldownUntil = failedUntil.get(fileName) ?? 0;
      const inCooldown = now < cooldownUntil;
      const exhausted = exhaustedFiles.has(fileName);
      if (isListed || busy || inCooldown || exhausted) continue;

      inFlight.add(fileName);
      try {
        await processSingleFile(fileName, apiKey);
        failedUntil.delete(fileName);
        attemptsByFile.delete(fileName);
        exhaustedFiles.delete(fileName);
      } catch (error) {
        const attempts = (attemptsByFile.get(fileName) ?? 0) + 1;
        attemptsByFile.set(fileName, attempts);

        if (attempts < MAX_ATTEMPTS_PER_CLIP) {
          failedUntil.set(fileName, Date.now() + RETRY_COOLDOWN_MS);
          console.error(
            `Failed processing ${fileName} (attempt ${attempts}/${MAX_ATTEMPTS_PER_CLIP}). Retrying once after cooldown...`,
            error,
          );
        } else {
          failedUntil.delete(fileName);
          exhaustedFiles.add(fileName);
          console.error(
            `Failed processing ${fileName} (attempt ${attempts}/${MAX_ATTEMPTS_PER_CLIP}). No more retries this run.`,
            error,
          );
        }
      } finally {
        inFlight.delete(fileName);
      }
    }
  };

  // Polling keeps behavior stable across editors/filesystems and naturally re-diffs HTML each cycle.
  setInterval(() => {
    void maybeProcessNewFiles();
  }, POLL_MS);
  void maybeProcessNewFiles();

  // Event-driven hint for faster reaction right after file writes finish.
  const watcher = watch(CLIPS_DIR);
  for await (const fileChangeEvent of watcher) {
    void fileChangeEvent;
    void maybeProcessNewFiles();
  }
}

runWatcher().catch((error) => {
  console.error(error);
  process.exit(1);
});
