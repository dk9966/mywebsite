"""Detect component bounding boxes from a top-down PCB reference image.

A component is a dark rectangular region whose perimeter is mostly painted
with cyan. We exploit that directly:

  1. Build a binary "cyan" mask of all drawn pixels.
  2. Close 1-px gaps so component borders are watertight.
  3. Run connected components on the *inverse* mask (dark pixels). Every
     chip interior becomes its own connected blob, separate from the open
     space between traces because the surrounding cyan border walls it off.
  4. Drop the giant blob (open background) and the tiny blobs (noise).
  5. For each survivor, score the cyan coverage of a thin band immediately
     outside its bbox. A real component has a near-complete cyan border.
  6. Merge close survivors so chips with multiple inner pockets collapse.

This is robust because it does not depend on the cyan strokes being neat
rectangles or on contour orientation - it just asks: "is this dark patch
surrounded by cyan?"
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Component:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def area(self) -> int:
        return self.w * self.h


def _cyan_mask(bgr: np.ndarray, close_kernel: int = 3) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([78, 35, 55], dtype=np.uint8)
    upper = np.array([110, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    if close_kernel > 1:
        k = np.ones((close_kernel, close_kernel), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    return mask


def _dark_blobs(cyan: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dark = cv2.bitwise_not(cyan)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(
        dark, connectivity=4
    )
    return labels, stats, centroids


def _outer_ring_cyan_ratio(
    cyan: np.ndarray, bbox: tuple[int, int, int, int], band: int = 3
) -> float:
    """Fraction of cyan pixels in a `band`-px thick ring immediately
    surrounding the bbox. 1.0 means the box is fully fenced."""
    x, y, w, h = bbox
    H, W = cyan.shape
    x0 = max(0, x - band)
    y0 = max(0, y - band)
    x1 = min(W, x + w + band)
    y1 = min(H, y + h + band)
    outer = cyan[y0:y1, x0:x1]
    inner = cyan[y : y + h, x : x + w]
    outer_count = int(outer.size)
    inner_count = int(inner.size)
    if outer_count - inner_count <= 0:
        return 0.0
    cyan_in_ring = int(outer.sum() // 255) - int(inner.sum() // 255)
    return cyan_in_ring / (outer_count - inner_count)


def _merge_containment(boxes: list[Component]) -> list[Component]:
    """Drop any box fully contained in a strictly larger box.

    Chips often produce an outer body blob and a smaller inner blob (e.g.
    inner cyan square). The inner blob sits *inside* the outer one - dropping
    the inner gives us one rectangle per chip without ever bridging two
    physical components that happen to sit close together."""
    if not boxes:
        return []
    # sort largest first
    ordered = sorted(boxes, key=lambda b: -b.area)
    keep: list[Component] = []
    for b in ordered:
        contained = False
        for k in keep:
            if (k.x <= b.x and k.y <= b.y
                    and k.x + k.w >= b.x + b.w
                    and k.y + k.h >= b.y + b.h
                    and k.area > b.area):
                contained = True
                break
        if not contained:
            keep.append(b)
    return keep


def _drop_nested(boxes: list[Component], *, overlap_threshold: float) -> list[Component]:
    """Drop a smaller box if more than `overlap_threshold` of its area lies
    inside any strictly larger box."""
    if not boxes:
        return []
    keep: list[Component] = []
    for b in sorted(boxes, key=lambda c: -c.area):
        nested = False
        for k in keep:
            if k.area <= b.area:
                continue
            ox0 = max(k.x, b.x)
            oy0 = max(k.y, b.y)
            ox1 = min(k.x + k.w, b.x + b.w)
            oy1 = min(k.y + k.h, b.y + b.h)
            if ox1 <= ox0 or oy1 <= oy0:
                continue
            overlap = (ox1 - ox0) * (oy1 - oy0)
            if overlap / float(b.area) > overlap_threshold:
                nested = True
                break
        if not nested:
            keep.append(b)
    return keep


def _merge_overlapping(boxes: list[Component], pad: int) -> list[Component]:
    if not boxes:
        return []
    grown = [
        (b.x - pad, b.y - pad, b.x + b.w + pad, b.y + b.h + pad) for b in boxes
    ]
    n = len(boxes)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        ax0, ay0, ax1, ay1 = grown[i]
        for j in range(i + 1, n):
            bx0, by0, bx1, by1 = grown[j]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    groups: dict[int, list[Component]] = {}
    for i, b in enumerate(boxes):
        groups.setdefault(find(i), []).append(b)

    merged: list[Component] = []
    for members in groups.values():
        x0 = min(m.x for m in members)
        y0 = min(m.y for m in members)
        x1 = max(m.x + m.w for m in members)
        y1 = max(m.y + m.h for m in members)
        merged.append(Component(x0, y0, x1 - x0, y1 - y0))
    return merged


def run(image_path: Path) -> tuple[list[Component], tuple[int, int]]:
    """Return (components, (image_width, image_height))."""
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(image_path)
    h, w = bgr.shape[:2]

    candidates: list[Component] = []
    # Two passes at different stroke-close kernels. The tight pass finds small
    # SMDs whose bodies are 1-cell rectangles; the broad pass fills in pin
    # patterns so big QFP chips read as a single rectangle.
    for close_kernel in (3, 5):
        cyan = _cyan_mask(bgr, close_kernel=close_kernel)
        _labels, stats, _ = _dark_blobs(cyan)
        canvas_area = w * h
        for i in range(1, len(stats)):
            x, y, ww, hh, area = stats[i]
            if area < 90:
                continue
            if area > 0.25 * canvas_area:
                continue
            if ww < 6 or hh < 6:
                continue
            long_side = max(ww, hh)
            short_side = max(1, min(ww, hh))
            if long_side / short_side > 6:
                continue
            if x <= 1 or y <= 1 or x + ww >= w - 1 or y + hh >= h - 1:
                continue
            fill_ratio = area / float(ww * hh)
            if fill_ratio < 0.62:
                continue
            bbox = (int(x), int(y), int(ww), int(hh))
            if _outer_ring_cyan_ratio(cyan, bbox, band=3) < 0.55:
                continue
            candidates.append(Component(*bbox))

    # Chips with split interiors (outer body + inner cyan square) appear as
    # several concentric dark blobs. Containment merge handles that case
    # without bridging neighbouring chips that simply sit close.
    merged = _merge_containment(candidates)
    # Drop small blobs that sit mostly inside a strictly larger box - those
    # are interior chip details (inner ring, cross-mark) re-detected as their
    # own component. They are not separate obstacles.
    merged = _drop_nested(merged, overlap_threshold=0.55)
    # Drop tiny detections (sub-200 px^2): in practice those are interior
    # marks that were not captured by `_drop_nested` because their parent
    # chip never coalesced into a single rectangle. They mostly hurt routing
    # space without contributing recognisable components.
    merged = [m for m in merged if m.area >= 200]
    return merged, (w, h)


if __name__ == "__main__":
    import sys

    img = Path(sys.argv[1])
    comps, size = run(img)
    print(f"image={size[0]}x{size[1]}  components={len(comps)}")
