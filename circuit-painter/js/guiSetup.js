import { params, rgbaToHex, hexToRgba } from './params.js';
import { isPainterMode } from './appMode.js';

function addObstacleControls(folder, { edit, recreate, redraw, mode }) {
    folder.add(params, 'obstaclesEnabled').name('Enable Obstacles').onChange(recreate);
    if (isPainterMode(mode)) {
        folder.add(params, 'obstacleCount', 1, 500, 1).name('Count').onChange(recreate);
        folder.add(params, 'obstacleSize', 2, 40, 1).name('Size (cells)').onChange(recreate);
        folder.add(params, 'obstacleSizeRandomness', 0, 1, 0.01)
            .name('Size Randomness').onChange(recreate);
        folder.add(params, 'qfpFraction', 0, 1, 0.01).name('QFP Fraction').onChange(recreate);
        folder.add(params, 'qfpSizeRandomness', 0, 1, 0.01)
            .name('QFP Size Randomness').onChange(recreate);
    } else {
        folder.add(params, 'generatorQfpCount', 1, 20, 1).name('QFP Count').onChange(recreate);
        folder.add(params, 'generatorSoicCount', 1, 20, 1).name('SOIC Count').onChange(recreate);
        folder.add(params, 'qfpSize', 2, 40, 1).name('Chip Size').onChange(recreate);
    }
    folder.add(params, 'obstacleKeepOut', 0, 5, 1).name('Keep-out').onChange(recreate);
    folder.add(params, 'obstacleMinSpacing', 0, 20, 1).name('Min Spacing').onChange(recreate);
    if (edit) {
        folder.add(params, 'editObstacles').name('Edit Obstacles').onChange(redraw);
    }
    folder.add(params, 'obstacleSpacingRandomness', 0, 1, 0.01)
        .name('Spacing Randomness').onChange(recreate);
    folder.add(params, 'qfpStyle').name('QFP Style').onChange(recreate);
    if (isPainterMode(mode)) {
        folder.add(params, 'qfpSize', 2, 40, 1).name('QFP Size (cells)').onChange(recreate);
    }
    folder.add(params, 'qfpPinSpacing', 1, 8, 1).name('Pin Spacing').onChange(recreate);
    folder.open();
}

export function buildGui(gui, mode, {
    recreate,
    recreateImmediate,
    redraw,
    resizeLayout,
    clearWireOverlay,
}) {
    gui.add(params, 'cellSize', 2, 80, 1).onChange(recreate);
    gui.add(params, 'mapWidth', 500, 2000, 10).name('Map Width')
        .onChange(() => { resizeLayout(); recreate(); });
    gui.add(params, 'mapHeight', 50, 1200, 10).name('Map Height')
        .onChange(() => { resizeLayout(); recreate(); });

    if (isPainterMode(mode)) {
        gui.add(params, 'showCircuits').name('Show Circuits').onChange(redraw);
        gui.add(params, 'editWires').name('Edit Wires').onChange(redraw);
        gui.add(params, 'showGrid').name('Show Grid').onChange(redraw);
    } else {
        gui.add(params, 'showCircuits').name('Show Circuits').onChange(redraw);
        gui.add(params, 'editWires').name('Edit Wires').onChange(redraw);
        gui.add(params, 'showBuses').name('Show Buses').onChange(recreate);
        gui.add(params, 'pinBusSlantLength', 1, 30, 1).name('Slant Length').onChange(recreate);
        gui.add(params, 'pinBusStraightMax', 2, 60, 1).name('Straight Max').onChange(recreate);
        gui.add(params, 'pinBusWireCount', 1, 16, 1).name('Bus Wires').onChange(recreate);
    }

    gui.add(params, 'regenerate').name('Regenerate');
    gui.add(params, 'seed', 0, 10000, 1).name('Seed').onChange(() => {
        clearWireOverlay();
        recreateImmediate();
    });

    const obstaclesFolder = gui.addFolder('Obstacles');
    addObstacleControls(obstaclesFolder, {
        edit: true,
        recreate,
        redraw,
        mode,
    });

    Object.defineProperty(params, 'bgColorHex', {
        get: () => rgbaToHex(params.bgColor),
        set: (hex) => { params.bgColor = hexToRgba(hex); redraw(); },
    });
    Object.defineProperty(params, 'fgColorHex', {
        get: () => rgbaToHex(params.fgColor),
        set: (hex) => { params.fgColor = hexToRgba(hex); redraw(); },
    });
    gui.addColor(params, 'bgColorHex').name('Background Color');
    gui.addColor(params, 'fgColorHex').name('Foreground Color');
    gui.add(params, 'savePNG').name('Save PNG');
}
