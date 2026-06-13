import { CONFIG } from './config.js';
import { generate } from './core/index.js';
import { renderCanvas } from './render/canvas.js';
import { modelToSvg } from './render/svg.js';

const canvas = document.querySelector('#roadCanvas');
const seedInput = document.querySelector('#seedInput');
const styleSelect = document.querySelector('#styleSelect');
const statsText = document.querySelector('#statsText');
const renderButton = document.querySelector('#renderButton');
const randomButton = document.querySelector('#randomButton');
const downloadButton = document.querySelector('#downloadButton');

let currentModel = null;

function render() {
    const seed = Math.max(1, Number(seedInput.value) || 1);
    const style = styleSelect.value;
    seedInput.value = String(seed);
    currentModel = generate(seed, CONFIG);
    renderCanvas(canvas, currentModel, CONFIG, { style });
    statsText.textContent = [
        `Seed ${seed}`,
        `${currentModel.parts.length} parts`,
        `${currentModel.traces.length} traces`,
        `${currentModel.vias.length} vias`,
    ].join(' / ');
}

function downloadSvg() {
    if (!currentModel) render();
    const style = styleSelect.value;
    const svg = modelToSvg(currentModel, CONFIG, { style });
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pcb-road-seed-${currentModel.seed}-${style}.svg`;
    link.click();
    URL.revokeObjectURL(url);
}

renderButton.addEventListener('click', render);
styleSelect.addEventListener('change', render);
seedInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') render();
});
randomButton.addEventListener('click', () => {
    seedInput.value = String(Math.floor(Math.random() * 9999) + 1);
    render();
});
downloadButton.addEventListener('click', downloadSvg);

render();

