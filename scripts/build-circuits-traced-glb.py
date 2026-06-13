#!/usr/bin/env python3
"""Build a GLB from circuits-traced.json with reference QFPs, heatsinks, and metal traces."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
from trimesh import creation, transformations as tf

ROOT = Path(__file__).resolve().parents[1]
TRACED_JSON = ROOT / "plans/circuit design/circuits-traced.json"
REF_GLB = ROOT / "plans/claude/files/component_reference.glb"
OUT_GLB = ROOT / "plans/circuit design/circuits-traced.glb"

COMPONENTS_DIR = ROOT / "plans/claude/files/pcb_export/components"
if str(COMPONENTS_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENTS_DIR))

from component_builders import BOARD_MAT, BOARD_T, ROWS, mat  # noqa: E402

PAD_CELLS = 6
CELL_PX = 9
BOARD_WORLD_W = 58.0
TRACE_RADIUS = 0.022
TRACE_Y = BOARD_T / 2 + TRACE_RADIUS

# Row/col indices in component_reference.glb (r0 = QFP, r3 = Heatsinks).
QFP_COLS = [0, 5, 1, 11, 12]
HS_COLS = [0, 7]

QFP_BUILDERS = ROWS[0][1]
HS_BUILDERS = ROWS[3][1]

TRACE_MAT = mat([0.62, 0.64, 0.66, 1.0], metallic=0.95, roughness=0.28)

_PART_INDEX = re.compile(r"_p(\d+)$")


def content_bounds(lines, boxes, pad_px: float) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    for line in lines:
        for x, y in line:
            xs.append(x)
            ys.append(y)
    for color in boxes.values():
        for box in color:
            xs.extend([box["x"], box["x"] + box["w"]])
            ys.extend([box["y"], box["y"] + box["h"]])
    return {
        "min_x": min(xs) - pad_px,
        "min_y": min(ys) - pad_px,
        "max_x": max(xs) + pad_px,
        "max_y": max(ys) + pad_px,
    }


def px_to_world(px: float, py: float, offset_x: float, offset_y: float, scale: float) -> tuple[float, float]:
    return (px - offset_x) * scale, (py - offset_y) * scale


def copy_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    out = mesh.copy()
    if hasattr(mesh.visual, "copy"):
        out.visual = mesh.visual.copy()
    return out


def part_index(geom_name: str) -> int:
    match = _PART_INDEX.search(geom_name)
    if not match:
        raise ValueError(f"Could not parse part index from {geom_name!r}")
    return int(match.group(1))


def extract_component(scene: trimesh.Scene, prefix: str) -> list[trimesh.Trimesh]:
    """Pull one reference-sheet instance from component_reference.glb."""
    boundary = f"{prefix}_p"
    indexed: list[tuple[int, trimesh.Trimesh]] = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        if not geom_name.startswith(boundary):
            continue
        # Avoid c1 matching c10/c11/etc.
        suffix = geom_name[len(prefix) :]
        if not _PART_INDEX.fullmatch(suffix):
            continue
        mesh = scene.geometry[geom_name].copy()
        mesh.apply_transform(transform)
        indexed.append((part_index(geom_name), mesh))
    if not indexed:
        raise ValueError(f"No geometry matched prefix {prefix!r}")
    indexed.sort(key=lambda item: item[0])
    return [mesh for _, mesh in indexed]


def build_component_parts(builder) -> list[trimesh.Trimesh]:
    """Instantiate the same meshes used when building component_reference.glb."""
    return [copy_mesh(part) for part in builder()]


def normalize_component(
    parts: list[trimesh.Trimesh],
) -> tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]:
    combined = trimesh.util.concatenate([copy_mesh(p) for p in parts])
    bounds = combined.bounds
    cx = (bounds[0, 0] + bounds[1, 0]) * 0.5
    cz = (bounds[0, 2] + bounds[1, 2]) * 0.5
    by = bounds[0, 1]
    offset = np.array([-cx, -by, -cz])
    return [copy_mesh(p) for p in parts], offset, combined.extents


def scale_parts(
    parts: list[trimesh.Trimesh],
    offset: np.ndarray,
    mesh_extents: np.ndarray,
    target_w: float,
    target_d: float,
) -> list[trimesh.Trimesh]:
    mesh_w = max(mesh_extents[0], 1e-6)
    mesh_d = max(mesh_extents[2], 1e-6)
    s = min(target_w / mesh_w, target_d / mesh_d)
    out: list[trimesh.Trimesh] = []
    for part in parts:
        mesh = copy_mesh(part)
        mesh.apply_translation(offset)
        mesh.apply_scale([s, 1.0, s])
        out.append(mesh)
    return out


def place_parts(parts: list[trimesh.Trimesh], wx: float, wz: float) -> list[trimesh.Trimesh]:
    placed: list[trimesh.Trimesh] = []
    for part in parts:
        mesh = copy_mesh(part)
        mesh.apply_translation([wx, 0.0, wz])
        placed.append(mesh)
    return placed


def make_trace_segment(p0: tuple[float, float], p1: tuple[float, float], radius: float) -> trimesh.Trimesh | None:
    a = np.array([p0[0], TRACE_Y, p0[1]], dtype=float)
    b = np.array([p1[0], TRACE_Y, p1[1]], dtype=float)
    vec = b - a
    length = float(np.linalg.norm(vec))
    if length < 1e-6:
        return None
    cyl = creation.cylinder(radius=radius, height=length, sections=8)
    direction = vec / length
    # trimesh cylinders are built with their axis along +Z.
    z_axis = np.array([0.0, 0.0, 1.0])
    cross = np.cross(z_axis, direction)
    dot = float(np.dot(z_axis, direction))
    if np.linalg.norm(cross) < 1e-6:
        rot = np.eye(4) if dot > 0 else tf.rotation_matrix(np.pi, [1.0, 0.0, 0.0])
    else:
        axis = cross / np.linalg.norm(cross)
        ang = np.arccos(np.clip(dot, -1.0, 1.0))
        rot = tf.rotation_matrix(ang, axis)
    cyl.apply_transform(rot)
    cyl.apply_translation((a + b) * 0.5)
    cyl.visual = trimesh.visual.TextureVisuals(material=TRACE_MAT)
    return cyl


def load_reference_templates(
    ref_scene: trimesh.Scene,
) -> tuple[
    dict[int, tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]],
    dict[int, tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]],
]:
    """Load QFP/heatsink templates and verify they match component_reference.glb."""
    qfp_cache: dict[int, tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]] = {}
    hs_cache: dict[int, tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]] = {}

    for col, builder in enumerate(QFP_BUILDERS):
        built = build_component_parts(builder)
        glb = extract_component(ref_scene, f"r0_QFP__chip_ICs_c{col}")
        if len(built) != len(glb):
            raise ValueError(f"QFP col {col}: builder parts {len(built)} != GLB parts {len(glb)}")
        if sum(len(p.vertices) for p in built) != sum(len(p.vertices) for p in glb):
            raise ValueError(f"QFP col {col}: builder vertex count does not match GLB")
        qfp_cache[col] = normalize_component(built)

    for col, builder in enumerate(HS_BUILDERS):
        built = build_component_parts(builder)
        glb = extract_component(ref_scene, f"r3_Heatsinks_c{col}")
        if len(built) != len(glb):
            raise ValueError(f"Heatsink col {col}: builder parts {len(built)} != GLB parts {len(glb)}")
        if sum(len(p.vertices) for p in built) != sum(len(p.vertices) for p in glb):
            raise ValueError(f"Heatsink col {col}: builder vertex count does not match GLB")
        hs_cache[col] = normalize_component(built)

    return qfp_cache, hs_cache


def build_scene() -> trimesh.Scene:
    traced = json.loads(TRACED_JSON.read_text())
    lines = traced["lines"]
    boxes = traced["boxes"]

    pad_px = PAD_CELLS * CELL_PX
    bounds = content_bounds(lines, boxes, pad_px)
    content_w = bounds["max_x"] - bounds["min_x"]
    content_h = bounds["max_y"] - bounds["min_y"]
    scale = BOARD_WORLD_W / content_w
    board_d = content_h * scale

    ref_scene = trimesh.load(REF_GLB, force="scene")
    qfp_cache, hs_cache = load_reference_templates(ref_scene)

    scene = trimesh.Scene()
    board = creation.box(extents=[BOARD_WORLD_W, BOARD_T, board_d])
    board.apply_translation([BOARD_WORLD_W * 0.5, -BOARD_T / 2, board_d * 0.5])
    board.visual = trimesh.visual.TextureVisuals(material=BOARD_MAT)
    scene.add_geometry(board, geom_name="board")

    for i, box in enumerate(boxes["green"]):
        col = QFP_COLS[i % len(QFP_COLS)]
        parts, offset, extents = qfp_cache[col]
        wx, wz = px_to_world(box["cx"], box["cy"], bounds["min_x"], bounds["min_y"], scale)
        target_w = box["w"] * scale
        target_d = box["h"] * scale
        scaled = scale_parts(parts, offset, extents, target_w, target_d)
        for j, mesh in enumerate(place_parts(scaled, wx, wz)):
            scene.add_geometry(mesh, geom_name=f"qfp_{i}_p{j}")

    for i, box in enumerate(boxes["pink"]):
        col = HS_COLS[i % len(HS_COLS)]
        parts, offset, extents = hs_cache[col]
        wx, wz = px_to_world(box["cx"], box["cy"], bounds["min_x"], bounds["min_y"], scale)
        target_w = box["w"] * scale
        target_d = box["h"] * scale
        scaled = scale_parts(parts, offset, extents, target_w, target_d)
        for j, mesh in enumerate(place_parts(scaled, wx, wz)):
            scene.add_geometry(mesh, geom_name=f"heatsink_{i}_p{j}")

    trace_pieces: list[trimesh.Trimesh] = []
    for line in lines:
        for a, b in zip(line, line[1:]):
            p0 = px_to_world(a[0], a[1], bounds["min_x"], bounds["min_y"], scale)
            p1 = px_to_world(b[0], b[1], bounds["min_x"], bounds["min_y"], scale)
            seg = make_trace_segment(p0, p1, TRACE_RADIUS)
            if seg is not None:
                trace_pieces.append(seg)
    if trace_pieces:
        traces = trimesh.util.concatenate(trace_pieces)
        scene.add_geometry(traces, geom_name="traces")

    return scene


def main() -> None:
    if not TRACED_JSON.is_file():
        raise FileNotFoundError(TRACED_JSON)
    if not REF_GLB.is_file():
        raise FileNotFoundError(REF_GLB)

    scene = build_scene()
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(OUT_GLB))

    geoms = list(scene.geometry.keys())
    print(f"Exported {OUT_GLB} ({OUT_GLB.stat().st_size / 1024:.1f} KB)")
    print(f"  geometries: {len(geoms)}")
    print(f"  qfp cols: {QFP_COLS}")
    print(f"  heatsink cols: {HS_COLS}")
    print(f"  sample names: {[g for g in geoms if g != 'board'][:12]}...")


if __name__ == "__main__":
    main()
