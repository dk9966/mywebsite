"""Emit fully-vector editable SVG, then rasterise it for the final PNG.

SVG structure (hand-editable):

  <svg viewBox="0 0 W H">
    <defs><style>...</style></defs>
    <rect class="board"/>
    <g id="components"> ... <rect> per detected AABB ... </g>
    <g id="traces-backbone"> ... <path> per long trace ... </g>
    <g id="traces-signal">   ... <path> per short trace ... </g>
  </svg>

Every coordinate is an integer in image pixels. Every `<path>` uses only
absolute `M`/`L` commands, so the file is fully editable in any vector
editor - no bezier curves, no transforms.

The PNG is produced by rasterising the same SVG through CairoSVG. That
guarantees the bitmap matches the vector exactly, only down-sampled to a
finite resolution. Bloom is deliberately omitted - the brief was "no glow
variation", and a single flat stroke colour reads as cleaner at any zoom.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

from detect import Component
from route import Trace


# ---- visual style ---------------------------------------------------------

BOARD_FILL = "#04101a"
TRACE_COLOR = "#5cd9ff"
COMPONENT_STROKE = "#3fb6da"
COMPONENT_FILL = "#020a10"
DIE_STROKE = "#2a8aaa"

STROKE_BACKBONE = 1.4
STROKE_SIGNAL = 0.7
STROKE_COMPONENT = 0.7
STROKE_DIE = 0.5

# Inset (px) for the inner "die marker" we draw on larger chips. A chip
# wider/taller than DIE_MIN_DIM gets a single inner rect inset by DIE_INSET
# from each edge - subtle PCB realism without breaking the infinite-zoom
# vector cleanliness.
DIE_INSET = 5
DIE_MIN_DIM = 36


def _trace_path_d(points: list[tuple[int, int]]) -> str:
    if not points:
        return ""
    parts = [f"M{points[0][0]} {points[0][1]}"]
    for x, y in points[1:]:
        parts.append(f"L{x} {y}")
    return " ".join(parts)


def write_svg(
    *,
    out_path: Path,
    image_size: tuple[int, int],
    components: list[Component],
    traces: list[Trace],
) -> None:
    w, h = image_size
    backbone = [t for t in traces if t.rank == 0]
    signal = [t for t in traces if t.rank != 0]

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" shape-rendering="geometricPrecision">'
    )
    lines.append("  <defs><style><![CDATA[")
    lines.append(f"    .board {{ fill: {BOARD_FILL}; }}")
    lines.append(
        f"    .component {{ fill: {COMPONENT_FILL}; stroke: {COMPONENT_STROKE}; "
        f"stroke-width: {STROKE_COMPONENT}; }}"
    )
    lines.append(
        f"    .die {{ fill: none; stroke: {DIE_STROKE}; "
        f"stroke-width: {STROKE_DIE}; }}"
    )
    lines.append(
        f"    .trace {{ fill: none; stroke: {TRACE_COLOR}; "
        f"stroke-linecap: square; stroke-linejoin: miter; }}"
    )
    lines.append(f"    .trace--backbone {{ stroke-width: {STROKE_BACKBONE}; }}")
    lines.append(f"    .trace--signal   {{ stroke-width: {STROKE_SIGNAL}; }}")
    lines.append("  ]]></style></defs>")
    lines.append(f'  <rect class="board" width="{w}" height="{h}"/>')

    # Backbone traces sit *under* components so their endpoints visibly tuck
    # into chip pads; signal traces sit on top so fine routing reads cleanly.
    lines.append('  <g id="traces-backbone">')
    for t in backbone:
        d = _trace_path_d(t.points_px)
        lines.append(f'    <path class="trace trace--backbone" d="{escape(d)}"/>')
    lines.append("  </g>")

    lines.append('  <g id="components">')
    for c in components:
        lines.append(
            f'    <rect class="component" x="{c.x}" y="{c.y}" '
            f'width="{c.w}" height="{c.h}"/>'
        )
        if c.w >= DIE_MIN_DIM and c.h >= DIE_MIN_DIM:
            lines.append(
                f'    <rect class="die" x="{c.x + DIE_INSET}" '
                f'y="{c.y + DIE_INSET}" '
                f'width="{c.w - 2 * DIE_INSET}" '
                f'height="{c.h - 2 * DIE_INSET}"/>'
            )
    lines.append("  </g>")

    lines.append('  <g id="traces-signal">')
    for t in signal:
        d = _trace_path_d(t.points_px)
        lines.append(f'    <path class="trace trace--signal" d="{escape(d)}"/>')
    lines.append("  </g>")

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def rasterise(
    *, svg_path: Path, png_path: Path, output_width: int, supersample: int = 2
) -> None:
    """Rasterise SVG -> PNG. Render at `supersample`x width and let CairoSVG
    handle the downsample so antialiasing is clean."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=output_width * supersample,
    )


def run(
    *,
    image_size: tuple[int, int],
    components: list[Component],
    traces: list[Trace],
    out_svg: Path,
    out_png: Path,
) -> None:
    write_svg(
        out_path=out_svg,
        image_size=image_size,
        components=components,
        traces=traces,
    )
    rasterise(svg_path=out_svg, png_path=out_png, output_width=image_size[0])
