"""Procedural texture generation for the railing kit.

Exactly one image is generated:

  edge_lut.png    a 2D falloff lookup table that turns the per-vertex
                  "distance to the nearest sharp edge" data baked into UV1
                  into a crisp highlight along every hard edge.

Nothing else is textured. The bridge's deck plate has no counterpart here --
there is no walking surface, and the island pillar established that surface
noise over dark alloy reads as wet photoreal stone rather than machined metal.
The silhouette and the edge highlights carry the whole model, which is also
why the file is a couple of hundred kilobytes rather than several megabytes.

The blue lenses and the lantern are not textures either. They are geometry
with their own emissive materials, so they stay crisp at any zoom and cost one
flat colour each -- see build_railings.py.
"""
import numpy as np
from PIL import Image

from config import LUT


def _srgb(linear):
    return (np.clip(linear, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def _profile(t, colour, power, core_width, core_boost):
    """Falloff for an edge highlight. t = 0 sits on the edge, 1 at the limit."""
    f = np.clip((1.0 - t) ** power, 0, 1)
    boost = 1.0 + core_boost * np.clip(1 - t / max(core_width, 1e-6), 0, 1)
    return np.asarray(colour)[None, :] * (f * boost)[:, None]


def make_edge_lut(path):
    """Edge falloff LUT.

    UV1 carries one distance per edge slot, stored as ``1 - d/w``: 1 right on
    the edge, 0 at the band limit, negative beyond it. The LUT's zero end sits
    at axis 0, so with CLAMP_TO_EDGE everything outside the band is handled for
    free -- which is what lets the per-vertex distances stay unclamped and
    therefore linear, and linearity is what keeps the line crisp.

    The LUT is 2D because two edge slots are encoded per triangle. The stored
    value is the sum of each axis' profile, so a corner where two edges meet
    reads brighter than either alone -- which is what makes the post caps and
    the octagonal pillar cap pick out their corners.
    """
    L = LUT['size']
    axis = np.linspace(0, 1, L)
    t = 1.0 - axis                                   # 0 on the edge, 1 at the limit
    # 'colour' is the final intended value; the material's emissiveStrength
    # multiplies the whole texture, so pre-divide to cancel it out here
    colour = np.array(LUT['colour']) / LUT['emissive_strength']
    prof = np.clip(_profile(t, colour, LUT['falloff_power'],
                            LUT['core_width'], LUT['core_boost']), 0, 1)

    lut = np.clip(prof[None, :, :] + prof[:, None, :], 0, 1)   # u along x, v along y
    Image.fromarray(_srgb(lut)).save(path)
    return path
