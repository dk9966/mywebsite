"""Render the painter trace mesh in isolation (no components, no board edges)
so the wire pattern is unambiguous. Reads the saved main.blend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from build_painter_traces import (  # noqa: E402
    COLL_TRACES,
    TRACE_PREFIX,
    render_still,
    setup_camera,
    split_board_and_components,
)
from import_claude_pcb import COLL_COMPONENTS, SCENE_NAME  # noqa: E402


def main() -> int:
    scene = bpy.data.scenes.get(SCENE_NAME)
    if scene is None:
        print("FAIL: missing scene", SCENE_NAME)
        return 1
    bpy.context.window.scene = scene

    coll_components = bpy.data.collections.get(COLL_COMPONENTS)
    coll_traces = bpy.data.collections.get(COLL_TRACES)

    trace_obs = [o for o in coll_traces.objects if o.name.startswith(TRACE_PREFIX)]
    if not trace_obs:
        print("FAIL: no trace objects")
        return 1

    (_, lo, hi), _ = split_board_and_components(coll_components)

    # Temporarily unlink the components collection from the scene so they
    # don't render (cleaner than per-object hide_render in headless mode).
    was_linked = COLL_COMPONENTS in scene.collection.children.keys()
    if was_linked:
        scene.collection.children.unlink(coll_components)
    bpy.context.view_layer.update()
    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)

    cam = setup_camera(scene, lo, hi, name="PainterPCB_Cam_TopOnly")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = span * 1.05
    cam.location = center + Vector((0.0, 0.0, span * 1.2))
    cam.rotation_euler = (0.0, 0.0, 0.0)

    out = os.path.join(_HERE, "renders", "painter-pcb-wires-only-top.png")
    render_still(scene, out, cam)
    print(f"[painter-only] -> {out}")

    if was_linked:
        scene.collection.children.link(coll_components)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
