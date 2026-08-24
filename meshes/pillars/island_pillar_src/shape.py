"""Procedural pillar shell -- one watertight surface, built in the right order.

Why this exists
---------------
The first pillar was a *pile of boxes*: a core cylinder with a few hundred
rectangular slabs scattered around it, exported as one mesh and never
booleaned. That order of operations is what produced every artefact the asset
had. Neighbouring slabs never share a vertex, so the seam between two ribs is a
hairline gap you can see straight through; slabs that overlap bury ~40% of the
faces inside the solid, where they z-fight with the visible ones; and the
crenellation ring, being another set of boxes dropped on top, intersects the
haunch below it at arbitrary angles.

None of that is fixable downstream. `reshape.py` grew a winding-number pass to
delete buried faces and a coincident-plane nudger to break depth ties, which
treats the symptoms and costs most of the build time -- but a gap between two
boxes is *missing surface*, and no post-pass can invent it.

The fix is to build the surface, not the solid. Everything below is one
function of two variables:

    R(theta, y)  ->  the radius interval the pillar occupies

sampled on a grid of angular columns x height rows. A cell is not a box; it is
a piece of *this* surface, and its four sides are shared exactly with the four
cells around it. So the mesh is watertight by construction: no gaps, no
overlaps, no buried faces, no coincident planes. The shape still has every
feature the box version had -- ribs, recessed channels, staggered block ends,
haunches, the brick-paved top -- because those are variations in R (plus the
paving's own field over the top disc), not separate objects.

How the surface is emitted
--------------------------
Each cell (i, j) owns a radius interval [inner, outer], as a multiple of the
silhouette profile at that height. Three kinds of face come out of it:

* **panel** -- the cell's own outer (and, where hollow, inner) surface.
* **theta wall** -- at the boundary between columns i and i+1, covering exactly
  the radii where one is solid and the other is not. That is a set difference,
  so it is emitted once and spans the full step: the thing that used to be a
  gap.
* **y wall** -- the same across a row boundary: every ledge, and both end caps,
  which are just the step down to the empty row past the end.

Watertightness needs one more rule. Where four cells meet, the four walls
around that corner all end on the same radial line, and if they were split at
different radii the mesh would carry T-junctions -- geometrically closed but a
source of hairline sparkle when rasterised. So every wall edge landing on a
corner is subdivided at *the same* set of radii: the endpoints of all four
cells there. Within any elementary interval between two of those radii all four
cells are then uniformly solid or empty, and walking the four-cell cycle the
number of solid/empty flips is necessarily even -- every sub-edge is shared by
exactly two faces. Manifold, not merely closed.

Planarity comes for free and matters for the edge-highlight pass: a theta wall
lies in a plane through the axis, a y wall in a horizontal plane, and a panel
between two parallel chords. Every quad here is flat.
"""
import numpy as np


# ---------------------------------------------------------------- profile
def monotone_spline(keys):
    """Fritsch-Carlson monotone cubic through (t, r) keypoints.

    A Catmull-Rom through the same points overshoots at the waist and puts a
    bulge just above it -- the silhouette is the whole read of this asset, so it
    gets an interpolant that cannot invent extrema between keys.
    """
    t = np.array([k[0] for k in keys], float)
    y = np.array([k[1] for k in keys], float)
    h = np.diff(t)
    d = np.diff(y) / h
    m = np.empty_like(y)
    m[0], m[-1] = d[0], d[-1]
    m[1:-1] = np.where(d[:-1] * d[1:] <= 0, 0.0,
                       (d[:-1] * h[1:] + d[1:] * h[:-1]) / (h[:-1] + h[1:]))
    for i in range(len(d)):                       # clamp so no overshoot
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9.0:
                k = 3.0 / np.sqrt(s)
                m[i], m[i + 1] = k * a * d[i], k * b * d[i]

    def f(x):
        x = np.clip(np.asarray(x, float), t[0], t[-1])
        i = np.clip(np.searchsorted(t, x) - 1, 0, len(h) - 1)
        s = (x - t[i]) / h[i]
        s2, s3 = s * s, s * s * s
        return ((2 * s3 - 3 * s2 + 1) * y[i] + (s3 - 2 * s2 + s) * h[i] * m[i]
                + (-2 * s3 + 3 * s2) * y[i + 1] + (s3 - s2) * h[i] * m[i + 1])
    return f


# ---------------------------------------------------------------- set algebra
def symmetric_difference(a1, b1, a2, b2, eps):
    """Radii where exactly one of two cells is solid.

    Returned as (lo, hi, first_is_the_solid_one) runs. An empty cell is any
    a == b, which this handles without a special case -- that is what makes the
    top ring work, where a merlon column sits next to nothing at all.
    """
    pts = sorted({a1, b1, a2, b2})
    out = []
    for lo, hi in zip(pts, pts[1:]):
        if hi - lo <= eps:
            continue
        mid = 0.5 * (lo + hi)
        first = a1 < mid < b1
        if first == (a2 < mid < b2):
            continue
        if out and out[-1][1] == lo and out[-1][2] == first:
            out[-1][1] = hi
        else:
            out.append([lo, hi, first])
    return out


# ---------------------------------------------------------------- mesher
class Surface:
    """Vertex-welded triangle accumulator.

    Welding on exact coordinates is safe here because every point is built by
    the same expression from the same grid values, so two faces meeting at a
    corner produce bit-identical floats rather than merely close ones.
    """

    def __init__(self):
        self.pos = []
        self._at = {}
        self.tris = []

    def vertex(self, p):
        key = (round(p[0], 9), round(p[1], 9), round(p[2], 9))
        i = self._at.get(key)
        if i is None:
            i = len(self.pos)
            self._at[key] = i
            self.pos.append(p)
        return i

    def triangle(self, p, q, r, ref):
        n = np.cross(q - p, r - p)
        if n @ n < 1e-20:                        # collapsed at the axis
            return
        a, b, c = (p, q, r) if n @ ref > 0 else (p, r, q)
        self.tris.append((self.vertex(a), self.vertex(b), self.vertex(c)))

    def quad(self, p, q, r, s, ref):
        self.triangle(p, q, r, ref)
        self.triangle(p, r, s, ref)

    def strip(self, chain_a, chain_b, ref):
        """Triangulate between two chains that run the same way and share ends.

        Both chains are monotone in radius, so a two-pointer merge gives a valid
        triangulation without ear clipping -- and, critically, adds no vertex to
        either chain. Adding one would be exactly the T-junction the corner
        splitting exists to avoid.

        The one case the plain merge gets wrong is a run that starts at radius
        zero: both chains then begin at the *same* point on the axis, and every
        triangle the merge builds off that vertex has all three corners on one
        radial line. Those come out zero-area and get dropped -- silently taking
        the chain's own sub-edges with them, which is a hole. Clipping the apex
        off as its own triangle first leaves two chains that no longer share a
        vertex, which is what the merge assumes.
        """
        ia = ib = 0
        na, nb = len(chain_a) - 1, len(chain_b) - 1
        if np.array_equal(chain_a[0][1], chain_b[0][1]):
            self.triangle(chain_a[0][1], chain_a[1][1], chain_b[1][1], ref)
            ia = ib = 1
        while ia < na or ib < nb:
            take_a = ib == nb or (ia < na and chain_a[ia + 1][0] <= chain_b[ib + 1][0])
            if take_a:
                self.triangle(chain_a[ia][1], chain_a[ia + 1][1], chain_b[ib][1], ref)
                ia += 1
            else:
                self.triangle(chain_a[ia][1], chain_b[ib + 1][1], chain_b[ib][1], ref)
                ib += 1

    def arrays(self):
        return np.array(self.tris, np.int64), np.array(self.pos, np.float64)


def mesh_field(theta, yv, radius, inner, outer, eps=1e-9, platform=None):
    """Turn a radius field into a watertight Surface (not yet arrays).

    theta  -- N+1 angular boundaries, last == first + 2pi
    yv     -- M+1 height boundaries
    radius -- radius of the nominal surface at each of the M+1 heights
    inner,
    outer  -- (N, M) multiples of that radius; inner == outer means empty

    ``platform`` is a row boundary index whose axis-touching upward run is NOT
    emitted: that disc is the top platform, and _paving() fills the identical
    region with brick geometry instead. Everything else at that boundary (the
    rim ring's overhang underside, for one) is still emitted normally.
    """
    N, M = outer.shape
    ct, st = np.cos(theta[:N]), np.sin(theta[:N])

    def point(d, i, j):
        r = d * radius[j]
        k = i % N
        return np.array([r * ct[k], yv[j], r * st[k]])

    def cell(i, j):
        if j < 0 or j >= M:
            return 0.0, 0.0
        k = i % N
        return float(inner[k, j]), float(outer[k, j])

    def corner(i, j):
        """Radii every wall edge landing on the line (theta[i], yv[j]) is cut at."""
        s = set()
        for ci, cj in ((i - 1, j - 1), (i, j - 1), (i - 1, j), (i, j)):
            a, b = cell(ci, cj)
            if b - a > eps:
                s.update((a, b))
        return sorted(s)

    def chain(splits, lo, hi, mk):
        ds = [lo] + [d for d in splits if lo + eps < d < hi - eps] + [hi]
        return [(d, mk(d)) for d in ds]

    surf = Surface()

    # panels: each cell's own outer skin, plus an inner one where it is a ring
    for i in range(N):
        mid = 0.5 * (theta[i] + theta[i + 1])
        out_ref = np.array([np.cos(mid), 0.0, np.sin(mid)])
        for j in range(M):
            a, b = cell(i, j)
            if b - a <= eps:
                continue
            for d, ref in ((b, out_ref), (a, -out_ref)):
                if d <= eps:
                    continue
                surf.quad(point(d, i, j), point(d, i + 1, j),
                          point(d, i + 1, j + 1), point(d, i, j + 1), ref)

    # theta walls: the step between two columns, spanning it exactly
    for i in range(N):
        th = theta[i + 1]
        side = np.array([-np.sin(th), 0.0, np.cos(th)])
        for j in range(M):
            a1, b1 = cell(i, j)
            a2, b2 = cell(i + 1, j)
            for lo, hi, first in symmetric_difference(a1, b1, a2, b2, eps):
                surf.strip(chain(corner(i + 1, j), lo, hi, lambda d: point(d, i + 1, j)),
                           chain(corner(i + 1, j + 1), lo, hi, lambda d: point(d, i + 1, j + 1)),
                           side if first else -side)

    # y walls: every ledge, and both end caps (the step down to nothing)
    up = np.array([0.0, 1.0, 0.0])
    for i in range(N):
        for j in range(-1, M):
            a1, b1 = cell(i, j)
            a2, b2 = cell(i, j + 1)
            for lo, hi, below in symmetric_difference(a1, b1, a2, b2, eps):
                if platform is not None and j + 1 == platform and below and lo <= eps:
                    continue                   # the platform disc; paving fills it
                surf.strip(chain(corner(i, j + 1), lo, hi, lambda d: point(d, i, j + 1)),
                           chain(corner(i + 1, j + 1), lo, hi, lambda d: point(d, i + 1, j + 1)),
                           up if below else -up)

    return surf



# ---------------------------------------------------------------- paving
def _paving(surf, theta, yv, radius, top, p, rng):
    """Brick paving for the top platform, as real geometry.

    The old platform was a flat disc with a brick *texture*, which meant the
    brick size was baked: scale the pillar up and the bricks scaled with it.
    These bricks are actual faces sized in world units, so a wider platform
    gets more bricks, not bigger ones -- the course count and the bricks per
    course are both derived from the final radius.

    Structure, outside in: a flush kerb ring exactly on the deck plane (the
    piece that bridges the shell's polygonal rim to the circular courses --
    see config), then concentric courses of bricks, then a round centre
    stone. The paving IS the whole top of the pillar; there is no ring of
    blocks around it any more. There is no mortar
    geometry and no texture at all. Each brick is dropped below the deck plane
    by a small multiple of ``drop``, chosen so that *every* brick differs from
    all of its neighbours: courses alternate {0,2} x drop against {1,3} x drop
    (so every course boundary is a step), and bricks alternate parity within a
    course (so every joint is a step). Every step is a sharp edge, and the
    body material's edge highlight draws the joint lines from that -- the same
    mechanism that outlines the blocks on the shaft, which is what keeps the
    platform looking like part of the same object.

    Watertightness follows the same two rules as the shell. Any circle shared
    by two rings is sampled at the union of both rings' joint angles, so the
    two polygonal approximations of that circle are the same polyline -- two
    rings with different brick counts would otherwise leave crescent-shaped
    cracks between their chords. And every vertical edge where four bricks
    meet is split at all four brick heights, exactly the shell's corner rule.

    The outermost circle is the platform hole mesh_field() left open, sampled
    at the shell's own column angles with bit-identical arithmetic, so the
    paving welds seamlessly into the pillar.
    """
    two_pi = 2 * np.pi
    N = len(theta) - 1
    deck = top['deck']
    deck_y = float(yv[deck])
    d = top['rim']
    R = d * radius[deck]              # exactly the shell's point() expression
    ct, st = np.cos(theta[:N]), np.sin(theta[:N])
    thn = sorted(float(t % two_pi) for t in theta[:N])
    rim_xz = {u: (R * ct[k], R * st[k])
              for k, u in ((k, float(theta[k] % two_pi)) for k in range(N))}

    q = p['drop']
    r_kerb = R - p['kerb_width']
    hub = p['hub_radius']
    n_c = max(0, int(round((r_kerb - hub) / p['course_width'])))
    if r_kerb <= hub or n_c == 0:     # platform too small for courses at all
        n_c, bounds = 0, [r_kerb]
    else:
        bounds = list(np.linspace(hub, r_kerb, n_c + 1))

    # rings, outside in. th holds each ring's joint angles sorted in [0, 2pi);
    # h holds the top height of the wedge *starting* at the matching angle.
    def joints(n, prev):
        """Joint angles for a course of n bricks, staggered off the course
        outside it. Purely random offsets occasionally land a joint within a
        ten-thousandth of a radian of one in the neighbouring course; the two
        radial walls are then coplanar in the same plane through the axis --
        which both z-fights at the touching corner and reads as one long
        crack running across the courses, the thing real paving staggers its
        joints to avoid. Keep the best of a few tries."""
        pa = np.array(prev)
        best = None
        for _ in range(30):
            off = float(rng.uniform(0, two_pi / n))
            th = sorted(float((off + m * two_pi / n) % two_pi) for m in range(n))
            gap = min(float(np.abs((pa - u + np.pi) % two_pi - np.pi).min())
                      for u in th)
            if best is None or gap > best[0]:
                best = (gap, th)
            if gap > 0.03:
                break
        return best[1]

    rings = [dict(r_out=R, r_in=r_kerb, th=[0.0], h=[deck_y])]
    for c in range(n_c):              # c = 0 is the course beside the kerb
        r_out, r_in = bounds[n_c - c], bounds[n_c - c - 1]
        n = max(4, 2 * int(round(np.pi * 0.5 * (r_in + r_out) / p['brick_arc'])))
        th = joints(n, rings[-1]['th'])
        par = (c + 1) % 2             # kerb is 0, so the first course is odd
        rings.append(dict(r_out=r_out, r_in=r_in, th=th,
                          h=[deck_y - (par + 2 * (j % 2)) * q for j in range(n)]))
    centre = deck_y - (1 - (n_c % 2)) * q      # differs from both inner values
    # The centre stone is one wedge, but it still needs a marker angle for its
    # span. Reuse the innermost course's first joint exactly: an independent
    # angle that happened to land a hair away from a joint would put two
    # nearly-coincident points on the shared circle -- a sliver triangle.
    rings.append(dict(r_out=bounds[0], r_in=0.0,
                      th=[rings[-1]['th'][0]], h=[centre]))

    # circle i = outer boundary of ring i, sampled at the union of the two
    # adjacent rings' angles (the shell's columns, for the outermost).
    XZ = []
    for i, ring in enumerate(rings):
        outer_th = thn if i == 0 else rings[i - 1]['th']
        U = sorted(set(outer_th) | set(ring['th']))
        if i == 0:
            xz = rim_xz
        else:
            r = ring['r_out']
            xz = {u: (r * np.cos(u), r * np.sin(u)) for u in U}
        XZ.append((U, xz))

    def cpt(i, u, y):
        x, z = XZ[i][1][u]
        return np.array([x, y, z])

    def h_at(ring, u):
        th = ring['th']
        u = u % two_pi
        j = int(np.searchsorted(th, u, side='right')) - 1
        return ring['h'][j]           # j == -1 wraps to the last wedge

    def vchain(i, u, lo, hi):
        """Vertical edge at (circle i, angle u), split at every brick height
        meeting there -- the shell's corner rule, in cylinder coordinates."""
        da = 1e-7                     # far below any joint spacing
        hs = {h_at(rings[i - 1], u - da), h_at(rings[i - 1], u + da),
              h_at(rings[i], u - da), h_at(rings[i], u + da)}
        ys = [lo] + [h for h in sorted(hs) if lo + 1e-12 < h < hi - 1e-12] + [hi]
        return [(y, cpt(i, u, y)) for y in ys]

    def span_pts(U, a0, a1):
        """Circle samples inside [a0, a1], unwrapped past 2pi as needed."""
        out = []
        for u in U:
            for uu in (u, u + two_pi):
                if a0 - 1e-12 <= uu <= a1 + 1e-12:
                    out.append((uu, u))
        out.sort()
        return out

    up = np.array([0.0, 1.0, 0.0])

    # brick tops (and the kerb and centre stone, which are 1-wedge rings)
    for i, ring in enumerate(rings):
        th, n = ring['th'], len(ring['th'])
        for j in range(n):
            a0 = th[j]
            a1 = th[j + 1] if j + 1 < n else th[0] + two_pi
            h = ring['h'][j]
            outer = [(uu, cpt(i, u, h)) for uu, u in span_pts(XZ[i][0], a0, a1)]
            if ring['r_in'] <= 1e-12:
                inner = [(a0, np.array([0.0, h, 0.0]))]
            else:
                inner = [(uu, cpt(i + 1, u, h))
                         for uu, u in span_pts(XZ[i + 1][0], a0, a1)]
            surf.strip(outer, inner, up)

    # course boundaries: a wall wherever the two sides sit at different heights
    for i in range(1, len(rings)):
        U = XZ[i][0]
        for m in range(len(U)):
            u0 = U[m]
            u1 = U[m + 1] if m + 1 < len(U) else U[0] + two_pi
            mid = 0.5 * (u0 + u1)
            hO, hI = h_at(rings[i - 1], mid), h_at(rings[i], mid)
            if abs(hI - hO) <= 1e-12:
                continue
            ref = np.array([np.cos(mid), 0.0, np.sin(mid)])
            surf.strip(vchain(i, u0, min(hI, hO), max(hI, hO)),
                       vchain(i, U[(m + 1) % len(U)], min(hI, hO), max(hI, hO)),
                       ref if hI > hO else -ref)

    # joints between bricks in the same course
    for i in range(1, len(rings)):
        ring = rings[i]
        th, n = ring['th'], len(ring['th'])
        if n < 2 or ring['r_in'] <= 1e-12:
            continue
        for j in range(n):
            b = th[j]
            hL, hR = ring['h'][j - 1], ring['h'][j]
            if abs(hL - hR) <= 1e-12:
                continue
            t = np.array([-np.sin(b), 0.0, np.cos(b)])
            surf.strip(vchain(i, b, min(hL, hR), max(hL, hR)),
                       vchain(i + 1, b, min(hL, hR), max(hL, hR)),
                       t if hL > hR else -t)


# ---------------------------------------------------------------- the shape
def _layout(rng, s):
    """Angular layout: runs of columns that share a depth, so a rib is one face.

    Column count is an *output*, not a setting. Ribs and channels are given
    widths in columns and the circle is cut to fit them, which is why rib widths
    can vary without the facets going uneven.
    """
    groups = []
    col = 0
    for k in range(s['ribs']):
        w = int(rng.choice(s['rib_cols']))
        g = int(rng.choice(s['gap_cols']))
        groups.append(dict(start=col, cols=w, rib=True))
        col += w
        groups.append(dict(start=col, cols=g, rib=False))
        col += g
    return groups, col


def _blocks(rng, M, s):
    """Row indices where a column's extrusion depth is allowed to change.

    The reference's ribs are not smooth pilasters; they read as stacks of blocks
    whose ends do not line up between neighbours. Each group therefore gets its
    own break heights, and the staggering falls out of that.
    """
    lo, hi = s['block_span']
    n = int(rng.integers(s['blocks'][0], s['blocks'][1] + 1))
    cuts = sorted(rng.choice(np.arange(int(lo * M), int(hi * M)), size=n, replace=False))
    return [0] + [int(c) for c in cuts] + [M]


def field(rng, M, s):
    """Build the (inner, outer) depth field and the angular grid it lives on."""
    groups, N = _layout(rng, s)
    inner = np.zeros((N, M))
    outer = np.zeros((N, M))

    deck = M                                  # the platform is the very top
    plinth = s['plinth_rows']                 # rows belonging to the base ring
    band = s['channel']

    for g in groups:
        cols = range(g['start'], g['start'] + g['cols'])
        base = (1.0 - band * float(rng.choice(s['rib_steps'])) if g['rib']
                else 1.0 - band)
        edges = _blocks(rng, deck, s)
        for j0, j1 in zip(edges, edges[1:]):
            d = base
            if g['rib'] and rng.random() < s['rib_break']:
                d = 1.0 - band                 # a rib that stops partway up
            d *= 1.0 + float(rng.uniform(-1, 1)) * s['jitter']
            for i in cols:
                outer[i, j0:j1] = d

    # Both ends are collars, not rib country. The channels close up over the
    # bottom rows and over the last rows under the deck, so the two outward
    # flares read as continuous bands the way they do in the reference -- left
    # ribbed, the block ends there make a ragged crown against the sky and a
    # frayed foot on the ground.
    for j in range(min(plinth, M)):
        step = s['plinth_step'] if j < s['plinth_lip'] else 0.0
        outer[:, j] = 1.0 + step
    outer[:, max(0, deck - s['haunch_rows']):deck] = 1.0

    # The top is nothing but the paving. There used to be a raised ring of
    # blocks up here -- it read as castle battlements, then as a flat parapet,
    # and the answer to both was to remove it: the brick disc now runs flush
    # to the outer edge, sitting directly on the closed collar row below. The
    # last row is that collar (outer exactly 1.0 for every column), so the top
    # boundary of the shell is one clean circle at one radius, which is the
    # hole the paving is generated against.
    # Snap every depth to a grid. Two blocks whose jitter lands 0.0001 apart
    # would otherwise get a real wall between them a tenth of a millimetre wide
    # -- a sliver triangle, which aliases badly and carries an edge highlight
    # nothing can resolve. On the grid those two depths become the same number
    # and no wall is emitted at all, while a step that is meant to be there
    # cannot come out thinner than one quantum.
    q = s['quantum']
    inner = np.round(inner / q) * q
    outer = np.round(outer / q) * q
    return N, inner, outer, dict(deck=M, rim=float(outer[0, M - 1]))


def _rows(M, height, bias):
    """Height bands, packed tighter toward both ends.

    Uniform bands force one compromise on two jobs. The shaft only needs enough
    rows to resolve a gentle curve, but the crown and the foot are where the
    profile turns hardest and where the blocks are smallest -- at a spacing that
    suits the middle, a merlon cannot be shorter than a third of a metre. This
    warps the grid so the ends get roughly half the band height of the waist,
    at no extra row count.
    """
    t = np.linspace(0.0, 1.0, M + 1)
    return height * (t - bias * np.sin(2 * np.pi * t) / (2 * np.pi))


def build(s, width=1.0, height=1.0):
    """Whole pillar: (indices, positions), base on y=0.

    ``width`` and ``height`` stretch the pillar here, at generation time,
    rather than by scaling positions afterwards. The difference matters for
    exactly one thing: the paving. Its brick size is fixed in world units, so
    it has to see the *final* platform radius to decide how many courses and
    bricks to lay -- generate at base size and stretch after, and a huge
    pillar gets nine giant bricks instead of six hundred normal ones.
    """
    rng = np.random.default_rng(s['seed'])
    M = s['rows']
    N, inner, outer, top = field(rng, M, s)

    theta = np.linspace(0.0, 2 * np.pi, N + 1) + s['phase']
    yv = _rows(M, s['height'] * height, s['row_bias'])
    prof = monotone_spline(s['profile'])
    radius = (s['radius'] * width) * prof(yv / (s['height'] * height))

    surf = mesh_field(theta, yv, radius, inner, outer, platform=top['deck'])
    _paving(surf, theta, yv, radius, top, s['paving'], rng)
    idx, pos = surf.arrays()

    # Split the welded surface back into three vertices per triangle. The
    # texturing pass stores UV0, UV1, the normal and the tangent *per corner* --
    # UV1 in particular holds each corner's distance to its own face's sharp
    # edges, which is a different number for every face meeting at a vertex --
    # and writes them into per-vertex arrays. Handing it shared vertices makes
    # those writes collide, and the winner is arbitrary: normals end up flipped
    # and the edge lines smear across whole faces. Welding is still what the
    # mesher does internally, and what `audit` re-derives, because that is the
    # only way to know the surface actually closed.
    pos = pos[idx].reshape(-1, 3)
    return np.arange(len(pos)).reshape(-1, 3), pos, dict(columns=N, rows=M)


# ---------------------------------------------------------------- checks
def audit(idx, pos):
    """Edge census: the one number that says whether the rebuild worked."""
    from collections import defaultdict
    weld, inv = np.unique(np.round(pos, 6), axis=0, return_inverse=True)
    F = inv[idx]
    count = defaultdict(int)
    for f in F:
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            count[(min(a, b), max(a, b))] += 1
    hist = defaultdict(int)
    for v in count.values():
        hist[v] += 1
    return dict(vertices=len(weld), triangles=len(idx),
                boundary=hist.get(1, 0),
                manifold=hist.get(2, 0),
                nonmanifold=sum(n for k, n in hist.items() if k > 2))
