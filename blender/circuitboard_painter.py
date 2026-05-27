"""
Port of ArtBIT/circuitboard-painter wire generator.

Reference: https://github.com/ArtBIT/circuitboard-painter (js/wire.js, js/main.js).

The painter walks a 2D grid one cell at a time, choosing 8-direction moves
biased toward continuing in the same direction. A `straightness` exponent
controls how strongly it prefers to go straight; higher means longer, cleaner
runs that look like real PCB traces. Wires never re-enter occupied cells, so
the algorithm naturally fills the available space with a tangle of routes.

This module is pure Python and Blender-free. The Blender driver
(`build_painter_traces.py`) marks component footprints as blocked cells before
calling :func:`generate_wires`.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


# 8-direction lookup matching the reference order:
# 0:[-1,-1] TL, 1:[0,-1] up,    2:[1,-1] TR, 3:[1, 0] right,
# 4:[ 1, 1] BR, 5:[0, 1] down,  6:[-1,1] BL, 7:[-1, 0] left.
_DIRS: tuple[tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1), (1, 0),
    (1, 1), (0, 1), (-1, 1), (-1, 0),
)


@dataclass
class PainterParams:
    """Knobs from the original ArtBIT painter, plus a wire-spacing halo."""

    wire_length: int = 80           # max cells per wire
    cut_off_length: int = 2         # discard wires shorter than this
    straightness: float = 14.0      # higher = longer straight runs
    wire_spacing: int = 0           # cells of halo blocked around each finished
                                    #   wire so neighboring wires keep distance
    seed: int = 1


@dataclass
class PainterResult:
    """Output of :func:`generate_wires` — simplified polylines + raw lengths."""

    wires: list[list[tuple[int, int]]]
    raw_cell_counts: list[int]


# ---------------------------------------------------------------------------
# Diagonal-crossover guard (from wire.js isValidDiagonalMove).
#
# A diagonal move from (cx, cy) to (nx, ny) is forbidden if BOTH cardinal
# neighbors of (nx, ny) that lie on the "other side" of the diagonal are
# already occupied — that situation means another wire's diagonal is crossing
# this one in an X shape. Allowing it produces visually crossed traces.
# ---------------------------------------------------------------------------
def _diagonal_ok(direction_index: int, nx: int, ny: int,
                 blocked: list[list[bool]], w: int, h: int) -> bool:
    if direction_index == 0:  # moved into TL diagonal
        return (nx + 1 < w and not blocked[nx + 1][ny]) or \
               (ny + 1 < h and not blocked[nx][ny + 1])
    if direction_index == 2:  # TR
        return (nx - 1 >= 0 and not blocked[nx - 1][ny]) or \
               (ny + 1 < h and not blocked[nx][ny + 1])
    if direction_index == 4:  # BR
        return (nx - 1 >= 0 and not blocked[nx - 1][ny]) or \
               (ny - 1 >= 0 and not blocked[nx][ny - 1])
    if direction_index == 6:  # BL
        return (nx + 1 < w and not blocked[nx + 1][ny]) or \
               (ny - 1 >= 0 and not blocked[nx][ny - 1])
    return True


def _initial_direction(x: int, y: int,
                       blocked: list[list[bool]], w: int, h: int,
                       rng: random.Random) -> int:
    avail = [0, 1, 2, 3, 4, 5, 6, 7]
    rng.shuffle(avail)
    for di in avail:
        dx, dy = _DIRS[di]
        nx, ny = x + dx, y + dy
        if 0 < nx < w - 1 and 0 < ny < h - 1 and not blocked[nx][ny]:
            return di
    return 0


def _grow_wire(start: tuple[int, int],
               blocked: list[list[bool]], w: int, h: int,
               params: PainterParams, rng: random.Random) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = [start]
    last_dir = _initial_direction(start[0], start[1], blocked, w, h, rng)

    while len(cells) < params.wire_length:
        cx, cy = cells[-1]

        # Coin-flip the order of the two side turns so neither direction is
        # subtly preferred when straightness picks a non-zero modifier.
        modifiers = [0, 1, -1] if rng.random() > 0.5 else [0, -1, 1]
        chosen = False

        while modifiers:
            # Power-curve weighted pick over the remaining modifiers; high
            # straightness collapses this toward index 0 (== keep going).
            idx = int((rng.random() ** params.straightness) * len(modifiers))
            mod = modifiers.pop(idx)
            di = (last_dir + 4 + mod + 8) % 8
            dx, dy = _DIRS[di]
            nx, ny = cx + dx, cy + dy

            if not (0 < nx < w - 1 and 0 < ny < h - 1):
                continue
            if blocked[nx][ny]:
                continue
            if not _diagonal_ok(di, nx, ny, blocked, w, h):
                continue

            cells.append((nx, ny))
            blocked[nx][ny] = True
            last_dir = (last_dir + mod + 8) % 8
            chosen = True
            break

        if not chosen:
            break

    return cells


def _simplify(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Collapse colinear runs so each wire becomes a polyline of corners."""
    if len(cells) < 3:
        return list(cells)
    out: list[tuple[int, int]] = [cells[0]]
    for i in range(1, len(cells) - 1):
        ax, ay = cells[i - 1]
        bx, by = cells[i]
        cx, cy = cells[i + 1]
        if (bx - ax, by - ay) != (cx - bx, cy - by):
            out.append((bx, by))
    out.append(cells[-1])
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_wires(blocked: list[list[bool]],
                   params: PainterParams) -> PainterResult:
    """Fill all free cells of `blocked` with painter-style wires.

    Mutates `blocked` in place: every cell visited by a wire (and its halo,
    if `wire_spacing > 0`) becomes True. Each wire is returned as a
    simplified polyline of corner cells; colinear runs are collapsed.
    """
    if not blocked:
        return PainterResult(wires=[], raw_cell_counts=[])
    w = len(blocked)
    h = len(blocked[0])
    rng = random.Random(params.seed)

    seeds = [(x, y) for x in range(1, w - 1) for y in range(1, h - 1)
             if not blocked[x][y]]
    rng.shuffle(seeds)

    wires: list[list[tuple[int, int]]] = []
    raw: list[int] = []
    halo = max(0, params.wire_spacing)
    for s in seeds:
        sx, sy = s
        if blocked[sx][sy]:
            continue
        blocked[sx][sy] = True
        cells = _grow_wire(s, blocked, w, h, params, rng)
        # Halo dilation: claim cells around the finished wire so subsequent
        # wires keep their distance. Done after growth (not during) so a wire
        # is free to run as long as the painter algorithm allows.
        if halo:
            for cx, cy in cells:
                for dx in range(-halo, halo + 1):
                    for dy in range(-halo, halo + 1):
                        x, y = cx + dx, cy + dy
                        if 0 <= x < w and 0 <= y < h:
                            blocked[x][y] = True
        if len(cells) >= params.cut_off_length:
            wires.append(_simplify(cells))
            raw.append(len(cells))
    return PainterResult(wires=wires, raw_cell_counts=raw)


# ---------------------------------------------------------------------------
# Helpers used by the Blender driver to rasterize component bboxes.
# ---------------------------------------------------------------------------
@dataclass
class GridSpec:
    cell_size: float
    origin_x: float
    origin_y: float
    width: int
    height: int

    def cell_to_world(self, ix: int, iy: int) -> tuple[float, float]:
        return (
            self.origin_x + (ix + 0.5) * self.cell_size,
            self.origin_y + (iy + 0.5) * self.cell_size,
        )


def make_grid(board_lo_x: float, board_lo_y: float,
              board_hi_x: float, board_hi_y: float,
              cell_size: float) -> tuple[GridSpec, list[list[bool]]]:
    """Allocate a blocked grid covering the board, with a 1-cell border block."""
    w = max(2, math.ceil((board_hi_x - board_lo_x) / cell_size))
    h = max(2, math.ceil((board_hi_y - board_lo_y) / cell_size))
    blocked = [[False] * h for _ in range(w)]
    for x in range(w):
        blocked[x][0] = True
        blocked[x][h - 1] = True
    for y in range(h):
        blocked[0][y] = True
        blocked[w - 1][y] = True
    return GridSpec(cell_size, board_lo_x, board_lo_y, w, h), blocked


def block_bbox(grid: GridSpec, blocked: list[list[bool]],
               lo_x: float, lo_y: float, hi_x: float, hi_y: float,
               clearance: float) -> int:
    """Mark every grid cell overlapping [lo - clearance, hi + clearance] as blocked.

    Returns the count of cells newly marked (for diagnostics).
    """
    x0 = lo_x - clearance
    y0 = lo_y - clearance
    x1 = hi_x + clearance
    y1 = hi_y + clearance
    i0 = max(0, math.floor((x0 - grid.origin_x) / grid.cell_size))
    j0 = max(0, math.floor((y0 - grid.origin_y) / grid.cell_size))
    i1 = min(grid.width - 1, math.ceil((x1 - grid.origin_x) / grid.cell_size) - 1)
    j1 = min(grid.height - 1, math.ceil((y1 - grid.origin_y) / grid.cell_size) - 1)
    if i1 < i0 or j1 < j0:
        return 0
    n = 0
    for i in range(i0, i1 + 1):
        col = blocked[i]
        for j in range(j0, j1 + 1):
            if not col[j]:
                col[j] = True
                n += 1
    return n
