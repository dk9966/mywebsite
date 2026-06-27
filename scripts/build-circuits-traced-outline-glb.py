#!/usr/bin/env python3
"""Build an outline-only, emissive GLB from circuits-traced.glb with part TronLine paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SRC_GLB = ROOT / "plans/circuit design/circuits-traced.glb"
OUT_GLB = ROOT / "plans/circuit design/circuits-traced-outline.glb"
PUBLIC_GLB = ROOT / "public/models/circuits-traced-outline.glb"

_LAYOUT_DIR = ROOT / "plans/claude/files/pcb_export/layout"
if str(_LAYOUT_DIR) not in sys.path:
    sys.path.insert(0, str(_LAYOUT_DIR))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from mesh_builder import (  # noqa: E402
    _dedupe_edges,
    _extract_crease_edges,
    _make_edge_cylinder,
)
from component_builders import mat  # noqa: E402
from gltf_lines import LineMeshSpec, merge_line_meshes_into_glb  # noqa: E402

EDGE_RADIUS = 0.012
EDGE_MAT = mat([0.35, 0.85, 1.0, 1.0], metallic=0.0, roughness=0.15, emissive=[0.4, 0.95, 1.0])
TRACE_EDGE_MAT = mat([0.55, 0.95, 1.0, 1.0], metallic=0.0, roughness=0.1, emissive=[0.65, 1.0, 1.0])

PART_START = 0.0
PART_END = 8.0
SURFACE_LIFT = 0.003

_PART_INDEX = re.compile(r"_p\d+$")


def world_meshes(scene: trimesh.Scene) -> list[tuple[str, trimesh.Trimesh]]:
    out: list[tuple[str, trimesh.Trimesh]] = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        mesh = scene.geometry[geom_name].copy()
        mesh.apply_transform(transform)
        out.append((geom_name, mesh))
    return out


def component_prefix(geom_name: str) -> str | None:
    if geom_name == "traces":
        return None
    if not _PART_INDEX.search(geom_name):
        return None
    return geom_name.rsplit("_p", 1)[0]


def group_component_meshes(
    scene: trimesh.Scene,
    qfp_bodies: dict[str, trimesh.Trimesh],
) -> dict[str, trimesh.Trimesh]:
    buckets: dict[str, list[trimesh.Trimesh]] = {}
    for geom_name, mesh in world_meshes(scene):
        prefix = component_prefix(geom_name)
        if prefix is None:
            continue
        if not include_part_outline_mesh(geom_name):
            continue
        buckets.setdefault(prefix, []).append(mesh)
    return {prefix: trimesh.util.concatenate(parts) for prefix, parts in buckets.items()}


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


def path_length(chain: list[np.ndarray]) -> float:
    total = 0.0
    for i in range(len(chain) - 1):
        total += float(np.linalg.norm(chain[i + 1] - chain[i]))
    return total


def chain_centroid(chain: list[np.ndarray]) -> np.ndarray:
    return np.asarray(chain, dtype=float).mean(axis=0)


def component_sort_key(prefix: str) -> tuple:
    kind, _, idx = prefix.partition("_")
    kind_rank = 0 if kind == "qfp" else 1
    return (kind_rank, int(idx))


def is_qfp_prefix(prefix: str) -> bool:
    return prefix.startswith("qfp_")


def qfp_body_by_prefix(scene: trimesh.Scene) -> dict[str, trimesh.Trimesh]:
    bodies: dict[str, trimesh.Trimesh] = {}
    for geom_name, mesh in world_meshes(scene):
        prefix = component_prefix(geom_name)
        if prefix is None or not is_qfp_prefix(prefix):
            continue
        if geom_name.endswith("_p0"):
            bodies[prefix] = mesh
    return bodies


def include_part_outline_mesh(geom_name: str) -> bool:
    """QFP outlines use the package body only — no leads or top markings."""
    prefix = component_prefix(geom_name)
    if prefix is None:
        return False
    if is_qfp_prefix(prefix):
        return geom_name.endswith("_p0")
    return True


def collect_outline_edges(
    src_scene: trimesh.Scene,
    qfp_bodies: dict[str, trimesh.Trimesh],
) -> tuple[np.ndarray, np.ndarray]:
    trace_edges: list[np.ndarray] = []
    part_edges: list[np.ndarray] = []

    for geom_name, mesh in world_meshes(src_scene):
        if geom_name == "traces":
            edges = _extract_crease_edges(mesh, length_threshold=0.006, angle_threshold_deg=15)
            if len(edges):
                trace_edges.append(edges)
            continue
        if not include_part_outline_mesh(geom_name):
            continue
        edges = _extract_crease_edges(mesh, length_threshold=0.006, angle_threshold_deg=15)
        if len(edges) == 0:
            continue
        part_edges.append(edges)

    parts = (
        _dedupe_edges(np.concatenate(part_edges, axis=0), tol=0.004)
        if part_edges
        else np.zeros((0, 2, 3))
    )
    traces = (
        _dedupe_edges(np.concatenate(trace_edges, axis=0), tol=0.003)
        if trace_edges
        else np.zeros((0, 2, 3))
    )
    return parts, traces


def part_outline_specs(
    src_scene: trimesh.Scene,
    qfp_bodies: dict[str, trimesh.Trimesh],
) -> list[LineMeshSpec]:
    """One TronLine per chained crease-edge polyline on each placed component."""
    ranked_entries: list[tuple[tuple, list[np.ndarray]]] = []

    for prefix, mesh in sorted(
        group_component_meshes(src_scene, qfp_bodies).items(),
        key=lambda item: component_sort_key(item[0]),
    ):
        edges = _extract_crease_edges(mesh, length_threshold=0.006, angle_threshold_deg=15)
        edges = _dedupe_edges(edges, tol=0.004)
        chains = chain_edges(edges)
        comp_centroid = np.asarray(mesh.centroid, dtype=float)
        for chain in chains:
            ranked_entries.append(
                (
                    (
                        comp_centroid[1],
                        component_sort_key(prefix),
                        -path_length(chain),
                        chain_centroid(chain)[0],
                        chain_centroid(chain)[2],
                    ),
                    chain,
                )
            )

    ranked_entries.sort(key=lambda item: item[0])
    count = len(ranked_entries)
    step = (PART_END - PART_START) / max(1, count - 1) if count > 1 else 0.0

    specs: list[LineMeshSpec] = []
    for order, (_, chain) in enumerate(ranked_entries, start=1):
        delay = PART_START + (order - 1) * step
        pts = np.asarray(chain, dtype=np.float32)
        pts[:, 1] += SURFACE_LIFT
        delay_cs = min(999_999, int(round(delay * 100)))
        sec = delay_cs // 100
        centi = delay_cs % 100
        specs.append(LineMeshSpec(name=f"TronLine_{order:04d}_{sec}_{centi:02d}_part", points=pts))

    return specs


def build_outline_scene(
    src_scene: trimesh.Scene,
    qfp_bodies: dict[str, trimesh.Trimesh],
) -> trimesh.Scene:
    out = trimesh.Scene()
    part_edges, trace_edges = collect_outline_edges(src_scene, qfp_bodies)

    if len(part_edges):
        part_tube = edges_to_tubes(part_edges, EDGE_RADIUS, EDGE_MAT)
        if part_tube is not None:
            out.add_geometry(part_tube, geom_name="outline_parts")

    if len(trace_edges):
        trace_tube = edges_to_tubes(trace_edges, EDGE_RADIUS * 0.85, TRACE_EDGE_MAT)
        if trace_tube is not None:
            out.add_geometry(trace_tube, geom_name="outline_traces")

    return out


def export_with_tron_lines(scene: trimesh.Scene, tron_specs: list[LineMeshSpec]) -> None:
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(OUT_GLB))
    added = merge_line_meshes_into_glb(OUT_GLB, tron_specs, OUT_GLB)
    PUBLIC_GLB.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_GLB.write_bytes(OUT_GLB.read_bytes())
    print(f"  part tron lines appended: {added}")


def main() -> None:
    if not SRC_GLB.is_file():
        raise FileNotFoundError(SRC_GLB)

    src_scene = trimesh.load(SRC_GLB, force="scene")
    qfp_bodies = qfp_body_by_prefix(src_scene)
    scene = build_outline_scene(src_scene, qfp_bodies)
    if not scene.geometry:
        raise RuntimeError("No outline edges were extracted from the source GLB")

    tron_specs = part_outline_specs(src_scene, qfp_bodies)
    export_with_tron_lines(scene, tron_specs)

    geoms = list(scene.geometry.keys())
    combined = trimesh.util.concatenate(list(scene.geometry.values()))
    print(f"Exported {OUT_GLB} ({OUT_GLB.stat().st_size / 1024:.1f} KB)")
    print(f"  public copy: {PUBLIC_GLB}")
    print(f"  geometries: {len(geoms)} ({', '.join(geoms)})")
    print(f"  part tron chains: {len(tron_specs)}")
    print(f"  vertices: {len(combined.vertices)}")
    print(f"  bounds: {combined.bounds}")


if __name__ == "__main__":
    main()
