"""Render top orthographic PNG of circuits-traced-outline.glb with bloom."""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
GLB_PATH = os.path.join(_root, "plans/circuit design/circuits-traced-outline.glb")
OUT_PATH = os.path.join(_root, "plans/circuit design/circuits-traced-outline.png")


def clear_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "CircuitsTracedOutline"
    return scene


def import_glb(path: str) -> tuple[Vector, Vector]:
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No meshes imported")
    lo = Vector((math.inf, math.inf, math.inf))
    hi = Vector((-math.inf, -math.inf, -math.inf))
    for ob in meshes:
        for corner in ob.bound_box:
            world = ob.matrix_world @ Vector(corner)
            lo.x = min(lo.x, world.x)
            lo.y = min(lo.y, world.y)
            lo.z = min(lo.z, world.z)
            hi.x = max(hi.x, world.x)
            hi.y = max(hi.y, world.y)
            hi.z = max(hi.z, world.z)
    return lo, hi


def setup_world(scene: bpy.types.Scene) -> None:
    world = bpy.data.worlds.new("CircuitsOutline_World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def setup_top_camera(scene: bpy.types.Scene, lo: Vector, hi: Vector) -> bpy.types.Object:
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    cam_data = bpy.data.cameras.new("CircuitsOutline_Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * 1.05
    cam_ob = bpy.data.objects.new("CircuitsOutline_Cam", cam_data)
    scene.collection.objects.link(cam_ob)
    cam_ob.location = center + Vector((0.0, 0.0, span * 1.2))
    cam_ob.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = cam_ob
    return cam_ob


def boost_emissive_materials() -> None:
    for mat in bpy.data.materials:
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        if nodes.get("Emission") is not None:
            continue
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        emissive = bsdf.inputs.get("Emission Color")
        strength = bsdf.inputs.get("Emission Strength")
        if emissive is None:
            continue
        color = tuple(emissive.default_value)
        emit_strength = float(strength.default_value) if strength else 1.0
        if max(color[:3]) < 0.05 and emit_strength < 0.05:
            color = (0.35, 0.85, 1.0, 1.0)
            emit_strength = 8.0
        else:
            emit_strength = max(emit_strength, 10.0)
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = color
        emit.inputs["Strength"].default_value = emit_strength
        links.new(emit.outputs["Emission"], out.inputs["Surface"])


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
    scene.view_settings.exposure = 0.45
    scene.view_settings.gamma = 1.0
    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        for attr, val in (("use_bloom", True), ("bloom_intensity", 0.18), ("bloom_threshold", 0.6)):
            if hasattr(eevee, attr):
                setattr(eevee, attr, val)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    scene = clear_scene()
    lo, hi = import_glb(GLB_PATH)
    boost_emissive_materials()
    setup_world(scene)
    cam = setup_top_camera(scene, lo, hi)
    render_still(scene, OUT_PATH, cam)
    print(f"[render_circuits_traced_outline] bbox lo={lo} hi={hi}")
    print(f"[render_circuits_traced_outline] render -> {OUT_PATH}")
