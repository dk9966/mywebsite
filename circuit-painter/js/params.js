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
    // Routing
    cellSize: 7,
    wireLength: 40,
    cutOffLength: 1,
    straightness: 15,
    // Probability that a diagonal step is allowed. 1 = original behavior;
    // 0 = Manhattan routing (no slants). Anything in between probabilistically
    // suppresses long slants while keeping the look organic.
    diagonalChance: 1,
    // How hard to soften corners. 0 = original behavior (sharp 90 degree turns
    // allowed). 1 = no right angles anywhere -- every would-be 90 degree corner
    // is replaced by a 45 degree bend (random-walk wires) or routed around with
    // a diagonal staircase (A* trunk lines). Values in between veto right angles
    // probabilistically.
    turnSmoothness: 0,
    // Probability per step of picking the modifier whose target direction
    // matches the most neighbor wire headings. 0 = each wire is independent
    // (original); 1 = wires aggressively run parallel to neighbors (buses).
    collectiveness: 0,
    // When true, wires that would render below cutOffLength are rolled back
    // (their cells released to the pool) so the algorithm gets another chance
    // to grow a long wire in that region. Pure quality-of-life for high
    // wireLength / cutOffLength combos; off by default to preserve behavior.
    prioritizeLongWires: false,
    // Number of A* "trunk" lines laid before the random-walk fill. Each goes
    // from a random edge cell to (preferably) the opposite edge, routing
    // around everything that's already on the board. Endpoints sit on the
    // canvas border so the wire renders without end pads -- the trace reads
    // as running off the edge of the board, not terminating at a via.
    // This is the only reliable way to get a wire that visibly spans the
    // whole canvas; pushing wireLength alone can't guarantee it because the
    // random walker has no backtracking.
    trunkWireCount: 8,
    // When true, hide fill / pin wires and draw only A* trunk lines. Display
    // only -- routing is unchanged.
    trunksOnly: false,
    // Post-process that fuses any two random-walk wires whose endpoints are
    // cardinally adjacent. After joining, the former join point is just an
    // interior bend (no end pad), so chains read as one continuous trace.
    // QFP pin wires and trunks are excluded -- their endpoint semantics are
    // load-bearing.
    joinEndpoints: false,
    // Global directional bias. -1 = strongly vertical, 0 = none, +1 = strongly
    // horizontal. Diagonals are treated as neutral. Implemented as another
    // probabilistic layer in pickModifierIndex; requires the expanded modifier
    // set so the wire can pivot 90 degrees onto the preferred axis.
    directionality: 0,
    showGrid: false,
    seed: 1,

    bgColor: 'rgba(51, 5, 51, 1)',
    fgColor: 'rgba(163, 204, 194, 1)',

    // Bus mode. The default look: instead of the random-walk fill, the free
    // space between obstacles is carved into large rectangles ("gap rects"),
    // each packed with a bus of parallel traces. Trace ends bend at 45 degrees
    // (never 90) so adjacent buses -- which alternate orientation in a
    // checkerboard -- can reach across the gap and link up. Turning this off
    // restores the original flow-field / random-walk behavior.
    busMode: true,
    // Draw the gap-rect outlines as a guide. Off just shows the buses.
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
    busLineSpacing: 4,
    // When on, each line's 45 degree tail runs out past the rect edge into the
    // gap toward the neighbor bus, so buses visibly link. Off keeps tails
    // inside their rect.
    connectBuses: true,
    // Max length (cells) of the 45 degree tail on each end of a bus line. The
    // tail stops early at any obstacle or board edge.
    busTailLength: 5,

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
    obstacleCount: 90,
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
    qfpPinSpacing: 2,

    regenerate() {},
    savePNG() {},
};
