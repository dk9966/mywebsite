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
        bm.faces.new((outer_top[i], outer_top[i + 1], inner_top[i + 1], inner_top[i]))
        bm.faces.new((inner_bot[i], inner_bot[i + 1], outer_bot[i + 1], outer_bot[i]))
        bm.faces.new((outer_bot[i], outer_bot[i + 1], outer_top[i + 1], outer_top[i]))
        bm.faces.new((inner_top[i], inner_top[i + 1], inner_bot[i + 1], inner_bot[i]))

    bm.faces.new((outer_bot[0], inner_bot[0], inner_top[0], outer_top[0]))
    bm.faces.new((outer_top[-1], inner_top[-1], inner_bot[-1], outer_bot[-1]))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def box(name, cx, cy, cz, sx, sy, sz):
    """Axis-aligned box centered at (cx,cy,cz) with full sizes (sx,sy,sz)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    hx, hy, hz = sx / 2, sy / 2, sz / 2
    coords = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
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
    bpy.context.collection.objects.link(obj)
    return obj


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


def build():
    clear_meshes()

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


if __name__ == "__main__":
    build()
