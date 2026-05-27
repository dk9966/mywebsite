"""
pcb_layout.py
=============

Grid-based PCB layout planner with controllable family counts and spatial
distribution. Decoupled from any specific mesh library - this module produces a
**layout plan** (a list of placements), and a separate module (mesh_builder.py)
materializes that plan into actual 3D meshes.

USAGE
-----

>>> from pcb_layout import LayoutPlanner, FamilySpec
>>>
>>> families = {
...     "qfp":       FamilySpec(count=15, footprint=(2,2), distributed=True, regions=(3,2)),
...     "dip":       FamilySpec(count=25, footprint=(2,1)),
...     "heatsink":  FamilySpec(count=6,  footprint=(2,2), distributed=True, regions=(2,2)),
...     "cap":       FamilySpec(count=40, footprint=(1,1)),
...     "smd":       FamilySpec(count=60, footprint=(1,1)),
...     "octagon":   FamilySpec(count=8,  footprint=(1,1)),
...     "header":    FamilySpec(count=10, footprint=(2,1)),
...     "connector": FamilySpec(count=10, footprint=(2,1)),
... }
>>>
>>> planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
>>> plan = planner.plan(families, seed=42)
>>> for placement in plan:
...     print(placement.family, placement.cell, placement.world_xz)


ALGORITHM
---------

1. Sort families by `priority` (default: largest footprint first).
2. For each family in priority order:
     a. If `distributed=True`, divide the board into `regions` (e.g. 3x2 = 6
        regions). Distribute the requested count across regions, weighted by
        region area. Each region gets at least `count // n_regions` items, and
        the remainder is randomly distributed.
     b. For each item to place:
        - If distributed: restrict candidate cells to this region
        - Try candidate cells in randomized order; place at the first free fit
     c. If a family can't meet its target, record the shortfall and continue
3. Optionally fill remaining cells with a `filler_family`.

This guarantees:
  - Exact counts per family (subject to board having enough space)
  - Even distribution of marked families across regions
  - Big components placed first while board is open
  - Total reproducibility via seed
"""

from dataclasses import dataclass, field
from typing import Optional
import random
import math


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FamilySpec:
    """How many of this family to place, and how."""
    count: int                              # target number to place
    footprint: tuple = (1, 1)               # cells (cols, rows) it occupies
    distributed: bool = False               # require even spread across regions?
    regions: tuple = (3, 2)                 # if distributed, (n_cols, n_rows)
                                            #   division of the board
    priority: Optional[int] = None          # lower = placed first; default
                                            #   inferred from footprint
    allow_rotation: bool = False            # may swap footprint to (rows,cols)?
    min_per_region: Optional[int] = None    # override the auto-computed minimum


@dataclass
class Placement:
    """The result of placing one component."""
    family: str
    cell: tuple                # (col, row) of the lower-left cell
    footprint: tuple           # (n_cols, n_rows) actually placed (may be rotated)
    world_xz: tuple            # (x, z) of the footprint center in world coords
    region: Optional[tuple] = None    # (region_col, region_row) if distributed


@dataclass
class LayoutReport:
    """Summary of what the planner achieved."""
    placements: list = field(default_factory=list)
    requested: dict = field(default_factory=dict)
    placed: dict = field(default_factory=dict)
    shortfall: dict = field(default_factory=dict)
    grid_fill: float = 0.0


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class LayoutPlanner:
    """
    Plan component placements on a grid.

    The grid is `grid_cols x grid_rows` cells. Each cell is `cell_size` units
    wide and tall. World origin is at the grid center.

    `padding` is included implicitly in cell_size: if your components are W
    units wide and you want G units gap between neighbors, use cell_size = W + G.
    """

    def __init__(self, grid_cols: int, grid_rows: int, cell_size: float = 1.4):
        self.cols = grid_cols
        self.rows = grid_rows
        self.cell = cell_size
        # 2D occupancy: None = free, otherwise an index into placements
        self.grid = [[None for _ in range(grid_rows)] for _ in range(grid_cols)]
        self.placements: list[Placement] = []

    # ---------- coordinate helpers ----------

    def cell_to_world(self, col: int, row: int, fp_w: int, fp_h: int) -> tuple:
        """World (x, z) of the center of a footprint anchored at (col, row)."""
        center_col = col + fp_w / 2 - 0.5
        center_row = row + fp_h / 2 - 0.5
        x = (center_col + 0.5 - self.cols / 2) * self.cell
        z = (center_row + 0.5 - self.rows / 2) * self.cell
        return (x, z)

    def board_size(self) -> tuple:
        return (self.cols * self.cell, self.rows * self.cell)

    # ---------- core placement primitives ----------

    def _fits(self, col: int, row: int, fp_w: int, fp_h: int) -> bool:
        if col < 0 or row < 0:
            return False
        if col + fp_w > self.cols or row + fp_h > self.rows:
            return False
        for c in range(col, col + fp_w):
            for r in range(row, row + fp_h):
                if self.grid[c][r] is not None:
                    return False
        return True

    def _mark(self, col, row, fp_w, fp_h, placement_idx):
        for c in range(col, col + fp_w):
            for r in range(row, row + fp_h):
                self.grid[c][r] = placement_idx

    def _place(self, family: str, col: int, row: int,
               fp_w: int, fp_h: int, region=None) -> Placement:
        idx = len(self.placements)
        self._mark(col, row, fp_w, fp_h, idx)
        wx, wz = self.cell_to_world(col, row, fp_w, fp_h)
        p = Placement(
            family=family,
            cell=(col, row),
            footprint=(fp_w, fp_h),
            world_xz=(wx, wz),
            region=region,
        )
        self.placements.append(p)
        return p

    # ---------- region helpers ----------

    def _region_bounds(self, region_grid, region_col, region_row):
        """Cell bounds (c0, c1, r0, r1) of region (region_col, region_row).
        region_grid is (n_region_cols, n_region_rows).
        """
        nrc, nrr = region_grid
        c0 = (region_col * self.cols) // nrc
        c1 = ((region_col + 1) * self.cols) // nrc
        r0 = (region_row * self.rows) // nrr
        r1 = ((region_row + 1) * self.rows) // nrr
        return (c0, c1, r0, r1)

    def _cells_in_region(self, region_grid, region_col, region_row):
        c0, c1, r0, r1 = self._region_bounds(region_grid, region_col, region_row)
        return [(c, r) for c in range(c0, c1) for r in range(r0, r1)]

    # ---------- family placement ----------

    def _try_place_family_item(self, family, fp_w, fp_h,
                                candidate_cells, rng,
                                allow_rotation=False, region=None):
        """Try to place one item from a family in any of the candidate cells.
        Returns True on success."""
        random.Random(rng.random()).shuffle(candidate_cells)
        # rotation: optionally try the rotated footprint as well
        orientations = [(fp_w, fp_h)]
        if allow_rotation and fp_w != fp_h:
            orientations.append((fp_h, fp_w))
        rng.shuffle(orientations)
        for (col, row) in candidate_cells:
            for (w, h) in orientations:
                if self._fits(col, row, w, h):
                    self._place(family, col, row, w, h, region=region)
                    return True
        return False

    def _distribute_count_to_regions(self, count, n_regions, rng):
        """Split `count` items across n_regions slots, biased to be roughly equal."""
        base = count // n_regions
        remainder = count - base * n_regions
        per_region = [base] * n_regions
        # randomly assign the remainder
        slots = list(range(n_regions))
        rng.shuffle(slots)
        for i in range(remainder):
            per_region[slots[i]] += 1
        return per_region

    def _place_family(self, family_name: str, spec: FamilySpec, rng):
        """Place all items of one family."""
        fp_w, fp_h = spec.footprint
        placed = 0

        if spec.distributed:
            nrc, nrr = spec.regions
            n_regions = nrc * nrr
            per_region = self._distribute_count_to_regions(spec.count, n_regions, rng)
            if spec.min_per_region is not None:
                per_region = [max(spec.min_per_region, p) for p in per_region]

            region_order = [(rc, rr) for rc in range(nrc) for rr in range(nrr)]
            rng.shuffle(region_order)
            for region_idx, (rc, rr) in enumerate(region_order):
                want = per_region[rc * nrr + rr]
                cells = self._cells_in_region(spec.regions, rc, rr)
                for _ in range(want):
                    ok = self._try_place_family_item(
                        family_name, fp_w, fp_h,
                        list(cells), rng,
                        allow_rotation=spec.allow_rotation,
                        region=(rc, rr),
                    )
                    if ok:
                        placed += 1
                    else:
                        # this region is full, give up on remaining in this region
                        break
            # second pass: any remaining count tries the WHOLE BOARD
            # (catches the shortfall when one region was already full)
            remaining = spec.count - placed
            if remaining > 0:
                all_cells = [(c, r) for c in range(self.cols) for r in range(self.rows)]
                for _ in range(remaining):
                    ok = self._try_place_family_item(
                        family_name, fp_w, fp_h,
                        list(all_cells), rng,
                        allow_rotation=spec.allow_rotation,
                    )
                    if ok:
                        placed += 1
                    else:
                        break
        else:
            all_cells = [(c, r) for c in range(self.cols) for r in range(self.rows)]
            for _ in range(spec.count):
                ok = self._try_place_family_item(
                    family_name, fp_w, fp_h,
                    list(all_cells), rng,
                    allow_rotation=spec.allow_rotation,
                )
                if ok:
                    placed += 1
                else:
                    break

        return placed

    # ---------- top-level plan ----------

    def plan(self, families: dict, *, seed: int = 0,
             filler_family: Optional[str] = None) -> LayoutReport:
        """
        Plan placements.

        families: dict mapping name -> FamilySpec
        seed:     RNG seed for reproducibility
        filler_family: if set, fills remaining 1x1 cells with this family name
                       (no FamilySpec needed; counts are unbounded)

        Returns a LayoutReport.
        """
        rng = random.Random(seed)

        # sort families by priority (low first). default priority = -footprint area
        items = list(families.items())
        def _key(item):
            name, spec = item
            if spec.priority is not None:
                return spec.priority
            return -spec.footprint[0] * spec.footprint[1]
        items.sort(key=_key)

        report = LayoutReport()
        report.requested = {name: spec.count for name, spec in items}

        for name, spec in items:
            placed = self._place_family(name, spec, rng)
            report.placed[name] = placed
            report.shortfall[name] = spec.count - placed

        if filler_family is not None:
            fill_count = 0
            for c in range(self.cols):
                for r in range(self.rows):
                    if self.grid[c][r] is None:
                        self._place(filler_family, c, r, 1, 1)
                        fill_count += 1
            report.placed[filler_family] = report.placed.get(filler_family, 0) + fill_count

        used = sum(1 for c in range(self.cols) for r in range(self.rows)
                   if self.grid[c][r] is not None)
        report.grid_fill = used / (self.cols * self.rows)
        report.placements = list(self.placements)
        return report


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    families = {
        "qfp":       FamilySpec(count=15, footprint=(2, 2),
                                 distributed=True, regions=(3, 2)),
        "heatsink":  FamilySpec(count=6,  footprint=(2, 2),
                                 distributed=True, regions=(2, 2)),
        "dip":       FamilySpec(count=20, footprint=(2, 1), allow_rotation=True),
        "header":    FamilySpec(count=12, footprint=(2, 1), allow_rotation=True),
        "connector": FamilySpec(count=10, footprint=(2, 1), allow_rotation=True),
        "octagon":   FamilySpec(count=8,  footprint=(1, 1)),
        "cap":       FamilySpec(count=40, footprint=(1, 1)),
        "smd":       FamilySpec(count=50, footprint=(1, 1)),
    }
    planner = LayoutPlanner(grid_cols=22, grid_rows=14, cell_size=1.4)
    report = planner.plan(families, seed=42, filler_family="smd")
    print(f"Requested: {report.requested}")
    print(f"Placed:    {report.placed}")
    print(f"Shortfall: {report.shortfall}")
    print(f"Grid fill: {report.grid_fill:.1%}")
    print(f"Total placements: {len(report.placements)}")
    # Show what the grid looks like
    grid = planner.grid
    print('\nGrid:')
    for r in range(planner.rows):
        line = ''
        for c in range(planner.cols):
            idx = grid[c][r]
            if idx is None:
                line += ' . '
            else:
                fam = report.placements[idx].family
                line += f' {fam[0].upper()} '
        print(line)
