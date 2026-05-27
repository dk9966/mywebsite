"""Project refined PCB line art onto ``random_pcb.glb``.

Modes (``TRACE_SOURCE`` env, default ``texture``):

  texture — emissive image plane on the board bbox (pixel copy of the PNG).
  svg     — 3D boxes along paths from ``output/traces.svg`` (vectorize pipeline).
  hough   — legacy Hough segments in ``blender/data/image_lines.json``.

Run::

    SAVE_BLEND_AFTER=1 /Applications/Blender.app/Contents/MacOS/Blender \\
      --background blender/main.blend \\
      --python blender/build_traces_from_image.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from import_claude_pcb import (  # noqa: E402
    SCENE_NAME,
    coll_ensure,
    ensure_scene,
    import_glb,
)
from build_claude_circuit_traces import (  # noqa: E402
    COLL_TRACES,
    TRACE_PREFIX,
    ensure_trace_material,
    purge_traces,
    render_still,
    retint_claude_materials,
    setup_camera,
    setup_world,
)

_REPO = Path(__file__).resolve().parents[1]
REFINED_PNG = (
    _REPO
    / "plans/chatgpt/refined lines - ChatGPT Image May 23, 2026, 09_26_21 PM.png"
)
TRACES_SVG = _REPO / "output/traces.svg"
LINES_JSON = Path(__file__).resolve().parent / "data" / "image_lines.json"

BOARD_TOP_Z = 1.52
TRACE_WIDTH = 0.028
TRACE_HEIGHT = 0.012
MIN_SEGMENT_WORLD = 0.08

SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def _source_mode() -> str:
    return os.environ.get("TRACE_SOURCE", "texture").strip().lower()


def _hide_components(hide: bool) -> None:
    coll = bpy.data.collections.get("ClaudePCB_Components")
    if not coll:
        return
    for ob in coll.objects:
        if ob.type == "MESH":
            ob.hide_render = hide
            ob.hide_viewport = hide


def _purge_trace_overlay() -> None:
    for name in (f"{TRACE_PREFIX}image_lines", f"{TRACE_PREFIX}refined_texture"):
        ob = bpy.data.objects.get(name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    for mesh_name in (
        f"{TRACE_PREFIX}image_lines_mesh",
        f"{TRACE_PREFIX}refined_texture_mesh",
    ):
        mesh = bpy.data.meshes.get(mesh_name)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    mat = bpy.data.materials.get("ClaudePCB_RefinedLinesTexture")
    if mat and mat.users == 0:
        bpy.data.materials.remove(mat)


def _pixel_to_world_segments(
    image_size: tuple[int, int],
    segments_px: list[tuple[float, float, float, float]],
    bbox_lo: Vector,
    bbox_hi: Vector,
) -> list[tuple[float, float, float, float]]:
    w_img, h_img = image_size
    x_lo, x_hi = bbox_lo.x, bbox_hi.x
    y_lo, y_hi = bbox_lo.y, bbox_hi.y

    def map_x(px: float) -> float:
        return x_lo + (px / w_img) * (x_hi - x_lo)

    def map_y(py: float) -> float:
        return y_hi - (py / h_img) * (y_hi - y_lo)

    out: list[tuple[float, float, float, float]] = []
    for x1, y1, x2, y2 in segments_px:
        wx1, wy1 = map_x(x1), map_y(y1)
        wx2, wy2 = map_x(x2), map_y(y2)
        if math.hypot(wx2 - wx1, wy2 - wy1) < MIN_SEGMENT_WORLD:
            continue
        out.append((wx1, wy1, wx2, wy2))
    return out


def _parse_path_d(d: str) -> list[tuple[float, float]]:
    """Parse simple M/L SVG path commands into (x, y) points."""
    tokens = re.findall(r"[ML]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", d)
    pts: list[tuple[float, float]] = []
    i = 0
    cmd = "M"
    while i < len(tokens):
        t = tokens[i]
        if t in ("M", "L"):
            cmd = t
            i += 1
            continue
        if i + 1 >= len(tokens):
            break
        x, y = float(tokens[i]), float(tokens[i + 1])
        pts.append((x, y))
        i += 2
        cmd = "L"
    return pts


def _load_svg_segments(svg_path: Path) -> tuple[tuple[int, int], list[tuple[float, float, float, float]]]:
    root = ET.parse(svg_path).getroot()
    view_box = root.get("viewBox", "")
    if view_box:
        parts = view_box.split()
        w, h = int(float(parts[2])), int(float(parts[3]))
    else:
        w = int(root.get("width", "0"))
        h = int(root.get("height", "0"))
    segments: list[tuple[float, float, float, float]] = []
    for el in root.findall(".//svg:path", SVG_NS):
        pts = _parse_path_d(el.get("d", ""))
        for j in range(len(pts) - 1):
            x0, y0 = pts[j]
            x1, y1 = pts[j + 1]
            if x0 != x1 or y0 != y1:
                segments.append((x0, y0, x1, y1))
    return (w, h), segments


def _load_hough_segments() -> tuple[tuple[int, int], list[tuple[float, float, float, float]]]:
    payload = json.loads(LINES_JSON.read_text(encoding="utf-8"))
    w, h = payload["image_size"]
    raw = payload["segments"]
    return (int(w), int(h)), [(float(a), float(b), float(c), float(d)) for a, b, c, d in raw]


def _add_trace_box(
    bm: bmesh.types.BMesh,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> None:
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-5:
        return
    mid = Vector(((x0 + x1) * 0.5, (y0 + y1) * 0.5, BOARD_TOP_Z))
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:]
    bmesh.ops.scale(bm, vec=(length, TRACE_WIDTH, TRACE_HEIGHT), verts=verts)
    angle = math.atan2(dy, dx)
    bmesh.ops.rotate(
        bm,
        cent=(0.0, 0.0, 0.0),
        matrix=Matrix.Rotation(angle, 3, "Z"),
        verts=verts,
    )
    bmesh.ops.translate(bm, vec=mid, verts=verts)


def _build_segment_mesh(
    segments: list[tuple[float, float, float, float]],
    coll: bpy.types.Collection,
    mat: bpy.types.Material,
) -> tuple[bpy.types.Object, int]:
    bm = bmesh.new()
    for seg in segments:
        _add_trace_box(bm, *seg)
    mesh = bpy.data.meshes.new(f"{TRACE_PREFIX}image_lines_mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    ob = bpy.data.objects.new(f"{TRACE_PREFIX}image_lines", mesh)
    coll.objects.link(ob)
    ob.data.materials.append(mat)
    return ob, len(segments)


def _build_texture_plane(
    image_path: Path,
    bbox_lo: Vector,
    bbox_hi: Vector,
    coll: bpy.types.Collection,
) -> bpy.types.Object:
    width = bbox_hi.x - bbox_lo.x
    height = bbox_hi.y - bbox_lo.y
    cx = (bbox_lo.x + bbox_hi.x) * 0.5
    cy = (bbox_lo.y + bbox_hi.y) * 0.5

    mesh = bpy.data.meshes.new(f"{TRACE_PREFIX}refined_texture_mesh")
    ob = bpy.data.objects.new(f"{TRACE_PREFIX}refined_texture", mesh)
    coll.objects.link(ob)

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bm.to_mesh(mesh)
    bm.free()

    ob.location = (cx, cy, BOARD_TOP_Z)
    ob.scale = (width * 0.5, height * 0.5, 1.0)

    mat = bpy.data.materials.new("ClaudePCB_RefinedLinesTexture")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    transp = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    tex = nodes.new("ShaderNodeTexImage")
    mapping = nodes.new("ShaderNodeMapping")
    coord = nodes.new("ShaderNodeTexCoord")
    to_bw = nodes.new("ShaderNodeRGBToBW")

    img = bpy.data.images.load(str(image_path), check_existing=True)
    tex.image = img
    tex.interpolation = "Closest"
    mapping.inputs["Scale"].default_value = (1.0, -1.0, 1.0)
    mapping.inputs["Location"].default_value = (0.0, 1.0, 0.0)
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(tex.outputs["Color"], to_bw.inputs["Color"])
    emit.inputs["Strength"].default_value = 6.0
    links.new(to_bw.outputs["Val"], mix.inputs["Fac"])
    links.new(transp.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mat.blend_method = "BLEND"
    ob.show_transparent = True
    mat.diffuse_color = (0.0, 0.92, 1.0, 1.0)

    ob.data.materials.append(mat)
    return ob


def build_all() -> dict:
    mode = _source_mode()
    scene = ensure_scene(SCENE_NAME)
    bpy.context.window.scene = scene

    import_stats = import_glb()
    retint_claude_materials()
    purge_traces()
    _purge_trace_overlay()
    coll_tr = coll_ensure(COLL_TRACES, scene)

    lo, hi = import_stats["bbox_lo"], import_stats["bbox_hi"]
    trace_ob: bpy.types.Object | None = None
    segment_count = 0
    image_size: tuple[int, int] | None = None

    if mode == "texture":
        if not REFINED_PNG.is_file():
            raise FileNotFoundError(REFINED_PNG)
        trace_ob = _build_texture_plane(REFINED_PNG, lo, hi, coll_tr)
        img = bpy.data.images.load(str(REFINED_PNG), check_existing=True)
        image_size = (img.size[0], img.size[1])
        hide_components = os.environ.get("HIDE_COMPONENTS", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        _hide_components(hide_components)
    elif mode == "svg":
        if not TRACES_SVG.is_file():
            raise FileNotFoundError(
                f"{TRACES_SVG} missing — run: python3 tools/pcb-trace-vectorize/pipeline.py"
            )
        image_size, segs_px = _load_svg_segments(TRACES_SVG)
        segs_world = _pixel_to_world_segments(image_size, segs_px, lo, hi)
        mat = ensure_trace_material()
        trace_ob, segment_count = _build_segment_mesh(segs_world, coll_tr, mat)
    elif mode == "hough":
        if not LINES_JSON.is_file():
            raise FileNotFoundError(
                f"{LINES_JSON} missing — run: python3 tools/image-trace/extract_lines.py"
            )
        image_size, segs_px = _load_hough_segments()
        segs_world = _pixel_to_world_segments(image_size, segs_px, lo, hi)
        mat = ensure_trace_material()
        trace_ob, segment_count = _build_segment_mesh(segs_world, coll_tr, mat)
    else:
        raise ValueError(f"unknown TRACE_SOURCE={mode!r} (texture|svg|hough)")

    setup_world(scene)
    cam = setup_camera(scene, lo, hi)
    bpy.context.view_layer.update()

    return {
        "scene": scene,
        "mode": mode,
        "image_size": image_size,
        "import": import_stats,
        "segment_count": segment_count,
        "trace_object": trace_ob,
        "camera": cam,
        "bbox_lo": lo,
        "bbox_hi": hi,
    }


if __name__ == "__main__":
    stats = build_all()
    lo, hi = stats["bbox_lo"], stats["bbox_hi"]
    print(f"[traces_from_image] mode={stats['mode']}")
    if stats["image_size"]:
        print(f"[traces_from_image] image={stats['image_size'][0]}x{stats['image_size'][1]}")
    if stats["mode"] != "texture":
        print(f"[traces_from_image] segments_placed={stats['segment_count']}")

    out_dir = os.path.join(_script_dir, "renders")
    ref_path = os.path.join(out_dir, "claude-pcb-image-traces-ref.png")
    render_still(stats["scene"], ref_path, stats["camera"])
    print(f"[traces_from_image] render -> {ref_path}")

    center = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.y - lo.y, 10.0)
    top_cam = setup_camera(
        stats["scene"], lo, hi, name="ClaudePCB_Cam_Top_ImageLines"
    )
    top_cam.data.type = "ORTHO"
    top_cam.data.ortho_scale = span * 1.05
    top_cam.location = center + Vector((0.0, 0.0, span * 1.2))
    top_cam.rotation_euler = (0.0, 0.0, 0.0)
    top_path = os.path.join(out_dir, "claude-pcb-image-traces-top.png")
    render_still(stats["scene"], top_path, top_cam)
    print(f"[traces_from_image] render -> {top_path}")

    if os.environ.get("SAVE_BLEND_AFTER", "").lower() in ("1", "true", "yes") and bpy.data.filepath:
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print("[traces_from_image] saved main.blend")
