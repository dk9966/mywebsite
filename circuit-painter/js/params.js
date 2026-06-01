// Tunables. Defaults are tuned for dense fill + straight routes.
// Slider ranges are widened (see main.js) on cellSize / wireLength /
// cutOffLength / straightness so the limits don't fight the look the user wants.

export function rgbaToHex(rgba) {
    const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) return '#000000';
    return '#' + [match[1], match[2], match[3]]
        .map((s) => parseInt(s, 10).toString(16).padStart(2, '0'))
        .join('');
}

export function hexToRgba(hex, alpha = 1) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return 'rgba(0, 0, 0, 1)';
    const r = parseInt(m[1], 16);
    const g = parseInt(m[2], 16);
    const b = parseInt(m[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export const params = {
    // Canvas size in pixels (routing grid is derived from this / cellSize).
    mapWidth: 1600,
    mapHeight: 810,

    // Routing
    cellSize: 9,
    wireLength: 40,
    cutOffLength: 1,
    straightness: 15,
    // Diagonal preference, shared by both modes. In the random walker it's the
    // probability a diagonal step is allowed. In the router it sets the diagonal
    // step cost: 1 = cheap diagonals (long 45 degree runs, diagonal grain);
    // lower = costlier diagonals, so routes stay rectilinear (H/V) with 45
    // degree chamfers at corners. Default tuned so slants are present but not
    // dominant -- rectilinear runs with noticeable 45 degree diagonal stretches.
    diagonalChance: 0.5,
    // Legacy shaped-route cost scaler. Corners ≤ 90° are always forbidden in
    // routing and chamfered on finished paths; only ±45° heading changes remain.
    turnSmoothness: 1,
    // Probability per step of picking the modifier whose target direction
    // matches the most neighbor wire headings. 0 = each wire is independent
    // (original); 1 = wires aggressively run parallel to neighbors (buses).
    collectiveness: 0,
    // When true, wires that would render below cutOffLength are rolled back
    // (their cells released to the pool) so the algorithm gets another chance
    // to grow a long wire in that region. Pure quality-of-life for high
    // wireLength / cutOffLength combos; off by default to preserve behavior.
    prioritizeLongWires: false,
    // Post-process that fuses any two random-walk wires whose endpoints are
    // cardinally adjacent. After joining, the former join point is just an
    // interior bend (no end pad), so chains read as one continuous trace.
    // QFP pin wires are excluded -- their endpoint semantics are load-bearing.
    joinEndpoints: false,
    // Global directional bias. -1 = strongly vertical, 0 = none, +1 = strongly
    // horizontal. Diagonals are treated as neutral. Implemented as another
    // probabilistic layer in pickModifierIndex.
    directionality: 0,
    showGrid: false,
    showCircuits: true,
    // Manual wire editing. When on, every trace shows draggable joint handles:
    // drag a joint to move it, click a corner (or the trace body near one) to
    // bevel it into a 45 degree slant. Edits live on each wire's `points`
    // override and are discarded on the next full rebuild (any slider change).
    editWires: false,
    // Pin buses: straight / slant traces from QFP pins. When on, replaces the
    // greedy random-walk fill. Roughly half the pins link to another chip's pin;
    // the rest wander out and stop.
    showBuses: true,
    // Minimum cells per straight or 45° run on pin-bus routes before the next bend
    // (hard constraint in A*; raising this lengthens visible slants and straights).
    pinBusSlantLength: 10,
    // Length a straight run may reach before the router is forced to bend 45°,
    // so a trace can't arrow straight forever: it slants off, runs straight,
    // then slants back.
    pinBusStraightMax: 18,
    // How many parallel wires the bus carries. If the facing chip edge has fewer
    // pins than this, the nearest pins around the chip's corner are pulled in to
    // make up the count.
    pinBusWireCount: 7,
    seed: 1,

    bgColor: 'rgba(51, 5, 51, 1)',
    fgColor: 'rgba(163, 204, 194, 1)',

    // Bus mode. The default look: the free space between chips is carved into
    // rectangular gaps, each gap is packed with parallel straight traces (a
    // bus), and the buses are linked across gaps by 45 degree slants running off
    // each line's ends. Turning this off restores the flow-field / random-walk
    // painting behavior.
    busMode: false,
    // Draw the gap-rect outlines as a faint guide. Off just shows the buses.
    showGapRects: false,
    // Upper bound on gap rects. Placement otherwise packs until the free space
    // is full, so this mostly acts as a ceiling.
    gapRectCount: 400,
    // Smallest rect (per side, in cells) worth keeping; smaller fits are
    // discarded so a bus always has room for a few lines.
    gapRectMinSize: 6,
    // Largest a rect is allowed to grow (per side, in cells). Bigger = fewer,
    // chunkier buses.
    gapRectMaxSize: 28,
    // Cells of empty space between adjacent bus lines. 0 packs them tight.
    busLineSpacing: 1,
    // When on, each line's ends are routed to the nearest other bus with a 45
    // degree slant, so adjacent buses visibly link into one network. Off leaves
    // the buses as isolated parallel-line blocks.
    connectBuses: true,
    // How far (roughly, in cells) a connecting slant may reach for the bus it
    // links to. Higher = slants can bridge wider channels; lower = only the
    // closest buses link.
    busTailLength: 5,
    // How buses are placed in free space: random gap rects, or centerline spine.
    busSpineMode: 'gapRects',
    // Centerline / corridor extraction (shared with circuit-painter-2).
    centerlineMinLength: 3,
    centerlineSimplify: 0.35,
    // Cells trimmed from corridor ends near junctions when packing centerline buses.
    corridorJunctionInset: 2,
    // Cap parallel lines per corridor (like gapRectMaxSize for width).
    corridorMaxLines: 28,

    // Flow-field painting
    paintFlow: false,
    brushSize: 3,
    brushOpacity: 0.5,
    brushMode: 'brush',
    angleSmoothing: 0.3,
    flowInfluence: 1.0,
    autoRegenerate: true,
    showFlowGrid: false,
    clearFlowGrid() {},

    // Obstacles ("meshes" the wires must avoid). The keep-out buffer is what
    // guarantees a visible gap so wires never touch a mesh edge.
    obstaclesEnabled: true,
    obstacleCount: 14,
    obstacleSize: 14,
    // 0 = every obstacle uses obstacleSize exactly; 1 = w/h vary independently
    // by up to +/- obstacleSize around the base (clamped to min 2 cells).
    obstacleSizeRandomness: 0.4,
    obstacleKeepOut: 1,
    // Drag obstacle corners to resize after generation. Turn off flow painting
    // or disable this when painting the flow field.
    editObstacles: false,
    // 0 = perfectly even grid placement, 1 = fully random (current behavior).
    // Implemented as a continuous lerp between each obstacle's grid anchor and
    // an independently-random point in the usable area.
    obstacleSpacingRandomness: 1,
    // Hard floor on the edge-to-edge gap between any two obstacles, in cells.
    // Distinct from obstacleKeepOut (which is the wire keep-out buffer around
    // each obstacle). When increased, obstacles get *shifted* apart by a
    // relaxation pass after initial placement -- so the slider visibly spreads
    // them out instead of just rejecting more placements.
    obstacleMinSpacing: 6,
    // When true, a fraction of obstacles (qfpFraction) become QFP-style chips
    // with pin-seeded wires. The rest stay as regular blocks. Per-obstacle
    // tagging happens during generation so each obstacle's buffer and drawing
    // path are decided once and respected everywhere.
    qfpStyle: true,
    qfpFraction: 0.45,
    qfpSize: 14,
    qfpSizeRandomness: 0.25,
    qfpPinSpacing: 2,

    regenerate() {},
    savePNG() {},
};
