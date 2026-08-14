"""Procedural texture generation for the island pillar.

Two things get generated:

  edge_lut.png   a 2D falloff lookup table that turns the per-vertex
                 "distance to nearest sharp edge" data baked into UV1
                 into a crisp emissive line along every hard edge.

  paving maps    the circular brick platform on top of the pillar:
                 concentric courses whose brick count scales with radius,
                 a wedge medallion in the middle and a radial kerb ring.

The pillar body itself has NO textures -- it is a flat baseColorFactor.
Surface noise made the asset read as wet/photoreal, which is not the look;
the geometry and the edge highlights carry it instead.
"""
import numpy as np
from PIL import Image

from noise import fbm, to_normal
from config import PAVING, LUT


def _srgb(linear):
    return (np.clip(linear, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def make_edge_lut(path):
    """Edge falloff LUT.

    UV1 carries (d0, d1) = distance to the two nearest sharp edges, already
    divided by the edge band width, so 0 sits exactly on an edge and >=1 is
    outside the band. The LUT stores falloff(min(d0, d1)); sampling it with
    CLAMP_TO_EDGE means values past the band simply read as zero.
    """
    L = LUT['size']
    u = np.linspace(0, 1, L)[None, :]
    v = np.linspace(0, 1, L)[:, None]
    t = np.minimum(u, v) * np.ones((L, L))
    f = (1.0 - t) ** LUT['falloff_power']
    f = np.clip(f + LUT['core_boost'] * np.clip(1 - t / LUT['core_width'], 0, 1),
                0, 1 + LUT['core_boost'] - 0.2)
    f = np.clip(f / f.max(), 0, 1)
    Image.fromarray(np.repeat(_srgb(f)[:, :, None], 3, 2)).save(path)
    return path


def make_paving(basecolor_path, normal_path, orm_path):
    """Circular brick paving for the top platform.

    Everything is derived from polar coordinates over a unit disc, so the
    texture is mapped with a simple planar XZ projection and the courses stay
    perfectly concentric on the mesh.
    """
    M = PAVING['size']
    rings = PAVING['rings']
    r_center = PAVING['center_radius']
    edge_band = PAVING['kerb_width']

    yy, xx = np.mgrid[0:M, 0:M]
    c = (M - 1) / 2
    X = (xx - c) / (M / 2)
    Y = (yy - c) / (M / 2)
    R = np.hypot(X, Y)
    TH = np.arctan2(Y, X)
    ang = (TH / (2 * np.pi)) % 1.0

    ring_lo, ring_hi = r_center, 1.0 - edge_band
    rw = (ring_hi - ring_lo) / rings
    # nudge the course boundaries with noise so they are not machine-perfect
    Rw = R + (fbm(M, 2.2, PAVING['wobble_seed']) - 0.5) * PAVING['wobble']

    ri = np.clip(np.floor((Rw - ring_lo) / rw), 0, rings - 1)
    # brick count per course grows with radius -> roughly constant arc length
    counts = np.array([max(6, int(round(2 * np.pi * (ring_lo + (k + 0.5) * rw)
                                        / PAVING['brick_arc']))) for k in range(rings)])
    counts = (counts // 2) * 2
    cnt = counts[ri.astype(int)]
    offset = np.where(ri.astype(int) % 2 == 0, 0.0, 0.5)   # stagger every other course
    seg = ang * cnt + offset
    si = np.floor(seg)

    # mortar = distance to the nearest course / brick boundary
    mort_r = np.minimum((Rw - ring_lo) / rw - ri, 1.0 - ((Rw - ring_lo) / rw - ri))
    mort_a = np.minimum(seg - si, 1.0 - (seg - si))
    inset = np.minimum(np.clip(mort_r / PAVING['mortar_radial'], 0, 1),
                       np.clip(mort_a / PAVING['mortar_angular'], 0, 1))
    course = np.clip(inset * 3.2, 0, 1)

    # centre medallion: radial wedges around a solid hub
    c_cnt = PAVING['center_wedges']
    cseg = ang * c_cnt
    cmr = np.clip((Rw - PAVING['hub_radius']) / (ring_lo - PAVING['hub_radius']), 0, 1)
    cm_a = np.minimum(cseg - np.floor(cseg), 1 - (cseg - np.floor(cseg)))
    centre = np.clip(np.minimum(cm_a / 0.14, np.minimum(cmr / 0.16, (1 - cmr) / 0.16)) * 3.0, 0, 1)
    centre = np.where(Rw < PAVING['hub_radius'], 1.0, centre)

    # outer kerb: narrow radial slabs
    k_cnt = PAVING['kerb_slabs']
    kseg = ang * k_cnt
    kt = np.minimum(kseg - np.floor(kseg), 1 - (kseg - np.floor(kseg)))
    kr = (Rw - ring_hi) / edge_band
    kerb = np.clip(np.minimum(kt / 0.16, np.minimum(kr / 0.20, (1 - kr) / 0.20)) * 3.0, 0, 1)
    kerb = np.where(R > 1.0, 0, kerb)

    in_ring = (Rw > ring_lo) & (Rw < ring_hi)
    in_centre = Rw <= ring_lo
    B = np.where(in_ring, course, np.where(in_centre, centre, kerb))

    # stable per-slab id -> tiny tonal jitter (kept small: flat is the look)
    ID = np.where(in_ring, ri.astype(int) * 1237 + si.astype(int) * 97,
                  np.where(in_centre, 5000 + np.floor(cseg).astype(int),
                           9000 + np.floor(kseg).astype(int)))
    h1 = ((ID * 2654435761) % 1000) / 1000.0

    lum = PAVING['slab_lum'] + PAVING['slab_jitter'] * h1
    slab = np.stack([lum * 0.90, lum * 0.97, lum * 1.20], -1)   # cool cast
    mortar = np.array(PAVING['mortar_lum'])[None, None, :] * np.ones((M, M, 3))
    Bs = np.clip(B, 0, 1)[..., None]
    Image.fromarray(_srgb(slab * Bs + mortar * (1 - Bs))).save(basecolor_path)

    # relief comes only from the mortar grooves
    Image.fromarray(to_normal(np.where(R > 1.0, 0, B), PAVING['normal_strength'])) \
         .save(normal_path)

    rough = np.clip(PAVING['roughness'] - 0.05 * Bs[..., 0], 0.2, 1.0)
    orm = np.stack([np.ones((M, M)), rough, np.zeros((M, M))], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(orm_path)
