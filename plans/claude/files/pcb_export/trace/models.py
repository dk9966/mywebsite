"""Data types for procedural PCB trace routing (board XZ plane, Y-up scene)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Tier = Literal["backbone", "medium", "thin"]
Side = Literal["N", "S", "E", "W"]

CLEARANCE_SMD = 0.08
CLEARANCE_IC = 0.15
CLEARANCE_BLOCK = 0.25

WIDTH_BACKBONE = 0.035
WIDTH_MEDIUM = 0.022
WIDTH_THIN = 0.012

FANOUT_QFP = 0.35
FANOUT_SOIC = 0.28
FANOUT_SMD = 0.18

PARALLEL_SPACING_SUB = 2  # subcells between parallel bus tracks


@dataclass(frozen=True)
class Keepout:
    x0: float
    z0: float
    x1: float
    z1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) * 0.5

    @property
    def cz(self) -> float:
        return (self.z0 + self.z1) * 0.5


@dataclass
class PlacedComponent:
    id: str
    family: str
    x: float
    z: float
    width: float
    depth: float
    rotation: int  # 0 or 90 (footprint swap)
    height: float
    keepout: Keepout
    route_block: Keepout
    pin_world: list[tuple[float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class Pin:
    """Pin on component edge + outward escape stub (world XZ)."""

    anchor: tuple[float, float]
    stub: tuple[float, float]
    direction: Side
    owner_id: str
    bus_id: int = -1


@dataclass
class TracePath:
    """Editable polyline on the board plane."""

    points: list[tuple[float, float]]
    width: float
    tier: Tier

    def length(self) -> float:
        total = 0.0
        for i in range(len(self.points) - 1):
            ax, az = self.points[i]
            bx, bz = self.points[i + 1]
            total += max(abs(bx - ax), abs(bz - az))
        return total


@dataclass
class RouteReport:
    traces: list[TracePath] = field(default_factory=list)
    components: list[PlacedComponent] = field(default_factory=list)
    requested_nets: int = 0
    routed_nets: int = 0
    stats: dict = field(default_factory=dict)
