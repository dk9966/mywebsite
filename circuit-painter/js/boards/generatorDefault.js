// Default QFP + SOIC layout for circuit generator snapshots.

export const GENERATOR_DEFAULT_NAME = 'Generator default';

export const GENERATOR_DEFAULT_PARAMS = {
    seed: 1,
    showBuses: true,
    generatorChipsOnly: true,
    generatorQfpCount: 4,
    generatorSoicCount: 4,
    qfpStyle: true,
    qfpSize: 14,
    obstacleMinSpacing: 4,
    obstacleKeepOut: 1,
    pinBusWireCount: 4,
    pinBusSlantLength: 10,
    pinBusStraightMax: 18,
    routeClearanceTarget: 6,
    routeClearanceBias: 0.9,
    pinBusRouteMargin: 12,
    pinBusMaxDetourRatio: 1.65,
    pinBusCorridorWeight: 0.22,
    pinBusSpineRatio: 0.52,
};

// Mesh layout from saved Snapshot 2 (Jun 9).
export const GENERATOR_DEFAULT_OBSTACLES = [
    { x: 13, y: 20, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 81, y: 13, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 132, y: 25, w: 14, h: 14, kind: 'qfp', qfp: true, rot: 0 },
    { x: 42, y: 38, w: 19, h: 5, kind: 'soic', qfp: false, rot: 2 },
    { x: 108, y: 38, w: 12, h: 6, kind: 'soic', qfp: false, rot: 0 },
    { x: 146, y: 36, w: 6, h: 12, kind: 'soic', qfp: false, rot: 1 },
    { x: 44, y: 16, w: 17, h: 13, kind: 'heatsink', qfp: false, rot: 0, auxPinSide: 'left', auxPinOffsets: [3, 11] },
    { x: 81, y: 37, w: 12, h: 9, kind: 'heatsink', qfp: false, rot: 0, auxPinSide: 'right', auxPinOffsets: [1, 7] },
];
