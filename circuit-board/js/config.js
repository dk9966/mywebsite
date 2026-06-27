// Dense PCB top-view generator config. Geometry targets are measured against
// the reference illustration (plans/chatgpt/top view spaced out.png, 1024x683):
// ~6 large QFPs, a handful of mid-size parts, 50-70 small parts, trace ribbons
// at ~8px pitch (at 1024 wide), every trace end closed by a pin, pad, or via.
//
// All routing happens on a square cell grid (grid.cell px per cell); pins and
// component footprints are cell-aligned so trace starts land on cell centers.

export const CONFIG = {
    board: { width: 1536, height: 1024 },

    grid: {
        cell: 6,
        edgeMargin: 3, // cells kept free along the board border
    },

    // Pin rows on chips: pitch/inset in cells, drawn tab reaches the anchor
    // cell center just outside the footprint so traces fuse with the tab.
    pins: { pitch: 2, inset: 2 },

    place: {
        qfp: { count: [5, 6], jitter: 0.3, body: [15, 21] },
        soic: { count: [3, 5], bodyW: [9, 13], bodyH: [4, 6] },
        heatsink: { count: [2, 4] },
        header: { count: [1, 2] },
        connector: { count: [1, 2] },
        satelliteRadius: [14, 62],
        small: {
            count: [135, 170],
            weights: [
                { value: 'passive', weight: 30 },
                { value: 'passivePair', weight: 14 },
                { value: 'smd', weight: 16 },
                { value: 'capRound', weight: 12 },
                { value: 'lonePad', weight: 12 },
                { value: 'drum', weight: 8 },
            ],
        },
        // Placement margins in cells, by part class.
        margin: { qfp: 5, mid: 4, small: 3 },
    },

    net: {
        extraEdges: [4, 6], // chip-graph edges beyond the MST
        busSize: [4, 8], // trace pairs per chip-to-chip ribbon
        soloChance: 0.95, // leftover pin group gets a ribbon fan
        soloDist: [22, 110], // cells
        // Leftover chip pins fan out in groups of adjacent pins; mostly 2-4.
        soloGroupSizes: [
            { value: 1, weight: 1 },
            { value: 2, weight: 2 },
            { value: 3, weight: 3 },
            { value: 4, weight: 2 },
        ],
        smallChance: 1, // every small-part pad gets a trace
        anchorLinkDist: 95, // small pads must find a substantial anchor within this range
        fillerMax: 140, // cap on connected via branches routed through empty regions
        fillerDist: [14, 92], // cells
        fillerStopOcc: 58, // stop filling once the emptiest 17x17 window has this many busy cells
        fillerPairChance: 0.65, // filler doubles into a two-lane ribbon
    },

    route: {
        segMin: 4, // cells before a heading change is free
        segPenalty: 2,
        turnSmoothness: 0.035,
        diagCost: 1.55, // Math.SQRT2 + slight tax keeps diagonals deliberate
        clearanceTarget: 2, // cells of breathing room around components
        clearanceWeight: 0.7,
        bundleNearPenalty: 1.2, // parallel trace 1 cell away: too tight
        bundleFarBonus: 0.55, // parallel trace 2 cells away: ribbon pitch
        corridorWeight: 0.06,
        corridorRadius: 4,
        maxExpansions: 60000,
        openMaxExpansions: 40000,
    },

    fillet: { radius: 9 }, // px, clamped per corner to fit its segments

    vias: {
        ringR: 3.4,
        dotR: 2.1,
        ringChance: 0.6,
        minGapCells: 4,
        groupGapCells: 2, // staggered via rows within one ribbon sit closer
    },

    defaultStyle: 'bw',
    styles: {
        bw: {
            bg: '#000000',
            fg: '#ececec',
            traceWidth: 2.6,
            glowBlur: 0,
            accents: { green: '#ececec', pink: '#ececec' },
        },
        neon: {
            bg: '#020308',
            fg: '#35d6f4',
            traceWidth: 2,
            glowBlur: 3.5,
            accents: { green: '#46e08a', pink: '#ff4fd8' },
        },
    },
};

const DENSE_LONG_CONFIG = denseLongConfig(CONFIG);

export const BOARD_VARIANTS = {
    default: {
        config: CONFIG,
        style: CONFIG.defaultStyle,
    },
    'dense-long': {
        config: DENSE_LONG_CONFIG,
        style: DENSE_LONG_CONFIG.defaultStyle,
        outDir: 'dense-long',
        reference: '../plans/board pcb road circuits.png',
    },
};

function denseLongConfig(baseConfig) {
    const config = structuredClone(baseConfig);

    config.place.qfp.count = [18, 22];
    config.place.qfp.slots = [6, 4];
    config.place.qfp.jitter = 0.34;
    config.place.qfp.body = [11, 16];
    config.place.soic.bodyW = [12, 17];
    config.place.soic.bodyH = [5, 8];
    config.place.soic.count = [8, 12];
    config.place.heatsink.count = [7, 10];
    config.place.header.count = [5, 8];
    config.place.connector.count = [5, 8];
    config.place.satelliteRadius = [10, 78];
    config.place.small.count = [0, 0];
    config.place.small.weights = [
        { value: 'passive', weight: 34 },
        { value: 'passivePair', weight: 18 },
        { value: 'smd', weight: 20 },
        { value: 'capRound', weight: 12 },
        { value: 'lonePad', weight: 10 },
        { value: 'drum', weight: 8 },
    ];
    config.place.margin = { qfp: 2, mid: 2, small: 2 };
    config.place.cityGrid = {
        cols: 12,
        rows: 8,
        fill: 0.96,
        gutter: 1,
        margin: 1,
        triesPerSlot: 12,
        weights: [
            { value: 'qfp', weight: 36 },
            { value: 'soic', weight: 16 },
            { value: 'heatsink', weight: 16 },
            { value: 'header', weight: 16 },
            { value: 'connector', weight: 16 },
        ],
    };

    config.net.extraEdges = [14, 20];
    config.net.longEdgeShare = 0.45;
    config.net.busSize = [5, 8];
    config.net.soloDist = [64, 190];
    config.net.soloGroupSizes = [
        { value: 2, weight: 2 },
        { value: 3, weight: 3 },
        { value: 4, weight: 3 },
        { value: 5, weight: 2 },
    ];
    config.net.smallChance = 0.45;
    config.net.anchorLinkDist = 120;
    config.net.fillerMax = 300;
    config.net.fillerDist = [58, 196];
    config.net.fillerStopOcc = 132;
    config.net.fillerPairChance = 0.78;

    config.route.clearanceTarget = 1;
    config.route.clearanceWeight = 0.45;
    config.route.segMin = 7;
    config.route.diagCost = 2.15;
    config.route.openMaxExpansions = 65000;
    config.route.maxExpansions = 90000;

    config.vias.ringChance = 0.72;
    config.output = { keepPlacedParts: true };
    config.defaultStyle = 'neon';
    config.styles.neon = {
        ...config.styles.neon,
        bg: '#000000',
        fg: '#27f4ee',
        traceWidth: 1.3,
        glowBlur: 0.8,
        accents: { green: '#27f4ee', pink: '#27f4ee' },
    };

    return config;
}

export function gridSize(config) {
    return {
        gw: Math.floor(config.board.width / config.grid.cell),
        gh: Math.floor(config.board.height / config.grid.cell),
    };
}
