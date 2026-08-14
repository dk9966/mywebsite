"""Every tunable knob for the island pillar, in one place."""

# ---------------------------------------------------------------- paths
SOURCE_MESH = '../island_pillar_untextured.glb'   # untextured input
OUTPUT_GLB  = '../island_pillar.glb'
PREVIEW_PNG = '../island_pillar_preview.png'
BUILD_DIR   = 'build'                             # intermediate texture maps

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
    'emissive': [0.095, 0.107, 0.132],
}

LUT = {
    'size': 256,
    'falloff_power': 2.6,   # higher = tighter line
    'core_boost': 0.55,     # hot core right on the edge
    'core_width': 0.16,
}

# ---------------------------------------------------------------- top platform
# Which faces become the circular paving: upward facing, near the top, inside
# the crenellation ring (those rim blocks stay plain stone).
TOP_DISC = {
    'normal_y': 0.7,
    'min_height': 5.90,
    'max_radius': 0.796,
    'uv_margin': 1.008,     # slack so the kerb ring lands just inside the rim
}

PAVING = {
    'size': 1024,
    'rings': 7,
    'center_radius': 0.135,
    'hub_radius': 0.045,
    'center_wedges': 12,
    'kerb_width': 0.055,
    'kerb_slabs': 48,
    'brick_arc': 0.135,     # target arc length per brick -> drives count per course
    'mortar_radial': 0.13,
    'mortar_angular': 0.10,
    'wobble': 0.010,
    'wobble_seed': 77,
    'slab_lum': 0.0175,     # linear; keep close to BODY.base_color
    'slab_jitter': 0.0055,
    'mortar_lum': [0.0075, 0.0080, 0.0105],
    'normal_strength': 70.0,
    'roughness': 0.35,
}

# ---------------------------------------------------------------- UV layout
# World units per texture tile for the body's triplanar projection. Unused by
# the flat material, but kept so maps can be dropped back in without redoing UVs.
TILE = 1.78

# ---------------------------------------------------------------- export
JPEG_QUALITY = 92
PAVING_NORMAL_SIZE = 512
