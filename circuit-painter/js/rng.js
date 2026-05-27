// Seeded RNG. Backed by seedrandom loaded from the page, kept module-local.
let rng;

export function setSeed(seed = 'circuit42') {
    rng = new Math.seedrandom(String(seed));
}

export function rnd() {
    return rng();
}

export function rndInt(n) {
    return Math.floor(rnd() * n);
}
