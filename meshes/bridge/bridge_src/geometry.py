"""Procedural construction of the bridge.

The whole model is a union of axis-aligned prisms that are *sheared onto the
arch*: a prism's four top corners sit at ``deck(x) + offset`` rather than at a
constant height, so every part -- slab, planks, ribs, abutments -- bends with
the span for free and their faces stay planar. Long parts are cut into
segments, because a single prism would chord the arch instead of following it,
and because the visible block joints are the look.

Nothing is booleaned. Parts are deliberately sunk into each other and the
interior faces are deleted afterwards by ``reshape.remove_buried_faces``; see
the README for why that is easier than getting the joins exactly right.

The arch rise is not a chosen number. It is solved by bisection so that the
model's highest point lands exactly on ``ENVELOPE['height']``, which is what
makes the exported bounding box match the reference drawing to the millimetre.
"""
import numpy as np

import config as cfg


class Rel(float):
    """A height measured from the deck's walking surface rather than the ground."""


def deck(x, rise):
    """Walking surface of the deck at position x along the span."""
    t = np.clip(np.asarray(x, float) / cfg.HALF_L, -1.0, 1.0)
    return cfg.ARCH['base'] + rise * (1.0 - t * t) + cfg.ARCH['thickness']


def segments(x0, x1, n):
    e = np.linspace(x0, x1, n + 1)
    return list(zip(e[:-1], e[1:])), e[1:-1]


# ---------------------------------------------------------------- assembly
class Solid:
    """Accumulates prisms into a triangle soup, tagging every face."""

    # the six faces of a box as vertex keys (i=x, j=y, k=z), oriented later
    _QUADS = [[(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)],
              [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
              [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
              [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
              [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
              [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]]

    def __init__(self, rise):
        self.rise = rise
        self.pos = []
        self.faces = []
        self.tags = []

    # -- primitives ------------------------------------------------------
    def prism(self, x, z, ylo, yhi, tag):
        """One sheared box. ``ylo``/``yhi`` are absolute, or ``Rel`` of the deck.

        Because y varies only with x, all six faces stay perfectly planar even
        though the box is sheared -- which is what keeps the flat-shaded joints
        crisp and the tangents well defined.
        """
        x0, x1 = x
        z0, z1 = z
        c = {0: deck(x0, self.rise), 1: deck(x1, self.rise)}
        v = {}
        for i, xv in ((0, x0), (1, x1)):
            for j, yv in ((0, ylo), (1, yhi)):
                y = (c[i] + float(yv)) if isinstance(yv, Rel) else float(yv)
                for k, zv in ((0, z0), (1, z1)):
                    v[(i, j, k)] = (xv, y, zv)

        base = len(self.pos)
        keys = list(v)
        index = {k: base + n for n, k in enumerate(keys)}
        self.pos.extend(v[k] for k in keys)
        centre = np.mean([v[k] for k in keys], axis=0)

        for quad in self._QUADS:
            p = np.array([v[k] for k in quad])
            n = np.cross(p[1] - p[0], p[2] - p[0])
            if n @ (p.mean(0) - centre) < 0:            # orient outward
                quad = quad[::-1]
            a, b, c2, d = (index[k] for k in quad)
            self.faces.append((a, b, c2))
            self.faces.append((a, c2, d))
            self.tags.extend([tag, tag])

    def mirror(self, x, z, ylo, yhi, tag):
        """The same prism on both sides of the deck."""
        self.prism(x, z, ylo, yhi, tag)
        self.prism(x, (-z[1], -z[0]), ylo, yhi, tag)

    def run(self, x, z, ylo, yhi, tag, n, collar=None, skip=(), stride=1):
        """A long part, cut into ``n`` segments, with optional joint collars.

        Segmenting is not cosmetic: one prism spanning a whole run would chord
        the arch and sag by centimetres. The facet count and the collar count
        are therefore independent -- ``n`` is how closely the part tracks the
        curve, ``stride`` is how often a joint is dressed with a band. Banding
        every joint turns a long part into corrugation.
        """
        segs, joints = segments(x[0], x[1], n)
        for s in segs:
            self.mirror(s, z, ylo, yhi, tag)
        if collar is None:
            return
        cz, clo, chi, cw = collar
        for i, j in enumerate(joints):
            if i % stride != stride // 2:
                continue
            if any(a <= j <= b for a, b in skip):        # joint hidden inside another part
                continue
            self.mirror((j - cw / 2, j + cw / 2), cz, clo, chi, tag + '_collar')

    # -- output ----------------------------------------------------------
    def arrays(self):
        """Triangles, positions, per-face tags -- with vertices split per face.

        Sharing the eight corners of a prism between its twelve triangles is
        the natural way to build it and the wrong way to ship it. Two later
        passes need one vertex per corner *per face*: normal smoothing writes a
        different normal into each face that meets at a corner, and
        break_coplanar_ties nudges a single face without dragging its
        neighbours along. Welding is done where it is actually wanted -- inside
        the edge detector, by rounded position -- so nothing is lost.
        """
        faces = np.array(self.faces, np.int64)
        pos = np.array(self.pos, np.float64)[faces.reshape(-1)]
        return (np.arange(len(pos), dtype=np.int64).reshape(-1, 3), pos,
                np.array(self.tags, object))


def plank_spans():
    """(start, end) in x of every plank."""
    D = cfg.DECK
    px0, px1 = D['plank_x']
    pitch = (px1 - px0) / D['planks']
    half = (pitch - D['plank_gap']) / 2
    return [(px0 + (i + 0.5) * pitch - half, px0 + (i + 0.5) * pitch + half)
            for i in range(D['planks'])]


def slab_edges():
    """Where to cut the deck slab, which is not a free choice.

    The slab has to be faceted to follow the arch, but *where* the facets fall
    decides whether the deck has holes in it. A slab-top face is deleted only
    if every probe across it lands inside the solid, so a face that sits under
    a plank for most of its width but pokes into the gap beside it can still
    read as fully buried, get deleted, and leave a slit you can see the
    background through -- from above only, since the slab's underside is still
    there and is single-sided.

    Cutting the slab at the plank boundaries removes the ambiguity: every
    slab-top face is then either wholly under a plank (correctly deleted) or
    wholly in the open (correctly kept). The abutment landings' inner edges are
    added for the same reason.
    """
    D = cfg.DECK
    lo, hi = D['slab_x']
    cuts = {lo, hi, -D['end_plate_x'][0], D['end_plate_x'][0]}
    for a, b in plank_spans():
        cuts.update((a, b))
    e = sorted(x for x in cuts if lo <= x <= hi)
    return list(zip(e[:-1], e[1:]))


def build(rise):
    """Assemble the whole bridge at a given arch rise."""
    s = Solid(rise)
    R = Rel
    D, U, AB = cfg.DECK, cfg.UNDER, cfg.ABUTMENT

    # --- deck: a continuous slab with separate planks laid on top. The planks
    # sink 8 mm into the slab, so their undersides come out as buried faces and
    # the grooves between them read as grooves rather than holes.
    for a, b in slab_edges():
        s.prism((a, b), (-D['slab_z'], D['slab_z']),
                R(D['slab_dy'][0]), R(D['slab_dy'][1]), 'slab')

    for a, b in plank_spans():
        s.prism((a, b), (-D['plank_z'], D['plank_z']),
                R(D['plank_dy'][0]), R(D['plank_dy'][1]), 'plank')

    for sgn in (-1, 1):
        a, b = sorted(sgn * v for v in D['end_plate_x'])
        s.prism((a, b), (-cfg.HALF_W, cfg.HALF_W),
                R(D['end_plate_dy'][0]), R(D['end_plate_dy'][1]), 'end_plate')

    # --- the ribs under the slab, the only structure left below the deck
    s.run(U['x'], U['z'], R(U['dy'][0]), R(U['dy'][1]), 'under', U['segments'])

    # --- abutments: a plinth carrying the landing, on a slightly wider base
    for sgn in (-1, 1):
        a, b = sorted(sgn * v for v in AB['plinth_x'])
        s.prism((a, b), (-AB['plinth_z'], AB['plinth_z']),
                AB['plinth_y'][0], R(D['slab_dy'][0]), 'plinth')
        a, b = sorted(sgn * v for v in AB['base_x'])
        s.prism((a, b), (-AB['base_z'], AB['base_z']),
                AB['base_y'][0], AB['base_y'][1], 'base')

    return s


def solve_rise():
    """Find the arch rise that puts the model's crown exactly on the envelope.

    The tallest point is not at x=0. The walking surface that now carries the
    crown is made of discrete planks, so its true maximum sits on whichever
    plank straddles the centre, and only on that plank's own top face -- a
    chord of the arch, slightly below it. Rather than reason about that, build
    the vertex set and measure it. Height is monotonic in rise, so plain
    bisection converges in ~40 steps and each step is only a few thousand
    vertices.
    """
    target = cfg.ENVELOPE['height']
    lo, hi = cfg.ARCH['rise_bounds']
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        h = np.array(build(mid).pos)[:, 1].max()
        if hi - lo < cfg.ARCH['rise_tol']:
            break
        lo, hi = (mid, hi) if h < target else (lo, mid)
    return 0.5 * (lo + hi)
