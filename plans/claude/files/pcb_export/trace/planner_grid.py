"""Planner-aligned routing grid with carved gutters around each placement."""
from __future__ import annotations

from .grid import RoutingGrid
from .models import PlacedComponent
from .scene import report_to_components

DEFAULT_SUBDIV = 14
DEFAULT_GUTTER_IC = 4
DEFAULT_GUTTER_SMD = 2


def build_planner_grid(
    planner,
    report,
    *,
    subdiv: int = DEFAULT_SUBDIV,
    gutter_ic: int = DEFAULT_GUTTER_IC,
    gutter_smd: int = DEFAULT_GUTTER_SMD,
) -> tuple[RoutingGrid, list[PlacedComponent]]:
    """
    Coarse grid snapped to layout cells: each planner cell becomes
    ``subdiv × subdiv`` routing cells. Each placement's inner core is blocked
    while ``gutter`` cells around the perimeter stay routable, so wires can
    pass close to components without touching them.
    """
    components = report_to_components(planner, report)
    pitch = planner.cell / subdiv
    bw = planner.cols * planner.cell
    bd = planner.rows * planner.cell
    x0 = -bw / 2
    z0 = -bd / 2

    grid = RoutingGrid(x0=x0, z0=z0, x1=x0 + bw, z1=z0 + bd, pitch=pitch)

    for p in report.placements:
        col, row = p.cell
        fw, fh = p.footprint
        gutter = gutter_smd if p.family == "smd" else gutter_ic
        sc0 = col * subdiv + gutter
        sr0 = row * subdiv + gutter
        sc1 = (col + fw) * subdiv - gutter
        sr1 = (row + fh) * subdiv - gutter
        if sc1 <= sc0:
            sc0 = col * subdiv + 1
            sc1 = (col + fw) * subdiv - 1
        if sr1 <= sr0:
            sr0 = row * subdiv + 1
            sr1 = (row + fh) * subdiv - 1
        for sc in range(max(0, sc0), min(grid.cols, sc1)):
            for sr in range(max(0, sr0), min(grid.rows, sr1)):
                grid.blocked[sc][sr] = True

    return grid, components
