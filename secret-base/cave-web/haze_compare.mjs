// Haze-only comparison in linear light, region by region.
//   node haze_compare.mjs blender-with.exr blender-without.exr web-with-log.png web-without-log.png
// Blender EXRs are decoded with Blender itself beforehand into .f32 dumps
// (see README); web captures use ?logout (log2 encoding, -14..+10 EV).
import sharp from 'sharp';
import { readFile } from 'node:fs/promises';

const [bw, bn, ww, wn] = process.argv.slice(2);
const W = 1200, H = 662;
const f32 = async (f) => new Float32Array((await readFile(f)).buffer.slice(0));
const decode = async (f) => {
  const { data } = await sharp(f).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const out = new Float32Array(W * H * 3);
  for (let i = 0; i < out.length; i++) out[i] = data[i] === 0 ? 0 : 2 ** (data[i] / 255 * 24 - 14);
  return out;
};
const [BW, BN, WW, WN] = await Promise.all([f32(bw), f32(bn), decode(ww), decode(wn)]);
// Blender dumps are bottom-up RGBA; web captures are top-down RGB.
const blender = (arr, x, y, c) => arr[((H - 1 - y) * W + x) * 4 + c];
const web = (arr, x, y, c) => arr[(y * W + x) * 3 + c];
const REGIONS = {
  'roof': [0.2, 0.0, 0.8, 0.06], 'rear hole': [0.42, 0.04, 0.62, 0.36], 'chasm below deck': [0.42, 0.72, 0.6, 0.98],
  'left beam': [0.15, 0.1, 0.3, 0.3], 'center above deck': [0.4, 0.38, 0.6, 0.5], 'right chasm': [0.62, 0.8, 0.9, 1.0],
  'left cave wall': [0.0, 0.05, 0.15, 0.5], 'upper right room': [0.75, 0.06, 0.92, 0.28], 'whole frame': [0, 0, 1, 1],
};
console.log('region'.padEnd(20), 'blender haze (lin)'.padEnd(28), 'web haze (lin)'.padEnd(28), 'ratio');
for (const [name, [x0, y0, x1, y1]] of Object.entries(REGIONS)) {
  const sb = [0, 0, 0], sw = [0, 0, 0]; let n = 0;
  for (let y = Math.floor(y0 * H); y < Math.floor(y1 * H); y++) for (let x = Math.floor(x0 * W); x < Math.floor(x1 * W); x++) {
    for (let c = 0; c < 3; c++) { sb[c] += blender(BW, x, y, c) - blender(BN, x, y, c); sw[c] += web(WW, x, y, c) - web(WN, x, y, c); }
    n++;
  }
  const fb = sb.map((v) => v / n), fw = sw.map((v) => v / n);
  const lum = (v) => 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  console.log(name.padEnd(20), fb.map((v) => v.toFixed(4)).join(' ').padEnd(28), fw.map((v) => v.toFixed(4)).join(' ').padEnd(28), (lum(fw) / lum(fb)).toFixed(2));
}
