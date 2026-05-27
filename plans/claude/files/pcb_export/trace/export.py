"""Export routed traces as editable SVG paths and JSON polylines."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from .models import PlacedComponent, RouteReport, TracePath

TRACE_COLOR = "#5cd9ff"
BOARD_FILL = "#000000"


def _path_d(points: list[tuple[float, float]], scale: float, ox: float, oz: float) -> str:
    if not points:
        return ""
    parts: list[str] = []
    for i, (x, z) in enumerate(points):
        px = (x - ox) * scale
        py = (z - oz) * scale
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd}{px:.2f} {py:.2f}")
    return " ".join(parts)


def _board_bounds(components: list[PlacedComponent], margin: float = 0.5) -> tuple[float, float, float, float]:
    xs = [c.keepout.x0 for c in components] + [c.keepout.x1 for c in components]
    zs = [c.keepout.z0 for c in components] + [c.keepout.z1 for c in components]
    return (min(xs) - margin, min(zs) - margin, max(xs) + margin, max(zs) + margin)


def write_svg(
    report: RouteReport,
    out_path: Path,
    *,
    pixels_per_unit: float = 28.0,
) -> None:
    x0, z0, x1, z1 = _board_bounds(report.components)
    w = int((x1 - x0) * pixels_per_unit)
    h = int((z1 - z0) * pixels_per_unit)
    scale = pixels_per_unit

    backbone = [t for t in report.traces if t.tier == "backbone"]
    medium = [t for t in report.traces if t.tier == "medium"]
    thin = [t for t in report.traces if t.tier == "thin"]

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" shape-rendering="geometricPrecision">',
        f'  <rect width="{w}" height="{h}" fill="{BOARD_FILL}"/>',
        '  <g id="traces-backbone" fill="none" stroke="' + TRACE_COLOR + '" stroke-linecap="square">',
    ]
    for t in backbone:
        lines.append(
            f'    <path d="{escape(_path_d(t.points, scale, x0, z0))}" '
            f'stroke-width="{t.width * scale * 1.8:.2f}"/>'
        )
    lines.append("  </g>")
    lines.append('  <g id="traces-medium" fill="none" stroke="' + TRACE_COLOR + '">')
    for t in medium:
        lines.append(
            f'    <path d="{escape(_path_d(t.points, scale, x0, z0))}" '
            f'stroke-width="{t.width * scale * 1.4:.2f}"/>'
        )
    lines.append("  </g>")
    lines.append('  <g id="traces-thin" fill="none" stroke="' + TRACE_COLOR + '">')
    for t in thin:
        lines.append(
            f'    <path d="{escape(_path_d(t.points, scale, x0, z0))}" '
            f'stroke-width="{max(0.6, t.width * scale):.2f}"/>'
        )
    lines.append("  </g>")
    lines.append("</svg>")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_json(report: RouteReport, out_path: Path) -> None:
    payload = {
        "traces": [
            {
                "points": [[x, z] for x, z in t.points],
                "width": t.width,
                "tier": t.tier,
            }
            for t in report.traces
        ],
        "stats": report.stats,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
