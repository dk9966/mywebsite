"""
Octilinear PCB trace router for Claude procedural layout.

Consumes LayoutPlanner + LayoutReport, emits polylines on the board plane.
Blender import maps planner world (x, z) -> mesh (x, y) with Z up.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Blender import: board in XY, thickness in Z (BOARD_T=0.4 -> top z≈0.2).
BOARD_TOP_Z = 0.38

_pcb_export = Path(__file__).resolve().parents[1] / "plans/claude/files/pcb_export"
if str(_pcb_export) not in sys.path:
    sys.path.insert(0, str(_pcb_export))

from trace.router import route_layout  # noqa: E402
from trace.models import RouteReport, TracePath  # noqa: E402


@dataclass
class TraceSegment:
    p0: tuple[float, float, float]
    p1: tuple[float, float, float]
    width: float
    tier: str


@dataclass
class RouterResult:
    segments: list[TraceSegment] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    report: RouteReport | None = None


def _polyline_to_segments(trace: TracePath) -> list[TraceSegment]:
    segs: list[TraceSegment] = []
    pts = trace.points
    for i in range(len(pts) - 1):
        x0, z0 = pts[i]
        x1, z1 = pts[i + 1]
        segs.append(
            TraceSegment(
                (x0, z0, BOARD_TOP_Z),
                (x1, z1, BOARD_TOP_Z),
                trace.width,
                trace.tier,
            )
        )
    return segs


def route_traces(planner, report, *, seed: int = 42) -> RouterResult:
    """Route traces between layout placements; does not modify component meshes."""
    result = route_layout(planner, report, seed=seed)
    segments: list[TraceSegment] = []
    for trace in result.traces:
        segments.extend(_polyline_to_segments(trace))
    return RouterResult(
        segments=segments,
        stats={
            "segment_count": len(segments),
            "trace_count": len(result.traces),
            "routed_nets": result.routed_nets,
            "requested_nets": result.requested_nets,
            **result.stats,
        },
        report=result,
    )
