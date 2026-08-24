"""Every tunable knob for the island pillar, in one place."""

# ---------------------------------------------------------------- shape
# The pillar's geometry is generated, not loaded. See shape.py for why: the old
# input mesh was a union of un-booleaned boxes, so every rib seam was an actual
# hole and every overlap a z-fighting pair. Everything below describes a radius
# field on an (angle, height) grid, which is meshed into a single watertight
# surface.
#
# Column count is derived, not set: ribs and channels are given widths in
# columns and the circle is cut to fit, so `ribs` x (`rib_cols` + `gap_cols`)
# decides how many facets the cross-section has.
SHAPE = {
    'height': 6.0,
    'radius': 1.180,          # radius where the profile reads 1.0 (the foot)
    'rows': 30,               # height bands; also the vertical profile resolution
    'row_bias': 0.45,         # >0 packs the bands toward both ends
    'seed': 20250823,
    'phase': 0.0,

    # Silhouette, as (fraction of height, fraction of `radius`). Interpolated
    # with a monotone cubic so the waist cannot overshoot into a belly.
    'profile': [
        (0.00, 1.000),
        (0.05, 0.985),
        (0.13, 0.870),
        (0.25, 0.720),
        (0.42, 0.635),
        (0.58, 0.615),        # skinniest point
        (0.75, 0.660),
        (0.88, 0.800),
        (0.95, 0.860),
        (1.00, 0.880),
    ],

    # Angular layout. A rib group is 2-3 columns wide and shares one depth, so
    # its columns produce no wall between them and the rib reads as one face.
    'ribs': 16,
    'rib_cols': [2, 3],
    'gap_cols': [1, 2],
    'channel': 0.105,         # how far a channel sits inside the nominal surface
    'rib_steps': [0.0, 0.0, 0.25, 0.45],   # ribs do not all stand equally proud

    # Vertical block structure. Each group gets its own break heights, which is
    # what staggers the block ends between neighbouring ribs.
    'blocks': (8, 12),        # breaks per group -> 9 to 13 blocks
    'block_span': (0.06, 0.96),
    'jitter': 0.045,          # per-block depth wobble
    'quantum': 0.010,         # depths snap to this grid, so no step is a sliver
    'rib_break': 0.20,        # chance a rib block drops back to channel depth

    # Base ring: the channels close over the bottom rows and the lowest of them
    # step out again into a foot.
    'plinth_rows': 4,
    'plinth_lip': 2,
    'plinth_step': 0.055,

    # Crenellated top ring. Above the deck only merlon groups survive, standing
    # on the platform rim and overhanging it slightly.
    'haunch_rows': 1,         # one closing row at the very top: the collar the
                              # paving's edge lands on, and the only place the
                              # ribs are forced to a single radius

    # Top platform paving, generated as real geometry (no texture). It IS the
    # top: the brick disc runs flush to the outer edge, no raised ring around
    # it. All sizes are world units and deliberately NOT scaled per variant: a
    # wider platform gets more bricks, the same size, like a real paved floor.
    'paving': {
        # A flush transition ring at the rim, exactly on the deck plane. It is
        # not decoration: the shell's top edge is a polygon of chords between
        # its 65 columns, while brick corners sit on the true circle -- one
        # ring sampled at the shell's own angles is what bridges the two
        # without cracks. Kept narrower than a brick so it reads as a border.
        'kerb_width': 0.07,
        'course_width': 0.14, # target radial depth of a course of bricks
        'brick_arc': 0.15,    # target arc length of one brick
        'hub_radius': 0.11,   # round centre stone
        # Bricks drop below the deck plane by 0-3x this. Neighbouring bricks
        # always land on different steps, so every joint is a real edge and the
        # edge highlight draws the joint lines -- that is all the "mortar" is.
        'drop': 0.006,
    },
}

# ---------------------------------------------------------------- paths
OUTPUT_GLB  = '../island_pillar.glb'
PREVIEW_PNG = '../island_pillar_preview.png'

# Size variants.
#
# Widths come from measuring the concept art, not from round numbers. Island
# deck widths in that render, in pixels: CONTACT 230, EXPERIENCES 260, minecraft
# 280, WORKSHOP 345, ABOUT ME 350, central 480-570. So the central island is
# roughly 2.4x the smallest side island -- nowhere near the 5x a first guess
# suggested.
#
#   base  -> a small side island (CONTACT / EXPERIENCES)
#   large -> a mid island        (WORKSHOP / ABOUT ME)
#   huge  -> the central island
#
# Height grows far more slowly than width, so the big ones read as broad masses
# rather than towers.
#
# `flare` deepens the hourglass: it pushes the top and bottom outward while
# leaving the waist alone, so the ends read full and the pinch reads deep. The
# base pillar is slender enough not to need it.
#
# There is a real trade-off here. Holding the overall width fixed while flaring
# hard makes the waist thinner in absolute terms -- at flare 2.25 the huge
# variant's waist dropped to 1.22, thinner than the *base* pillar's 1.37, which
# reads wrong for the thing carrying the biggest island. `grow` lets a variant
# exceed its island-derived width so the ends can get genuinely fuller without
# the neck going spindly. 1.0 pins the width exactly.
VARIANTS = [
    dict(suffix='',       width=1.00, height=1.00, fill=0.00),
    dict(suffix='_large', width=1.50, height=1.10, fill=0.10, fill_power=2.0),
    dict(suffix='_huge',  width=2.40, height=1.25, fill=0.14, fill_power=2.0),
]

# How sharply the flare falls off toward the waist. Lower spreads it further up
# and down the shaft; higher keeps it tight to the very ends.
FLARE_POWER = 1.7

# How sharply the waist fill falls off toward the ends.
#
# This interacts with the amount in a way that is easy to get wrong. A large
# fill on a low power peaks hard at mid height and the pillar develops a visible
# belly -- at fill 0.50 / power 1.5 the middle bowed 0.077 past its neighbours
# and read as a barrel rather than a column. Keeping the fill modest and the
# power at 2.0 straightens the sides while still thickening the waist.
FILL_POWER = 2.0

BUILD_DIR = 'build'                               # intermediate texture maps

# ---------------------------------------------------------------- shading
# Quads get cut into triangles, and where a quad is not perfectly flat its two
# halves face slightly different ways. Flat-shaded, that cut line shows up as a
# visible triangle. Averaging the normal across any edge that bends less than
# this makes the pair read as one panel; anything sharper stays a crease.
SHADING = {
    'smooth_deg': 28.0,
}

# ---------------------------------------------------------------- body material
# Deliberately flat: a plain colour with no basecolor/normal/roughness maps.
# Surface noise made this read as wet photoreal stone; the silhouette and the
# edge highlights are what should carry the look.
BODY = {
    # linear-space RGB (glTF baseColorFactor). ~#232529 in sRGB.
    'base_color': [0.0129, 0.0139, 0.0176, 1.0],
    'roughness': 0.35,          # semi-gloss: clean broad reflections
    'metallic': 0.0,            # dielectric, F0 = 0.04
}

# ---------------------------------------------------------------- edge highlight
EDGES = {
    'min_angle': 24.0,      # degrees of dihedral before an edge counts as sharp
    'band': 0.024,          # world-space half width of the highlight, in mesh units
    'angle_lo': 22.0,       # angle -> width ramp, so blunt edges get thinner lines
    'angle_hi': 80.0,
    'min_scale': 0.30,
    # emissive tint; raise for a stronger glow, drop to 0 to disable entirely
    'emissive': [1.0, 1.0, 1.0],   # global dimmer; per-type colour lives in the LUT
}

# Glowing lines. These are ordinary sharp edges given a hot emissive profile --
# no tubes, strips or any other added geometry. GLOW['band'] is a bit wider than
# EDGES['band'] so the lines read as light bleeding out of the crack.
# Glowing cracks. Free polylines lying on the surface, deliberately NOT tied to
# mesh edges -- an edge-locked line can only trace the boundary between faces,
# which reads as glowing trim on the corners. The reference's cracks run across
# faces, so these do too. See cracks.py.
GLOW = {
    'band': 0.068,          # world-space reach of a crack including its halo
    # 0 = no cracks. Everything below still works; raise this to bring the blue
    # glow back and it regenerates from the same parameters.
    'paths': 0,
    'top_range': (4.15, 5.05),
    'bottom_range': (0.95, 1.75),
    'min_extent': 2.5,
    'step': 0.11,           # how far a path descends per point
    'jog_chance': 0.13,     # chance per step of stepping sideways
    'jog_degrees': (3.5, 8.0),
    'offset': 0.004,        # lift off the surface so the crack is not buried
    'field_angles': 720,    # resolution of the surface-radius lookup
    'field_heights': 480,
    'plane_tol': 0.055,     # how close a crack must sit to a face's own plane
    'fade': 0.70,           # world units over which each end fades to nothing
    'seed': 12345,
}

LUT = {
    'size': 256,
    'falloff_power': 2.6,   # higher = tighter line
    'core_boost': 0.55,     # hot core right on the edge
    'core_width': 0.16,
    # UV1 packing: an ordinary edge maps its distance into [0, plain_peak]
    # (peak on the edge, falling to 0 outward) and a glow edge into
    # [glow_peak, 1]. The gap between them is dead space so the two profiles
    # can never bleed into each other under bilinear filtering.
    'plain_peak': 0.45,
    'glow_peak': 0.55,
    # Emissive is pushed past the 0-1 texture ceiling with
    # KHR_materials_emissive_strength. The strength multiplies everything, so
    # plain_color below is the *final* intended value and gets divided by the
    # strength when the LUT is written; the glow keeps the full 0-1 range and
    # therefore ends up `emissive_strength` times brighter.
    'emissive_strength': 8.0,
    # linear RGB. plain stays as before; glow runs a hot near-white core out
    # into saturated blue.
    'plain_color': [0.095, 0.107, 0.132],
    # three-part glow: hot core, blue line, broad dim halo. The halo is doing
    # the job of engine bloom, so the asset reads as glowing even in a viewer
    # with no post-processing.
    'glow_core': [0.62, 0.86, 1.00],
    # The core has to stay a couple of pixels wide on screen or it stair-steps.
    # At band 0.068 a core of 0.10 is 0.007 world units -- roughly one pixel at
    # normal viewing distance, which is exactly when aliasing bites.
    'glow_core_width': 0.26,
    'glow_core_power': 1.15,   # lower = softer core edge, less stair-stepping
    'glow_color': [0.05, 0.38, 1.00],
    'glow_power': 4.0,      # falloff of the line itself (tight)
    'halo_color': [0.010, 0.058, 0.155],
    'halo_power': 1.55,     # falloff of the halo (broad)
}

# ---------------------------------------------------------------- geometry fix
# All three passes below repaired the *old* source mesh, which was a union of
# overlapping boxes that had never been booleaned: ~40% of its faces were buried
# inside the solid, plenty more were exactly coplanar with a visible face and
# z-fought against it, and the top haunch poked out past the cap because the two
# were separate objects. shape.py generates one watertight surface with no
# interior faces and no coincident planes, so all three are off. They are kept
# because they still work, and cost roughly a minute of build time when on.
BURIED = {
    'enabled': False,
    'probe': 0.004,        # how far outside a face to test, in world units
    'threshold': 0.5,      # winding number above this means "inside the solid"
}

# Faces that survive burial removal but still sit exactly coincident with
# another visible face. Neither can be deleted; nudging one breaks the depth
# tie so they stop flickering. The offset is far below visible scale.
ZFIGHT = {
    'enabled': False,
    'tolerance': 1e-4,     # plane separation under this counts as coincident
    # 3e-4 was not enough headroom: with a far clip plane a depth buffer
    # resolves less than that at distance and the pair flickers anyway. 1.5e-3
    # is 0.025% of the model height -- still invisible, six times the margin.
    'offset': 1.5e-3,      # how far to push the loser inward, world units
    'passes': 6,           # a face can lose several ties; repeat until clean
}

TOP_CAP = {
    'enabled': False,
    'y_split': 5.85,             # everything above this is the cap
    'haunch_band': (5.50, 5.70), # where the flare lives
    'outer_rmin': 0.60,          # ignore interior verts when measuring outer radius
    'bins': 48,                  # angular resolution of the measurement
    'clearance': 0.025,          # how far the cap must overhang the haunch
}

# ---------------------------------------------------------------- UV layout
# World units per texture tile for the body's triplanar projection. Unused by
# the flat material, but kept so maps can be dropped back in without redoing UVs.
TILE = 1.78

# ---------------------------------------------------------------- export
# Textures ship as PNG; see build_pillar.prepare_textures for why.
