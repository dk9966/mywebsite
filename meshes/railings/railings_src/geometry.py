"""Primitive assembly for the railing kit.

Everything in this kit is a prism whose top rectangle is allowed to differ
from its bottom rectangle, plus a regular polygonal prism for the octagonal
caps. That is the entire vocabulary, and it is enough:

  * equal rects            -> a box
  * uniformly shrunk rect  -> a chamfer or a taper
  * rect offset in x only  -> a slanted strut, no shear maths required

The generality is free because **all six faces stay planar** in every one of
those cases. The top and bottom are horizontal by construction; a side face
has both of its bottom vertices at one (y, z) and both of its top vertices at
another, so the plane through them contains the x axis and all four points lie
on it. The same argument holds swapping x and z. Planarity is what keeps the
flat-shaded block joints crisp and the tangents well defined -- the bridge had
to segment its parts to keep it, and here it comes for nothing.

Nothing is booleaned. Parts are deliberately sunk into each other and the
interior faces are deleted afterwards by ``reshape.remove_buried_faces``. That
is easier than getting the joins exact, and strictly better: exact butts
produce coincident surfaces, which is the one failure the cleanup cannot fix
by deletion.
"""
import numpy as np


def rect(x, z):
    """(x0, x1, z0, z1) from an x span and a z span."""
    return (x[0], x[1], z[0], z[1])


def sym(x, hz):
    """A rect spanning ``x`` and symmetric about z = 0 with half-width ``hz``."""
    return (x[0], x[1], -hz, hz)


class Solid:
    """Accumulates prisms into a triangle soup, tagging every face."""

    # the six faces of a box as vertex keys (i=x, j=y, k=z); oriented later
    _QUADS = [[(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)],
              [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
              [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
              [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
              [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
              [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]]

    def __init__(self):
        self.pos = []
        self.faces = []
        self.tags = []

    # -- internals -------------------------------------------------------
    def _emit(self, verts, tris, tag):
        """Append a convex part, orienting every triangle away from its centre."""
        base = len(self.pos)
        verts = np.asarray(verts, float)
        centre = verts.mean(0)
        self.pos.extend(map(tuple, verts))
        for a, b, c in tris:
            p = verts[[a, b, c]]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            if n @ (p.mean(0) - centre) < 0:
                a, b, c = a, c, b
            self.faces.append((base + a, base + b, base + c))
            self.tags.append(tag)

    # -- primitives ------------------------------------------------------
    def prism(self, bottom, top, ylo, yhi, tag):
        """One prism between two axis-aligned rectangles at two heights.

        ``bottom`` and ``top`` are ``(x0, x1, z0, z1)``. They may differ freely:
        shrink both axes for a chamfer, shift x for a slanted strut. All six
        faces stay planar either way -- see the module docstring.
        """
        r = {0: bottom, 1: top}
        keys, verts = [], []
        for i in (0, 1):
            for j in (0, 1):
                for k in (0, 1):
                    keys.append((i, j, k))
                    verts.append((r[j][i], ylo if j == 0 else yhi, r[j][2 + k]))
        n = {key: m for m, key in enumerate(keys)}

        tris = []
        for quad in self._QUADS:
            a, b, c, d = (n[key] for key in quad)
            tris.append((a, b, c))
            tris.append((a, c, d))
        self._emit(verts, tris, tag)

    def box(self, x, z, ylo, yhi, tag):
        """A plain axis-aligned box. ``z`` may be a half-width or a span."""
        z = (-z, z) if np.isscalar(z) else z
        r = rect(x, z)
        self.prism(r, r, ylo, yhi, tag)

    def mirror(self, x, z, ylo, yhi, tag):
        """The same box on both sides of the run, at +z and -z."""
        z0, z1 = (z, z) if np.isscalar(z) else z
        self.box(x, (z0, z1), ylo, yhi, tag)
        self.box(x, (-z1, -z0), ylo, yhi, tag)

    def taper(self, cx, cz, r0, r1, ylo, yhi, tag):
        """A square frustum centred on (cx, cz), half-width r0 -> r1."""
        self.prism((cx - r0, cx + r0, cz - r0, cz + r0),
                   (cx - r1, cx + r1, cz - r1, cz + r1), ylo, yhi, tag)

    def poly(self, cx, cz, r0, r1, ylo, yhi, sides, tag):
        """A regular polygonal frustum, rotated so a flat faces each axis.

        Used for the pillar's octagonal cap. The rotation matters: with a
        vertex on the axis instead of a flat, the octagon's corners would poke
        out past the square shaft's faces on the diagonals and the cap would
        stop reading as a cap.
        """
        a = np.arange(sides) * (2 * np.pi / sides) + np.pi / sides
        verts = [(cx + r0 * np.cos(t), ylo, cz + r0 * np.sin(t)) for t in a]
        verts += [(cx + r1 * np.cos(t), yhi, cz + r1 * np.sin(t)) for t in a]
        verts += [(cx, ylo, cz), (cx, yhi, cz)]
        lo_c, hi_c = 2 * sides, 2 * sides + 1

        tris = []
        for i in range(sides):
            j = (i + 1) % sides
            tris += [(i, j, sides + j), (i, sides + j, sides + i)]   # side quad
            tris += [(lo_c, i, j), (hi_c, sides + i, sides + j)]     # end fans
        self._emit(verts, tris, tag)

    # -- output ----------------------------------------------------------
    def arrays(self):
        """Triangles, positions, per-face tags -- with vertices split per face.

        Sharing a prism's corners between the triangles that meet there is the
        natural way to build one and the wrong way to ship it. Two later passes
        need one vertex per corner *per face*: normal smoothing writes a
        different normal into each face at a corner, and break_coplanar_ties
        nudges a single face without dragging its neighbours. Welding happens
        where it is actually wanted -- inside the edge detector, by rounded
        position -- so nothing is lost.
        """
        faces = np.array(self.faces, np.int64)
        pos = np.array(self.pos, np.float64)[faces.reshape(-1)]
        return (np.arange(len(pos), dtype=np.int64).reshape(-1, 3), pos,
                np.array(self.tags, object))
