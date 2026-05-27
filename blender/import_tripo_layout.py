"""
Import Tripo Neon Circuit Components GLB into scene Tripo Layout.

Splits the import into separate mesh objects only where there is empty XY space
between edge-connected islands (merges nearby mesh fragments on the same part).

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/import_tripo_layout.py

Tune gap (world units, model is ~1 m wide)::

    TRIPO_GAP_XY=0.018 SAVE_BLEND_AFTER=1 ...
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

SCENE_NAME = "Tripo Layout"
COLL_NAME = "TripoLayout"
ROOT_NAME = "tripo_neon_circuit_components"
PART_PREFIX = "trip_comp_"

# Merge islands whose XY bbox gaps are both smaller than this (empty aisle = split).
GAP_XY = float(os.environ.get("TRIPO_GAP_XY", "0.018"))
SWEEP_X_NEIGHBORS = 800

_REPO_ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = _REPO_ROOT / "plans/tripo/Neon Circuit Components 3D Model.glb"


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
    if coll.users == 0:
        bpy.data.collections.remove(coll)


def _world_bbox(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            lo.x = min(lo.x, w.x)
            lo.y = min(lo.y, w.y)
            lo.z = min(lo.z, w.z)
            hi.x = max(hi.x, w.x)
            hi.y = max(hi.y, w.y)
            hi.z = max(hi.z, w.z)
    return lo, hi


def _part_sort_key(obj: bpy.types.Object) -> tuple:
    co = obj.matrix_world.translation
    return (round(co.y, 5), round(co.x, 5), round(co.z, 5))


def _island_bboxes_and_faces(
    me: bpy.types.Mesh, matrix_world: bpy.types.Matrix
) -> list[tuple[list[int], Vector, Vector]]:
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    visited: set[int] = set()
    islands: list[tuple[list[int], Vector, Vector]] = []

    for seed in bm.faces:
        if seed.index in visited:
            continue
        stack = [seed]
        visited.add(seed.index)
        face_idxs: list[int] = []
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        while stack:
            face = stack.pop()
            face_idxs.append(face.index)
            for vert in face.verts:
                w = matrix_world @ vert.co
                lo.x = min(lo.x, w.x)
                lo.y = min(lo.y, w.y)
                lo.z = min(lo.z, w.z)
                hi.x = max(hi.x, w.x)
                hi.y = max(hi.y, w.y)
                hi.z = max(hi.z, w.z)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked.index not in visited:
                        visited.add(linked.index)
                        stack.append(linked)
        islands.append((face_idxs, lo, hi))

    bm.free()
    return islands


def _cluster_island_indices(boxes: list[tuple[Vector, Vector]], gap: float) -> list[list[int]]:
    n = len(boxes)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    order = sorted(range(n), key=lambda i: boxes[i][0].x)
    for ai, i in enumerate(order):
        lo1, hi1 = boxes[i]
        for j in order[ai + 1 : ai + SWEEP_X_NEIGHBORS]:
            lo2, hi2 = boxes[j]
            if lo2.x - hi1.x > gap:
                break
            gap_x = max(0.0, lo1.x - hi2.x, lo2.x - hi1.x)
            gap_y = max(0.0, lo1.y - hi2.y, lo2.y - hi1.y)
            if gap_x < gap and gap_y < gap:
                union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return list(groups.values())


def _mesh_object_from_faces(
    src_me: bpy.types.Mesh,
    face_indices: set[int],
    name: str,
    materials,
) -> bpy.types.Object:
    bm = bmesh.new()
    bm.from_mesh(src_me)
    bm.faces.ensure_lookup_table()
    delete = [f for f in bm.faces if f.index not in face_indices]
    if delete:
        bmesh.ops.delete(bm, geom=delete, context="FACES")
    me_out = bpy.data.meshes.new(name)
    bm.to_mesh(me_out)
    bm.free()
    me_out.update()
    ob = bpy.data.objects.new(name, me_out)
    for mat in materials:
        if mat is not None:
            ob.data.materials.append(mat)
    return ob


def separate_by_spatial_gap(
    src_obj: bpy.types.Object,
    target_coll: bpy.types.Collection,
    root: bpy.types.Object,
    gap: float,
) -> list[bpy.types.Object]:
    islands = _island_bboxes_and_faces(src_obj.data, src_obj.matrix_world)
    boxes = [(lo, hi) for _, lo, hi in islands]
    groups = _cluster_island_indices(boxes, gap)

    parts: list[bpy.types.Object] = []
    for group in groups:
        face_set: set[int] = set()
        for idx in group:
            face_set.update(islands[idx][0])
        parts.append(
            _mesh_object_from_faces(
                src_obj.data,
                face_set,
                f"{PART_PREFIX}tmp",
                src_obj.data.materials,
            )
        )

    bpy.data.objects.remove(src_obj, do_unlink=True)

    for ob in parts:
        for coll in list(ob.users_collection):
            coll.objects.unlink(ob)
        target_coll.objects.link(ob)
        ob.parent = root

    parts.sort(key=_part_sort_key)
    for i, ob in enumerate(parts):
        ob.name = f"{PART_PREFIX}{i:04d}"
        ob.data.name = ob.name

    return parts


def import_glb(path: Path, target_coll: bpy.types.Collection) -> bpy.types.Object | None:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"GLB not found: {path}")

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in imported if o.parent is None]
    if not roots:
        print("[tripo_layout] import produced no root objects")
        return None

    root = bpy.data.objects.new(ROOT_NAME, None)
    target_coll.objects.link(root)
    for obj in roots:
        obj.parent = root
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        if obj.name not in target_coll.objects:
            target_coll.objects.link(obj)

    bpy.context.view_layer.update()
    return root


def main() -> None:
    if not GLB_PATH.is_file():
        raise FileNotFoundError(GLB_PATH)

    scene = ensure_scene(SCENE_NAME)
    bpy.context.window.scene = scene
    purge_collection(COLL_NAME)
    coll = coll_ensure(COLL_NAME, scene)

    root = import_glb(GLB_PATH, coll)
    if root is None:
        return

    src_meshes = [o for o in list(coll.objects) if o.type == "MESH" and o.parent == root]
    parts: list[bpy.types.Object] = []
    for src in src_meshes:
        parts.extend(separate_by_spatial_gap(src, coll, root, GAP_XY))

    lo, hi = _world_bbox(parts)
    span = hi - lo
    print(f"[tripo_layout] scene={SCENE_NAME!r} collection={COLL_NAME!r}")
    print(f"[tripo_layout] gap_xy={GAP_XY}")
    print(f"[tripo_layout] root={root.name} components={len(parts)}")
    print(
        f"[tripo_layout] bbox x={lo.x:.4f}..{hi.x:.4f} "
        f"y={lo.y:.4f}..{hi.y:.4f} z={lo.z:.4f}..{hi.z:.4f}"
    )
    print(f"[tripo_layout] span {span.x:.4f} x {span.y:.4f} x {span.z:.4f}")


if __name__ == "__main__":
    main()
    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[tripo_layout] saved main.blend")
