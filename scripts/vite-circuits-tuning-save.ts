import fs from "node:fs/promises";
import path from "node:path";
import type { Connect, Plugin } from "vite";
import type { ServerResponse } from "node:http";

const SAVE_ROUTE = "/__save-circuits-tuning";
const REL_PATH = "src/data/circuits-tuning.json";

/** Named version snapshots live here, one JSON file per version. */
const VERSIONS_ROUTE = "/__circuit-versions";
const VERSIONS_DIR = "src/data/circuit-versions";

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function readBody(req: Connect.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

/** Reject anything that could escape the versions directory. */
function safeVersionName(raw: string | null): string | null {
  if (!raw) return null;
  const name = raw.trim();
  if (!/^[a-zA-Z0-9 _-]{1,60}$/.test(name)) return null;
  return name;
}

export function circuitsTuningSavePlugin(): Plugin {
  return {
    name: "circuits-tuning-save",
    configureServer(server) {
      const root = server.config.root;
      const outPath = path.resolve(root, REL_PATH);
      const versionsDir = path.resolve(root, VERSIONS_DIR);

      const versionPath = (name: string) =>
        path.join(versionsDir, `${name}.json`);

      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url ?? "/", "http://localhost");
        const pathname = url.pathname;

        if (pathname === SAVE_ROUTE) {
          await handleDefault(req, res, outPath);
          return;
        }

        if (pathname === VERSIONS_ROUTE) {
          await handleVersions(req, res, versionsDir, versionPath, url);
          return;
        }

        next();
      });
    },
  };
}

/**
 * Dev-only route for the committed circuits tuning JSON.
 * POST writes the file; GET returns the file as it is on disk right now, so
 * Reset can revert to what's actually saved (not each tab's stale in-memory
 * copy from page-load time).
 */
async function handleDefault(
  req: Connect.IncomingMessage,
  res: ServerResponse,
  outPath: string,
): Promise<void> {
  if (req.method === "GET") {
    try {
      const current = await fs.readFile(outPath, "utf8");
      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Cache-Control", "no-store");
      res.end(current);
    } catch (err) {
      sendJson(res, 500, { ok: false, error: String(err) });
    }
    return;
  }

  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }

  try {
    const body = await readBody(req);
    JSON.parse(body);
    await fs.writeFile(outPath, `${body.trimEnd()}\n`, "utf8");
    sendJson(res, 200, { ok: true, path: REL_PATH });
  } catch (err) {
    sendJson(res, 500, { ok: false, error: String(err) });
  }
}

/**
 * Dev-only CRUD for named version files under src/data/circuit-versions.
 *   GET    /__circuit-versions            -> { versions: string[] }
 *   GET    /__circuit-versions?name=foo   -> raw JSON of that version
 *   POST   /__circuit-versions?name=foo   -> write current tuning to that file
 *   DELETE /__circuit-versions?name=foo   -> remove that file
 */
async function handleVersions(
  req: Connect.IncomingMessage,
  res: ServerResponse,
  versionsDir: string,
  versionPath: (name: string) => string,
  url: URL,
): Promise<void> {
  const name = safeVersionName(url.searchParams.get("name"));

  if (req.method === "GET" && !url.searchParams.has("name")) {
    try {
      const entries = await fs.readdir(versionsDir);
      const versions = entries
        .filter((f) => f.endsWith(".json"))
        .map((f) => f.slice(0, -".json".length))
        .sort((a, b) => a.localeCompare(b));
      sendJson(res, 200, { ok: true, versions });
    } catch {
      // Directory not created yet — no versions saved.
      sendJson(res, 200, { ok: true, versions: [] });
    }
    return;
  }

  if (!name) {
    sendJson(res, 400, { ok: false, error: "invalid version name" });
    return;
  }

  if (req.method === "GET") {
    try {
      const current = await fs.readFile(versionPath(name), "utf8");
      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Cache-Control", "no-store");
      res.end(current);
    } catch {
      sendJson(res, 404, { ok: false, error: "version not found" });
    }
    return;
  }

  if (req.method === "POST") {
    try {
      const body = await readBody(req);
      JSON.parse(body);
      await fs.mkdir(versionsDir, { recursive: true });
      await fs.writeFile(versionPath(name), `${body.trimEnd()}\n`, "utf8");
      sendJson(res, 200, { ok: true, name });
    } catch (err) {
      sendJson(res, 500, { ok: false, error: String(err) });
    }
    return;
  }

  if (req.method === "DELETE") {
    try {
      await fs.unlink(versionPath(name));
      sendJson(res, 200, { ok: true, name });
    } catch {
      sendJson(res, 404, { ok: false, error: "version not found" });
    }
    return;
  }

  sendJson(res, 405, { ok: false, error: "method not allowed" });
}
