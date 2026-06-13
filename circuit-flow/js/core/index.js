// Pipeline entry: a seed fully determines the output model.
//
//   compose   chips in a horizontal band, pin rows at lane pitch
//   corridors horizontal transfer levels across the board
//   flows     bundles routed src -> sink over the corridor levels
//   fray      staggered ends, truncations, peels, pin stubs
//   balance   sparse-column fillers + clearance safety net

import { createRng } from '../rng.js';
import { composeChips } from './compose.js';
import { buildCorridors } from './corridors.js';
import { planFlows } from './flows.js';
import { frayBundles } from './fray.js';
import { balanceModel } from './balance.js';

export function generate(seed, config) {
    const rng = createRng(seed);
    const chips = composeChips(rng, config);
    const state = {
        chips,
        corridors: buildCorridors(rng, chips, config),
        occupancy: [],
        usedPins: new Map(chips.map((c) => [c, { left: new Set(), right: new Set() }])),
        bundles: [],
    };

    planFlows(rng, state, config);
    frayBundles(rng, state, config);
    const { traces, meshStats } = balanceModel(rng, state, config);

    // Only pins that actually carry a trace (or stub) survive to the render
    // model -- bare tabs on unused pins just look like noise.
    for (const chip of chips) {
        const used = state.usedPins.get(chip);
        chip.pins = {
            left: chip.pins.left.filter((_, i) => used.left.has(i)),
            right: chip.pins.right.filter((_, i) => used.right.has(i)),
        };
    }

    return { chips, traces, meshStats };
}
