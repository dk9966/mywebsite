"""
Route traces for random_pcb layout (seed 42) and export SVG + JSON.

Run from repo root::

    python3 plans/claude/files/pcb_export/trace/build_traces.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LAYOUT = _ROOT / "layout"
if str(_LAYOUT) not in sys.path:
    sys.path.insert(0, str(_LAYOUT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pcb_layout import FamilySpec, LayoutPlanner  # noqa: E402

from trace.export import write_json, write_svg  # noqa: E402
from trace.router import route_layout  # noqa: E402

FAMILIES = {
    "qfp": FamilySpec(count=18, footprint=(2, 2), distributed=True, regions=(3, 2)),
    "heatsink": FamilySpec(count=8, footprint=(2, 2), distributed=True, regions=(2, 2)),
    "dip": FamilySpec(count=25, footprint=(2, 1), allow_rotation=True),
    "header": FamilySpec(count=15, footprint=(2, 1), allow_rotation=True),
    "connector": FamilySpec(count=12, footprint=(2, 1), allow_rotation=True),
    "octagon": FamilySpec(count=10, footprint=(1, 1)),
    "cap": FamilySpec(count=35, footprint=(1, 1)),
}

SEED = 42
OUT_DIR = Path(__file__).resolve().parents[3] / "outputs"


def main() -> None:
    planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
    report = planner.plan(FAMILIES, seed=SEED, filler_family="smd")
    result = route_layout(planner, report, seed=SEED)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = OUT_DIR / "random_pcb_traces.svg"
    json_path = OUT_DIR / "random_pcb_traces.json"
    write_svg(result, svg_path)
    write_json(result, json_path)

    print(f"[trace] components={len(result.components)} traces={len(result.traces)}")
    print(f"[trace] stats={result.stats}")
    print(f"[trace] svg -> {svg_path}")
    print(f"[trace] json -> {json_path}")


if __name__ == "__main__":
    main()
