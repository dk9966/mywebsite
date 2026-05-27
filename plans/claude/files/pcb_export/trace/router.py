"""High-level entry: layout plan -> painted trace polylines."""
from __future__ import annotations

from .grid import RoutingGrid
from .models import (
    PlacedComponent,
    RouteReport,
    TracePath,
    WIDTH_BACKBONE,
    WIDTH_MEDIUM,
    WIDTH_THIN,
)
from .painter import PainterConfig, PinSeed, SIDE_TO_DIR, paint_traces
from .path_style import drop_micro_jogs, simplify_collinear
from .pins import generate_routing_pins
from .planner_grid import build_planner_grid


def _pin_seeds_for_components(
    components: list[PlacedComponent], grid: RoutingGrid
) -> list[PinSeed]:
    """
    Seed cell = the pin's anchor on the placement perimeter.

    With the gutter-inside grid, the anchor cell sits on a free routable
    border cell, and the first outward move enters the inter-component gap.
    """
    seeds: list[PinSeed] = []
    for comp in components:
        x0 = comp.x - comp.width * 0.5
        z0 = comp.z - comp.depth * 0.5
        x1 = comp.x + comp.width * 0.5
        z1 = comp.z + comp.depth * 0.5
        for anchor, _stub, side, _ in generate_routing_pins(
            comp, x0, z0, x1, z1, comp.id
        ):
            cell = grid.world_to_cell(*anchor)
            seeds.append(
                PinSeed(cell=cell, direction=SIDE_TO_DIR[side], anchor=anchor)
            )
    return seeds


def _cells_to_world(
    grid: RoutingGrid,
    cell_path: list[tuple[int, int]],
    pin_anchor: tuple[float, float] | None,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if pin_anchor is not None:
        pts.append(pin_anchor)
    for c, r in cell_path:
        pts.append(grid.cell_to_world(c, r))
    pts = simplify_collinear(pts)
    return drop_micro_jogs(pts)


def _trace_length(points: list[tuple[float, float]]) -> float:
    return sum(
        max(abs(points[k + 1][0] - points[k][0]), abs(points[k + 1][1] - points[k][1]))
        for k in range(len(points) - 1)
    )


def _tier_for_length(length: float) -> tuple[str, float]:
    if length > 8.0:
        return ("backbone", WIDTH_BACKBONE)
    if length > 3.0:
        return ("medium", WIDTH_MEDIUM)
    return ("thin", WIDTH_THIN)


def route_layout(
    planner,
    report,
    *,
    seed: int = 42,
    subdiv: int = 14,
    gutter_ic: int = 4,
    gutter_smd: int = 2,
    wire_length: int = 260,
    straightness: float = 14.0,
    cut_off_cells: int = 1,
) -> RouteReport:
    """Run the painter on a planner layout and return TracePath polylines."""
    grid, components = build_planner_grid(
        planner, report, subdiv=subdiv, gutter_ic=gutter_ic, gutter_smd=gutter_smd
    )

    pin_seeds = _pin_seeds_for_components(components, grid)
    pin_anchor_by_cell = {ps.cell: ps.anchor for ps in pin_seeds}

    paths, pin_flags = paint_traces(
        grid,
        pin_seeds,
        PainterConfig(
            wire_length=wire_length,
            straightness=straightness,
            cut_off_cells=cut_off_cells,
            seed=seed,
        ),
    )

    rep = RouteReport(components=components)
    rep.requested_nets = len(paths)

    pin_count = 0
    for path, was_pinned in zip(paths, pin_flags):
        anchor = pin_anchor_by_cell.get(path[0]) if was_pinned else None
        world = _cells_to_world(grid, path, anchor)
        if len(world) < 2:
            continue
        length = _trace_length(world)
        tier, width = _tier_for_length(length)
        rep.traces.append(TracePath(points=world, width=width, tier=tier))
        if was_pinned:
            pin_count += 1

    rep.routed_nets = len(rep.traces)
    rep.stats = {
        "component_count": len(components),
        "grid_cols": grid.cols,
        "grid_rows": grid.rows,
        "pitch": grid.pitch,
        "pin_seed_count": pin_count,
        "backbone_traces": sum(1 for t in rep.traces if t.tier == "backbone"),
        "wire_length": wire_length,
        "straightness": straightness,
        "cut_off_cells": cut_off_cells,
        "gutter_ic": gutter_ic,
        "gutter_smd": gutter_smd,
        "subdiv": subdiv,
    }
    return rep
