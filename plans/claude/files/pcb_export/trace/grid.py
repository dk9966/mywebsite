"""Snapped routing grid with keepouts and trace occupancy (8-connected)."""
from __future__ import annotations

from typing import Optional

from .models import Keepout, PlacedComponent


CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
NEIGHBOURS = CARDINAL + DIAGONAL


class RoutingGrid:
    def __init__(
        self,
        *,
        x0: float,
        z0: float,
        x1: float,
        z1: float,
        pitch: float,
    ) -> None:
        self.x0 = x0
        self.z0 = z0
        self.pitch = pitch
        self.cols = max(8, int((x1 - x0) / pitch) + 1)
        self.rows = max(8, int((z1 - z0) / pitch) + 1)
        self.blocked = [[False] * self.rows for _ in range(self.cols)]
        self.used = [[False] * self.rows for _ in range(self.cols)]
        self.reserved_edges: set[tuple] = set()

    def world_to_cell(self, x: float, z: float) -> tuple[int, int]:
        c = int(round((x - self.x0) / self.pitch))
        r = int(round((z - self.z0) / self.pitch))
        return (max(0, min(self.cols - 1, c)), max(0, min(self.rows - 1, r)))

    def cell_to_world(self, c: int, r: int) -> tuple[float, float]:
        x = self.x0 + c * self.pitch
        z = self.z0 + r * self.pitch
        return (x, z)

    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def mark_keepout(self, box: Keepout) -> None:
        c0, r0 = self.world_to_cell(box.x0, box.z0)
        c1, r1 = self.world_to_cell(box.x1, box.z1)
        for c in range(c0, c1 + 1):
            for r in range(r0, r1 + 1):
                if self.in_bounds(c, r):
                    self.blocked[c][r] = True

    def mark_components(self, components: list[PlacedComponent]) -> None:
        for comp in components:
            self.mark_keepout(comp.route_block)

    def free(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r):
            return False
        return not self.blocked[c][r]

    def available(self, c: int, r: int, goal: Optional[tuple[int, int]] = None) -> bool:
        if not self.free(c, r):
            return False
        if goal == (c, r):
            return True
        return not self.used[c][r]

    @staticmethod
    def _edge_key(a: tuple[int, int], b: tuple[int, int]) -> tuple:
        return (a, b) if a < b else (b, a)

    @staticmethod
    def _crossing_edge(a: tuple[int, int], b: tuple[int, int]) -> Optional[tuple]:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if abs(dx) != 1 or abs(dy) != 1:
            return None
        c = (a[0], b[1])
        d = (b[0], a[1])
        return RoutingGrid._edge_key(c, d)

    def edge_available(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        ek = self._edge_key(a, b)
        if ek in self.reserved_edges:
            return False
        crossing = self._crossing_edge(a, b)
        if crossing is not None and crossing in self.reserved_edges:
            return False
        return True

    def neighbors8(
        self,
        c: int,
        r: int,
        goal: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for dc, dr in NEIGHBOURS:
            nc, nr = c + dc, r + dr
            if self.available(nc, nr, goal):
                out.append((nc, nr))
        return out

    def reserve_path(self, path: list[tuple[int, int]]) -> None:
        for c, r in path:
            self.used[c][r] = True
        for i in range(len(path) - 1):
            ek = self._edge_key(path[i], path[i + 1])
            self.reserved_edges.add(ek)
            crossing = self._crossing_edge(path[i], path[i + 1])
            if crossing is not None:
                self.reserved_edges.add(crossing)
