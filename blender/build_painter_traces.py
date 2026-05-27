"""
Generate ArtBIT-style wire traces over the random_pcb.glb scene.

What it does (top-down):

1. Imports `plans/claude/files/random_pcb.glb`.
2. Identifies the board substrate (largest XY mesh) and collects every other
   mesh as a component obstacle.
3. Lays a fine 2D grid over the board's XY footprint and marks every cell
   covered by a component bbox (plus a small clearance buffer) as blocked.
4. Runs the ArtBIT/circuitboard-painter wire generator: random walks with high
   straightness fill the remaining free cells with mostly-straight, gently
   curving traces. See https://github.com/ArtBIT/circuitboard-painter.
5. Builds one thin emissive box per simplified segment at z = board top, then
   renders both a 3/4 reference view and a flat top-down view.

Run:

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/build_painter_traces.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from circuitboard_painter import (  # noqa: E402
    GridSpec,
    PainterParams,
    block_bbox,
    generate_wires,
    make_grid,
)
from import_claude_pcb import (  # noqa: E402
    COLL_COMPONENTS,
    SCENE_NAME,
    coll_ensure,
    ensure_scene,
    import_glb,
)


# ---------------------------------------------------------------------------
# Tuning. Trace thickness is decoupled from cell size so we can grow cells
# (which lets wires run further before the painter dies on a blocked corridor)
# without making the rendered traces visually thicker.
# ---------------------------------------------------------------------------
CELL_SIZE_WORLD = 0.20      # painter cell width
CLEARANCE_WORLD = 0.12      # extra gap around each component bbox
TRACE_WIDTH_WORLD = 0.077   # rendered trace width (kept fixed across cell sizes)
TRACE_HEIGHT_WORLD = 0.04   # rendered box thickness in Z

PAINTER = PainterParams(
    wire_length=400,         # high cap; actual length is corridor-bound
    cut_off_length=15,       # drop short stubs — only long traces survive
    straightness=14.0,
    wire_spacing=2,          # 2-cell halo so neighboring wires keep clear distance
    seed=1,
)

COLL_TRACES = "PainterPCB_Traces"
TRACE_PREFIX = "painter_trace_"
EMISSIVE_NAME = "PainterPCB_TraceEmissive"
EPS = 1e-4

# Legacy trace artifacts from `build_claude_circuit_traces.py`. We strip them
# whenever the painter runs so the saved scene contains just the painter mesh.
_LEGACY_PREFIX = "claude_trace_"
_LEGACY_COLL = "ClaudePCB_Traces"


# ---------------------------------------------------------------------------
# Cleanup / collection plumbing
# ---------------------------------------------------------------------------
def _purge_prefix(prefix: str) -> None:
    for ob in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(ob, do_unlink=True)
    for m in [m for m in bpy.data.meshes
              if m.name.startswith(prefix) and m.users == 0]:
        bpy.data.meshes.remove(m)


def _purge_collection(name: str) -> None:
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for parent in bpy.data.collections:
        if name in parent.children.keys():
            parent.children.unlink(coll)
    for sc in bpy.data.scenes:
        if name in sc.collection.children.keys():
            sc.collection.children.unlink(coll)
    if coll.users == 0:
        bpy.data.collections.remove(coll)


def purge_traces() -> None:
    _purge_prefix(TRACE_PREFIX)
    coll = bpy.data.collections.get(COLL_TRACES)
    if coll and coll.users == 0:
        bpy.data.collections.remove(coll)
    # Also remove the old octilinear-router output so the saved scene only
    # contains painter wires.
    _purge_prefix(_LEGACY_PREFIX)
    _purge_collection(_LEGACY_COLL)


# ---------------------------------------------------------------------------
# Materials. Match the existing cyan-on-black aesthetic.
# ---------------------------------------------------------------------------
def ensure_emissive_material() -> bpy.types.Material:
    mat = bpy.data.materials.get(EMISSIVE_NAME) or bpy.data.materials.new(EMISSIVE_NAME)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.0, 0.92, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 14.0
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = (0.0, 0.92, 1.0, 1.0)
    return mat


def _set_emission(mat: bpy.types.Material,
                  color: tuple[float, float, float, float],
                  strength: float) -> None:
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    links.new(emit.outputs["Emission"], out.inputs["Surface"])


def _set_principled(mat: bpy.types.Material,
                    color: tuple[float, float, float, float]) -> None:
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 1.0


def retint_imported_materials() -> None:
    """Push the GLB's defaults into the cyan-on-black palette used elsewhere."""
    dark_board = (0.0, 0.004, 0.008, 1.0)
    dark_component = (0.002, 0.006, 0.008, 1.0)
    cyan = (0.0, 0.9, 1.0, 1.0)
    board_cyan = (0.05, 0.55, 0.72, 1.0)
    for mat in bpy.data.materials:
        base = mat.name.split(".")[0]
        if base == "Material_0":
            _set_principled(mat, dark_board)
        elif base == "Material_2":
            _set_principled(mat, dark_component)
        elif base == "Material_1":
            _set_emission(mat, board_cyan, 1.6)
        elif base == "Material_3":
            _set_emission(mat, cyan, 2.4)


# ---------------------------------------------------------------------------
# Mesh inspection: pick board, collect component bboxes.
# ---------------------------------------------------------------------------
def _world_bbox(ob: bpy.types.Object) -> tuple[Vector, Vector]:
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    for corner in ob.bound_box:
        w = ob.matrix_world @ Vector(corner)
        for k in range(3):
            lo[k] = min(lo[k], w[k])
            hi[k] = max(hi[k], w[k])
    return lo, hi


def split_board_and_components(coll: bpy.types.Collection):
    """Largest XY mesh = board substrate; everything else = component."""
    meshes = [o for o in coll.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh objects in components collection")

    bboxes = [(o, *_world_bbox(o)) for o in meshes]

    def xy_area(b):
        _, lo, hi = b
        return (hi.x - lo.x) * (hi.y - lo.y)

    board_entry = max(bboxes, key=xy_area)
    components = [b for b in bboxes if b[0] is not board_entry[0]]
    return board_entry, components


# ---------------------------------------------------------------------------
# Build wires into a single bmesh, one box per simplified segment.
# ---------------------------------------------------------------------------
def _world_polyline(wire: list[tuple[int, int]],
                    grid: GridSpec, z: float) -> list[Vector]:
    return [Vector((*grid.cell_to_world(ix, iy), z)) for ix, iy in wire]


def _add_segment_box(bm: bmesh.types.BMesh, p0: Vector, p1: Vector,
                     width: float, height: float) -> None:
    delta = p1 - p0
    length = delta.length
    if length < EPS:
        return
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:]
    bmesh.ops.scale(bm, vec=(length, width, height), verts=verts)
    angle = math.atan2(delta.y, delta.x)
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0),
                     matrix=Matrix.Rotation(angle, 3, "Z"), verts=verts)
    bmesh.ops.translate(bm, vec=(p0 + p1) * 0.5, verts=verts)


def build_trace_object(wires: list[list[tuple[int, int]]],
                       grid: GridSpec, top_z: float,
                       coll: bpy.types.Collection,
                       mat: bpy.types.Material) -> tuple[bpy.types.Object, int]:
    bm = bmesh.new()
    n_segments = 0
    # Center the box so its bottom face rests flush on the board top.
    z = top_z + TRACE_HEIGHT_WORLD * 0.5 + EPS
    for wire in wires:
        pts = _world_polyline(wire, grid, z)
        for i in range(len(pts) - 1):
            _add_segment_box(bm, pts[i], pts[i + 1],
                             TRACE_WIDTH_WORLD, TRACE_HEIGHT_WORLD)
            n_segments += 1
    mesh = bpy.data.meshes.new(f"{TRACE_PREFIX}mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    ob = bpy.data.objects.new(f"{TRACE_PREFIX}all", mesh)
    coll.objects.link(ob)
    ob.data.materials.append(mat)
    return ob, n_segments


# ---------------------------------------------------------------------------
# Scene / camera / render setup (mirrors build_claude_circuit_traces.py).
# ---------------------------------------------------------------------------
def setup_world(scene: bpy.types.Scene) -> None:
    world = scene.world or bpy.data.worlds.new("PainterPCB_World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def setup_camera(scene: bpy.types.Scene, lo: Vector, hi: Vector,
                 *, name: str = "PainterPCB_Cam_Ref") -> bpy.types.Object:
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 36.0
    cam_ob = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_ob)
    cam_ob.location = center + Vector((span * 0.48, -span * 0.62, span * 0.82))
    cam_ob.rotation_euler = (math.radians(52), 0.0, math.radians(30))
    scene.camera = cam_ob
    return cam_ob


def render_still(scene: bpy.types.Scene, filepath: str,
                 cam_ob: bpy.types.Object) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "BLENDER_EEVEE"
    scene.camera = cam_ob
    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        for attr, val in (("use_bloom", True), ("bloom_intensity", 0.12)):
            if hasattr(eevee, attr):
                setattr(eevee, attr, val)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.35
    scene.view_settings.gamma = 1.0
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------
def build_all() -> dict:
    scene = ensure_scene(SCENE_NAME)
    bpy.context.window.scene = scene

    import_stats = import_glb()
    retint_imported_materials()
    purge_traces()
    coll_tr = coll_ensure(COLL_TRACES, scene)

    coll_components = bpy.data.collections.get(COLL_COMPONENTS)
    (board_ob, board_lo, board_hi), comps = split_board_and_components(coll_components)

    grid, blocked = make_grid(board_lo.x, board_lo.y, board_hi.x, board_hi.y,
                              CELL_SIZE_WORLD)
    blocked_cells = 0
    for _ob, lo, hi in comps:
        blocked_cells += block_bbox(grid, blocked, lo.x, lo.y, hi.x, hi.y,
                                    CLEARANCE_WORLD)

    result = generate_wires(blocked, PAINTER)

    # Place trace mesh just above the board's top face
    top_z = board_hi.z

    mat = ensure_emissive_material()
    trace_ob, n_segments = build_trace_object(result.wires, grid, top_z,
                                              coll_tr, mat)

    setup_world(scene)
    cam = setup_camera(scene, import_stats["bbox_lo"], import_stats["bbox_hi"])
    bpy.context.view_layer.update()

    return {
        "scene": scene,
        "import": import_stats,
        "board_object": board_ob,
        "board_top_z": top_z,
        "trace_object": trace_ob,
        "camera": cam,
        "grid": grid,
        "blocked_cells": blocked_cells,
        "n_components": len(comps),
        "n_wires": len(result.wires),
        "n_segments": n_segments,
        "raw_cell_lengths": result.raw_cell_counts,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    stats = build_all()
    grid: GridSpec = stats["grid"]
    total_cells = grid.width * grid.height
    print(f"[painter] components={stats['n_components']} "
          f"grid={grid.width}x{grid.height} "
          f"({total_cells} cells, {stats['blocked_cells']} blocked by components)")
    print(f"[painter] board_top_z={stats['board_top_z']:.3f}")
    rl = stats["raw_cell_lengths"]
    if rl:
        sl = sorted(rl)
        avg = sum(rl) / len(rl)
        print(f"[painter] wires={stats['n_wires']} "
              f"raw cells min/median/avg/max={min(rl)}/{sl[len(sl)//2]}/{avg:.1f}/{max(rl)} "
              f"segments={stats['n_segments']}")

    out_dir = os.path.join(_SCRIPT_DIR, "renders")
    ref_path = os.path.join(out_dir, "painter-pcb-traces-ref.png")
    render_still(stats["scene"], ref_path, stats["camera"])
    print(f"[painter] render -> {ref_path}")

    lo, hi = stats["import"]["bbox_lo"], stats["import"]["bbox_hi"]
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    top_cam = setup_camera(stats["scene"], lo, hi, name="PainterPCB_Cam_Top")
    top_cam.data.type = "ORTHO"
    top_cam.data.ortho_scale = span * 1.05
    top_cam.location = center + Vector((0.0, 0.0, span * 1.2))
    top_cam.rotation_euler = (0.0, 0.0, 0.0)
    top_path = os.path.join(out_dir, "painter-pcb-traces-top.png")
    render_still(stats["scene"], top_path, top_cam)
    print(f"[painter] render -> {top_path}")

    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") \
            and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[painter] saved main.blend")
