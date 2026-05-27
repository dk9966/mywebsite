"""Extract straight line segments from a top-down PCB reference image.

Pipeline (no Douglas-Peucker, no polyline simplification):

  1. Build a binary mask of bright trace pixels.
  2. Morphologically skeletonise the mask so every trace becomes ~1 px wide.
  3. Run ``cv2.HoughLinesP`` on the skeleton -- it returns line *segments*,
     each as a single ``(x1, y1, x2, y2)`` tuple, with a built-in
     ``minLineLength`` filter that drops the short bits we don't want.
  4. Deduplicate near-collinear overlapping segments (Hough often returns
     a few wobbly siblings for the same physical line).

Output:

  - ``--out`` JSON  -- ``{ "image_size": [W,H], "segments": [[x1,y1,x2,y2]...] }``
  - ``--debug`` PNG -- the source image with detected segments painted over.

Run::

    python3 tools/image-trace/extract_lines.py
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[2]
DEFAULT_SRC = (
    REPO
    / "plans/chatgpt/refined lines - ChatGPT Image May 23, 2026, 09_26_21 PM.png"
)
DEFAULT_OUT = REPO / "blender/data/image_lines.json"
DEFAULT_DEBUG = REPO / "plans/chatgpt/_debug_image_lines.png"


# ---------------------------------------------------------------------------
# Image -> binary trace mask
# ---------------------------------------------------------------------------


def trace_mask(bgr: np.ndarray, *, brightness_threshold: int = 90) -> np.ndarray:
    """Bright-on-dark mask. The reference is monochrome cyan/white on black,
    so a single grayscale threshold cleanly separates trace pixels from
    board background and component fill."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, brightness_threshold, 255, cv2.THRESH_BINARY)
    return mask


def skeletonise(mask: np.ndarray) -> np.ndarray:
    """Morphological skeleton: peel one ring of pixels per iteration until
    nothing is left, OR-ing each peeled ridge into the result. Output is a
    one-pixel-wide centreline for every connected trace in the mask."""
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
# Skeleton -> straight line segments
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

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


def hough_segments(
    skel: np.ndarray,
    *,
    threshold: int,
    min_length: int,
    max_gap: int,
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
    return [Segment(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in lines[:, 0, :]]


def _signed_perp_distance(seg: Segment, px: float, py: float) -> float:
    """Perpendicular distance from a point to the infinite line through ``seg``."""
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        return math.hypot(px - seg.x1, py - seg.y1)
    return ((px - seg.x1) * dy - (py - seg.y1) * dx) / norm


def _project_t(seg: Segment, px: float, py: float) -> float:
    """Parametric position 0..1 of the foot of perpendicular from (px,py)."""
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    n2 = dx * dx + dy * dy
    if n2 < 1e-6:
        return 0.0
    return ((px - seg.x1) * dx + (py - seg.y1) * dy) / n2


def dedupe_segments(
    segs: list[Segment],
    *,
    angle_eps_deg: float = 3.0,
    perp_eps_px: float = 3.5,
    overlap_eps: float = 0.55,
) -> list[Segment]:
    """Merge near-collinear segments whose axial spans overlap.

    HoughLinesP often emits two or three near-copies of the same physical
    line (one per detected ridge slice). For each new segment we check it
    against everything kept so far; if it's the same line geometrically we
    extend the existing one to cover both, otherwise we keep the new one.
    """
    kept: list[Segment] = []
    # Bigger lines first so the longer one defines the canonical orientation.
    ordered = sorted(segs, key=lambda s: -s.length)
    for s in ordered:
        merged_into: int | None = None
        for i, k in enumerate(kept):
            d_ang = abs(((s.angle_mod180 - k.angle_mod180) + 90) % 180 - 90)
            if d_ang > angle_eps_deg:
                continue
            # both endpoints of `s` must lie close to the line of `k`
            d1 = abs(_signed_perp_distance(k, s.x1, s.y1))
            d2 = abs(_signed_perp_distance(k, s.x2, s.y2))
            if max(d1, d2) > perp_eps_px:
                continue
            # axial overlap
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
        # Extend k to cover s along k's direction.
        candidates = [
            (k.x1, k.y1),
            (k.x2, k.y2),
            (s.x1, s.y1),
            (s.x2, s.y2),
        ]
        ts = [(_project_t(k, x, y), (x, y)) for x, y in candidates]
        ts.sort()
        (_, lo), *_mid, (_, hi) = ts
        kept[merged_into] = Segment(int(lo[0]), int(lo[1]), int(hi[0]), int(hi[1]))
    return kept


# ---------------------------------------------------------------------------
# Debug + entry point
# ---------------------------------------------------------------------------


def render_debug(
    bgr: np.ndarray,
    segments: list[Segment],
    out_path: Path,
) -> None:
    overlay = bgr.copy()
    h, w = overlay.shape[:2]
    overlay[:, :] = (10, 14, 18)  # near-black backdrop so cyan lines pop
    for s in segments:
        cv2.line(
            overlay,
            (s.x1, s.y1),
            (s.x2, s.y2),
            (255, 220, 0),  # BGR cyan-ish
            thickness=1,
            lineType=cv2.LINE_AA,
        )
        cv2.circle(overlay, (s.x1, s.y1), 2, (0, 80, 255), -1, lineType=cv2.LINE_AA)
    cv2.imwrite(str(out_path), overlay)


def run(
    src: Path,
    out_json: Path,
    debug_png: Path | None,
    *,
    min_length: int = 18,
    threshold: int = 18,
    max_gap: int = 4,
) -> dict:
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(src)
    h, w = bgr.shape[:2]

    mask = trace_mask(bgr)
    skel = skeletonise(mask)
    raw = hough_segments(
        skel,
        threshold=threshold,
        min_length=min_length,
        max_gap=max_gap,
    )
    deduped = dedupe_segments(raw)
    # Drop short stubs that fell out of dedupe (a merge can shorten a leg).
    deduped = [s for s in deduped if s.length >= min_length]

    payload = {
        "image": str(src.relative_to(REPO)),
        "image_size": [w, h],
        "segments": [list(s.as_tuple()) for s in deduped],
        "stats": {
            "raw_segments": len(raw),
            "kept_segments": len(deduped),
            "min_length_px": min_length,
        },
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if debug_png is not None:
        render_debug(bgr, deduped, debug_png)
    return payload


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--debug", type=Path, default=DEFAULT_DEBUG)
    p.add_argument("--min-length", type=int, default=18,
                   help="Hough minLineLength; below this is treated as too short.")
    p.add_argument("--threshold", type=int, default=18,
                   help="Hough accumulator threshold.")
    p.add_argument("--max-gap", type=int, default=4,
                   help="Hough maxLineGap.")
    args = p.parse_args()

    payload = run(
        args.src,
        args.out,
        args.debug,
        min_length=args.min_length,
        threshold=args.threshold,
        max_gap=args.max_gap,
    )
    s = payload["stats"]
    print(
        f"[image-trace] image={payload['image_size']} "
        f"raw={s['raw_segments']} kept={s['kept_segments']} "
        f"min_len={s['min_length_px']}px"
    )
    print(f"[image-trace] json  -> {args.out.relative_to(REPO)}")
    if args.debug is not None:
        print(f"[image-trace] debug -> {args.debug.relative_to(REPO)}")


if __name__ == "__main__":
    main()
