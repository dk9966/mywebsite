// Region-by-region luminance/colour comparison of two same-size renders.
//   node secret-base/cave-web/compare.mjs blender.png three.png
import sharp from 'sharp';

const [a, b] = process.argv.slice(2);
const load = async (f) => sharp(f).removeAlpha().raw().toBuffer({ resolveWithObject: true });
const A = await load(a);
const B = await load(b);
const { width: W, height: H } = A.info;
const srgbToLin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
// Named regions as fractions of the frame (x0, y0, x1, y1).
const REGIONS = {
  'center deck': [0.38, 0.5, 0.62, 0.68],
  'console': [0.45, 0.43, 0.55, 0.5],
  'rear hole': [0.42, 0.04, 0.62, 0.36],
  'upper right room': [0.75, 0.06, 0.92, 0.28],
  'lower right deck': [0.7, 0.55, 0.98, 0.75],
  'holo table': [0.78, 0.57, 0.89, 0.66],
  'left stairs top': [0.18, 0.32, 0.36, 0.47],
  'left floor': [0.02, 0.72, 0.3, 0.98],
  'chasm below deck': [0.42, 0.72, 0.6, 0.98],
  'left cave wall': [0.0, 0.05, 0.15, 0.5],
  'right cave wall': [0.92, 0.3, 1.0, 0.55],
  'roof': [0.2, 0.0, 0.8, 0.06],
  'whole frame': [0, 0, 1, 1],
};
const stats = (img, [x0, y0, x1, y1]) => {
  const xs = Math.floor(x0 * W), xe = Math.floor(x1 * W), ys = Math.floor(y0 * H), ye = Math.floor(y1 * H);
  let r = 0, g = 0, bl = 0, n = 0; const lums = [];
  for (let y = ys; y < ye; y++) for (let x = xs; x < xe; x++) {
    const i = (y * W + x) * 3;
    r += img.data[i]; g += img.data[i + 1]; bl += img.data[i + 2]; n++;
    lums.push(0.2126 * srgbToLin(img.data[i]) + 0.7152 * srgbToLin(img.data[i + 1]) + 0.0722 * srgbToLin(img.data[i + 2]));
  }
  lums.sort((p, q) => p - q);
  return { r: r / n, g: g / n, b: bl / n, p10: lums[Math.floor(n * 0.1)], p50: lums[Math.floor(n * 0.5)], p90: lums[Math.floor(n * 0.9)] };
};
const fmt = (v) => v.toFixed(1).padStart(6);
console.log('region'.padEnd(20), 'blender rgb'.padEnd(24), 'three rgb'.padEnd(24), 'p50 ratio', 'p90 ratio', 'p10 ratio');
for (const [name, box] of Object.entries(REGIONS)) {
  const s = stats(A, box), t = stats(B, box);
  console.log(name.padEnd(20), `${fmt(s.r)}${fmt(s.g)}${fmt(s.b)}`.padEnd(24), `${fmt(t.r)}${fmt(t.g)}${fmt(t.b)}`.padEnd(24),
    (t.p50 / s.p50).toFixed(2).padStart(9), (t.p90 / s.p90).toFixed(2).padStart(9), (t.p10 / s.p10).toFixed(2).padStart(9));
}
