"""Author Tron-line polylines on the desk and export the table to public/models/table.glb.

Contract is documented in plans/tron-lines-on-table.md.

Lines are edge-only meshes named TronLine_<order>_<delaySec>, placed in a top-level
'TronLines' collection of Main Scene. They are hand-routed against build_table.py's
geometry constants so they hug the desk's actual edges.

Idempotent: re-running clears any prior TronLine_* objects and regenerates them.
Run with SAVE_BLEND_AFTER=1 to persist into main.blend per project convention.
"""

import math
import os
import struct
import json

import bmesh
import bpy


# Geometry constants mirrored from build_table.py — keep in sync if that file changes.
INNER_R = 0.95
OUTER_R = 1.65
TOP_HEIGHT = 1.05
SLAB_Z_BOTTOM = 1.01
SKIRT_INSET = 0.08
SKIRT_Z_TOP = SLAB_Z_BOTTOM
SKIRT_Z_BOTTOM = 0.91
BRACE_THICKNESS = 0.04
BRACE_INNER_R = 1.27
BRACE_OUTER_R = 1.33
LEG_RADIUS = 0.5 * (INNER_R + OUTER_R)
LEG_BOTTOM_Z = BRACE_THICKNESS
LEG_TOP_Z = SKIRT_Z_BOTTOM
LEG_ANGLES = [(2 * k + 1) * math.pi / 8 for k in range(4)]

# Skirt is inset from the top slab on every edge; angular inset uses arc length
# at the mid-radius. These mirror build_table.py's annular_sector_solid args.
SKIRT_OUTER_R = OUTER_R - SKIRT_INSET
SKIRT_INNER_R = INNER_R + SKIRT_INSET
SKIRT_ANGULAR_INSET = SKIRT_INSET / (0.5 * (INNER_R + OUTER_R))

TARGET_SCENE = "Main Scene"
TRON_COLL_NAME = "TronLines"
OUTPUT_RELATIVE = "../public/models/table.glb"

# A tiny lift keeps the line off the surface so neither Blender's viewport nor a
# WebGL renderer can z-fight against the slab/brace it traces.
SURFACE_LIFT = 0.005


def get_or_create_top_level_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    for child in scene.collection.children:
        if child.name == name:
            return child
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


def remove_existing_tron_lines() -> None:
    stale_objs = [obj for obj in bpy.data.objects if obj.name.startswith("TronLine_")]
    for obj in stale_objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    stale_meshes = [m for m in bpy.data.meshes if m.name.startswith("TronLine_") and m.users == 0]
    for m in stale_meshes:
        bpy.data.meshes.remove(m)


def make_polyline(name: str, points, collection: bpy.types.Collection) -> bpy.types.Object:
    """Edge-only mesh through the given (x,y,z) points; no faces."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in points]
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i + 1]))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def build_arc(
    radius: float,
    z: float,
    angle_start: float,
    angle_end: float,
    segments: int = 48,
) -> list[tuple[float, float, float]]:
    """Polyline along a circular arc at constant z; sweeps angle_start → angle_end."""
    out = []
    for t in range(segments + 1):
        a = angle_start + (angle_end - angle_start) * t / segments
        out.append((radius * math.cos(a), radius * math.sin(a), z + SURFACE_LIFT))
    return out


def build_radial_segment(
    inner_r: float,
    outer_r: float,
    angle: float,
    z: float,
) -> list[tuple[float, float, float]]:
    """Single straight segment from inner radius to outer radius at the given angle."""
    cx, cy = math.cos(angle), math.sin(angle)
    return [
        (inner_r * cx, inner_r * cy, z + SURFACE_LIFT),
        (outer_r * cx, outer_r * cy, z + SURFACE_LIFT),
    ]


def build_chord_cap_closer(
    inner_r: float,
    outer_r: float,
    angle: float,
    z_drawn: float,
    z_far: float,
) -> list[tuple[float, float, float]]:
    """Three-edge polyline that closes a chord cap whose horizontal at z_drawn
    is already authored as a separate line.

    Draws outer-vertical -> far horizontal -> inner-vertical, so the four
    corners of the cap quad are connected. SURFACE_LIFT pushes the horizontals
    onto the same side as their drawn counterpart; verticals are lifted away
    from the bounding mesh face along the chord-outward direction.
    """
    cx, cy = math.cos(angle), math.sin(angle)
    return [
        (outer_r * cx, outer_r * cy, z_drawn + SURFACE_LIFT),
        (outer_r * cx, outer_r * cy, z_far + SURFACE_LIFT),
        (inner_r * cx, inner_r * cy, z_far + SURFACE_LIFT),
        (inner_r * cx, inner_r * cy, z_drawn + SURFACE_LIFT),
    ]


# Leg local corner offsets in XY. Matches build_table.py's box() which centers
# the mesh and gives it half-extents LEG_SIDE/2 along local X and Y.
_LEG_HX = 0.5 * 0.06  # matches LEG_SIDE/2 in build_table.py
LEG_LOCAL_CORNERS = [
    (_LEG_HX, _LEG_HX),
    (_LEG_HX, -_LEG_HX),
    (-_LEG_HX, -_LEG_HX),
    (-_LEG_HX, _LEG_HX),
]


def leg_corner_world_xy(leg_index: int, corner_index: int) -> tuple[float, float]:
    """World XY of a leg's vertical edge (one of the leg's 4 corners).

    Mirrors build_table.py: each leg is a box centered at
    (LEG_RADIUS*cos(a), LEG_RADIUS*sin(a)) then rotated by a + π/2 around Z.
    """
    angle = LEG_ANGLES[leg_index]
    cx = LEG_RADIUS * math.cos(angle)
    cy = LEG_RADIUS * math.sin(angle)
    theta = angle + math.pi / 2
    ct, st = math.cos(theta), math.sin(theta)
    lx, ly = LEG_LOCAL_CORNERS[corner_index]
    return (cx + ct * lx - st * ly, cy + st * lx + ct * ly)


def build_leg_corner_vertical(
    leg_index: int,
    corner_index: int,
) -> list[tuple[float, float, float]]:
    """Vertical line along one of a leg's 4 corner edges, floor to skirt-bottom."""
    wx, wy = leg_corner_world_xy(leg_index, corner_index)
    return [
        (wx, wy, LEG_BOTTOM_Z + SURFACE_LIFT),
        (wx, wy, LEG_TOP_Z - SURFACE_LIFT),
    ]


def collect_table_export_objects(scene: bpy.types.Scene) -> list[bpy.types.Object]:
    # Just the desk itself + the authored Tron lines. SuitPlatform / SuitCase_*
    # / SuitDisplays are spatially related but conceptually separate scope —
    # they belong to a later export, not 'the table'.
    explicit = {"Top", "Skirt", "FootBrace", "Leg_1", "Leg_2", "Leg_3", "Leg_4"}
    prefixes = ("TronLine_",)
    out = []
    for obj in scene.objects:
        if obj.name in explicit or obj.name.startswith(prefixes):
            out.append(obj)
    return out


def verify_glb(path: str) -> dict:
    """Parse the GLB header and return its JSON manifest for inspection."""
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"glTF":
            raise RuntimeError(f"Not a glTF binary: magic={magic!r}")
        _version, _length = struct.unpack("<II", f.read(8))
        chunk_len = struct.unpack("<I", f.read(4))[0]
        _chunk_type = f.read(4)
        return json.loads(f.read(chunk_len))


def main() -> None:
    if TARGET_SCENE not in bpy.data.scenes:
        raise SystemExit(f"Scene {TARGET_SCENE!r} not found")
    scene = bpy.data.scenes[TARGET_SCENE]
    if bpy.context.window is not None:
        bpy.context.window.scene = scene

    coll = get_or_create_top_level_collection(scene, TRON_COLL_NAME)
    remove_existing_tron_lines()

    # Order, delay, geometry. The names encode the spawn schedule the JS reads.
    #
    # Bottom-up outline draw. 4 layers, light overlap between layers so it feels
    # alive rather than strictly sequential. By ~t=5s the entire desk silhouette
    # is traced in cyan and the table reads as a Tron-lines wireframe.
    pi = math.pi
    si = SKIRT_ANGULAR_INSET
    lines: list[tuple[str, list[tuple[float, float, float]]]] = [
        # ----- Layer 1 — foot brace (the bottom support, z = 0..0.04) -----
        # Outer + inner rims at both z so the brace reads as a solid ring,
        # plus chord-cap closers that pair with the existing top radials to
        # form a closed quad at each tip.
        ("TronLine_001_0.0", build_arc(BRACE_OUTER_R, BRACE_THICKNESS, 0.0, pi)),
        ("TronLine_031_0.2", build_arc(BRACE_INNER_R, BRACE_THICKNESS, pi, 0.0)),
        ("TronLine_002_0.4", build_arc(BRACE_OUTER_R, 0.0, 0.0, pi)),
        ("TronLine_032_0.5", build_arc(BRACE_INNER_R, 0.0, pi, 0.0)),
        ("TronLine_003_0.6", build_radial_segment(BRACE_INNER_R, BRACE_OUTER_R, 0.0, BRACE_THICKNESS)),
        ("TronLine_033_0.65", build_chord_cap_closer(BRACE_INNER_R, BRACE_OUTER_R, 0.0, BRACE_THICKNESS, 0.0)),
        ("TronLine_004_0.7", build_radial_segment(BRACE_INNER_R, BRACE_OUTER_R, pi, BRACE_THICKNESS)),
        ("TronLine_034_0.75", build_chord_cap_closer(BRACE_INNER_R, BRACE_OUTER_R, pi, BRACE_THICKNESS, 0.0)),

        # ----- Layer 2 — legs (z 0.04 → 0.91). 4 verticals per leg, 4 legs.
        # All 4 corners of one leg fire together so each leg reads as a single
        # "appearance event"; legs themselves are staggered so the wave moves
        # around the arc instead of all 16 verticals popping at once.
        # Leg_1 (angle π/8, front-right)
        ("TronLine_005_1.5", build_leg_corner_vertical(0, 0)),
        ("TronLine_006_1.5", build_leg_corner_vertical(0, 1)),
        ("TronLine_007_1.5", build_leg_corner_vertical(0, 2)),
        ("TronLine_008_1.5", build_leg_corner_vertical(0, 3)),
        # Leg_2 (angle 3π/8)
        ("TronLine_009_1.7", build_leg_corner_vertical(1, 0)),
        ("TronLine_010_1.7", build_leg_corner_vertical(1, 1)),
        ("TronLine_011_1.7", build_leg_corner_vertical(1, 2)),
        ("TronLine_012_1.7", build_leg_corner_vertical(1, 3)),
        # Leg_3 (angle 5π/8)
        ("TronLine_013_1.9", build_leg_corner_vertical(2, 0)),
        ("TronLine_014_1.9", build_leg_corner_vertical(2, 1)),
        ("TronLine_015_1.9", build_leg_corner_vertical(2, 2)),
        ("TronLine_016_1.9", build_leg_corner_vertical(2, 3)),
        # Leg_4 (angle 7π/8, front-left)
        ("TronLine_017_2.1", build_leg_corner_vertical(3, 0)),
        ("TronLine_018_2.1", build_leg_corner_vertical(3, 1)),
        ("TronLine_019_2.1", build_leg_corner_vertical(3, 2)),
        ("TronLine_020_2.1", build_leg_corner_vertical(3, 3)),

        # ----- Layer 3 — skirt. Outer + inner rims at both z (top edge meets
        # the slab underside, bottom edge meets the legs), plus chord-cap
        # closers that pair with the existing bottom radials to close each tip.
        ("TronLine_021_2.6", build_arc(SKIRT_OUTER_R, SKIRT_Z_BOTTOM, si, pi - si)),
        ("TronLine_035_2.7", build_arc(SKIRT_OUTER_R, SKIRT_Z_TOP, si, pi - si)),
        ("TronLine_022_2.8", build_arc(SKIRT_INNER_R, SKIRT_Z_BOTTOM, pi - si, si)),
        ("TronLine_036_2.9", build_arc(SKIRT_INNER_R, SKIRT_Z_TOP, pi - si, si)),
        ("TronLine_023_3.0", build_radial_segment(SKIRT_INNER_R, SKIRT_OUTER_R, si, SKIRT_Z_BOTTOM)),
        ("TronLine_037_3.05", build_chord_cap_closer(SKIRT_INNER_R, SKIRT_OUTER_R, si, SKIRT_Z_BOTTOM, SKIRT_Z_TOP)),
        ("TronLine_024_3.1", build_radial_segment(SKIRT_INNER_R, SKIRT_OUTER_R, pi - si, SKIRT_Z_BOTTOM)),
        ("TronLine_038_3.15", build_chord_cap_closer(SKIRT_INNER_R, SKIRT_OUTER_R, pi - si, SKIRT_Z_BOTTOM, SKIRT_Z_TOP)),

        # ----- Layer 4 — top slab. Outer + inner arcs at both z so the slab
        # reads as having thickness; chord-cap closers turn each open tip
        # radial into a fully closed quad.
        ("TronLine_025_3.5", build_arc(OUTER_R, TOP_HEIGHT, 0.0, pi)),
        ("TronLine_026_3.7", build_arc(OUTER_R, SLAB_Z_BOTTOM, 0.0, pi)),
        ("TronLine_027_3.9", build_arc(INNER_R, TOP_HEIGHT, pi, 0.0)),
        ("TronLine_028_4.0", build_arc(INNER_R, SLAB_Z_BOTTOM, pi, 0.0)),
        ("TronLine_029_4.2", build_radial_segment(INNER_R, OUTER_R, 0.0, TOP_HEIGHT)),
        ("TronLine_039_4.25", build_chord_cap_closer(INNER_R, OUTER_R, 0.0, TOP_HEIGHT, SLAB_Z_BOTTOM)),
        ("TronLine_030_4.3", build_radial_segment(INNER_R, OUTER_R, pi, TOP_HEIGHT)),
        ("TronLine_040_4.35", build_chord_cap_closer(INNER_R, OUTER_R, pi, TOP_HEIGHT, SLAB_Z_BOTTOM)),
    ]
    for name, pts in lines:
        make_polyline(name, pts, coll)
    print(f"[tron-lines] authored {len(lines)} lines in collection {coll.name!r}")

    if os.environ.get("SAVE_BLEND_AFTER") == "1":
        bpy.ops.wm.save_mainfile()
        print(f"[tron-lines] saved {bpy.data.filepath!r}")

    # Export only the table + TronLines, not the whole 700-object scene.
    bpy.ops.object.select_all(action="DESELECT")
    to_export = collect_table_export_objects(scene)
    for obj in to_export:
        obj.select_set(True)
    print(f"[tron-lines] selected {len(to_export)} objects for export")

    blend_dir = os.path.dirname(bpy.data.filepath) or os.getcwd()
    output_path = os.path.abspath(os.path.join(blend_dir, OUTPUT_RELATIVE))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        # use_active_scene matters: without it, glTF walks every scene in the file
        # and picks up cross-scene selection state left over from prior saves
        # (e.g. PCB roster objects in 'Circuit-elements').
        use_active_scene=True,
        use_selection=True,
        export_apply=True,
        export_yup=True,
        use_mesh_edges=True,
        use_mesh_vertices=False,
        export_extras=True,
    )
    print(f"[tron-lines] exported {output_path}")

    manifest = verify_glb(output_path)
    node_names = [n.get("name", "") for n in manifest.get("nodes", [])]
    tron_nodes = sorted(n for n in node_names if n.startswith("TronLine_"))
    print(f"[verify] total nodes: {len(node_names)}")
    print(f"[verify] TronLine nodes ({len(tron_nodes)}):")
    for n in tron_nodes:
        print(f"  - {n}")
    if len(tron_nodes) != len(lines):
        raise SystemExit(
            f"[verify] expected {len(lines)} TronLine nodes, got {len(tron_nodes)}"
        )


if __name__ == "__main__":
    main()
