"""The five modules of the kit, assembled from geometry.Solid primitives.

Every module is built in its own local space, centred on x = 0 and standing on
y = 0, spanning one PITCH in X. Three conventions run through all of it, and
they are the reason the pieces interchange and the reason a run can curve:

**A module owns the run between two grid nodes.** Its rails go from x = -0.5
to x = +0.5 exactly, so consecutive copies at a 1 m spacing meet with no gap
and no overlap.

**A module owns the post on its -X seam only.** The neighbour supplies the one
at +0.5. That is what keeps posts evenly spaced across a join instead of
doubling one up at every seam, and it is what puts a post exactly where two
modules meet.

**The seam post is round and wider than the rails.** A rail's cross-section
half-diagonal is 0.0316 and the post covers 0.0342 flat to flat, so the post
encloses both rail ends completely. Rotate one module against the
other by any angle and the wedge that opens between the two rail ends stays
inside the cylinder, hidden. This is the whole trick behind curved and
squiggly runs: there is no curve geometry anywhere in the kit, only straight
modules whose joints happen to be invisible at any angle.

**A terminal owns a grid node, not a module.** The pylon and the pillar are
centred on x = +0.5 and overhang it by half their own footprint, exactly as
Post_Corner would if you dropped one there.
"""
import config as cfg
from geometry import Solid


# ---------------------------------------------------------------- run pieces
def rails(s, x0, x1):
    R = cfg.RAIL
    s.box((x0, x1), R['z'], *R['lower_y'], 'body')
    s.box((x0, x1), R['z'], *R['upper_y'], 'body')


def posts(s, xs):
    """A round post: a base flange, a shaft, a proud cap and a bevelled top.
    Ten sides, which reads as round once the normals are smoothed and still
    gives the edge highlight a cap rim to pick out."""
    P = cfg.POST
    n = P['sides']
    for cx in xs:
        s.poly(cx, 0.0, P['base_r'], P['base_r'], *P['base_y'], n, 'body')
        s.poly(cx, 0.0, P['shaft_r'], P['shaft_r'], *P['shaft_y'], n, 'body')
        s.poly(cx, 0.0, P['cap_r'], P['cap_r'], *P['cap_y'], n, 'body')
        s.poly(cx, 0.0, *P['bevel_r'], *P['bevel_y'], n, 'body')

        # the chips stay rectangular against the round shaft, which reads as a
        # panel let into the post rather than as a band wrapped round it
        w, r = P['lens_half_w'], P['shaft_r']
        for ylo, yhi in P['lens_y']:
            s.mirror((cx - w, cx + w), (r - 0.006, r + cfg.PROUD), ylo, yhi, 'strip')


# ---------------------------------------------------------------- terminals
def pillar(s, cx):
    """The heavy square pillar with the octagonal cap. Deliberately *not*
    rounded: it is the piece that marks a corner or a junction, and it should
    read as a different, heavier kind of object than the run's posts."""
    P = cfg.PILLAR
    for r, y in ((P['plinth_r'], P['plinth_y']), (P['course_r'], P['course_y']),
                 (P['shaft_r'], P['shaft_y']), (P['neck_r'], P['neck_y'])):
        s.taper(cx, 0.0, r, r, *y, 'body')
    s.poly(cx, 0.0, *P['cap_r'], *P['cap_y'], P['sides'], 'body')
    s.poly(cx, 0.0, *P['bevel_r'], *P['bevel_y'], P['sides'], 'body')

    # a vertical bar on all four faces, so a corner piece reads from any angle
    w, r = P['bar_half_w'], P['shaft_r']
    lo, hi = r - 0.006, r + cfg.PROUD
    s.mirror((cx - w, cx + w), (lo, hi), *P['bar_y'], 'strip')
    for sgn in (-1, 1):
        s.box((cx + sgn * lo, cx + sgn * hi), (-w, w), *P['bar_y'], 'strip')


def pylon(s):
    """The angular end terminal: a slab, a head chamfered on the outward side,
    and a bevelled cap. Centred on the grid node at x = +0.5."""
    P = cfg.PYLON
    s.box(P['x'], P['z'], *P['body_y'], 'body')
    s.prism((*P['x'], -P['z'], P['z']),
            (*P['head_top_x'], -P['z'], P['z']), *P['head_y'], 'body')
    s.box(P['cap_x'], P['cap_z'], *P['cap_y'], 'body')
    s.prism((*P['cap_x'], -P['cap_z'], P['cap_z']),
            (*P['bevel_x'], -P['bevel_z'], P['bevel_z']), *P['bevel_y'], 'body')

    lo, hi = P['z'] - 0.006, P['z'] + cfg.PROUD
    s.mirror(P['bar_x'], (lo, hi), *P['bar_y'], 'strip')
    w = P['end_bar_half_w']
    s.box((P['x'][1] - 0.006, P['x'][1] + cfg.PROUD), (-w, w), *P['bar_y'], 'strip')


def lantern(s, cx):
    """The warm lamp on top of the pillar."""
    L = cfg.LANTERN
    s.taper(cx, 0.0, L['base_r'], L['base_r'], *L['base_y'], 'body')
    s.taper(cx, 0.0, L['glass_r'], L['glass_r'], *L['glass_y'], 'lamp')

    # corner mullions standing proud of the glass, so it reads as four panes
    a, b = L['mullion']
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = sorted((cx + sx * a, cx + sx * b))
            z = sorted((sz * a, sz * b))
            s.box(x, z, *L['mullion_y'], 'body')

    s.taper(cx, 0.0, L['ring_r'], L['ring_r'], *L['ring_y'], 'body')
    s.taper(cx, 0.0, *L['roof_r'], *L['roof_y'], 'body')
    s.taper(cx, 0.0, L['finial_r'], L['finial_r'], *L['finial_y'], 'body')


# ---------------------------------------------------------------- the modules
def rail_middle():
    s = Solid()
    rails(s, -cfg.HALF, cfg.HALF)
    posts(s, cfg.POST['x'])
    return s


def rail_span():
    """Rails only, no posts at all -- not even the seam post. Everything in it
    is constant along X, so scaling this node in X stretches it to any length
    with nothing to distort. Use it to fill a gap that is not a whole number of
    modules; put a Post_Corner or a neighbouring module's seam post at each
    end to cover the cut."""
    s = Solid()
    rails(s, -cfg.HALF, cfg.HALF)
    return s


def rail_end():
    s = Solid()
    rails(s, -cfg.HALF, cfg.HALF)
    posts(s, cfg.POST['x'])
    pylon(s)
    return s


def rail_lamp():
    s = Solid()
    rails(s, -cfg.HALF, cfg.HALF)
    posts(s, cfg.POST['x'])
    pillar(s, cfg.HALF)
    lantern(s, cfg.HALF)
    return s


def post_corner():
    s = Solid()
    pillar(s, 0.0)
    return s


BUILDERS = {
    'Rail_Middle': rail_middle,
    'Rail_Span':   rail_span,
    'Rail_End':    rail_end,
    'Rail_Lamp':   rail_lamp,
    'Post_Corner': post_corner,
}
