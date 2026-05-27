"""
build_random_pcb.py
===================

Main driver: configure component counts, run the planner, export the GLB.

Tweak the FAMILIES dict to control what gets placed and where:

  - count:        exact target number to place (planner achieves this if
                  the board has space)
  - footprint:    (cols, rows) of grid cells the component occupies
  - distributed:  if True, force spread across the board's regions
  - regions:      (n_cols, n_rows) division of the board for distribution
                  e.g. (3, 2) = 6 board sections, item gets count/6 in each
  - allow_rotation: planner may swap to (rows, cols) if helpful
  - priority:     placement order override (default: largest first)

Run:
    python build_random_pcb.py

Writes outputs/random_pcb.glb
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcb_layout import LayoutPlanner, FamilySpec
from mesh_builder import build_scene, FAMILY_BUILDERS


# ============================================================
# CONFIGURATION
# ============================================================

FAMILIES = {
    # Large chips - spread across 3x2 = 6 board regions so they appear
    # in every section. Each region will get count // 6 = 3 QFPs.
    'qfp':       FamilySpec(count=18, footprint=(2, 2),
                            distributed=True, regions=(3, 2)),

    # Heatsinks - spread across 2x2 = 4 board quadrants.
    'heatsink':  FamilySpec(count=8,  footprint=(2, 2),
                            distributed=True, regions=(2, 2)),

    # Medium 2x1 components - DIPs, headers, connectors.
    # allow_rotation lets the planner orient them horizontally OR vertically.
    'dip':       FamilySpec(count=25, footprint=(2, 1), allow_rotation=True),
    'header':    FamilySpec(count=15, footprint=(2, 1), allow_rotation=True),
    'connector': FamilySpec(count=12, footprint=(2, 1), allow_rotation=True),

    # Small 1x1 components
    'octagon':   FamilySpec(count=10, footprint=(1, 1)),
    'cap':       FamilySpec(count=35, footprint=(1, 1)),
    # smd is the filler - set via filler_family below, no FamilySpec needed
}

# Grid parameters
GRID_COLS = 22
GRID_ROWS = 14
CELL_SIZE = 1.4    # world units per cell. The 0.4 unit of slack inside each
                   # cell (vs the ~1.0 widest component) becomes the visible
                   # gap between adjacent placements.

# RNG seed - change for a different randomized layout
SEED = 42

# Wireframe render or solid mesh
WIREFRAME = True

# Output
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUT_DIR, 'random_pcb.glb')


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    planner = LayoutPlanner(grid_cols=GRID_COLS,
                             grid_rows=GRID_ROWS,
                             cell_size=CELL_SIZE)
    report = planner.plan(FAMILIES, seed=SEED, filler_family='smd')

    bw, bd = planner.board_size()
    print(f'Board:     {bw:.1f} x {bd:.1f} world units')
    print(f'Grid:      {GRID_COLS}x{GRID_ROWS} cells of {CELL_SIZE}')
    print(f'Grid fill: {report.grid_fill:.1%}')
    print()
    print(f'{"Family":<12} {"Requested":>10} {"Placed":>8} {"Short":>7}')
    print('-' * 42)
    for fam in sorted(report.placed.keys()):
        req = report.requested.get(fam, 0)
        plc = report.placed.get(fam, 0)
        sht = report.shortfall.get(fam, 0)
        print(f'{fam:<12} {req:>10} {plc:>8} {sht:>7}')
    print()
    print(f'Total placements: {len(report.placements)}')
    print()
    print(f'Building scene (wireframe={WIREFRAME})...')

    build_scene(report, planner, FAMILY_BUILDERS,
                out_path=OUTPUT_PATH,
                seed=SEED,
                wireframe=WIREFRAME,
                edge_radius=0.012,
                board_padding=1.5)

    sz = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f'Wrote {OUTPUT_PATH}  ({sz:.2f} MB)')
