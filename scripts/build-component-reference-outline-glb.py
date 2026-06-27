#!/usr/bin/env python3
"""Build outline-only TronLine GLB from component_reference.glb (pins omitted)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SRC_GLB = ROOT / "plans/claude/files/component_reference.glb"
OUT_GLB = ROOT / "plans/claude/files/component_reference-outline.glb"
PUBLIC_GLB = ROOT / "public/models/component-reference-outline.glb"

_LAYOUT_DIR = ROOT / "plans/claude/files/pcb_export/layout"
if str(_LAYOUT_DIR) not in sys.path:
    sys.path.insert(0, str(_LAYOUT_DIR))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from mesh_builder import _dedupe_edges, _extract_crease_edges, _make_edge_cylinder  # noqa: E402
from component_builders import mat  # noqa: E402
from gltf_lines import LineMeshSpec, merge_line_meshes_into_glb  # noqa: E402

EDGE_RADIUS = 0.012
EDGE_MAT = mat([0.35, 0.85, 1.0, 1.0], metallic=0.0, roughness=0.15, emissive=[0.4, 0.95, 1.0])
SURFACE_LIFT = 0.003

_INSTANCE = re.compile(r"^(r\d+_.+_c\d+)_p(\d+)$")


def world_meshes(scene: trimesh.Scene) -> list[tuple[str, trimesh.Trimesh]]:
    out: list[tuple[str, trimesh.Trimesh]] = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        mesh = scene.geometry[geom_name].copy()
        mesh.apply_transform(transform)
        out.append((geom_name, mesh))
    return out


def instance_prefixes(scene: trimesh.Scene) -> list[str]:
    found: set[str] = set()
    for geom_name, _ in world_meshes(scene):
        match = _INSTANCE.match(geom_name)
        if match:
            found.add(match.group(1))
    return sorted(found)


def parts_for_instance(scene: trimesh.Scene, prefix: str) -> list[tuple[int, trimesh.Trimesh]]:
    parts: list[tuple[int, trimesh.Trimesh]] = []
    for geom_name, mesh in world_meshes(scene):
        match = _INSTANCE.match(geom_name)
        if not match or match.group(1) != prefix:
            continue
        parts.append((int(match.group(2)), mesh))
    parts.sort(key=lambda item: item[0])
    return parts


def is_pin_part(part_idx: int, mesh: trimesh.Trimesh, parts: list[tuple[int, trimesh.Trimesh]]) -> bool:
    """Drop leads and repeated pin arrays; keep bodies, shrouds, and markings."""
    body_idx = max(range(len(parts)), key=lambda i: parts[i][1].volume)
    if part_idx == parts[body_idx][0]:
        return False

    body = parts[body_idx][1]
    bounds = body.bounds
    margin = 0.015
    x0, z0 = bounds[0][0] - margin, bounds[0][2] - margin
    x1, z1 = bounds[1][0] + margin, bounds[1][2] + margin
    cx, cz = mesh.centroid[0], mesh.centroid[2]
    if cx < x0 or cx > x1 or cz < z0 or cz > z1:
        return True

    vol_key = round(float(mesh.volume), 4)
    same_vol = sum(1 for _, m in parts if round(float(m.volume), 4) == vol_key)
    if same_vol >= 4 and mesh.volume < 0.02:
        return True
    return False


def chain_edges(edges_arr: np.ndarray, tol: float = 0.004) -> list[list[np.ndarray]]:
    def quantize(v: np.ndarray) -> tuple[int, int, int]:
        return tuple(np.round(v / tol).astype(int))

    pos_map: dict[tuple[int, int, int], np.ndarray] = {}
    adj: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}

    for pair in edges_arr:
        va = np.asarray(pair[0], dtype=float)
        vb = np.asarray(pair[1], dtype=float)
        ka, kb = quantize(va), quantize(vb)
        if ka == kb:
            continue
        pos_map[ka] = va
        pos_map[kb] = vb
        adj.setdefault(ka, []).append(kb)
        adj.setdefault(kb, []).append(ka)

    visited: set[tuple[tuple[int, int, int], tuple[int, int, int]]] = set()

    def edge_key(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple:
        return (a, b) if a < b else (b, a)

    chains: list[list[np.ndarray]] = []
    endpoints = [k for k, n in adj.items() if len(n) == 1]
    order = endpoints + [k for k in adj if k not in endpoints]

    for start in order:
        while True:
            nbrs = [n for n in adj[start] if edge_key(start, n) not in visited]
            if not nbrs:
                break
            chain = [pos_map[start]]
            cur = start
            while True:
                nbrs = [n for n in adj[cur] if edge_key(cur, n) not in visited]
                if not nbrs:
                    break
                nxt = nbrs[0]
                visited.add(edge_key(cur, nxt))
                chain.append(pos_map[nxt])
                cur = nxt
            if len(chain) >= 2:
                chains.append(chain)

    return chains


def edges_to_tubes(
    edges: np.ndarray,
    radius: float,
    material: trimesh.visual.material.PBRMaterial,
) -> trimesh.Trimesh | None:
    if len(edges) == 0:
        return None
    pieces: list[trimesh.Trimesh] = []
    for start, end in edges:
        cyl = _make_edge_cylinder(start, end, radius=radius, sections=3)
        if cyl is not None:
            pieces.append(cyl)
    if not pieces:
        return None
    tube = trimesh.util.concatenate(pieces)
    tube.visual = trimesh.visual.TextureVisuals(material=material)
    return tube


def outline_meshes_for_parts(parts: list[tuple[int, trimesh.Trimesh]]) -> trimesh.Trimesh | None:
    edges_list: list[np.ndarray] = []
    for part_idx, mesh in parts:
        if is_pin_part(part_idx, mesh, parts):
            continue
        edges = _extract_crease_edges(mesh, length_threshold=0.006, angle_threshold_deg=15)
        if len(edges):
            edges_list.append(edges)
    if not edges_list:
        return None
    combined = np.concatenate(edges_list, axis=0) if len(edges_list) > 1 else edges_list[0]
    combined = _dedupe_edges(combined, tol=0.004)
    return combined


def tron_specs_from_scene(scene: trimesh.Scene) -> list[LineMeshSpec]:
    ranked: list[tuple[tuple, list[np.ndarray]]] = []

    for prefix in instance_prefixes(scene):
        parts = parts_for_instance(scene, prefix)
        edges = outline_meshes_for_parts(parts)
        if edges is None or len(edges) == 0:
            continue
        mesh = trimesh.util.concatenate([m for _, m in parts if not is_pin_part(_, m, parts)])
        centroid = np.asarray(mesh.centroid, dtype=float)
        for chain in chain_edges(edges):
            length = sum(
                float(np.linalg.norm(chain[i + 1] - chain[i]))
                for i in range(len(chain) - 1)
            )
            ranked.append(((centroid[1], prefix, -length), chain))

    # Board outline (single mesh, no pins).
    for geom_name, mesh in world_meshes(scene):
        if geom_name != "board":
            continue
        edges = _extract_crease_edges(mesh, length_threshold=0.02, angle_threshold_deg=15)
        edges = _dedupe_edges(edges, tol=0.004)
        for chain in chain_edges(edges):
            ranked.append(((mesh.centroid[1] - 1.0, "board", 0.0), chain))

    ranked.sort(key=lambda item: item[0])

    specs: list[LineMeshSpec] = []
    for order, (_, chain) in enumerate(ranked, start=1):
        pts = np.asarray(chain, dtype=np.float32)
        pts[:, 1] += SURFACE_LIFT
        specs.append(LineMeshSpec(name=f"TronLine_{order:04d}_0_00_part", points=pts))
    return specs


def build_outline_scene(scene: trimesh.Scene) -> trimesh.Scene:
    out = trimesh.Scene()
    all_edges: list[np.ndarray] = []

    for prefix in instance_prefixes(scene):
        parts = parts_for_instance(scene, prefix)
        edges = outline_meshes_for_parts(parts)
        if edges is not None and len(edges):
            all_edges.append(edges)

    for geom_name, mesh in world_meshes(scene):
        if geom_name != "board":
            continue
        edges = _extract_crease_edges(mesh, length_threshold=0.02, angle_threshold_deg=15)
        if len(edges):
            all_edges.append(edges)

    if not all_edges:
        raise RuntimeError("No outline edges were extracted")

    combined = _dedupe_edges(np.concatenate(all_edges, axis=0), tol=0.004)
    tube = edges_to_tubes(combined, EDGE_RADIUS, EDGE_MAT)
    if tube is not None:
        out.add_geometry(tube, geom_name="outline_parts")
    return out


def main() -> None:
    if not SRC_GLB.is_file():
        raise FileNotFoundError(SRC_GLB)

    src_scene = trimesh.load(SRC_GLB, force="scene")
    scene = build_outline_scene(src_scene)
    tron_specs = tron_specs_from_scene(src_scene)

    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(OUT_GLB))
    added = merge_line_meshes_into_glb(OUT_GLB, tron_specs, OUT_GLB)
    PUBLIC_GLB.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_GLB.write_bytes(OUT_GLB.read_bytes())

    combined = trimesh.util.concatenate(list(scene.geometry.values()))
    print(f"Exported {OUT_GLB} ({OUT_GLB.stat().st_size / 1024:.1f} KB)")
    print(f"  public copy: {PUBLIC_GLB}")
    print(f"  tron line chains: {len(tron_specs)} (merged {added})")
    print(f"  bounds: {combined.bounds}")


if __name__ == "__main__":
    main()
