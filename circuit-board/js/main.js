import { CONFIG } from './config.js';
import { generate } from './core/index.js';
import { render } from './render/canvas.js';
import { modelToSvg } from './render/svg.js';

const app = document.createElement('div');
app.className = 'board-app';

const canvas = document.createElement('canvas');
canvas.className = 'board-app__canvas';
canvas.width = CONFIG.board.width;
canvas.height = CONFIG.board.height;

const toolbar = document.createElement('div');
toolbar.className = 'board-toolbar';
toolbar.innerHTML = `
    <span class="board-toolbar__label">seed</span>
    <input class="board-toolbar__seed" type="number" value="1">
    <select class="board-toolbar__style">
        ${Object.keys(CONFIG.styles).map((s) => `<option value="${s}">${s}</option>`).join('')}
    </select>
    <button class="board-toolbar__button" data-action="regenerate">Regenerate</button>
    <button class="board-toolbar__button" data-action="export">Export SVG</button>
`;

app.append(canvas, toolbar);
document.body.appendChild(app);

const seedInput = toolbar.querySelector('.board-toolbar__seed');
const styleSelect = toolbar.querySelector('.board-toolbar__style');
const ctx = canvas.getContext('2d');
let model = null;

function rebuild() {
    const seed = Number(seedInput.value) || 0;
    model = generate(seed, CONFIG);
    render(ctx, model, CONFIG, { style: styleSelect.value });
}

toolbar.addEventListener('click', (e) => {
    const action = e.target.dataset?.action;
    if (action === 'regenerate') {
        seedInput.value = String((Number(seedInput.value) || 0) + 1);
        rebuild();
    } else if (action === 'export') {
        const blob = new Blob(
            [modelToSvg(model, CONFIG, { style: styleSelect.value })],
            { type: 'image/svg+xml' },
        );
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `circuit-board-${seedInput.value}.svg`;
        a.click();
        URL.revokeObjectURL(a.href);
    }
});

seedInput.addEventListener('change', rebuild);
styleSelect.addEventListener('change', () => render(ctx, model, CONFIG, { style: styleSelect.value }));

rebuild();
