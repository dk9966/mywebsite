// PCB road-circuit generator config. The visual target is
// plans/board pcb road circuits.png: a dense black board with cyan component
// islands, bus-like road corridors, many vias, and no unanchored trace ends.

export const CONFIG = {
    board: { width: 1536, height: 1024 },

    grid: {
        cell: 8,
        margin: 32,
    },

    place: {
        largeChips: 11,
        mediumIcs: 18,
        busBlocks: 4,
        padClusters: 7,
        passives: 150,
        attempts: 9000,
        gap: 18,
    },

    route: {
        majorLinks: 32,
        busLaneRange: [4, 8],
        localLinks: 185,
        branchLinks: 90,
        edgeBranches: 42,
        bendJitter: 140,
        chamfer: 34,
    },

    vias: {
        ringR: 4.4,
        dotR: 2.1,
        traceChance: 0.24,
        branchChance: 0.72,
    },

    styles: {
        neon: {
            bg: '#020606',
            fg: '#27f0e6',
            dim: '#118b87',
            traceWidth: 2,
            partWidth: 2,
            pinWidth: 1.35,
            glowBlur: 3.25,
        },
        blueprint: {
            bg: '#02040a',
            fg: '#7ff4ff',
            dim: '#2a8c98',
            traceWidth: 1.75,
            partWidth: 1.8,
            pinWidth: 1.25,
            glowBlur: 1.75,
        },
    },

    defaultStyle: 'neon',
};

