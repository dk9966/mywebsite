"""Every tunable knob for the railing kit, in one place.

Units are metres and the kit is built to the bridge's scale. `bridge.glb` is
4.00 x 2.00 x 0.30 and its reference sheet's 60 cm measured to the top of a
handrail that was dropped from that asset; this kit is that handrail.

HEIGHT is *not* derived from the bridge, and the tempting story that it is
does not survive checking. Standing a terminal on the bridge's crown gives
0.3003 + 0.325 = 0.6253, not the drawing's 0.60 -- the bridge's arch rise
solves to 0.1403, so its walking surface at the crown is 0.3003. (Note the
bridge's own README quotes a rise of 0.1145 from an earlier revision and is
stale on this point; `geometry.solve_rise()` is the truth.) Recovering 0.60
exactly would mean HEIGHT = 0.2997, which would squash every proportion taken
off the reference sheet. The drawing won: HEIGHT is 0.325 because that is what
the sheet's own proportions give, and the bridge relationship is a coincidence
that isn't one.

Every module is centred on its own origin and spans exactly one PITCH in X:
x in [-0.5, +0.5], centred on z = 0, sitting on y = 0. Each module carries the
post that sits on its -X seam; the neighbour supplies the one at +X. Drop
copies at x = 0, 1, 2, ... and the posts come out evenly spaced with none
doubled. Terminal pieces are centred on the grid node at x = +0.5 and
deliberately overhang it -- see NODES.
"""

# ---------------------------------------------------------------- paths
OUTPUT_GLB  = '../railings.glb'
PREVIEW_PNG = '../railings_preview.png'
BUILD_DIR   = 'build'                    # intermediate texture maps

# ---------------------------------------------------------------- envelope
PITCH  = 1.000      # one module of run; the whole kit is on this grid
HALF   = PITCH / 2
HEIGHT = 0.325      # top of a terminal cap; set by the drawing, see above

# ---------------------------------------------------------------- shading
# Nothing here is sheared -- unlike the bridge there is no arch, so every quad
# is perfectly planar and the diagonal cut never shows. The threshold is kept
# low on purpose: it still merges the octagonal cap's 22.5 deg facets into a
# smooth ring while leaving every block joint razor sharp.
SHADING = {
    'smooth_deg': 26.0,
}

# ---------------------------------------------------------------- body material
# Flat colour, no basecolor/normal/roughness maps -- the same decision as the
# bridge and the island pillar. Matched to the bridge exactly so a railing set
# on the bridge deck reads as the same alloy.
BODY = {
    'base_color': [0.0126, 0.0138, 0.0172, 1.0],   # linear; ~#222630 sRGB
    'roughness': 0.32,
    'metallic': 0.0,
}

# ---------------------------------------------------------------- edge highlight
# Identical machinery to the bridge: per-vertex distance to the two nearest
# sharp convex edges, stored in TEXCOORD_1, resolved through a 2D falloff LUT.
# This is not a light. It is the specular a hard machined edge catches from the
# environment, faked as emissive so it survives on faces turned away from the
# key light -- without it a model this dark is unreadable in shadow.
EDGES = {
    'min_angle': 24.0,      # degrees of dihedral before an edge counts as sharp
    'band': 0.0042,         # world-space half width; smaller than the bridge's
                            # because every part here is smaller
    'angle_lo': 22.0,       # angle -> width ramp, so blunt edges get thinner lines
    'angle_hi': 80.0,
    'min_scale': 0.30,
    'emissive': [1.0, 1.0, 1.0],   # global dimmer; the colour lives in the LUT
}

LUT = {
    'size': 256,
    'falloff_power': 2.6,   # higher = tighter line
    'core_boost': 0.55,     # hot core right on the edge
    'core_width': 0.16,
    # UV1 packing: 1 on the edge, falling to 0 at the band limit and running
    # negative beyond it, where CLAMP_TO_EDGE reads the LUT's zero border. That
    # is what lets the stored distance stay unclamped, and therefore linear,
    # which is what keeps the line crisp.
    'emissive_strength': 8.0,
    'colour': [0.085, 0.100, 0.128],
}

# ---------------------------------------------------------------- the lights
# The reference sheet is covered in them and the two existing assets have none.
# Both are honoured: the lenses are always real geometry with a real 3 mm
# proud lip, so the silhouette is identical either way, but whether they are
# emissive is a switch. Turn a channel off and its faces are re-assigned to the
# body material, the material disappears from the file entirely, and the piece
# matches bridge.glb exactly. validate.py checks whichever state you are in.
LIGHTS = {
    'strips': True,     # the chips on the posts, the bars on the terminals
    'lamp':   True,     # the warm lantern on the lamp-top terminal
}

# A lens is flat -- no falloff, one value across the whole surface -- so the
# strength that reads best is much lower than the edge highlight's. The first
# pass used 6.0 and every lens came out solid white: past roughly 0.6 the green
# channel saturates in any tonemapper, and once green and blue both clip the
# hue is gone and a bright blue light renders as a paper rectangle. These
# numbers keep green under that knee and let blue clip alone, which is what
# actually produces a saturated blue with a hot core. Engine bloom then has
# somewhere to go instead of starting from white.
STRIP_MAT = {
    'base_color': [0.010, 0.030, 0.055, 1.0],   # dark when unpowered
    'roughness': 0.22,
    'emissive': [0.075, 0.31, 1.00],            # x strength below = final value
    'emissive_strength': 1.6,
}

LAMP_MAT = {
    'base_color': [0.055, 0.032, 0.012, 1.0],
    'roughness': 0.28,
    'emissive': [1.00, 0.28, 0.10],
    'emissive_strength': 1.6,
}

# How far every lens stands proud of the surface it is set into. This is not a
# styling number. remove_buried_faces probes BURIED['probe'] outside a face and
# needs at least one sample on the lens rim to land in open air, so the rim
# survives and the lens reads as an inset bar rather than a painted rectangle.
# At 1.5 mm the nearest corner sample cleared the host wall by 0.7 mm and the
# rims were one bad rounding away from being deleted. 3 mm is not tight.
PROUD = 0.003

# ---------------------------------------------------------------- the rails
# There is no base beam. The reference sheet has a continuous plinth carrying
# the light strips, and one was built and then removed. Two reasons, and the
# second is the real one. It made every run a solid wall at ankle height; and
# a continuous ground-level extrusion cannot follow a curve. Rails can be
# short straight chords hidden inside the posts at each end, but a plinth is
# one long box whose *side faces* are visible for their whole length, so every
# bend either facets openly or has to be rebuilt per radius.
#
# The rails also dropped ~32 mm when the plinth went, so the run does not read
# as a fence up on stilts with an empty band underneath.
#
# The rails came in with the posts, and not for looks. The seam post has to
# enclose a rail's whole cross-section to hide an angled joint, so rail size
# and post size are one decision, not two: slimming the post without slimming
# the rail puts the rail corners outside the cover and every curve grows a
# notch at every joint. Half-diagonal is now 0.0316 against a 0.0342 cover.
RAIL = {
    'lower_y': (0.100, 0.136),
    'upper_y': (0.198, 0.234),
    'z': 0.026,
}

# The rails carry no lights. They briefly did -- the reference's plinth runs
# were moved into the lower rail when the plinth was dropped -- but a glowing
# line following every rail read as a lit handrail rather than as a fence, and
# it fought the post chips for attention. What is left is the reference's
# other two light families: a chip on each post at each rail height, and the
# vertical bars on the terminals.

# ---------------------------------------------------------------- the posts
# Round, and this is the change that makes curved runs work at all.
#
# A post now sits *on* the module seam at x = -0.5 as well as at the interior
# marks, and each module owns only its -X seam post -- the neighbour supplies
# the one at +0.5. Two modules meeting at an angle therefore both end their
# rails on the same post axis, and because a rail's cross-section is narrower
# than the post is round (half-diagonal 0.037 against shaft_r 0.041) the post
# cylinder encloses both rail ends completely. The wedge that opens between
# them is inside the cylinder, so it is invisible -- at *any* angle, with no
# per-radius geometry. A square post cannot do this: it only hides the joint
# for rotations that happen to line up with its faces.
#
# validate.py asserts the enclosure directly rather than trusting these
# numbers to stay consistent.
POST = {
    # Three to a module rather than four, so the pitch opens from 0.25 to
    # 0.333. Computed from PITCH rather than written out, because the even
    # spacing across a join is an invariant validate.py asserts: the module
    # owns its -X post and the neighbour supplies the +X one, so the list plus
    # +0.5 has to come out evenly divided.
    'x': tuple(-HALF + i * PITCH / 3 for i in range(3)),
    # 10 sides reads as round once the normals are smoothed. What sets the
    # radius is not looks: the covering circle is the *inradius* (flat to
    # flat), not the circumradius, because a rail end poking out between two
    # facets is just as visible as one poking past a cylinder. At 10 sides the
    # inradius is 0.036 * cos(18 deg) = 0.0342 against a rail half-diagonal of
    # 0.0316, so there is 2.6 mm of margin at every angle -- tighter than
    # before, and the reason the rails had to be slimmed alongside the posts.
    # This is the floor: any thinner and the rails have to shrink again.
    'sides': 10,
    'base_r':  0.042, 'base_y':  (0.000, 0.016),   # a flange, so the post is
    'shaft_r': 0.036, 'shaft_y': (0.016, 0.246),   # planted rather than stabbed
    'cap_r':   0.040, 'cap_y':   (0.246, 0.255),
    'bevel_r': (0.040, 0.031), 'bevel_y': (0.255, 0.262),
    # the two blue chips, one centred on each rail, on both faces. Now the
    # only lights on the run itself.
    'lens_half_w': 0.009,
    'lens_y': ((0.106, 0.130), (0.204, 0.228)),
}

# ---------------------------------------------------------------- corner pillar
# The heavy square pillar with the octagonal cap. Used standalone at corners
# and junctions, and carried by the lamp terminal.
PILLAR = {
    'plinth_r': 0.095, 'plinth_y': (0.000, 0.030),
    'course_r': 0.085, 'course_y': (0.030, 0.048),
    'shaft_r':  0.075, 'shaft_y':  (0.048, 0.262),
    'neck_r':   0.083, 'neck_y':   (0.262, 0.276),
    # octagon, rotated so a flat faces each axis and lines up with the square
    # shaft underneath. r is circumradius; flat-to-flat is 1.848 r.
    'cap_r':   (0.090, 0.096), 'cap_y':   (0.276, 0.306),
    'bevel_r': (0.096, 0.078), 'bevel_y': (0.306, 0.325),
    'sides': 8,
    # a vertical blue bar on all four faces, so a corner reads from any angle
    'bar_half_w': 0.009, 'bar_y': (0.090, 0.230),
}

# ---------------------------------------------------------------- end terminal
# The angular pylon. Centred on the grid node at x = +0.5 and overhanging it,
# which is the whole convention: a terminal marks a grid node rather than
# occupying a module, so Post_Corner and Rail_End put their mass in the same
# place and can be swapped freely.
PYLON = {
    'x': (0.445, 0.555), 'z': 0.058,
    'body_y': (0.000, 0.255),
    # the chamfered head, sloping back on the outward (+X) side only
    'head_y': (0.255, 0.300), 'head_top_x': (0.445, 0.520),
    'cap_x': (0.439, 0.526), 'cap_z': 0.064, 'cap_y': (0.300, 0.316),
    'bevel_x': (0.449, 0.516), 'bevel_z': 0.054, 'bevel_y': (0.316, 0.325),
    'bar_x': (0.478, 0.508), 'bar_y': (0.095, 0.245),
    'end_bar_half_w': 0.020,
}

# There is no diagonal gusset. The reference sheet has one on both terminal
# panels, but at this scale it read as a stray slanted bar rather than as
# structure, and it crowded the last post besides. Removed rather than tuned:
# the terminals carry the rail run perfectly well without it.

# ---------------------------------------------------------------- the lantern
LANTERN = {
    'base_r': 0.044, 'base_y': (0.325, 0.340),
    'glass_r': 0.035, 'glass_y': (0.340, 0.408),
    # corner mullions standing proud of the glass, so the glass reads as four
    # panes rather than one glowing cube
    'mullion': (0.030, 0.044), 'mullion_y': (0.340, 0.408),
    'ring_r': 0.046, 'ring_y': (0.408, 0.420),
    'roof_r': (0.046, 0.015), 'roof_y': (0.420, 0.462),
    'finial_r': 0.010, 'finial_y': (0.462, 0.478),
}

# ---------------------------------------------------------------- the kit
# Each entry becomes its own node and its own mesh in the one output file.
# 'height' is asserted by validate.py; 'x' is the exported X extent, which for
# the terminals runs past +0.5 by design.
NODES = [
    ('Rail_Middle', 'the repeatable run: use as many as the span needs'),
    ('Rail_Span',   'rails and beam only, no posts -- safe to scale in X to '
                    'fill a leftover gap that is not a whole number of modules'),
    ('Rail_End',    'run terminating in the angular pylon at +X'),
    ('Rail_Lamp',   'run terminating in the lamp-top pillar at +X'),
    ('Post_Corner', 'the pillar alone, for corners and junctions'),
]


# ---------------------------------------------------------------- geometry fix
# Same story as the bridge and the pillar: this is an un-booleaned union of
# overlapping prisms, so a large fraction of its faces sit inside the solid,
# many exactly coplanar with a visible face. Two surfaces at identical depth
# flicker against each other and no amount of MSAA fixes it.
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
