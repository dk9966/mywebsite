"""Procedural texture generation for the island pillar.

One thing gets generated:

  edge_lut.png   a 2D falloff lookup table that turns the per-vertex
                 "distance to nearest sharp edge" data baked into UV1
                 into a crisp emissive line along every hard edge.

The circular brick paving maps that used to live here are gone: the platform
is real brick geometry now (shape._paving), and its joint lines come out of
the same edge LUT as every other edge on the pillar.

The pillar body itself has NO textures -- it is a flat baseColorFactor.
Surface noise made the asset read as wet/photoreal, which is not the look;
the geometry and the edge highlights carry it instead.
"""
import numpy as np
from PIL import Image

from config import LUT


def _srgb(linear):
    return (np.clip(linear, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def _plain_profile(t, colour, power, core_width, core_boost):
    """Falloff for an ordinary edge highlight. t=0 sits on the edge."""
    f = np.clip((1.0 - t) ** power, 0, 1)
    boost = 1.0 + core_boost * np.clip(1 - t / max(core_width, 1e-6), 0, 1)
    return np.asarray(colour)[None, :] * (f * boost)[:, None]


def _glow_profile(t, LUT):
    """Falloff for a glow line, in three parts.

    A single curve cannot both stay pencil-thin and spread light onto the
    surrounding stone. So the profile is a hot near-white core over a saturated
    blue line over a broad, dim halo. The halo is what sells it as *glowing*
    rather than as a painted stripe -- it is standing in for the bloom a real
    engine would add, so the asset still reads correctly in a viewer without
    post-processing.
    """
    core = np.clip(1 - t / max(LUT['glow_core_width'], 1e-6), 0, 1) ** LUT['glow_core_power']
    line = np.clip((1.0 - t) ** LUT['glow_power'], 0, 1)
    halo = np.clip((1.0 - t) ** LUT['halo_power'], 0, 1)
    return (np.asarray(LUT['glow_core'])[None, :] * core[:, None]
            + np.asarray(LUT['glow_color'])[None, :] * line[:, None]
            + np.asarray(LUT['halo_color'])[None, :] * halo[:, None])


def make_edge_lut(path):
    """Two-profile edge falloff LUT.

    UV1 carries one packed value per edge slot. An ordinary edge maps its
    distance to ``plain_peak * (1 - d/w)`` and a glow edge to
    ``glow_peak + (1 - glow_peak) * d/w``. So an ordinary edge lives in the
    lower part of the axis with its peak inward, a glow edge lives in the upper
    part with its peak inward, and both fall off toward a texture border where
    the LUT is zero. CLAMP_TO_EDGE then handles anything outside the band for
    free, which is what lets the per-vertex distances stay unclamped and
    therefore linear.

    The LUT is 2D because two edge slots are encoded per triangle; the stored
    value is simply the sum of each axis' profile.
    """
    L = LUT['size']
    axis = np.linspace(0, 1, L)
    prof = np.zeros((L, 3))
    pk, gk = LUT['plain_peak'], LUT['glow_peak']

    # Each profile plateaus at its peak value across the gap rather than
    # dropping off a cliff there. Nothing samples the gap, but this keeps
    # bilinear taps next to the peak from reading a neighbour of zero and
    # halving the brightness of the line core.
    lower = axis <= 0.5
    t = np.clip(1.0 - axis[lower] / pk, 0, 1)        # 0 on the edge, 1 at band limit
    # plain_color is the final intended value; the material's emissiveStrength
    # multiplies the whole texture, so pre-divide to cancel it out here
    plain = np.array(LUT['plain_color']) / LUT['emissive_strength']
    prof[lower] = _plain_profile(t, plain, LUT['falloff_power'],
                                 LUT['core_width'], LUT['core_boost'])

    upper = ~lower
    t = np.clip((axis[upper] - gk) / (1.0 - gk), 0, 1)
    prof[upper] = _glow_profile(t, LUT)

    prof = np.clip(prof, 0, 1)
    lut = np.clip(prof[None, :, :] + prof[:, None, :], 0, 1)   # u along x, v along y
    Image.fromarray(_srgb(lut)).save(path)
    return path
