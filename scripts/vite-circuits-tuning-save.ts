import fs from "node:fs/promises";
import path from "node:path";
import type { Plugin } from "vite";

const SAVE_ROUTE = "/__save-circuits-tuning";

/** Dev-only route that writes the committed circuits tuning JSON. */
export function circuitsTuningSavePlugin(): Plugin {
  return {
    name: "circuits-tuning-save",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== SAVE_ROUTE || req.method !== "POST") {
          next();
          return;
        }

        try {
          const body = await new Promise<string>((resolve, reject) => {
            const chunks: Buffer[] = [];
            req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
            req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
            req.on("error", reject);
          });
          JSON.parse(body);

          const outPath = path.resolve(server.config.root, "src/data/circuits-tuning.json");
          await fs.writeFile(outPath, `${body.trimEnd()}\n`, "utf8");

          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ ok: true, path: "src/data/circuits-tuning.json" }));
        } catch (err) {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ ok: false, error: String(err) }));
        }
      });
    },
  };
}
