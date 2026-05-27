"""
Import Claude random_pcb.glb and generate octilinear circuit traces (no vias).

Follows plans/chatgpt/circuit-lines-gen-rules.md — traces only, 45°/90° routing,
parallel buses, emissive cyan on board top.

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/build_claude_circuit_traces.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from circuit_trace_router import RouterResult, TraceSegment, route_traces

# Claude layout planner (same config as build_random_pcb.py seed=42)
_layout_dir = Path(__file__).resolve().parents[1] / "plans/claude/files/pcb_export/layout"
if str(_layout_dir) not in sys.path:
    sys.path.insert(0, str(_layout_dir))

from pcb_layout import FamilySpec, LayoutPlanner  # noqa: E402

from import_claude_pcb import (  # noqa: E402
    COLL_COMPONENTS,
    SCENE_NAME,
    coll_ensure,
    ensure_scene,
    import_glb,
)

COLL_TRACES = "ClaudePCB_Traces"
TRACE_PREFIX = "claude_trace_"
SEED = 42

FAMILIES = {
    "qfp": FamilySpec(count=18, footprint=(2, 2), distributed=True, regions=(3, 2)),
    "heatsink": FamilySpec(count=8, footprint=(2, 2), distributed=True, regions=(2, 2)),
    "dip": FamilySpec(count=25, footprint=(2, 1), allow_rotation=True),
    "header": FamilySpec(count=15, footprint=(2, 1), allow_rotation=True),
    "connector": FamilySpec(count=12, footprint=(2, 1), allow_rotation=True),
    "octagon": FamilySpec(count=10, footprint=(1, 1)),
    "cap": FamilySpec(count=35, footprint=(1, 1)),
}


def purge_traces() -> None:
    stale = [o for o in bpy.data.objects if o.name.startswith(TRACE_PREFIX)]
    for ob in stale:
        bpy.data.objects.remove(ob, do_unlink=True)
    stale_m = [m for m in bpy.data.meshes if m.name.startswith(TRACE_PREFIX) and m.users == 0]
    for m in stale_m:
        bpy.data.meshes.remove(m)
    coll = bpy.data.collections.get(COLL_TRACES)
    if coll and coll.users == 0:
        bpy.data.collections.remove(coll)


def ensure_trace_material() -> bpy.types.Material:
    mat = bpy.data.materials.get("ClaudePCB_TraceEmissive")
    if mat is None:
        mat = bpy.data.materials.new("ClaudePCB_TraceEmissive")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.0, 0.92, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 12.0
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = (0.0, 0.92, 1.0, 1.0)
    return mat


def _set_emission_material(
    mat: bpy.types.Material,
    color: tuple[float, float, float, float],
    strength: float,
) -> None:
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


def _set_principled_material(
    mat: bpy.types.Material,
    color: tuple[float, float, float, float],
) -> None:
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 1.0


def retint_claude_materials() -> None:
    """Push imported GLB materials toward the ChatGPT cyan-on-black top view."""
    dark_board = (0.0, 0.004, 0.008, 1.0)
    dark_component = (0.002, 0.006, 0.008, 1.0)
    cyan = (0.0, 0.9, 1.0, 1.0)
    board_cyan = (0.05, 0.55, 0.72, 1.0)
    for mat in bpy.data.materials:
        base = mat.name.split(".")[0]
        if base == "Material_0":
            _set_principled_material(mat, dark_board)
        elif base == "Material_2":
            _set_principled_material(mat, dark_component)
        elif base == "Material_1":
            _set_emission_material(mat, board_cyan, 1.6)
        elif base == "Material_3":
            _set_emission_material(mat, cyan, 2.4)


def segment_direction(seg: TraceSegment) -> Vector:
    return Vector(seg.p1) - Vector(seg.p0)


def add_trace_segment(
    bm: bmesh.types.BMesh,
    seg: TraceSegment,
) -> None:
    p0 = Vector(seg.p0)
    p1 = Vector(seg.p1)
    delta = p1 - p0
    length = delta.length
    if length < 1e-5:
        return
    # Thin box extruded along segment (reads as neon line in viewport)
    mid = (p0 + p1) * 0.5
    # Visual multiplier so thin spec widths read clearly in Eevee ortho renders
    w = max(seg.width * 2.8, 0.028)
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:]
    bmesh.ops.scale(bm, vec=(length, w, max(w * 0.5, 0.06)), verts=verts)
    # Board plane XY; thin in Z. Rotate segment to lie along XY.
    angle = math.atan2(delta.y, delta.x)
    bmesh.ops.rotate(
        bm,
        cent=(0.0, 0.0, 0.0),
        matrix=Matrix.Rotation(angle, 3, "Z"),
        verts=verts,
    )
    bmesh.ops.translate(bm, vec=mid, verts=verts)


def build_trace_mesh(segments: list[TraceSegment], coll: bpy.types.Collection, mat: bpy.types.Material) -> bpy.types.Object:
    bm = bmesh.new()
    for seg in segments:
        add_trace_segment(bm, seg)
    mesh = bpy.data.meshes.new(f"{TRACE_PREFIX}mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    ob = bpy.data.objects.new(f"{TRACE_PREFIX}all", mesh)
    coll.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def setup_world(scene: bpy.types.Scene) -> None:
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("ClaudePCB_World")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def setup_camera(
    scene: bpy.types.Scene,
    lo: Vector,
    hi: Vector,
    *,
    name: str = "ClaudePCB_Cam_Ref",
) -> bpy.types.Object:
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 36.0
    cam_ob = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_ob)
    # Reference-style 3/4 view: elevated +Z, looking at board in XY
    cam_ob.location = center + Vector((span * 0.48, -span * 0.62, span * 0.82))
    cam_ob.rotation_euler = (math.radians(52), 0.0, math.radians(30))
    scene.camera = cam_ob
    return cam_ob


def render_still(scene: bpy.types.Scene, filepath: str, cam_ob: bpy.types.Object) -> None:
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


def run_layout_and_route() -> RouterResult:
    planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
    report = planner.plan(FAMILIES, seed=SEED, filler_family="smd")
    return route_traces(planner, report, seed=SEED)


def build_all() -> dict:
    scene = ensure_scene(SCENE_NAME)
    bpy.context.window.scene = scene

    import_stats = import_glb()
    retint_claude_materials()
    purge_traces()
    coll_tr = coll_ensure(COLL_TRACES, scene)

    router_result = run_layout_and_route()
    mat = ensure_trace_material()
    trace_ob = build_trace_mesh(router_result.segments, coll_tr, mat)

    setup_world(scene)
    lo, hi = import_stats["bbox_lo"], import_stats["bbox_hi"]
    cam = setup_camera(scene, lo, hi)

    bpy.context.view_layer.update()
    return {
        "scene": scene,
        "import": import_stats,
        "router": router_result,
        "trace_object": trace_ob,
        "camera": cam,
        "bbox_lo": lo,
        "bbox_hi": hi,
    }


if __name__ == "__main__":
    stats = build_all()
    rr = stats["router"]
    print(
        f"[claude_traces] segments={rr.stats.get('segment_count', len(rr.segments))} "
        f"traces={rr.stats.get('trace_count')} "
        f"routed_nets={rr.stats.get('routed_nets')}"
    )
    print(f"[claude_traces] import meshes={stats['import']['mesh_count']}")
    lo, hi = stats["bbox_lo"], stats["bbox_hi"]
    print(
        f"[claude_traces] bbox x={lo.x:.2f}..{hi.x:.2f} "
        f"y={lo.y:.2f}..{hi.y:.2f} z={lo.z:.2f}..{hi.z:.2f}"
    )

    out_dir = os.path.join(_script_dir, "renders")
    render_path = os.path.join(out_dir, "claude-pcb-traces-ref.png")
    render_still(stats["scene"], render_path, stats["camera"])
    print(f"[claude_traces] render -> {render_path}")

    # Top ortho for comparison with ChatGPT top-view reference
    center = (stats["bbox_lo"] + stats["bbox_hi"]) * 0.5
    span = max(
        stats["bbox_hi"].x - stats["bbox_lo"].x,
        stats["bbox_hi"].y - stats["bbox_lo"].y,
        10.0,
    )
    top_cam = setup_camera(
        stats["scene"], stats["bbox_lo"], stats["bbox_hi"], name="ClaudePCB_Cam_Top"
    )
    top_cam.data.type = "ORTHO"
    top_cam.data.ortho_scale = span * 1.05
    top_cam.location = center + Vector((0.0, 0.0, span * 1.2))
    top_cam.rotation_euler = (0.0, 0.0, 0.0)
    top_path = os.path.join(out_dir, "claude-pcb-traces-top.png")
    render_still(stats["scene"], top_path, top_cam)
    print(f"[claude_traces] render -> {top_path}")

    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[claude_traces] saved main.blend")
