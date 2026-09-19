// Watch saved Blender edits; export in a separate process so the editor stays usable.
import { stat, rename, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const source = path.resolve(root, process.argv[2] || 'secret-base/base.blend');
const output = path.join(root, 'secret-base/models/pillar.glb');
const temporary = path.join(path.dirname(output), `.pillar-live-${process.pid}.glb`);
const blender = process.env.BLENDER_BIN || (process.platform === 'darwin'
  ? '/Applications/Blender.app/Contents/MacOS/Blender' : 'blender');
let child;
let stopped = false;
let exported;
let observed;
let stableSince = 0;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const signature = async () => {
  const info = await stat(source);
  return `${info.mtimeMs}:${info.size}`;
};
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  stopped = true;
  child?.kill('SIGTERM');
});

console.log(`[Blender live] Watching ${source}. Save in Blender to update the station.`);
try {
  while (!stopped) {
    try {
      const current = await signature();
      if (current !== observed) {
        observed = current;
        stableSince = Date.now();
      }
      if (current !== exported && Date.now() - stableSince >= 1000) {
        console.log('[Blender live] Exporting saved scene…');
        await new Promise((resolve, reject) => {
          child = spawn(blender, ['--background', source, '--python-exit-code', '1',
            '--python', path.join(root, 'secret-base/export_pillar.py')], {
            cwd: root, stdio: 'inherit', env: { ...process.env, BLENDER_EXPORT_OUT: temporary },
          });
          child.on('error', reject);
          child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Blender exited ${code}`)));
        });
        child = undefined;
        // Never publish a partial export or one superseded by another save.
        if (!stopped && await signature() === current) {
          await rename(temporary, output);
          exported = current;
          console.log('[Blender live] Station mesh updated.');
        }
      }
    } catch (error) {
      console.error('[Blender live]', error.message);
      await delay(4000);
    }
    await delay(500);
  }
} finally {
  await rm(temporary, { force: true });
}
