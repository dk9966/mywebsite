"""Builds the cave's section titles as signed-distance fields (models/cave/labels/*.png).

The titles are the neon lettering from the type board (label-board.webp). The
board's stroke cores are thresholded at 4x for smooth edges, and the distance
field lets the cave draw them razor sharp at any size. The board only has
"Project": its trailing "s" is lifted from "Experiences" (same face).

    python3 secret-base/cave-web/make_label_sdf.py

Units match CaveLabels.tsx: the field is 2 texels per board pixel, spread 14 px.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "models" / "cave" / "labels"
BANDS = {"projects": (116, 296), "about": (318, 476), "experiences": (484, 664), "contact": (684, 836)}
UP = 4          # supersampling for the threshold
TEXEL = 2       # output texels per board pixel
SPREAD = 14     # board pixels of distance kept on each side of the edge
PAD = SPREAD + 2
CORE = 205      # green level halfway between the glow shoulder (~157) and the stroke core (255)
LETTER_GAP = 25  # board pixels between letters of this face


def green(name):
    y0, y1 = BANDS[name]
    return np.asarray(Image.open(HERE / "label-board.webp").convert("RGB"))[y0:y1, :, 1]


def ink_columns(band):
    cols = np.where((band > CORE).any(axis=0))[0]
    return cols.min(), cols.max() + 1


def title(name):
    band = green(name)
    x0, x1 = ink_columns(band)
    if name != "projects":
        return band[:, x0:x1]
    # "Project" + the "s" of "Experiences", baseline-aligned on the "c" and given the board's letter gap.
    s_band = green("experiences")
    s_cols = (s_band > CORE).any(axis=0)
    s1 = np.where(s_cols)[0].max() + 1
    s0 = s1 - 85
    letter = s_band[:, s0:s1]
    base = band.copy()
    c_rows = np.where((band[:, 801:884] > CORE).any(axis=1))[0]
    s_rows = np.where((letter > CORE).any(axis=1))[0]
    shift = c_rows.max() - s_rows.max()
    left = 957 + LETTER_GAP
    canvas = np.zeros((band.shape[0], left + letter.shape[1] + 4), band.dtype)
    canvas[:, : band.shape[1]] = base[:, : canvas.shape[1]] if band.shape[1] >= canvas.shape[1] else base
    # Paste the "s" (rows shifted so baselines agree).
    for r in range(letter.shape[0]):
        rr = r + shift
        if 0 <= rr < canvas.shape[0]:
            canvas[rr, left : left + letter.shape[1]] = np.maximum(canvas[rr, left : left + letter.shape[1]], letter[r])
    return canvas[:, x0 : left + letter.shape[1]]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name in BANDS:
        g = title(name)
        rows = np.where((g > CORE).any(axis=1))[0]
        g = g[max(rows.min() - 2, 0) : rows.max() + 3]
        big = np.asarray(Image.fromarray(g).resize((g.shape[1] * UP, g.shape[0] * UP), Image.LANCZOS))
        inside = np.pad(big >= CORE, PAD * UP)
        d = (distance_transform_edt(inside) - distance_transform_edt(~inside)) / UP   # board px, positive inside
        d = d[:: UP // TEXEL, :: UP // TEXEL]
        enc = np.clip(d / SPREAD * 0.5 + 0.5, 0, 1) * 255
        Image.fromarray(enc.astype(np.uint8), "L").save(OUT / f"{name}.png", optimize=True)
        print(name, enc.shape)
