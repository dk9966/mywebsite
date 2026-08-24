"""Every tunable knob for the bridge, in one place.

Units are metres, matching the reference sheet's 400 x 200 x 60 cm.
The origin sits at the centre of the span, on the ground plane:
X runs along the length, Z across the width, Y up from y=0.

Vertical offsets for anything sitting on or above the deck are given
*relative to the deck's walking surface*, which is a curve. Offsets below
the deck are relative to the same curve, so the whole superstructure bends
with the arch for free.
"""

# ---------------------------------------------------------------- paths
OUTPUT_GLB  = '../bridge.glb'
PREVIEW_PNG = '../bridge_preview.png'
BUILD_DIR   = 'build'                    # intermediate texture maps

# ---------------------------------------------------------------- envelope
# The drawing's dimensions. X and Z fall out of the part positions exactly;
# the height does not, because the tallest point lands wherever the arch and
# the planks happen to put it. Rather than fudge a thickness, the arch rise is
# *solved* for -- see geometry.solve_rise.
ENVELOPE = {
    'length': 4.00,
    'width':  2.00,
    # The drawing's 60 cm measured to the top of a handrail. With the railings
    # and side beams removed the tallest thing is the deck itself, so the
    # height is restated rather than inherited; length and width are unaffected.
    'height': 0.30,
}

HALF_L = ENVELOPE['length'] / 2      # 2.00
HALF_W = ENVELOPE['width'] / 2       # 1.00

# ---------------------------------------------------------------- the arch
# deck(x) = base + rise * (1 - (x/HALF_L)^2) + thickness
#
# A parabola, not a circular arc: it is flattest at the crown and steepest at
# the abutments, which is the profile in the reference orthos. `rise` is solved
# at build time so the model's highest point lands exactly on ENVELOPE.height.
ARCH = {
    'base': 0.105,           # underside of the deck slab at the abutments
    'thickness': 0.055,      # slab bottom -> walking surface
    'rise_bounds': (0.02, 0.30),   # bisection bracket for the solve
    'rise_tol': 1e-9,
}

# ---------------------------------------------------------------- shading
# Quads get cut into triangles, and where a quad is not perfectly flat its two
# halves face slightly different ways. Flat-shaded, that cut line shows up as a
# visible triangle. The bridge's prisms are sheared along the arch, so their
# side faces are genuinely non-planar by a fraction of a degree -- exactly the
# case this fixes. Anything sharper than the threshold stays a crease.
SHADING = {
    'smooth_deg': 20.0,
}

# ---------------------------------------------------------------- body material
# Deliberately flat, like the island pillar: a plain colour with no basecolor,
# normal or roughness maps. The silhouette and the edge highlights carry it.
# Slightly cooler and slightly more metallic than the pillar's stone, because
# this is fabricated alloy rather than rock.
BODY = {
    'base_color': [0.0126, 0.0138, 0.0172, 1.0],   # linear; ~#222630 sRGB
    'roughness': 0.32,
    'metallic': 0.0,
}

# ---------------------------------------------------------------- deck surface
# The one textured surface on the model. Everything else is flat colour.
DECK_MAT = {
    'base_color_scale': 1.0,
    'normal_scale': 0.75,
}

# ---------------------------------------------------------------- edge highlight
EDGES = {
    'min_angle': 24.0,      # degrees of dihedral before an edge counts as sharp
    'band': 0.0075,         # world-space half width of the highlight
    'angle_lo': 22.0,       # angle -> width ramp, so blunt edges get thinner lines
    'angle_hi': 80.0,
    'min_scale': 0.30,
    'emissive': [1.0, 1.0, 1.0],   # global dimmer; the colour lives in the LUT
}

# The asset carries no light sources: no strip lamps, no glowing runs along the
# deck edge. What is left is the edge highlight, which is not a light --
# it is the specular a hard machined edge would catch from the environment,
# faked as emissive so it survives on faces turned away from the key light. A
# model this dark is unreadable in shadow without it.
LUT = {
    'size': 256,
    'falloff_power': 2.6,   # higher = tighter line
    'core_boost': 0.55,     # hot core right on the edge
    'core_width': 0.16,
    # UV1 packing: distance maps to 1 on the edge, falling to 0 at the band
    # limit and running negative beyond it, where CLAMP_TO_EDGE reads the
    # LUT's zero border. That is what lets the stored distance stay unclamped,
    # and therefore linear, which is what keeps the line crisp.
    # Emissive is pushed past the 0-1 texture ceiling with
    # KHR_materials_emissive_strength. The strength multiplies everything, so
    # 'colour' is the *final* intended value and gets divided by the strength
    # when the LUT is written.
    'emissive_strength': 8.0,
    'colour': [0.085, 0.100, 0.128],
}

# ---------------------------------------------------------------- parts
# Every z value here is for the +Z side and mirrored automatically. Nothing may
# exceed |z| = 1.000 or |x| = 2.000, which is what makes the envelope exact.
# 'dy' pairs are offsets from the deck's walking surface.

DECK = {
    'slab_x': (-1.64, 1.64),
    'slab_z': 0.905,          # the planks cantilever 95 mm past this on each
                              # side; the walkway itself is only this wide
    'slab_dy': (-0.055, -0.022),
    # The slab is faceted at the plank boundaries rather than on a count of its
    # own -- see geometry.slab_edges for why that is not a free choice.
    'plank_x': (-1.60, 1.60),
    'planks': 15,
    'plank_gap': 0.028,       # groove between planks
    # The planks run the full width and cantilever 95 mm past the slab on each
    # side, so their ends are the outermost thing on the model -- which is what
    # puts |z| = 1.000 on them. There is no side beam.
    'plank_z': 1.000,
    'plank_dy': (-0.030, 0.0),
    'end_plate_x': (1.60, 2.00),   # solid, un-grooved landing at each abutment
    'end_plate_dy': (-0.055, 0.0),
    # planar XZ projection for the deck maps: one tile per plank pitch along X,
    # one tile across this half-width in Z
    'uv_half_width': 1.00,
}

UNDER = {                     # longitudinal ribs under the slab
    'x': (-1.62, 1.62),
    'z': (0.400, 0.520),
    'dy': (-0.098, -0.050),
    'segments': 11,
}

# There is no railing and no side beam. The reference sheet's posts, caps, two
# runs of rail per side and the curbs under them are all gone; the deck is a
# bare plank surface cantilevered over the slab. The walking surface is now the
# tallest thing on the model, which is why the envelope is 30 cm rather than
# the drawing's 60 -- the drawing measured to the top of a handrail that no
# longer exists.

ABUTMENT = {
    'plinth_x': (1.64, 2.00),
    'plinth_z': 0.970,
    'plinth_y': (0.050, None),     # None -> up to the deck slab's underside
    'base_x': (1.58, 2.00),
    'base_z': 1.000,
    'base_y': (0.0, 0.050),
}

# ---------------------------------------------------------------- deck texture
PLATE = {
    'size': 512,
    'supersample': 3,        # thin hard-edged features alias badly otherwise
    'grain_beta': 1.9,       # brushed metal, stretched across the plank
    'grain_amount': 0.055,
    'grain_seed': 41,
    'rivet_v': (0.055, 0.945),   # two rows, near the plank ends
    'rivet_r': 0.0085,           # in v (world-proportional); scaled in u
    'rivet_height': 0.55,
    'seam_width': 0.030,         # painted plank joint, for the abutment plates
    'seam_depth': 0.45,
    'lum': 0.0150,               # linear; keep close to BODY.base_color
    'lum_jitter': 0.0022,
    'seam_lum': [0.0068, 0.0074, 0.0096],
    'grain_relief': 0.11,        # how much of the grain reaches the normal map
    'normal_strength': 17.0,
    'roughness': 0.34,
}

# ---------------------------------------------------------------- geometry fix
# The bridge is assembled as a union of overlapping prisms that were never
# booleaned, so a good fraction of its faces sit buried inside the solid, many
# exactly coplanar with a visible face. Two surfaces at identical depth flicker
# against each other and no amount of MSAA fixes it.
BURIED = {
    'enabled': True,
    'probe': 0.0025,       # how far outside a face to test, in world units
    'threshold': 0.5,      # winding number above this means "inside the solid"
}

ZFIGHT = {
    'enabled': True,
    'tolerance': 1e-4,     # plane separation under this counts as coincident
    'offset': 4.0e-4,      # how far to push the loser inward, world units
    'passes': 6,           # a face can lose several ties; repeat until clean
}

# ---------------------------------------------------------------- UV layout
# World units per texture tile for the body's triplanar projection. Unused by
# the flat material, but kept so maps can be dropped in without redoing UVs.
TILE = 0.42
