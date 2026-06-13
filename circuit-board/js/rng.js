// Seeded RNG (mulberry32) plus the sampling helpers the generator uses.
// A single Rng instance threads through the whole pipeline so a seed fully
// determines the output.

export function createRng(seed) {
    let a = seed >>> 0;
    const next = () => {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    return {
        float: next,
        range: (min, max) => min + next() * (max - min),
        int: (min, max) => Math.floor(min + next() * (max - min + 1)),
        chance: (p) => next() < p,
        pick: (arr) => arr[Math.floor(next() * arr.length)],
        sign: () => (next() < 0.5 ? -1 : 1),
        // Weighted pick from [{ value, weight }, ...]
        weighted(entries) {
            const total = entries.reduce((s, e) => s + e.weight, 0);
            let r = next() * total;
            for (const e of entries) {
                r -= e.weight;
                if (r <= 0) return e.value;
            }
            return entries[entries.length - 1].value;
        },
        shuffle(arr) {
            const out = arr.slice();
            for (let i = out.length - 1; i > 0; i--) {
                const j = Math.floor(next() * (i + 1));
                [out[i], out[j]] = [out[j], out[i]];
            }
            return out;
        },
    };
}
