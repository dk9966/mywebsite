// Right-click an obstacle's center handle to pop Rotate / Delete actions. The
// hit test reuses the same center-handle target the move tool uses.

import { getCanvas } from './canvas.js';
import { hitTestCenter, removeObstacle, rotateObstacle } from './obstacles.js';

let menuEl = null;

export function initObstacleMenu({ onChange, onRedraw }) {
    const canvas = getCanvas();

    canvas.addEventListener('contextmenu', (e) => {
        const rect = canvas.getBoundingClientRect();
        const hit = hitTestCenter(e.clientX - rect.left, e.clientY - rect.top, canvas);
        if (!hit) {
            hideMenu();
            return;
        }
        e.preventDefault();
        showMenu(e.clientX, e.clientY, hit.obstacle, onChange, onRedraw);
    });

    // Dismiss on any click outside the menu, on Escape, or when the view shifts.
    document.addEventListener('mousedown', (e) => {
        if (menuEl && !menuEl.contains(e.target)) hideMenu();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideMenu();
    });
    document.addEventListener('scroll', hideMenu, true);
    window.addEventListener('resize', hideMenu);
}

function showMenu(clientX, clientY, obstacle, onChange, onRedraw) {
    hideMenu();

    menuEl = document.createElement('div');
    menuEl.className = 'obstacle-menu';
    menuEl.style.left = `${clientX}px`;
    menuEl.style.top = `${clientY}px`;

    const rotateBtn = document.createElement('button');
    rotateBtn.className = 'obstacle-menu__rotate';
    rotateBtn.textContent = 'Rotate';
    rotateBtn.addEventListener('click', () => {
        rotateObstacle(obstacle);
        if (onChange) onChange();
        else if (onRedraw) onRedraw();
    });

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'obstacle-menu__delete';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', () => {
        removeObstacle(obstacle);
        hideMenu();
        if (onChange) onChange();
    });

    menuEl.append(rotateBtn, deleteBtn);
    document.body.appendChild(menuEl);
}

function hideMenu() {
    if (menuEl) {
        menuEl.remove();
        menuEl = null;
    }
}
