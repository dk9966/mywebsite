"""
Import Claude procedural PCB GLB into scene "Claude PCB".

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/import_claude_pcb.py
"""
from __future__ import annotations

import os
from pathlib import Path

import bpy
from mathutils import Vector

SCENE_NAME = "Claude PCB"
COLL_COMPONENTS = "ClaudePCB_Components"
ROOT_NAME = "claude_random_pcb"

_REPO_ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = _REPO_ROOT / "plans/claude/files/random_pcb.glb"


def ensure_scene(name: str) -> bpy.types.Scene:
    scene = bpy.data.scenes.get(name)
    if scene is None:
        scene = bpy.data.scenes.new(name)
    return scene


def coll_ensure(name: str, scene: bpy.types.Scene) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if name not in scene.collection.children.keys():
        scene.collection.children.link(coll)
    return coll


def purge_collection(name: str) -> None:
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
    if coll.users == 0:
        bpy.data.collections.remove(coll)


def collection_bbox(coll: bpy.types.Collection) -> tuple[Vector, Vector]:
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    for ob in coll.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
    return lo, hi


def import_glb() -> dict:
    scene = ensure_scene(SCENE_NAME)
    bpy.context.window.scene = scene

    purge_collection(COLL_COMPONENTS)
    coll = coll_ensure(COLL_COMPONENTS, scene)

    if bpy.data.objects.get(ROOT_NAME):
        bpy.data.objects.remove(bpy.data.objects[ROOT_NAME], do_unlink=True)

    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    imported = [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]

    root = bpy.data.objects.new(ROOT_NAME, None)
    coll.objects.link(root)

    for ob in imported:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob.parent = root

    bpy.context.view_layer.update()
    lo, hi = collection_bbox(coll)
    mesh_count = sum(1 for o in coll.objects if o.type == "MESH" and o != root)

    return {
        "scene": scene,
        "collection": coll,
        "root": root,
        "mesh_count": mesh_count,
        "bbox_lo": lo,
        "bbox_hi": hi,
    }


if __name__ == "__main__":
    if not GLB_PATH.is_file():
        raise FileNotFoundError(GLB_PATH)
    stats = import_glb()
    lo, hi = stats["bbox_lo"], stats["bbox_hi"]
    print(f"[import_claude_pcb] scene={SCENE_NAME} meshes={stats['mesh_count']}")
    print(
        f"[import_claude_pcb] bbox "
        f"x={lo.x:.2f}..{hi.x:.2f} "
        f"y={lo.y:.2f}..{hi.y:.2f} "
        f"z={lo.z:.2f}..{hi.z:.2f}"
    )
    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[import_claude_pcb] saved main.blend")
