#!/usr/bin/env python3
"""Rectify scanned circuit polylines to strict 0/45/90/135 degree segments.

Pipeline:
  drop tiny stubs at free endpoints (stroke caps the tracer mistook for diagonals)
  -> cluster near-duplicate junction points across polylines (keeps the net connected)
  -> classify each segment to its nearest 45-degree direction
  -> global least squares: move points minimally so every segment is exactly on axis
  -> integer snap + local repair so constraints hold exactly in integer coords
  -> drop collinear midpoints, rewrite JSON, render PNG
  (render trims diagonal caps at junctions so branch end caps don't poke past lines)
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from trace_circuits import render

JSON_PATH = Path("plans/circuit design/circuits-traced.json")
REF_PNG = Path("plans/circuit design/circuits-traced.png")
OUT_PNG = Path("plans/circuit design/circuits-traced-refined.png")

MERGE_RADIUS = 3.0
STUB_MAX = 6.0


def drop_stubs(lines: list[list[list[int]]]) -> list[list[list[int]]]:
    """Remove short first/last segments whose free endpoint touches nothing else.

    The reference image draws lines with rounded caps; the skeleton tracer turns
    those caps into 3-5px diagonal hooks at line ends. Junction endpoints (near
    another line's point) are kept so connectivity is untouched.
    """
    out = []
    for i, line in enumerate(lines):
        pts = [tuple(p) for p in line]
        others = [tuple(p) for j, other in enumerate(lines) if j != i for p in other]

        def isolated(p):
            return all(math.dist(p, q) > MERGE_RADIUS for q in others)

        while len(pts) >= 3 and math.dist(pts[0], pts[1]) < STUB_MAX and isolated(pts[0]):
            pts.pop(0)
        while len(pts) >= 3 and math.dist(pts[-1], pts[-2]) < STUB_MAX and isolated(pts[-1]):
            pts.pop()
        out.append([list(p) for p in pts])
    return out


def trim_junction_caps(lines: list[list[list[int]]]) -> list[list[tuple[int, int]]]:
    """Pull diagonal endpoints at junctions back 1px, for rendering only.

    A width-2 diagonal stroke has square end caps whose corners land 1px past
    the endpoint perpendicular to the stroke, poking out above/below the line
    the branch meets. Retracting the drawn endpoint one step along the diagonal
    keeps the joint covered (the through line's stroke fills the junction px)
    without the overshoot. JSON coordinates are not affected.
    """
    counts = Counter(tuple(p) for line in lines for p in line)
    out = []
    for line in lines:
        pts = [tuple(p) for p in line]
        for end, nb in ((0, 1), (-1, -2)):
            p, q = pts[end], pts[nb]
            dx, dy = q[0] - p[0], q[1] - p[1]
            if counts[p] >= 2 and dx != 0 and dy != 0:
                pts[end] = (p[0] + (1 if dx > 0 else -1), p[1] + (1 if dy > 0 else -1))
        out.append(pts)
    return out


def cluster_points(points: list[tuple[float, float]]) -> list[int]:
    """Union-find over all points; points within MERGE_RADIUS share a cluster."""
    parent = list(range(len(points)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if math.dist(points[i], points[j]) <= MERGE_RADIUS:
                parent[find(i)] = find(j)
    return [find(i) for i in range(len(points))]


def segment_class(a: tuple[float, float], b: tuple[float, float]) -> int:
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
    return round(ang / 45.0) % 4 * 45


def violation(pa, pb, cls) -> float:
    """Signed distance of the segment vector from its target direction (normal dot)."""
    dx, dy = pb[0] - pa[0], pb[1] - pa[1]
    if cls == 0:
        return dy
    if cls == 90:
        return dx
    if cls == 45:
        return dy - dx
    return dy + dx  # 135


def solve_least_squares(pts: np.ndarray, segs: list[tuple[int, int, int]]) -> np.ndarray:
    """Minimal-norm point correction so every segment lies exactly on its axis."""
    n = len(pts)
    rows = []
    for a, b, cls in segs:
        row = np.zeros(2 * n)
        if cls == 0:
            row[2 * a + 1], row[2 * b + 1] = -1, 1
        elif cls == 90:
            row[2 * a], row[2 * b] = -1, 1
        elif cls == 45:
            row[2 * a], row[2 * a + 1] = 1, -1
            row[2 * b], row[2 * b + 1] = -1, 1
        else:  # 135
            row[2 * a], row[2 * a + 1] = -1, -1
            row[2 * b], row[2 * b + 1] = 1, 1
        rows.append(row)
    A = np.array(rows)
    p0 = pts.flatten()
    delta, *_ = np.linalg.lstsq(A, A @ p0, rcond=None)
    return (p0 - delta).reshape(-1, 2)


def repair_integers(pts: np.ndarray, segs: list[tuple[int, int, int]]) -> np.ndarray:
    """Round to ints, then nudge points by +-1 until every constraint is exact."""
    p = np.rint(pts).astype(int)
    incident: dict[int, list[tuple[int, int, int]]] = {}
    for seg in segs:
        incident.setdefault(seg[0], []).append(seg)
        incident.setdefault(seg[1], []).append(seg)

    def point_cost(i):
        return sum(abs(violation(p[a], p[b], cls)) for a, b, cls in incident.get(i, []))

    for _ in range(50):
        total = sum(abs(violation(p[a], p[b], cls)) for a, b, cls in segs)
        if total == 0:
            break
        for i in range(len(p)):
            if point_cost(i) == 0:
                continue
            best, best_cost = (0, 0), point_cost(i)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    p[i] += (ox, oy)
                    c = point_cost(i)
                    p[i] -= (ox, oy)
                    if c < best_cost:
                        best, best_cost = (ox, oy), c
            p[i] += best
    return p


def simplify(line: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Drop repeated points and collinear midpoints."""
    out = [line[0]]
    for pt in line[1:]:
        if pt != out[-1]:
            out.append(pt)
    i = 1
    while i < len(out) - 1:
        if segment_class(out[i - 1], out[i]) == segment_class(out[i], out[i + 1]) and violation(
            out[i - 1], out[i + 1], segment_class(out[i - 1], out[i])
        ) == 0:
            out.pop(i)
        else:
            i += 1
    return out


def main():
    payload = json.loads(JSON_PATH.read_text())
    lines = drop_stubs(payload["lines"])

    flat = [tuple(p) for line in lines for p in line]
    roots = cluster_points(flat)
    # One shared variable per cluster; cluster position = mean of its members.
    root_ids = sorted(set(roots))
    index_of = {r: i for i, r in enumerate(root_ids)}
    point_idx = [index_of[r] for r in roots]
    sums = np.zeros((len(root_ids), 2))
    counts = np.zeros(len(root_ids))
    for k, pt in enumerate(flat):
        sums[point_idx[k]] += pt
        counts[point_idx[k]] += 1
    pts = sums / counts[:, None]

    # Polylines as cluster indices; classify segments from original geometry.
    idx_lines = []
    cursor = 0
    for line in lines:
        idx_lines.append(point_idx[cursor : cursor + len(line)])
        cursor += len(line)

    seg_set = {}
    for line, idx_line in zip(lines, idx_lines):
        for (pa, pb), (a, b) in zip(zip(line, line[1:]), zip(idx_line, idx_line[1:])):
            if a == b:
                continue
            key = (min(a, b), max(a, b))
            if key not in seg_set:
                cls = segment_class(pa, pb) if a < b else segment_class(pb, pa)
                seg_set[key] = (key[0], key[1], cls)
    segs = list(seg_set.values())

    solved = solve_least_squares(pts, segs)
    snapped = repair_integers(solved, segs)

    residual = sum(abs(violation(snapped[a], snapped[b], cls)) for a, b, cls in segs)
    max_move = max(math.dist(flat[k], snapped[point_idx[k]]) for k in range(len(flat)))

    new_lines = []
    for idx_line in idx_lines:
        line = simplify([tuple(map(int, snapped[i])) for i in idx_line])
        if len(line) >= 2:
            new_lines.append([list(p) for p in line])

    payload["lines"] = new_lines
    JSON_PATH.write_text(json.dumps(payload, indent=2))

    size = Image.open(REF_PNG).size
    render(trim_junction_caps(new_lines), payload["boxes"], size).save(OUT_PNG)

    print(f"clusters: {len(root_ids)} (from {len(flat)} points)")
    print(f"segments: {len(segs)}, residual after snap: {residual}")
    print(f"max point move: {max_move:.2f}px")
    print(f"wrote {JSON_PATH}")
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
