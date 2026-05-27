"""Convert layout planner output into placed components with keepouts and pins."""
from __future__ import annotations

from .pins import generate_pins_for_component
from .models import (
    CLEARANCE_BLOCK,
    CLEARANCE_IC,
    CLEARANCE_SMD,
    Keepout,
    PlacedComponent,
)

_LARGE = frozenset({"qfp", "heatsink", "dip", "connector", "header"})
_BLOCK = frozenset({"heatsink"})


def _clearance_for_family(family: str) -> float:
    if family in _BLOCK:
        return CLEARANCE_BLOCK
    if family in _LARGE or family == "octagon":
        return CLEARANCE_IC
    return CLEARANCE_SMD


def _route_block_pad(family: str) -> float:
    """Tight routing obstacle — leaves gutters between packed grid cells."""
    if family in _BLOCK:
        return 0.10
    if family in _LARGE:
        return 0.06
    return 0.03


def placement_footprint_world(
    col: int,
    row: int,
    fw: int,
    fh: int,
    cols: int,
    rows: int,
    cell: float,
) -> tuple[float, float, float, float]:
    """Axis-aligned world XZ bounds (x0, z0, x1, z1), origin at board center."""
    x0 = (col - cols / 2) * cell
    z0 = (row - rows / 2) * cell
    x1 = x0 + fw * cell
    z1 = z0 + fh * cell
    return (x0, z0, x1, z1)


def report_to_components(planner, report, *, height: float = 0.4) -> list[PlacedComponent]:
    out: list[PlacedComponent] = []
    for idx, p in enumerate(report.placements):
        col, row = p.cell
        fw, fh = p.footprint
        rotation = 90 if fw < fh and p.footprint != (fw, fh) else 0
        x0, z0, x1, z1 = placement_footprint_world(
            col, row, fw, fh, planner.cols, planner.rows, planner.cell
        )
        pad = _clearance_for_family(p.family)
        keep = Keepout(x0 - pad, z0 - pad, x1 + pad, z1 + pad)
        rb = _route_block_pad(p.family)
        block = Keepout(x0 + rb, z0 + rb, x1 - rb, z1 - rb)
        comp = PlacedComponent(
            id=f"c{idx}",
            family=p.family,
            x=p.world_xz[0],
            z=p.world_xz[1],
            width=x1 - x0,
            depth=z1 - z0,
            rotation=rotation,
            height=height,
            keepout=keep,
            route_block=block,
        )
        comp.pin_world = generate_pins_for_component(comp, x0, z0, x1, z1)
        out.append(comp)
    return out
