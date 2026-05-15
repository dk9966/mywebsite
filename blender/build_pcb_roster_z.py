"""
Detailed silhouette meshes for plans/pcb-z-roster.html items.

Lives in the **Circuit-elements** scene's ``PCB_Roster_Z`` collection. Every
mesh is built from axis-aligned boxes and faceted prisms (no arcs/circles), to
match the angular language used elsewhere in the project.

For high-scream parts (SOIC, QFP, heatsink, DIMM, CPU socket) we emit multiple
variants laid out in a "variants row" below the canonical 25-item grid so the
team can pick the silhouette that reads best per shot.

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/build_pcb_roster_z.py
"""
from __future__ import annotations

import math
import os
import bpy
import bmesh
from mathutils import Vector


# ---------------------------------------------------------------------------
# scene + bbox helpers
# ---------------------------------------------------------------------------

SCENE_NAME = "Circuit-elements"
COLL_NAME = "PCB_Roster_Z"


def get_target_scene() -> bpy.types.Scene:
    sc = bpy.data.scenes.get(SCENE_NAME)
    if sc is None:
        raise RuntimeError(f"Scene '{SCENE_NAME}' not found")
    return sc


def pcb_bbox_mm():
    pcb = bpy.data.collections.get("PCB")
    if not pcb:
        raise RuntimeError("Collection 'PCB' not found")

    lo = Vector((1e30,) * 3)
    hi = Vector((-1e30,) * 3)
    for ob in pcb.objects:
        if ob.type != "MESH" or not ob.data.vertices:
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            c = mw @ v.co
            lo.x = min(lo.x, c.x); lo.y = min(lo.y, c.y); lo.z = min(lo.z, c.z)
            hi.x = max(hi.x, c.x); hi.y = max(hi.y, c.y); hi.z = max(hi.z, c.z)
    return lo, hi


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


# ---------------------------------------------------------------------------
# bmesh primitives
# ---------------------------------------------------------------------------

def bm_add_box(bm, cx, cy, z0, sx, sy, sz):
    """Axis-aligned box; z0 = bottom Z, center X/Y."""
    bmesh.ops.create_cube(bm, size=1.0)
    vs = bm.verts[-8:]
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=vs)
    bmesh.ops.translate(bm, vec=(cx, cy, z0 + sz * 0.5), verts=vs)


def bm_add_hex_prism(bm, cx, cy, z0, r, h, sides: int):
    """Vertical n-gon prism; z0 = bottom (faceted, no arcs)."""
    ang_offset = math.pi / sides
    verts_low, verts_hi = [], []
    for i in range(sides):
        a = i * (2 * math.pi / sides) + ang_offset
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        verts_low.append(bm.verts.new((x, y, z0)))
        verts_hi.append(bm.verts.new((x, y, z0 + h)))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((verts_low[i], verts_low[j], verts_hi[j], verts_hi[i]))
    bm.faces.new(tuple(reversed(verts_low)))
    bm.faces.new(tuple(verts_hi))


def bm_pad(bm, cx, cy, sx, sy):
    """Thin solder-pad slab just above PCB plane (z=0..0.05)."""
    bm_add_box(bm, cx, cy, 0.0, sx, sy, 0.05)


def bm_pin1_dot(bm, cx, cy, z_top):
    """Tiny pin-1 indent on top of a chip body."""
    bm_add_box(bm, cx, cy, z_top - 0.06, 0.6, 0.6, 0.06)


# ---------------------------------------------------------------------------
# leg helpers (gull-wing as two boxes: foot on PCB + riser into body)
# ---------------------------------------------------------------------------

def bm_legs_y_pair(bm, n, body_w, body_h_top, side_y, leg_pitch=None, leg_w=0.4, foot_l=0.7, foot_h=0.25):
    """N legs sticking out in +Y or -Y direction (body_w along X)."""
    if leg_pitch is None:
        leg_pitch = body_w / max(n, 1)
    sign = 1.0 if side_y > 0 else -1.0
    foot_y_center = side_y + sign * foot_l * 0.5
    x0 = -(n - 1) * 0.5 * leg_pitch
    for i in range(n):
        x = x0 + i * leg_pitch
        bm_add_box(bm, x, foot_y_center, 0.0, leg_w, foot_l, foot_h)
        bm_add_box(bm, x, side_y + sign * 0.05, foot_h, leg_w, 0.1, body_h_top - foot_h)


def bm_legs_x_pair(bm, n, body_h, body_h_top, side_x, leg_pitch=None, leg_w=0.4, foot_l=0.7, foot_h=0.25):
    """N legs sticking out in +X or -X direction (body_h along Y)."""
    if leg_pitch is None:
        leg_pitch = body_h / max(n, 1)
    sign = 1.0 if side_x > 0 else -1.0
    foot_x_center = side_x + sign * foot_l * 0.5
    y0 = -(n - 1) * 0.5 * leg_pitch
    for i in range(n):
        y = y0 + i * leg_pitch
        bm_add_box(bm, foot_x_center, y, 0.0, foot_l, leg_w, foot_h)
        bm_add_box(bm, side_x + sign * 0.05, y, foot_h, 0.1, leg_w, body_h_top - foot_h)


def bm_legs_qfp(bm, n_per_side, body_w, body_h, body_h_top, leg_w=0.35, foot_l=0.9, foot_h=0.2):
    """Four-sided perimeter legs (QFP/LQFP)."""
    pitch = (body_w - 2 * leg_w) / max(n_per_side, 1)
    bm_legs_y_pair(bm, n_per_side, body_w - 2 * leg_w, body_h_top, body_h * 0.5,
                   leg_pitch=pitch, leg_w=leg_w, foot_l=foot_l, foot_h=foot_h)
    bm_legs_y_pair(bm, n_per_side, body_w - 2 * leg_w, body_h_top, -body_h * 0.5,
                   leg_pitch=pitch, leg_w=leg_w, foot_l=foot_l, foot_h=foot_h)
    pitch_y = (body_h - 2 * leg_w) / max(n_per_side, 1)
    bm_legs_x_pair(bm, n_per_side, body_h - 2 * leg_w, body_h_top, body_w * 0.5,
                   leg_pitch=pitch_y, leg_w=leg_w, foot_l=foot_l, foot_h=foot_h)
    bm_legs_x_pair(bm, n_per_side, body_h - 2 * leg_w, body_h_top, -body_w * 0.5,
                   leg_pitch=pitch_y, leg_w=leg_w, foot_l=foot_l, foot_h=foot_h)


# ---------------------------------------------------------------------------
# mesh / object plumbing
# ---------------------------------------------------------------------------

def mesh_from_bmesh(name: str, bm: bmesh.types.BMesh):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def put_object(name: str, bm: bmesh.types.BMesh, coll, loc: Vector):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = mesh_from_bmesh(name, bm)
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    ob.location = loc
    return ob


def grid_slot(i: int, cols: int, pitch_x: float, pitch_y: float, ox: float, oy: float) -> Vector:
    row = i // cols
    col = i % cols
    return Vector((ox + col * pitch_x, oy + row * pitch_y, 0.0))


# ---------------------------------------------------------------------------
# builders — canonical 25, with detail upgrades
# ---------------------------------------------------------------------------

def m_passives():
    """0201/0402/0603 cluster: tiny chips + visible solder pads under them."""
    bm = bmesh.new()
    for c in range(5):
        for r in range(3):
            cx = (c - 2) * 1.6
            cy = (r - 1) * 1.4
            bm_pad(bm, cx - 0.45, cy, 0.45, 0.55)
            bm_pad(bm, cx + 0.45, cy, 0.45, 0.55)
            bm_add_box(bm, cx, cy, 0.05, 1.0, 0.5, 0.35)
            bm_add_box(bm, cx, cy, 0.4, 0.4, 0.5, 0.04)  # body stripe
    return bm


def m_smd_led_sot():
    """SOT-23 (3-leg), SOD-123 diode, and an 0805 LED."""
    bm = bmesh.new()
    bm_add_box(bm, -2.0, 0.0, 0.0, 1.6, 1.3, 0.95)
    bm_add_box(bm, -2.7, 0.5, 0.0, 0.5, 0.4, 0.15)
    bm_add_box(bm, -2.7, -0.5, 0.0, 0.5, 0.4, 0.15)
    bm_add_box(bm, -1.3, 0.0, 0.0, 0.5, 0.4, 0.15)
    bm_add_box(bm, 0.5, 0.0, 0.0, 2.6, 1.5, 1.1)
    bm_add_box(bm, -0.4, 0.0, 1.1, 0.3, 1.5, 0.03)  # cathode stripe
    bm_add_box(bm, 3.0, 0.0, 0.0, 2.0, 1.25, 0.6)
    bm_add_box(bm, 2.4, 0.0, 0.6, 1.4, 0.9, 0.05)  # die window hint
    return bm


def m_qfn():
    """QFN body + pad halo + pin-1 dot + edge land castellations."""
    bm = bmesh.new()
    bm_pad(bm, 0.0, 0.0, 5.6, 5.6)  # pad halo under
    bm_add_box(bm, 0.0, 0.0, 0.05, 5.0, 5.0, 0.95)
    bm_add_box(bm, 0.0, 0.0, 1.0, 4.5, 4.5, 0.05)  # rim recess
    for i in range(6):
        d = -2.0 + i * 0.8
        bm_add_box(bm, d, 2.55, 0.0, 0.3, 0.4, 0.3)
        bm_add_box(bm, d, -2.55, 0.0, 0.3, 0.4, 0.3)
        bm_add_box(bm, 2.55, d, 0.0, 0.4, 0.3, 0.3)
        bm_add_box(bm, -2.55, d, 0.0, 0.4, 0.3, 0.3)
    bm_pin1_dot(bm, -1.9, 1.9, 1.0)
    return bm


def m_tssop_ssop():
    """TSSOP body + 16 fine-pitch gull-wing legs per side."""
    bm = bmesh.new()
    body_w, body_h, body_z = 8.0, 3.0, 1.05
    bm_add_box(bm, 0.0, 0.0, 0.1, body_w, body_h, body_z)
    bm_legs_y_pair(bm, 16, body_w - 0.4, body_z + 0.05, body_h * 0.5,
                   leg_w=0.22, foot_l=0.6, foot_h=0.18)
    bm_legs_y_pair(bm, 16, body_w - 0.4, body_z + 0.05, -body_h * 0.5,
                   leg_w=0.22, foot_l=0.6, foot_h=0.18)
    bm_pin1_dot(bm, -3.4, 1.05, body_z + 0.1)
    return bm


def m_soic_so8():
    """SO-8 narrow body, 4 gull-wing legs per side."""
    bm = bmesh.new()
    body_w, body_h, body_z = 5.0, 4.0, 1.55
    bm_add_box(bm, 0.0, 0.0, 0.15, body_w, body_h, body_z)
    bm_legs_y_pair(bm, 4, body_w - 0.4, body_z + 0.15, body_h * 0.5,
                   leg_w=0.45, foot_l=0.9, foot_h=0.25)
    bm_legs_y_pair(bm, 4, body_w - 0.4, body_z + 0.15, -body_h * 0.5,
                   leg_w=0.45, foot_l=0.9, foot_h=0.25)
    bm_add_box(bm, 0.0, 0.0, body_z + 0.05, body_w - 1.0, body_h - 1.0, 0.04)
    bm_pin1_dot(bm, -1.7, 1.4, body_z + 0.15)
    return bm


def m_soic_w16():
    """SOIC-W (300-mil wide), 8 gull-wing legs per side."""
    bm = bmesh.new()
    body_w, body_h, body_z = 10.5, 7.5, 1.85
    bm_add_box(bm, 0.0, 0.0, 0.2, body_w, body_h, body_z)
    bm_legs_y_pair(bm, 8, body_w - 0.6, body_z + 0.2, body_h * 0.5,
                   leg_w=0.45, foot_l=1.1, foot_h=0.3)
    bm_legs_y_pair(bm, 8, body_w - 0.6, body_z + 0.2, -body_h * 0.5,
                   leg_w=0.45, foot_l=1.1, foot_h=0.3)
    bm_add_box(bm, 0.0, 0.0, body_z + 0.1, body_w - 1.4, body_h - 1.4, 0.05)
    bm_pin1_dot(bm, -4.4, 3.0, body_z + 0.2)
    return bm


def _qfp_body(body_w, body_h, n_per_side, leg_w=0.35, foot_l=0.9):
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.2, body_w, body_w, body_h)
    bm_add_box(bm, 0.0, 0.0, 0.2 + body_h - 0.04, body_w - 1.2, body_w - 1.2, 0.04)
    bm_legs_qfp(bm, n_per_side, body_w, body_w, 0.2 + body_h, leg_w=leg_w, foot_l=foot_l)
    bm_pin1_dot(bm, -(body_w * 0.5 - 1.4), body_w * 0.5 - 1.4, 0.2 + body_h)
    return bm


def m_qfp_qfp32():
    return _qfp_body(7.0, 1.4, n_per_side=8, leg_w=0.4, foot_l=0.8)


def m_qfp_lqfp64():
    return _qfp_body(10.0, 1.6, n_per_side=16, leg_w=0.32, foot_l=0.85)


def m_qfp_lqfp144():
    return _qfp_body(20.0, 1.7, n_per_side=36, leg_w=0.28, foot_l=1.0)


def m_bga():
    """BGA cap + ball grid hint + heat slug notch on top."""
    bm = bmesh.new()
    bm_pad(bm, 0.0, 0.0, 13.0, 13.0)
    bm_add_box(bm, 0.0, 0.0, 0.05, 12.0, 12.0, 1.9)
    bm_add_box(bm, 0.0, 0.0, 1.95, 11.0, 11.0, 0.4)  # lid step
    bm_add_box(bm, 0.0, 0.0, 2.35, 6.0, 6.0, 0.08)   # heat slug
    for r in range(8):
        for c in range(8):
            x = -5.25 + c * 1.5
            y = -5.25 + r * 1.5
            bm_add_box(bm, x, y, 0.0, 0.45, 0.45, 0.18)  # ball hint
    bm_pin1_dot(bm, -5.0, 5.0, 1.95)
    return bm


def m_tantalum():
    """Molded chip tantalum brick: body + polarity stripe + 2 solder pads."""
    bm = bmesh.new()
    bm_pad(bm, -1.4, 0.0, 0.9, 2.4)
    bm_pad(bm, 1.4, 0.0, 0.9, 2.4)
    bm_add_box(bm, 0.0, 0.0, 0.05, 3.4, 2.2, 1.9)
    bm_add_box(bm, -1.2, 0.0, 1.93, 0.7, 1.6, 0.05)  # polarity bar
    bm_add_box(bm, 0.0, 0.0, 1.93, 1.5, 0.3, 0.04)
    bm_add_box(bm, 0.0, 0.0, 1.93, 0.3, 1.5, 0.04)
    return bm


def m_emi_can():
    """EMI shield: stepped lid + corner clip seams + finger tabs along base."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 16.0, 13.0, 3.2)
    bm_add_box(bm, 0.0, 0.0, 3.2, 14.5, 11.5, 1.9)
    bm_add_box(bm, 0.0, 0.0, 5.1, 6.0, 4.0, 0.18)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * 7.5, sy * 6.0, 0.0, 0.6, 0.6, 3.4)
    for i in range(7):
        x = -7.0 + i * (14.0 / 6.0)
        bm_add_box(bm, x, 6.6, 0.0, 0.7, 0.4, 1.0)
        bm_add_box(bm, x, -6.6, 0.0, 0.7, 0.4, 1.0)
    for j in range(5):
        y = -5.0 + j * (10.0 / 4.0)
        bm_add_box(bm, 8.1, y, 0.0, 0.4, 0.7, 1.0)
        bm_add_box(bm, -8.1, y, 0.0, 0.4, 0.7, 1.0)
    return bm


def m_m2_2280():
    """M.2 2280 slab + 4 NAND chips + controller + key notch + mount notch."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 42.0, 22.0, 1.0)
    for i, x in enumerate((-16.5, -8.5, -0.5, 7.5)):
        bm_add_box(bm, x, 4.0, 1.0, 7.0, 6.0, 0.85)
        bm_pin1_dot(bm, x - 2.8, 6.6, 1.85)
    bm_add_box(bm, 11.5, -3.5, 1.0, 8.0, 6.0, 1.05)  # controller
    bm_add_box(bm, 11.5, -3.5, 2.05, 6.0, 4.0, 0.05)
    bm_add_box(bm, -19.0, -8.5, 1.0, 3.0, 1.5, 0.45)  # M-key block
    bm_add_box(bm, -19.0, 7.5, 1.0, 1.5, 4.0, 0.45)
    bm_add_box(bm, 19.5, 0.0, 1.0, 2.0, 4.0, 0.35)
    for i in range(20):
        x = -20.5 + i * 0.9
        bm_pad(bm, x, -10.5, 0.4, 1.4)  # gold fingers
    return bm


def m_hc49_xtal():
    """HC-49 octagonal crystal can + two leg posts."""
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.4, 2.6, 6.0, 8)
    bm_add_box(bm, 0.0, 0.0, 0.0, 5.8, 0.6, 0.4)  # standoff strip
    bm_add_box(bm, -2.4, 0.0, 0.0, 0.5, 0.5, 0.4)
    bm_add_box(bm, 2.4, 0.0, 0.0, 0.5, 0.5, 0.4)
    bm_add_box(bm, 0.0, 0.0, 6.35, 4.6, 2.0, 0.05)  # stamped marking
    return bm


def m_dip():
    """DIP-16 body + pin forest + notch + brand stamp top."""
    bm = bmesh.new()
    body_w, body_h, body_z = 19.0, 7.0, 3.8
    bm_add_box(bm, 0.0, 0.0, 0.6, body_w, body_h, body_z)
    bm_add_box(bm, -body_w * 0.5 + 0.6, 0.0, 0.6 + body_z - 0.2, 0.6, 2.4, 0.2)  # notch carve
    for i in range(8):
        x = -7.6 + i * 2.18
        bm_add_box(bm, x, -3.0, -2.4, 0.55, 0.45, 3.0)  # downward pin
        bm_add_box(bm, x, 3.0, -2.4, 0.55, 0.45, 3.0)
        bm_add_box(bm, x, -3.6, 0.0, 0.55, 0.4, 0.6)   # shoulder
        bm_add_box(bm, x, 3.6, 0.0, 0.55, 0.4, 0.6)
    bm_add_box(bm, 0.0, 0.0, 0.6 + body_z, body_w - 2.0, body_h - 2.0, 0.05)
    return bm


def m_smd_elko():
    """V-chip aluminum SMD electrolytic: hex can + saddle + cross vent stamp."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 7.0, 7.0, 0.6)
    bm_add_hex_prism(bm, 0.0, 0.0, 0.6, 3.0, 8.0, 8)
    bm_add_box(bm, 0.0, 0.0, 8.55, 4.8, 0.45, 0.05)  # cross stamp
    bm_add_box(bm, 0.0, 0.0, 8.55, 0.45, 4.8, 0.05)
    bm_add_box(bm, -2.6, 0.0, 0.6, 0.5, 0.8, 0.05)  # polarity bar on saddle
    return bm


def m_inductor():
    """Shielded power inductor: outer block + bobbin coil rings + leads."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 10.5, 10.5, 6.0)
    bm_add_box(bm, 0.0, 0.0, 6.0, 8.5, 8.5, 1.8)
    for i in range(4):
        z = 1.0 + i * 1.2
        bm_add_hex_prism(bm, 0.0, 0.0, z, 3.8, 0.25, 12)  # bobbin coil ring
    bm_add_hex_prism(bm, 0.0, 0.0, 6.0, 2.5, 2.5, 12)  # central post
    bm_add_box(bm, 5.0, 0.0, 0.0, 1.2, 4.0, 0.4)  # solder tab
    bm_add_box(bm, -5.0, 0.0, 0.0, 1.2, 4.0, 0.4)
    return bm


def m_to220():
    """TO-220: plastic body + metal tab + mounting hole bump + 3 through-hole leads."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 10.0, 4.6, 9.0)   # plastic body
    bm_add_box(bm, 0.0, 0.0, 9.0, 9.5, 2.0, 4.0)    # metal tab (lower band)
    bm_add_box(bm, 0.0, 0.0, 13.0, 9.5, 2.0, 3.5)   # metal tab (upper band)
    bm_add_box(bm, 0.0, 0.0, 16.5, 2.5, 2.0, 1.0)   # mount-hole boss (filled, hole implied)
    for i in (-1, 0, 1):
        bm_add_box(bm, i * 2.5, 0.0, -3.0, 0.7, 0.6, 3.0)  # leads down
        bm_add_box(bm, i * 2.5, 0.0, 0.0, 0.7, 0.6, 0.6)   # leads emerging from body
    bm_add_box(bm, 0.0, -1.6, 4.5, 7.0, 0.05, 5.0)  # stamped marking on plastic front
    return bm


def m_coin_cell():
    """CR2032 coin in holder: octagon battery + holder rim + clip fingers."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 22.0, 22.0, 1.2)
    bm_add_hex_prism(bm, 0.0, 0.0, 1.2, 10.0, 3.0, 8)
    bm_add_hex_prism(bm, 0.0, 0.0, 4.2, 7.0, 0.1, 8)
    bm_add_box(bm, 11.0, 0.0, 1.2, 1.8, 6.0, 3.2)
    bm_add_box(bm, -11.0, 0.0, 1.2, 1.8, 6.0, 3.2)
    bm_add_box(bm, 11.0, 4.0, 1.2, 1.0, 1.6, 2.4)  # finger
    bm_add_box(bm, 11.0, -4.0, 1.2, 1.0, 1.6, 2.4)
    bm_add_box(bm, -11.0, 4.0, 1.2, 1.0, 1.6, 2.4)
    bm_add_box(bm, -11.0, -4.0, 1.2, 1.0, 1.6, 2.4)
    return bm


def m_radial_elko():
    """Radial through-hole aluminum electrolytic: tall can + vent cross + leads."""
    bm = bmesh.new()
    bm_add_hex_prism(bm, 0.0, 0.0, 0.0, 4.5, 17.0, 12)
    bm_add_hex_prism(bm, 0.0, 0.0, 17.0, 4.3, 0.4, 12)
    bm_add_box(bm, 0.0, 0.0, 17.4, 5.5, 0.45, 0.05)  # cross vent
    bm_add_box(bm, 0.0, 0.0, 17.4, 0.45, 5.5, 0.05)
    bm_add_box(bm, -3.6, 0.0, 0.05, 0.4, 0.5, 0.15)  # negative stripe pad
    bm_add_box(bm, -3.6, 0.0, 1.0, 0.4, 0.5, 15.0)
    bm_add_box(bm, 1.0, 0.0, -3.0, 0.45, 0.45, 3.0)  # leads
    bm_add_box(bm, -1.0, 0.0, -3.0, 0.45, 0.45, 3.0)
    return bm


def m_pin_header():
    """2x8 pin header: plastic base + square pins emerging through it."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 20.5, 5.5, 2.5)  # plastic base
    for r in range(2):
        for c in range(8):
            x = (c - 3.5) * 2.54
            y = (r - 0.5) * 2.54
            bm_add_box(bm, x, y, 2.5, 0.65, 0.65, 6.0)
            bm_add_box(bm, x, y, -2.5, 0.5, 0.5, 2.5)
    return bm


def m_cpu_socket_frame():
    """LGA socket frame: open square ring + lever block + retention tabs."""
    bm = bmesh.new()
    s = 42.0
    t = 2.8
    bm_add_box(bm, 0.0, s * 0.5 - t * 0.5, 0.0, s, t, 3.2)
    bm_add_box(bm, 0.0, -s * 0.5 + t * 0.5, 0.0, s, t, 3.2)
    bm_add_box(bm, s * 0.5 - t * 0.5, 0.0, 0.0, t, s - 2 * t, 3.2)
    bm_add_box(bm, -s * 0.5 + t * 0.5, 0.0, 0.0, t, s - 2 * t, 3.2)
    bm_add_box(bm, 0.0, 0.0, 3.2, 28.0, 28.0, 0.4)
    bm_add_box(bm, s * 0.5 + 2.4, 0.0, 0.0, 2.8, 16.0, 5.5)  # cam lever block
    bm_add_box(bm, s * 0.5 + 3.5, 8.0, 5.5, 0.6, 4.0, 1.8)
    bm_add_box(bm, -s * 0.5 - 2.4, 0.0, 0.0, 2.8, 16.0, 4.5)  # hinge
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * (s * 0.5 + 0.6), sy * (s * 0.5 + 0.6), 0.0, 3.0, 3.0, 1.2)
            bm_add_hex_prism(bm, sx * (s * 0.5 + 0.6), sy * (s * 0.5 + 0.6), 1.2, 0.9, 1.0, 6)
    return bm


def m_cpu_socket_with_die():
    """LGA socket frame + populated die + thermal grease window."""
    bm = m_cpu_socket_frame()
    bm_add_box(bm, 0.0, 0.0, 3.6, 22.0, 22.0, 1.0)   # IHS-style die lid
    bm_add_box(bm, 0.0, 0.0, 4.6, 14.0, 14.0, 0.05)  # marking window
    bm_add_box(bm, 0.0, 0.0, 4.6, 4.0, 0.4, 0.06)
    bm_add_box(bm, 0.0, 0.0, 4.6, 0.4, 4.0, 0.06)
    return bm


def m_rj45():
    """RJ45 jack: body + cable mouth recess + 2 LED windows + latch slot."""
    bm = bmesh.new()
    w, d, h = 16.5, 18.0, 13.0
    bm_add_box(bm, 0.0, 0.0, 0.0, w, d, h)
    bm_add_box(bm, 0.0, -d * 0.5 + 1.6, 1.2, w - 3.0, 3.2, h - 2.4)  # mouth
    bm_add_box(bm, 0.0, -d * 0.5 + 0.8, h * 0.5 + 2.0, 2.2, 1.0, 1.2)  # latch slot
    bm_add_box(bm, -5.0, -d * 0.5 + 0.5, h - 3.5, 2.5, 0.4, 1.8)   # LED window left
    bm_add_box(bm, 5.0, -d * 0.5 + 0.5, h - 3.5, 2.5, 0.4, 1.8)    # LED window right
    bm_add_box(bm, 0.0, d * 0.5 - 0.8, h * 0.5, w - 2.0, 0.5, h - 2.0)
    for sx in (-1, 1):
        bm_add_box(bm, sx * (w * 0.5 - 0.8), 0.0, h - 1.6, 1.0, d - 2.0, 0.5)
    for sx in (-1, 1):
        bm_add_box(bm, sx * (w * 0.5 - 0.5), -d * 0.5 + 0.5, -2.0, 0.6, 0.5, 2.0)
    return bm


def m_pcie_edge():
    """PCIe edge connector: card finger pattern + slot mouth + retention notch."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 32.0, 4.0, 1.6)  # slot body
    bm_add_box(bm, 0.0, 0.0, 1.6, 30.5, 2.6, 9.0)  # slot mouth
    bm_add_box(bm, -14.0, 0.0, 1.6, 1.0, 2.6, 11.0)  # end walls
    bm_add_box(bm, 14.0, 0.0, 1.6, 1.0, 2.6, 11.0)
    bm_add_box(bm, 15.0, 1.0, 1.6, 2.4, 1.2, 4.0)  # retention clip
    for i in range(22):
        x = -13.0 + i * (26.0 / 21.0)
        bm_add_box(bm, x, 0.0, 1.6, 0.7, 1.2, 8.4)  # gold finger inside slot
    bm_add_box(bm, 0.0, 0.0, 1.6, 1.8, 1.0, 8.0)  # PCIe key bump (small key notch suggestion)
    return bm


def m_usb_a_th():
    """Through-hole USB-A: U-shaped shell + back plate + internal contact tongue."""
    bm = bmesh.new()
    t = 0.9
    w, d, h = 13.5, 16.5, 7.0
    bm_add_box(bm, 0.0, d * 0.5 - t * 0.5, h * 0.5, w, t, h)
    bm_add_box(bm, 0.0, -d * 0.5 + t * 0.5, h * 0.5, w, t, h)
    bm_add_box(bm, w * 0.5 - t * 0.5, 0.0, h * 0.5, t, d - 2 * t, h)
    bm_add_box(bm, -w * 0.5 + t * 0.5, 0.0, h * 0.5, t, d - 2 * t, h)
    bm_add_box(bm, 0.0, 0.0, 0.3, w - 2 * t, d - 2 * t, 0.5)  # floor
    bm_add_box(bm, 0.0, 1.5, 1.8, w - 2.8, d - 4.0, 1.2)  # tongue
    for i in range(4):
        x = -3.6 + i * 2.4
        bm_add_box(bm, x, 1.5, 3.0, 1.4, d - 4.5, 0.12)  # contact strip
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * (w * 0.5 - 0.5), sy * (d * 0.5 + 0.5), -2.5, 1.0, 1.0, 2.8)  # shell tab
    for i in range(4):
        x = -3.6 + i * 2.4
        bm_add_box(bm, x, d * 0.5 - 0.5, -2.5, 0.6, 0.6, 2.8)  # signal leg
    return bm


def m_heatsink_chipset():
    """Stepped chipset heatsink: pyramidal slab with 4 mounting hole bosses."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 32.0, 32.0, 6.0)
    bm_add_box(bm, 0.0, 0.0, 6.0, 26.0, 26.0, 5.0)
    bm_add_box(bm, 0.0, 0.0, 11.0, 20.0, 20.0, 5.5)
    bm_add_box(bm, 0.0, 0.0, 16.5, 14.0, 14.0, 4.5)
    bm_add_box(bm, 0.0, 0.0, 21.0, 8.0, 8.0, 3.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * 14.0, sy * 14.0, 0.0, 4.0, 4.0, 4.5)  # mount boss
            bm_add_hex_prism(bm, sx * 14.0, sy * 14.0, 4.5, 1.0, 1.0, 6)  # screw cap
    return bm


def m_heatsink_fins():
    """VRM-style parallel-blade fin sink: many tall knife fins on a base."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 36.0, 28.0, 3.5)
    n = 12
    pitch = 32.0 / (n - 1)
    for i in range(n):
        x = -16.0 + i * pitch
        bm_add_box(bm, x, 0.0, 3.5, 1.0, 26.0, 18.0)
    bm_add_box(bm, 0.0, 14.5, 3.5, 36.0, 0.6, 18.0)  # spine top edge
    bm_add_box(bm, 0.0, -14.5, 3.5, 36.0, 0.6, 18.0)
    for sx in (-1, 1):
        bm_add_box(bm, sx * 16.5, 0.0, 0.0, 1.5, 4.0, 4.5)  # screw boss
    return bm


def m_heatsink_pinfin():
    """Pin-fin grid heatsink (low-profile chipset style)."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 30.0, 30.0, 2.5)
    n = 8
    pitch = 24.0 / (n - 1)
    for r in range(n):
        for c in range(n):
            x = -12.0 + c * pitch
            y = -12.0 + r * pitch
            h = 12.0 + ((r + c) % 3) * 1.2
            bm_add_box(bm, x, y, 2.5, 1.6, 1.6, h)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_add_box(bm, sx * 13.5, sy * 13.5, 0.0, 3.0, 3.0, 4.0)  # mount boss
    return bm


def m_dimm_bare():
    """DDR DIMM slab: tall, key notch at bottom, gold fingers + latch ears."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 34.0, 1.6, 30.0)  # PCB slab
    bm_add_box(bm, 2.0, 0.0, 0.0, 1.4, 1.6, 1.5)  # key notch (added as small block at notch position)
    for i in range(40):
        x = -16.0 + i * 0.78
        bm_add_box(bm, x, -0.9, 0.0, 0.55, 0.04, 2.4)  # fingers front
        bm_add_box(bm, x, 0.9, 0.0, 0.55, 0.04, 2.4)
    bm_add_box(bm, -16.5, 0.0, 27.5, 1.4, 2.4, 3.5)  # latch ears top
    bm_add_box(bm, 16.5, 0.0, 27.5, 1.4, 2.4, 3.5)
    return bm


def m_dimm_with_chips():
    """DDR DIMM with 8 surface-mount DRAM chips per side + heat spreader band."""
    bm = m_dimm_bare()
    for i in range(8):
        x = -14.0 + i * 4.0
        for sy in (-1, 1):
            bm_add_box(bm, x, sy * 1.05, 6.0, 3.4, 0.6, 1.0)  # DRAM chip body
            bm_pin1_dot(bm, x - 1.4, sy * 1.05 + 0.15, 7.0)
    bm_add_box(bm, 0.0, 0.95, 4.0, 30.0, 0.3, 18.0)  # heat spreader strip
    bm_add_box(bm, 0.0, -0.95, 4.0, 30.0, 0.3, 18.0)
    return bm


def m_cpu_cooler():
    """Tower cooler: copper base + 4 heatpipes + finned tower + octagonal fan + blades."""
    bm = bmesh.new()
    bm_add_box(bm, 0.0, 0.0, 0.0, 40.0, 40.0, 4.5)  # base plate
    bm_add_box(bm, 0.0, 0.0, 4.5, 30.0, 30.0, 3.0)  # copper block
    for i, x in enumerate((-9.0, -3.0, 3.0, 9.0)):
        bm_add_box(bm, x, 0.0, 7.5, 1.2, 30.0, 2.0)  # heatpipe horizontal segment
        bm_add_box(bm, x, 12.0, 7.5, 1.2, 1.2, 32.0)  # vertical riser back
        bm_add_box(bm, x, -12.0, 7.5, 1.2, 1.2, 32.0)
    n_fins = 22
    fin_pitch = 32.0 / (n_fins - 1)
    for i in range(n_fins):
        z = 10.0 + i * fin_pitch
        bm_add_box(bm, 0.0, 0.0, z, 28.0, 26.0, 0.5)  # thin fin plates
    bm_add_box(bm, 0.0, -16.0, 24.0, 30.0, 4.0, 30.0)  # fan housing slab
    bm_add_hex_prism(bm, 0.0, -16.0, 24.0, 14.0, 4.0, 8)  # fan ring
    bm_add_hex_prism(bm, 0.0, -16.0, 25.5, 4.0, 1.0, 12)  # fan hub
    for k in range(7):
        a = k * (2 * math.pi / 7)
        r = 9.0
        x = r * math.cos(a)
        z = 24.0 + r * math.sin(a)
        bm_add_box(bm, x, -16.0, z, 8.5, 0.25, 0.6)  # fan blade approx
    bm_add_box(bm, 0.0, 0.0, 44.0, 22.0, 22.0, 2.5)  # cap
    return bm


# ---------------------------------------------------------------------------
# layout + entry point
# ---------------------------------------------------------------------------

def build_all():
    scene = get_target_scene()
    bpy.context.window.scene = scene

    purge_collection(COLL_NAME)
    coll = coll_ensure(COLL_NAME, scene)

    lo, hi = pcb_bbox_mm()
    gap = 28.0
    pitch_x = 50.0
    pitch_y = 48.0
    cols = 7
    origin_x = hi.x + gap
    origin_y = lo.y + 12.0

    canonical = [
        ("roster_passives",       m_passives),
        ("roster_smd_led_sot",    m_smd_led_sot),
        ("roster_qfn",            m_qfn),
        ("roster_tssop_ssop",     m_tssop_ssop),
        ("roster_soic",           m_soic_so8),
        ("roster_qfp",            m_qfp_lqfp64),
        ("roster_bga",            m_bga),
        ("roster_tantalum",       m_tantalum),
        ("roster_emi_can",        m_emi_can),
        ("roster_m2_2280",        m_m2_2280),
        ("roster_hc49_xtal",      m_hc49_xtal),
        ("roster_dip",            m_dip),
        ("roster_smd_elko",       m_smd_elko),
        ("roster_inductor",       m_inductor),
        ("roster_to220",          m_to220),
        ("roster_coin_cell",      m_coin_cell),
        ("roster_radial_elko",    m_radial_elko),
        ("roster_pin_header",     m_pin_header),
        ("roster_cpu_socket",     m_cpu_socket_frame),
        ("roster_rj45",           m_rj45),
        ("roster_pcie_edge",      m_pcie_edge),
        ("roster_usb_a_th",       m_usb_a_th),
        ("roster_heatsink",       m_heatsink_chipset),
        ("roster_dimm",           m_dimm_bare),
        ("roster_cpu_cooler",     m_cpu_cooler),
    ]

    # Hero variants drop into row 4 of the grid (slots 25..31).
    variants = [
        ("roster_soic_w16",            m_soic_w16),
        ("roster_qfp_qfp32",           m_qfp_qfp32),
        ("roster_qfp_lqfp144",         m_qfp_lqfp144),
        ("roster_heatsink_fins",       m_heatsink_fins),
        ("roster_heatsink_pinfin",     m_heatsink_pinfin),
        ("roster_dimm_with_chips",     m_dimm_with_chips),
        ("roster_cpu_socket_with_die", m_cpu_socket_with_die),
    ]

    labels = canonical + variants

    for i, (name, builder) in enumerate(labels):
        bm = builder()
        slot = grid_slot(i, cols, pitch_x, pitch_y, origin_x, origin_y)
        put_object(name, bm, coll, slot)

    bpy.context.view_layer.update()
    return len(labels), len(canonical), len(variants), origin_x, hi.x, lo, hi


if __name__ == "__main__":
    total, n_main, n_var, ox, px, lo, hi = build_all()
    print(
        f"[pcb_roster_z] built {total} meshes "
        f"({n_main} canonical + {n_var} variants) "
        f"in '{COLL_NAME}'; grid starts x>{ox:.1f} "
        f"(pcb max x was {px:.1f}); pcb y range {lo.y:.1f}..{hi.y:.1f}"
    )

    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
