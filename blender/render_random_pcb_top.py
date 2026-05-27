"""Render a top orthographic PNG of plans/claude/files/random_pcb.glb."""

from __future__ import annotations

import os
import sys

import bpy
from mathutils import Vector

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from import_claude_pcb import import_glb  # noqa: E402

OUT_PATH = os.path.join(_script_dir, "renders", "random-pcb-top.png")


def setup_world(scene: bpy.types.Scene) -> None:
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("RandomPCB_World")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def setup_top_camera(scene: bpy.types.Scene, lo: Vector, hi: Vector) -> bpy.types.Object:
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    name = "RandomPCB_Cam_Top"
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * 1.05
    cam_ob = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_ob)
    cam_ob.location = center + Vector((0.0, 0.0, span * 1.2))
    cam_ob.rotation_euler = (0.0, 0.0, 0.0)
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
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.35
    scene.view_settings.gamma = 1.0
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    stats = import_glb()
    scene = stats["scene"]
    bpy.context.window.scene = scene
    setup_world(scene)
    cam = setup_top_camera(scene, stats["bbox_lo"], stats["bbox_hi"])
    render_still(scene, OUT_PATH, cam)
    lo, hi = stats["bbox_lo"], stats["bbox_hi"]
    print(f"[render_random_pcb_top] meshes={stats['mesh_count']}")
    print(
        f"[render_random_pcb_top] bbox "
        f"x={lo.x:.2f}..{hi.x:.2f} y={lo.y:.2f}..{hi.y:.2f} z={lo.z:.2f}..{hi.z:.2f}"
    )
    print(f"[render_random_pcb_top] render -> {OUT_PATH}")
