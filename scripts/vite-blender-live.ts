import { stat } from 'node:fs/promises';
import path from 'node:path';
import type { Plugin } from 'vite';

export function blenderLivePlugin(): Plugin {
  return {
    name: 'blender-live',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__blender-live', async (req, res) => {
        const model = new URL(req.url || '/', 'http://localhost').searchParams.get('model');
        if (model !== 'pillar' && model !== 'world') {
          res.statusCode = 400;
          res.end('Unknown model');
          return;
        }
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Content-Type', 'application/json');
        try {
          const info = await stat(path.join(server.config.root, 'secret-base/models', `${model}.glb`));
          res.end(JSON.stringify({ version: `${info.mtimeMs}-${info.size}` }));
        } catch {
          res.statusCode = 503;
          res.end(JSON.stringify({ error: 'Model unavailable' }));
        }
      });
    },
  };
}
