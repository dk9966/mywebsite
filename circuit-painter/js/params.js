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
    cellSize: 6,
    wireLength: 40,
    cutOffLength: 1,
    straightness: 15,
    // Probability that a diagonal step is allowed. 1 = original behavior;
    // 0 = Manhattan routing (no slants). Anything in between probabilistically
    // suppresses long slants while keeping the look organic.
    diagonalChance: 1,
    // Probability per step of picking the modifier whose target direction
    // matches the most neighbor wire headings. 0 = each wire is independent
    // (original); 1 = wires aggressively run parallel to neighbors (buses).
    collectiveness: 0,
    // When true, wires that would render below cutOffLength are rolled back
    // (their cells released to the pool) so the algorithm gets another chance
    // to grow a long wire in that region. Pure quality-of-life for high
    // wireLength / cutOffLength combos; off by default to preserve behavior.
    prioritizeLongWires: false,
    // Global directional bias. -1 = strongly vertical, 0 = none, +1 = strongly
    // horizontal. Diagonals are treated as neutral. Implemented as another
    // probabilistic layer in pickModifierIndex; requires the expanded modifier
    // set so the wire can pivot 90 degrees onto the preferred axis.
    directionality: 0,
    showGrid: false,
    seed: 1,

    bgColor: 'rgba(51, 5, 51, 1)',
    fgColor: 'rgba(163, 204, 194, 1)',

    // Flow-field painting
    paintFlow: true,
    brushSize: 3,
    brushOpacity: 0.5,
    brushMode: 'brush',
    angleSmoothing: 0.3,
    flowInfluence: 1.0,
    autoRegenerate: true,
    showFlowGrid: true,
    clearFlowGrid() {},

    // Obstacles ("meshes" the wires must avoid). The keep-out buffer is what
    // guarantees a visible gap so wires never touch a mesh edge.
    obstaclesEnabled: false,
    obstacleCount: 5,
    obstacleSize: 8,
    // 0 = every obstacle uses obstacleSize exactly; 1 = w/h vary independently
    // by up to +/- obstacleSize around the base (clamped to min 2 cells).
    obstacleSizeRandomness: 0,
    obstacleKeepOut: 1,
    // Drag obstacle corners to resize after generation. Turn off flow painting
    // or disable this when painting the flow field.
    editObstacles: false,
    // 0 = perfectly even grid placement, 1 = fully random (current behavior).
    // Implemented as a continuous lerp between each obstacle's grid anchor and
    // an independently-random point in the usable area.
    obstacleSpacingRandomness: 1,
    // When true, a fraction of obstacles (qfpFraction) become QFP-style chips
    // with pin-seeded wires. The rest stay as regular blocks. Per-obstacle
    // tagging happens during generation so each obstacle's buffer and drawing
    // path are decided once and respected everywhere.
    qfpStyle: false,
    qfpFraction: 0.33,
    qfpPinSpacing: 2,

    regenerate() {},
    savePNG() {},
};
