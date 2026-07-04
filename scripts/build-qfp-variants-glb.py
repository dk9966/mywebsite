#!/usr/bin/env python3
"""Build qfp-variants.glb: rudimentary geometric representations of PCB
packages, shown as crease-edge outlines only (no solid surfaces) in the same
style as component_reference-outline.glb.

Four rows (spread along +X with footprint-based gaps):
  row 1  square QFP family — prism/frustum, beveled and plain bodies, L-pins,
         connected ring, gull-wing 90°/slant, layered bodies, mixes
  row 2  rectangular family — SOIC-style 2-side pins, long/narrow/wide plain
         and beveled bodies, layered stacks, mixes
  row 3  CPU chips — many-layer stacks: substrate / interposer / die / lid,
         chiplets, PGA peg grid, wafer stacks, mixes
  row 4  heat sinks — fin stacks with varying plate width/spacing/height,
         pin-fin grids, stepped stacks, two-tier bases, heatsink-on-QFP

Bodies are built from stacked slabs (box / chamfered / tapered) so variants
can mix layer counts and thicknesses freely. Gull-wing pins are corner-safe:
pin rows are laid out inside the straight portion of each face, so no lead
hovers in front of a beveled corner.

Each variant contributes:
  - emissive tube outlines (visible in any GLB viewer)
  - TronLine_<order>_0_00_part LINES primitives (ingestable by tronLinesFromGLB)

  python3 scripts/build-qfp-variants-glb.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT_GLB = ROOT / "models/qfp-variants.glb"
PUBLIC_GLB = ROOT / "public/models/qfp-variants.glb"

for extra in (ROOT / "plans/claude/files/pcb_export/layout", ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from mesh_builder import (  # noqa: E402
    _dedupe_edges,
    _extract_crease_edges,
    _make_edge_cylinder,
)
from gltf_lines import LineMeshSpec, merge_line_meshes_into_glb  # noqa: E402

EDGE_RADIUS = 0.008
GAP = 1.0  # clear space between variant footprints
ROW_CZ = [0.0, 2.6, 5.6, 8.8, 11.6, 14.2, 17.2, 20.0]

# ---------------------------------------------------------------------------
# Primitive slabs (used only to derive outlines; solids are discarded)
# ---------------------------------------------------------------------------

BODY_Y0 = 0.04  # stand-off above the board plane
CHAMFER_FRAC = 0.15  # corner cut as a fraction of the SHORTER side
TAPER_INSET = 0.20  # total shrink of each dimension across a tapered slab


def frustum(
    cx: float,
    cz: float,
    y0: float,
    y1: float,
    w0: float,
    d0: float,
    w1: float,
    d1: float,
) -> trimesh.Trimesh:
    """Closed rectangular frustum: w0 x d0 at y0 tapering to w1 x d1 at y1."""
    hw0, hd0, hw1, hd1 = w0 / 2, d0 / 2, w1 / 2, d1 / 2
    verts = np.array(
        [
            [cx - hw0, y0, cz - hd0],
            [cx + hw0, y0, cz - hd0],
            [cx + hw0, y0, cz + hd0],
            [cx - hw0, y0, cz + hd0],
            [cx - hw1, y1, cz - hd1],
            [cx + hw1, y1, cz - hd1],
            [cx + hw1, y1, cz + hd1],
            [cx - hw1, y1, cz + hd1],
        ],
        dtype=float,
    )
    quads = [
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
        (3, 2, 1, 0),
        (4, 5, 6, 7),
    ]
    faces = []
    for a, b, c, d in quads:
        faces.append((a, b, c))
        faces.append((a, c, d))
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def octagon_ring(
    cx: float, cz: float, y: float, w: float, d: float, cut: float
) -> np.ndarray:
    hw, hd = w / 2, d / 2
    c = cut
    pts = [
        (hw, hd - c),
        (hw, -(hd - c)),
        (hw - c, -hd),
        (-(hw - c), -hd),
        (-hw, -(hd - c)),
        (-hw, hd - c),
        (-(hw - c), hd),
        (hw - c, hd),
    ]
    return np.array([[cx + px, y, cz + pz] for px, pz in pts], dtype=float)


def oct_frustum(
    cx: float,
    cz: float,
    y0: float,
    y1: float,
    w0: float,
    d0: float,
    w1: float,
    d1: float,
    cut: float,
) -> trimesh.Trimesh:
    r0 = octagon_ring(cx, cz, y0, w0, d0, cut)
    r1 = octagon_ring(cx, cz, y1, w1, d1, cut)
    c0 = np.array([[cx, y0, cz]])
    c1 = np.array([[cx, y1, cz]])
    verts = np.concatenate([r0, r1, c0, c1])
    faces = []
    for i in range(8):
        j = (i + 1) % 8
        faces.append((i, j, 8 + j))
        faces.append((i, 8 + j, 8 + i))
        faces.append((16, j, i))
        faces.append((17, 8 + i, 8 + j))
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def slab(
    w: float,
    d: float,
    y0: float,
    h: float,
    style: str = "box",
    dx: float = 0.0,
    dz: float = 0.0,
) -> trimesh.Trimesh:
    """One body layer. style: box | cham (chamfered corners) | taper
    (chamfered corners, shrinking toward the top)."""
    if style == "box":
        return frustum(dx, dz, y0, y0 + h, w, d, w, d)
    cut = CHAMFER_FRAC * min(w, d)
    if style == "cham":
        return oct_frustum(dx, dz, y0, y0 + h, w, d, w, d, cut)
    if style == "taper":
        ins = min(TAPER_INSET, w * 0.4, d * 0.4)
        return oct_frustum(dx, dz, y0, y0 + h, w, d, w - ins, d - ins, cut)
    if style == "can":  # near-octagonal cross-section, reads as a capacitor can
        return oct_frustum(dx, dz, y0, y0 + h, w, d, w, d, 0.29 * min(w, d))
    raise ValueError(style)


# Layer spec: (w, d, h, style[, dx, dz[, advance]])
# advance=False keeps the next layer on the SAME level (side-by-side parts).
Layer = tuple


def layered_body(layers: list[Layer], y0: float = BODY_Y0) -> list[trimesh.Trimesh]:
    out = []
    y = y0
    for layer in layers:
        w, d, h, style = layer[:4]
        dx = layer[4] if len(layer) > 4 else 0.0
        dz = layer[5] if len(layer) > 5 else 0.0
        advance = layer[6] if len(layer) > 6 else True
        out.append(slab(w, d, y, h, style, dx, dz))
        if advance:
            y += h
    return out


# Classic bodies expressed as layers.
def body_beveled(w: float, d: float) -> list[trimesh.Trimesh]:
    return layered_body([(w, d, 0.16, "cham"), (w, d, 0.10, "taper")])


def body_plain(w: float, d: float) -> list[trimesh.Trimesh]:
    return layered_body([(w, d, 0.24, "box")])


def body_prism_frustum(w: float, d: float) -> list[trimesh.Trimesh]:
    return [
        frustum(0, 0, BODY_Y0, 0.20, w, d, w, d),
        frustum(0, 0, 0.20, 0.30, w - 0.06, d - 0.06, w - 0.36, d - 0.36),
    ]


# ---------------------------------------------------------------------------
# Pins
# ---------------------------------------------------------------------------

# L-shaped pin: leg drops from the body seam, foot runs outward on the board.
PIN_TOP = 0.16
LEG_T = 0.05
FOOT_T = 0.05
FOOT_LEN = 0.16
PIN_W = 0.06
PIN_PITCH = 0.125


def l_profile_2d() -> np.ndarray:
    return np.array(
        [
            [0.0, PIN_TOP],
            [LEG_T, PIN_TOP],
            [LEG_T, FOOT_T],
            [FOOT_LEN, FOOT_T],
            [FOOT_LEN, 0.0],
            [0.0, 0.0],
        ]
    )


# Gull-wing lead: constant-thickness bent strip (see the reference outline).
# Kept short — shoulder, drop and foot are all compact.
GW_SHOULDER_V = 0.15  # underside of the shoulder (body seam)
GW_T = 0.05  # lead thickness
GW_SHOULDER_LEN = 0.055  # shoulder underside length before the bend
GW_FOOT_LEN = 0.06  # flat foot beyond the outer slant landing
GW_SLANT_RUN = 0.08  # horizontal travel of the slanted drop


def gullwing_profile_2d(run: float) -> np.ndarray:
    sv = GW_SHOULDER_V
    t = GW_T
    u1 = GW_SHOULDER_LEN
    hyp = float(np.hypot(run, sv))
    off = t * (hyp - run) / sv
    u3b = u1 + run
    u3t = u1 + off + run
    u2 = u3t + GW_FOOT_LEN
    return np.array(
        [
            [0.0, sv + t],
            [u1 + off, sv + t],
            [u3t, t],
            [u2, t],
            [u2, 0.0],
            [u3b, 0.0],
            [u1, sv],
            [0.0, sv],
        ]
    )


def profile_pin(
    profile: np.ndarray, side: int, offset: float, w: float, d: float
) -> trimesh.Trimesh:
    """Extruded pin profile on a body side (0:+X 1:-X 2:+Z 3:-Z)."""
    from shapely.geometry import Polygon

    pin = trimesh.creation.extrude_polygon(Polygon(profile), height=PIN_W)
    pin.apply_translation([0, 0, -PIN_W / 2])
    hw, hd = w / 2, d / 2
    if side == 0:
        pin.apply_translation([hw, 0, offset])
    elif side == 1:
        pin.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
        pin.apply_translation([-hw, 0, offset])
    elif side == 2:
        pin.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
        pin.apply_translation([offset, 0, hd])
    else:
        pin.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        pin.apply_translation([offset, 0, -hd])
    return pin


def pin_offsets(side_len: float, cut: float) -> list[float]:
    """Pin centers along a face, confined to its straight portion: the row
    stays clear of chamfered corners (no lead hovers past the face)."""
    usable = side_len - 2 * cut - PIN_W - 0.06
    if usable < PIN_W:
        return []
    count = max(2, int(usable / PIN_PITCH) + 1)
    span = (count - 1) * PIN_PITCH
    while span > usable and count > 2:
        count -= 1
        span = (count - 1) * PIN_PITCH
    return [-span / 2 + i * PIN_PITCH for i in range(count)]


def pins(
    profile: np.ndarray,
    w: float,
    d: float,
    chamfered: bool = True,
    sides: tuple[int, ...] = (0, 1, 2, 3),
) -> list[trimesh.Trimesh]:
    cut = CHAMFER_FRAC * min(w, d) if chamfered else 0.0
    out = []
    for side in sides:
        side_len = d if side in (0, 1) else w
        for off in pin_offsets(side_len, cut):
            out.append(profile_pin(profile, side, off, w, d))
    return out


def pin_ring(w: float, d: float) -> list[trimesh.Trimesh]:
    """Pins fused into one continuous L-profile ring."""
    from shapely.geometry import Polygon

    hw, hd = w / 2, d / 2

    def annulus(grow_in: float, grow_out: float) -> Polygon:
        iw, ih = hw + grow_in, hd + grow_in
        ow, oh = hw + grow_out, hd + grow_out
        outer = [(-ow, -oh), (ow, -oh), (ow, oh), (-ow, oh)]
        inner = [(-iw, -ih), (-iw, ih), (iw, ih), (iw, -ih)]
        return Polygon(outer, [inner])

    rx = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    leg = trimesh.creation.extrude_polygon(annulus(0.0, LEG_T), height=PIN_TOP)
    leg.apply_transform(rx)
    foot = trimesh.creation.extrude_polygon(annulus(LEG_T, FOOT_LEN), height=FOOT_T)
    foot.apply_transform(rx)
    return [leg, foot]


GW90 = gullwing_profile_2d(0.0)
GWSL = gullwing_profile_2d(GW_SLANT_RUN)

# ---------------------------------------------------------------------------
# Heat sinks
# ---------------------------------------------------------------------------


def fins_x(
    w: float,
    d: float,
    y0: float,
    fin_t: float,
    gap: float,
    fin_h: float,
) -> list[trimesh.Trimesh]:
    """Vertical fin plates spread across the width, running along Z."""
    out = []
    pitch = fin_t + gap
    count = max(2, int((w - fin_t) / pitch) + 1)
    span = (count - 1) * pitch
    x = -span / 2
    for _ in range(count):
        out.append(frustum(x, 0, y0, y0 + fin_h, fin_t, d, fin_t, d))
        x += pitch
    return out


def pin_fins(
    w: float, d: float, y0: float, t: float, nx: int, nz: int, h: float
) -> list[trimesh.Trimesh]:
    """Grid of square pillars (pin-fin heatsink)."""
    out = []
    xs = np.linspace(-(w - t) / 2, (w - t) / 2, nx)
    zs = np.linspace(-(d - t) / 2, (d - t) / 2, nz)
    for x in xs:
        for z in zs:
            out.append(frustum(x, z, y0, y0 + h, t, t, t, t))
    return out


def heatsink(
    w: float,
    d: float,
    base_layers: list[Layer],
    fin_t: float = 0.06,
    gap: float = 0.10,
    fin_h: float = 0.5,
    style: str = "fins",
    nx: int = 6,
    nz: int = 5,
) -> list[trimesh.Trimesh]:
    out = layered_body(base_layers, y0=0.02)
    y = 0.02 + sum(layer[2] for layer in base_layers)
    top_w, top_d = base_layers[-1][0], base_layers[-1][1]
    if style == "fins":
        out += fins_x(top_w, top_d, y, fin_t, gap, fin_h)
    elif style == "pins":
        out += pin_fins(top_w, top_d, y, fin_t, nx, nz, fin_h)
    elif style == "none":
        pass
    return out


# ---------------------------------------------------------------------------
# Motherboard part builders
# ---------------------------------------------------------------------------


def box_at(cx: float, cz: float, y0: float, h: float, w: float, d: float) -> trimesh.Trimesh:
    return frustum(cx, cz, y0, y0 + h, w, d, w, d)


PLATE_T = 0.025


def plates_on_face(
    cx: float,
    cz: float,
    w: float,
    d: float,
    face: int,
    plates: list[tuple[float, float, float, float]],
) -> list[trimesh.Trimesh]:
    """Thin detail plates on a vertical face (0:+X 1:-X 2:+Z 3:-Z).
    Each plate: (offset_along_face, y0, plate_w, plate_h). These read as port
    openings, chip packages, labels — the giveaway details."""
    out = []
    for off, y0, pw, ph in plates:
        if face == 2:
            out.append(box_at(cx + off, cz + d / 2 + PLATE_T / 2, y0, ph, pw, PLATE_T))
        elif face == 3:
            out.append(box_at(cx + off, cz - d / 2 - PLATE_T / 2, y0, ph, pw, PLATE_T))
        elif face == 0:
            out.append(box_at(cx + w / 2 + PLATE_T / 2, cz + off, y0, ph, PLATE_T, pw))
        else:
            out.append(box_at(cx - w / 2 - PLATE_T / 2, cz + off, y0, ph, PLATE_T, pw))
    return out


def shift(solids: list[trimesh.Trimesh], dx: float = 0.0, dz: float = 0.0):
    for s in solids:
        s.apply_translation([dx, 0, dz])
    return solids


def io_box(
    cx: float, w: float, d: float, h: float, ports: list[tuple[float, float, float, float]]
) -> list[trimesh.Trimesh]:
    """Rear-I/O block: upright box with recessed port plates on its front."""
    return [box_at(cx, 0, 0.02, h, w, d)] + plates_on_face(cx, 0, w, d, 2, ports)


def dimm_slot(
    length: float, populated: bool = True, chips: int = 6, card_h: float = 0.72
) -> list[trimesh.Trimesh]:
    """DIMM slot: base bar, two rails with the card gap, end latches, and an
    optional memory card standing in the slot with chip plates on both faces."""
    ln = length
    out = [box_at(0, 0, 0.02, 0.10, ln + 0.24, 0.30)]
    out.append(box_at(0, -0.10, 0.12, 0.08, ln, 0.08))
    out.append(box_at(0, 0.10, 0.12, 0.08, ln, 0.08))
    out.append(box_at(-(ln / 2 + 0.19), 0, 0.02, 0.36, 0.14, 0.26))
    out.append(box_at(ln / 2 + 0.19, 0, 0.02, 0.36, 0.14, 0.26))
    if populated:
        cw = ln - 0.2
        out.append(box_at(0, 0, 0.12, card_h, cw, 0.05))
        span = cw - 0.5
        step = span / max(chips - 1, 1)
        chip_plates = [
            (-span / 2 + i * step, 0.30, min(0.30, step * 0.72), 0.34)
            for i in range(chips)
        ]
        out += plates_on_face(0, 0, cw, 0.05, 2, chip_plates)
        out += plates_on_face(0, 0, cw, 0.05, 3, chip_plates)
    return out


def pcie_card(
    length: float,
    card_h: float,
    chips: list[tuple[float, float, float, float]],
    bracket: bool = True,
    fingers: int = 10,
    slot_len: float | None = None,
    populated: bool = True,
) -> list[trimesh.Trimesh]:
    """PCIe slot with a card standing in it: edge-connector finger plates along
    the bottom, big chip plates on the card face, rear bracket at one end."""
    slot_len = slot_len if slot_len is not None else length * 0.62
    out = [box_at(0, 0, 0.02, 0.12, slot_len, 0.24)]
    out.append(box_at(0, -0.08, 0.12, 0.06, slot_len - 0.1, 0.06))
    out.append(box_at(0, 0.08, 0.12, 0.06, slot_len - 0.1, 0.06))
    if not populated:
        return out
    out.append(box_at(0, 0, 0.14, card_h, length, 0.05))
    span = slot_len - 0.35
    stepf = span / max(fingers - 1, 1)
    finger_plates = [(-span / 2 + i * stepf, 0.16, 0.07, 0.10) for i in range(fingers)]
    out += plates_on_face(0, 0, length, 0.05, 2, finger_plates)
    out += plates_on_face(0, 0, length, 0.05, 2, chips)
    if bracket:
        bx = -(length / 2 + 0.10)
        out.append(box_at(bx, 0, 0.0, card_h + 0.30, 0.05, 0.30))
        out.append(box_at(bx + 0.10, 0, card_h + 0.24, 0.06, 0.24, 0.30))
    return out


def vrm_row(
    n: int,
    choke: float = 0.32,
    choke_h: float = 0.28,
    gap: float = 0.12,
    mosfets: bool = True,
    caps: bool = False,
    alt: bool = False,
) -> list[trimesh.Trimesh]:
    """VRM phases: a strip of consecutive choke cubes (with top marking
    plates), a front row of flat MOSFETs, optionally cap cans behind."""
    pitch = choke + gap
    span = (n - 1) * pitch
    depth = 0.95 if (mosfets or caps) else 0.55
    out = [box_at(0, 0.04, 0.02, 0.03, span + choke + 0.30, depth)]
    zc = -0.16 if (mosfets or caps) else 0.0
    for i in range(n):
        x = -span / 2 + i * pitch
        h = choke_h * (1.3 if (alt and i % 2) else 1.0)
        out.append(box_at(x, zc, 0.05, h, choke, choke))
        out.append(box_at(x, zc, 0.05 + h, 0.02, choke * 0.58, choke * 0.58))
    if mosfets:
        for i in range(n):
            x = -span / 2 + i * pitch
            out.append(box_at(x, 0.30, 0.05, 0.07, 0.22, 0.15))
    if caps:
        for i in range(max(n - 1, 1)):
            x = -span / 2 + i * pitch + pitch / 2
            out.append(slab(0.17, 0.17, 0.05, 0.22, "can", dx=x, dz=0.34))
    return out


# ---------------------------------------------------------------------------
# Variant rows
# ---------------------------------------------------------------------------


def V(name, *parts):
    solids = []
    for p in parts:
        solids += p
    return (name, solids)


def build_rows() -> list[list[tuple[str, list[trimesh.Trimesh]]]]:
    row1 = [
        V("q1-prism-frustum", body_prism_frustum(1.0, 1.0)),
        V("q2-beveled", body_beveled(1.0, 1.0)),
        V("q3-plain-prism", body_plain(1.0, 1.0)),
        V("q4-l-pins", body_beveled(1.0, 1.0), pins(l_profile_2d(), 1.0, 1.0)),
        V(
            "q5-l-pins-plain-small",
            body_plain(0.8, 0.8),
            pins(l_profile_2d(), 0.8, 0.8, chamfered=False),
        ),
        V("q6-connected-ring", body_beveled(1.0, 1.0), pin_ring(1.0, 1.0)),
        V("q7-gullwing-90", body_beveled(1.0, 1.0), pins(GW90, 1.0, 1.0)),
        V("q8-gullwing-slant", body_beveled(1.0, 1.0), pins(GWSL, 1.0, 1.0)),
        V(
            "q9-gw90-plain-small",
            body_plain(0.7, 0.7),
            pins(GW90, 0.7, 0.7, chamfered=False),
        ),
        V(
            "q10-layered-gw-slant",
            layered_body(
                [(1.0, 1.0, 0.14, "cham"), (0.9, 0.9, 0.10, "box"), (0.72, 0.72, 0.12, "taper")]
            ),
            pins(GWSL, 1.0, 1.0),
        ),
        V(
            "q11-tall-layer-stack",
            layered_body(
                [
                    (0.9, 0.9, 0.14, "cham"),
                    (0.8, 0.8, 0.10, "box"),
                    (0.8, 0.8, 0.08, "cham"),
                    (0.62, 0.62, 0.16, "taper"),
                ]
            ),
        ),
        # Tall additions with identifying details (inductor, caps, transformer).
        V(
            "q12-choke",  # SMD power inductor: base flange, cube, marking plate
            layered_body([(0.8, 0.8, 0.06, "box"), (0.68, 0.68, 0.46, "box")]),
            [box_at(0, 0, 0.52, 0.02, 0.4, 0.4)],
        ),
        V(
            "q13-cap-can",  # electrolytic can on a base pad, with top step
            layered_body(
                [(0.62, 0.62, 0.05, "box"), (0.55, 0.55, 0.62, "can"), (0.40, 0.40, 0.05, "can")]
            ),
        ),
        V(
            "q14-tall-gw90",
            layered_body([(0.8, 0.8, 0.45, "box")]),
            pins(GW90, 0.8, 0.8, chamfered=False),
        ),
        V(
            "q15-transformer",  # base flange, winding body, side windows, top plate
            layered_body([(1.0, 0.9, 0.06, "box"), (0.85, 0.70, 0.50, "box")]),
            plates_on_face(0, 0, 0.85, 0.70, 2, [(0.0, 0.16, 0.52, 0.30)]),
            plates_on_face(0, 0, 0.85, 0.70, 3, [(0.0, 0.16, 0.52, 0.30)]),
            [box_at(0, 0, 0.56, 0.03, 0.62, 0.5)],
        ),
        V(
            "q16-radial-cap",  # tall through-hole electrolytic on a pad
            layered_body([(0.55, 0.55, 0.04, "box"), (0.5, 0.5, 0.80, "can")]),
        ),
    ]

    row2 = [
        V("r1-rect-beveled", body_beveled(1.6, 0.8)),
        V("r2-long-plain", body_plain(2.0, 0.7)),
        V(
            "r3-soic-2side",
            body_plain(1.4, 0.7),
            pins(GW90, 1.4, 0.7, chamfered=False, sides=(2, 3)),
        ),
        V("r4-rect-gw-slant", body_beveled(1.6, 0.8), pins(GWSL, 1.6, 0.8)),
        V("r5-rect-l-pins", body_beveled(1.2, 0.6), pins(l_profile_2d(), 1.2, 0.6)),
        V("r6-rect-ring", body_beveled(1.4, 0.9), pin_ring(1.4, 0.9)),
        V(
            "r7-rect-layered-gw90",
            layered_body(
                [(1.8, 1.0, 0.12, "cham"), (1.5, 0.8, 0.10, "box"), (1.1, 0.6, 0.12, "taper")]
            ),
            pins(GW90, 1.8, 1.0),
        ),
        V(
            "r8-small-flat-slant",
            body_plain(0.9, 0.45),
            pins(GWSL, 0.9, 0.45, chamfered=False, sides=(2, 3)),
        ),
        V(
            "r9-wide-thin-layers",
            layered_body(
                [(2.2, 1.2, 0.10, "box"), (2.0, 1.0, 0.07, "cham"), (1.8, 0.8, 0.08, "box")]
            ),
        ),
        # Tall additions with identifying details (relay, header, crystal, caps).
        V(
            "r10-relay",  # relay block: label plate + bottom corner pads
            layered_body([(1.3, 0.6, 0.55, "box")]),
            plates_on_face(0, 0, 1.3, 0.6, 2, [(0.0, 0.22, 0.80, 0.26)]),
            [box_at(-0.5, 0, 0.0, 0.04, 0.12, 0.5), box_at(0.5, 0, 0.0, 0.04, 0.12, 0.5)],
        ),
        V(
            "r11-pin-header",  # shrouded header: stepped body + pin plates in the opening
            layered_body([(1.6, 0.7, 0.28, "box"), (1.45, 0.55, 0.30, "box")]),
            plates_on_face(
                0,
                0,
                1.45,
                0.55,
                2,
                [(-0.45 + i * 0.3, 0.36, 0.10, 0.14) for i in range(4)],
            ),
        ),
        V(
            "r12-tall-bar-gw",
            layered_body([(1.2, 0.6, 0.45, "box")]),
            pins(GW90, 1.2, 0.6, chamfered=False, sides=(2, 3)),
        ),
        V(
            "r13-crystal-osc",  # metal-can oscillator on a base slab
            layered_body([(1.0, 0.55, 0.08, "box"), (0.78, 0.42, 0.34, "cham")]),
            [box_at(0, 0, 0.44, 0.02, 0.5, 0.24)],
        ),
        V(
            "r14-tantalum-pair",  # two polarized caps on a shared pad
            layered_body(
                [
                    (1.8, 0.8, 0.10, "box"),
                    (0.55, 0.6, 0.42, "box", -0.50, 0.0, False),
                    (0.55, 0.6, 0.42, "box", 0.50, 0.0),
                ]
            ),
            plates_on_face(-0.50, 0, 0.55, 0.6, 2, [(0.0, 0.30, 0.30, 0.14)]),
            plates_on_face(0.50, 0, 0.55, 0.6, 2, [(0.0, 0.30, 0.30, 0.14)]),
        ),
    ]

    row3 = [
        V(
            "c1-lga",
            layered_body(
                [(1.8, 1.8, 0.12, "box"), (1.55, 1.55, 0.09, "cham"), (1.35, 1.35, 0.16, "taper")]
            ),
        ),
        V(
            "c2-die-stack",
            layered_body(
                [
                    (1.9, 1.9, 0.10, "box"),
                    (1.3, 1.3, 0.12, "cham"),
                    (0.8, 0.8, 0.14, "box"),
                    (0.55, 0.55, 0.10, "box"),
                ]
            ),
        ),
        V(
            "c3-chiplets",
            layered_body(
                [
                    (2.4, 1.8, 0.12, "box"),
                    (1.8, 1.3, 0.09, "cham"),
                    (0.6, 0.9, 0.14, "box", -0.38, 0.0, False),
                    (0.6, 0.9, 0.14, "box", 0.38, 0.0, False),
                    (0.9, 0.28, 0.10, "box", 0.0, 0.48),
                ]
            ),
        ),
        V(
            "c4-pga",
            pin_fins(1.5, 1.5, 0.0, 0.07, 6, 6, 0.05),
            layered_body(
                [(1.7, 1.7, 0.12, "box"), (1.4, 1.4, 0.14, "taper")], y0=0.05
            ),
        ),
        V(
            "c5-wafer-stack",
            layered_body(
                [
                    (1.5, 1.5, 0.07, "box"),
                    (1.34, 1.34, 0.05, "cham"),
                    (1.5, 1.5, 0.07, "box"),
                    (1.34, 1.34, 0.05, "cham"),
                    (1.5, 1.5, 0.07, "box"),
                    (1.15, 1.15, 0.09, "taper"),
                ]
            ),
        ),
        V(
            "c6-lga-gullwing",
            layered_body(
                [(1.8, 1.8, 0.10, "box"), (1.55, 1.55, 0.08, "cham"), (1.35, 1.35, 0.14, "taper")]
            ),
            pins(GW90, 1.8, 1.8, chamfered=False),
        ),
        V(
            "c7-heatspreader-stack",
            layered_body(
                [
                    (2.6, 2.0, 0.10, "box"),
                    (2.2, 1.6, 0.08, "box"),
                    (1.6, 1.2, 0.09, "cham"),
                    (1.2, 0.9, 0.12, "box"),
                ]
            ),
        ),
        # Tall, mostly-unbeveled additions.
        V(
            "c8-cpu-tower",
            layered_body(
                [(1.8, 1.8, 0.12, "box"), (1.4, 1.4, 0.14, "box"), (0.9, 0.9, 0.45, "box")]
            ),
        ),
        V(
            "c9-stacked-dies-tall",
            layered_body(
                [
                    (1.6, 1.6, 0.14, "box"),
                    (1.2, 1.2, 0.18, "box"),
                    (0.9, 0.9, 0.18, "box"),
                    (0.6, 0.6, 0.18, "box"),
                ]
            ),
        ),
        V(
            "c10-hbm-towers",
            layered_body(
                [
                    (2.2, 1.6, 0.14, "box"),
                    (0.8, 1.0, 0.35, "box", 0.0, 0.0, False),
                    (0.45, 0.9, 0.50, "box", -0.75, 0.0, False),
                    (0.45, 0.9, 0.50, "box", 0.75, 0.0),
                ]
            ),
        ),
        V(
            "c11-monolith-cpu",  # substrate flange + tall body + lid + face label
            layered_body(
                [(1.5, 1.5, 0.08, "box"), (1.2, 1.2, 0.62, "box"), (1.0, 1.0, 0.10, "box")]
            ),
            plates_on_face(0, 0, 1.2, 1.2, 2, [(0.0, 0.30, 0.7, 0.34)]),
        ),
        V(
            "c12-tall-lga-gw",
            layered_body([(1.5, 1.5, 0.15, "box"), (1.2, 1.2, 0.50, "box")]),
            pins(GW90, 1.5, 1.5, chamfered=False),
        ),
    ]

    row4 = [
        V(
            "h1-classic-fins",
            heatsink(1.6, 1.2, [(1.6, 1.2, 0.14, "box")], fin_t=0.06, gap=0.10, fin_h=0.50),
        ),
        V(
            "h2-wide-plates",
            heatsink(1.6, 1.2, [(1.6, 1.2, 0.16, "box")], fin_t=0.14, gap=0.20, fin_h=0.45),
        ),
        V(
            "h3-dense-thin",
            heatsink(1.5, 1.1, [(1.5, 1.1, 0.12, "box")], fin_t=0.03, gap=0.07, fin_h=0.40),
        ),
        V(
            "h4-tall-fins",
            heatsink(1.2, 1.2, [(1.2, 1.2, 0.14, "box")], fin_t=0.05, gap=0.12, fin_h=0.85),
        ),
        V(
            "h5-pin-fin",
            heatsink(1.4, 1.2, [(1.4, 1.2, 0.14, "box")], style="pins", fin_t=0.09, nx=6, nz=5, fin_h=0.45),
        ),
        V(
            "h6-stepped-stack",
            layered_body(
                [
                    (1.6, 1.2, 0.16, "box"),
                    (1.35, 1.0, 0.14, "box"),
                    (1.1, 0.8, 0.12, "box"),
                    (0.85, 0.6, 0.12, "box"),
                    (0.6, 0.4, 0.10, "box"),
                ],
                y0=0.02,
            ),
        ),
        V(
            "h7-two-tier",
            heatsink(
                1.6,
                1.2,
                [(1.6, 1.2, 0.12, "box"), (1.3, 1.0, 0.10, "cham")],
                fin_t=0.05,
                gap=0.11,
                fin_h=0.5,
            ),
        ),
    ]

    # Rear I/O port clusters.
    row5 = [
        V(
            "io1-usb-stack",
            io_box(0, 0.55, 0.5, 0.75, [(0.0, 0.14, 0.34, 0.16), (0.0, 0.44, 0.34, 0.16)]),
        ),
        V(
            "io2-eth-usb",
            io_box(0, 0.6, 0.55, 0.85, [(0.0, 0.30, 0.40, 0.36)]),
            io_box(0.75, 0.5, 0.5, 0.6, [(0.0, 0.12, 0.30, 0.14), (0.0, 0.36, 0.30, 0.14)]),
        ),
        V(
            "io3-audio-trio",
            io_box(-0.45, 0.34, 0.4, 0.38, [(0.0, 0.12, 0.16, 0.16)]),
            io_box(0.0, 0.34, 0.4, 0.38, [(0.0, 0.12, 0.16, 0.16)]),
            io_box(0.45, 0.34, 0.4, 0.38, [(0.0, 0.12, 0.16, 0.16)]),
        ),
        V(
            "io4-video-out",
            io_box(0, 0.9, 0.5, 0.55, [(0.0, 0.12, 0.55, 0.13), (0.0, 0.34, 0.42, 0.12)]),
        ),
        V(
            "io5-full-cluster",
            [box_at(0.65, 0.05, 0.0, 0.03, 2.4, 0.7)],
            io_box(-0.25, 0.55, 0.5, 0.78, [(0.0, 0.16, 0.34, 0.16), (0.0, 0.46, 0.34, 0.16)]),
            io_box(0.42, 0.5, 0.5, 0.46, [(0.0, 0.14, 0.30, 0.16)]),
            io_box(1.08, 0.6, 0.55, 0.88, [(0.0, 0.36, 0.40, 0.36)]),
            io_box(1.72, 0.44, 0.5, 0.60, [(0.0, 0.10, 0.26, 0.12), (0.0, 0.30, 0.26, 0.12)]),
        ),
    ]

    # DIMM slots with memory cards inside.
    row6 = [
        V("d1-dimm-populated", dimm_slot(2.8, populated=True, chips=6)),
        V("d2-sodimm", dimm_slot(1.9, populated=True, chips=4, card_h=0.58)),
        V("d3-dimm-empty", dimm_slot(2.8, populated=False)),
        V(
            "d4-dimm-pair",
            shift(dimm_slot(2.6, populated=True, chips=5), dz=-0.28),
            shift(dimm_slot(2.6, populated=False), dz=0.28),
        ),
        V(
            "d5-dimm-bank",
            shift(dimm_slot(2.4, populated=True, chips=5), dz=-0.56),
            shift(dimm_slot(2.4, populated=True, chips=5), dz=0.0),
            shift(dimm_slot(2.4, populated=True, chips=5), dz=0.56),
        ),
    ]

    # PCIe slots with cards inside.
    row7 = [
        V(
            "p1-gpu-long",
            pcie_card(
                3.2,
                1.15,
                [(-0.55, 0.55, 0.85, 0.60), (0.75, 0.62, 0.60, 0.48)],
                fingers=12,
            ),
        ),
        V(
            "p2-nic-short",
            pcie_card(1.8, 0.85, [(0.15, 0.42, 0.60, 0.42)], fingers=7, slot_len=1.2),
        ),
        V("p3-slot-empty", pcie_card(2.4, 0.0, [], populated=False, slot_len=2.4)),
        V(
            "p4-accel-mid",
            pcie_card(
                2.6,
                1.0,
                [(-0.35, 0.50, 0.70, 0.50), (0.55, 0.42, 0.40, 0.34)],
                fingers=10,
            ),
        ),
        V(
            "p5-m2-stick",  # flat M.2 card on standoffs with top chip plates
            [box_at(0, 0, 0.10, 0.04, 1.5, 0.44)],
            [box_at(-0.80, 0, 0.02, 0.08, 0.14, 0.2), box_at(0.80, 0, 0.02, 0.12, 0.14, 0.2)],
            [box_at(-0.35, 0, 0.14, 0.05, 0.55, 0.34), box_at(0.25, 0, 0.14, 0.05, 0.38, 0.30)],
            [box_at(0.62, 0, 0.14, 0.04, 0.18, 0.24)],
        ),
    ]

    # VRM phases: consecutive choke cubes with MOSFET rows / cap cans.
    row8 = [
        V("v1-vrm-4phase", vrm_row(4, choke=0.38, choke_h=0.34, gap=0.14)),
        V("v2-vrm-8dense", vrm_row(8, choke=0.26, choke_h=0.24, gap=0.08)),
        V("v3-vrm-6caps", vrm_row(6, choke=0.30, choke_h=0.28, gap=0.12, caps=True)),
        V("v4-vrm-alt", vrm_row(6, choke=0.30, choke_h=0.24, gap=0.12, alt=True, mosfets=False)),
        V(
            "v5-vrm-double",
            shift(vrm_row(5, choke=0.30, choke_h=0.28, gap=0.10, mosfets=False), dz=-0.30),
            shift(vrm_row(5, choke=0.30, choke_h=0.28, gap=0.10, mosfets=False), dz=0.34),
        ),
    ]

    return [row1, row2, row3, row4, row5, row6, row7, row8]


# ---------------------------------------------------------------------------
# Compatibility shim for scripts/render-circuit-city.py
# ---------------------------------------------------------------------------

VARIANTS = [
    "v1-prism-frustum",
    "v2-beveled-prism",
    "v3-l-pins",
    "v4-connected-pins",
    "v5-gullwing-90",
    "v6-gullwing-slant",
]


def variant_solids(
    cx: float, cz: float, kind: str, w: float, d: float
) -> list[trimesh.Trimesh]:
    if kind == "v1-prism-frustum":
        solids = body_prism_frustum(w, d)
    elif kind == "v2-beveled-prism":
        solids = body_beveled(w, d)
    elif kind == "v3-l-pins":
        solids = body_beveled(w, d) + pins(l_profile_2d(), w, d)
    elif kind == "v4-connected-pins":
        solids = body_beveled(w, d) + pin_ring(w, d)
    elif kind == "v5-gullwing-90":
        solids = body_beveled(w, d) + pins(GW90, w, d)
    elif kind == "v6-gullwing-slant":
        solids = body_beveled(w, d) + pins(GWSL, w, d)
    else:
        raise ValueError(kind)
    for s in solids:
        s.apply_translation([cx, 0, cz])
    return solids


# ---------------------------------------------------------------------------
# Outline extraction (same recipe as component_reference-outline)
# ---------------------------------------------------------------------------


def crease_edges(solids: list[trimesh.Trimesh]) -> np.ndarray:
    edges_list = []
    for mesh in solids:
        edges = _extract_crease_edges(mesh, length_threshold=0.006, angle_threshold_deg=15)
        if len(edges):
            edges_list.append(edges)
    combined = np.concatenate(edges_list, axis=0)
    return _dedupe_edges(combined, tol=0.003)


def chain_edges(edges_arr: np.ndarray, tol: float = 0.003) -> list[list[np.ndarray]]:
    def q(v: np.ndarray) -> tuple[int, int, int]:
        return tuple(np.round(v / tol).astype(int))

    pos: dict[tuple, np.ndarray] = {}
    adj: dict[tuple, list[tuple]] = {}
    for a, b in edges_arr:
        ka, kb = q(np.asarray(a, float)), q(np.asarray(b, float))
        if ka == kb:
            continue
        pos[ka], pos[kb] = np.asarray(a, float), np.asarray(b, float)
        adj.setdefault(ka, []).append(kb)
        adj.setdefault(kb, []).append(ka)

    visited: set[tuple] = set()

    def ek(a: tuple, b: tuple) -> tuple:
        return (a, b) if a < b else (b, a)

    chains: list[list[np.ndarray]] = []
    endpoints = [k for k, n in adj.items() if len(n) == 1]
    for start in endpoints + [k for k in adj if k not in endpoints]:
        while True:
            nbrs = [n for n in adj[start] if ek(start, n) not in visited]
            if not nbrs:
                break
            chain = [pos[start]]
            cur = start
            while True:
                nbrs = [n for n in adj[cur] if ek(cur, n) not in visited]
                if not nbrs:
                    break
                nxt = nbrs[0]
                visited.add(ek(cur, nxt))
                chain.append(pos[nxt])
                cur = nxt
            if len(chain) >= 2:
                chains.append(chain)
    return chains


def edge_material() -> trimesh.visual.material.PBRMaterial:
    return trimesh.visual.material.PBRMaterial(
        baseColorFactor=[0.35, 0.85, 1.0, 1.0],
        metallicFactor=0.0,
        roughnessFactor=0.15,
        emissiveFactor=[0.4, 0.95, 1.0],
    )


def edges_to_tubes(edges: np.ndarray) -> trimesh.Trimesh | None:
    pieces = []
    for start, end in edges:
        cyl = _make_edge_cylinder(start, end, radius=EDGE_RADIUS, sections=3)
        if cyl is not None:
            pieces.append(cyl)
    if not pieces:
        return None
    tube = trimesh.util.concatenate(pieces)
    tube.visual = trimesh.visual.TextureVisuals(material=edge_material())
    return tube


# ---------------------------------------------------------------------------


def main() -> None:
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)

    scene = trimesh.Scene()
    specs: list[LineMeshSpec] = []
    order = 0

    for row_idx, row in enumerate(build_rows()):
        cz = ROW_CZ[row_idx]
        cursor = 0.0
        for name, solids in row:
            edges = crease_edges(solids)
            min_x = float(edges[..., 0].min())
            max_x = float(edges[..., 0].max())
            cx = cursor - min_x
            edges = edges.copy()
            edges[..., 0] += cx
            edges[..., 2] += cz
            cursor = cx + max_x + GAP

            tube = edges_to_tubes(edges)
            if tube is not None:
                scene.add_geometry(tube, geom_name=f"outline_{name}")

            for chain in chain_edges(edges):
                order += 1
                pts = np.asarray(chain, dtype=np.float32)
                specs.append(
                    LineMeshSpec(name=f"TronLine_{order:04d}_0_00_part_{name}", points=pts)
                )

            print(f"{name}: {len(edges)} edges")

    scene.export(str(OUT_GLB))
    added = merge_line_meshes_into_glb(OUT_GLB, specs, OUT_GLB)
    PUBLIC_GLB.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_GLB.write_bytes(OUT_GLB.read_bytes())

    print(f"\nExported {OUT_GLB} ({OUT_GLB.stat().st_size / 1024:.1f} KB)")
    print(f"  public copy: {PUBLIC_GLB}")
    print(f"  tron line chains merged: {added}")


if __name__ == "__main__":
    main()
