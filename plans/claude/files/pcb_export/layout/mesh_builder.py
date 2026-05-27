"""
mesh_builder.py
===============

Materializes a layout plan into a 3D scene. Handles:

  1. Picking a specific builder lambda for each placement (random variation
     selection per family)
  2. Translating component meshes to their world positions
  3. Optionally extracting OUTLINE wireframe edges via dihedral-angle filtering
     (so internal triangulation lines are dropped)
  4. Rendering trace-edge tubes with a Tron-blue emissive material

This is the ONLY module in the pipeline that imports trimesh - everything
upstream (planner, family specs) is pure logic.

KEY ALGORITHM - WIREFRAME EXTRACTION
------------------------------------
trimesh stores every mesh as triangles. A rectangular face appears as TWO
triangles joined along a diagonal edge. The naive "all edges" extraction
includes that internal diagonal, which looks like noise.

We use the DIHEDRAL ANGLE between adjacent triangles:
  - If two adjacent triangles are coplanar (angle near 0), they're two halves
    of one flat face -> the edge between them is internal triangulation -> DROP
  - If the angle exceeds a threshold (default 15 deg), it's a real geometric
    crease (edge of the cube, rim of a cylinder, etc.) -> KEEP

This is exactly what trimesh.face_adjacency_angles gives us. The result for
a box: only the 12 perimeter edges. For an octagonal prism: 24 outline edges
(8 top rim + 8 bottom rim + 8 vertical), no fan-cuts across the caps.

USAGE
-----

  >>> from pcb_layout import LayoutPlanner, FamilySpec
  >>> from mesh_builder import build_scene, FAMILY_BUILDERS
  >>>
  >>> planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
  >>> report = planner.plan(families, seed=42)
  >>> build_scene(report, planner, FAMILY_BUILDERS,
  ...             out_path='out.glb',
  ...             wireframe=True)
"""

import os
import sys
import random
import numpy as np
import trimesh
from trimesh import creation, transformations as tf

# Make the component builders importable from a sibling directory
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_COMPONENTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, '..', 'components'))
if _COMPONENTS_DIR not in sys.path:
    sys.path.insert(0, _COMPONENTS_DIR)

from component_builders import ROWS, mat, BOARD_T  # noqa: E402

# ============================================================
# Map family-name (used by layout planner) -> list of builder lambdas
# ============================================================
FAMILY_BUILDERS = {
    'qfp':       dict(ROWS)['QFP / chip ICs'],
    'dip':       dict(ROWS)['DIP ICs'],
    'cap':       dict(ROWS)['Capacitors'],
    'heatsink':  dict(ROWS)['Heatsinks'],
    'octagon':   dict(ROWS)['Octagonal / drum'],
    'header':    dict(ROWS)['Headers / terminals'],
    'connector': dict(ROWS)['Connectors / ports'],
    'smd':       dict(ROWS)['SMD passives / LEDs'],
}

# ============================================================
# Materials - Tron-blue palette, dark base + emissive edges
# ============================================================

BOARD_FACE_MAT = mat([0.005, 0.008, 0.012, 1.0], metallic=0.0, roughness=1.0)
DARK_BASE_MAT  = mat([0.01, 0.01, 0.015, 1.0],  metallic=0.0, roughness=1.0)
EDGE_MAT       = mat([0.35, 0.55, 1.0, 1.0],    metallic=0.0, roughness=0.2,
                     emissive=[0.5, 0.75, 1.0])
BOARD_EDGE_MAT = mat([0.25, 0.4, 0.9, 1.0],     metallic=0.0, roughness=0.2,
                     emissive=[0.3, 0.5, 0.95])


# ============================================================
# Geometry helpers
# ============================================================

def _make_edge_cylinder(p0, p1, radius=0.04, sections=3):
    """Build a thin cylinder mesh going from p0 to p1.

    Used for rendering a 3D line segment as a tube. sections=3 = triangular
    prism (very cheap). p0/p1 are 3-tuples (x, y, z).
    """
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    vec = p1 - p0
    length = np.linalg.norm(vec)
    if length < 1e-6:
        return None
    cyl = creation.cylinder(radius=radius, height=length, sections=sections)
    # rotate from Z-axis (cylinder default) to the vector direction
    z_axis = np.array([0, 0, 1.0])
    direction = vec / length
    cross = np.cross(z_axis, direction)
    dot = float(np.dot(z_axis, direction))
    if np.linalg.norm(cross) < 1e-6:
        R = np.eye(4) if dot > 0 else tf.rotation_matrix(np.pi, [1, 0, 0])
    else:
        axis = cross / np.linalg.norm(cross)
        ang = np.arccos(np.clip(dot, -1, 1))
        R = tf.rotation_matrix(ang, axis)
    cyl.apply_transform(R)
    cyl.apply_translation((p0 + p1) / 2)
    return cyl


def _extract_crease_edges(mesh, length_threshold=0.04, angle_threshold_deg=15):
    """Extract OUTLINE edges from a mesh, dropping internal triangulation.

    Uses dihedral-angle filtering: edges between two triangles whose normals
    are nearly parallel (coplanar) are internal triangulation and are dropped.
    Edges between triangles at a real geometric angle (>= angle_threshold_deg)
    are kept.

    Boundary edges (edges belonging to only one triangle) are also kept as
    a safety net for open meshes.

    Returns: ndarray of shape (n, 2, 3): n edges, each with start/end point.
    """
    if not hasattr(mesh, 'face_adjacency'):
        return np.zeros((0, 2, 3))
    verts = mesh.vertices
    kept = []
    if len(mesh.face_adjacency) > 0:
        angles = mesh.face_adjacency_angles
        adj_edges = mesh.face_adjacency_edges
        crease_mask = angles > np.radians(angle_threshold_deg)
        if crease_mask.any():
            kept.append(verts[adj_edges[crease_mask]])
    # Boundary edges (only-one-triangle edges)
    try:
        boundary_idx = mesh.edges[trimesh.grouping.group_rows(
            np.sort(mesh.edges, axis=1), require_count=1)]
        if len(boundary_idx) > 0:
            kept.append(verts[boundary_idx])
    except Exception:
        pass
    if not kept:
        return np.zeros((0, 2, 3))
    pts = np.concatenate(kept, axis=0)
    lengths = np.linalg.norm(pts[:, 1] - pts[:, 0], axis=1)
    return pts[lengths > length_threshold]


def _dedupe_edges(edges, tol=0.005):
    """Remove duplicate edges (shared between adjacent parts of a component)
    by quantizing endpoint coordinates."""
    if len(edges) == 0:
        return edges
    seen = set()
    out = []
    for s, e in edges:
        a = tuple(np.round(s / tol).astype(int))
        b = tuple(np.round(e / tol).astype(int))
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        out.append((s, e))
    return np.array(out) if out else np.zeros((0, 2, 3))


# ============================================================
# Build a complete scene from a layout plan
# ============================================================

def build_scene(report, planner, family_builders, *,
                out_path: str,
                seed: int = 0,
                wireframe: bool = True,
                edge_radius: float = 0.012,
                board_padding: float = 1.0,
                return_positioned_parts: bool = False):
    """
    Build and export a 3D scene matching the layout plan.

    Parameters
    ----------
    report : LayoutReport
        Output of LayoutPlanner.plan(...)
    planner : LayoutPlanner
        The planner that produced the report (used for grid geometry)
    family_builders : dict
        Maps family name (str) -> list of builder lambdas. Each builder
        produces one component variation when called.
    out_path : str
        File path to write the GLB
    seed : int
        RNG seed for variation choice (which specific builder per placement)
    wireframe : bool
        If True, emit Tron-style edge tubes. If False, emit the original
        solid meshes (good for pin extraction in later phases).
    edge_radius : float
        Thickness of wireframe edge tubes
    board_padding : float
        Extra board area beyond the grid extent (in world units)
    return_positioned_parts : bool
        If True, also return a dict mapping placement index to list of
        positioned trimesh objects. Useful if downstream code needs to
        inspect actual mesh geometry (e.g., to find pin locations).

    Returns
    -------
    scene : trimesh.Scene
    positioned_parts : dict (only if return_positioned_parts=True)
    """
    rng = random.Random(seed)
    scene = trimesh.Scene()

    bw = planner.cols * planner.cell + board_padding * 2
    bd = planner.rows * planner.cell + board_padding * 2
    board = creation.box(extents=[bw, BOARD_T, bd])
    board.visual = trimesh.visual.TextureVisuals(material=BOARD_FACE_MAT)
    scene.add_geometry(board, geom_name='board_face')

    if wireframe:
        # Board edge wireframe - the 12 box edges
        cy, by = BOARD_T/2, -BOARD_T/2
        board_edges = [
            ((-bw/2, cy, -bd/2), ( bw/2, cy, -bd/2)),
            (( bw/2, cy, -bd/2), ( bw/2, cy,  bd/2)),
            (( bw/2, cy,  bd/2), (-bw/2, cy,  bd/2)),
            ((-bw/2, cy,  bd/2), (-bw/2, cy, -bd/2)),
            ((-bw/2, by, -bd/2), ( bw/2, by, -bd/2)),
            (( bw/2, by, -bd/2), ( bw/2, by,  bd/2)),
            (( bw/2, by,  bd/2), (-bw/2, by,  bd/2)),
            ((-bw/2, by,  bd/2), (-bw/2, by, -bd/2)),
            ((-bw/2, by, -bd/2), (-bw/2, cy, -bd/2)),
            (( bw/2, by, -bd/2), ( bw/2, cy, -bd/2)),
            (( bw/2, by,  bd/2), ( bw/2, cy,  bd/2)),
            ((-bw/2, by,  bd/2), (-bw/2, cy,  bd/2)),
        ]
        for (a, b) in board_edges:
            c = _make_edge_cylinder(a, b, radius=0.03)
            if c is not None:
                c.visual = trimesh.visual.TextureVisuals(material=BOARD_EDGE_MAT)
                scene.add_geometry(c)

    # Place each component
    positioned_parts_by_idx = {}
    for idx, placement in enumerate(report.placements):
        builders = family_builders.get(placement.family)
        if not builders:
            continue
        builder = rng.choice(builders)
        parts = builder()

        # Center the parts' AABB at the placement's world_xz
        mins = np.array([np.inf]*3)
        maxs = np.array([-np.inf]*3)
        for p in parts:
            b = p.bounds
            mins = np.minimum(mins, b[0])
            maxs = np.maximum(maxs, b[1])
        ax, az = (mins[0]+maxs[0])/2, (mins[2]+maxs[2])/2
        wx, wz = placement.world_xz
        dx, dz = wx - ax, wz - az

        positioned = []
        for p in parts:
            q = p.copy()
            q.apply_translation([dx, 0, dz])
            positioned.append(q)
        positioned_parts_by_idx[idx] = positioned

        if wireframe:
            # Dark face copy of each part (so the wireframe sits over a shadow,
            # not on the board itself - looks better in renderers)
            for pj, p in enumerate(positioned):
                face = p.copy()
                face.visual = trimesh.visual.TextureVisuals(material=DARK_BASE_MAT)
                scene.add_geometry(face, geom_name=f'c{idx}_p{pj}_face')
            # Aggregate edges across all parts of this component, dedupe,
            # then emit as a single concatenated edge tube
            edges_list = []
            for p in positioned:
                e = _extract_crease_edges(p)
                if len(e):
                    edges_list.append(e)
            if edges_list:
                combined = (np.concatenate(edges_list, axis=0)
                            if len(edges_list) > 1 else edges_list[0])
                combined = _dedupe_edges(combined, tol=0.005)
                pieces = []
                for s, e in combined:
                    cyl = _make_edge_cylinder(s, e, radius=edge_radius,
                                              sections=3)
                    if cyl is not None:
                        pieces.append(cyl)
                if pieces:
                    tube = trimesh.util.concatenate(pieces)
                    tube.visual = trimesh.visual.TextureVisuals(material=EDGE_MAT)
                    scene.add_geometry(tube, geom_name=f'c{idx}_edges')
        else:
            for pj, p in enumerate(positioned):
                scene.add_geometry(p, geom_name=f'c{idx}_p{pj}')

    scene.export(out_path)
    if return_positioned_parts:
        return scene, positioned_parts_by_idx
    return scene
