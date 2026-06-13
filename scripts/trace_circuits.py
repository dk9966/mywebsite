#!/usr/bin/env python3
"""Trace cyan circuit lines and locate green/pink boxes in a reference image.

Pipeline:
  cyan color mask -> skeletonize -> polylines
  green/pink masks -> connected components -> axis-aligned boxes
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from skimage.morphology import skeletonize, remove_small_objects

SRC = Path("plans/circuit design/circuits for tracing.png")
OUT_PNG = Path("plans/circuit design/circuits-traced.png")
OUT_JSON = Path("plans/circuit design/circuits-traced.json")


def green_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    mask = (g > 90) & (g > r + 35) & (g > b + 35)
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    return remove_small_objects(mask, min_size=200)


def pink_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    mask = (r > 90) & (b > 90) & (r > g + 25) & (b > g + 25)
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    return remove_small_objects(mask, min_size=200)


def mask_to_boxes(mask: np.ndarray, min_side: int = 12) -> list[dict]:
    labeled, count = ndimage.label(mask)
    boxes = []
    for i in range(1, count + 1):
        ys, xs = np.nonzero(labeled == i)
        if len(xs) == 0:
            continue
        xmin, xmax = int(xs.min()), int(xs.max())
        ymin, ymax = int(ys.min()), int(ys.max())
        w, h = xmax - xmin + 1, ymax - ymin + 1
        if w < min_side or h < min_side:
            continue
        boxes.append(
            {
                "x": xmin,
                "y": ymin,
                "w": w,
                "h": h,
                "cx": round((xmin + xmax) / 2, 1),
                "cy": round((ymin + ymax) / 2, 1),
            }
        )
    boxes.sort(key=lambda b: (b["y"], b["x"]))
    return boxes


def cyan_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    # Core of a cyan trace: green and blue both strong, red clearly behind.
    # Green boxes fail (b low), pink boxes fail (r high).
    mask = (b > 90) & (g > 90) & (r < (np.minimum(g, b) - 40))
    mask = ndimage.binary_closing(mask, structure=np.ones((3, 3)))
    mask = remove_small_objects(mask, min_size=30)
    return mask


def skeleton_to_polylines(skel: np.ndarray) -> list[list[tuple[int, int]]]:
    """Walk the 1px skeleton: split at junctions/endpoints, follow degree-2 runs."""
    ys, xs = np.nonzero(skel)
    pixels = set(zip(map(int, xs), map(int, ys)))

    def neighbors(p):
        x, y = p
        return [
            (x + dx, y + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (dx or dy) and (x + dx, y + dy) in pixels
        ]

    degree = {p: len(neighbors(p)) for p in pixels}
    nodes = {p for p, d in degree.items() if d != 2}
    visited_edges = set()
    polylines = []

    def walk(start, first):
        """Follow a run of degree-2 pixels from a node until the next node."""
        path = [start, first]
        prev, cur = start, first
        while cur not in nodes:
            nxt = [n for n in neighbors(cur) if n != prev]
            if not nxt:
                break  # dead end inside a run (shouldn't happen, but be safe)
            prev, cur = cur, nxt[0]
            path.append(cur)
        return path

    for node in nodes:
        for nb in neighbors(node):
            edge = frozenset((node, nb))
            if edge in visited_edges:
                continue
            path = walk(node, nb)
            for a, b in zip(path, path[1:]):
                visited_edges.add(frozenset((a, b)))
            if len(path) > 2:
                polylines.append(path)

    # Pure loops (no junction anywhere on them) have no node to start from.
    covered = {p for line in polylines for p in line}
    leftover = pixels - covered - nodes
    while leftover:
        start = leftover.pop()
        path = [start]
        prev, cur = None, start
        while True:
            nxt = [n for n in neighbors(cur) if n != prev and n in leftover or n == start and len(path) > 2]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start:
                path.append(cur)
                break
            path.append(cur)
            leftover.discard(cur)
        if len(path) > 2:
            polylines.append(path)

    return polylines


def rdp(points: list[tuple[int, int]], eps: float) -> list[tuple[int, int]]:
    if len(points) < 3:
        return points
    pts = np.asarray(points, dtype=float)
    start, end = pts[0], pts[-1]
    seg = end - start
    seg_len = np.hypot(*seg)
    if seg_len == 0:
        dists = np.hypot(*(pts - start).T)
    else:
        dists = np.abs(np.cross(seg, start - pts)) / seg_len
    i = int(np.argmax(dists))
    if dists[i] > eps:
        left = rdp(points[: i + 1], eps)
        right = rdp(points[i:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]


def render(polylines, boxes, size, scale=1):
    w, h = size
    img = Image.new("RGB", (w * scale, h * scale), "black")

    glow = Image.new("L", img.size, 0)
    gdraw = ImageDraw.Draw(glow)
    for line in polylines:
        pts = [(x * scale, y * scale) for x, y in line]
        gdraw.line(pts, fill=255, width=5 * scale)
    glow = glow.filter(ImageFilter.GaussianBlur(4 * scale))

    cyan_layer = Image.new("RGB", img.size, (0, 170, 210))
    img = Image.composite(cyan_layer, img, glow)

    draw = ImageDraw.Draw(img)
    for line in polylines:
        pts = [(x * scale, y * scale) for x, y in line]
        draw.line(pts, fill=(120, 245, 255), width=2 * scale)

    for box in boxes.get("green", []):
        x0, y0 = box["x"] * scale, box["y"] * scale
        x1, y1 = (box["x"] + box["w"]) * scale, (box["y"] + box["h"]) * scale
        draw.rectangle([x0, y0, x1, y1], outline=(80, 255, 120), width=2 * scale)
    for box in boxes.get("pink", []):
        x0, y0 = box["x"] * scale, box["y"] * scale
        x1, y1 = (box["x"] + box["w"]) * scale, (box["y"] + box["h"]) * scale
        draw.rectangle([x0, y0, x1, y1], outline=(255, 90, 200), width=2 * scale)
    return img


def main():
    rgb = np.asarray(Image.open(SRC).convert("RGB"))
    mask = cyan_mask(rgb)
    skel = skeletonize(mask)
    raw = skeleton_to_polylines(skel)
    simplified = [rdp(line, eps=2.0) for line in raw]
    # Drop tiny stubs left over from glow blobs.
    def length(line):
        return sum(np.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(line, line[1:]))
    simplified = [line for line in simplified if length(line) >= 8]

    boxes = {
        "green": mask_to_boxes(green_mask(rgb)),
        "pink": mask_to_boxes(pink_mask(rgb)),
    }
    payload = {
        "lines": [[list(p) for p in line] for line in simplified],
        "boxes": boxes,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    img = render(simplified, boxes, (rgb.shape[1], rgb.shape[0]))
    img.save(OUT_PNG)

    print(f"skeleton px: {int(skel.sum())}")
    print(f"polylines: {len(simplified)}")
    print(f"points after simplify: {sum(len(l) for l in simplified)}")
    print(f"green boxes: {len(boxes['green'])}")
    print(f"pink boxes: {len(boxes['pink'])}")
    for color in ("green", "pink"):
        for i, box in enumerate(boxes[color]):
            print(f"  {color}[{i}]: x={box['x']} y={box['y']} w={box['w']} h={box['h']}")
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
