"""
Full-density circuit board component layout for the ChatGPT reference (no traces/vias).

Scene: Circuit Layout
Collections: CircuitLayout (assembly), CircuitLayout_Parts (library grid)

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/build_circuit_layout.py
"""
from __future__ import annotations

import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

# Allow import when Blender runs script by path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from pcb_bmesh_lib import (
    bm_add_box,
    bm_add_hex_prism,
    bm_legs_qfp,
    bm_legs_x_pair,
    bm_legs_y_pair,
    bm_pad,
    bm_pin1_dot,
    grid_slot,
    mesh_from_bmesh,
    put_object,
)

SCENE_NAME = "Circuit Layout"
COLL_ASM = "CircuitLayout"
COLL_PARTS = "CircuitLayout_Parts"

BOARD_W = 290.0
BOARD_D = 220.0
BOARD_T = 0.4
# Tripo Layout reference: med footprint ~0.10 board-fraction, bbox gap ~0.19 of that.
TRIPO_GAP_TO_FOOTPRINT = 0.19
TARGET_MEDIAN_FOOTPRINT_MM = 9.0
# Tight, even aisles — placement AABB matches scaled mesh (no phantom overlap).
GAP_MM = 0.10
FOOTPRINT_PLACE_SCALE = 1.0
LAYOUT_COMPRESS = 0.56
CLUSTER_PULL = 0.90
# Visual scale per variant — compress size spread toward Tripo (~3.4× max/median).
MESH_VISUAL_SCALE: dict[tuple[str, str], float] = {
    ("smd", "pair0201"): 4.5 / 3.0,
    ("smd", "block4"): 4.5 / 3.9,
    ("smd", "pair0805"): 4.8 / 4.0,
    ("smd", "row6"): 5.5 / 9.3,
    ("ic_rect", "soic8"): 7.0 / 6.2,
    ("ic_rect", "tssop20"): 7.5 / 9.0,
    ("ic_rect", "soic16"): 9.0 / 10.0,
    ("ic_rect", "2side"): 10.0 / 14.0,
    ("ic_sq", "qfp32"): 9.0 / 10.0,
    ("ic_sq", "lqfp64"): 11.0 / 14.0,
    ("ic_sq", "lqfp64_w"): 12.0 / 18.0,
    ("ic_sq", "wide"): 14.0 / 19.9,
    ("bga", "10"): 10.0 / 11.0,
    ("bga", "14"): 12.0 / 15.0,
    ("bga", "20"): 14.0 / 21.0,
    ("cap_cyl", "short"): 5.5 / 6.4,
    ("cap_cyl", "tall"): 6.5 / 7.6,
    ("cap_cyl", "2x2"): 12.0 / 12.8,
    ("cap_cyl", "row4"): 12.0 / 15.4,
    ("dip", "14"): 14.0 / 17.0,
    ("dip", "24"): 20.0 / 30.0,
    ("oct", "low"): 12.0 / 16.6,
    ("oct", "medium"): 14.0 / 20.3,
    ("hsink", "fins6"): 18.0 / 28.0,
    ("hsink", "fins10"): 22.0 / 38.0,
    ("hsink", "fins14"): 26.0 / 48.0,
    ("hsink", "stepped"): 18.0 / 26.0,
    ("socket", "frame"): 22.0 / 38.0,
    ("socket", "die"): 22.0 / 38.0,
    ("conn_slot", "usb"): 12.0 / 16.5,
    ("conn_slot", "pcie"): 18.0 / 34.0,
    ("conn_slot", "slot3"): 22.0 / 42.0,
    ("conn_slot", "wide"): 26.0 / 52.0,
}

# ---------------------------------------------------------------------------
# scene helpers
# ---------------------------------------------------------------------------


def get_target_scene() -> bpy.types.Scene:
    sc = bpy.data.scenes.get(SCENE_NAME)
    if sc is None:
        raise RuntimeError(f"Scene '{SCENE_NAME}' not found")
    return sc


def coll_ensure(name: str, scene: bpy.types.Scene) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if name not in scene.collection.children.keys():
        scene.collection.children.link(coll)
    return coll


def purge_collection(name: str):
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for parent in bpy.data.collections:
        if coll.name in parent.children.keys():
            parent.children.unlink(coll)
    for sc in bpy.data.scenes:
        if coll.name in sc.collection.children.keys():
            sc.collection.children.unlink(coll)
    bpy.data.collections.remove(coll)


def mesh_scale_for(key: tuple[str, str]) -> float:
    return MESH_VISUAL_SCALE.get(key, 1.0)


def apply_visual_scale(ob: bpy.types.Object, key: tuple[str, str]) -> None:
    s = mesh_scale_for(key)
    if abs(s - 1.0) > 1e-6:
        ob.scale = (s, s, s)


def object_xy_half_extents(ob: bpy.types.Object) -> tuple[float, float]:
    """World-space half-width / half-depth from axis-aligned bbox."""
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    for corner in ob.bound_box:
        w = ob.matrix_world @ Vector(corner)
        lo.x = min(lo.x, w.x)
        lo.y = min(lo.y, w.y)
        lo.z = min(lo.z, w.z)
        hi.x = max(hi.x, w.x)
        hi.y = max(hi.y, w.y)
        hi.z = max(hi.z, w.z)
    return (hi.x - lo.x) * 0.5, (hi.y - lo.y) * 0.5


def read_tripo_slots() -> list[dict]:
    """Sample Tripo Layout component centers and footprints in Circuit board mm."""
    coll = bpy.data.collections.get("TripoLayout")
    if coll is None:
        return []
    parts = [
        o
        for o in coll.objects
        if o.type == "MESH"
        and o.parent
        and o.parent.name == "tripo_neon_circuit_components"
    ]
    if not parts:
        return []
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    raw: list[tuple[float, float, float, float, float]] = []
    for o in parts:
        blo = Vector((1e30, 1e30, 1e30))
        bhi = Vector((-1e30, -1e30, -1e30))
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            for k in range(3):
                blo[k] = min(blo[k], w[k])
                bhi[k] = max(bhi[k], w[k])
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
        cx = (blo.x + bhi.x) * 0.5
        cy = (blo.y + bhi.y) * 0.5
        hw = (bhi.x - blo.x) * 0.5
        hd = (bhi.y - blo.y) * 0.5
        raw.append((cx, cy, hw, hd, max(bhi.x - blo.x, bhi.y - blo.y)))
    bw = max(hi.x - lo.x, 1e-6)
    bh = max(hi.y - lo.y, 1e-6)
    cx0 = (lo.x + hi.x) * 0.5
    cy0 = (lo.y + hi.y) * 0.5
    slots = []
    for cx, cy, hw, hd, mf in raw:
        x = (cx - cx0) / bw * BOARD_W
        y = (cy - cy0) / bh * BOARD_D
        mf_mm = mf / bw * BOARD_W
        slots.append(
            {
                "x": round(x * LAYOUT_COMPRESS * CLUSTER_PULL / 2) * 2,
                "y": round(y * LAYOUT_COMPRESS * CLUSTER_PULL / 2) * 2,
                "hw": hw / bw * BOARD_W * 0.5,
                "hd": hd / bh * BOARD_D * 0.5,
                "mf": mf_mm,
            }
        )
    return slots


def match_part_for_tripo_mf(mf_mm: float) -> tuple[str, str]:
    """Pick library variant from Tripo island size (mf_mm = max XY on board)."""
    if mf_mm >= 180:
        return ("conn_slot", "wide")
    if mf_mm >= 130:
        return ("hsink", "fins14")
    if mf_mm >= 95:
        return ("conn_slot", "slot3")
    if mf_mm >= 72:
        return ("socket", "die")
    if mf_mm >= 58:
        return ("hsink", "fins10")
    if mf_mm >= 48:
        return ("oct", "medium")
    tiers: list[tuple[float, str, str]] = [
        (4.5, "smd", "block4"),
        (5.0, "smd", "pair0805"),
        (6.0, "ic_rect", "soic8"),
        (7.5, "ic_rect", "tssop20"),
        (9.0, "ic_sq", "qfp32"),
        (10.0, "ic_rect", "soic16"),
        (11.0, "ic_sq", "lqfp64"),
        (12.0, "bga", "10"),
        (13.0, "bga", "14"),
        (14.0, "bga", "20"),
        (15.0, "ic_sq", "lqfp64_w"),
        (16.0, "cap_cyl", "2x2"),
        (18.0, "hsink", "fins6"),
        (20.0, "dip", "24"),
        (22.0, "hsink", "stepped"),
        (24.0, "cap_cyl", "row4"),
    ]
    best = tiers[0][1:]
    best_d = 1e9
    for target, arch, var in tiers:
        d = abs(mf_mm - target)
        if d < best_d:
            best_d = d
            best = (arch, var)
    return best


def zone_for_xy(x: float, y: float) -> str:
    if x < -40 and y > 20:
        return "NW"
    if x > 40 and y > 20:
        return "NE"
    if x < -40 and y < -20:
        return "SW"
    if x > 40 and y < -20:
        return "SE"
    if y > 20:
        return "N"
    if y < -20:
        if x < -40:
            return "SW"
        if x > 40:
            return "SE"
        return "C"
    if x < -40:
        return "W"
    if x > 40:
        return "E"
    return "C"


# ---------------------------------------------------------------------------
# stylized component builders (bottom-center origin, Z=0 feet)
# ---------------------------------------------------------------------------


def _qfp_stylized(body_w, n_per_side, body_h=1.5, leg_w=0.38, foot_l=1.0):
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.15, body_w, body_w, body_h)
    bm_add_box(bm, 0.0, 0.0, 0.15 + body_h - 0.06, body_w - 1.4, body_w - 1.4, 0.06)
    bm_legs_qfp(bm, n_per_side, body_w, body_w, 0.15 + body_h, leg_w=leg_w, foot_l=foot_l, foot_h=0.22)
    bm_pin1_dot(bm, -(body_w * 0.5 - 1.2), body_w * 0.5 - 1.2, 0.15 + body_h)
    return bm


def cl_ic_sq_qfp32():
    return _qfp_stylized(8.0, 8, body_h=1.35)


def cl_ic_sq_lqfp64():
    return _qfp_stylized(12.0, 16, body_h=1.55)


def cl_ic_sq_lqfp64_w():
    return _qfp_stylized(16.0, 20, body_h=1.6, leg_w=0.32)


def cl_ic_sq_wide():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.2, 18.0, 18.0, 1.2)
    bm_add_box(bm, 0.0, 0.0, 1.4, 15.0, 15.0, 0.08)
    bm_legs_qfp(bm, 24, 18.0, 18.0, 1.4, leg_w=0.3, foot_l=0.95)
    return bm


def cl_ic_rect_soic8():
    bm = bmesh.new()
    bw, bh, bz = 5.5, 4.2, 1.6
    bm_add_box(bm, 0.0, 0.0, 0.12, bw, bh, bz)
    bm_legs_y_pair(bm, 4, bw - 0.4, bz + 0.12, bh * 0.5, leg_w=0.48, foot_l=1.0, foot_h=0.28)
    bm_legs_y_pair(bm, 4, bw - 0.4, bz + 0.12, -bh * 0.5, leg_w=0.48, foot_l=1.0, foot_h=0.28)
    bm_pin1_dot(bm, -1.8, 1.5, bz + 0.12)
    return bm


def cl_ic_rect_soic16():
    bm = bmesh.new()
    bw, bh, bz = 10.0, 7.0, 1.85
    bm_add_box(bm, 0.0, 0.0, 0.15, bw, bh, bz)
    bm_legs_y_pair(bm, 8, bw - 0.5, bz + 0.15, bh * 0.5, leg_w=0.45, foot_l=1.05, foot_h=0.3)
    bm_legs_y_pair(bm, 8, bw - 0.5, bz + 0.15, -bh * 0.5, leg_w=0.45, foot_l=1.05, foot_h=0.3)
    return bm


def cl_ic_rect_tssop20():
    bm = bmesh.new()
    bw, bh, bz = 9.0, 3.2, 1.1
    bm_add_box(bm, 0.0, 0.0, 0.1, bw, bh, bz)
    bm_legs_y_pair(bm, 10, bw - 0.3, bz + 0.1, bh * 0.5, leg_w=0.24, foot_l=0.65, foot_h=0.18)
    bm_legs_y_pair(bm, 10, bw - 0.3, bz + 0.1, -bh * 0.5, leg_w=0.24, foot_l=0.65, foot_h=0.18)
    return bm


def cl_ic_rect_2side():
    bm = bmesh.new()
    bw, bh, bz = 14.0, 5.0, 1.4
    bm_add_box(bm, 0.0, 0.0, 0.12, bw, bh, bz)
    bm_legs_y_pair(bm, 14, bw - 0.4, bz + 0.12, bh * 0.5, leg_w=0.3, foot_l=0.8, foot_h=0.22)
    bm_legs_y_pair(bm, 14, bw - 0.4, bz + 0.12, -bh * 0.5, leg_w=0.3, foot_l=0.8, foot_h=0.22)
    return bm


def _bga_cap(size, ball_n=6):
    bm = bmesh.new()
    bm_pad(bm, 0.0, 0.0, size + 1.0, size + 1.0)
    bm_add_box(bm, 0.0, 0.0, 0.05, size, size, 1.85)
    bm_add_box(bm, 0.0, 0.0, 1.9, size - 1.0, size - 1.0, 0.35)
    pitch = (size - 2) / max(ball_n - 1, 1)
    o = (size - 2) * 0.5
    for r in range(ball_n):
        for c in range(ball_n):
            x = -o + c * pitch
            y = -o + r * pitch
            bm_add_box(bm, x, y, 0.0, 0.4, 0.4, 0.16)
    return bm


def cl_bga_10():
    return _bga_cap(10.0, 5)


def cl_bga_14():
    return _bga_cap(14.0, 7)


def cl_bga_20():
    return _bga_cap(20.0, 8)


def cl_cap_cyl_short():
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.0, 3.2, 9.0, 10)
    bm_add_box(bm, 0.0, 0.0, 9.0, 4.0, 0.4, 0.05)
    bm_add_box(bm, 1.0, 0.0, -2.5, 0.45, 0.45, 2.5)
    bm_add_box(bm, -1.0, 0.0, -2.5, 0.45, 0.45, 2.5)
    return bm


def cl_cap_cyl_tall():
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.0, 3.8, 16.0, 10)
    bm_add_box(bm, 0.0, 0.0, 16.0, 4.5, 0.45, 0.05)
    return bm


def cl_cap_cyl_cluster_2x2():
    bm = bmesh.new()
    for ox, oy in ((-3.8, -3.8), (3.8, -3.8), (-3.8, 3.8), (3.8, 3.8)):
        bm_add_hex_prism(bm, ox, oy, 0.0, 2.6, 11.0, 10)
    return bm


def cl_cap_cyl_row4():
    bm = bmesh.new()
    for i in range(4):
        bm_add_hex_prism(bm, -5.4 + i * 3.6, 0.0, 0.0, 2.4, 10.0, 10)
    return bm


def cl_hsink_fins_6():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 28.0, 22.0, 3.0)
    for i in range(6):
        x = -10.0 + i * 4.0
        bm_add_box(bm, x, 0.0, 3.0, 0.9, 20.0, 16.0)
    return bm


def cl_hsink_fins_10():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 38.0, 30.0, 3.5)
    n = 10
    pitch = 34.0 / (n - 1)
    for i in range(n):
        x = -17.0 + i * pitch
        bm_add_box(bm, x, 0.0, 3.5, 1.0, 28.0, 20.0)
    bm_add_box(bm, 0.0, 14.5, 3.5, 38.0, 0.55, 20.0)
    bm_add_box(bm, 0.0, -14.5, 3.5, 38.0, 0.55, 20.0)
    return bm


def cl_hsink_fins_14():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 48.0, 36.0, 4.0)
    n = 14
    pitch = 44.0 / (n - 1)
    for i in range(n):
        x = -22.0 + i * pitch
        bm_add_box(bm, x, 0.0, 4.0, 0.95, 34.0, 22.0)
    return bm


def cl_hsink_stepped():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 26.0, 26.0, 5.0)
    bm_add_box(bm, 0.0, 0.0, 5.0, 22.0, 22.0, 4.0)
    bm_add_box(bm, 0.0, 0.0, 9.0, 18.0, 18.0, 4.5)
    bm_add_box(bm, 0.0, 0.0, 13.5, 14.0, 14.0, 3.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * 11.0, sy * 11.0, 0.0, 3.0, 3.0, 4.0)
    return bm


def cl_smd_pair_0201():
    bm = bmesh.new()
    for ox in (-0.9, 0.9):
        bm_pad(bm, ox - 0.4, 0.0, 0.4, 0.5)
        bm_pad(bm, ox + 0.4, 0.0, 0.4, 0.5)
        bm_add_box(bm, ox, 0.0, 0.05, 0.9, 0.45, 0.32)
    return bm


def cl_smd_row6():
    bm = bmesh.new()
    for i in range(6):
        cx = -4.0 + i * 1.6
        bm_pad(bm, cx - 0.45, 0.0, 0.45, 0.55)
        bm_pad(bm, cx + 0.45, 0.0, 0.45, 0.55)
        bm_add_box(bm, cx, 0.0, 0.05, 1.0, 0.5, 0.38)
    return bm


def cl_smd_pair_0805():
    bm = bmesh.new()
    for ox in (-1.2, 1.2):
        bm_pad(bm, ox - 0.55, 0.0, 0.55, 0.65)
        bm_pad(bm, ox + 0.55, 0.0, 0.55, 0.65)
        bm_add_box(bm, ox, 0.0, 0.05, 1.4, 0.75, 0.55)
    return bm


def cl_smd_block4():
    bm = bmesh.new()
    for ox, oy in ((-1.4, -0.7), (1.4, -0.7), (-1.4, 0.7), (1.4, 0.7)):
        bm_add_box(bm, ox, oy, 0.05, 1.1, 0.55, 0.4)
    return bm


def cl_conn_slot3():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 42.0, 28.0, 1.2)
    for sx in (-11.0, 0.0, 11.0):
        bm_add_box(bm, sx, 0.0, 1.2, 8.0, 24.0, 6.0)
        bm_add_box(bm, sx, 0.0, 7.2, 6.0, 22.0, 0.5)
    return bm


def cl_conn_pcie():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 34.0, 4.5, 1.6)
    bm_add_box(bm, 0.0, 0.0, 1.6, 32.0, 2.8, 10.0)
    for i in range(20):
        x = -14.5 + i * (29.0 / 19.0)
        bm_add_box(bm, x, 0.0, 1.6, 0.65, 1.3, 8.5)
    return bm


def cl_conn_usb():
    bm = bmesh.new()
    t = 0.9
    w, d, h = 13.5, 16.5, 7.0
    bm_add_box(bm, 0.0, d * 0.5 - t * 0.5, h * 0.5, w, t, h)
    bm_add_box(bm, 0.0, -d * 0.5 + t * 0.5, h * 0.5, w, t, h)
    bm_add_box(bm, w * 0.5 - t * 0.5, 0.0, h * 0.5, t, d - 2 * t, h)
    bm_add_box(bm, -w * 0.5 + t * 0.5, 0.0, h * 0.5, t, d - 2 * t, h)
    bm_add_box(bm, 0.0, 1.5, 1.8, w - 2.8, d - 4.0, 1.2)
    return bm


def cl_conn_wide():
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 52.0, 22.0, 1.0)
    for i in range(5):
        x = -20.0 + i * 10.0
        bm_add_box(bm, x, 0.0, 1.0, 6.0, 18.0, 4.5)
    bm_add_box(bm, 0.0, 0.0, 5.5, 48.0, 2.0, 0.4)
    return bm


def cl_oct_low():
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.0, 9.0, 2.2, 8)
    bm_add_hex_prism(bm, 0.0, 0.0, 2.2, 7.5, 0.35, 8)
    return bm


def cl_oct_medium():
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.0, 11.0, 3.5, 8)
    bm_add_box(bm, 0.0, 0.0, 3.5, 14.0, 14.0, 0.5)
    return bm


def cl_socket_frame():
    bm = bmesh.new()
    s, t = 38.0, 2.6
    bm_add_box(bm, 0.0, s * 0.5 - t * 0.5, 0.0, s, t, 3.0)
    bm_add_box(bm, 0.0, -s * 0.5 + t * 0.5, 0.0, s, t, 3.0)
    bm_add_box(bm, s * 0.5 - t * 0.5, 0.0, 0.0, t, s - 2 * t, 3.0)
    bm_add_box(bm, -s * 0.5 + t * 0.5, 0.0, 0.0, t, s - 2 * t, 3.0)
    bm_add_box(bm, 0.0, 0.0, 3.0, 26.0, 26.0, 0.35)
    for r in range(5):
        for c in range(5):
            x = -8.0 + c * 4.0
            y = -8.0 + r * 4.0
            bm_add_box(bm, x, y, 3.35, 0.35, 0.35, 0.25)
    return bm


def cl_socket_die():
    bm = cl_socket_frame()
    bm_add_box(bm, 0.0, 0.0, 3.7, 20.0, 20.0, 0.9)
    bm_add_box(bm, 0.0, 0.0, 4.6, 12.0, 12.0, 0.05)
    return bm


def cl_dip_14():
    bm = bmesh.new()
    bw, bh, bz = 17.0, 6.5, 3.5
    bm_add_box(bm, 0.0, 0.0, 0.5, bw, bh, bz)
    for i in range(7):
        x = -6.8 + i * 2.2
        for sy in (-1, 1):
            bm_add_box(bm, x, sy * 2.8, -2.0, 0.5, 0.42, 2.5)
    return bm


def cl_dip_24():
    bm = bmesh.new()
    bw, bh, bz = 30.0, 7.0, 3.8
    bm_add_box(bm, 0.0, 0.0, 0.6, bw, bh, bz)
    for i in range(12):
        x = -12.5 + i * 2.18
        for sy in (-1, 1):
            bm_add_box(bm, x, sy * 3.0, -2.2, 0.52, 0.44, 2.8)
    return bm


# (archetype, variant) -> (builder, half_w, half_d) for AABB placement
PARTS: dict[tuple[str, str], tuple] = {
    ("ic_sq", "qfp32"): (cl_ic_sq_qfp32, 6.5, 6.5),
    ("ic_sq", "lqfp64"): (cl_ic_sq_lqfp64, 9.5, 9.5),
    ("ic_sq", "lqfp64_w"): (cl_ic_sq_lqfp64_w, 12.5, 12.5),
    ("ic_sq", "wide"): (cl_ic_sq_wide, 14.0, 14.0),
    ("ic_rect", "soic8"): (cl_ic_rect_soic8, 4.5, 3.5),
    ("ic_rect", "soic16"): (cl_ic_rect_soic16, 7.5, 5.5),
    ("ic_rect", "tssop20"): (cl_ic_rect_tssop20, 6.5, 2.5),
    ("ic_rect", "2side"): (cl_ic_rect_2side, 10.0, 4.0),
    ("bga", "10"): (cl_bga_10, 7.0, 7.0),
    ("bga", "14"): (cl_bga_14, 9.5, 9.5),
    ("bga", "20"): (cl_bga_20, 13.0, 13.0),
    ("cap_cyl", "short"): (cl_cap_cyl_short, 4.5, 4.5),
    ("cap_cyl", "tall"): (cl_cap_cyl_tall, 5.0, 5.0),
    ("cap_cyl", "2x2"): (cl_cap_cyl_cluster_2x2, 8.5, 8.5),
    ("cap_cyl", "row4"): (cl_cap_cyl_row4, 10.0, 3.5),
    ("hsink", "fins6"): (cl_hsink_fins_6, 16.0, 13.0),
    ("hsink", "fins10"): (cl_hsink_fins_10, 22.0, 17.0),
    ("hsink", "fins14"): (cl_hsink_fins_14, 28.0, 21.0),
    ("hsink", "stepped"): (cl_hsink_stepped, 16.0, 16.0),
    ("smd", "pair0201"): (cl_smd_pair_0201, 2.2, 1.2),
    ("smd", "row6"): (cl_smd_row6, 5.5, 1.2),
    ("smd", "pair0805"): (cl_smd_pair_0805, 3.0, 1.5),
    ("smd", "block4"): (cl_smd_block4, 2.5, 1.5),
    ("conn_slot", "slot3"): (cl_conn_slot3, 24.0, 16.0),
    ("conn_slot", "pcie"): (cl_conn_pcie, 19.0, 6.0),
    ("conn_slot", "usb"): (cl_conn_usb, 9.0, 10.0),
    ("conn_slot", "wide"): (cl_conn_wide, 28.0, 13.0),
    ("oct", "low"): (cl_oct_low, 11.0, 11.0),
    ("oct", "medium"): (cl_oct_medium, 13.0, 13.0),
    ("socket", "frame"): (cl_socket_frame, 22.0, 22.0),
    ("socket", "die"): (cl_socket_die, 22.0, 22.0),
    ("dip", "14"): (cl_dip_14, 10.0, 4.5),
    ("dip", "24"): (cl_dip_24, 17.0, 5.0),
}

# ---------------------------------------------------------------------------
# placement manifest — zone-tagged, snapped to 2 mm grid
# (archetype, variant, x, y, rot_deg, zone)
# ---------------------------------------------------------------------------

def _p(zone: str, arch: str, var: str, x: float, y: float, rot: int = 0):
    x = round(x * LAYOUT_COMPRESS * CLUSTER_PULL / 2) * 2
    y = round(y * LAYOUT_COMPRESS * CLUSTER_PULL / 2) * 2
    return (arch, var, x, y, rot, zone)


PLACEMENTS: list[tuple] = [
    # NW — large heatsink + neighbors
    _p("NW", "conn_slot", "slot3", -200, 5),
    _p("NW", "hsink", "fins14", -190, 130),
    _p("NW", "hsink", "stepped", -118, 118),
    _p("NW", "ic_sq", "lqfp64_w", -100, 140),
    _p("NW", "cap_cyl", "2x2", -210, 70),
    _p("NW", "ic_rect", "soic16", -160, 90),
    _p("NW", "bga", "14", -120, 100),
    _p("NW", "smd", "row6", -170, 50),
    _p("NW", "ic_rect", "tssop20", -130, 60, 90),
    _p("NW", "smd", "pair0805", -200, 40),
    _p("NW", "ic_sq", "qfp32", -90, 80),
    _p("NW", "cap_cyl", "short", -220, 20),
    _p("NW", "cap_cyl", "short", -205, 18),
    # N center — dense IC row
    _p("N", "ic_sq", "wide", -24, 152),
    _p("N", "socket", "die", 50, 155),
    _p("N", "ic_sq", "lqfp64", 110, 150),
    _p("N", "ic_rect", "2side", 170, 145, 90),
    _p("N", "bga", "20", 36, 100),
    _p("N", "ic_sq", "qfp32", -60, 120),
    _p("N", "ic_sq", "qfp32", -40, 118),
    _p("N", "ic_sq", "qfp32", -20, 120),
    _p("N", "ic_rect", "soic8", 80, 125),
    _p("N", "ic_rect", "soic8", 95, 123),
    _p("N", "ic_rect", "soic16", 130, 120),
    _p("N", "cap_cyl", "row4", -80, 100),
    _p("N", "hsink", "fins6", 142, 92),
    _p("N", "smd", "block4", 0, 110),
    _p("N", "smd", "block4", 20, 108),
    _p("N", "smd", "pair0805", 60, 112),
    _p("N", "smd", "pair0805", 75, 110),
    # NE — connectors + BGA (wide first — large footprint)
    _p("NE", "conn_slot", "wide", 225, 40),
    _p("NE", "conn_slot", "pcie", 200, 70, 90),
    _p("NE", "conn_slot", "usb", 220, 30),
    _p("NE", "bga", "14", 170, 90),
    _p("NE", "bga", "10", 185, 55),
    _p("NE", "ic_sq", "lqfp64", 148, 72),
    _p("NE", "ic_rect", "tssop20", 165, 50, 90),
    _p("NE", "dip", "14", 190, 10),
    _p("NE", "smd", "row6", 140, 60),
    _p("NE", "cap_cyl", "tall", 168, 8),
    _p("NE", "cap_cyl", "tall", 182, 6),
    # W — cap clusters + SOIC
    _p("W", "cap_cyl", "2x2", -210, -20),
    _p("W", "cap_cyl", "2x2", -200, -60),
    _p("W", "cap_cyl", "row4", -180, -100),
    _p("W", "ic_rect", "soic16", -150, -40),
    _p("W", "ic_rect", "soic8", -130, -70),
    _p("W", "ic_sq", "qfp32", -110, -30),
    _p("W", "dip", "24", -170, -130, 90),
    _p("W", "smd", "pair0805", -195, -85),
    _p("W", "bga", "10", -120, -90),
    _p("W", "hsink", "fins6", -80, -120),
    # C — central dense mix
    _p("C", "ic_sq", "lqfp64", -30, 40),
    _p("C", "ic_sq", "lqfp64_w", 14, 30),
    _p("C", "bga", "20", 52, 38),
    _p("C", "ic_rect", "soic16", -50, 10),
    _p("C", "ic_rect", "tssop20", 40, 15, 90),
    _p("C", "ic_sq", "qfp32", 0, -10),
    _p("C", "ic_sq", "qfp32", 15, -12),
    _p("C", "ic_sq", "qfp32", 28, -18),
    _p("C", "ic_rect", "soic8", -70, 25),
    _p("C", "ic_rect", "soic8", -55, 22),
    _p("C", "socket", "frame", 88, 8),
    _p("C", "cap_cyl", "short", -90, -20),
    _p("C", "cap_cyl", "short", -75, -22),
    _p("C", "cap_cyl", "short", 55, -25),
    _p("C", "hsink", "fins10", -10, -70),
    _p("C", "ic_rect", "2side", 100, 0, 90),
    _p("C", "bga", "14", 120, -30),
    _p("C", "smd", "row6", -40, -45),
    _p("C", "smd", "row6", 50, -50),
    _p("C", "smd", "block4", -15, 55),
    _p("C", "smd", "pair0805", 65, 5),
    # E — right column BGAs / ICs
    _p("E", "bga", "20", 180, 28),
    _p("E", "bga", "14", 200, -20),
    _p("E", "ic_sq", "lqfp64_w", 160, 10),
    _p("E", "ic_sq", "qfp32", 175, -50),
    _p("E", "ic_sq", "qfp32", 190, -48),
    _p("E", "ic_rect", "soic16", 150, -60),
    _p("E", "cap_cyl", "2x2", 210, -70),
    _p("E", "hsink", "stepped", 130, -90),
    _p("E", "smd", "pair0805", 165, -35),
    # SW — octagon + caps
    _p("SW", "oct", "medium", 70, -150),
    _p("SW", "oct", "low", 30, -165),
    _p("SW", "cap_cyl", "row4", -60, -160),
    _p("SW", "cap_cyl", "2x2", -100, -150),
    _p("SW", "ic_sq", "qfp32", 10, -140),
    _p("SW", "ic_rect", "soic8", -30, -130),
    _p("SW", "dip", "14", -80, -170),
    _p("SW", "bga", "10", 110, -155),
    _p("SW", "smd", "block4", 50, -135),
    _p("SW", "smd", "pair0805", -50, -145),
    # SE — slot module + bottom edge
    _p("SE", "conn_slot", "pcie", 150, -170),
    _p("SE", "conn_slot", "usb", 220, -160),
    _p("SE", "ic_sq", "wide", 100, -120),
    _p("SE", "cap_cyl", "tall", 40, -175),
    _p("SE", "cap_cyl", "tall", 55, -172),
    _p("SE", "cap_cyl", "tall", 70, -175),
    _p("SE", "ic_rect", "soic16", 130, -150),
    _p("SE", "bga", "14", 200, -120),
    _p("SE", "smd", "row6", 0, -155),
    _p("SE", "smd", "row6", 25, -158),
    # extra fill along aisles
    _p("C", "smd", "block4", -100, 60),
    _p("C", "smd", "block4", 110, 70),
    _p("N", "smd", "block4", 145, 95),
    _p("W", "smd", "block4", -145, -15),
    _p("E", "smd", "block4", 145, 25),
    _p("NE", "ic_sq", "qfp32", 155, 35),
    _p("NW", "ic_rect", "soic8", -75, 55),
    _p("SE", "ic_sq", "qfp32", 165, -95),
    _p("SE", "ic_rect", "tssop20", 145, -110, 90),
    # gap-fill (nudged to avoid skips)
    _p("N", "smd", "block4", 18, 106),
    _p("NE", "cap_cyl", "tall", 178, 2),
    _p("C", "ic_sq", "qfp32", 44, -22),
    _p("C", "socket", "frame", 102, 14),
    _p("E", "ic_sq", "lqfp64_w", 152, 18),
    _p("E", "ic_sq", "qfp32", 184, -58),
    _p("SE", "ic_sq", "wide", 92, -128),
    _p("W", "smd", "block4", -192, -95),
    _p("C", "smd", "block4", -108, 64),
    _p("E", "bga", "10", 172, -58),
    _p("N", "ic_rect", "soic8", 62, 118),
    _p("SW", "cap_cyl", "short", -110, -158),
    _p("C", "ic_rect", "soic8", -38, -55),
    _p("NE", "smd", "pair0805", 158, 42),
]

# Procedural SMD fill — block4/0805 only (no tiny 0201 rice); pre-compress coords
SMD_FILL_ZONES = [
    ("C", "pair0805", -35, -48, 48, -8, 3.8, 5),
    ("N", "block4", 5, 72, 72, 90, 3.8, 3),
    ("NW", "pair0805", -155, 22, -88, 55, 3.8, 3),
]
MAX_SMD_FILL_TOTAL = 0

# ---------------------------------------------------------------------------
# placement + assembly
# ---------------------------------------------------------------------------


# Scaled mesh half-extents after library build (filled by build_library).
SCALED_FOOTPRINT: dict[tuple[str, str], tuple[float, float]] = {}


def footprint_hw_hd(arch: str, var: str, rot_deg: int) -> tuple[float, float]:
    key = (arch, var)
    if key in SCALED_FOOTPRINT:
        hw, hd = SCALED_FOOTPRINT[key]
    else:
        _, hw, hd = PARTS[key]
        s = mesh_scale_for(key)
        hw *= s * FOOTPRINT_PLACE_SCALE
        hd *= s * FOOTPRINT_PLACE_SCALE
    if rot_deg in (90, 270):
        return hd, hw
    return hw, hd


class PlacedBox:
    __slots__ = ("name", "x", "y", "hw", "hd", "zone")

    def __init__(self, name: str, x: float, y: float, hw: float, hd: float, zone: str):
        self.name = name
        self.x = x
        self.y = y
        self.hw = hw
        self.hd = hd
        self.zone = zone

    def overlaps(self, other: PlacedBox, gap: float) -> bool:
        return (
            abs(self.x - other.x) < self.hw + other.hw + gap
            and abs(self.y - other.y) < self.hd + other.hd + gap
        )


def fits(boxes: list[PlacedBox], x: float, y: float, hw: float, hd: float) -> bool:
    for b in boxes:
        t = PlacedBox("_", x, y, hw, hd, "")
        if t.overlaps(b, GAP_MM):
            return False
    return True


def build_library(coll_parts, origin_x: float) -> dict[tuple[str, str], bpy.types.Object]:
    keys = list(PARTS.keys())
    cols = 8
    pitch_x, pitch_y = 44.0, 40.0
    lib: dict[tuple[str, str], bpy.types.Object] = {}
    SCALED_FOOTPRINT.clear()
    for i, key in enumerate(keys):
        arch, var = key
        builder, _, _ = PARTS[key]
        bm = builder()
        name = f"cl_{arch}_{var}"
        loc = grid_slot(i, cols, pitch_x, pitch_y, origin_x, -120.0)
        ob = put_object(name, bm, coll_parts, loc)
        apply_visual_scale(ob, key)
        bpy.context.view_layer.update()
        hw, hd = object_xy_half_extents(ob)
        SCALED_FOOTPRINT[key] = (hw * FOOTPRINT_PLACE_SCALE, hd * FOOTPRINT_PLACE_SCALE)
        lib[key] = ob
    return lib


def build_board_base(coll_asm) -> bpy.types.Object:
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, -BOARD_T, BOARD_W, BOARD_D, BOARD_T)
    return put_object("cl_board", bm, coll_asm, Vector((0.0, 0.0, 0.0)))


def instance_part(
    lib: dict[tuple[str, str], bpy.types.Object],
    coll_asm,
    name: str,
    key: tuple[str, str],
    loc: Vector,
    rot_deg: float,
) -> bpy.types.Object:
    src = lib[key]
    ob = src.copy()
    ob.data = src.data
    ob.name = name
    coll_asm.objects.link(ob)
    ob.location = loc
    ob.rotation_euler.z = math.radians(rot_deg)
    ob.scale = src.scale
    return ob


def generate_smd_placements(boxes: list[PlacedBox]) -> list[tuple]:
    out = []
    idx = 0
    for zone, variant, x0, y0, x1, y1, step, max_count in SMD_FILL_ZONES:
        if idx >= MAX_SMD_FILL_TOTAL:
            break
        scale = LAYOUT_COMPRESS * CLUSTER_PULL
        x0 = round(x0 * scale / 2) * 2
        x1 = round(x1 * scale / 2) * 2
        y0 = round(y0 * scale / 2) * 2
        y1 = round(y1 * scale / 2) * 2
        arch = "smd"
        hw, hd = footprint_hw_hd(arch, variant, 0)
        placed_in_zone = 0
        y = y0
        while y <= y1 and placed_in_zone < max_count and idx < MAX_SMD_FILL_TOTAL:
            x = x0
            while x <= x1 and placed_in_zone < max_count and idx < MAX_SMD_FILL_TOTAL:
                if fits(boxes, x, y, hw, hd):
                    out.append((arch, variant, x, y, 0, zone, idx))
                    idx += 1
                    placed_in_zone += 1
                x += step
            y += step
    return out


def _slot_row(slot: dict, arch: str, var: str) -> tuple:
    x, y = int(slot["x"]), int(slot["y"])
    zone = zone_for_xy(x, y)
    hw = slot["hw"] * FOOTPRINT_PLACE_SCALE
    hd = slot["hd"] * FOOTPRINT_PLACE_SCALE
    return (arch, var, x, y, 0, zone, hw, hd)


def tripo_derived_placements() -> list[tuple]:
    """Map Tripo Layout islands to library parts at Tripo board coordinates."""
    slots = read_tripo_slots()
    out: list[tuple] = []
    used: set[tuple[int, int]] = set()

    def take_slot(slot: dict, arch: str, var: str) -> None:
        row = _slot_row(slot, arch, var)
        key = (row[2], row[3])
        if key in used:
            return
        used.add(key)
        out.append(row)

    by_zone: dict[str, list[dict]] = {}
    for slot in slots:
        by_zone.setdefault(zone_for_xy(slot["x"], slot["y"]), []).append(slot)

    if by_zone.get("NW"):
        take_slot(max(by_zone["NW"], key=lambda s: s["mf"]), "hsink", "fins14")
    if by_zone.get("N"):
        take_slot(max(by_zone["N"], key=lambda s: s["mf"]), "socket", "die")
    if by_zone.get("SW"):
        take_slot(max(by_zone["SW"], key=lambda s: s["mf"]), "oct", "medium")
    if by_zone.get("NE"):
        take_slot(max(by_zone["NE"], key=lambda s: s["mf"]), "conn_slot", "wide")

    for slot in sorted(slots, key=lambda s: (-s["mf"], s["y"], s["x"])):
        key = (int(slot["x"]), int(slot["y"]))
        if key in used:
            continue
        arch, var = match_part_for_tripo_mf(slot["mf"])
        take_slot(slot, arch, var)

    return out


# Heroes only when Tripo matching missed a landmark (open grid cell).
PLACEMENT_HERO_OVERRIDES: list[tuple] = [
    _p("NW", "conn_slot", "slot3", -200, 5),
    _p("NE", "conn_slot", "wide", 225, 40),
    _p("SW", "oct", "medium", 70, -150),
]


def merged_placements() -> list[tuple]:
    """Tripo island layout + explicit hero overrides when a slot is still open."""
    merged: list[tuple] = list(tripo_derived_placements())
    occupied = {(int(r[2]), int(r[3])) for r in merged}
    for arch, var, x, y, rot, zone in PLACEMENT_HERO_OVERRIDES:
        xi, yi = int(x), int(y)
        if (xi, yi) in occupied:
            continue
        hw, hd = footprint_hw_hd(arch, var, rot)
        merged.append((arch, var, xi, yi, rot, zone, hw, hd))
        occupied.add((xi, yi))
    return merged


def assemble_from_manifest(coll_asm, lib: dict) -> tuple[list[PlacedBox], list[tuple]]:
    boxes: list[PlacedBox] = []
    skipped: list[tuple] = []
    asm_index = 0

    def place_entry(
        arch,
        var,
        x,
        y,
        rot,
        zone,
        hw: float | None = None,
        hd: float | None = None,
        suffix: str = "",
    ):
        nonlocal asm_index
        key = (arch, var)
        if key not in PARTS:
            skipped.append((arch, var, x, y, "unknown_part"))
            return
        if hw is None or hd is None:
            hw, hd = footprint_hw_hd(arch, var, rot)
        lib_hw, lib_hd = footprint_hw_hd(arch, var, rot)
        hw = min(hw, lib_hw)
        hd = min(hd, lib_hd)
        if not fits(boxes, x, y, hw, hd):
            skipped.append((arch, var, x, y, "overlap"))
            return
        name = f"cl_asm_{zone}_{asm_index:03d}{suffix}"
        instance_part(lib, coll_asm, name, key, Vector((x, y, 0.0)), rot)
        boxes.append(PlacedBox(name, x, y, hw, hd, zone))
        asm_index += 1

    for row in merged_placements():
        if len(row) == 8:
            arch, var, x, y, rot, zone, hw, hd = row
            place_entry(arch, var, x, y, rot, zone, hw=hw, hd=hd)
        else:
            arch, var, x, y, rot, zone = row
            place_entry(arch, var, x, y, rot, zone)

    smd_extra = generate_smd_placements(boxes)
    for arch, var, x, y, rot, zone, sidx in smd_extra:
        place_entry(arch, var, x, y, rot, zone, suffix=f"_s{sidx:02d}")

    return boxes, skipped


def audit_overlaps(boxes: list[PlacedBox], gap: float = 0.5) -> list[tuple[str, str, float]]:
    hits = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a.overlaps(b, gap):
                dx = abs(a.x - b.x) - (a.hw + b.hw)
                dy = abs(a.y - b.y) - (a.hd + b.hd)
                hits.append((a.name, b.name, min(dx, dy)))
    return hits


def collection_bbox(coll) -> tuple[Vector, Vector]:
    lo = Vector((1e30,) * 3)
    hi = Vector((-1e30,) * 3)
    for ob in coll.objects:
        if ob.type != "MESH" or not ob.data.vertices:
            continue
        for corner in ob.bound_box:
            c = ob.matrix_world @ Vector(corner)
            for k in range(3):
                lo[k] = min(lo[k], c[k])
                hi[k] = max(hi[k], c[k])
    return lo, hi


def _remove_cameras(prefix: str):
    for ob in list(bpy.data.objects):
        if ob.name.startswith(prefix):
            bpy.data.objects.remove(ob, do_unlink=True)
    for cam in list(bpy.data.cameras):
        if cam.name.startswith(prefix):
            bpy.data.cameras.remove(cam)


def setup_camera(
    scene: bpy.types.Scene,
    name: str,
    *,
    ortho: bool,
    location: Vector,
    rotation: tuple[float, float, float],
    ortho_scale: float | None = None,
    lens: float = 50.0,
) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO" if ortho else "PERSP"
    if ortho and ortho_scale is not None:
        cam_data.ortho_scale = ortho_scale
    if not ortho:
        cam_data.lens = lens
    cam_ob = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_ob)
    cam_ob.location = location
    cam_ob.rotation_euler = rotation
    return cam_ob


def content_span(lo: Vector, hi: Vector, margin: float = 1.03) -> tuple[Vector, float]:
    cx = (lo.x + hi.x) * 0.5
    cy = (lo.y + hi.y) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 80.0) * margin
    return Vector((cx, cy, 0.0)), span


def setup_top_camera(scene: bpy.types.Scene, lo: Vector, hi: Vector):
    center, span = content_span(lo, hi)
    _remove_cameras("CircuitLayout_Cam")
    cam_ob = setup_camera(
        scene,
        "CircuitLayout_Cam_Top",
        ortho=True,
        location=center + Vector((0.0, 0.0, 350.0)),
        rotation=(0.0, 0.0, 0.0),
        ortho_scale=span,
    )
    scene.camera = cam_ob
    return cam_ob


def _ensure_diagnostic_material():
    mat = bpy.data.materials.get("CircuitLayout_Diag")
    if mat is None:
        mat = bpy.data.materials.new("CircuitLayout_Diag")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.55, 0.58, 0.62, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def _prep_diagnostic_render(scene: bpy.types.Scene, coll_asm):
    mat = _ensure_diagnostic_material()
    for ob in coll_asm.objects:
        if ob.type != "MESH":
            continue
        if not ob.data.materials:
            ob.data.materials.append(mat)
        elif ob.data.materials[0] is None:
            ob.data.materials[0] = mat

    if bpy.data.objects.get("CircuitLayout_Sun") is None:
        sun = bpy.data.lights.new("CircuitLayout_Sun", "SUN")
        sun.energy = 2.5
        sun_ob = bpy.data.objects.new("CircuitLayout_Sun", sun)
        scene.collection.objects.link(sun_ob)
        sun_ob.rotation_euler = (math.radians(55), 0.0, math.radians(25))

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("CircuitLayout_World")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.04, 0.04, 0.05, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def render_still(scene: bpy.types.Scene, coll_asm, filepath: str, cam_ob: bpy.types.Object):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "BLENDER_EEVEE"
    scene.camera = cam_ob
    _prep_diagnostic_render(scene, coll_asm)
    bpy.ops.render.render(write_still=True)


def render_diagnostic_views(scene: bpy.types.Scene, coll_asm, lo: Vector, hi: Vector) -> list[str]:
    """Multi-angle verification against the ChatGPT reference."""
    center, span = content_span(lo, hi)
    out_dir = os.path.join(_script_dir, "renders")
    paths: list[str] = []
    _remove_cameras("CircuitLayout_Cam")

    shots: list[tuple[str, bool, Vector, tuple[float, float, float], float | None, float]] = [
        # tag, ortho, location offset from center, rotation (rad), ortho_scale, lens
        ("top", True, Vector((0.0, 0.0, 320.0)), (0.0, 0.0, 0.0), span, 50.0),
        # Primary reference angle (~52° elev, front-right quarter)
        ("ref", False, Vector((span * 0.48, -span * 0.62, span * 0.82)), (math.radians(52), 0.0, math.radians(30)), None, 36.0),
        ("ref-low", False, Vector((span * 0.55, -span * 0.45, span * 0.65)), (math.radians(40), 0.0, math.radians(25)), None, 40.0),
        ("ref-high", False, Vector((span * 0.4, -span * 0.75, span * 1.05)), (math.radians(62), 0.0, math.radians(35)), None, 34.0),
        ("from-left", False, Vector((-span * 0.75, -span * 0.35, span * 0.7)), (math.radians(50), 0.0, math.radians(-18)), None, 38.0),
        ("from-right", False, Vector((span * 0.78, -span * 0.3, span * 0.68)), (math.radians(50), 0.0, math.radians(42)), None, 38.0),
        ("from-front", False, Vector((0.0, -span * 0.85, span * 0.75)), (math.radians(48), 0.0, 0.0), None, 40.0),
    ]
    for tag, ortho, loc, rot, ortho_scale, lens in shots:
        cam = setup_camera(
            scene,
            f"CircuitLayout_Cam_{tag}",
            ortho=ortho,
            location=center + loc,
            rotation=rot,
            ortho_scale=ortho_scale,
            lens=lens,
        )
        path = os.path.join(out_dir, f"circuit-layout-{tag}.png")
        render_still(scene, coll_asm, path, cam)
        paths.append(path)

    half = span * 0.38
    quads = [
        ("nw", Vector((lo.x + half * 0.5, hi.y - half * 0.42, 0.0))),
        ("ne", Vector((hi.x - half * 0.5, hi.y - half * 0.42, 0.0))),
        ("sw", Vector((lo.x + half * 0.5, lo.y + half * 0.42, 0.0))),
        ("se", Vector((hi.x - half * 0.5, lo.y + half * 0.42, 0.0))),
    ]
    for tag, quad_center in quads:
        cam = setup_camera(
            scene,
            f"CircuitLayout_Cam_{tag}",
            ortho=True,
            location=quad_center + Vector((0.0, 0.0, 180.0)),
            rotation=(0.0, 0.0, 0.0),
            ortho_scale=half,
        )
        path = os.path.join(out_dir, f"circuit-layout-{tag}.png")
        render_still(scene, coll_asm, path, cam)
        paths.append(path)

    return paths


def build_all():
    scene = get_target_scene()
    bpy.context.window.scene = scene

    purge_collection(COLL_ASM)
    purge_collection(COLL_PARTS)
    coll_asm = coll_ensure(COLL_ASM, scene)
    coll_parts = coll_ensure(COLL_PARTS, scene)

    lib_origin_x = BOARD_W * 0.5 + 60.0
    lib = build_library(coll_parts, lib_origin_x)
    build_board_base(coll_asm)
    boxes, skipped = assemble_from_manifest(coll_asm, lib)

    bpy.context.view_layer.update()
    lo, hi = collection_bbox(coll_asm)
    overlaps = audit_overlaps(boxes)
    zone_counts: dict[str, int] = {}
    for b in boxes:
        zone_counts[b.zone] = zone_counts.get(b.zone, 0) + 1

    return {
        "lib_count": len(lib),
        "asm_count": len(boxes),
        "skipped": skipped,
        "overlaps": overlaps,
        "bbox_lo": lo,
        "bbox_hi": hi,
        "zone_counts": zone_counts,
        "coll_asm": coll_asm,
        "scene": scene,
    }


if __name__ == "__main__":
    tripo_n = len(read_tripo_slots())
    print(f"[circuit_layout] tripo_slots={tripo_n}")
    stats = build_all()
    print(
        f"[circuit_layout] library={stats['lib_count']} "
        f"assembled={stats['asm_count']} skipped={len(stats['skipped'])} "
        f"overlaps={len(stats['overlaps'])}"
    )
    print(f"[circuit_layout] zones: {stats['zone_counts']}")
    lo, hi = stats["bbox_lo"], stats["bbox_hi"]
    print(f"[circuit_layout] bbox x={lo.x:.1f}..{hi.x:.1f} y={lo.y:.1f}..{hi.y:.1f} z={lo.z:.1f}..{hi.z:.1f}")
    if stats["skipped"]:
        print(f"[circuit_layout] first skips: {stats['skipped'][:8]}")
        slot_skips = [s for s in stats["skipped"] if s[0] == "conn_slot" and s[1] == "slot3"]
        if slot_skips:
            print(f"[circuit_layout] slot3 skips: {slot_skips[:5]}")
    if stats["overlaps"]:
        print(f"[circuit_layout] overlap pairs: {stats['overlaps'][:10]}")

    def _has_mesh(suffix: str) -> bool:
        return any(
            o.type == "MESH" and o.data and suffix in o.data.name
            for o in stats["coll_asm"].objects
        )

    for label, suffix in [
        ("NW_heatsink", "cl_hsink_fins14"),
        ("N_socket", "cl_socket_die"),
        ("SW_oct", "cl_oct_medium"),
        ("NW_slot3", "cl_conn_slot_slot3"),
        ("NE_wide", "cl_conn_slot_wide"),
    ]:
        print(f"[circuit_layout] hero {label}: {'OK' if _has_mesh(suffix) else 'MISSING'}")

    render_paths = render_diagnostic_views(
        stats["scene"], stats["coll_asm"], stats["bbox_lo"], stats["bbox_hi"]
    )
    fill_objs = [o.name for o in stats["coll_asm"].objects if "fill" in o.name.lower()]
    print(f"[circuit_layout] cl_asm_fill count={len(fill_objs)}")
    for rp in render_paths:
        print(f"[circuit_layout] render -> {rp}")

    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[circuit_layout] saved main.blend")
