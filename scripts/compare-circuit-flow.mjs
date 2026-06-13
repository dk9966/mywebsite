// One-off comparison: reference traced lines vs generated seeds.
import { readFileSync } from 'fs';
import { CONFIG } from '../circuit-flow/js/config.js';
import { generate } from '../circuit-flow/js/core/index.js';

const ref = JSON.parse(
    readFileSync(new URL('../plans/circuit design/circuits-traced.json', import.meta.url)),
);

function metrics(lines, label, boardW, boardH) {
    const segs = [];
    let total = 0;
    const ys = [];
    let bumps = 0;
    let stairs = 0;
    let diagCount = 0;

    for (const ln of lines) {
        const signs = [];
        for (let i = 0; i + 1 < ln.length; i++) {
            const [x1, y1] = ln[i];
            const [x2, y2] = ln[i + 1];
            const len = Math.hypot(x2 - x1, y2 - y1);
            if (len < 1e-6) continue;
            total += len;
            ys.push(y1, y2);
            segs.push([x1, y1, x2, y2, len]);
            if (Math.abs(y2 - y1) > 2) {
                signs.push({ s: Math.sign(y2 - y1), x: (x1 + x2) / 2 });
                diagCount++;
            }
        }
        for (let i = 0; i + 1 < signs.length; i++) {
            const close = Math.abs(signs[i + 1].x - signs[i].x) < 160;
            if (signs[i + 1].s !== signs[i].s && close) bumps++;
            if (signs[i + 1].s === signs[i].s && close) stairs++;
        }
    }

    ys.sort((a, b) => a - b);
    const p = (q) => ys[Math.floor(q * (ys.length - 1))];
    const vSpread = p(0.95) - p(0.05);

    // median gap between vertically-near overlapping horizontal runs
    const runs = segs.filter(([x1, y1, x2, y2]) => Math.abs(y2 - y1) <= 2 && Math.abs(x2 - x1) > 40);
    const gaps = [];
    for (let i = 0; i < runs.length; i++) {
        let nearest = Infinity;
        for (let j = 0; j < runs.length; j++) {
            if (i === j) continue;
            const [a1, ay, a2] = [Math.min(runs[i][0], runs[i][2]), runs[i][1], Math.max(runs[i][0], runs[i][2])];
            const [b1, by, b2] = [Math.min(runs[j][0], runs[j][2]), runs[j][1], Math.max(runs[j][0], runs[j][2])];
            if (Math.min(a2, b2) - Math.max(a1, b1) < 30) continue;
            const g = Math.abs(ay - by);
            if (g > 1 && g < nearest) nearest = g;
        }
        if (nearest < Infinity) gaps.push(nearest);
    }
    gaps.sort((a, b) => a - b);
    const medGap = gaps.length ? gaps[Math.floor(gaps.length / 2)] : 0;

    console.log(
        `${label.padEnd(10)} lines=${String(lines.length).padStart(3)}  ink=${(total / 1000).toFixed(1)}k` +
        `  ink/area=${(total / (boardW * boardH) * 1000).toFixed(1)}` +
        `  vSpread=${vSpread.toFixed(0)}px (${(vSpread / boardH * 100).toFixed(0)}%)` +
        `  diag/line=${(diagCount / lines.length).toFixed(1)}` +
        `  bumps/line=${(bumps / lines.length).toFixed(2)}` +
        `  stairs/line=${(stairs / lines.length).toFixed(2)}` +
        `  medParallelGap=${medGap.toFixed(0)}`,
    );
}

// Reference: coordinates live in a ~1568x~620 space; use observed bounds.
const refXs = ref.lines.flat().map((p) => p[0]);
const refYs = ref.lines.flat().map((p) => p[1]);
const refW = Math.max(...refXs) - Math.min(...refXs);
const refH = Math.max(...refYs) - Math.min(...refYs);
console.log(`reference board (line bbox): ${refW.toFixed(0)} x ${refH.toFixed(0)}`);
metrics(ref.lines, 'reference', refW, refH);

for (const seed of [1, 2, 3, 4, 5]) {
    const model = generate(seed, CONFIG);
    metrics(model.traces.map((t) => t.points), `seed ${seed}`, CONFIG.board.width, CONFIG.board.height);
}
