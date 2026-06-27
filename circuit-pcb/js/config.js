// Dense PCB top-view generator config. Geometry targets the reference
// illustration (plans/board pcb road circuits.png): thin teal traces on pure
// black, hollow silkscreen footprints (no solid fills), a rich part vocabulary
// (QFP chips, dumbbell-passive banks, round through-holes, octagonal pads,
// pill connectors, ribbon-cable bundles), and gently filleted octilinear runs.
//
// All routing happens on a square cell grid (grid.cell px per cell); pins and
// component footprints are cell-aligned so trace starts land on cell centers.

export const CONFIG = {
    board: { width: 1536, height: 1024 },

    grid: {
        cell: 6,
        edgeMargin: 3, // cells kept free along the board border
    },

    // Pin rows on chips: pitch/inset in cells. The drawn tab reaches the anchor
    // cell center just outside the footprint so traces fuse with the tab.
    pins: { pitch: 2, inset: 2 },

    place: {
        // Pin-row chips that anchor the bus network.
        qfp: { count: [13, 17], body: [8, 15] },
        soic: { count: [6, 9], bodyW: [8, 13], bodyH: [4, 6] },

        // Larger fixed-footprint features.
        ribbon: { count: [2, 4] },
        pill: { count: [4, 7] },
        header: { count: [2, 4] },
        holeCluster: { count: [3, 6] },
        octagon: { count: [1, 2] },

        // Small parts fill the gaps, biased to sit near the chips they wire to.
        satelliteRadius: [10, 72],
        fill: {
            count: [120, 150],
            weights: [
                { value: 'passiveBank', weight: 34 },
                { value: 'passive', weight: 18 },
                { value: 'pad', weight: 16 },
                { value: 'holePad', weight: 12 },
                { value: 'octPad', weight: 8 },
            ],
        },
        passiveBank: { size: [3, 6], pitch: 3 },

        // Placement margins in cells, by part class.
        margin: { qfp: 3, mid: 2, small: 2 },
    },

    net: {
        extraEdges: [7, 11], // chip-graph edges beyond the MST
        busSize: [3, 6], // trace pairs per chip-to-chip ribbon
        soloChance: 0.9, // leftover pin group gets a ribbon fan
        soloDist: [22, 130], // cells
        // Leftover chip pins fan out in groups of adjacent pins; mostly 2-4.
        soloGroupSizes: [
            { value: 1, weight: 1 },
            { value: 2, weight: 3 },
            { value: 3, weight: 3 },
            { value: 4, weight: 2 },
        ],
        smallChance: 0.6, // share of small-part pads that grow a trace
        anchorLinkDist: 110, // small pads must find an anchor within this range
        fillerMax: 260, // cap on connected via branches routed through empty regions
        fillerDist: [16, 110], // cells
        fillerStopOcc: 86, // stop filling once the emptiest window is this busy
        fillerPairChance: 0.6, // filler doubles into a two-lane ribbon
    },

    route: {
        segMin: 5, // cells before a heading change is free
        segPenalty: 2,
        turnSmoothness: 0.04,
        diagCost: 1.7, // Math.SQRT2 + tax keeps diagonals deliberate
        clearanceTarget: 2, // cells of breathing room around components
        clearanceWeight: 0.6,
        bundleNearPenalty: 1.2, // parallel trace 1 cell away: too tight
        bundleFarBonus: 0.55, // parallel trace 2 cells away: ribbon pitch
        corridorWeight: 0.06,
        corridorRadius: 4,
        maxExpansions: 70000,
        openMaxExpansions: 45000,
    },

    fillet: { radius: 8 }, // px, clamped per corner to fit its segments

    vias: {
        ringR: 3.2,
        dotR: 1.9,
        ringChance: 0.55,
        minGapCells: 4,
        groupGapCells: 2, // staggered via rows within one ribbon sit closer
    },

    // Every footprint is drawn hollow (stroke fg, fill bg) for the thin
    // silkscreen read; renderers resolve 'fg'/'bg' tokens per style.
    output: { keepPlacedParts: true },

    defaultStyle: 'teal',
    styles: {
        teal: {
            bg: '#000000',
            fg: '#18b3a1',
            traceWidth: 1.6,
            glowBlur: 0,
        },
        blueprint: {
            bg: '#04141f',
            fg: '#6fc6ff',
            traceWidth: 1.6,
            glowBlur: 0,
        },
    },
};

export function gridSize(config) {
    return {
        gw: Math.floor(config.board.width / config.grid.cell),
        gh: Math.floor(config.board.height / config.grid.cell),
    };
}
