#!/usr/bin/env python3
"""Render Tron-style "circuit city" stills: 2D traces reading as roads, PCB
components as wireframe buildings rising in Y — the reference-clip look
(plans/clips/02 - Tron Lines) applied to circuits.

Component wireframes are the crease-edge outlines from
scripts/build-qfp-variants-glb.py (gull-wing QFPs, beveled caps, L-pin chips),
instanced onto a procedural board of buses, staircase jogs, stubs, pads and
vias. A perspective camera + bloom + depth fade give the cinematic frame.

  python3 scripts/render-circuit-city.py           # all scenes
  python3 scripts/render-circuit-city.py wide-01   # one scene

Outputs → output/circuit-scenes/<name>.png
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output/circuit-scenes"

_spec = importlib.util.spec_from_file_location(
    "qfpv", ROOT / "scripts/build-qfp-variants-glb.py"
)
qfpv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qfpv)

SS = 2  # supersample factor

# Palette (r, g, b) — dim teal roads, bright cyan mains, white-hot heads.
COL_SCAFFOLD = (10, 30, 34)
COL_DIM = (16, 66, 76)
COL_MID = (34, 124, 136)
COL_BRIGHT = (104, 232, 236)
COL_HOT = (228, 255, 255)

# ---------------------------------------------------------------------------
# Component edge libraries (crease outlines, cached per kind)
# ---------------------------------------------------------------------------


def _edges(kind: str, w: float, d: float) -> np.ndarray:
    solids = qfpv.variant_solids(0.0, 0.0, kind, w, d)
    return qfpv.crease_edges(solids)


_LIB: dict[str, np.ndarray] = {}


def component_edges(name: str) -> np.ndarray:
    if name not in _LIB:
        if name == "qfp":
            _LIB[name] = _edges("v5-gullwing-90", 1.0, 1.0)
        elif name == "qfp_slant":
            _LIB[name] = _edges("v6-gullwing-slant", 1.0, 1.0)
        elif name == "chip_rect":
            _LIB[name] = _edges("v6-gullwing-slant", 1.6, 0.8)
        elif name == "lchip":
            _LIB[name] = _edges("v3-l-pins", 1.2, 0.6)
        elif name == "cap":
            _LIB[name] = _edges("v2-beveled-prism", 0.55, 0.55)
        elif name == "block":
            _LIB[name] = _edges("v1-prism-frustum", 0.8, 0.8)
        else:
            raise ValueError(name)
    return _LIB[name]


def place_edges(name: str, x: float, z: float, s: float, rot90: int) -> np.ndarray:
    """Instance a component edge set: scale, rotate (multiples of 90°), move."""
    e = component_edges(name).copy() * s
    for _ in range(rot90 % 4):
        ex = e[..., 0].copy()
        e[..., 0] = -e[..., 2]
        e[..., 2] = ex
    e[..., 0] += x
    e[..., 2] += z
    return e


# Footprint half-extents (board keep-out) per kind at scale 1, incl. pins.
FOOT_HALF = {
    "qfp": 0.95,
    "qfp_slant": 0.95,
    "chip_rect": 1.25,
    "lchip": 1.0,
    "cap": 0.45,
    "block": 0.55,
}

# ---------------------------------------------------------------------------
# Procedural board: components + traces
# ---------------------------------------------------------------------------


class Board:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.comps: list[tuple[str, float, float, float, int]] = []  # name,x,z,s,rot
        self.lines: list[tuple[list[tuple[float, float]], float]] = []  # pts, tier
        self.heads: list[tuple[float, float, float, float]] = []  # hot segs x0z0x1z1

    def comp_boxes(self, margin: float) -> list[tuple[float, float, float, float]]:
        out = []
        for name, x, z, s, _ in self.comps:
            h = FOOT_HALF[name] * s + margin
            out.append((x - h, z - h, x + h, z + h))
        return out

    def add_component(self, name: str, x: float, z: float, s: float, rot90: int) -> bool:
        h = FOOT_HALF[name] * s + 0.4
        for bx0, bz0, bx1, bz1 in self.comp_boxes(0.4):
            if x + h > bx0 and x - h < bx1 and z + h > bz0 and z - h < bz1:
                return False
        self.comps.append((name, x, z, s, rot90))
        return True

    def scatter_components(
        self, x0: float, x1: float, z0: float, z1: float, count: int, big: float
    ) -> None:
        kinds = ["qfp", "qfp_slant", "chip_rect", "lchip", "cap", "cap", "block"]
        tries = 0
        placed = 0
        while placed < count and tries < count * 40:
            tries += 1
            name = self.rng.choice(kinds)
            s = big * self.rng.uniform(0.75, 1.25) * (0.55 if name == "cap" else 1.0)
            x = self.rng.uniform(x0, x1)
            z = self.rng.uniform(z0, z1)
            if self.add_component(name, x, z, s, self.rng.randrange(4)):
                placed += 1

    # -- traces --------------------------------------------------------------

    def bus(
        self,
        x0: float,
        x1: float,
        z: float,
        n: int,
        tier: float,
        jog_prob: float = 0.6,
    ) -> None:
        """Horizontal multi-line bus with staircase jogs, routed around
        component keep-outs (the PCB detour look)."""
        rng = self.rng
        spacing = 0.16
        jogs: list[tuple[float, float]] = []
        # random staircase jogs
        cx = x0 + rng.uniform(2.0, 6.0)
        while cx < x1 - 3.0:
            if rng.random() < jog_prob:
                jogs.append((cx, rng.choice([-1, 1]) * rng.uniform(0.8, 2.4)))
            cx += rng.uniform(3.0, 8.0)

        boxes = self.comp_boxes(0.55)
        for k in range(n):
            zk = z + k * spacing
            pts: list[tuple[float, float]] = [(x0, zk)]
            cur_z = zk
            cur_x = x0
            for jx, dz in jogs:
                jxk = jx + k * spacing  # staircase offset between twin lines
                pts.append((jxk, cur_z))
                cur_z += dz
                pts.append((jxk, cur_z))
                cur_x = jxk
            pts.append((x1, cur_z))

            pts = self._detour(pts, boxes)
            self.lines.append((pts, tier))
            if rng.random() < 0.30:
                self._head_at(pts)

    def _detour(
        self,
        pts: list[tuple[float, float]],
        boxes: list[tuple[float, float, float, float]],
    ) -> list[tuple[float, float]]:
        """Route horizontal runs around component boxes with a square detour."""
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if abs(a[1] - b[1]) > 1e-9 or a[0] == b[0]:  # vertical / degenerate
                out.append(b)
                continue
            x_lo, x_hi = min(a[0], b[0]), max(a[0], b[0])
            sgn = 1 if b[0] >= a[0] else -1
            zline = a[1]
            hits = [
                (bx0, bz0, bx1, bz1)
                for bx0, bz0, bx1, bz1 in boxes
                if bz0 < zline < bz1 and bx1 > x_lo and bx0 < x_hi
            ]
            hits.sort(key=lambda h: h[0] * sgn)
            cur = a
            for bx0, bz0, bx1, bz1 in hits:
                enter = bx0 if sgn > 0 else bx1
                exit_ = bx1 if sgn > 0 else bx0
                # go over or under, whichever is closer
                zd = bz0 - 0.001 if abs(zline - bz0) < abs(zline - bz1) else bz1 + 0.001
                out.extend([(enter, cur[1]), (enter, zd), (exit_, zd), (exit_, zline)])
                cur = (exit_, zline)
            out.append(b)
        return out

    def branch(self, x: float, z: float, length: float, tier: float) -> None:
        """Vertical branch with an optional 90° elbow."""
        rng = self.rng
        dz = rng.choice([-1, 1]) * length
        pts = [(x, z), (x, z + dz)]
        if rng.random() < 0.5:
            dx = rng.choice([-1, 1]) * rng.uniform(1.5, 5.0)
            pts.append((x + dx, z + dz))
        self.lines.append((pts, tier))
        if rng.random() < 0.35:
            self._head_at(pts)

    def frame(self, x0: float, z0: float, x1: float, z1: float, tier: float) -> None:
        """Open rectangle outline (three sides), like the clip's frames."""
        openside = self.rng.randrange(4)
        corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1), (x0, z0)]
        pts = []
        for i in range(4):
            if i == openside:
                if pts:
                    self.lines.append((pts, tier))
                pts = []
                continue
            if not pts:
                pts.append(corners[i])
            pts.append(corners[i + 1])
        if pts:
            self.lines.append((pts, tier))

    def stub_components(self) -> None:
        """Short connector stubs from component edges out to the board."""
        rng = self.rng
        for name, x, z, s, _ in self.comps:
            h = FOOT_HALF[name] * s
            for _ in range(rng.randrange(2, 5)):
                side = rng.randrange(4)
                off = rng.uniform(-h * 0.5, h * 0.5)
                ln = rng.uniform(0.8, 2.6)
                if side == 0:
                    pts = [(x + h, z + off), (x + h + ln, z + off)]
                elif side == 1:
                    pts = [(x - h, z + off), (x - h - ln, z + off)]
                elif side == 2:
                    pts = [(x + off, z + h), (x + off, z + h + ln)]
                else:
                    pts = [(x + off, z - h), (x + off, z - h - ln)]
                self.lines.append((pts, 0.5))

    def _head_at(self, pts: list[tuple[float, float]]) -> None:
        """Hot comet-head segment somewhere along a line."""
        rng = self.rng
        i = rng.randrange(len(pts) - 1)
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        t = rng.uniform(0.3, 0.9)
        hx, hz = ax + (bx - ax) * t, az + (bz - az) * t
        L = 0.5
        d = math.hypot(bx - ax, bz - az)
        if d < 1e-6:
            return
        ux, uz = (bx - ax) / d, (bz - az) / d
        self.heads.append((hx - ux * L, hz - uz * L, hx, hz))


def build_board(
    rng: random.Random,
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    comp_count: int,
    comp_scale: float,
    bus_count: int,
    branch_count: int,
    frame_count: int,
) -> Board:
    b = Board(rng)
    b.scatter_components(x0 + 3, x1 - 3, z0 + 2, z1 - 2, comp_count, comp_scale)
    for _ in range(frame_count):
        fx0 = rng.uniform(x0, x1 - 8)
        fz0 = rng.uniform(z0, z1 - 5)
        b.frame(fx0, fz0, fx0 + rng.uniform(5, 14), fz0 + rng.uniform(3, 8), 0.35)
    for _ in range(bus_count):
        z = rng.uniform(z0, z1)
        n = rng.choice([1, 2, 2, 3])
        tier = rng.choice([0.5, 0.5, 1.0])
        b.bus(x0 - rng.uniform(0, 4), x1 + rng.uniform(0, 4), z, n, tier)
    for _ in range(branch_count):
        b.branch(rng.uniform(x0, x1), rng.uniform(z0, z1), rng.uniform(2, 7), 0.5)
    b.stub_components()
    return b


# ---------------------------------------------------------------------------
# Camera + renderer
# ---------------------------------------------------------------------------


def normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)


class Camera:
    def __init__(self, eye, target, fov_deg: float, w: int, h: int):
        self.eye = np.asarray(eye, float)
        self.w, self.h = w, h
        fwd = normalize(np.asarray(target, float) - self.eye)
        right = normalize(np.cross(fwd, np.array([0.0, 1.0, 0.0])))
        up = np.cross(right, fwd)
        self.m = np.stack([right, up, fwd])
        self.f = 0.5 * h / math.tan(math.radians(fov_deg) / 2)

    def project_seg(self, a: np.ndarray, b: np.ndarray):
        va = self.m @ (a - self.eye)
        vb = self.m @ (b - self.eye)
        near = 0.2
        if va[2] < near and vb[2] < near:
            return None
        if va[2] < near or vb[2] < near:  # clip to near plane
            t = (near - va[2]) / (vb[2] - va[2])
            c = va + t * (vb - va)
            if va[2] < near:
                va = c
            else:
                vb = c
        ax = self.w / 2 + self.f * va[0] / va[2]
        ay = self.h / 2 - self.f * va[1] / va[2]
        bx = self.w / 2 + self.f * vb[0] / vb[2]
        by = self.h / 2 - self.f * vb[1] / vb[2]
        return (ax, ay), (bx, by), (va[2] + vb[2]) / 2


def fade(depth: float, k: float) -> float:
    return math.exp(-depth * k)


def scale_col(col, s: float):
    return tuple(min(255, int(c * s)) for c in col)


def render_scene(name: str, cfg: dict) -> Path:
    rng = random.Random(cfg["seed"])
    W, H = cfg.get("size", (1920, 1080))
    w, h = W * SS, H * SS

    board = build_board(
        rng,
        *cfg["extent"],
        comp_count=cfg["comps"],
        comp_scale=cfg["comp_scale"],
        bus_count=cfg["buses"],
        branch_count=cfg["branches"],
        frame_count=cfg["frames"],
    )
    cam = Camera(cfg["eye"], cfg["target"], cfg["fov"], w, h)
    fog = cfg["fog"]

    img = Image.new("RGB", (w, h), (1, 3, 4))
    d = ImageDraw.Draw(img)

    def seg3(a3, b3, col, width, tier=1.0):
        p = cam.project_seg(np.asarray(a3, float), np.asarray(b3, float))
        if not p:
            return
        (ax, ay), (bx, by), depth = p
        if max(ax, bx) < -50 or min(ax, bx) > w + 50:
            return
        if max(ay, by) < -50 or min(ay, by) > h + 50:
            return
        s = tier * fade(depth, fog)
        if s < 0.02:
            return
        d.line([(ax, ay), (bx, by)], fill=scale_col(col, s), width=width)

    x0, x1, z0, z1 = cfg["extent"]

    # faint scaffold grid (barely-there graph paper)
    step = cfg.get("grid_step", 2.0)
    gx = x0 - 6
    while gx <= x1 + 6:
        seg3((gx, 0, z0 - 6), (gx, 0, z1 + 6), COL_SCAFFOLD, SS, 0.35)
        gx += step
    gz = z0 - 6
    while gz <= z1 + 6:
        seg3((x0 - 6, 0, gz), (x1 + 6, 0, gz), COL_SCAFFOLD, SS, 0.35)
        gz += step

    # traces
    for pts, tier in board.lines:
        col = COL_BRIGHT if tier >= 1.0 else (COL_MID if tier >= 0.5 else COL_DIM)
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            seg3((ax, 0, az), (bx, 0, bz), col, 2 * SS, tier)

    # components (the buildings)
    for cname, cx, cz, s, rot in board.comps:
        for a, b in place_edges(cname, cx, cz, s, rot):
            seg3(a, b, COL_BRIGHT, 2 * SS, 0.95)

    # hot heads
    for hx0, hz0, hx1, hz1 in board.heads:
        seg3((hx0, 0, hz0), (hx1, 0, hz1), COL_HOT, 3 * SS, 1.0)

    # bloom: two blurred layers added back, kept subtle so lines stay crisp
    glow1 = img.filter(ImageFilter.GaussianBlur(2 * SS))
    glow2 = img.filter(ImageFilter.GaussianBlur(9 * SS))
    img = ImageChops.add(img, glow1.point(lambda v: v * 3 // 5))
    img = ImageChops.add(img, glow2.point(lambda v: v // 4))

    img = img.resize((W, H), Image.LANCZOS)

    # vignette
    vig = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vig)
    dv.ellipse([-W * 0.35, -H * 0.45, W * 1.35, H * 1.45], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(img, black, vig.point(lambda v: 15 + v * 240 // 255))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.png"
    img.save(out)
    print(f"{name}: {out.relative_to(ROOT)}")
    return out


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

SCENES: dict[str, dict] = {
    # Close-ups: low grazing camera, big components, strong z-direction read.
    "closeup-01": dict(
        seed=11,
        extent=(-6, 26, -8, 10),
        comps=6,
        comp_scale=3.4,
        buses=10,
        branches=10,
        frames=3,
        eye=(-3.0, 1.7, 8.5),
        target=(10.0, 0.5, -1.0),
        fov=52,
        fog=0.026,
        grid_step=1.0,
    ),
    "closeup-02": dict(
        seed=23,
        extent=(-6, 26, -9, 9),
        comps=7,
        comp_scale=3.0,
        buses=12,
        branches=12,
        frames=3,
        eye=(20.0, 1.4, 7.0),
        target=(6.0, 0.5, -2.0),
        fov=55,
        fog=0.026,
        grid_step=1.0,
    ),
    # Medium: pattern legible, several components.
    "medium-01": dict(
        seed=37,
        extent=(-14, 34, -14, 14),
        comps=14,
        comp_scale=2.0,
        buses=18,
        branches=22,
        frames=6,
        eye=(-6.0, 7.5, 20.0),
        target=(12.0, 0.0, -2.0),
        fov=50,
        fog=0.016,
    ),
    "medium-02": dict(
        seed=41,
        extent=(-14, 34, -14, 14),
        comps=16,
        comp_scale=1.8,
        buses=20,
        branches=24,
        frames=6,
        eye=(28.0, 6.0, 18.0),
        target=(8.0, 0.0, -4.0),
        fov=52,
        fog=0.016,
    ),
    # Wide: the circuit pattern reads like a city grid from above.
    "wide-01": dict(
        seed=53,
        extent=(-24, 44, -20, 20),
        comps=22,
        comp_scale=1.7,
        buses=22,
        branches=26,
        frames=8,
        eye=(4.0, 22.0, 34.0),
        target=(10.0, 0.0, -2.0),
        fov=48,
        fog=0.010,
        grid_step=2.0,
    ),
    "wide-02": dict(
        seed=67,
        extent=(-26, 46, -22, 22),
        comps=26,
        comp_scale=1.5,
        buses=26,
        branches=32,
        frames=9,
        eye=(34.0, 26.0, 30.0),
        target=(8.0, 0.0, -4.0),
        fov=46,
        fog=0.009,
        grid_step=2.0,
    ),
}


def main() -> None:
    wanted = sys.argv[1:] or list(SCENES)
    for name in wanted:
        render_scene(name, SCENES[name])


if __name__ == "__main__":
    main()
