import fs from "node:fs/promises";
import path from "node:path";
import type { Connect, Plugin } from "vite";
import type { ServerResponse } from "node:http";

interface JsonFileSaveOptions {
  /** Vite plugin name, shown in logs. */
  name: string;
  /** Dev route the client GETs/POSTs, e.g. "/__save-desk-layout". */
  route: string;
  /** Committed file path relative to the project root. */
  relPath: string;
}

function readBody(req: Connect.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

/**
 * Dev-only route backing a single committed JSON file. GET returns the file as
 * it is on disk right now; POST validates and overwrites it. This is what lets
 * "Set as default" persist to source instead of one browser's localStorage, so
 * every browser sees the same committed settings after a reload.
 */
export function jsonFileSavePlugin(opts: JsonFileSaveOptions): Plugin {
  return {
    name: opts.name,
    configureServer(server) {
      const outPath = path.resolve(server.config.root, opts.relPath);

      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url ?? "/", "http://localhost");
        if (url.pathname !== opts.route) {
          next();
          return;
        }

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

        if (req.method === "POST") {
          try {
            const body = await readBody(req);
            JSON.parse(body);
            await fs.writeFile(outPath, `${body.trimEnd()}\n`, "utf8");
            sendJson(res, 200, { ok: true, path: opts.relPath });
          } catch (err) {
            sendJson(res, 500, { ok: false, error: String(err) });
          }
          return;
        }

        sendJson(res, 405, { ok: false, error: "method not allowed" });
      });
    },
  };
}
