import { CONFIG } from './config.js';
import { generate } from './core/index.js';
import { render } from './render/canvasRender.js';
import { modelToSvg } from './render/svg.js';

const app = document.createElement('div');
app.className = 'flow-app';

const canvas = document.createElement('canvas');
canvas.className = 'flow-app__canvas';
canvas.width = CONFIG.board.width;
canvas.height = CONFIG.board.height;

const toolbar = document.createElement('div');
toolbar.className = 'flow-toolbar';
toolbar.innerHTML = `
    <span class="flow-toolbar__label">seed</span>
    <input class="flow-toolbar__seed" type="number" value="1">
    <button class="flow-toolbar__button" data-action="regenerate">Regenerate</button>
    <button class="flow-toolbar__button" data-action="export">Export SVG</button>
`;

app.append(canvas, toolbar);
document.body.appendChild(app);

const seedInput = toolbar.querySelector('.flow-toolbar__seed');
const ctx = canvas.getContext('2d');
let model = null;

function rebuild() {
    const seed = Number(seedInput.value) || 0;
    model = generate(seed, CONFIG);
    render(ctx, model, CONFIG);
}

toolbar.addEventListener('click', (e) => {
    const action = e.target.dataset?.action;
    if (action === 'regenerate') {
        seedInput.value = String((Number(seedInput.value) || 0) + 1);
        rebuild();
    } else if (action === 'export') {
        const blob = new Blob([modelToSvg(model, CONFIG)], { type: 'image/svg+xml' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `circuit-flow-${seedInput.value}.svg`;
        a.click();
        URL.revokeObjectURL(a.href);
    }
});

seedInput.addEventListener('change', rebuild);

rebuild();
