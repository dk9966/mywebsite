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
    cellSize: 5,
    showGrid: false,
    seed: 1,

    bgColor: 'rgba(51, 5, 51, 1)',
    fgColor: 'rgba(163, 204, 194, 1)',

    // Greedy random-walk router (ported from circuit-painter).
    wireLength: 40,
    cutOffLength: 1,
    straightness: 15,
    diagonalChance: 0.5,
    turnSmoothness: 1,
    // Per-step chance of choosing the direction matching the most neighbor
    // wires -- this is what makes traces run parallel and read as buses.
    collectiveness: 0.5,
    prioritizeLongWires: false,
    trunkWireCount: 8,
    trunksOnly: false,
    joinEndpoints: false,
    directionality: 0,
    // How strongly the walker obeys the flow grid (0 = ignore, 1 = always).
    flowInfluence: 1.0,

    // Centerline (medial-axis) guide.
    centerlineMinLength: 3,
    centerlineSimplify: 0.35,
    // Draw the bare medial-axis lines as a faint guide on top of the traces.
    showCenterlines: false,
    // Feed centerline directions into the flow grid so wires align to the
    // nearest corridor's axis.
    alignToCenterlines: true,
    // Flow strength stamped on a centerline cell (0-255); spreads outward.
    centerlineStrength: 255,
    // Strength lost per cell of spread away from a centerline. Smaller = the
    // corridor axis reaches farther into the gap.
    centerlineFalloff: 24,
    // Draw the derived flow field arrows (debug).
    showFlowField: false,

    obstaclesEnabled: true,
    obstacleCount: 90,
    obstacleSize: 14,
    obstacleSizeRandomness: 0.4,
    obstacleKeepOut: 1,
    editObstacles: false,
    obstacleSpacingRandomness: 1,
    obstacleMinSpacing: 6,
    qfpStyle: true,
    qfpFraction: 0.45,
    qfpPinSpacing: 2,

    regenerate() {},
    savePNG() {},
};
