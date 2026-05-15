"""
Import four vehicle meshes and place them in front of the desk (+Y). Minimal logic: uniform
scale to ``MAX_PLAN_EXTENT``, floor at Z=0, face local +Y toward the clearing.

Uses the scene/collection that holds the table so props show up in **Main Scene** (see
``.cursor/rules/blender-table-front.mdc``).

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/table/vehicle_bays.py
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parents[2]

# Rough layout in front of the arc (same scale as early passes; not tied to build_table).
OUTER_R = 1.65
PLAZA_CENTER_Y = OUTER_R + 1.35
CLEARING_HALF_WIDTH = 1.22
COLUMN_OFFSET_X = CLEARING_HALF_WIDTH + 0.92
ROW_ALONG_Y = 0.62
MAX_PLAN_EXTENT = 1.75
MAX_HEIGHT = None

VEHICLE_SLOTS: tuple[dict, ...] = (
    {
        "id": "LukeSpeeder",
        "folder": "lukespeeder",
        "path": REPO_ROOT / "models" / "lukespeeder" / "source" / "LS_Sketch.fbx",
        "column_x": -COLUMN_OFFSET_X,
        "row_y": PLAZA_CENTER_Y + ROW_ALONG_Y,
    },
    {
        "id": "TronBike",
        "folder": "tronbike",
        "path": REPO_ROOT / "models" / "tronbike" / "source" / "Moto_TRON.fbx",
        "column_x": -COLUMN_OFFSET_X,
        "row_y": PLAZA_CENTER_Y - ROW_ALONG_Y,
    },
    {
        "id": "Batmobile",
        "folder": "batmobile",
        "path": REPO_ROOT
        / "models"
        / "batmobile"
        / "source"
        / "Batmobile for Sketchfab.fbx",
        "column_x": COLUMN_OFFSET_X,
        "row_y": PLAZA_CENTER_Y + ROW_ALONG_Y,
    },
    {
        "id": "Impala1967",
        "folder": "impala1967",
        "path": REPO_ROOT
        / "models"
        / "impala1967"
        / "Chevrolet Impala 1967 Supernatural.glb",
        "column_x": COLUMN_OFFSET_X,
        "row_y": PLAZA_CENTER_Y - ROW_ALONG_Y,
    },
)

TABLE_PART_NAMES = ("Top", "Skirt", "FootBrace", "Leg_1")


def _scene_with_table():
    for scene in bpy.data.scenes:
        names = {o.name for o in scene.objects}
        if any(n in names for n in TABLE_PART_NAMES):
            return scene
    return None


def _collection_with_table(scene):
    def walk(coll):
        names = {o.name for o in coll.objects}
        if any(n in names for n in TABLE_PART_NAMES):
            return coll
        for child in coll.children:
            found = walk(child)
            if found:
                return found
        return None

    return walk(scene.collection) or scene.collection


def _find_layer_collection(root, target_coll):
    if root.collection is target_coll:
        return root
    for child in root.children:
        found = _find_layer_collection(child, target_coll)
        if found:
            return found
    return None


def _activate_scene(scene):
    win = bpy.context.window or (
        bpy.context.window_manager.windows[0]
        if bpy.context.window_manager.windows
        else None
    )
    if win is not None:
        win.scene = scene


def _object_tree_iter(root: bpy.types.Object):
    stack = [root]
    while stack:
        o = stack.pop()
        yield o
        stack.extend(o.children)


def _force_entire_tree_into_collection(root: bpy.types.Object, coll: bpy.types.Collection):
    for o in _object_tree_iter(root):
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        if coll not in o.users_collection:
            coll.objects.link(o)


def _first_model_file(dir_name: str) -> Path | None:
    base = REPO_ROOT / "models" / dir_name
    if not base.is_dir():
        return None
    for pattern in ("*.glb", "*.GLB", "*.fbx", "*.FBX"):
        matches = sorted(base.rglob(pattern))
        if matches:
            return matches[0]
    return None


def _remove_vehicle_plaza():
    names = [n for n in bpy.data.objects.keys() if n.startswith("Vehicle_")]
    for name in sorted(names, key=len, reverse=True):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)


def _all_meshes_under(roots: list[bpy.types.Object]) -> list[bpy.types.Object]:
    out: list[bpy.types.Object] = []
    stack = list(roots)
    while stack:
        o = stack.pop()
        if o.type == "MESH" and o.data:
            out.append(o)
        stack.extend(o.children)
    return out


def _world_bbox_corners(obj: bpy.types.Object) -> list[Vector]:
    corners = []
    if obj.type != "MESH" or not obj.data:
        return corners
    for c in obj.bound_box:
        corners.append(obj.matrix_world @ Vector(c))
    return corners


def _combined_xy_extents(objects: list[bpy.types.Object]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for obj in objects:
        for co in _world_bbox_corners(obj):
            xs.append(co.x)
            ys.append(co.y)
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), max(xs), min(ys), max(ys)


def _combined_z_range(objects: list[bpy.types.Object]) -> tuple[float, float]:
    zs: list[float] = []
    for obj in objects:
        zs.extend(c.z for c in _world_bbox_corners(obj))
    if not zs:
        return 0.0, 0.0
    return min(zs), max(zs)


def _import_path(path: Path) -> list[bpy.types.Object]:
    path = path.resolve()
    if not path.is_file():
        return []
    before = set(bpy.data.objects)
    ext = path.suffix.lower()
    if ext == ".glb" or ext == ".gltf":
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    else:
        print(f"[vehicle_bays] unsupported extension: {path}")
        return []
    after = [o for o in bpy.data.objects if o not in before]
    return [o for o in after if o.parent is None]


def _face_toward_world_point(root: bpy.types.Object, target: Vector):
    """Assume local +Y forward; Z rotation only."""
    pos = root.matrix_world.translation
    flat = Vector((target.x - pos.x, target.y - pos.y))
    if flat.length_squared < 1e-12:
        return
    flat.normalize()
    root.rotation_euler = (0.0, 0.0, math.atan2(-flat.x, flat.y))


def _fit_and_place(
    roots: list[bpy.types.Object],
    slot_x: float,
    slot_y: float,
    face_toward: Vector,
    target_coll: bpy.types.Collection,
) -> bpy.types.Object | None:
    if not roots:
        return None

    parent = bpy.data.objects.new("VehicleRoot", None)
    target_coll.objects.link(parent)

    for r in roots:
        r.parent = parent

    bpy.context.view_layer.update()

    meshes = _all_meshes_under(roots)
    if not meshes:
        bpy.data.objects.remove(parent, do_unlink=True)
        return None

    for _ in range(28):
        bpy.context.view_layer.update()
        min_x, max_x, min_y, max_y = _combined_xy_extents(meshes)
        dx = max_x - min_x
        dy = max_y - min_y
        z0, z1 = _combined_z_range(meshes)
        dz = z1 - z0
        span = max(dx, dy, 1e-6)
        s_need = MAX_PLAN_EXTENT / span
        if MAX_HEIGHT is not None and dz > 1e-6:
            s_need = min(s_need, MAX_HEIGHT / dz)
        if s_need >= 0.9995:
            break
        sx, sy, sz = parent.scale
        parent.scale = (sx * s_need, sy * s_need, sz * s_need)
    bpy.context.view_layer.update()

    min_x, max_x, min_y, max_y = _combined_xy_extents(meshes)
    z_lo, _ = _combined_z_range(meshes)

    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    parent.location = (slot_x - cx, slot_y - cy, -z_lo)

    bpy.context.view_layer.update()
    _face_toward_world_point(parent, face_toward)

    bpy.context.view_layer.update()
    z_lo2, _ = _combined_z_range(meshes)
    parent.location.z -= z_lo2
    return parent


def build():
    target_scene = _scene_with_table()
    if target_scene is None:
        raise RuntimeError(
            "vehicle_bays: no scene contains the desk (Top, Skirt, FootBrace, Leg_1)."
        )
    target_coll = _collection_with_table(target_scene)
    _activate_scene(target_scene)

    layer_coll = _find_layer_collection(
        bpy.context.view_layer.layer_collection, target_coll
    )
    if layer_coll is not None:
        bpy.context.view_layer.active_layer_collection = layer_coll

    _remove_vehicle_plaza()

    plaza = bpy.data.objects.new("VehiclePlaza", None)
    plaza.empty_display_type = "PLAIN_AXES"
    plaza.empty_display_size = 0.25
    target_coll.objects.link(plaza)

    clearing_mid = Vector((0.0, PLAZA_CENTER_Y, 0.0))
    other_scenes = [s.name for s in bpy.data.scenes if s != target_scene]

    for slot in VEHICLE_SLOTS:
        vid = slot["id"]
        path = slot.get("path")
        if path is None:
            path = _first_model_file(slot["folder"])
        elif isinstance(path, Path):
            path = path if path.is_file() else _first_model_file(slot["folder"])

        if path is None or not Path(path).is_file():
            print(
                f"[vehicle_bays] SKIP {vid}: no model under models/{slot['folder']}/"
            )
            continue

        roots = _import_path(Path(path))
        if not roots:
            print(f"[vehicle_bays] SKIP {vid}: import failed for {path}")
            continue

        root = _fit_and_place(
            roots,
            slot["column_x"],
            slot["row_y"],
            clearing_mid,
            target_coll,
        )
        if root is None:
            for r in roots:
                bpy.data.objects.remove(r, do_unlink=True)
            continue

        root.name = f"Vehicle_{vid}"
        root.parent = plaza
        _force_entire_tree_into_collection(root, target_coll)

        print(f"[vehicle_bays] OK {vid} <- {path}")

    _force_entire_tree_into_collection(plaza, target_coll)

    print(
        f"[vehicle_bays] scene={target_scene.name!r} collection={target_coll.name!r} "
        f"| children={len(plaza.children)}"
    )
    if other_scenes:
        print(
            f"[vehicle_bays] other scenes: {other_scenes} — vehicles only in "
            f"{target_scene.name!r}"
        )


if __name__ == "__main__":
    build()
    _blend_out = os.environ.get("BLEND_OUT")
    if _blend_out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(_blend_out))
    elif os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
