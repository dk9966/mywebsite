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
        largeChips: 10,
        mediumIcs: 16,
        busBlocks: 4,
        padClusters: 8,
        passives: 170,
        attempts: 9000,
        gap: 16,
    },

    route: {
        majorLinks: 26,
        busLaneRange: [2, 4],
        localLinks: 155,
        branchLinks: 130,
        edgeBranches: 30,
        bendJitter: 34,
        chamfer: 14,
        lanePitch: 12,
        corridorGap: 48,
        localMaxDist: 260,
        branchLength: [38, 128],
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
            fg: '#24d8d2',
            dim: '#0d7774',
            traceWidth: 1.35,
            partWidth: 1.45,
            pinWidth: 0.95,
            glowBlur: 0.9,
        },
        blueprint: {
            bg: '#02040a',
            fg: '#7ff4ff',
            dim: '#2a8c98',
            traceWidth: 1.25,
            partWidth: 1.35,
            pinWidth: 0.9,
            glowBlur: 0.65,
        },
    },

    defaultStyle: 'neon',
};

