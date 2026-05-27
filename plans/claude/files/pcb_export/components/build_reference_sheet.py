"""
build_reference_sheet.py
========================

Builds a "component reference sheet" GLB: an 8-row by 20-column grid showing
all the component variations available, with colored row markers identifying
each family.

Useful for:
  - Visually previewing the entire component catalog
  - Confirming that a new variation you added renders correctly
  - Sharing the catalog with a teammate

USAGE
-----
    python build_reference_sheet.py

Writes `outputs/component_reference.glb`.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import trimesh
from trimesh import creation

from component_builders import (
    ROWS, BOARD_T, BOARD_MAT, mat, _vis,
)

# ---------- layout constants ----------
CELL_W = 3.0
CELL_D = 3.0
N_COLS = max(len(variations) for _, variations in ROWS)
N_ROWS = len(ROWS)

BOARD_W = CELL_W * N_COLS + 3.0  # extra room for left marker tiles
BOARD_D = CELL_D * N_ROWS + 2.0

# Row marker colors (one per family) - desaturated grayscale with subtle tint
ROW_COLORS = [
    [0.40, 0.36, 0.36, 1.0],
    [0.45, 0.42, 0.36, 1.0],
    [0.50, 0.48, 0.40, 1.0],
    [0.40, 0.44, 0.40, 1.0],
    [0.36, 0.42, 0.46, 1.0],
    [0.38, 0.40, 0.46, 1.0],
    [0.44, 0.40, 0.46, 1.0],
    [0.50, 0.50, 0.52, 1.0],
]

# ---------- build the scene ----------
scene = trimesh.Scene()

# Big dark board
board = creation.box(extents=[BOARD_W, BOARD_T, BOARD_D])
_vis(board, BOARD_MAT)
scene.add_geometry(board, geom_name='board')

all_part_count = 0
for row_i, (row_name, variations) in enumerate(ROWS):
    row_z = (row_i - (N_ROWS - 1) / 2) * CELL_D

    # Color-coded marker tile at the left of each row
    marker_mat = mat(ROW_COLORS[row_i], metallic=0.7, roughness=0.45)
    marker = creation.box(extents=[0.8, 0.05, CELL_D * 0.8])
    _vis(marker, marker_mat)
    marker_x = -BOARD_W / 2 + 0.6
    marker.apply_translation([marker_x, BOARD_T/2 + 0.025, row_z])
    scene.add_geometry(marker, geom_name=f'row_marker_{row_i}')

    # Each column = one variation builder
    for col_i, builder in enumerate(variations):
        col_x = (col_i - (N_COLS - 1) / 2) * CELL_W + 0.9
        try:
            parts = builder()
        except Exception as e:
            print(f'  Builder failed row {row_i} col {col_i}: {e}')
            continue
        for part_j, p in enumerate(parts):
            q = p.copy()
            q.apply_translation([col_x, 0, row_z])
            safe_name = row_name.replace(' ', '_').replace('/', '')
            scene.add_geometry(q, geom_name=f'r{row_i}_{safe_name}_c{col_i}_p{part_j}')
            all_part_count += 1

print(f'Rows: {N_ROWS}, Cols (max): {N_COLS}')
print(f'Total parts: {all_part_count}')
print(f'Board: {BOARD_W:.1f} x {BOARD_D:.1f}')

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'outputs')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'component_reference.glb')
scene.export(out_path)
print(f'Exported {out_path}  ({os.path.getsize(out_path)/1024:.1f} KB)')
