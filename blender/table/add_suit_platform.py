"""
Insert or refresh **SuitPlatform** in the Blender file you already have open.

Use this when your scene already has the table (and anything else) and you only
want the hex platform added — it does **not** delete other objects.

**From Cursor / terminal** (no clicking Run Script): load your `.blend`, run this
script, optionally save in one shot::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background /path/to/your_scene.blend \\
      --python /path/to/add_suit_platform.py

**In Blender:** Scripting → Open this file → Run Script.

Set ``SAVE_BLEND_AFTER=1`` when using ``--background`` so the file is written
back to disk; interactive runs usually omit it and save manually.
"""

import os
from pathlib import Path

import bpy
import importlib.util


def _table_package_dir() -> Path:
    # Saved script on disk (recommended).
    fp = globals().get("__file__")
    if fp:
        return Path(fp).resolve().parent
    # Fallback: same folder as the open blend file.
    blend = bpy.data.filepath
    if blend:
        d = Path(blend).resolve().parent / "table"
        if (d / "build_table.py").exists():
            return d
    return Path("/Users/danielku/mywebsite/blender/table")


def _load_build_table():
    path = _table_package_dir() / "build_table.py"
    if not path.is_file():
        raise FileNotFoundError(
            f"Could not find build_table.py at {path}. "
            "Put add_suit_platform.py next to build_table.py, or save your blend under blender/."
        )
    spec = importlib.util.spec_from_file_location("build_table_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TABLE_PART_NAMES = ("Top", "Skirt", "FootBrace", "Leg_1")


def _scene_with_table() -> "bpy.types.Scene | None":
    """The scene whose view layer contains the table parts."""
    for scene in bpy.data.scenes:
        names = {o.name for o in scene.objects}
        if any(n in names for n in TABLE_PART_NAMES):
            return scene
    return None


def _collection_with_table(scene) -> "bpy.types.Collection":
    """A collection inside ``scene`` that holds the table parts (else root)."""
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
    """Make ``scene`` the active scene for window + context (headless-safe)."""
    win = bpy.context.window or (
        bpy.context.window_manager.windows[0]
        if bpy.context.window_manager.windows
        else None
    )
    if win is not None:
        win.scene = scene


def main(save_after: bool | None = None):
    bt = _load_build_table()

    target_scene = _scene_with_table()
    if target_scene is None:
        raise RuntimeError(
            "No scene contains the table objects (Top/Skirt/FootBrace/Leg_*). "
            "Open a blend that has the table built first."
        )
    target_coll = _collection_with_table(target_scene)

    _activate_scene(target_scene)

    # Remove old SuitPlatform from anywhere it currently lives.
    old = bpy.data.objects.get("SuitPlatform")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    # Activate the table's collection so new objects land there.
    layer_coll = _find_layer_collection(
        bpy.context.view_layer.layer_collection, target_coll
    )
    if layer_coll is not None:
        bpy.context.view_layer.active_layer_collection = layer_coll

    before = set(bpy.data.objects)
    bt.build_suit_platform()
    new_objs = [o for o in bpy.data.objects if o not in before]

    # Force every new object into ONLY the table collection.
    for obj in new_objs:
        for c in list(obj.users_collection):
            if c is not target_coll:
                c.objects.unlink(obj)
        if target_coll not in obj.users_collection:
            target_coll.objects.link(obj)

    if save_after is None:
        save_after = os.environ.get("SAVE_BLEND_AFTER", "").lower() in (
            "1",
            "true",
            "yes",
        )
    if save_after and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)

    sp = bpy.data.objects.get("SuitPlatform")
    print(
        "[add_suit_platform] target scene:",
        target_scene.name,
        "| target collection:",
        target_coll.name,
        "| SuitPlatform present:",
        bool(sp),
        "| in scene:",
        sp is not None and sp.name in {o.name for o in target_scene.objects},
    )


if __name__ == "__main__":
    main()
