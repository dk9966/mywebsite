"""Octilinear PCB trace router.

Design
------
Everything happens on a snapped pitch grid. A cell is `PITCH` pixels wide
and tall. Routing is 8-connected (cardinal + diagonal), so every emitted
segment is exactly horizontal, vertical, or 45 degrees - mathematically by
construction. No bezier, no noise possible.

Pipeline:

  1. Inflate component bboxes by a small margin and mark covered cells
     `blocked`. This guarantees a `PITCH`-cell air-gap around every chip.
  2. Walk each component's perimeter at fixed stride and drop "pins"
     (boundary point on the chip, plus an outward stub cell that is free).
  3. Pair pins into nets greedily by shortest reachable distance. Longest
     nets go first so they claim the long corridors and shorter nets pack
     parallel to them - this is what produces the bus look without any
     special-case code.
  4. For each net, A* from one stub to the other. Edge cost is 10 for
     cardinal, 14 for diagonal (so the heuristic stays admissible) plus a
     small turn penalty that biases the result toward long straight runs.
  5. Mark every traversed cell as `used`; subsequent nets cannot reuse it.
     This is the hard "no overlap / no crossing" constraint.
  6. Compress each path to direction-change vertices and prepend / append
     the stub-to-pin segment so the trace lands precisely on the chip edge.

The output is a list of `Trace` dataclasses with integer pixel polylines
suitable for emitting as SVG `M`/`L` paths.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from detect import Component


# -- Grid constants ---------------------------------------------------------

CARDINAL = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAGONAL = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
NEIGHBOURS = CARDINAL + DIAGONAL
STEP_COST = {d: (10 if (d in CARDINAL) else 14) for d in NEIGHBOURS}
TURN_PENALTY = 6

# Outward direction names for pin placement.
OUTWARD = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


# -- Data types -------------------------------------------------------------


@dataclass(frozen=True)
class Pin:
    """A pin on a component's edge plus the first free cell outside it."""

    cell_in: tuple[int, int]   # cell coord on the component edge (blocked)
    cell_out: tuple[int, int]  # first free cell outward from the edge
    direction: str             # one of N/S/E/W
    owner: int                 # index into the component list


@dataclass
class Trace:
    points_px: list[tuple[int, int]]
    rank: int = 0  # 0 = backbone (long), 1 = signal (short); for styling


@dataclass
class RouteReport:
    traces: list[Trace] = field(default_factory=list)
    requested_nets: int = 0
    routed_nets: int = 0
    grid_shape: tuple[int, int] = (0, 0)
    pitch: int = 0


# -- Router -----------------------------------------------------------------


class Router:
    def __init__(
        self,
        image_size: tuple[int, int],
        components: list[Component],
        pitch: int = 8,
        margin: int = 1,
    ) -> None:
        self.W, self.H = image_size
        self.pitch = pitch
        self.cols = self.W // pitch
        self.rows = self.H // pitch
        self.margin = margin

        # `blocked` = chip interior + safety pad. Permanent obstacles.
        # `used`    = cells consumed by an already-routed trace.
        self.blocked = np.zeros((self.cols, self.rows), dtype=bool)
        self.used = np.zeros((self.cols, self.rows), dtype=bool)
        self.components = components

        for comp in components:
            self._block_component(comp)

    # ---- grid helpers -----------------------------------------------------

    def _block_component(self, comp: Component) -> None:
        c0 = max(0, comp.x // self.pitch - self.margin)
        r0 = max(0, comp.y // self.pitch - self.margin)
        c1 = min(self.cols, (comp.x + comp.w + self.pitch - 1) // self.pitch + self.margin)
        r1 = min(self.rows, (comp.y + comp.h + self.pitch - 1) // self.pitch + self.margin)
        self.blocked[c0:c1, r0:r1] = True

    def _in_bounds(self, cell: tuple[int, int]) -> bool:
        c, r = cell
        return 0 <= c < self.cols and 0 <= r < self.rows

    def _cell_to_px(self, cell: tuple[int, int]) -> tuple[int, int]:
        c, r = cell
        return (c * self.pitch + self.pitch // 2, r * self.pitch + self.pitch // 2)

    # ---- pin generation ---------------------------------------------------

    def generate_pins(self, *, stride_cells: int = 2) -> list[Pin]:
        """Drop pins along every component's perimeter.

        The stride scales with chip size: tiny SMDs get one pin per edge,
        large chips get a full pin row at `stride_cells` spacing. That mimics
        how real components have proportionally many pads."""
        pins: list[Pin] = []
        for idx, comp in enumerate(self.components):
            c0 = max(0, comp.x // self.pitch)
            r0 = max(0, comp.y // self.pitch)
            c1 = min(self.cols - 1, (comp.x + comp.w) // self.pitch)
            r1 = min(self.rows - 1, (comp.y + comp.h) // self.pitch)

            def add(cell_in: tuple[int, int], direction: str) -> None:
                dx, dy = OUTWARD[direction]
                stub = (cell_in[0] + dx * (self.margin + 1),
                        cell_in[1] + dy * (self.margin + 1))
                if not self._in_bounds(stub):
                    return
                if self.blocked[stub]:
                    return
                pins.append(Pin(cell_in=cell_in, cell_out=stub,
                                direction=direction, owner=idx))

            def edge_positions(a: int, b: int) -> list[int]:
                span = b - a
                if span <= 0:
                    return [a]
                if span < stride_cells:
                    return [a + span // 2]
                return list(range(a, b + 1, stride_cells))

            for c in edge_positions(c0, c1):
                add((c, r0), "N")
                add((c, r1), "S")
            for r in edge_positions(r0, r1):
                add((c0, r), "W")
                add((c1, r), "E")

        return pins

    # ---- A* ---------------------------------------------------------------

    @staticmethod
    def _octile(a: tuple[int, int], b: tuple[int, int]) -> int:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        # admissible heuristic for STEP_COST {cardinal=10, diagonal=14}
        return 10 * (dx + dy) + (14 - 2 * 10) * min(dx, dy)

    def a_star(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]] | None:
        if start == goal:
            return [start]
        if not self._in_bounds(start) or not self._in_bounds(goal):
            return None
        if self.blocked[start] or self.blocked[goal]:
            return None
        if self.used[start] or self.used[goal]:
            return None

        # State key: (cell, last_step_dir). Tracking direction lets us charge a
        # turn penalty, which makes A* prefer long straight runs.
        open_set: list[tuple[int, int, tuple[int, int], tuple[int, int] | None]] = []
        heapq.heappush(open_set, (self._octile(start, goal), 0, start, None))

        came_from: dict[tuple[tuple[int, int], tuple[int, int] | None],
                        tuple[tuple[int, int], tuple[int, int] | None]] = {}
        best_g: dict[tuple[tuple[int, int], tuple[int, int] | None], int] = {
            (start, None): 0
        }

        while open_set:
            _, g, cell, last_dir = heapq.heappop(open_set)
            if cell == goal:
                # reconstruct
                path: list[tuple[int, int]] = [cell]
                key = (cell, last_dir)
                while key in came_from:
                    key = came_from[key]
                    path.append(key[0])
                path.reverse()
                return path

            for dx, dy in NEIGHBOURS:
                nx, ny = cell[0] + dx, cell[1] + dy
                if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                    continue
                if self.blocked[nx, ny] or self.used[nx, ny]:
                    continue
                step = STEP_COST[(dx, dy)]
                turn = 0 if last_dir is None or last_dir == (dx, dy) else TURN_PENALTY
                ng = g + step + turn
                nkey = ((nx, ny), (dx, dy))
                if ng >= best_g.get(nkey, 10**18):
                    continue
                best_g[nkey] = ng
                came_from[nkey] = (cell, last_dir)
                f = ng + self._octile((nx, ny), goal)
                heapq.heappush(open_set, (f, ng, (nx, ny), (dx, dy)))

        return None

    # ---- net pairing ------------------------------------------------------

    @staticmethod
    def _greedy_pair(pins: list[Pin], *, max_reach: int) -> list[tuple[int, int]]:
        """Pair each pin with a not-yet-used partner that minimises octile
        distance. Greedy by shortest pair first."""
        n = len(pins)
        if n < 2:
            return []
        coords = np.array([p.cell_out for p in pins], dtype=np.int32)
        owners = np.array([p.owner for p in pins], dtype=np.int32)

        # Build a flat list of candidate pair distances under reach.
        candidates: list[tuple[int, int, int]] = []
        for i in range(n):
            dx = np.abs(coords[:, 0] - coords[i, 0])
            dy = np.abs(coords[:, 1] - coords[i, 1])
            oct_d = 10 * (dx + dy) - 6 * np.minimum(dx, dy)
            for j in range(i + 1, n):
                if owners[j] == owners[i]:
                    continue
                if oct_d[j] > max_reach:
                    continue
                candidates.append((int(oct_d[j]), i, j))

        candidates.sort()

        used = [False] * n
        pairs: list[tuple[int, int]] = []
        for _, i, j in candidates:
            if used[i] or used[j]:
                continue
            used[i] = True
            used[j] = True
            pairs.append((i, j))
        return pairs

    # ---- end-to-end -------------------------------------------------------

    def _edge_pins(self) -> list[Pin]:
        """Synthetic pins anchored at each free border cell. They give
        unpaired chip pins somewhere to go - traces that route to one
        of these appear to leave the board, which is what high-end
        motherboards actually do."""
        out: list[Pin] = []
        owner = -1  # sentinel - never matches a real chip
        # top / bottom
        for c in range(0, self.cols, 1):
            for r in (0, self.rows - 1):
                if self.blocked[c, r]:
                    continue
                out.append(Pin(cell_in=(c, r), cell_out=(c, r),
                               direction="N" if r == 0 else "S", owner=owner))
        # left / right
        for r in range(0, self.rows, 1):
            for c in (0, self.cols - 1):
                if self.blocked[c, r]:
                    continue
                out.append(Pin(cell_in=(c, r), cell_out=(c, r),
                               direction="W" if c == 0 else "E", owner=owner))
        return out

    def route_all(
        self,
        *,
        pin_stride_cells: int = 2,
        max_reach_cells: int = 28,
        max_nets: int | None = None,
        edge_exit_fraction: float = 0.18,
    ) -> RouteReport:
        chip_pins = self.generate_pins(stride_cells=pin_stride_cells)
        reach = max_reach_cells * 10
        pairs = self._greedy_pair(chip_pins, max_reach=reach)

        # Build a flat pin table so net index pairs are uniform.
        pins: list[Pin] = list(chip_pins)
        paired_idx: set[int] = set()
        for i, j in pairs:
            paired_idx.add(i)
            paired_idx.add(j)

        # Some chip pins didn't find a partner; route a fraction of them off
        # to the nearest board edge so the layout looks like a real PCB.
        edge_pins = self._edge_pins()
        edge_base = len(pins)
        pins.extend(edge_pins)
        unpaired = [i for i in range(len(chip_pins)) if i not in paired_idx]
        unpaired.sort(key=lambda i: hash((pins[i].cell_in,)))  # deterministic shuffle
        keep = max(1, int(len(unpaired) * edge_exit_fraction))
        unpaired = unpaired[:keep]
        for pi in unpaired:
            p = pins[pi]
            # nearest edge pin matching the chip pin's outward direction
            best = None
            best_d = 10**9
            for ej, ep in enumerate(edge_pins):
                if ep.direction != p.direction:
                    continue
                d = self._octile(p.cell_out, ep.cell_out)
                if d < best_d:
                    best_d = d
                    best = ej
            if best is None:
                continue
            pairs.append((pi, edge_base + best))

        # Route shortest nets first: nearby chip-to-chip connections have very
        # few valid octilinear paths, so they get to claim the obvious route
        # before bigger nets steal the corridor. Bigger nets then detour around
        # the locked-in short ones, which still produces bus-like parallels
        # because the turn penalty makes them prefer straight runs.
        def _dist(p: tuple[int, int]) -> int:
            i, j = p
            a, b = pins[i].cell_out, pins[j].cell_out
            return self._octile(a, b)

        pairs.sort(key=_dist)
        if max_nets is not None:
            pairs = pairs[:max_nets]

        report = RouteReport(
            requested_nets=len(pairs),
            grid_shape=(self.cols, self.rows),
            pitch=self.pitch,
        )

        routed_chip_pins: set[int] = set()
        for i, j in pairs:
            pi, pj = pins[i], pins[j]
            path = self.a_star(pi.cell_out, pj.cell_out)
            if path is None or len(path) < 2:
                continue
            for c in path:
                self.used[c] = True
            if pi.owner >= 0:
                routed_chip_pins.add(i)
            if pj.owner >= 0:
                routed_chip_pins.add(j)
            poly = self._simplify_to_pixels(pi, path, pj)
            length = sum(
                max(abs(poly[k + 1][0] - poly[k][0]),
                    abs(poly[k + 1][1] - poly[k][1]))
                for k in range(len(poly) - 1)
            )
            rank = 0 if length > 14 * self.pitch else 1
            report.traces.append(Trace(points_px=poly, rank=rank))

        # Salvage pass: every chip pin still unrouted gets routed to its
        # nearest free board edge in its outward direction. That guarantees
        # the result has no orphan chip pins floating with nothing attached,
        # and produces the off-board "trace leaves the board" silhouette.
        for idx, p in enumerate(chip_pins):
            if idx in routed_chip_pins:
                continue
            target = self._nearest_edge_cell(p)
            if target is None:
                continue
            path = self.a_star(p.cell_out, target)
            if path is None or len(path) < 2:
                continue
            for c in path:
                self.used[c] = True
            # Synthetic edge pin for the anchor-on-board-edge endpoint.
            edge_pin = Pin(
                cell_in=target, cell_out=target,
                direction=p.direction, owner=-1,
            )
            poly = self._simplify_to_pixels(p, path, edge_pin)
            report.traces.append(Trace(points_px=poly, rank=1))

        report.routed_nets = len(report.traces)
        return report

    def _nearest_edge_cell(self, pin: Pin) -> tuple[int, int] | None:
        """Cell on the board border reached by walking outward from `pin`."""
        c, r = pin.cell_out
        if pin.direction == "N":
            target = (c, 0)
        elif pin.direction == "S":
            target = (c, self.rows - 1)
        elif pin.direction == "W":
            target = (0, r)
        else:
            target = (self.cols - 1, r)
        if not self._in_bounds(target):
            return None
        if self.blocked[target] or self.used[target]:
            return None
        return target

    # ---- path -> pixel polyline ------------------------------------------

    def _simplify_to_pixels(
        self, pin_a: Pin, path: list[tuple[int, int]], pin_b: Pin
    ) -> list[tuple[int, int]]:
        # 1) Convert cells to pixel coordinates.
        px = [self._cell_to_px(c) for c in path]
        # 2) Prepend / append the chip-edge anchor so the trace lands on the
        #    component border, not floating in the safety pad.
        anchor_a = self._pin_anchor_px(pin_a)
        anchor_b = self._pin_anchor_px(pin_b)
        px = [anchor_a] + px + [anchor_b]
        # 3) Drop collinear waypoints so the SVG is just direction-change knots.
        out = [px[0]]
        for i in range(1, len(px) - 1):
            ax, ay = out[-1]
            bx, by = px[i]
            cx, cy = px[i + 1]
            dx1, dy1 = bx - ax, by - ay
            dx2, dy2 = cx - bx, cy - by
            # collinear iff direction cross-product is zero
            if dx1 * dy2 - dy1 * dx2 == 0:
                continue
            out.append(px[i])
        out.append(px[-1])
        return out

    def _pin_anchor_px(self, pin: Pin) -> tuple[int, int]:
        """Pixel point exactly on the owning component's edge under the pin,
        or on the board edge for synthetic off-board pins."""
        c, r = pin.cell_in
        x = c * self.pitch + self.pitch // 2
        y = r * self.pitch + self.pitch // 2
        if pin.owner < 0:
            if pin.direction == "N":
                return (x, 0)
            if pin.direction == "S":
                return (x, self.H)
            if pin.direction == "W":
                return (0, y)
            return (self.W, y)
        comp = self.components[pin.owner]
        if pin.direction == "N":
            return (x, comp.y)
        if pin.direction == "S":
            return (x, comp.y + comp.h)
        if pin.direction == "W":
            return (comp.x, y)
        return (comp.x + comp.w, y)
