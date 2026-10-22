// Bloom contribution of a render: (with bloom) - (without), as an image + stats.
//   node bloom_compare.mjs with.png without.png diff.png
import sharp from 'sharp';
const [a, b, out] = process.argv.slice(2);
const A = await sharp(a).removeAlpha().raw().toBuffer({ resolveWithObject: true });
const B = await sharp(b).removeAlpha().raw().toBuffer();
const { width: W, height: H } = A.info; const d = Buffer.alloc(W * H * 3); let tot = 0, mx = 0, n20 = 0;
for (let i = 0; i < d.length; i++) { const v = Math.max(0, A.data[i] - B[i]); d[i] = Math.min(255, v * 4); tot += v; if (v > mx) mx = v; if (v > 20) n20++; }
console.log('mean added', (tot / d.length).toFixed(3), 'max', mx, 'px>20', n20);
await sharp(d, { raw: { width: W, height: H, channels: 3 } }).png().toFile(out);
