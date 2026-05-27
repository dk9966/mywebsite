"""Per-family pin and escape-point generation on the board XZ plane."""
from __future__ import annotations

from .models import (
    FANOUT_QFP,
    FANOUT_SMD,
    FANOUT_SOIC,
    PlacedComponent,
    Side,
)

_QFP = frozenset({"qfp"})
_SOIC_TWO_SIDE = frozenset({"dip", "header", "connector"})
_SMD = frozenset({"smd", "cap"})
_BLOCK = frozenset({"heatsink", "octagon"})


def _side_outward(side: Side) -> tuple[float, float]:
    return {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}[side]


def _qfp_pins_per_side(fw: float, fh: float) -> int:
    """Scale pin density with QFP footprint — dense buses at large ICs."""
    span = max(fw, fh)
    return max(6, min(11, int(span * 2.8)))


def _soic_pins_per_side(fw: float, fh: float) -> int:
    return max(4, min(8, int(max(fw, fh) * 2.2)))


def _edge_pins(
    x0: float,
    z0: float,
    x1: float,
    z1: float,
    side: Side,
    count: int,
    fanout: float,
) -> list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]:
    """Return (anchor_xz, stub_xz, outward_dir) tuples."""
    if count < 1:
        return []
    out: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = []
    ox, oz = _side_outward(side)
    if side in ("N", "S"):
        span = x1 - x0
        for i in range(count):
            t = (i + 1) / (count + 1)
            x = x0 + span * t
            z = z0 if side == "N" else z1
            anchor = (x, z)
            stub = (x + ox * fanout, z + oz * fanout)
            out.append((anchor, stub, (ox, oz)))
    else:
        span = z1 - z0
        for i in range(count):
            t = (i + 1) / (count + 1)
            z = z0 + span * t
            x = x0 if side == "W" else x1
            anchor = (x, z)
            stub = (x + ox * fanout, z + oz * fanout)
            out.append((anchor, stub, (ox, oz)))
    return out


def _long_sides(fw_cells: float, fh_cells: float) -> tuple[Side, Side]:
    """Two long edges for SOIC-style packages (world footprint may be rotated)."""
    if fw_cells >= fh_cells:
        return ("N", "S")
    return ("W", "E")


def generate_pins_for_component(
    comp: PlacedComponent,
    x0: float,
    z0: float,
    x1: float,
    z1: float,
) -> list[tuple[float, float]]:
    """World XZ anchor points on the component perimeter (for debug / export)."""
    anchors: list[tuple[float, float]] = []
    fw = x1 - x0
    fh = z1 - z0

    if comp.family in _QFP:
        n = _qfp_pins_per_side(fw, fh)
        for side in ("N", "S", "E", "W"):
            for anchor, _, _ in _edge_pins(x0, z0, x1, z1, side, n, FANOUT_QFP):
                anchors.append(anchor)
    elif comp.family in _SOIC_TWO_SIDE:
        n = _soic_pins_per_side(fw, fh)
        s0, s1 = _long_sides(fw, fh)
        for side in (s0, s1):
            for anchor, _, _ in _edge_pins(x0, z0, x1, z1, side, n, FANOUT_SOIC):
                anchors.append(anchor)
    elif comp.family in _SMD:
        cx, cz = comp.x, comp.z
        pad = min(fw, fh) * 0.2
        anchors.extend([(x0 + pad, cz), (x1 - pad, cz)])
    elif comp.family in _BLOCK:
        n = 2
        for side in ("N", "E"):
            for anchor, _, _ in _edge_pins(x0, z0, x1, z1, side, n, FANOUT_SOIC * 0.8):
                anchors.append(anchor)
    else:
        cx, cz = comp.x, comp.z
        anchors.append((cx, z0))
        anchors.append((cx, z1))
    return anchors


def generate_routing_pins(
    comp: PlacedComponent,
    x0: float,
    z0: float,
    x1: float,
    z1: float,
    owner_id: str,
) -> list[tuple[tuple[float, float], tuple[float, float], Side, str]]:
    """(anchor, stub, direction, owner_id) for the router."""
    fw = x1 - x0
    fh = z1 - z0
    pins: list[tuple[tuple[float, float], tuple[float, float], Side, str]] = []

    if comp.family in _QFP:
        n = _qfp_pins_per_side(fw, fh)
        for side in ("N", "S", "E", "W"):
            for anchor, stub, _ in _edge_pins(x0, z0, x1, z1, side, n, FANOUT_QFP):
                pins.append((anchor, stub, side, owner_id))
    elif comp.family in _SOIC_TWO_SIDE:
        n = _soic_pins_per_side(fw, fh)
        for side in _long_sides(fw, fh):
            for anchor, stub, _ in _edge_pins(x0, z0, x1, z1, side, n, FANOUT_SOIC):
                pins.append((anchor, stub, side, owner_id))
    elif comp.family in _SMD:
        cx, cz = comp.x, comp.z
        pad = min(fw, fh) * 0.2
        a0, a1 = (x0 + pad, cz), (x1 - pad, cz)
        pins.append((a0, (a0[0] - FANOUT_SMD, cz), "W", owner_id))
        pins.append((a1, (a1[0] + FANOUT_SMD, cz), "E", owner_id))
    elif comp.family in _BLOCK:
        for side in ("N", "E"):
            for anchor, stub, _ in _edge_pins(x0, z0, x1, z1, side, 2, FANOUT_SOIC * 0.8):
                pins.append((anchor, stub, side, owner_id))
    else:
        cx, cz = comp.x, comp.z
        pins.append(((cx, z0), (cx, z0 - FANOUT_SMD), "N", owner_id))
        pins.append(((cx, z1), (cx, z1 + FANOUT_SMD), "S", owner_id))

    return pins
