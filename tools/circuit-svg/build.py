"""End-to-end pipeline: reference image -> editable SVG + final composite PNG.

Usage::

    python3 tools/circuit-svg/build.py

Outputs land next to the reference under ``plans/chatgpt/``.
"""

from __future__ import annotations

from pathlib import Path

import detect
import route
import render

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "plans/chatgpt/lines applied ChatGPT Image May 23, 2026, 08_34_53 PM.png"
OUT_SVG = REPO / "plans/chatgpt/circuit-traces.svg"
OUT_PNG = REPO / "plans/chatgpt/circuit-traces-final.png"


def main() -> None:
    print(f"[detect] {SRC.name}")
    components, size = detect.run(SRC)
    print(f"[detect] image={size[0]}x{size[1]}  components={len(components)}")

    print("[route] octilinear A* over snapped pitch grid")
    router = route.Router(size, components, pitch=6, margin=1)
    report = router.route_all(
        pin_stride_cells=2,
        max_reach_cells=26,
        edge_exit_fraction=0.45,
    )
    print(
        f"[route] requested={report.requested_nets} "
        f"routed={report.routed_nets} "
        f"grid={report.grid_shape[0]}x{report.grid_shape[1]}@{report.pitch}px"
    )

    print("[render] writing SVG + rasterising PNG")
    render.run(
        image_size=size,
        components=components,
        traces=report.traces,
        out_svg=OUT_SVG,
        out_png=OUT_PNG,
    )
    print(f"[render] {OUT_SVG.relative_to(REPO)}")
    print(f"[render] {OUT_PNG.relative_to(REPO)}")


if __name__ == "__main__":
    main()
