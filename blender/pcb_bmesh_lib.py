"""
Shared bmesh primitives for PCB-style procedural meshes.

No bpy scene side effects — safe to import from layout/roster builders.
"""
from __future__ import annotations

import math
import bpy
import bmesh
from mathutils import Vector


def bm_add_box(bm, cx, cy, z0, sx, sy, sz):
    """Axis-aligned box; z0 = bottom Z, center X/Y."""
    bmesh.ops.create_cube(bm, size=1.0)
    vs = bm.verts[-8:]
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=vs)
    bmesh.ops.translate(bm, vec=(cx, cy, z0 + sz * 0.5), verts=vs)


def bm_add_hex_prism(bm, cx, cy, z0, r, h, sides: int):
    """Vertical n-gon prism; z0 = bottom."""
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
    bm_add_box(bm, cx, cy, 0.0, sx, sy, 0.05)


def bm_pin1_dot(bm, cx, cy, z_top):
    bm_add_box(bm, cx, cy, z_top - 0.06, 0.6, 0.6, 0.06)


def bm_legs_y_pair(bm, n, body_w, body_h_top, side_y, leg_pitch=None, leg_w=0.4, foot_l=0.7, foot_h=0.25):
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


def mesh_from_bmesh(name: str, bm: bmesh.types.BMesh):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def put_object(name: str, bm: bmesh.types.BMesh, coll, loc: Vector, rot_z: float = 0.0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = mesh_from_bmesh(name, bm)
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    ob.location = loc
    ob.rotation_euler.z = math.radians(rot_z)
    return ob


def grid_slot(i: int, cols: int, pitch_x: float, pitch_y: float, ox: float, oy: float) -> Vector:
    row = i // cols
    col = i % cols
    return Vector((ox + col * pitch_x, oy + row * pitch_y, 0.0))
