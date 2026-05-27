"""PCB raster -> clean octilinear vector traces.

Uses a **paired-image diff** (full PCB art minus mesh-only plate) to isolate
trace ink, then Hough line detection on the trace mask. Avoids morphological
opening and skeleton-walking, which destroy 1px routing on AI-generated art.

Run::

    python3 tools/pcb-trace-vectorize/pipeline.py
    python3 tools/pcb-trace-vectorize/pipeline.py --diff-thresh 18 --hough-min-length 10
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PCB = (
    REPO
    / "plans/chatgpt/refined lines - ChatGPT Image May 23, 2026, 09_26_21 PM.png"
)
DEFAULT_MESH = (
    REPO
    / "plans/chatgpt/no lines only meshChatGPT Image May 24, 2026, 11_27_34 AM.png"
)
DEFAULT_OUT_DIR = REPO / "output"

ALLOWED_ANGLES = (0.0, 45.0, 90.0, 135.0)


# ---------------------------------------------------------------------------
# Step 1–2: load + threshold
# ---------------------------------------------------------------------------


def load_grayscale(path: Path) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def threshold_bright(gray: np.ndarray, *, fixed: int = 90) -> np.ndarray:
    """Binary mask: white traces on black background."""
    _, mask = cv2.threshold(gray, fixed, 255, cv2.THRESH_BINARY)
    if cv2.countNonZero(mask) < gray.size * 0.002:
        mask = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            -8,
        )
    return mask


# ---------------------------------------------------------------------------
# Step 3: extract traces from PCB + mesh pair
# ---------------------------------------------------------------------------


def align_mesh(mesh_gray: np.ndarray, pcb_shape: tuple[int, int]) -> np.ndarray:
    h, w = pcb_shape
    if mesh_gray.shape[:2] == (h, w):
        return mesh_gray
    return cv2.resize(mesh_gray, (w, h), interpolation=cv2.INTER_LINEAR)


def _drop_filled_blobs(
    mask: np.ndarray,
    *,
    max_area: int = 2800,
    compact_area: int = 700,
    compact_aspect: float = 2.8,
) -> np.ndarray:
    """Remove large compact blobs left from component fill differences."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        short, long = min(w, h), max(w, h)
        aspect = long / max(short, 1)
        if area > max_area:
            continue
        if area >= compact_area and aspect < compact_aspect:
            continue
        out[labels == i] = 255
    return out


def extract_trace_mask(
    pcb_gray: np.ndarray,
    mesh_gray: np.ndarray,
    *,
    diff_thresh: int = 22,
) -> np.ndarray:
    """Traces = what changed between the full PCB art and the mesh-only plate.

    The mesh image is outline-only; subtracting it from a thresholded PCB
    leaves filled component bodies behind. A brightness diff between the two
    paired renders isolates the trace ink much more reliably.
    """
    mesh_gray = align_mesh(mesh_gray, pcb_gray.shape[:2])
    diff = cv2.absdiff(pcb_gray, mesh_gray)
    _, mask = cv2.threshold(diff, diff_thresh, 255, cv2.THRESH_BINARY)

    # Bridge 1px gaps in trace strokes (do not open — that deletes thin lines).
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)
    return _drop_filled_blobs(mask)


# ---------------------------------------------------------------------------
# Step 4: denoise (speckle only)
# ---------------------------------------------------------------------------


def remove_dense_clusters(mask: np.ndarray) -> np.ndarray:
    """Remove filled pin-field / connector mesh blobs (high fill ratio in bbox)."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        bbox_area = w * h
        fill = area / max(bbox_area, 1)
        aspect = max(w, h) / max(min(w, h), 1)
        if bbox_area < 1600 and fill > 0.32:
            continue
        out[labels == i] = 255
    return out


def suppress_pads(mask: np.ndarray) -> np.ndarray:
    """Drop tiny square pads; keep strokes and long routing."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        short, long = min(w, h), max(w, h)
        aspect = long / max(short, 1)
        ratio = w / max(h, 1)

        if area < 90 and aspect < 4.0:
            continue
        if area < 320 and 0.7 < ratio < 1.45 and aspect < 2.2:
            continue
        out[labels == i] = 255
    return out


def filter_dense_mesh_segments(segments: list[Segment], mask: np.ndarray) -> list[Segment]:
    """Drop short segments sitting inside pin-field / mesh clutter."""
    h, w = mask.shape
    kept: list[Segment] = []
    for s in segments:
        mx = (s.x1 + s.x2) // 2
        my = (s.y1 + s.y2) // 2
        r = 7
        y0, y1 = max(0, my - r), min(h, my + r + 1)
        x0, x1 = max(0, mx - r), min(w, mx + r + 1)
        density = cv2.countNonZero(mask[y0:y1, x0:x1])
        if density > 52 and s.length < 22:
            continue
        kept.append(s)
    return kept


def clean_mask(mask: np.ndarray, *, max_speckle_area: int = 3) -> np.ndarray:
    """Remove isolated pixels only — preserve thin routing."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = mask.copy()
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] <= max_speckle_area:
            out[labels == i] = 0
    return out


# ---------------------------------------------------------------------------
# Step 5: skeletonize (morphological, no ximgproc dependency)
# ---------------------------------------------------------------------------


def skeletonize(mask: np.ndarray) -> np.ndarray:
    skel = np.zeros_like(mask)
    work = mask.copy()
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv2.erode(work, element)
        opened = cv2.dilate(eroded, element)
        ridge = cv2.subtract(work, opened)
        skel = cv2.bitwise_or(skel, ridge)
        work = eroded
        if cv2.countNonZero(work) == 0:
            return skel


# ---------------------------------------------------------------------------
# Step 6–7: Hough line segments + light angle snap
# ---------------------------------------------------------------------------

ALLOWED_DIRS = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)


def hough_segments(
    skel: np.ndarray,
    *,
    threshold: int = 14,
    min_length: int = 12,
    max_gap: int = 8,
) -> list[Segment]:
    lines = cv2.HoughLinesP(
        skel,
        rho=1,
        theta=np.pi / 180.0,
        threshold=threshold,
        minLineLength=min_length,
        maxLineGap=max_gap,
    )
    if lines is None:
        return []
    return [
        Segment(int(x1), int(y1), int(x2), int(y2))
        for x1, y1, x2, y2 in lines[:, 0, :]
    ]


def snap_segment(seg: Segment) -> Segment:
    """Snap segment bearing to nearest octilinear direction."""
    ang = math.degrees(math.atan2(seg.y2 - seg.y1, seg.x2 - seg.x1)) % 360.0
    snap = min(ALLOWED_DIRS, key=lambda a: min(abs(ang - a), 360.0 - abs(ang - a)))
    length = seg.length
    if length < 1e-6:
        return seg
    rad = math.radians(snap)
    x2 = int(round(seg.x1 + length * math.cos(rad)))
    y2 = int(round(seg.y1 + length * math.sin(rad)))
    return Segment(seg.x1, seg.y1, x2, y2)


# ---------------------------------------------------------------------------
# Legacy: skeleton graph walk (unused — kept for experiments)
# ---------------------------------------------------------------------------

NEIGH8 = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


def _neighbors(y: int, x: int, skel: np.ndarray) -> list[tuple[int, int]]:
    h, w = skel.shape
    out: list[tuple[int, int]] = []
    for dy, dx in NEIGH8:
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and skel[ny, nx]:
            out.append((ny, nx))
    return out


def _edge_key(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    return (a, b) if a < b else (b, a)


def trace_polylines(skel: np.ndarray, *, min_points: int = 4) -> list[list[tuple[int, int]]]:
    """Walk the 1px skeleton graph into ordered pixel chains."""
    ys, xs = np.where(skel > 0)
    if len(xs) == 0:
        return []

    h, w = skel.shape
    on = np.zeros((h, w), dtype=np.uint8)
    on[ys, xs] = 1

    degree = np.zeros((h, w), dtype=np.uint8)
    for y, x in zip(ys, xs, strict=True):
        degree[y, x] = len(_neighbors(y, x, on))

    visited_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    polylines: list[list[tuple[int, int]]] = []

    def walk(start: tuple[int, int], nxt: tuple[int, int]) -> list[tuple[int, int]]:
        path = [start, nxt]
        visited_edges.add(_edge_key(start, nxt))
        prev, cur = start, nxt
        while True:
            nbrs = [p for p in _neighbors(cur[0], cur[1], on) if p != prev]
            if not nbrs:
                break
            nxt_pt = None
            for cand in nbrs:
                ek = _edge_key(cur, cand)
                if ek not in visited_edges:
                    nxt_pt = cand
                    break
            if nxt_pt is None:
                break
            visited_edges.add(_edge_key(cur, nxt_pt))
            path.append(nxt_pt)
            prev, cur = cur, nxt_pt
            if degree[cur[0], cur[1]] != 2:
                break
        return path

    # Endpoints and junctions seed branches; degree-2 only appears in loops.
    seeds: list[tuple[int, int]] = []
    for y, x in zip(ys, xs, strict=True):
        d = degree[y, x]
        if d == 1 or d >= 3:
            seeds.append((y, x))

    for sy, sx in seeds:
        for ny, nx in _neighbors(sy, sx, on):
            ek = _edge_key((sy, sx), (ny, nx))
            if ek in visited_edges:
                continue
            chain = walk((sy, sx), (ny, nx))
            if len(chain) >= min_points:
                polylines.append([(c[1], c[0]) for c in chain])  # (x, y)

    # Closed loops (all degree 2).
    for y, x in zip(ys, xs, strict=True):
        if degree[y, x] != 2:
            continue
        if any(_edge_key((y, x), n) in visited_edges for n in _neighbors(y, x, on)):
            continue
        nbrs = _neighbors(y, x, on)
        if not nbrs:
            continue
        chain = walk((y, x), nbrs[0])
        if len(chain) >= min_points:
            polylines.append([(c[1], c[0]) for c in chain])

    return polylines


# ---------------------------------------------------------------------------
# Step 7: Douglas–Peucker + angle snap
# ---------------------------------------------------------------------------


def _perp_dist(pt: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    px, py = pt
    dx, dy = bx - ax, by - ay
    n2 = dx * dx + dy * dy
    if n2 < 1e-9:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def douglas_peucker(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points[:]
    a, b = points[0], points[-1]
    idx, dmax = 0, -1.0
    for i in range(1, len(points) - 1):
        d = _perp_dist(points[i], a, b)
        if d > dmax:
            idx, dmax = i, d
    if dmax > epsilon:
        left = douglas_peucker(points[: idx + 1], epsilon)
        right = douglas_peucker(points[idx:], epsilon)
        return left[:-1] + right
    return [a, b]


def _snap_angle_deg(deg: float) -> float:
    deg = deg % 180.0
    best = ALLOWED_ANGLES[0]
    best_d = 999.0
    for a in ALLOWED_ANGLES:
        d = abs(((deg - a + 90.0) % 180.0) - 90.0)
        if d < best_d:
            best_d, best = d, a
    return best


def _unit_from_angle(deg: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return math.cos(rad), math.sin(rad)


def _line_intersection(
    p: tuple[float, float],
    u: tuple[float, float],
    q: tuple[float, float],
    v: tuple[float, float],
) -> tuple[float, float]:
    px, py = p
    qx, qy = q
    ux, uy = u
    vx, vy = v
    cross = ux * vy - uy * vx
    if abs(cross) < 1e-9:
        return q
    t = ((qx - px) * vy - (qy - py) * vx) / cross
    return (px + t * ux, py + t * uy)


def snap_polyline(points: list[tuple[float, float]]) -> list[tuple[int, int]]:
    if len(points) < 2:
        return [(int(round(x)), int(round(y))) for x, y in points]

    snapped_dirs: list[float] = []
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0
        snapped_dirs.append(_snap_angle_deg(ang))

    out: list[tuple[int, int]] = []
    p0 = (float(points[0][0]), float(points[0][1]))
    out.append((int(round(p0[0])), int(round(p0[1]))))

    for i in range(len(points) - 2):
        u = _unit_from_angle(snapped_dirs[i])
        v = _unit_from_angle(snapped_dirs[i + 1])
        corner = _line_intersection(p0, u, (float(points[i + 1][0]), float(points[i + 1][1])), v)
        out.append((int(round(corner[0])), int(round(corner[1]))))
        p0 = corner

    p_end = (float(points[-1][0]), float(points[-1][1]))
    u_last = _unit_from_angle(snapped_dirs[-1])
    t = (p_end[0] - p0[0]) * u_last[0] + (p_end[1] - p0[1]) * u_last[1]
    last = (p0[0] + t * u_last[0], p0[1] + t * u_last[1])
    out.append((int(round(last[0])), int(round(last[1]))))
    return _merge_collinear(out)


def _merge_collinear(pts: list[tuple[int, int]], angle_eps: float = 4.0) -> list[tuple[int, int]]:
    if len(pts) < 3:
        return pts
    merged = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = merged[-1], pts[i], pts[i + 1]
        ang1 = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
        ang2 = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0])) % 180.0
        if abs(((ang1 - ang2 + 90) % 180) - 90) < angle_eps:
            continue
        merged.append(b)
    merged.append(pts[-1])
    return merged


def simplify_polylines(
    polylines: list[list[tuple[int, int]]],
    *,
    rdp_epsilon: float = 2.5,
    min_seg_len: int = 6,
) -> list[list[tuple[int, int]]]:
    out: list[list[tuple[int, int]]] = []
    for pl in polylines:
        if len(pl) < 2:
            continue
        fp = [(float(x), float(y)) for x, y in pl]
        simp = douglas_peucker(fp, rdp_epsilon)
        snapped = snap_polyline(simp)
        snapped = _merge_collinear(snapped)
        if _polyline_length(snapped) < min_seg_len:
            continue
        if len(snapped) >= 2:
            out.append(snapped)
    return out


def _polyline_length(pts: list[tuple[int, int]]) -> float:
    return sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )


# ---------------------------------------------------------------------------
# Step 8: merge close parallel fragments
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def angle_mod180(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1)) % 180.0


def polylines_to_segments(polylines: list[list[tuple[int, int]]]) -> list[Segment]:
    segs: list[Segment] = []
    for pl in polylines:
        for i in range(len(pl) - 1):
            x0, y0 = pl[i]
            x1, y1 = pl[i + 1]
            if x0 != x1 or y0 != y1:
                segs.append(Segment(x0, y0, x1, y1))
    return segs


def segments_to_polylines(segments: list[Segment]) -> list[list[tuple[int, int]]]:
    return [[(s.x1, s.y1), (s.x2, s.y2)] for s in segments if s.length > 0.5]


def _signed_perp_distance(seg: Segment, px: float, py: float) -> float:
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        return math.hypot(px - seg.x1, py - seg.y1)
    return ((px - seg.x1) * dy - (py - seg.y1) * dx) / norm


def _project_t(seg: Segment, px: float, py: float) -> float:
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    n2 = dx * dx + dy * dy
    if n2 < 1e-6:
        return 0.0
    return ((px - seg.x1) * dx + (py - seg.y1) * dy) / n2


def merge_parallel_segments(
    segs: list[Segment],
    *,
    angle_eps_deg: float = 4.0,
    perp_eps_px: float = 3.0,
    overlap_eps: float = 0.5,
) -> list[Segment]:
    kept: list[Segment] = []
    ordered = sorted(segs, key=lambda s: -s.length)
    for s in ordered:
        merged_into: int | None = None
        for i, k in enumerate(kept):
            d_ang = abs(((s.angle_mod180 - k.angle_mod180) + 90) % 180 - 90)
            if d_ang > angle_eps_deg:
                continue
            d1 = abs(_signed_perp_distance(k, s.x1, s.y1))
            d2 = abs(_signed_perp_distance(k, s.x2, s.y2))
            if max(d1, d2) > perp_eps_px:
                continue
            t1 = _project_t(k, s.x1, s.y1)
            t2 = _project_t(k, s.x2, s.y2)
            tmin, tmax = sorted((t1, t2))
            if tmin > 1.0 + overlap_eps or tmax < -overlap_eps:
                continue
            merged_into = i
            break
        if merged_into is None:
            kept.append(s)
            continue
        k = kept[merged_into]
        candidates = [(k.x1, k.y1), (k.x2, k.y2), (s.x1, s.y1), (s.x2, s.y2)]
        ts = sorted((_project_t(k, x, y), (x, y)) for x, y in candidates)
        (_, lo), *_mid, (_, hi) = ts
        kept[merged_into] = Segment(int(lo[0]), int(lo[1]), int(hi[0]), int(hi[1]))
    return kept


# ---------------------------------------------------------------------------
# Step 9: extend broken connections
# ---------------------------------------------------------------------------


@dataclass
class Endpoint:
    x: int
    y: int
    angle_deg: float  # direction leaving the endpoint along the trace
    seg_index: int
    is_start: bool


def _segment_dir(seg: Segment, from_start: bool) -> float:
    if from_start:
        return math.degrees(math.atan2(seg.y2 - seg.y1, seg.x2 - seg.x1))
    return math.degrees(math.atan2(seg.y1 - seg.y2, seg.x1 - seg.x2))


def connect_near_endpoints(
    segments: list[Segment],
    *,
    max_gap_px: float = 12.0,
    angle_tol_deg: float = 28.0,
) -> list[Segment]:
    if not segments:
        return segments

    endpoints: list[Endpoint] = []
    for i, s in enumerate(segments):
        endpoints.append(Endpoint(s.x1, s.y1, _segment_dir(s, True), i, True))
        endpoints.append(Endpoint(s.x2, s.y2, _segment_dir(s, False), i, False))

    used: set[int] = set()
    bridges: list[Segment] = []

    for i, a in enumerate(endpoints):
        if i in used:
            continue
        best_j: int | None = None
        best_d = max_gap_px + 1.0
        for j, b in enumerate(endpoints):
            if j <= i or j in used or a.seg_index == b.seg_index:
                continue
            d = math.hypot(b.x - a.x, b.y - a.y)
            if d > max_gap_px or d >= best_d:
                continue
            da = abs(((a.angle_deg - b.angle_deg + 180) % 360) - 180)
            if da > angle_tol_deg and abs(da - 180) > angle_tol_deg:
                continue
            best_d, best_j = d, j
        if best_j is not None:
            b = endpoints[best_j]
            bridges.append(Segment(a.x, a.y, b.x, b.y))
            used.add(i)
            used.add(best_j)

    return segments + bridges


# ---------------------------------------------------------------------------
# SVG + verification raster
# ---------------------------------------------------------------------------


def write_svg(
    polylines: list[list[tuple[int, int]]],
    size: tuple[int, int],
    path: Path,
) -> None:
    w, h = size
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        f'  <rect width="{w}" height="{h}" fill="#000000"/>',
        '  <g id="traces" fill="none" stroke="#ffffff" stroke-width="1" '
        'stroke-linecap="square" stroke-linejoin="miter" shape-rendering="crispEdges">',
    ]
    for pl in polylines:
        if len(pl) < 2:
            continue
        d = f"M{pl[0][0]} {pl[0][1]}" + "".join(f"L{x} {y}" for x, y in pl[1:])
        lines.append(f'    <path d="{d}"/>')
    lines.extend(["  </g>", "</svg>"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_verification(
    polylines: list[list[tuple[int, int]]],
    size: tuple[int, int],
    path: Path,
    *,
    line_px: int = 1,
) -> None:
    w, h = size
    img = np.zeros((h, w), dtype=np.uint8)
    for pl in polylines:
        for i in range(len(pl) - 1):
            cv2.line(
                img,
                pl[i],
                pl[i + 1],
                255,
                thickness=line_px,
                lineType=cv2.LINE_8,
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)


# ---------------------------------------------------------------------------
# Pipeline driver
# ---------------------------------------------------------------------------


def run(
    pcb_path: Path,
    mesh_path: Path,
    out_dir: Path,
    *,
    brightness: int = 90,
    diff_thresh: int = 18,
    hough_min_length: int = 10,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    gray = load_grayscale(pcb_path)
    h, w = gray.shape[:2]
    size = (w, h)

    threshold = threshold_bright(gray, fixed=brightness)
    cv2.imwrite(str(out_dir / "threshold.png"), threshold)

    mesh_gray = load_grayscale(mesh_path)
    trace_only = extract_trace_mask(gray, mesh_gray, diff_thresh=diff_thresh)
    cv2.imwrite(str(out_dir / "trace_only.png"), trace_only)

    mesh_removed = cv2.bitwise_and(threshold, cv2.bitwise_not(trace_only))
    cv2.imwrite(str(out_dir / "mesh_removed.png"), mesh_removed)

    routing = suppress_pads(trace_only)
    cleaned = clean_mask(routing)
    cv2.imwrite(str(out_dir / "cleaned.png"), cleaned)

    skel = skeletonize(cleaned)
    cv2.imwrite(str(out_dir / "skeleton.png"), skel)

    # Hough on the trace mask (not skeleton) — skeletonization breaks thin strokes.
    raw_segs = hough_segments(
        cleaned,
        min_length=hough_min_length,
        threshold=12,
        max_gap=10,
    )
    raw_segs = filter_dense_mesh_segments(raw_segs, cleaned)
    snapped = [snap_segment(s) for s in raw_segs if s.length >= hough_min_length]
    simplified_pl = segments_to_polylines(snapped)
    write_svg(simplified_pl, size, out_dir / "simplified.svg")

    segs = merge_parallel_segments(snapped)
    merged_pl = segments_to_polylines(segs)
    write_svg(merged_pl, size, out_dir / "merged.svg")

    connected_segs = connect_near_endpoints(segs)
    connected_pl = segments_to_polylines(connected_segs)
    write_svg(connected_pl, size, out_dir / "connected.svg")

    traces_path = out_dir / "traces.svg"
    write_svg(connected_pl, size, traces_path)

    verification_path = out_dir / "verification.png"
    render_verification(connected_pl, size, verification_path)

    return {
        "size": size,
        "trace_pixels": int(cv2.countNonZero(trace_only)),
        "cleaned_pixels": int(cv2.countNonZero(cleaned)),
        "hough_raw": len(raw_segs),
        "segments_merged": len(segs),
        "segments_connected": len(connected_segs),
        "out_dir": str(out_dir),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    p.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--brightness", type=int, default=90)
    p.add_argument("--diff-thresh", type=int, default=18)
    p.add_argument("--hough-min-length", type=int, default=10)
    args = p.parse_args()

    stats = run(
        args.pcb,
        args.mesh,
        args.out_dir,
        brightness=args.brightness,
        diff_thresh=args.diff_thresh,
        hough_min_length=args.hough_min_length,
    )
    print(
        f"[pcb-trace] {stats['size'][0]}x{stats['size'][1]} "
        f"trace_px={stats['trace_pixels']} cleaned_px={stats['cleaned_pixels']} "
        f"hough={stats['hough_raw']} merged={stats['segments_merged']} "
        f"connected={stats['segments_connected']}"
    )
    print(f"[pcb-trace] output -> {Path(stats['out_dir']).relative_to(REPO)}")


if __name__ == "__main__":
    main()
