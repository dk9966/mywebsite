// All tunables in one place. The geometry numbers come from measuring the 36
// hand-traced polylines in plans/circuit design/circuits-traced.json:
//   - segment angles are ~96% in {0, 45, 90, 135} deg, 69% of length horizontal
//   - straight runs: median 56px, p25 33px; diagonals: median 37px, max 94px
//   - bends per trace: avg 2.3, mostly 1-3
//   - parallel horizontal gaps cluster at 12-14px (lane pitch) and multiples
//   - endpoint mix: ~25% box-to-box, ~47% one end on a box, ~28% floating

export const CONFIG = {
    board: {
        width: 1600,
        height: 900,
        marginX: 40, // traces may run all the way to this margin
    },

    // Layout grammar measured from the reference: chips sit at evenly spaced
    // x-stations hugging a horizontal spine. A station is either one chip
    // offset slightly above/below the spine, or a stacked pair straddling it
    // with a gap the spine traces flow through.
    chips: {
        stations: [5, 6],
        stackChance: 0.4,
        outerPad: [150, 210], // horizontal inset of first/last station
        singleOffset: [10, 60], // |chip-center offset| from the spine
        stackGap: [55, 115], // clear vertical gap inside a stacked pair
        greenSquare: { size: [78, 124] },
        pinkRect: { w: [140, 170], h: [56, 80] },
        pinkShare: 0.28,
        pinInset: 12, // first/last pin distance from chip corner
    },

    lanes: {
        pitch: 13, // pin pitch, from the 12-14px gap cluster
        bundleSize: [3, 4], // pins per departing ribbon (leader + followers)
        maxPerEdge: 6, // total routed pins allowed per chip edge
        clearance: 8, // min distance between unrelated traces / chip walls
    },

    corridors: {
        extraAboveBelow: [1, 2], // corridor groups outside the chip band -- the
        // escape levels mid-band branches climb onto before they may end.
        // Kept low: every extra group is vertical room for open ends to fan
        // into, and density belongs between the obstacles
        // Corridors come in groups of pitch-spaced lanes (the reference's
        // 12-14px parallel gaps) separated by wider breathing gaps. Tight
        // inside a group, loose between groups -- no mid-range spacing.
        groupSize: [2, 4], // lanes per group, at lanes.pitch
        groupGap: [36, 60], // edge-to-edge gap between groups; must stay
        // <= routing.jogSpan max or the next group is unreachable
    },

    routing: {
        minStraight: 28, // lead length at sources, sinks, and junctions
        directChance: 0.35, // chance an aligned pin pair may route dead straight
        jogSpacing: [28, 84], // per-line straight run between consecutive slants
        jogSpan: [13, 64], // vertical span of a single 45deg jog
        jogPenalty: 1.2, // Dijkstra cost multiplier per px of jog span
        hopPenalty: 24, // flat cost per jog: chip links take few, calm bends
        reversePenalty: 40, // cost for reversing slant direction (mountain look)
        sameDirMax: 2, // hard cap on consecutive same-direction slants
        hopNoise: 30, // random cost noise so sibling lines diverge
        spinePull: 0.8, // horizontal-travel tax per 100px off the spine
        openHops: [1, 2], // corridor changes for traces that end in space; <= the
        // open-route slant cap (sameDirMax + 1) so a whole cascade can lean
        // one way. Low on purpose: each hop is an outward step, and open
        // ends should settle near the band instead of staircasing away
        maxRun: 220, // longest straight run before an open trace terminates
        edgeRunChance: 0.15, // open trace running all the way to the board edge
        minOpenSpan: 130, // min horizontal span of a line that ends in space
        minOpenSpanFloor: 50, // lower bound when trimming open spans
        pairGapStitch: 100, // chip pairs closer than this get one spine link
        pairGapDirect: 140, // close pairs may route dead straight
        pinDyMax: 200, // max pin dy considered for chip-to-chip pairing
        slantBias: [1.2, 3.5], // per-line exponent for early-vs-late jog placement
        crowdRadius: 10, // parallel runs closer than this make a level "crowded";
        // below lanes.pitch on purpose: pitch-mates ride free as ribbons,
        // only sub-pitch squeeze (off-grid pin levels) pays the tax
        crowdPenalty: 3, // extra cost per crowded px, per parallel neighbor
        driftPenalty: 3, // cost per px an open line's jog cuts back toward the spine
    },

    flows: {
        perEdge: [2, 3], // flows stack onto the spine band, so density is safe
        sinkMix: [
            { value: 'chip', weight: 80 },
            { value: 'open', weight: 20 },
        ],
        branchCount: [4, 7], // forks off the spine band, leaning outward
        maxPairLinks: 2, // max lines between one chip pair (pairs, not buses)
    },

    // Junctions only split (host runs through, branch diverges off it);
    // dangling ends terminate on chip pins or stay open, never on lines --
    // a trace ending on a trace reads as flows consolidating into one.
    mesh: {
        anchoredShare: 0.55, // hard floor: lines with BOTH ends on a chip.
        // The best boards land near 0.7 naturally; the floor culls the
        // wandering open excess (shortest first) on the ones that don't
        mergeReach: 420, // how far a dangling end may extend to find a pin
        mergeCandidates: 60, // pin targets tried per dangling end
        mergeJogMax: 80, // final jog onto a pin may span more than routing jogs
    },

    fray: {
        truncateChance: 0.1, // lane stops early at a random point
        peelChance: 0.14, // lane takes its own final jog then stops
        endJitter: [0, 90], // stagger of open bundle ends, px
        stubChance: 0.05, // unused pin grows a short decorative stub
        stubLead: [16, 40],
        stubJog: [16, 40],
        peelRun: [20, 60], // horizontal run after a peel jog
        stubTail: [12, 34], // optional final stub segment
    },

    balance: {
        columns: 16, // density histogram resolution
        sparseRatio: 0.3, // columns below this fraction of mean get filler
        maxFillers: 1,
    },

    style: {
        bg: '#020308',
        trace: '#35d6f4',
        traceWidth: 3,
        glow: 'rgba(53, 214, 244, 0.55)',
        glowWidth: 9,
        chipGreen: '#5ee85e',
        chipPink: '#f25ad0',
        chipWidth: 2.5,
        pinLength: 8, // visual pin tab poking out of the chip wall
        glowBlur: 3.5,
    },
};

function scaleRange([lo, hi], factor) {
    return [lo * factor, hi * factor];
}

function scaleIntRange([lo, hi], factor) {
    return [Math.max(1, Math.round(lo * factor)), Math.max(1, Math.round(hi * factor))];
}

/**
 * Deep-clone CONFIG for a larger canvas. The board and station count grow by
 * factor; chip footprints stay at reference size so station spacing keeps
 * pace (scaling chip sizes with the board leaves span unchanged and the
 * spine gets walled off). Layout offsets and routing spans scale with the
 * board; lane pitch stays tied to chip size.
 */
export function scaleConfig(config, factor) {
    if (factor === 1) return config;

    const c = structuredClone(config);
    c.board.width *= factor;
    c.board.height *= factor;
    c.board.marginX *= factor;

    c.chips.stations = scaleIntRange(c.chips.stations, factor);
    c.chips.stackChance = Math.max(0.12, c.chips.stackChance / Math.sqrt(factor));
    c.chips.outerPad = scaleRange(c.chips.outerPad, factor);
    c.chips.singleOffset = scaleRange(c.chips.singleOffset, factor);
    c.chips.stackGap = scaleRange(c.chips.stackGap, factor);

    c.corridors.groupGap = scaleRange(c.corridors.groupGap, factor);

    c.routing.minStraight *= factor;
    c.routing.jogSpacing = scaleRange(c.routing.jogSpacing, factor);
    c.routing.jogSpan = scaleRange(c.routing.jogSpan, factor);
    c.routing.maxRun *= factor;
    c.routing.minOpenSpan *= factor;
    c.routing.minOpenSpanFloor *= factor;
    c.routing.pairGapStitch *= factor;
    c.routing.pairGapDirect *= factor;
    c.routing.pinDyMax *= factor;
    c.routing.crowdRadius *= factor;

    c.mesh.mergeReach *= factor;
    c.mesh.mergeJogMax *= factor;

    c.fray.endJitter = scaleRange(c.fray.endJitter, factor);
    c.fray.stubLead = scaleRange(c.fray.stubLead, factor);
    c.fray.stubJog = scaleRange(c.fray.stubJog, factor);
    c.fray.peelRun = scaleRange(c.fray.peelRun, factor);
    c.fray.stubTail = scaleRange(c.fray.stubTail, factor);

    const branchScale = Math.sqrt(factor);
    c.flows.branchCount = c.flows.branchCount.map((n) => Math.max(1, Math.round(n * branchScale)));

    c.balance.columns = Math.max(4, Math.round(c.balance.columns * factor));
    c.balance.maxFillers = Math.max(1, Math.round(c.balance.maxFillers * factor));

    return c;
}

/**
 * Deep-clone CONFIG for a wider board at native density. Where scaleConfig
 * zooms the whole drawing, this keeps every feature at reference size and
 * only adds horizontal room plus the stations to fill it -- the output
 * reads as several reference boards joined seamlessly side to side.
 */
export function stretchConfigX(config, factor) {
    if (factor === 1) return config;

    const c = structuredClone(config);
    c.board.width *= factor;
    c.chips.stations = scaleIntRange(c.chips.stations, factor);
    c.balance.columns = Math.round(c.balance.columns * factor);
    c.balance.maxFillers = Math.round(c.balance.maxFillers * factor);
    return c;
}
