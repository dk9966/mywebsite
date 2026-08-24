"""Render the raw generated shell, flat shaded, before any texturing runs.

The full preview goes through build_pillar and reads the exported .glb back,
which is the right check for the material but far too slow a loop for judging
silhouette and block layout. This draws shape.build() straight, so the only
thing on screen is geometry.

Run:  python render_shell.py [output.png]
"""
import os
import sys

import numpy as np
from PIL import Image

import config as cfg
import shape
from raster import render

VIEWS = [
    dict(cam=(8.6, 4.8, 10.0),  tgt=(0, 3.0, 0), fov=25, W=520, H=940),   # full body
    dict(cam=(-9.2, 4.4, -8.2), tgt=(0, 3.0, 0), fov=25, W=520, H=940),   # far side
    dict(cam=(3.0, 3.2, 3.4),   tgt=(0, 2.9, 0), fov=24, W=520, H=940),   # waist
    dict(cam=(2.6, 6.7, 2.9),   tgt=(0, 5.5, 0), fov=30, W=520, H=940),   # top ring
    dict(cam=(0.4, 12.5, 0.8),  tgt=(0, 5.3, 0), fov=21, W=520, H=940),   # plan
    dict(cam=(4.2, 1.6, 4.5),   tgt=(0, 0.8, 0), fov=26, W=520, H=940),   # foot
]

MATS = {0: {'base': np.full((2, 2, 3), 0.055),
            'orm': np.stack([np.ones((2, 2)), np.full((2, 2), 0.42),
                             np.zeros((2, 2))], -1),
            'lut': None}}


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    out = sys.argv[1] if len(sys.argv) > 1 else '../island_pillar_shell.png'
    idx, pos, info = shape.build(cfg.SHAPE)
    print('columns %d, rows %d' % (info['columns'], info['rows']))
    print('audit: %s' % shape.audit(idx, pos))

    uv = np.zeros((len(pos), 2))
    frames = [render(pos, idx, uv, uv, np.zeros(len(idx), int), MATS, **v)
              for v in VIEWS]
    Image.fromarray(np.concatenate(frames, 1)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
