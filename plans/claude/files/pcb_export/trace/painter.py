"""
Procedural PCB trace painter.

Port of https://github.com/ArtBIT/circuitboard-painter (wire.js, main.js):
wires grow octilinearly with a straightness bias on a grid where component
cells are pre-blocked, then the algorithm repeatedly seeds new wires from
any cell that is still free until the gap space is filled.

Wires never overlap and never touch a blocked cell. Diagonals are checked
for crossover so two diagonal wires can't share the same X.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .grid import RoutingGrid

DIRS_8: tuple[tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1), (1, 0),
    (1, 1),   (0, 1),  (-1, 1), (-1, 0),
)

SIDE_TO_DIR = {"N": 1, "S": 5, "E": 3, "W": 7}


@dataclass(frozen=True)
class PinSeed:
    """One pin's stub cell plus the outward 8-direction index."""

    cell: tuple[int, int]
    direction: int
    anchor: tuple[float, float]


@dataclass
class PainterConfig:
    wire_length: int = 220
    straightness: float = 14.0
    cut_off_cells: int = 1
    seed: int = 42
    clearance_cells: int = 0


def _in_bounds(x: int, y: int, w: int, h: int) -> bool:
    return 0 < x < w - 1 and 0 < y < h - 1


def _valid_diagonal(idx: int, x: int, y: int, used: list[list[bool]]) -> bool:
    """Anti-crossover: at least one cardinal neighbour must still be free."""
    if idx == 0:
        return (not used[x + 1][y]) or (not used[x][y + 1])
    if idx == 2:
        return (not used[x - 1][y]) or (not used[x][y + 1])
    if idx == 4:
        return (not used[x - 1][y]) or (not used[x][y - 1])
    if idx == 6:
        return (not used[x + 1][y]) or (not used[x][y - 1])
    return True


def _random_start_dir(
    x: int, y: int, used: list[list[bool]], w: int, h: int, rng: random.Random
) -> int:
    options = list(range(8))
    rng.shuffle(options)
    for d in options:
        dx, dy = DIRS_8[d]
        nx, ny = x + dx, y + dy
        if _in_bounds(nx, ny, w, h) and not used[nx][ny]:
            return d
    return 0


def grow_wire(
    start: tuple[int, int],
    used: list[list[bool]],
    *,
    w: int,
    h: int,
    wire_length: int,
    straightness: float,
    rng: random.Random,
    initial_dir: int | None = None,
) -> list[tuple[int, int]]:
    """Grow a single ArtBIT-style wire from `start`; mutates `used` in place."""
    sx, sy = start
    if not _in_bounds(sx, sy, w, h) or used[sx][sy]:
        return []

    cells: list[tuple[int, int]] = [start]
    used[sx][sy] = True

    if initial_dir is not None:
        last = (initial_dir + 4) % 8
    else:
        last = _random_start_dir(sx, sy, used, w, h, rng)

    while len(cells) < wire_length:
        cur = cells[-1]
        modifiers = [0, 1, -1] if rng.random() > 0.5 else [0, -1, 1]
        moved = False
        while modifiers and not moved:
            r = rng.random() ** straightness
            pick = min(int(r * len(modifiers)), len(modifiers) - 1)
            choice = modifiers.pop(pick)

            di = (last + 4 + choice + 8) % 8
            dx, dy = DIRS_8[di]
            nx, ny = cur[0] + dx, cur[1] + dy
            if not _in_bounds(nx, ny, w, h):
                continue
            if used[nx][ny]:
                continue
            if not _valid_diagonal(di, nx, ny, used):
                continue
            cells.append((nx, ny))
            used[nx][ny] = True
            last = (last + choice + 8) % 8
            moved = True
        if not moved:
            break
    return cells


def _dilate_blocked(used: list[list[bool]], w: int, h: int, n: int) -> None:
    """Expand the blocked region by `n` cardinal rings (Manhattan dilation)."""
    for _ in range(n):
        adds: list[tuple[int, int]] = []
        for x in range(w):
            row = used[x]
            for y in range(h):
                if row[y]:
                    continue
                if (
                    (x + 1 < w and used[x + 1][y])
                    or (x > 0 and used[x - 1][y])
                    or (y + 1 < h and row[y + 1])
                    or (y > 0 and row[y - 1])
                ):
                    adds.append((x, y))
        for x, y in adds:
            used[x][y] = True


def paint_traces(
    grid: RoutingGrid,
    pin_seeds: list[PinSeed],
    config: PainterConfig,
) -> tuple[list[list[tuple[int, int]]], list[bool]]:
    """
    Paint wires across `grid`.

    Returns:
        (paths, pin_seeded) where `paths[i]` is a list of cell coords and
        `pin_seeded[i]` is True iff that wire grew from a pin stub.
    """
    rng = random.Random(config.seed)
    w, h = grid.cols, grid.rows
    used: list[list[bool]] = [row[:] for row in grid.blocked]
    if config.clearance_cells > 0:
        _dilate_blocked(used, w, h, config.clearance_cells)

    paths: list[list[tuple[int, int]]] = []
    pin_seeded: list[bool] = []

    for seed in pin_seeds:
        cx, cy = seed.cell
        if not _in_bounds(cx, cy, w, h) or used[cx][cy]:
            continue
        path = grow_wire(
            seed.cell,
            used,
            w=w,
            h=h,
            wire_length=config.wire_length,
            straightness=config.straightness,
            rng=rng,
            initial_dir=seed.direction,
        )
        if len(path) > config.cut_off_cells:
            paths.append(path)
            pin_seeded.append(True)

    pool: list[tuple[int, int]] = [
        (x, y) for x in range(w) for y in range(h) if not used[x][y]
    ]
    rng.shuffle(pool)
    for cell in pool:
        cx, cy = cell
        if used[cx][cy]:
            continue
        path = grow_wire(
            cell,
            used,
            w=w,
            h=h,
            wire_length=config.wire_length,
            straightness=config.straightness,
            rng=rng,
        )
        if len(path) > config.cut_off_cells:
            paths.append(path)
            pin_seeded.append(False)

    return paths, pin_seeded
