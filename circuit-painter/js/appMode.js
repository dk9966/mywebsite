// Which surface we're running: manual painter vs auto-generated buses.

export const MODES = {
    painter: {
        defaults: {
            showBuses: false,
            showGreedyCircuits: false,
            editWires: true,
            editObstacles: true,
            busMode: false,
        },
    },
    generator: {
        defaults: {
            showBuses: true,
            showGreedyCircuits: false,
            editWires: false,
            editObstacles: true,
            busMode: false,
            generatorChipsOnly: true,
            generatorQfpCount: 4,
            generatorSoicCount: 4,
            qfpStyle: true,
            obstacleMinSpacing: 4,
        },
    },
};

export function resolveAppMode() {
    return window.__CIRCUIT_MODE === 'generator' ? 'generator' : 'painter';
}

export function applyModeDefaults(params, mode) {
    Object.assign(params, MODES[mode].defaults);
}

export function isPainterMode(mode) {
    return mode === 'painter';
}

export function isGeneratorMode(mode) {
    return mode === 'generator';
}
