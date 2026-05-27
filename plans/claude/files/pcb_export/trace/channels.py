"""Scan routing grid for long free corridors (backbone bus candidates)."""
from __future__ import annotations

from .grid import RoutingGrid


def scan_corridors(
    grid: RoutingGrid,
    *,
    min_length: int = 10,
) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    """
    Return horizontal and vertical corridor descriptors.

    Horizontal: (fixed_row, col_start, col_end)
    Vertical: (fixed_col, row_start, row_end)
    """
    horiz: list[tuple[int, int, int]] = []
    vert: list[tuple[int, int, int]] = []

    for r in range(grid.rows):
        c = 0
        while c < grid.cols:
            if not grid.free(c, r):
                c += 1
                continue
            start = c
            while c < grid.cols and grid.free(c, r):
                c += 1
            if c - start >= min_length:
                horiz.append((r, start, c - 1))

    for c in range(grid.cols):
        r = 0
        while r < grid.rows:
            if not grid.free(c, r):
                r += 1
                continue
            start = r
            while r < grid.rows and grid.free(c, r):
                r += 1
            if r - start >= min_length:
                vert.append((c, start, r - 1))

    horiz.sort(key=lambda t: -(t[2] - t[0]))
    vert.sort(key=lambda t: -(t[2] - t[0]))
    return horiz, vert
