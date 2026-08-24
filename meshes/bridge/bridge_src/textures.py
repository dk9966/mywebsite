"""Procedural texture generation for the bridge.

Two things get generated:

  edge_lut.png    a 2D falloff lookup table that turns the per-vertex
                  "distance to nearest sharp edge" data baked into UV1 into a
                  crisp highlight along every hard edge.

  deck plate      the walking surface: brushed alloy with a bolt at each end
                  of every plank and a painted joint at the plank pitch, so
                  the un-grooved abutment landings still read as planked.

Everything else on the model is a flat baseColorFactor, as on the island
pillar: surface noise on the body made that asset read as wet photoreal stone,
and the same is true of pretending dark alloy has visible grain everywhere.
"""
import numpy as np
from PIL import Image

from noise import fbm, to_normal
from config import PLATE, LUT, DECK


def _srgb(linear):
    return (np.clip(linear, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


# ---------------------------------------------------------------- edge LUT
def _plain_profile(t, colour, power, core_width, core_boost):
    """Falloff for an ordinary edge highlight. t=0 sits on the edge."""
    f = np.clip((1.0 - t) ** power, 0, 1)
    boost = 1.0 + core_boost * np.clip(1 - t / max(core_width, 1e-6), 0, 1)
    return np.asarray(colour)[None, :] * (f * boost)[:, None]


def make_edge_lut(path):
    """Edge falloff LUT.

    UV1 carries one distance per edge slot, stored as ``1 - d/w``: 1 right on
    the edge, 0 at the band limit, negative beyond it. The LUT's zero end sits
    at axis 0, so with CLAMP_TO_EDGE everything outside the band is handled for
    free -- which is what lets the per-vertex distances stay unclamped and
    therefore linear.

    The LUT is 2D because two edge slots are encoded per triangle; the stored
    value is simply the sum of each axis' profile, so a corner where two edges
    meet reads brighter than either alone.
    """
    L = LUT['size']
    axis = np.linspace(0, 1, L)
    t = 1.0 - axis                                   # 0 on the edge, 1 at the limit
    # 'colour' is the final intended value; the material's emissiveStrength
    # multiplies the whole texture, so pre-divide to cancel it out here
    colour = np.array(LUT['colour']) / LUT['emissive_strength']
    prof = np.clip(_plain_profile(t, colour, LUT['falloff_power'],
                                  LUT['core_width'], LUT['core_boost']), 0, 1)

    lut = np.clip(prof[None, :, :] + prof[:, None, :], 0, 1)   # u along x, v along y
    Image.fromarray(_srgb(lut)).save(path)
    return path


# ---------------------------------------------------------------- deck plate
def _box_downsample(a, factor):
    if factor == 1:
        return a
    h, w = a.shape[:2]
    tail = a.shape[2:]
    return a.reshape(h // factor, factor, w // factor, factor, *tail).mean((1, 3))


def _plate(M):
    """One tile of deck: u spans a plank pitch, v spans the deck width.

    The plank is centred on u=0.5 so the painted joint lands on the tile
    boundary, which is exactly where the real groove between plank prisms is.
    That alignment is what lets the abutment landings -- solid plate with no
    grooves cut in them -- carry on the plank rhythm without a seam in the
    pattern.
    """
    P = PLATE
    yy, xx = np.mgrid[0:M, 0:M]
    U = (xx / M).astype(np.float32)
    V = (yy / M).astype(np.float32)
    del xx, yy

    # aspect of the tile in world units, so round things stay round
    pitch = (DECK['plank_x'][1] - DECK['plank_x'][0]) / DECK['planks']
    span = 2.0 * DECK['uv_half_width']
    aspect = span / pitch

    # Brushed grain, stretched along the plank -- the plank's long axis is Z,
    # which is v here. Holding rows constant in blocks smears the noise along
    # v; mixing the unstretched field back in stops it reading as bar code.
    g = fbm(M, P['grain_beta'], P['grain_seed']).astype(np.float32)
    stretch = 8
    grain = 0.5 * (g[(np.arange(M) // stretch * stretch) % M] + g)
    del g

    # painted plank joint at the tile boundary
    du = np.minimum(U, 1.0 - U)
    seam = 1.0 - np.clip(du / P['seam_width'], 0, 1)

    # one bolt at each end of the plank
    ru = P['rivet_r'] * aspect
    bolt = np.zeros_like(U)
    for vc in P['rivet_v']:
        r = np.hypot((U - 0.5) / ru, (V - vc) / P['rivet_r'])
        bolt = np.maximum(bolt, np.clip(1.0 - r, 0, 1) ** 0.45)

    height = (0.5
              - P['seam_depth'] * seam
              + P['rivet_height'] * bolt
              + (grain - 0.5) * P['grain_relief'])

    lum = P['lum'] + P['lum_jitter'] * (grain - 0.5) * 2.0 + 0.0016 * bolt
    colour = np.stack([lum * 0.92, lum * 0.98, lum * 1.16], -1)
    mortar = np.array(P['seam_lum'], np.float32)[None, None, :]
    s = np.clip(seam, 0, 1)[..., None]
    colour = colour * (1 - s) + mortar * s
    return np.clip(colour, 0, 1), np.clip(height, 0, 1).astype(np.float32), seam


def make_plate(basecolor_path, normal_path, orm_path):
    """Deck maps, rendered supersampled and box-filtered down.

    The joint and the bolt rims are thin hard-edged shapes. Generated straight
    at output resolution they are one or two texels wide with no
    anti-aliasing, and they bead into dotted lines at grazing angles -- which
    on a deck seen almost edge-on is most of the time.
    """
    M, ss = PLATE['size'], PLATE['supersample']
    colour, height, seam = _plate(M * ss)

    Image.fromarray(_srgb(_box_downsample(colour, ss))).save(basecolor_path)

    hd = _box_downsample(height, ss)
    Image.fromarray(to_normal(hd, PLATE['normal_strength'])).save(normal_path)

    sd = _box_downsample(seam, ss)
    rough = np.clip(PLATE['roughness'] + 0.16 * sd, 0.2, 1.0)
    orm = np.stack([np.ones_like(rough), rough, np.zeros_like(rough)], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(orm_path)
