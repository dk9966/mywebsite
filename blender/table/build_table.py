import bpy
import bmesh
import math


# ---------- Scene helpers ----------

def clear_meshes():
    for obj in list(bpy.data.objects):
        if obj.type == "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


# ---------- Mesh primitives ----------

def annular_sector_solid(
    name, inner_radius, outer_radius, start_angle, end_angle,
    z_bottom, z_top, segments=128,
):
    """A thick annular sector — a flat curved bar with an inner hole."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    angles = [
        start_angle + (end_angle - start_angle) * i / segments
        for i in range(segments + 1)
    ]

    def ring(radius, z):
        return [
            bm.verts.new((radius * math.cos(a), radius * math.sin(a), z))
            for a in angles
        ]

    outer_top = ring(outer_radius, z_top)
    outer_bot = ring(outer_radius, z_bottom)
    inner_top = ring(inner_radius, z_top)
    inner_bot = ring(inner_radius, z_bottom)

    for i in range(segments):
        bm.faces.new((outer_top[i], outer_top[i + 1],
                     inner_top[i + 1], inner_top[i]))
        bm.faces.new((inner_bot[i], inner_bot[i + 1],
                     outer_bot[i + 1], outer_bot[i]))
        bm.faces.new((outer_bot[i], outer_bot[i + 1],
                     outer_top[i + 1], outer_top[i]))
        bm.faces.new((inner_top[i], inner_top[i + 1],
                     inner_bot[i + 1], inner_bot[i]))

    bm.faces.new((outer_top[0], inner_top[0], inner_bot[0], outer_bot[0]))
    bm.faces.new((outer_bot[-1], inner_bot[-1], inner_top[-1], outer_top[-1]))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def box(name, cx, cy, cz, sx, sy, sz):
    """
    Axis-aligned box centered at (cx,cy,cz) with full sizes (sx,sy,sz).
    Mesh verts stay in local space at the origin so rotations apply around
    the object's center (location), not the global origin.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    hx, hy, hz = sx / 2, sy / 2, sz / 2
    coords = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    v = [bm.verts.new(c) for c in coords]
    faces = [
        (v[0], v[1], v[2], v[3]),
        (v[7], v[6], v[5], v[4]),
        (v[0], v[4], v[5], v[1]),
        (v[1], v[5], v[6], v[2]),
        (v[2], v[6], v[7], v[3]),
        (v[3], v[7], v[4], v[0]),
    ]
    for f in faces:
        bm.faces.new(f)

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    bpy.context.collection.objects.link(obj)
    return obj


def annulus_solid(
    name,
    inner_radius,
    outer_radius,
    z_bottom,
    z_top,
    segments=96,
    cx=0.0,
    cy=0.0,
):
    """Full 360° annular slab (washer-shaped ring)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    angles = [2 * math.pi * i / segments for i in range(segments)]

    def ring(radius, z):
        return [
            bm.verts.new(
                (cx + radius * math.cos(a), cy + radius * math.sin(a), z)
            )
            for a in angles
        ]

    outer_top = ring(outer_radius, z_top)
    outer_bot = ring(outer_radius, z_bottom)
    inner_top = ring(inner_radius, z_top)
    inner_bot = ring(inner_radius, z_bottom)

    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((outer_top[i], outer_top[j], inner_top[j], inner_top[i]))
        bm.faces.new((inner_bot[i], inner_bot[j], outer_bot[j], outer_bot[i]))
        bm.faces.new((outer_bot[i], outer_bot[j], outer_top[j], outer_top[i]))
        bm.faces.new((inner_top[i], inner_top[j], inner_bot[j], inner_bot[i]))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def cylinder_disc(name, cx, cy, z_bottom, z_top, radius, segments=96):
    """Right circular cylinder (solid disc / pedestal)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    z0, z1 = min(z_bottom, z_top), max(z_bottom, z_top)

    angles = [2 * math.pi * i / segments for i in range(segments)]
    bottom = [
        bm.verts.new((cx + radius * math.cos(a), cy + radius * math.sin(a), z0))
        for a in angles
    ]
    top = [
        bm.verts.new((cx + radius * math.cos(a), cy + radius * math.sin(a), z1))
        for a in angles
    ]

    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))

    bm.faces.new(tuple(bottom[i] for i in range(segments)))
    bm.faces.new(tuple(reversed([top[i] for i in range(segments)])))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def hex_leg_wedge(
    name,
    cx,
    cy,
    r_disk,
    r_knee,
    r_out,
    width,
    z_top,
    angle_rad,
):
    """
    One leg: flat on top from the disk rim to r_knee, then ramps down to the
    floor at r_out. Local +X is outward along this leg; wedge extruded in Y.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    h = z_top
    w = width
    ca, sa = math.cos(angle_rad), math.sin(angle_rad)

    def wv(lx, ly, lz):
        wx = cx + ca * lx - sa * ly
        wy = cy + sa * lx + ca * ly
        return bm.verts.new((wx, wy, lz))

    # Inner vertical wall at x=r_disk; outer corners at x=r_out, z=0.
    v0 = wv(r_disk, -w / 2, h)
    v1 = wv(r_knee, -w / 2, h)
    v2 = wv(r_out, -w / 2, 0.0)
    v3 = wv(r_disk, -w / 2, 0.0)
    v4 = wv(r_disk, w / 2, h)
    v5 = wv(r_knee, w / 2, h)
    v6 = wv(r_out, w / 2, 0.0)
    v7 = wv(r_disk, w / 2, 0.0)

    bm.faces.new((v0, v1, v5, v4))
    bm.faces.new((v3, v7, v6, v2))
    bm.faces.new((v0, v3, v2, v1))
    bm.faces.new((v4, v5, v6, v7))
    bm.faces.new((v0, v4, v7, v3))
    bm.faces.new((v1, v2, v6, v5))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def hex_leg_ridges(
    name_prefix,
    cx,
    cy,
    r_knee,
    r_out,
    width,
    z_top,
    angle_rad,
    ridge_count,
):
    """Thin horizontal shelves on the outer ramp (rudimentary steps)."""
    objs = []
    ca, sa = math.cos(angle_rad), math.sin(angle_rad)
    ramp_len = r_out - r_knee
    thin = max(z_top * 0.022, 0.009)
    dr = ramp_len / max(ridge_count + 1, 2) * 0.48
    for i in range(ridge_count):
        t = (i + 1) / (ridge_count + 1)
        x_mid = r_knee + ramp_len * t
        z_surf = z_top * (r_out - x_mid) / ramp_len
        wx = cx + ca * x_mid
        wy = cy + sa * x_mid
        cz = z_surf + thin * 0.62
        leg = box(
            f"{name_prefix}_{i + 1}",
            wx,
            wy,
            cz,
            2 * dr,
            width * 0.9,
            thin,
        )
        leg.rotation_euler[2] = angle_rad
        objs.append(leg)
    return objs


def join_mesh_objects(name, objects):
    """Merge meshes into one object (caller ensures shared layer/collection)."""
    if not objects:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    return joined


# ---------- Parameters ----------

# Top slab (flat semicircular annulus)
INNER_R = 0.95
OUTER_R = 1.65
SLAB_THICKNESS = 0.04
TOP_HEIGHT = 1.05                       # top surface Z
SLAB_Z_BOTTOM = TOP_HEIGHT - SLAB_THICKNESS

# Skirt: a smaller annular sector hanging below the slab.
# Same shape, inset on every edge (outer/inner/tips) by SKIRT_INSET.
SKIRT_INSET = 0.08
SKIRT_HEIGHT = 0.10                     # how far the skirt drops below the slab
SKIRT_Z_TOP = SLAB_Z_BOTTOM
SKIRT_Z_BOTTOM = SKIRT_Z_TOP - SKIRT_HEIGHT

# Four legs descend straight down from the underside of the skirt on the
# median radius. They're pushed inward along the arc so none of them hug
# the semicircle's end tips — the outer pair sits well inside the skirt's
# tip cuts, the inner pair sits symmetrically on either side of the apex.
LEG_SIDE = 0.06
LEG_RADIUS = 0.5 * (INNER_R + OUTER_R)
LEG_COUNT = 4
# Evenly spaced across the arc at positions (2k-1)/(2N) * π, i.e. the same
# pattern as midpoints of N equal sectors. For N=4 that's π/8, 3π/8, 5π/8,
# 7π/8 — 22.5°, 67.5°, 112.5°, 157.5°. Clean symmetric rhythm with the
# outer legs pulled a full 22.5° in from the tips.
LEG_ANGLES = [
    (2 * k + 1) * math.pi / (2 * LEG_COUNT) for k in range(LEG_COUNT)
]

# Foot brace: curved bar at the leg arc — same radial band width as a leg;
# vertical thickness matches the top slab (same Z extrusion as the table).
BRACE_THICKNESS = SLAB_THICKNESS
BRACE_INNER_R = LEG_RADIUS - LEG_SIDE / 2
BRACE_OUTER_R = LEG_RADIUS + LEG_SIDE / 2
BRACE_START_ANGLE = 0.0
BRACE_END_ANGLE = math.pi

LEG_TOP_Z = SKIRT_Z_BOTTOM
LEG_BOTTOM_Z = BRACE_THICKNESS

# Suit platform (hex base; centered at (SP_X, SP_Y) on the floor).
# Table parts stay at the origin; main.blend layout offsets the platform on -Y.
# Older +Y layouts used SP_Y ≈ 2.42; current scene matches SuitPlatform empty ~ -4.77.
SP_X = 0.0
SP_Y = -4.76619
SP_DISK_R = 0.42
SP_DISK_H = 0.048
SP_PED_R = 0.11
SP_PED_H = 0.052
SP_RING_R0 = SP_PED_R - 0.016
SP_RING_R1 = SP_PED_R + 0.008
SP_RING_Z0 = SP_DISK_H + 0.001
SP_RING_Z1 = SP_DISK_H + 0.012
SP_TOOTH_R = SP_PED_R + 0.068
SP_TOOTH_COUNT = 20
SP_TOOTH_W = 0.036
SP_TOOTH_D = 0.018
SP_TOOTH_H = 0.014
SP_R_KNEE = 0.49
SP_R_OUT = 0.66
SP_LEG_W = 0.13
SP_LEG_RIDGES = 4


def build_suit_platform():
    """Hex-symmetric pedestal + six ramp legs; centered at (SP_X, SP_Y)."""
    cx, cy = SP_X, SP_Y
    parts = []

    parts.append(
        cylinder_disc("SP_MainDisk", cx, cy, 0.0, SP_DISK_H, SP_DISK_R)
    )
    parts.append(
        cylinder_disc(
            "SP_Pedestal",
            cx,
            cy,
            SP_DISK_H,
            SP_DISK_H + SP_PED_H,
            SP_PED_R,
        )
    )
    parts.append(
        annulus_solid(
            "SP_Ring",
            SP_RING_R0,
            SP_RING_R1,
            SP_RING_Z0,
            SP_RING_Z1,
            segments=72,
            cx=cx,
            cy=cy,
        )
    )

    for i in range(SP_TOOTH_COUNT):
        a = 2 * math.pi * i / SP_TOOTH_COUNT
        tx = cx + math.cos(a) * SP_TOOTH_R
        ty = cy + math.sin(a) * SP_TOOTH_R
        tz = SP_DISK_H + SP_TOOTH_H / 2
        tooth = box(f"SP_Tooth_{i + 1}", tx, ty, tz, SP_TOOTH_W, SP_TOOTH_D, SP_TOOTH_H)
        tooth.rotation_euler[2] = a
        parts.append(tooth)

    for k in range(6):
        ang = -math.pi / 2 + k * math.pi / 3
        parts.append(
            hex_leg_wedge(
                f"SP_Leg_{k + 1}",
                cx,
                cy,
                SP_DISK_R,
                SP_R_KNEE,
                SP_R_OUT,
                SP_LEG_W,
                SP_DISK_H,
                ang,
            )
        )
        parts.extend(
            hex_leg_ridges(
                f"SP_LegRidge_{k + 1}",
                cx,
                cy,
                SP_R_KNEE,
                SP_R_OUT,
                SP_LEG_W,
                SP_DISK_H,
                ang,
                SP_LEG_RIDGES,
            )
        )

    join_mesh_objects("SuitPlatform", parts)


# ---------- Suit display cases (matched to main.blend suit row + facing) ----------

# Case bases lie on a circle around (SD_ARC_PIVOT_X, SD_ARC_PIVOT_Y) (fitted from the
# five objects in the current scene). Trapezoidal +X faces the suit platform at (SP_X, SP_Y).
# SD_ARC_CENTER = 3π/2 is the middle of the row on the -Y side of the pivot.
SD_COUNT = 5
SD_ARC_PIVOT_X = 0.0
SD_ARC_PIVOT_Y = -9.06825
SD_ARC_CENTER = 1.5 * math.pi
SD_ARC_RADIUS = 2.52
SD_MIN_CLEARANCE = 0.18
SD_ARC_HALF_SPAN_MIN = 0.74
SD_CASE_DEPTH = 0.48
SD_CASE_HEIGHT = 2.2
SD_BOTTOM_WIDTH = 0.88
SD_TOP_WIDTH = 0.65
SD_BEVEL_WIDTH = 0.04
SD_BEVEL_SEGMENTS = 3


def trapezoidal_display_case_mesh(name):
    """
    Vertical frustum prism: bottom wider than top, constant depth.
    Local: origin at floor footprint center; +X is the trapezoidal display face
    (emissive panel); Z up. Width varies in Y vs height (trapezoid in YZ as seen
    from +X toward the platform center).
    """
    d = SD_CASE_DEPTH
    h = SD_CASE_HEIGHT
    wb = SD_BOTTOM_WIDTH
    wt = SD_TOP_WIDTH
    hx = d / 2

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    def verts_at_x(x0):
        return [
            bm.verts.new((x0, -wb / 2, 0)),
            bm.verts.new((x0, wb / 2, 0)),
            bm.verts.new((x0, -wt / 2, h)),
            bm.verts.new((x0, wt / 2, h)),
        ]

    vb = verts_at_x(-hx)
    vf = verts_at_x(hx)

    faces = [
        (vb[0], vb[1], vf[1], vf[0]),  # bottom
        (vb[2], vf[2], vf[3], vb[3]),  # top
        (vb[0], vf[0], vf[2], vb[2]),  # -Y side
        (vb[1], vb[3], vf[3], vf[1]),  # +Y side
        (vb[0], vb[2], vb[3], vb[1]),  # back (-X)
        (vf[0], vf[1], vf[3], vf[2]),  # front (+X)
    ]
    for f in faces:
        bm.faces.new(f)

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _ensure_suit_display_materials():
    """Dark frame + cool emissive panel (shared across cases)."""
    mat_frame = bpy.data.materials.get("SuitCase_Frame")
    if mat_frame is None:
        mat_frame = bpy.data.materials.new("SuitCase_Frame")
        mat_frame.use_nodes = True
        nt = mat_frame.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.045, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.55
        bsdf.inputs["Specular IOR Level"].default_value = 0.35
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mat_panel = bpy.data.materials.get("SuitCase_Panel")
    if mat_panel is None:
        mat_panel = bpy.data.materials.new("SuitCase_Panel")
        mat_panel.use_nodes = True
        nt = mat_panel.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        mix = nt.nodes.new("ShaderNodeMixShader")
        glass = nt.nodes.new("ShaderNodeBsdfPrincipled")
        glass.inputs["Transmission Weight"].default_value = 0.92
        glass.inputs["Roughness"].default_value = 0.08
        glass.inputs["IOR"].default_value = 1.45
        glass.inputs["Base Color"].default_value = (0.75, 0.88, 1.0, 1.0)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (0.55, 0.78, 1.0, 1.0)
        em.inputs["Strength"].default_value = 3.5
        nt.links.new(glass.outputs["BSDF"], mix.inputs[1])
        nt.links.new(em.outputs["Emission"], mix.inputs[2])
        mix.inputs["Fac"].default_value = 0.35
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    return mat_frame, mat_panel


def _assign_case_face_materials(obj, mat_frame, mat_panel):
    """Front (+X) gets panel; other faces frame."""
    if not obj.data.materials:
        obj.data.materials.append(mat_frame)
        obj.data.materials.append(mat_panel)
    for poly in obj.data.polygons:
        poly.material_index = 1 if abs(poly.normal.x) > 0.85 else 0
    obj.data.update()


def build_suit_display_cases():
    """
    Five trapezoidal cases on an arc around (SD_ARC_PIVOT_X, SD_ARC_PIVOT_Y), middle on
    the -Y ray (SD_ARC_CENTER = 3π/2). Each front (+X) faces the suit platform at
    (SP_X, SP_Y). Spacing from bottom width + SD_MIN_CLEARANCE at SD_ARC_RADIUS.
    Removes any prior SuitCase_* / SuitDisplays.
    """
    mat_frame, mat_panel = _ensure_suit_display_materials()

    for name in list(bpy.data.objects.keys()):
        if name.startswith("SuitCase_") or name == "SuitDisplays":
            o = bpy.data.objects[name]
            bpy.data.objects.remove(o, do_unlink=True)

    fx, fy = SP_X, SP_Y
    pvx, pvy = SD_ARC_PIVOT_X, SD_ARC_PIVOT_Y
    n = SD_COUNT
    if n < 1:
        return

    angles = []
    if n == 1:
        angles = [SD_ARC_CENTER]
    else:
        step = (SD_BOTTOM_WIDTH + SD_MIN_CLEARANCE) / SD_ARC_RADIUS
        half_span = 0.5 * (n - 1) * step
        half_span = max(half_span, SD_ARC_HALF_SPAN_MIN)
        lo = SD_ARC_CENTER - half_span
        hi = SD_ARC_CENTER + half_span
        angles = [lo + (hi - lo) * i / (n - 1) for i in range(n)]

    parent = bpy.data.objects.new("SuitDisplays", None)
    parent.empty_display_type = "PLAIN_AXES"
    parent.empty_display_size = 0.08
    bpy.context.collection.objects.link(parent)

    for i, a in enumerate(angles, start=1):
        mesh = trapezoidal_display_case_mesh(f"SuitCase_{i}_mesh")
        obj = bpy.data.objects.new(f"SuitCase_{i}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = parent

        px = pvx + SD_ARC_RADIUS * math.cos(a)
        py = pvy + SD_ARC_RADIUS * math.sin(a)
        obj.location = (px, py, 0.0)
        # Trapezoidal face (+X) aims at the suit platform center (circular disk).
        dx, dy = fx - px, fy - py
        obj.rotation_euler[2] = math.atan2(dy, dx)

        _assign_case_face_materials(obj, mat_frame, mat_panel)

        bev = obj.modifiers.new(name="Bevel", type="BEVEL")
        bev.affect = "EDGES"
        bev.limit_method = "ANGLE"
        bev.angle_limit = math.radians(50)
        bev.width = SD_BEVEL_WIDTH
        bev.segments = SD_BEVEL_SEGMENTS


DESK_MESH_NAMES = frozenset({"Top", "Skirt", "FootBrace"})


def clear_desk_meshes():
    """Remove only the desk GLB export set, not the rest of main.blend."""
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        if obj.name in DESK_MESH_NAMES or obj.name.startswith("Leg_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def build_desk():
    """Rebuild Top / Skirt / Leg_* / FootBrace for table.glb export."""
    clear_desk_meshes()

    start_angle = 0.0
    end_angle = math.pi

    # 1) Flat top slab.
    annular_sector_solid(
        name="Top",
        inner_radius=INNER_R,
        outer_radius=OUTER_R,
        start_angle=start_angle,
        end_angle=end_angle,
        z_bottom=SLAB_Z_BOTTOM,
        z_top=TOP_HEIGHT,
        segments=128,
    )

    # 2) Skirt hanging below the slab — same shape, inset on every edge.
    # Radial inset shrinks the radii; angular inset (using arc length at the
    # mid-radius) trims the sweep so the tip edges are also offset uniformly.
    avg_r = 0.5 * (INNER_R + OUTER_R)
    angular_inset = SKIRT_INSET / avg_r
    annular_sector_solid(
        name="Skirt",
        inner_radius=INNER_R + SKIRT_INSET,
        outer_radius=OUTER_R - SKIRT_INSET,
        start_angle=start_angle + angular_inset,
        end_angle=end_angle - angular_inset,
        z_bottom=SKIRT_Z_BOTTOM,
        z_top=SKIRT_Z_TOP,
        segments=128,
    )

    # 3) Legs from skirt to foot brace — each rotated around Z so local +Y
    # points toward the semicircle center (origin), i.e. radially inward.
    for i, a in enumerate(LEG_ANGLES, start=1):
        cx = LEG_RADIUS * math.cos(a)
        cy = LEG_RADIUS * math.sin(a)
        cz = (LEG_TOP_Z + LEG_BOTTOM_Z) / 2
        height = LEG_TOP_Z - LEG_BOTTOM_Z
        leg_obj = box(f"Leg_{i}", cx, cy, cz, LEG_SIDE, LEG_SIDE, height)
        leg_obj.rotation_euler[2] = a + math.pi / 2

    # 4) Thin curved foot brace at the leg arc, spanning the full semicircle.
    annular_sector_solid(
        name="FootBrace",
        inner_radius=BRACE_INNER_R,
        outer_radius=BRACE_OUTER_R,
        start_angle=BRACE_START_ANGLE,
        end_angle=BRACE_END_ANGLE,
        z_bottom=0.0,
        z_top=BRACE_THICKNESS,
        segments=128,
    )


def build():
    clear_meshes()
    build_desk()
    build_suit_platform()
    build_suit_display_cases()


if __name__ == "__main__":
    build()
    import os

    _blend_out = os.environ.get("BLEND_OUT")
    if _blend_out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(_blend_out))
