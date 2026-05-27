"""
component_builders.py
=====================

Procedural builders for 8 families of electronic components, each with
~14-20 distinct variations. All builders return a list of trimesh objects
representing one component, centered at the world origin and sitting on a
board of thickness BOARD_T at y=0.

FAMILIES
--------
- QFP / chip ICs        (make_qfp, make_bga, make_ceramic_qfp)
- DIP ICs               (make_dip, make_dip_socketed)
- Capacitors            (make_capacitor, make_tantalum_cap, make_film_cap, make_stacked_cap)
- Heatsinks             (make_heatsink, make_pin_fin_heatsink, make_heatsink_with_pad)
- Octagonal / drum      (make_octagon, make_octagon_torus_top, make_octagon_shielded,
                         make_octagon_vented)
- Headers / terminals   (make_header, make_screw_terminal, make_idc_header, make_jst_header)
- Connectors / ports    (make_connector, make_usb_port, make_audio_jack, make_rj45,
                         make_card_edge_slot)
- SMD passives / LEDs   (make_resistor_smd, make_smd_led, make_smd_inductor, make_smd_4pad,
                         make_smd_tall_cap)

MATERIAL PALETTE
----------------
All materials are desaturated and metallic (industrial vibe). No emissive
glow on components themselves - the visible glow comes from the wireframe
extraction step (see mesh_builder.py).

ROWS TABLE
----------
The module also exports a ROWS list of (family_name, [builder_lambdas]) that
the layout planner uses to sample which specific variation to build at each
placement.

USAGE
-----
>>> import component_builders as cb
>>> qfp_parts = cb.make_qfp(2.0, 2.0, h=0.34, pins_per_side=12)
>>> # parts is a list of trimesh Trimesh objects
>>> import trimesh
>>> trimesh.Scene(qfp_parts).export('out.glb')
"""

"""
Component reference sheet v3.
- Sizes within each row clustered tightly
- More creative variations appended to each row
"""

import numpy as np
import trimesh
from trimesh import creation, transformations as tf

def mat(color_rgba, metallic=0.0, roughness=0.7, emissive=None):
    m = trimesh.visual.material.PBRMaterial(
        baseColorFactor=color_rgba,
        metallicFactor=metallic,
        roughnessFactor=roughness,
    )
    if emissive is not None:
        m.emissiveFactor = emissive
    return m

# Industrial palette: all desaturated, no bright colors.
# Metallic + reflective for that brushed-metal/machined-steel vibe.
BOARD_MAT      = mat([0.06, 0.06, 0.07, 1.0], metallic=0.3, roughness=0.7)
CHIP_MAT       = mat([0.07, 0.07, 0.08, 1.0], metallic=0.3, roughness=0.55)
CHIP_LIGHT_MAT = mat([0.16, 0.16, 0.17, 1.0], metallic=0.4, roughness=0.5)
CERAMIC_MAT    = mat([0.35, 0.33, 0.30, 1.0], metallic=0.15, roughness=0.7)
# "Glow" mats kept as neutral steel tones, NO emissive
CHIP_GLOW_MAT  = mat([0.32, 0.33, 0.36, 1.0], metallic=0.85, roughness=0.35)
CHIP_GLOW_WARM = mat([0.30, 0.28, 0.26, 1.0], metallic=0.7,  roughness=0.45)
CHIP_GLOW_GREEN= mat([0.25, 0.27, 0.26, 1.0], metallic=0.7,  roughness=0.45)
CHIP_GLOW_RED  = mat([0.28, 0.25, 0.25, 1.0], metallic=0.7,  roughness=0.45)
DIE_MAT        = mat([0.45, 0.46, 0.48, 1.0], metallic=0.9,  roughness=0.25)
PIN_MAT        = mat([0.58, 0.60, 0.62, 1.0], metallic=0.95, roughness=0.3)
PIN_GOLD_MAT   = mat([0.50, 0.48, 0.42, 1.0], metallic=0.92, roughness=0.35)
SOLDER_BALL    = mat([0.55, 0.56, 0.58, 1.0], metallic=0.9,  roughness=0.4)
CAP_MAT        = mat([0.12, 0.13, 0.14, 1.0], metallic=0.5,  roughness=0.5)
CAP_STRIPE_MAT = mat([0.04, 0.04, 0.05, 1.0], metallic=0.3,  roughness=0.65)
CAP_TOP_MAT    = mat([0.30, 0.31, 0.33, 1.0], metallic=0.7,  roughness=0.4)
CAP_TOP_RED    = mat([0.24, 0.22, 0.22, 1.0], metallic=0.6,  roughness=0.5)
TANTALUM_MAT   = mat([0.20, 0.18, 0.18, 1.0], metallic=0.5,  roughness=0.55)
FILM_MAT       = mat([0.36, 0.34, 0.30, 1.0], metallic=0.4,  roughness=0.6)
HEATSINK_MAT   = mat([0.42, 0.43, 0.45, 1.0], metallic=0.92, roughness=0.32)
HEATSINK_DARK  = mat([0.18, 0.18, 0.19, 1.0], metallic=0.85, roughness=0.4)
HEATSINK_BLACK_ANO = mat([0.06, 0.06, 0.07, 1.0], metallic=0.55, roughness=0.65)
SCREW_MAT      = mat([0.50, 0.51, 0.52, 1.0], metallic=0.95, roughness=0.25)
LABEL_MAT      = mat([0.55, 0.55, 0.56, 1.0], metallic=0.2,  roughness=0.7)
SHIELD_MAT     = mat([0.62, 0.63, 0.65, 1.0], metallic=0.95, roughness=0.3)
COPPER_MAT     = mat([0.38, 0.34, 0.30, 1.0], metallic=0.85, roughness=0.45)
PLASTIC_WHITE  = mat([0.55, 0.55, 0.56, 1.0], metallic=0.15, roughness=0.65)
PLASTIC_BLUE   = mat([0.16, 0.17, 0.19, 1.0], metallic=0.25, roughness=0.55)
PLASTIC_GREEN  = mat([0.18, 0.19, 0.18, 1.0], metallic=0.25, roughness=0.55)

# Row markers: still distinguishable, but desaturated grayscale-with-a-tint
ROW_COLORS = [
    [0.40, 0.36, 0.36, 1.0],
    [0.45, 0.42, 0.36, 1.0],
    [0.50, 0.48, 0.40, 1.0],
    [0.40, 0.44, 0.40, 1.0],
    [0.36, 0.42, 0.46, 1.0],
    [0.38, 0.40, 0.46, 1.0],
    [0.44, 0.40, 0.46, 1.0],
    [0.50, 0.50, 0.52, 1.0],
]

BOARD_T = 0.4

def _vis(part, material):
    part.visual = trimesh.visual.TextureVisuals(material=material)
    return part

# ============ QFP-FAMILY ============
def make_qfp(w, d, h=0.32, pins_per_side=10, top_marking='none',
             pin_material=PIN_MAT, body_material=CHIP_MAT,
             chamfer=False, label_band=False):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, body_material)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    top_y = h + BOARD_T/2 + 0.005
    if top_marking == 'dot':
        dot = creation.cylinder(radius=0.05, height=0.02, sections=12)
        _vis(dot, CHIP_GLOW_MAT)
        dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        dot.apply_translation([-w/2 + 0.15, top_y + 0.01, -d/2 + 0.15])
        parts.append(dot)
    elif top_marking == 'line':
        line = creation.box(extents=[w*0.7, 0.02, 0.04])
        _vis(line, CHIP_GLOW_MAT)
        line.apply_translation([0, top_y + 0.01, -d/2 + 0.12])
        parts.append(line)
    elif top_marking == 'square':
        pad = creation.box(extents=[w*0.55, 0.04, d*0.55])
        _vis(pad, CHIP_GLOW_MAT)
        pad.apply_translation([0, top_y + 0.02, 0])
        parts.append(pad)
    elif top_marking == 'stripe':
        for sz in (-d*0.25, 0, d*0.25):
            stripe = creation.box(extents=[w*0.8, 0.02, 0.05])
            _vis(stripe, LABEL_MAT)
            stripe.apply_translation([0, top_y + 0.01, sz])
            parts.append(stripe)
    elif top_marking == 'cross':
        h_bar = creation.box(extents=[w*0.7, 0.02, 0.05])
        _vis(h_bar, CHIP_GLOW_WARM)
        h_bar.apply_translation([0, top_y + 0.01, 0])
        parts.append(h_bar)
        v_bar = creation.box(extents=[0.05, 0.02, d*0.7])
        _vis(v_bar, CHIP_GLOW_WARM)
        v_bar.apply_translation([0, top_y + 0.01, 0])
        parts.append(v_bar)
    elif top_marking == 'square_pin1':
        pad = creation.box(extents=[w*0.55, 0.04, d*0.55])
        _vis(pad, CHIP_GLOW_MAT)
        pad.apply_translation([0, top_y + 0.02, 0])
        parts.append(pad)
        dot = creation.cylinder(radius=0.06, height=0.02, sections=12)
        _vis(dot, CHIP_GLOW_WARM)
        dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        dot.apply_translation([-w/2 + 0.13, top_y + 0.05, -d/2 + 0.13])
        parts.append(dot)
    elif top_marking == 'exposed_die':
        die = creation.box(extents=[w*0.45, 0.04, d*0.45])
        _vis(die, DIE_MAT)
        die.apply_translation([0, top_y + 0.02, 0])
        parts.append(die)
        dot = creation.cylinder(radius=0.05, height=0.02, sections=12)
        _vis(dot, CHIP_GLOW_MAT)
        dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        dot.apply_translation([-w/2 + 0.13, top_y + 0.05, -d/2 + 0.13])
        parts.append(dot)
    elif top_marking == 'dual':
        dot = creation.cylinder(radius=0.05, height=0.02, sections=12)
        _vis(dot, CHIP_GLOW_MAT)
        dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        dot.apply_translation([-w/2 + 0.15, top_y + 0.01, -d/2 + 0.15])
        parts.append(dot)
        line = creation.box(extents=[w*0.7, 0.02, 0.04])
        _vis(line, CHIP_GLOW_WARM)
        line.apply_translation([0, top_y + 0.01, d/2 - 0.12])
        parts.append(line)
    if label_band:
        band = creation.box(extents=[w*0.85, 0.025, d*0.12])
        _vis(band, LABEL_MAT)
        band.apply_translation([0, top_y + 0.012, d*0.3])
        parts.append(band)
    if chamfer:
        c = creation.box(extents=[0.12, 0.04, 0.12])
        _vis(c, CHIP_LIGHT_MAT)
        c.apply_translation([-(w/2 - 0.06), h + BOARD_T/2 + 0.02, -(d/2 - 0.06)])
        parts.append(c)
    pin_h, pin_w, pin_l = h * 0.5, 0.04, 0.18
    py = pin_h/2 + BOARD_T/2
    for side in ['l', 'r', 't', 'b']:
        if side in ('l', 'r'):
            ys = np.linspace(-d/2 + 0.12, d/2 - 0.12, pins_per_side)
            x = -w/2 - pin_l/2 if side == 'l' else w/2 + pin_l/2
            for yz in ys:
                p = creation.box(extents=[pin_l, pin_h, pin_w])
                _vis(p, pin_material)
                p.apply_translation([x, py, yz])
                parts.append(p)
        else:
            xs = np.linspace(-w/2 + 0.12, w/2 - 0.12, pins_per_side)
            z = -d/2 - pin_l/2 if side == 't' else d/2 + pin_l/2
            for xx in xs:
                p = creation.box(extents=[pin_w, pin_h, pin_l])
                _vis(p, pin_material)
                p.apply_translation([xx, py, z])
                parts.append(p)
    return parts

def make_bga(w, d, h=0.35, grid=10, body_material=CHIP_MAT):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, body_material)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    dot = creation.cylinder(radius=0.05, height=0.02, sections=12)
    _vis(dot, CHIP_GLOW_MAT)
    dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    dot.apply_translation([-w/2 + 0.13, h + BOARD_T/2 + 0.015, -d/2 + 0.13])
    parts.append(dot)
    die = creation.box(extents=[w*0.35, 0.03, d*0.35])
    _vis(die, DIE_MAT)
    die.apply_translation([0, h + BOARD_T/2 + 0.015, 0])
    parts.append(die)
    ball_r = min(w, d) / (grid * 2.5)
    xs = np.linspace(-w/2 + ball_r*2, w/2 - ball_r*2, grid)
    zs = np.linspace(-d/2 + ball_r*2, d/2 - ball_r*2, grid)
    for xi, x in enumerate(xs):
        for zi, z in enumerate(zs):
            if xi in (0, grid-1) or zi in (0, grid-1):
                ball = creation.icosphere(radius=ball_r, subdivisions=1)
                _vis(ball, SOLDER_BALL)
                ball.apply_translation([x, BOARD_T/2 - ball_r*0.3, z])
                parts.append(ball)
    return parts

def make_ceramic_qfp(w, d, h=0.4, pins_per_side=12):
    return make_qfp(w, d, h=h, pins_per_side=pins_per_side,
                    top_marking='square_pin1', body_material=CERAMIC_MAT,
                    pin_material=PIN_GOLD_MAT)

# ============ DIP-FAMILY ============
def make_dip(w, d, h=0.3, pins_per_side=7, notch_style='dot',
             pin_material=PIN_MAT, body_material=CHIP_MAT, groove=False):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, body_material)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    top_y = h + BOARD_T/2 + 0.005
    if notch_style == 'dot':
        dot = creation.cylinder(radius=0.05, height=0.02, sections=12)
        _vis(dot, CHIP_GLOW_MAT)
        dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        dot.apply_translation([-w/2 + 0.13, top_y + 0.01, -d/2 + 0.13])
        parts.append(dot)
    elif notch_style == 'half_circle':
        notch = creation.cylinder(radius=0.1, height=0.05, sections=20)
        _vis(notch, BOARD_MAT)
        notch.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        notch.apply_translation([-w/2 + 0.05, top_y + 0.025, 0])
        parts.append(notch)
    elif notch_style == 'slot':
        slot = creation.box(extents=[0.08, 0.05, d*0.5])
        _vis(slot, BOARD_MAT)
        slot.apply_translation([-w/2 + 0.1, top_y + 0.025, 0])
        parts.append(slot)
    elif notch_style == 'bar':
        bar = creation.box(extents=[w*0.85, 0.02, 0.04])
        _vis(bar, LABEL_MAT)
        bar.apply_translation([0, top_y + 0.01, -d/2 + 0.1])
        parts.append(bar)
    if groove:
        g = creation.box(extents=[w*0.92, 0.04, 0.04])
        _vis(g, BOARD_MAT)
        g.apply_translation([0, top_y + 0.02, 0])
        parts.append(g)
    xs = np.linspace(-w/2 + 0.1, w/2 - 0.1, pins_per_side)
    for side_z in (-d/2 - 0.08, d/2 + 0.08):
        for xx in xs:
            p = creation.box(extents=[0.05, 0.15, 0.12])
            _vis(p, pin_material)
            p.apply_translation([xx, 0.075 + BOARD_T/2, side_z])
            parts.append(p)
    return parts

def make_dip_socketed(w, d, h=0.3, pins_per_side=8):
    parts = []
    sock_h = 0.15
    socket = creation.box(extents=[w + 0.15, sock_h, d + 0.25])
    _vis(socket, CHIP_LIGHT_MAT)
    socket.apply_translation([0, sock_h/2 + BOARD_T/2, 0])
    parts.append(socket)
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, sock_h + h/2 + BOARD_T/2, 0])
    parts.append(body)
    notch = creation.cylinder(radius=0.1, height=0.05, sections=20)
    _vis(notch, BOARD_MAT)
    notch.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    notch.apply_translation([-w/2 + 0.05, sock_h + h + BOARD_T/2 + 0.025, 0])
    parts.append(notch)
    xs = np.linspace(-w/2 + 0.1, w/2 - 0.1, pins_per_side)
    for side_z in (-d/2 - 0.12, d/2 + 0.12):
        for xx in xs:
            p = creation.box(extents=[0.05, sock_h, 0.08])
            _vis(p, PIN_MAT)
            p.apply_translation([xx, sock_h/2 + BOARD_T/2, side_z])
            parts.append(p)
    return parts

# ============ CAPACITOR-FAMILY ============
def make_capacitor(radius=0.25, height=1.0, sections=20,
                   top_style='plus', stripe=False, top_color=CAP_TOP_MAT,
                   sleeve_color=CAP_MAT, label_band=False):
    parts = []
    body = creation.cylinder(radius=radius, height=height, sections=sections)
    _vis(body, sleeve_color)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, height/2 + BOARD_T/2, 0])
    parts.append(body)
    if stripe:
        s_h = height * 0.95
        s = creation.box(extents=[radius * 0.5, s_h, 0.02])
        _vis(s, CAP_STRIPE_MAT)
        s.apply_translation([0, height/2 + BOARD_T/2, -radius - 0.005])
        parts.append(s)
    if label_band:
        ring = creation.cylinder(radius=radius * 1.01, height=height*0.12, sections=sections)
        _vis(ring, LABEL_MAT)
        ring.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        ring.apply_translation([0, height*0.4 + BOARD_T/2, 0])
        parts.append(ring)
    top_y = height + BOARD_T/2
    if top_style == 'flat':
        top = creation.cylinder(radius=radius*0.85, height=0.04, sections=sections)
        _vis(top, top_color)
        top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        top.apply_translation([0, top_y + 0.02, 0])
        parts.append(top)
    elif top_style == 'ring':
        ring = creation.cylinder(radius=radius*0.85, height=0.05, sections=sections)
        _vis(ring, top_color)
        ring.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        ring.apply_translation([0, top_y + 0.025, 0])
        parts.append(ring)
        inner = creation.cylinder(radius=radius*0.5, height=0.03, sections=sections)
        _vis(inner, sleeve_color)
        inner.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        inner.apply_translation([0, top_y + 0.05, 0])
        parts.append(inner)
    elif top_style == 'dome':
        dome = creation.icosphere(radius=radius*0.7, subdivisions=2)
        dome.apply_scale([1.0, 0.4, 1.0])
        _vis(dome, top_color)
        dome.apply_translation([0, top_y + 0.05, 0])
        parts.append(dome)
    elif top_style == 'plus':
        top = creation.cylinder(radius=radius*0.85, height=0.04, sections=sections)
        _vis(top, top_color)
        top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        top.apply_translation([0, top_y + 0.02, 0])
        parts.append(top)
        for rot in (0, np.pi/2):
            vent = creation.box(extents=[radius*1.3, 0.03, 0.04])
            _vis(vent, CAP_STRIPE_MAT)
            m = tf.rotation_matrix(rot, [0, 1, 0])
            vent.apply_transform(m)
            vent.apply_translation([0, top_y + 0.05, 0])
            parts.append(vent)
    return parts

def make_tantalum_cap(w=0.6, d=0.6, h=0.55):
    """Tantalum-style block, sized to fit the cap-row footprint."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, TANTALUM_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # polarity bar across top
    bar = creation.box(extents=[w*0.22, 0.025, d*0.85])
    _vis(bar, LABEL_MAT)
    bar.apply_translation([-w/2 + w*0.15, h + BOARD_T/2 + 0.015, 0])
    parts.append(bar)
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.08, h, d])
        _vis(cap, SOLDER_BALL)
        cap.apply_translation([sx*(w/2 - w*0.04), h/2 + BOARD_T/2, 0])
        parts.append(cap)
    return parts

def make_film_cap(w=0.6, d=0.6, h=1.0):
    """Film cap sized to fit cap-row footprint (taller than wide like a real one)."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, FILM_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    band = creation.box(extents=[w*0.85, 0.02, d*0.95])
    _vis(band, LABEL_MAT)
    band.apply_translation([0, h + BOARD_T/2 + 0.012, 0])
    parts.append(band)
    # vertical stripe
    stripe = creation.box(extents=[w*0.6, h*0.85, 0.012])
    _vis(stripe, CAP_STRIPE_MAT)
    stripe.apply_translation([0, h/2 + BOARD_T/2, -d/2 - 0.006])
    parts.append(stripe)
    return parts

def make_stacked_cap(radius=0.22, height_each=0.55):
    """Two smaller caps side-by-side, tighter to match row footprint."""
    parts = []
    for sx in (-radius*1.02, radius*1.02):
        body = creation.cylinder(radius=radius, height=height_each*2, sections=24)
        _vis(body, CAP_MAT)
        body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        body.apply_translation([sx, height_each + BOARD_T/2, 0])
        parts.append(body)
        top = creation.cylinder(radius=radius*0.85, height=0.04, sections=24)
        _vis(top, CAP_TOP_MAT)
        top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        top.apply_translation([sx, 2*height_each + BOARD_T/2 + 0.02, 0])
        parts.append(top)
        for rot in (0, np.pi/2):
            vent = creation.box(extents=[radius*1.3, 0.03, 0.04])
            _vis(vent, CAP_STRIPE_MAT)
            m = tf.rotation_matrix(rot, [0, 1, 0])
            vent.apply_transform(m)
            vent.apply_translation([sx, 2*height_each + BOARD_T/2 + 0.05, 0])
            parts.append(vent)
    return parts

# ============ HEATSINK-FAMILY ============
def make_heatsink(w, d, h=0.7, fins=7, fin_axis='x',
                  base_style='flat', fin_style='straight', color=HEATSINK_MAT):
    parts = []
    base = creation.box(extents=[w, 0.1, d])
    _vis(base, color)
    base.apply_translation([0, 0.05 + BOARD_T/2, 0])
    parts.append(base)
    if base_style == 'raised':
        plinth = creation.box(extents=[w*1.05, 0.06, d*1.05])
        _vis(plinth, HEATSINK_DARK)
        plinth.apply_translation([0, 0.03 + BOARD_T/2, 0])
        parts.append(plinth)
    elif base_style == 'with_holes':
        for sx, sz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            hole = creation.cylinder(radius=0.06, height=0.12, sections=12)
            _vis(hole, BOARD_MAT)
            hole.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
            hole.apply_translation([sx*(w/2 - 0.12), 0.06 + BOARD_T/2, sz*(d/2 - 0.12)])
            parts.append(hole)
    if fin_axis == 'x':
        fin_t = w / (fins * 2 + 1)
        xs = np.linspace(-w/2 + fin_t, w/2 - fin_t, fins)
        for xx in xs:
            fin = creation.box(extents=[fin_t * 0.7, h, d * 0.95])
            _vis(fin, color)
            fin.apply_translation([xx, h/2 + 0.1 + BOARD_T/2, 0])
            parts.append(fin)
            if fin_style == 'beveled':
                topper = creation.box(extents=[fin_t * 0.4, 0.05, d * 0.9])
                _vis(topper, HEATSINK_DARK)
                topper.apply_translation([xx, h + 0.1 + BOARD_T/2 + 0.025, 0])
                parts.append(topper)
            elif fin_style == 'pinned':
                cap = creation.cylinder(radius=fin_t*0.2, height=0.05, sections=8)
                _vis(cap, SCREW_MAT)
                cap.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
                cap.apply_translation([xx, h + 0.1 + BOARD_T/2 + 0.025, 0])
                parts.append(cap)
    else:
        fin_t = d / (fins * 2 + 1)
        zs = np.linspace(-d/2 + fin_t, d/2 - fin_t, fins)
        for zz in zs:
            fin = creation.box(extents=[w * 0.95, h, fin_t * 0.7])
            _vis(fin, color)
            fin.apply_translation([0, h/2 + 0.1 + BOARD_T/2, zz])
            parts.append(fin)
    return parts

def make_pin_fin_heatsink(w=1.9, d=1.4, h=0.7, grid_x=8, grid_z=6, color=HEATSINK_MAT):
    parts = []
    base = creation.box(extents=[w, 0.1, d])
    _vis(base, color)
    base.apply_translation([0, 0.05 + BOARD_T/2, 0])
    parts.append(base)
    pin_r = min(w/grid_x, d/grid_z) * 0.3
    xs = np.linspace(-w/2 + pin_r*2, w/2 - pin_r*2, grid_x)
    zs = np.linspace(-d/2 + pin_r*2, d/2 - pin_r*2, grid_z)
    for x in xs:
        for z in zs:
            pin = creation.cylinder(radius=pin_r, height=h, sections=8)
            _vis(pin, color)
            pin.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
            pin.apply_translation([x, h/2 + 0.1 + BOARD_T/2, z])
            parts.append(pin)
    return parts

def make_heatsink_with_pad(w=1.9, d=1.4, h=0.7, fins=8):
    parts = []
    slug = creation.box(extents=[w*0.55, 0.05, d*0.55])
    _vis(slug, COPPER_MAT)
    slug.apply_translation([0, 0.025 + BOARD_T/2, 0])
    parts.append(slug)
    base = creation.box(extents=[w, 0.1, d])
    _vis(base, HEATSINK_MAT)
    base.apply_translation([0, 0.05 + 0.05 + BOARD_T/2, 0])
    parts.append(base)
    fin_t = w / (fins * 2 + 1)
    xs = np.linspace(-w/2 + fin_t, w/2 - fin_t, fins)
    for xx in xs:
        fin = creation.box(extents=[fin_t * 0.7, h, d * 0.95])
        _vis(fin, HEATSINK_MAT)
        fin.apply_translation([xx, h/2 + 0.15 + BOARD_T/2, 0])
        parts.append(fin)
    return parts

# ============ OCTAGONAL-FAMILY ============
def make_octagon(radius=0.5, height=0.55, sections=8, top_detail='none',
                 body_color=CHIP_MAT):
    parts = []
    body = creation.cylinder(radius=radius, height=height, sections=sections)
    _vis(body, body_color)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, height/2 + BOARD_T/2, 0])
    parts.append(body)
    top_y = height + BOARD_T/2
    if top_detail == 'ring':
        ring = creation.cylinder(radius=radius*0.65, height=0.05, sections=max(sections, 16))
        _vis(ring, CHIP_GLOW_MAT)
        ring.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        ring.apply_translation([0, top_y + 0.025, 0])
        parts.append(ring)
    elif top_detail == 'screw':
        screw = creation.cylinder(radius=radius*0.45, height=0.08, sections=12)
        _vis(screw, SCREW_MAT)
        screw.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        screw.apply_translation([0, top_y + 0.04, 0])
        parts.append(screw)
        slot = creation.box(extents=[radius*0.7, 0.02, 0.04])
        _vis(slot, BOARD_MAT)
        slot.apply_translation([0, top_y + 0.085, 0])
        parts.append(slot)
    elif top_detail == 'center_pin':
        pin = creation.cylinder(radius=0.05, height=0.15, sections=10)
        _vis(pin, PIN_MAT)
        pin.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        pin.apply_translation([0, top_y + 0.075, 0])
        parts.append(pin)
    elif top_detail == 'double_ring':
        outer = creation.cylinder(radius=radius*0.8, height=0.04, sections=max(sections, 16))
        _vis(outer, CHIP_GLOW_MAT)
        outer.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        outer.apply_translation([0, top_y + 0.02, 0])
        parts.append(outer)
        inner = creation.cylinder(radius=radius*0.45, height=0.06, sections=max(sections, 16))
        _vis(inner, CHIP_GLOW_WARM)
        inner.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        inner.apply_translation([0, top_y + 0.05, 0])
        parts.append(inner)
    return parts

def make_octagon_torus_top(radius=0.5, height=0.55, sections=12):
    parts = []
    body = creation.cylinder(radius=radius, height=height, sections=sections)
    _vis(body, CHIP_MAT)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, height/2 + BOARD_T/2, 0])
    parts.append(body)
    outer = creation.cylinder(radius=radius*0.8, height=0.08, sections=24)
    _vis(outer, COPPER_MAT)
    outer.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    outer.apply_translation([0, height + BOARD_T/2 + 0.04, 0])
    parts.append(outer)
    inner = creation.cylinder(radius=radius*0.4, height=0.1, sections=24)
    _vis(inner, BOARD_MAT)
    inner.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    inner.apply_translation([0, height + BOARD_T/2 + 0.05, 0])
    parts.append(inner)
    return parts

def make_octagon_shielded(radius=0.5, height=0.6, sections=8):
    parts = []
    body = creation.cylinder(radius=radius, height=height, sections=sections)
    _vis(body, SHIELD_MAT)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, height/2 + BOARD_T/2, 0])
    parts.append(body)
    strap = creation.box(extents=[radius*2.2, 0.04, radius*0.4])
    _vis(strap, SHIELD_MAT)
    strap.apply_translation([0, height + BOARD_T/2 + 0.02, 0])
    parts.append(strap)
    for sx in (-1, 1):
        bolt = creation.cylinder(radius=0.06, height=0.05, sections=10)
        _vis(bolt, SCREW_MAT)
        bolt.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        bolt.apply_translation([sx*radius*0.95, height + BOARD_T/2 + 0.045, 0])
        parts.append(bolt)
    return parts

def make_octagon_vented(radius=0.55, height=0.6, sections=8):
    parts = []
    body = creation.cylinder(radius=radius, height=height, sections=sections)
    _vis(body, CHIP_LIGHT_MAT)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, height/2 + BOARD_T/2, 0])
    parts.append(body)
    n_vents = sections
    for i in range(n_vents):
        ang = 2 * np.pi * i / n_vents
        slot = creation.box(extents=[0.04, height*0.6, 0.04])
        _vis(slot, BOARD_MAT)
        m = tf.rotation_matrix(ang, [0, 1, 0])
        slot.apply_transform(m)
        slot.apply_translation([radius*0.98*np.cos(ang), height/2 + BOARD_T/2,
                                radius*0.98*np.sin(ang)])
        parts.append(slot)
    top = creation.cylinder(radius=radius*0.85, height=0.04, sections=sections)
    _vis(top, CHIP_LIGHT_MAT)
    top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    top.apply_translation([0, height + BOARD_T/2 + 0.02, 0])
    parts.append(top)
    return parts

# ============ HEADER-FAMILY ============
def make_header(n_pins=10, spacing=0.16, rows=1, shrouded=False, right_angle=False):
    parts = []
    w = n_pins * spacing
    d = spacing if rows == 1 else spacing * rows
    base_h = 0.2
    if shrouded:
        wall_t = 0.05
        for sx in (-1, 1):
            wall = creation.box(extents=[wall_t, 0.5, d + wall_t*2])
            _vis(wall, CHIP_LIGHT_MAT)
            wall.apply_translation([sx*(w/2 + wall_t/2), 0.25 + BOARD_T/2, 0])
            parts.append(wall)
        for sz in (-1, 1):
            wall = creation.box(extents=[w, 0.5, wall_t])
            _vis(wall, CHIP_LIGHT_MAT)
            wall.apply_translation([0, 0.25 + BOARD_T/2, sz*(d/2 + wall_t/2)])
            parts.append(wall)
        key = creation.box(extents=[wall_t*1.5, 0.5, 0.08])
        _vis(key, CHIP_LIGHT_MAT)
        key.apply_translation([-w/2 - wall_t, 0.25 + BOARD_T/2, 0])
        parts.append(key)
    else:
        base = creation.box(extents=[w, base_h, d + 0.05])
        _vis(base, CHIP_MAT)
        base.apply_translation([0, base_h/2 + BOARD_T/2, 0])
        parts.append(base)
    for row_i in range(rows):
        row_z = (row_i - (rows-1)/2) * spacing
        for i in range(n_pins):
            x = -w/2 + spacing/2 + i*spacing
            if right_angle:
                pin_v = creation.box(extents=[0.06, 0.2, 0.06])
                _vis(pin_v, PIN_MAT)
                pin_v.apply_translation([x, 0.1 + BOARD_T/2, row_z])
                parts.append(pin_v)
                pin_h_ext = creation.box(extents=[0.06, 0.06, 0.35])
                _vis(pin_h_ext, PIN_MAT)
                pin_h_ext.apply_translation([x, 0.2 + BOARD_T/2 - 0.03, row_z + 0.175])
                parts.append(pin_h_ext)
            else:
                pin = creation.box(extents=[0.06, 0.4, 0.06])
                _vis(pin, PIN_MAT)
                pin.apply_translation([x, 0.2 + BOARD_T/2, row_z])
                parts.append(pin)
    return parts

def make_screw_terminal(n_pos=4, pitch=None, h=0.6, total_w=1.6, color=PLASTIC_GREEN):
    """Screw terminal block. If pitch is None, distributes n_pos screws over total_w."""
    parts = []
    if pitch is None:
        pitch = total_w / n_pos
        w = total_w
    else:
        w = n_pos * pitch
    d = max(pitch * 0.95, 0.4)
    body = creation.box(extents=[w, h, d])
    _vis(body, color)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    xs = np.linspace(-w/2 + pitch/2, w/2 - pitch/2, n_pos)
    for x in xs:
        screw = creation.cylinder(radius=pitch*0.32, height=0.06, sections=12)
        _vis(screw, SCREW_MAT)
        screw.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        screw.apply_translation([x, h + BOARD_T/2 + 0.03, 0])
        parts.append(screw)
        slot = creation.box(extents=[pitch*0.5, 0.02, 0.04])
        _vis(slot, BOARD_MAT)
        slot.apply_translation([x, h + BOARD_T/2 + 0.065, 0])
        parts.append(slot)
        hole = creation.cylinder(radius=pitch*0.22, height=0.06, sections=12)
        _vis(hole, BOARD_MAT)
        hole.apply_translation([x, h*0.45 + BOARD_T/2, d/2 + 0.025])
        parts.append(hole)
    return parts

def make_idc_header(n_pins=10, total_w=1.6):
    """IDC ribbon header, width-clamped to fit the headers row baseline."""
    parts = []
    spacing = total_w / n_pins
    w = total_w
    d = max(0.5, spacing * 2.5)
    wall_h = 0.6
    wall_t = 0.06
    for sx in (-1, 1):
        wall = creation.box(extents=[wall_t, wall_h, d + wall_t*2])
        _vis(wall, CHIP_LIGHT_MAT)
        wall.apply_translation([sx*(w/2 + wall_t/2), wall_h/2 + BOARD_T/2, 0])
        parts.append(wall)
    for sz in (-1, 1):
        wall = creation.box(extents=[w, wall_h, wall_t])
        _vis(wall, CHIP_LIGHT_MAT)
        wall.apply_translation([0, wall_h/2 + BOARD_T/2, sz*(d/2 + wall_t/2)])
        parts.append(wall)
    for sz in (-1, 1):
        bump = creation.box(extents=[w*0.25, wall_h*0.3, wall_t*1.5])
        _vis(bump, CHIP_LIGHT_MAT)
        bump.apply_translation([0, wall_h*0.7 + BOARD_T/2, sz*(d/2 + wall_t*1.5)])
        parts.append(bump)
    key_cut = creation.box(extents=[w*0.15, wall_h*0.5, wall_t*2])
    _vis(key_cut, BOARD_MAT)
    key_cut.apply_translation([0, wall_h*0.75 + BOARD_T/2, -d/2 - wall_t])
    parts.append(key_cut)
    pin_z_spacing = d * 0.5
    for row_i in range(2):
        row_z = (row_i - 0.5) * pin_z_spacing
        for i in range(n_pins):
            x = -w/2 + spacing/2 + i*spacing
            pin = creation.box(extents=[0.05, 0.35, 0.05])
            _vis(pin, PIN_MAT)
            pin.apply_translation([x, 0.175 + BOARD_T/2, row_z])
            parts.append(pin)
    return parts

def make_jst_header(n_pins=4, pitch=0.3):
    """JST-style header, scaled up so it sits in the same footprint as other headers."""
    parts = []
    w = max(1.6, n_pins * pitch + 0.3)
    d = 0.55
    h = 0.5
    body = creation.box(extents=[w, h, d])
    _vis(body, PLASTIC_WHITE)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # opening on top
    slot = creation.box(extents=[w*0.85, 0.05, d*0.5])
    _vis(slot, BOARD_MAT)
    slot.apply_translation([0, h + BOARD_T/2 + 0.025, 0])
    parts.append(slot)
    # latch tab on front
    latch = creation.box(extents=[w*0.25, h*0.45, 0.04])
    _vis(latch, PLASTIC_WHITE)
    latch.apply_translation([0, h*0.7 + BOARD_T/2, d/2 + 0.025])
    parts.append(latch)
    # side guide rails
    for sx in (-1, 1):
        rail = creation.box(extents=[0.06, h*0.9, d*0.3])
        _vis(rail, PLASTIC_WHITE)
        rail.apply_translation([sx*(w/2 + 0.03), h*0.45 + BOARD_T/2, 0])
        parts.append(rail)
    # pins
    xs = np.linspace(-(n_pins-1)*pitch/2, (n_pins-1)*pitch/2, n_pins)
    for x in xs:
        pin = creation.box(extents=[0.04, 0.35, 0.04])
        _vis(pin, PIN_MAT)
        pin.apply_translation([x, 0.175 + BOARD_T/2, 0])
        parts.append(pin)
    return parts

# ============ CONNECTOR-FAMILY ============
def make_connector(w, d, h=0.45, slot_style='single', latch=False, color=CHIP_MAT):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, color)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    top_y = h + BOARD_T/2 + 0.005
    if slot_style == 'single':
        slot = creation.box(extents=[w*0.85, 0.05, d*0.55])
        _vis(slot, CHIP_GLOW_MAT)
        slot.apply_translation([0, top_y + 0.025, 0])
        parts.append(slot)
    elif slot_style == 'double':
        for sz in (-d*0.2, d*0.2):
            slot = creation.box(extents=[w*0.85, 0.05, d*0.25])
            _vis(slot, CHIP_GLOW_MAT)
            slot.apply_translation([0, top_y + 0.025, sz])
            parts.append(slot)
    elif slot_style == 'multi':
        n = 6
        slot_w = w * 0.85 / n
        xs = np.linspace(-w*0.85/2 + slot_w/2, w*0.85/2 - slot_w/2, n)
        for xx in xs:
            slot = creation.box(extents=[slot_w*0.7, 0.05, d*0.55])
            _vis(slot, CHIP_GLOW_MAT)
            slot.apply_translation([xx, top_y + 0.025, 0])
            parts.append(slot)
    elif slot_style == 'keyed':
        slot = creation.box(extents=[w*0.85, 0.05, d*0.55])
        _vis(slot, CHIP_GLOW_MAT)
        slot.apply_translation([0, top_y + 0.025, 0])
        parts.append(slot)
        key = creation.box(extents=[0.08, h*0.7, 0.08])
        _vis(key, color)
        key.apply_translation([-w/2 + 0.04, h*0.35 + BOARD_T/2, 0])
        parts.append(key)
    if latch:
        latch_b = creation.box(extents=[w*0.3, h*0.4, 0.06])
        _vis(latch_b, color)
        latch_b.apply_translation([0, h*0.7 + BOARD_T/2, d/2 + 0.03])
        parts.append(latch_b)
    return parts

def make_usb_port(w=1.7, d=0.7, h=0.55):
    parts = []
    shell = creation.box(extents=[w, h, d])
    _vis(shell, SHIELD_MAT)
    shell.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(shell)
    mouth = creation.box(extents=[w*0.7, h*0.5, 0.06])
    _vis(mouth, BOARD_MAT)
    mouth.apply_translation([0, h*0.5 + BOARD_T/2, d/2 + 0.03])
    parts.append(mouth)
    insert = creation.box(extents=[w*0.55, h*0.18, 0.04])
    _vis(insert, PLASTIC_WHITE)
    insert.apply_translation([0, h*0.55 + BOARD_T/2, d/2 + 0.025])
    parts.append(insert)
    for sx in (-1, 1):
        tab = creation.box(extents=[0.15, 0.15, d])
        _vis(tab, SHIELD_MAT)
        tab.apply_translation([sx*(w/2 + 0.075), 0.075 + BOARD_T/2, 0])
        parts.append(tab)
    return parts

def make_audio_jack(w=1.7, d=0.7, h=0.7):
    """Audio jack: cubic body with cylindrical barrel; sized to fill connector row."""
    parts = []
    # main square body section
    body = creation.box(extents=[w*0.5, h, d])
    _vis(body, CHIP_LIGHT_MAT)
    body.apply_translation([-w*0.25, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # cylindrical barrel taking the rest of the width
    barrel = creation.cylinder(radius=min(h, d)*0.42, height=w*0.55, sections=24)
    _vis(barrel, SHIELD_MAT)
    barrel.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    barrel.apply_translation([w*0.2, h*0.55 + BOARD_T/2, 0])
    parts.append(barrel)
    # hole at end (jack opening)
    hole = creation.cylinder(radius=min(h, d)*0.22, height=0.1, sections=20)
    _vis(hole, BOARD_MAT)
    hole.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    hole.apply_translation([w*0.47, h*0.55 + BOARD_T/2, 0])
    parts.append(hole)
    # contact tabs at body base
    for sz in (-d*0.35, d*0.35):
        tab = creation.box(extents=[w*0.45, 0.06, d*0.1])
        _vis(tab, PIN_MAT)
        tab.apply_translation([-w*0.25, 0.03 + BOARD_T/2, sz])
        parts.append(tab)
    return parts

def make_rj45(w=1.1, d=1.2, h=0.7):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_LIGHT_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    mouth = creation.box(extents=[w*0.75, h*0.55, 0.05])
    _vis(mouth, BOARD_MAT)
    mouth.apply_translation([0, h*0.45 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth)
    for sx in (-1, 1):
        led = creation.box(extents=[w*0.18, 0.08, 0.06])
        _vis(led, CHIP_GLOW_GREEN if sx < 0 else CHIP_GLOW_WARM)
        led.apply_translation([sx*w*0.22, h*0.85 + BOARD_T/2, d/2 + 0.03])
        parts.append(led)
    for sx in (-1, 1):
        wing = creation.box(extents=[0.08, h*0.7, d*0.9])
        _vis(wing, SHIELD_MAT)
        wing.apply_translation([sx*(w/2 + 0.04), h*0.35 + BOARD_T/2, 0])
        parts.append(wing)
    return parts

def make_card_edge_slot(w=2.0, d=0.4, h=0.5):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, PLASTIC_BLUE)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    slot = creation.box(extents=[w*0.9, 0.06, d*0.4])
    _vis(slot, BOARD_MAT)
    slot.apply_translation([0, h + BOARD_T/2 + 0.03, 0])
    parts.append(slot)
    n_contacts = 14
    xs = np.linspace(-w*0.4, w*0.4, n_contacts)
    for x in xs:
        contact = creation.box(extents=[w*0.025, 0.04, d*0.3])
        _vis(contact, PIN_GOLD_MAT)
        contact.apply_translation([x, h + BOARD_T/2 + 0.025, 0])
        parts.append(contact)
    key = creation.box(extents=[0.08, h*0.7, 0.08])
    _vis(key, PLASTIC_BLUE)
    key.apply_translation([w*0.25, h*0.35 + BOARD_T/2, 0])
    parts.append(key)
    return parts

# ============ SMD-FAMILY ============
def make_resistor_smd(w=0.3, d=0.14, h=0.08, stripe_color=None,
                      end_cap_material=PIN_MAT):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.18, h, d])
        _vis(cap, end_cap_material)
        cap.apply_translation([sx*(w/2 - w*0.09), h/2 + BOARD_T/2, 0])
        parts.append(cap)
    if stripe_color is not None:
        stripe = creation.box(extents=[w*0.1, 0.01, d*0.9])
        _vis(stripe, stripe_color)
        stripe.apply_translation([0, h + BOARD_T/2 + 0.005, 0])
        parts.append(stripe)
    return parts

def make_smd_led(w=0.3, d=0.18, h=0.1, emit_color=CHIP_GLOW_RED):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, PLASTIC_WHITE)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    lens = creation.box(extents=[w*0.5, 0.04, d*0.6])
    _vis(lens, emit_color)
    lens.apply_translation([0, h + BOARD_T/2 + 0.02, 0])
    parts.append(lens)
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.15, h*0.5, d])
        _vis(cap, PIN_MAT)
        cap.apply_translation([sx*(w/2 - w*0.075), h*0.25 + BOARD_T/2, 0])
        parts.append(cap)
    return parts

def make_smd_inductor(w=0.35, d=0.32, h=0.18):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_LIGHT_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    for sz in np.linspace(-d*0.35, d*0.35, 4):
        stripe = creation.box(extents=[w*1.005, h*1.005, 0.012])
        _vis(stripe, COPPER_MAT)
        stripe.apply_translation([0, h/2 + BOARD_T/2, sz])
        parts.append(stripe)
    return parts

def make_smd_4pad(w=0.32, d=0.32, h=0.1):
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    for sz in (-d*0.25, d*0.25):
        for sx in (-1, 1):
            pad = creation.box(extents=[w*0.18, h, d*0.32])
            _vis(pad, PIN_MAT)
            pad.apply_translation([sx*(w/2 - w*0.09), h/2 + BOARD_T/2, sz])
            parts.append(pad)
    dot = creation.box(extents=[w*0.1, 0.012, d*0.1])
    _vis(dot, CHIP_GLOW_MAT)
    dot.apply_translation([-w*0.25, h + BOARD_T/2 + 0.006, -d*0.25])
    parts.append(dot)
    return parts

def make_smd_tall_cap(w=0.32, d=0.32, h=0.45):
    parts = []
    base = creation.box(extents=[w, 0.06, d])
    _vis(base, PLASTIC_WHITE)
    base.apply_translation([0, 0.03 + BOARD_T/2, 0])
    parts.append(base)
    body = creation.cylinder(radius=min(w, d)*0.48, height=h-0.06, sections=20)
    _vis(body, CAP_MAT)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, 0.06 + (h-0.06)/2 + BOARD_T/2, 0])
    parts.append(body)
    top = creation.cylinder(radius=min(w, d)*0.4, height=0.03, sections=20)
    _vis(top, CAP_TOP_MAT)
    top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    top.apply_translation([0, h + BOARD_T/2 + 0.015, 0])
    parts.append(top)
    for rot in (0, np.pi/2):
        vent = creation.box(extents=[w*0.7, 0.02, 0.03])
        _vis(vent, CAP_STRIPE_MAT)
        m = tf.rotation_matrix(rot, [0, 1, 0])
        vent.apply_transform(m)
        vent.apply_translation([0, h + BOARD_T/2 + 0.035, 0])
        parts.append(vent)
    return parts

# ============ EXTRA BUILDERS for new variations ============

def make_qfp_with_dimple(w, d, h=0.34, pins_per_side=13, pin_material=PIN_MAT):
    """QFP with a dimpled top: circular indent in center + corner dot."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='dot',
                     pin_material=pin_material)
    # circular dimple
    dimple = creation.cylinder(radius=min(w, d)*0.22, height=0.05, sections=24)
    _vis(dimple, BOARD_MAT)
    dimple.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    dimple.apply_translation([0, h + BOARD_T/2 + 0.025, 0])
    parts.append(dimple)
    return parts

def make_qfp_diagonal_text(w, d, h=0.34, pins_per_side=14):
    """QFP with diagonal text-like ridges."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='dot',
                     body_material=CHIP_LIGHT_MAT)
    # diagonal ridges hinting at part number text
    for off in (-0.25, 0, 0.25):
        ridge = creation.box(extents=[w*0.55, 0.025, 0.06])
        _vis(ridge, LABEL_MAT)
        ridge.apply_transform(tf.rotation_matrix(np.pi/8, [0, 1, 0]))
        ridge.apply_translation([0, h + BOARD_T/2 + 0.012, off*d])
        parts.append(ridge)
    return parts

def make_qfp_two_die(w, d, h=0.34, pins_per_side=14):
    """QFP with two visible exposed dies side-by-side."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='dot')
    for sx in (-0.22, 0.22):
        die = creation.box(extents=[w*0.32, 0.045, d*0.5])
        _vis(die, DIE_MAT)
        die.apply_translation([sx*w, h + BOARD_T/2 + 0.022, 0])
        parts.append(die)
    return parts

def make_qfp_bond_wires(w, d, h=0.36, pins_per_side=12):
    """QFP-like with central exposed cavity hinting at bond wires (tiny lines)."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='none',
                     body_material=CERAMIC_MAT, pin_material=PIN_GOLD_MAT)
    # cavity (dark recess)
    cavity = creation.box(extents=[w*0.55, 0.05, d*0.55])
    _vis(cavity, BOARD_MAT)
    cavity.apply_translation([0, h + BOARD_T/2 + 0.025, 0])
    parts.append(cavity)
    # die in the cavity
    die = creation.box(extents=[w*0.25, 0.02, d*0.25])
    _vis(die, DIE_MAT)
    die.apply_translation([0, h + BOARD_T/2 + 0.048, 0])
    parts.append(die)
    # 4 hair-thin "bond wires" (gold strips from die to cavity edge)
    for sx, sz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        wire = creation.box(extents=[w*0.17, 0.012, 0.025])
        _vis(wire, PIN_GOLD_MAT)
        ang = np.arctan2(sz, sx)
        wire.apply_transform(tf.rotation_matrix(ang, [0, 1, 0]))
        wire.apply_translation([sx*w*0.18, h + BOARD_T/2 + 0.054, sz*d*0.18])
        parts.append(wire)
    return parts

def make_qfp_topside_logo(w, d, h=0.34, pins_per_side=13):
    """QFP with stacked logo-like bars + dot, lighter body."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='dot',
                     body_material=CHIP_LIGHT_MAT)
    # logo bars
    for i, sz in enumerate((-0.18, -0.06, 0.06, 0.18)):
        ln = creation.box(extents=[w*(0.4 + 0.08*i), 0.022, 0.04])
        _vis(ln, CHIP_GLOW_WARM if i % 2 == 0 else LABEL_MAT)
        ln.apply_translation([w*0.05, h + BOARD_T/2 + 0.011, sz*d])
        parts.append(ln)
    return parts

def make_qfp_with_xtal(w, d, h=0.32, pins_per_side=12):
    """QFP with a small crystal can sitting on top (combo package look)."""
    parts = make_qfp(w, d, h=h, pins_per_side=pins_per_side, top_marking='square')
    # silvery crystal can on the chip
    can = creation.cylinder(radius=min(w, d)*0.18, height=0.18, sections=20)
    _vis(can, SHIELD_MAT)
    can.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    can.apply_translation([w*0.2, h + BOARD_T/2 + 0.09 + min(w, d)*0.18, 0])
    parts.append(can)
    # base of crystal
    base = creation.box(extents=[min(w, d)*0.5, 0.04, min(w, d)*0.4])
    _vis(base, CHIP_LIGHT_MAT)
    base.apply_translation([w*0.2, h + BOARD_T/2 + 0.02, 0])
    parts.append(base)
    return parts

def make_dip_window(w, d, h=0.3, pins_per_side=9):
    """DIP with quartz window on top (EPROM look)."""
    parts = make_dip(w, d, h=h, pins_per_side=pins_per_side, notch_style='half_circle',
                     body_material=CERAMIC_MAT, pin_material=PIN_GOLD_MAT)
    # window
    window = creation.cylinder(radius=min(w*0.25, d*0.35), height=0.05, sections=24)
    _vis(window, CHIP_GLOW_MAT)
    window.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    window.apply_translation([0, h + BOARD_T/2 + 0.025, 0])
    parts.append(window)
    return parts

def make_dip_zif(w, d, h=0.32, pins_per_side=10):
    """ZIF-socket-style DIP: socket with lever arm."""
    parts = make_dip_socketed(w, d, h=h, pins_per_side=pins_per_side)
    # lever arm protruding from one end
    lever = creation.box(extents=[w*0.35, 0.06, 0.08])
    _vis(lever, CHIP_LIGHT_MAT)
    lever.apply_translation([w*0.5 + w*0.175, 0.12 + BOARD_T/2, d*0.55])
    parts.append(lever)
    # lever pivot
    pivot = creation.cylinder(radius=0.05, height=0.1, sections=10)
    _vis(pivot, SCREW_MAT)
    pivot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    pivot.apply_translation([w*0.5, 0.15 + BOARD_T/2, d*0.6])
    parts.append(pivot)
    return parts

def make_dip_dual_notch(w, d, h=0.3, pins_per_side=10):
    """DIP with notches on BOTH ends + slot down middle (industrial look)."""
    parts = make_dip(w, d, h=h, pins_per_side=pins_per_side, notch_style='none',
                     body_material=CHIP_LIGHT_MAT)
    top_y = h + BOARD_T/2 + 0.005
    for sx in (-1, 1):
        notch = creation.cylinder(radius=0.1, height=0.05, sections=20)
        _vis(notch, BOARD_MAT)
        notch.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        notch.apply_translation([sx*(w/2 - 0.05), top_y + 0.025, 0])
        parts.append(notch)
    return parts

def make_dip_with_chip_on_top(w, d, h=0.3, pins_per_side=8):
    """DIP with a tiny secondary SMD package mounted on top."""
    parts = make_dip(w, d, h=h, pins_per_side=pins_per_side, notch_style='dot')
    # small SMD piggyback
    pb = creation.box(extents=[w*0.45, 0.12, d*0.7])
    _vis(pb, CHIP_LIGHT_MAT)
    pb.apply_translation([0, h + 0.06 + BOARD_T/2, 0])
    parts.append(pb)
    # pin1 dot on piggyback
    dot = creation.cylinder(radius=0.04, height=0.02, sections=10)
    _vis(dot, CHIP_GLOW_WARM)
    dot.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    dot.apply_translation([-w*0.18, h + 0.12 + BOARD_T/2 + 0.01, -d*0.25])
    parts.append(dot)
    return parts

def make_dip_speckled(w, d, h=0.32, pins_per_side=10):
    """DIP with multiple small surface bumps (ID dots and date code)."""
    parts = make_dip(w, d, h=h, pins_per_side=pins_per_side, notch_style='bar')
    top_y = h + BOARD_T/2 + 0.005
    # series of small dots in a line (date code-ish)
    for i, x in enumerate(np.linspace(-w*0.35, w*0.35, 5)):
        dot = creation.box(extents=[0.05, 0.018, 0.05])
        _vis(dot, LABEL_MAT)
        dot.apply_translation([x, top_y + 0.009, d*0.18])
        parts.append(dot)
    return parts

def make_dip_long(w, d, h=0.3, pins_per_side=12):
    """Extra-wide DIP (more pins) but kept within row width by tighter spacing."""
    return make_dip(w, d, h=h, pins_per_side=pins_per_side, notch_style='slot',
                    body_material=CERAMIC_MAT)

def make_cap_double_stripe(radius=0.30, height=1.10, sections=28):
    """Electrolytic with two vertical polarity stripes."""
    parts = make_capacitor(radius=radius, height=height, sections=sections,
                           top_style='plus')
    for ang in (np.pi, np.pi*1.1):
        s = creation.box(extents=[radius * 0.4, height * 0.95, 0.02])
        _vis(s, CAP_STRIPE_MAT)
        s.apply_transform(tf.rotation_matrix(ang, [0, 1, 0]))
        s.apply_translation([radius * np.cos(ang) * 1.005, height/2 + BOARD_T/2,
                            radius * np.sin(ang) * 1.005])
        parts.append(s)
    return parts

def make_cap_squat_smd(w=0.6, d=0.6, h=0.55):
    """Squat SMD-style aluminum cap."""
    parts = []
    # base plate
    base = creation.box(extents=[w, 0.06, d])
    _vis(base, PLASTIC_WHITE)
    base.apply_translation([0, 0.03 + BOARD_T/2, 0])
    parts.append(base)
    body = creation.cylinder(radius=min(w, d)*0.45, height=h - 0.06, sections=28)
    _vis(body, CAP_MAT)
    body.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    body.apply_translation([0, 0.06 + (h - 0.06)/2 + BOARD_T/2, 0])
    parts.append(body)
    top = creation.cylinder(radius=min(w, d)*0.4, height=0.04, sections=28)
    _vis(top, CAP_TOP_RED)
    top.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    top.apply_translation([0, h + BOARD_T/2 + 0.02, 0])
    parts.append(top)
    for rot in (0, np.pi/2):
        vent = creation.box(extents=[min(w, d)*0.75, 0.02, 0.03])
        _vis(vent, CAP_STRIPE_MAT)
        m = tf.rotation_matrix(rot, [0, 1, 0])
        vent.apply_transform(m)
        vent.apply_translation([0, h + BOARD_T/2 + 0.04, 0])
        parts.append(vent)
    return parts

def make_cap_with_band_and_dome(radius=0.3, height=1.1, sections=28):
    """Cap with both a label band and a dome top."""
    return make_capacitor(radius=radius, height=height, sections=sections,
                          top_style='dome', stripe=True, label_band=True,
                          top_color=CAP_TOP_RED)

def make_cap_translucent_top(radius=0.3, height=1.1, sections=32):
    """Cap with bright orange top suggesting different chemistry."""
    return make_capacitor(radius=radius, height=height, sections=sections,
                          top_style='ring', stripe=True,
                          top_color=CHIP_GLOW_WARM,
                          sleeve_color=CAP_MAT)

def make_cap_with_screw_top(radius=0.3, height=1.1, sections=28):
    """Cap with a screw-like indicator on top."""
    parts = make_capacitor(radius=radius, height=height, sections=sections,
                           top_style='flat', stripe=True)
    screw = creation.cylinder(radius=radius*0.4, height=0.05, sections=12)
    _vis(screw, SCREW_MAT)
    screw.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    screw.apply_translation([0, height + BOARD_T/2 + 0.06, 0])
    parts.append(screw)
    slot = creation.box(extents=[radius*0.7, 0.02, 0.04])
    _vis(slot, BOARD_MAT)
    slot.apply_translation([0, height + BOARD_T/2 + 0.09, 0])
    parts.append(slot)
    return parts

def make_cap_with_topside_text(radius=0.3, height=1.1, sections=28):
    """Cap with horizontal bars on top hinting at part marking."""
    parts = make_capacitor(radius=radius, height=height, sections=sections,
                           top_style='plus', stripe=True)
    for sz in (-radius*0.5, 0, radius*0.5):
        bar = creation.box(extents=[radius*1.2, 0.015, 0.04])
        _vis(bar, LABEL_MAT)
        bar.apply_translation([0, height + BOARD_T/2 + 0.07, sz])
        parts.append(bar)
    return parts

def make_heatsink_crosshatch(w=1.9, d=1.4, h=0.7):
    """Crossed fins (X-axis and Z-axis), forming a grid of pockets."""
    parts = []
    base = creation.box(extents=[w, 0.1, d])
    _vis(base, HEATSINK_MAT)
    base.apply_translation([0, 0.05 + BOARD_T/2, 0])
    parts.append(base)
    # X-axis fins
    n_x = 6
    fin_t = w / (n_x * 2 + 1)
    for x in np.linspace(-w/2 + fin_t, w/2 - fin_t, n_x):
        fin = creation.box(extents=[fin_t*0.6, h*0.7, d*0.95])
        _vis(fin, HEATSINK_MAT)
        fin.apply_translation([x, h*0.35 + 0.1 + BOARD_T/2, 0])
        parts.append(fin)
    # Z-axis fins (shorter, sitting on top of x-fins)
    n_z = 5
    fin_d = d / (n_z * 2 + 1)
    for z in np.linspace(-d/2 + fin_d, d/2 - fin_d, n_z):
        fin = creation.box(extents=[w*0.95, h*0.4, fin_d*0.6])
        _vis(fin, HEATSINK_DARK)
        fin.apply_translation([0, h*0.7 + 0.1 + BOARD_T/2 + h*0.2, z])
        parts.append(fin)
    return parts

def make_heatsink_radial(w=1.9, d=1.4, h=0.7, blades=12):
    """Round heatsink with radial fins (sun-burst pattern)."""
    parts = []
    base = creation.cylinder(radius=min(w, d)/2, height=0.1, sections=24)
    _vis(base, HEATSINK_MAT)
    base.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    base.apply_translation([0, 0.05 + BOARD_T/2, 0])
    parts.append(base)
    # central hub
    hub = creation.cylinder(radius=min(w, d)*0.18, height=h, sections=20)
    _vis(hub, HEATSINK_DARK)
    hub.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    hub.apply_translation([0, h/2 + 0.1 + BOARD_T/2, 0])
    parts.append(hub)
    # radial blades
    r_out = min(w, d) * 0.47
    for i in range(blades):
        ang = 2 * np.pi * i / blades
        blade = creation.box(extents=[r_out * 0.85, h, 0.05])
        _vis(blade, HEATSINK_MAT)
        m = tf.rotation_matrix(ang, [0, 1, 0])
        blade.apply_transform(m)
        cx = (r_out * 0.5) * np.cos(ang)
        cz = (r_out * 0.5) * np.sin(ang)
        blade.apply_translation([cx, h/2 + 0.1 + BOARD_T/2, cz])
        parts.append(blade)
    return parts

def make_heatsink_with_fan(w=1.9, d=1.4, h=0.75):
    """Heatsink with a fan/spinner on top (4-blade)."""
    parts = make_heatsink(w, d, h=h*0.55, fins=10, fin_axis='x', base_style='raised')
    # fan housing
    hub_y = h*0.55 + 0.1 + BOARD_T/2 + 0.05
    housing = creation.cylinder(radius=min(w, d)*0.42, height=0.04, sections=24)
    _vis(housing, HEATSINK_DARK)
    housing.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    housing.apply_translation([0, hub_y, 0])
    parts.append(housing)
    # 4 fan blades
    for i in range(4):
        ang = np.pi * i / 2
        blade = creation.box(extents=[min(w, d)*0.36, 0.03, 0.08])
        _vis(blade, CHIP_LIGHT_MAT)
        m = tf.rotation_matrix(ang, [0, 1, 0])
        blade.apply_transform(m)
        cx = (min(w, d)*0.2) * np.cos(ang)
        cz = (min(w, d)*0.2) * np.sin(ang)
        blade.apply_translation([cx, hub_y + 0.04, cz])
        parts.append(blade)
    # hub
    hub = creation.cylinder(radius=min(w, d)*0.1, height=0.05, sections=12)
    _vis(hub, SCREW_MAT)
    hub.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    hub.apply_translation([0, hub_y + 0.06, 0])
    parts.append(hub)
    return parts

def make_heatsink_low_profile(w=1.9, d=1.4, h=0.4, fins=14):
    """Very low-profile heatsink with many thin fins."""
    return make_heatsink(w, d, h=h, fins=fins, fin_axis='x', base_style='flat',
                         fin_style='straight', color=HEATSINK_MAT)

def make_heatsink_diagonal(w=1.9, d=1.4, h=0.7, fins=8):
    """Heatsink with fins rotated 45° diagonally."""
    parts = []
    base = creation.box(extents=[w, 0.1, d])
    _vis(base, HEATSINK_MAT)
    base.apply_translation([0, 0.05 + BOARD_T/2, 0])
    parts.append(base)
    diag = (w + d) * 0.5
    fin_t = diag / (fins * 2 + 1)
    positions = np.linspace(-diag/2 + fin_t, diag/2 - fin_t, fins)
    for pos in positions:
        fin = creation.box(extents=[fin_t * 0.6, h, diag * 0.7])
        _vis(fin, HEATSINK_MAT)
        m = tf.rotation_matrix(np.pi/4, [0, 1, 0])
        fin.apply_transform(m)
        # translate along the diagonal direction
        fin.apply_translation([pos * np.cos(np.pi/4), h/2 + 0.1 + BOARD_T/2,
                              pos * np.sin(np.pi/4)])
        parts.append(fin)
    return parts

def make_heatsink_extruded_holes(w=1.9, d=1.4, h=0.7, fins=9):
    """Heatsink with through-holes in each fin (industrial look)."""
    parts = make_heatsink(w, d, h=h, fins=fins, fin_axis='x', base_style='raised',
                          color=HEATSINK_BLACK_ANO)
    fin_t = w / (fins * 2 + 1)
    xs = np.linspace(-w/2 + fin_t, w/2 - fin_t, fins)
    for x in xs:
        for sz in (-d*0.25, d*0.25):
            hole = creation.cylinder(radius=fin_t*0.25, height=fin_t*0.9, sections=10)
            _vis(hole, BOARD_MAT)
            hole.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
            hole.apply_translation([x, h*0.6 + 0.1 + BOARD_T/2, sz])
            parts.append(hole)
    return parts

def make_octagon_capped(radius=0.55, height=0.6, sections=8):
    """Octagonal can with a flat metallic top cap (hex bolt style)."""
    parts = make_octagon(radius, height, sections=sections, top_detail='none',
                         body_color=SHIELD_MAT)
    cap = creation.cylinder(radius=radius*0.95, height=0.06, sections=6)
    _vis(cap, SCREW_MAT)
    cap.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    cap.apply_translation([0, height + BOARD_T/2 + 0.03, 0])
    parts.append(cap)
    return parts

def make_octagon_label(radius=0.55, height=0.6, sections=10):
    """Octagonal with horizontal label band on the side."""
    parts = make_octagon(radius, height, sections=sections, top_detail='ring')
    band = creation.cylinder(radius=radius * 1.01, height=height*0.18, sections=sections)
    _vis(band, LABEL_MAT)
    band.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    band.apply_translation([0, height*0.5 + BOARD_T/2, 0])
    parts.append(band)
    return parts

def make_octagon_with_pins(radius=0.55, height=0.6, sections=8, n_pins=4):
    """Octagonal can with through-hole pins emerging from sides (relay-style)."""
    parts = make_octagon(radius, height, sections=sections, top_detail='ring',
                         body_color=CHIP_LIGHT_MAT)
    # pins at the base, evenly around
    for i in range(n_pins):
        ang = 2 * np.pi * i / n_pins + np.pi/n_pins
        pin = creation.box(extents=[0.05, 0.2, 0.05])
        _vis(pin, PIN_MAT)
        pin.apply_translation([radius*1.1*np.cos(ang), 0.1 + BOARD_T/2,
                              radius*1.1*np.sin(ang)])
        parts.append(pin)
    return parts

def make_octagon_glowing_top(radius=0.55, height=0.6, sections=12):
    """Octagonal with a strongly emissive top (like an indicator)."""
    parts = make_octagon(radius, height, sections=sections, top_detail='none')
    glow = creation.cylinder(radius=radius*0.7, height=0.08, sections=sections)
    _vis(glow, CHIP_GLOW_WARM)
    glow.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
    glow.apply_translation([0, height + BOARD_T/2 + 0.04, 0])
    parts.append(glow)
    return parts

def make_octagon_taller(radius=0.55, height=0.85, sections=8):
    """Taller octagonal can — same footprint but more height."""
    return make_octagon(radius, height, sections=sections, top_detail='double_ring',
                        body_color=SHIELD_MAT)

def make_octagon_with_strap_diag(radius=0.55, height=0.6, sections=8):
    """Octagonal with diagonal strap on top instead of straight."""
    parts = make_octagon(radius, height, sections=sections, top_detail='none',
                         body_color=SHIELD_MAT)
    strap = creation.box(extents=[radius*2.2, 0.04, radius*0.35])
    _vis(strap, SHIELD_MAT)
    strap.apply_transform(tf.rotation_matrix(np.pi/4, [0, 1, 0]))
    strap.apply_translation([0, height + BOARD_T/2 + 0.02, 0])
    parts.append(strap)
    for sx, sz in [(-1, -1), (1, 1)]:
        bolt = creation.cylinder(radius=0.06, height=0.05, sections=10)
        _vis(bolt, SCREW_MAT)
        bolt.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        bolt.apply_translation([sx*radius*0.7, height + BOARD_T/2 + 0.045, sz*radius*0.7])
        parts.append(bolt)
    return parts

def make_header_boxed(n_pins=10, total_w=1.6, color=PLASTIC_BLUE):
    """Pin header with full colored plastic box (no shrouded walls — full body)."""
    parts = []
    spacing = total_w / n_pins
    base_h = 0.3
    base = creation.box(extents=[total_w, base_h, 0.4])
    _vis(base, color)
    base.apply_translation([0, base_h/2 + BOARD_T/2, 0])
    parts.append(base)
    for i in range(n_pins):
        x = -total_w/2 + spacing/2 + i*spacing
        pin = creation.box(extents=[0.06, 0.45, 0.06])
        _vis(pin, PIN_MAT)
        pin.apply_translation([x, base_h + 0.225 + BOARD_T/2 - 0.15, 0])
        parts.append(pin)
    return parts

def make_header_screw_blue(n_pos=4, total_w=1.6):
    return make_screw_terminal(n_pos=n_pos, total_w=total_w, color=PLASTIC_BLUE)

def make_header_screw_black(n_pos=5, total_w=1.6):
    return make_screw_terminal(n_pos=n_pos, total_w=total_w, color=CHIP_LIGHT_MAT)

def make_header_dual_idc(n_pins=10, total_w=1.6):
    """Two IDC headers stacked closely (compact dual port)."""
    parts = []
    # just make a wider/deeper shrouded header
    spacing = total_w / n_pins
    w = total_w
    d = 0.7
    wall_h = 0.55
    wall_t = 0.05
    for sx in (-1, 1):
        wall = creation.box(extents=[wall_t, wall_h, d + wall_t*2])
        _vis(wall, CHIP_LIGHT_MAT)
        wall.apply_translation([sx*(w/2 + wall_t/2), wall_h/2 + BOARD_T/2, 0])
        parts.append(wall)
    for sz in (-1, 1):
        wall = creation.box(extents=[w, wall_h, wall_t])
        _vis(wall, CHIP_LIGHT_MAT)
        wall.apply_translation([0, wall_h/2 + BOARD_T/2, sz*(d/2 + wall_t/2)])
        parts.append(wall)
    # divider in middle
    divider = creation.box(extents=[w, wall_h*0.7, wall_t])
    _vis(divider, CHIP_LIGHT_MAT)
    divider.apply_translation([0, wall_h*0.35 + BOARD_T/2, 0])
    parts.append(divider)
    # pins in 4 rows (2 banks × 2 rows each)
    for bank in (-1, 1):
        for row_i in range(2):
            row_z = bank * (d*0.3) + (row_i - 0.5) * spacing * 0.8
            for i in range(n_pins):
                x = -w/2 + spacing/2 + i*spacing
                pin = creation.box(extents=[0.05, 0.35, 0.05])
                _vis(pin, PIN_MAT)
                pin.apply_translation([x, 0.175 + BOARD_T/2, row_z])
                parts.append(pin)
    return parts

def make_header_locking(n_pins=6, total_w=1.6):
    """Header with a locking lever on top."""
    spacing = total_w / n_pins
    parts = make_jst_header(n_pins=n_pins, pitch=spacing)
    # add a lever bar on top
    lever = creation.box(extents=[total_w*0.5, 0.05, 0.12])
    _vis(lever, PLASTIC_BLUE)
    lever.apply_translation([0, 0.55 + BOARD_T/2, -0.2])
    parts.append(lever)
    return parts

def make_header_terminal_strip(n_pos=6, total_w=1.6):
    """Barrier strip terminal: screws on top, no enclosing box."""
    parts = []
    pitch = total_w / n_pos
    body = creation.box(extents=[total_w, 0.25, 0.55])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, 0.125 + BOARD_T/2, 0])
    parts.append(body)
    xs = np.linspace(-total_w/2 + pitch/2, total_w/2 - pitch/2, n_pos)
    for x in xs:
        # tall barrier walls between screws
        barrier = creation.box(extents=[0.04, 0.35, 0.5])
        _vis(barrier, CHIP_MAT)
        barrier.apply_translation([x - pitch/2, 0.175 + BOARD_T/2, 0])
        parts.append(barrier)
        # screw on top
        screw = creation.cylinder(radius=pitch*0.28, height=0.07, sections=12)
        _vis(screw, SCREW_MAT)
        screw.apply_transform(tf.rotation_matrix(np.pi/2, [1, 0, 0]))
        screw.apply_translation([x, 0.25 + BOARD_T/2 + 0.035, 0])
        parts.append(screw)
        slot = creation.box(extents=[pitch*0.45, 0.02, 0.04])
        _vis(slot, BOARD_MAT)
        slot.apply_translation([x, 0.25 + BOARD_T/2 + 0.075, 0])
        parts.append(slot)
    # closing barrier
    barrier_end = creation.box(extents=[0.04, 0.35, 0.5])
    _vis(barrier_end, CHIP_MAT)
    barrier_end.apply_translation([total_w/2, 0.175 + BOARD_T/2, 0])
    parts.append(barrier_end)
    return parts

def make_usb_c(w=1.7, d=0.7, h=0.5):
    """USB-C-style port: more rounded, with internal contacts."""
    parts = []
    shell = creation.box(extents=[w, h, d])
    _vis(shell, SHIELD_MAT)
    shell.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(shell)
    # rounded oval mouth (approximate with multiple boxes)
    mouth = creation.box(extents=[w*0.5, h*0.35, 0.05])
    _vis(mouth, BOARD_MAT)
    mouth.apply_translation([0, h*0.5 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth)
    # internal tongue
    tongue = creation.box(extents=[w*0.42, h*0.08, 0.06])
    _vis(tongue, PLASTIC_WHITE)
    tongue.apply_translation([0, h*0.5 + BOARD_T/2, d/2 + 0.03])
    parts.append(tongue)
    # mounting tabs
    for sx in (-1, 1):
        tab = creation.box(extents=[0.12, 0.18, d])
        _vis(tab, SHIELD_MAT)
        tab.apply_translation([sx*(w/2 + 0.06), 0.09 + BOARD_T/2, 0])
        parts.append(tab)
    return parts

def make_hdmi_port(w=1.7, d=0.7, h=0.55):
    """HDMI-style port: trapezoidal mouth, metal shell."""
    parts = []
    shell = creation.box(extents=[w, h, d])
    _vis(shell, SHIELD_MAT)
    shell.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(shell)
    # wider top, narrower bottom mouth — approximate with stacked boxes
    mouth_top = creation.box(extents=[w*0.7, h*0.2, 0.05])
    _vis(mouth_top, BOARD_MAT)
    mouth_top.apply_translation([0, h*0.65 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth_top)
    mouth_bot = creation.box(extents=[w*0.55, h*0.15, 0.05])
    _vis(mouth_bot, BOARD_MAT)
    mouth_bot.apply_translation([0, h*0.4 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth_bot)
    # tongue
    tongue = creation.box(extents=[w*0.5, h*0.08, 0.04])
    _vis(tongue, PLASTIC_WHITE)
    tongue.apply_translation([0, h*0.52 + BOARD_T/2, d/2 + 0.025])
    parts.append(tongue)
    for sx in (-1, 1):
        tab = creation.box(extents=[0.12, 0.15, d])
        _vis(tab, SHIELD_MAT)
        tab.apply_translation([sx*(w/2 + 0.06), 0.075 + BOARD_T/2, 0])
        parts.append(tab)
    return parts

def make_barrel_jack(w=1.7, d=0.7, h=0.65):
    """DC barrel jack: large cylindrical body in a square housing."""
    parts = []
    base = creation.box(extents=[w*0.55, h, d])
    _vis(base, CHIP_MAT)
    base.apply_translation([-w*0.225, h/2 + BOARD_T/2, 0])
    parts.append(base)
    # barrel
    barrel = creation.cylinder(radius=min(h, d)*0.4, height=w*0.55, sections=24)
    _vis(barrel, SHIELD_MAT)
    barrel.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    barrel.apply_translation([w*0.22, h*0.55 + BOARD_T/2, 0])
    parts.append(barrel)
    # central pin (hole proxy is dark cylinder, the pin is visible)
    pin_outer = creation.cylinder(radius=min(h, d)*0.22, height=0.1, sections=20)
    _vis(pin_outer, BOARD_MAT)
    pin_outer.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    pin_outer.apply_translation([w*0.5, h*0.55 + BOARD_T/2, 0])
    parts.append(pin_outer)
    pin_inner = creation.cylinder(radius=min(h, d)*0.08, height=0.12, sections=16)
    _vis(pin_inner, SCREW_MAT)
    pin_inner.apply_transform(tf.rotation_matrix(np.pi/2, [0, 0, 1]))
    pin_inner.apply_translation([w*0.49, h*0.55 + BOARD_T/2, 0])
    parts.append(pin_inner)
    return parts

def make_sd_slot(w=1.7, d=0.7, h=0.35):
    """SD card slot: low, wide, with a mouth opening."""
    parts = []
    shell = creation.box(extents=[w, h, d])
    _vis(shell, SHIELD_MAT)
    shell.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(shell)
    # wide mouth
    mouth = creation.box(extents=[w*0.85, h*0.4, 0.05])
    _vis(mouth, BOARD_MAT)
    mouth.apply_translation([0, h*0.5 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth)
    # tongue with contacts visible
    tongue = creation.box(extents=[w*0.7, h*0.15, 0.05])
    _vis(tongue, PLASTIC_WHITE)
    tongue.apply_translation([0, h*0.55 + BOARD_T/2, d/2 + 0.025])
    parts.append(tongue)
    # contacts on tongue (gold strips)
    for x in np.linspace(-w*0.28, w*0.28, 6):
        c = creation.box(extents=[w*0.04, h*0.05, 0.04])
        _vis(c, PIN_GOLD_MAT)
        c.apply_translation([x, h*0.55 + BOARD_T/2, d/2 + 0.025])
        parts.append(c)
    return parts

def make_micro_usb(w=1.7, d=0.7, h=0.4):
    """Micro USB port: smaller mouth than USB-A."""
    parts = []
    shell = creation.box(extents=[w, h, d])
    _vis(shell, SHIELD_MAT)
    shell.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(shell)
    mouth = creation.box(extents=[w*0.4, h*0.3, 0.05])
    _vis(mouth, BOARD_MAT)
    mouth.apply_translation([0, h*0.6 + BOARD_T/2, d/2 + 0.025])
    parts.append(mouth)
    tongue = creation.box(extents=[w*0.3, h*0.1, 0.04])
    _vis(tongue, PLASTIC_WHITE)
    tongue.apply_translation([0, h*0.6 + BOARD_T/2, d/2 + 0.022])
    parts.append(tongue)
    for sx in (-1, 1):
        tab = creation.box(extents=[0.1, 0.12, d])
        _vis(tab, SHIELD_MAT)
        tab.apply_translation([sx*(w/2 + 0.05), 0.06 + BOARD_T/2, 0])
        parts.append(tab)
    return parts

def make_smd_diode(w=0.35, d=0.18, h=0.1):
    """SMD diode: like resistor but with a clear cathode stripe."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.18, h, d])
        _vis(cap, PIN_MAT)
        cap.apply_translation([sx*(w/2 - w*0.09), h/2 + BOARD_T/2, 0])
        parts.append(cap)
    # cathode stripe at one end
    stripe = creation.box(extents=[w*0.12, 0.012, d*0.9])
    _vis(stripe, LABEL_MAT)
    stripe.apply_translation([-w*0.3, h + BOARD_T/2 + 0.006, 0])
    parts.append(stripe)
    return parts

def make_smd_xtal(w=0.4, d=0.3, h=0.16):
    """SMD crystal oscillator: small can with 4 corner pads."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, SHIELD_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # corner pads
    for sx, sz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        pad = creation.box(extents=[w*0.18, h*0.4, d*0.25])
        _vis(pad, PIN_GOLD_MAT)
        pad.apply_translation([sx*(w/2 - w*0.09), h*0.2 + BOARD_T/2, sz*(d/2 - d*0.125)])
        parts.append(pad)
    # frequency marking on top (line)
    line = creation.box(extents=[w*0.6, 0.012, 0.02])
    _vis(line, LABEL_MAT)
    line.apply_translation([0, h + BOARD_T/2 + 0.007, 0])
    parts.append(line)
    return parts

def make_smd_rgb_led(w=0.4, d=0.32, h=0.12):
    """SMD RGB LED with three small color zones."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, PLASTIC_WHITE)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # three lens zones
    colors = [CHIP_GLOW_RED, CHIP_GLOW_GREEN, CHIP_GLOW_MAT]
    for i, col in enumerate(colors):
        lens = creation.box(extents=[w*0.18, 0.04, d*0.6])
        _vis(lens, col)
        lens.apply_translation([(i - 1) * w*0.22, h + BOARD_T/2 + 0.02, 0])
        parts.append(lens)
    # end caps
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.1, h*0.5, d])
        _vis(cap, PIN_MAT)
        cap.apply_translation([sx*(w/2 - w*0.05), h*0.25 + BOARD_T/2, 0])
        parts.append(cap)
    return parts

def make_smd_transistor(w=0.4, d=0.3, h=0.14):
    """SOT-23-style transistor: small body with 3 leads."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, CHIP_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # 3 leads: 2 on one side, 1 on the other
    for sx_off in (-w*0.25, w*0.25):
        lead = creation.box(extents=[0.05, h*0.4, d*0.2])
        _vis(lead, PIN_MAT)
        lead.apply_translation([sx_off, h*0.2 + BOARD_T/2, -d/2 - d*0.1])
        parts.append(lead)
    lead = creation.box(extents=[0.05, h*0.4, d*0.2])
    _vis(lead, PIN_MAT)
    lead.apply_translation([0, h*0.2 + BOARD_T/2, d/2 + d*0.1])
    parts.append(lead)
    # marking dot
    dot = creation.box(extents=[w*0.1, 0.012, d*0.1])
    _vis(dot, LABEL_MAT)
    dot.apply_translation([-w*0.3, h + BOARD_T/2 + 0.006, 0])
    parts.append(dot)
    return parts

def make_smd_inductor_shielded(w=0.4, d=0.4, h=0.22):
    """Shielded SMD inductor: solid metal cube with cross indicator."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, SHIELD_MAT)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # cross indicator on top
    for rot in (0, np.pi/2):
        bar = creation.box(extents=[w*0.65, 0.015, 0.04])
        _vis(bar, CHIP_LIGHT_MAT)
        m = tf.rotation_matrix(rot, [0, 1, 0])
        bar.apply_transform(m)
        bar.apply_translation([0, h + BOARD_T/2 + 0.008, 0])
        parts.append(bar)
    return parts

def make_smd_fuse(w=0.4, d=0.2, h=0.12):
    """SMD fuse: green/blue body with thin element visible."""
    parts = []
    body = creation.box(extents=[w, h, d])
    _vis(body, PLASTIC_BLUE)
    body.apply_translation([0, h/2 + BOARD_T/2, 0])
    parts.append(body)
    # fuse element (thin line on top)
    element = creation.box(extents=[w*0.7, 0.012, 0.02])
    _vis(element, COPPER_MAT)
    element.apply_translation([0, h + BOARD_T/2 + 0.006, 0])
    parts.append(element)
    for sx in (-1, 1):
        cap = creation.box(extents=[w*0.13, h, d])
        _vis(cap, PIN_MAT)
        cap.apply_translation([sx*(w/2 - w*0.065), h/2 + BOARD_T/2, 0])
        parts.append(cap)
    return parts

# ============ ROW DEFINITIONS ============
ROWS = [
    ("QFP / chip ICs", [
        lambda: make_qfp(1.95, 1.95, h=0.32, pins_per_side=10, top_marking='dot'),
        lambda: make_qfp(2.00, 2.00, h=0.32, pins_per_side=12, top_marking='line'),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=14, top_marking='square'),
        lambda: make_qfp(1.95, 1.95, h=0.32, pins_per_side=11, top_marking='stripe'),
        lambda: make_qfp(2.05, 2.05, h=0.34, pins_per_side=13, top_marking='cross'),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=12, top_marking='square_pin1',
                         pin_material=PIN_GOLD_MAT),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=14, top_marking='square',
                         body_material=CHIP_LIGHT_MAT),
        lambda: make_qfp(2.05, 2.05, h=0.36, pins_per_side=15, top_marking='square_pin1',
                         chamfer=True),
        lambda: make_bga(2.0, 2.0, h=0.38, grid=12),
        lambda: make_ceramic_qfp(2.05, 2.05, h=0.42, pins_per_side=13),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=13, top_marking='exposed_die'),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=14, top_marking='dual',
                         pin_material=PIN_GOLD_MAT),
        lambda: make_qfp(2.05, 2.05, h=0.36, pins_per_side=15, top_marking='square',
                         label_band=True, body_material=CHIP_LIGHT_MAT),
        lambda: make_qfp(2.00, 2.00, h=0.34, pins_per_side=12, top_marking='square_pin1',
                         chamfer=True, body_material=CERAMIC_MAT,
                         pin_material=PIN_GOLD_MAT),
        lambda: make_qfp_with_dimple(2.00, 2.00, h=0.34, pins_per_side=13),
        lambda: make_qfp_diagonal_text(2.00, 2.00, h=0.34, pins_per_side=14),
        lambda: make_qfp_two_die(2.00, 2.00, h=0.34, pins_per_side=14),
        lambda: make_qfp_bond_wires(2.05, 2.05, h=0.4, pins_per_side=12),
        lambda: make_qfp_topside_logo(2.00, 2.00, h=0.34, pins_per_side=13),
        lambda: make_qfp_with_xtal(2.00, 2.00, h=0.32, pins_per_side=12),
    ]),
    ("DIP ICs", [
        lambda: make_dip(1.55, 0.5, h=0.3, pins_per_side=7, notch_style='dot'),
        lambda: make_dip(1.6, 0.5, h=0.3, pins_per_side=8, notch_style='half_circle'),
        lambda: make_dip(1.65, 0.55, h=0.32, pins_per_side=9, notch_style='slot'),
        lambda: make_dip(1.6, 0.5, h=0.3, pins_per_side=8, notch_style='bar'),
        lambda: make_dip(1.7, 0.55, h=0.32, pins_per_side=10, notch_style='dot',
                         pin_material=PIN_GOLD_MAT),
        lambda: make_dip(1.65, 0.5, h=0.3, pins_per_side=9, notch_style='half_circle'),
        lambda: make_dip(1.75, 0.55, h=0.32, pins_per_side=10, notch_style='slot'),
        lambda: make_dip(1.7, 0.55, h=0.32, pins_per_side=9, notch_style='none'),
        lambda: make_dip_socketed(1.65, 0.55, h=0.32, pins_per_side=9),
        lambda: make_dip(1.7, 0.55, h=0.34, pins_per_side=10, notch_style='slot',
                        body_material=CERAMIC_MAT, pin_material=PIN_GOLD_MAT),
        lambda: make_dip(1.7, 0.55, h=0.32, pins_per_side=10, notch_style='dot', groove=True),
        lambda: make_dip(1.75, 0.6, h=0.34, pins_per_side=11, notch_style='half_circle',
                        body_material=CERAMIC_MAT),
        lambda: make_dip(1.65, 0.55, h=0.32, pins_per_side=9, notch_style='bar',
                        body_material=CHIP_LIGHT_MAT, pin_material=PIN_GOLD_MAT),
        lambda: make_dip(1.7, 0.55, h=0.34, pins_per_side=10, notch_style='slot',
                        groove=True, body_material=CERAMIC_MAT,
                        pin_material=PIN_GOLD_MAT),
        lambda: make_dip_window(1.7, 0.55, h=0.3, pins_per_side=9),
        lambda: make_dip_zif(1.7, 0.55, h=0.32, pins_per_side=10),
        lambda: make_dip_dual_notch(1.7, 0.55, h=0.3, pins_per_side=10),
        lambda: make_dip_with_chip_on_top(1.65, 0.55, h=0.3, pins_per_side=8),
        lambda: make_dip_speckled(1.7, 0.55, h=0.32, pins_per_side=10),
        lambda: make_dip_long(1.8, 0.55, h=0.3, pins_per_side=12),
    ]),
    ("Capacitors", [
        lambda: make_capacitor(0.30, 1.05, sections=24, top_style='flat'),
        lambda: make_capacitor(0.30, 1.05, sections=24, top_style='ring'),
        lambda: make_capacitor(0.30, 1.10, sections=28, top_style='dome'),
        lambda: make_capacitor(0.30, 1.05, sections=24, top_style='plus'),
        lambda: make_capacitor(0.30, 1.10, sections=28, top_style='ring', stripe=True),
        lambda: make_capacitor(0.32, 1.10, sections=28, top_style='plus', stripe=True,
                               top_color=CAP_TOP_RED),
        lambda: make_capacitor(0.30, 1.05, sections=24, top_style='dome', stripe=True),
        lambda: make_capacitor(0.30, 1.10, sections=32, top_style='ring',
                               top_color=CAP_TOP_RED),
        lambda: make_capacitor(0.32, 1.10, sections=28, top_style='plus', stripe=True,
                               label_band=True),
        lambda: make_capacitor(0.30, 1.10, sections=28, top_style='ring', stripe=True,
                               sleeve_color=PLASTIC_BLUE, top_color=CAP_TOP_RED),
        lambda: make_tantalum_cap(),
        lambda: make_film_cap(),
        lambda: make_stacked_cap(),
        lambda: make_capacitor(0.30, 1.10, sections=32, top_style='plus', stripe=True,
                               sleeve_color=PLASTIC_GREEN, top_color=CAP_TOP_MAT,
                               label_band=True),
        lambda: make_cap_double_stripe(),
        lambda: make_cap_squat_smd(),
        lambda: make_cap_with_band_and_dome(),
        lambda: make_cap_translucent_top(),
        lambda: make_cap_with_screw_top(),
        lambda: make_cap_with_topside_text(),
    ]),
    ("Heatsinks", [
        lambda: make_heatsink(1.85, 1.35, h=0.7, fins=7, fin_axis='x', base_style='flat'),
        lambda: make_heatsink(1.90, 1.35, h=0.7, fins=9, fin_axis='x', base_style='raised'),
        lambda: make_heatsink(1.85, 1.40, h=0.72, fins=8, fin_axis='z', base_style='flat'),
        lambda: make_heatsink(1.90, 1.40, h=0.7, fins=8, fin_axis='x', base_style='with_holes'),
        lambda: make_heatsink(1.85, 1.35, h=0.7, fins=10, fin_axis='x', fin_style='beveled'),
        lambda: make_heatsink(1.90, 1.40, h=0.72, fins=7, fin_axis='x',
                              fin_style='pinned', base_style='raised'),
        lambda: make_heatsink(1.85, 1.40, h=0.7, fins=11, fin_axis='z', base_style='with_holes'),
        lambda: make_heatsink(1.95, 1.40, h=0.75, fins=9, fin_axis='x',
                              fin_style='beveled', base_style='raised', color=HEATSINK_DARK),
        lambda: make_pin_fin_heatsink(w=1.9, d=1.4, h=0.65, grid_x=8, grid_z=6),
        lambda: make_heatsink_with_pad(w=1.9, d=1.4, h=0.7, fins=9),
        lambda: make_pin_fin_heatsink(w=1.9, d=1.4, h=0.7, grid_x=10, grid_z=7,
                                      color=HEATSINK_BLACK_ANO),
        lambda: make_heatsink(1.90, 1.40, h=0.75, fins=8, fin_axis='x', fin_style='pinned',
                              base_style='with_holes', color=HEATSINK_BLACK_ANO),
        lambda: make_heatsink(1.90, 1.40, h=0.7, fins=12, fin_axis='z',
                              fin_style='straight', base_style='raised'),
        lambda: make_pin_fin_heatsink(w=1.95, d=1.4, h=0.7, grid_x=6, grid_z=4,
                                      color=HEATSINK_BLACK_ANO),
        lambda: make_heatsink_crosshatch(w=1.9, d=1.4, h=0.7),
        lambda: make_heatsink_radial(w=1.9, d=1.4, h=0.7, blades=12),
        lambda: make_heatsink_with_fan(w=1.9, d=1.4, h=0.75),
        lambda: make_heatsink_low_profile(w=1.9, d=1.4, h=0.45, fins=14),
        lambda: make_heatsink_diagonal(w=1.85, d=1.4, h=0.7, fins=8),
        lambda: make_heatsink_extruded_holes(w=1.9, d=1.4, h=0.7, fins=9),
    ]),
    ("Octagonal / drum", [
        lambda: make_octagon(0.55, 0.6, sections=6, top_detail='none'),
        lambda: make_octagon(0.55, 0.6, sections=8, top_detail='none'),
        lambda: make_octagon(0.55, 0.6, sections=8, top_detail='ring'),
        lambda: make_octagon(0.55, 0.6, sections=8, top_detail='screw'),
        lambda: make_octagon(0.55, 0.6, sections=10, top_detail='center_pin'),
        lambda: make_octagon(0.55, 0.6, sections=12, top_detail='double_ring'),
        lambda: make_octagon(0.55, 0.6, sections=12, top_detail='screw'),
        lambda: make_octagon(0.55, 0.6, sections=16, top_detail='double_ring',
                             body_color=CHIP_LIGHT_MAT),
        lambda: make_octagon_torus_top(0.55, 0.55, sections=12),
        lambda: make_octagon_shielded(0.55, 0.6, sections=8),
        lambda: make_octagon_vented(0.58, 0.6, sections=8),
        lambda: make_octagon(0.55, 0.6, sections=8, top_detail='ring', body_color=COPPER_MAT),
        lambda: make_octagon_shielded(0.55, 0.65, sections=12),
        lambda: make_octagon(0.55, 0.6, sections=12, top_detail='center_pin',
                             body_color=CERAMIC_MAT),
        lambda: make_octagon_capped(0.55, 0.6, sections=8),
        lambda: make_octagon_label(0.55, 0.6, sections=10),
        lambda: make_octagon_with_pins(0.55, 0.6, sections=8, n_pins=4),
        lambda: make_octagon_glowing_top(0.55, 0.55, sections=12),
        lambda: make_octagon_taller(0.55, 0.85, sections=8),
        lambda: make_octagon_with_strap_diag(0.55, 0.6, sections=8),
    ]),
    ("Headers / terminals", [
        lambda: make_header(n_pins=10, spacing=0.16),
        lambda: make_header(n_pins=12, spacing=0.16, rows=2),
        lambda: make_header(n_pins=10, spacing=0.16, shrouded=True),
        lambda: make_header(n_pins=10, spacing=0.16, right_angle=True),
        lambda: make_header(n_pins=11, spacing=0.16),
        lambda: make_header(n_pins=11, spacing=0.16, rows=2, shrouded=True),
        lambda: make_header(n_pins=10, spacing=0.16, rows=2, right_angle=True),
        lambda: make_header(n_pins=12, spacing=0.15, shrouded=True),
        lambda: make_screw_terminal(n_pos=4, total_w=1.55, h=0.5),
        lambda: make_idc_header(n_pins=8, total_w=1.6),
        lambda: make_jst_header(n_pins=4, pitch=0.3),
        lambda: make_screw_terminal(n_pos=5, total_w=1.6, h=0.5),
        lambda: make_idc_header(n_pins=10, total_w=1.6),
        lambda: make_jst_header(n_pins=6, pitch=0.22),
        lambda: make_header_boxed(n_pins=10, total_w=1.6, color=PLASTIC_BLUE),
        lambda: make_header_screw_blue(n_pos=4, total_w=1.6),
        lambda: make_header_screw_black(n_pos=5, total_w=1.6),
        lambda: make_header_dual_idc(n_pins=8, total_w=1.6),
        lambda: make_header_locking(n_pins=5, total_w=1.6),
        lambda: make_header_terminal_strip(n_pos=5, total_w=1.6),
    ]),
    ("Connectors / ports", [
        lambda: make_connector(1.7, 0.55, h=0.42, slot_style='none'),
        lambda: make_connector(1.7, 0.55, h=0.42, slot_style='single'),
        lambda: make_connector(1.7, 0.6, h=0.44, slot_style='double'),
        lambda: make_connector(1.75, 0.6, h=0.45, slot_style='multi'),
        lambda: make_connector(1.7, 0.6, h=0.44, slot_style='keyed'),
        lambda: make_connector(1.7, 0.6, h=0.45, slot_style='single', latch=True),
        lambda: make_connector(1.75, 0.6, h=0.45, slot_style='multi', latch=True),
        lambda: make_connector(1.75, 0.65, h=0.48, slot_style='keyed', latch=True,
                               color=CHIP_LIGHT_MAT),
        lambda: make_usb_port(w=1.7, d=0.75, h=0.55),
        lambda: make_audio_jack(),
        lambda: make_rj45(w=1.7, d=0.85, h=0.7),
        lambda: make_card_edge_slot(w=1.7, d=0.5, h=0.5),
        lambda: make_usb_port(w=1.7, d=0.7, h=0.5),
        lambda: make_card_edge_slot(w=1.7, d=0.45, h=0.45),
        lambda: make_usb_c(w=1.7, d=0.7, h=0.5),
        lambda: make_hdmi_port(w=1.7, d=0.7, h=0.55),
        lambda: make_barrel_jack(w=1.7, d=0.7, h=0.65),
        lambda: make_sd_slot(w=1.7, d=0.7, h=0.35),
        lambda: make_micro_usb(w=1.7, d=0.7, h=0.4),
        lambda: make_rj45(w=1.7, d=0.8, h=0.65),
    ]),
    ("SMD passives / LEDs", [
        lambda: make_resistor_smd(0.8, 0.4, 0.2),
        lambda: make_resistor_smd(0.8, 0.4, 0.2),
        lambda: make_resistor_smd(0.8, 0.4, 0.2, stripe_color=LABEL_MAT),
        lambda: make_resistor_smd(0.8, 0.4, 0.2, stripe_color=CHIP_GLOW_MAT),
        lambda: make_resistor_smd(0.8, 0.4, 0.2, end_cap_material=PIN_GOLD_MAT),
        lambda: make_resistor_smd(0.8, 0.4, 0.2, end_cap_material=PIN_GOLD_MAT,
                                  stripe_color=CHIP_GLOW_WARM),
        lambda: make_resistor_smd(0.85, 0.44, 0.22, stripe_color=LABEL_MAT),
        lambda: make_resistor_smd(0.85, 0.44, 0.22, stripe_color=CHIP_GLOW_GREEN,
                                  end_cap_material=PIN_GOLD_MAT),
        lambda: make_smd_led(0.8, 0.44, 0.22, emit_color=CHIP_GLOW_RED),
        lambda: make_smd_led(0.8, 0.44, 0.22, emit_color=CHIP_GLOW_GREEN),
        lambda: make_smd_led(0.8, 0.44, 0.22, emit_color=CHIP_GLOW_MAT),
        lambda: make_smd_inductor(0.8, 0.56, 0.36),
        lambda: make_smd_4pad(0.8, 0.56, 0.22),
        lambda: make_smd_tall_cap(0.8, 0.64, 0.9),
        lambda: make_smd_diode(0.8, 0.44, 0.22),
        lambda: make_smd_xtal(0.85, 0.6, 0.32),
        lambda: make_smd_rgb_led(0.85, 0.6, 0.26),
        lambda: make_smd_transistor(0.85, 0.56, 0.28),
        lambda: make_smd_inductor_shielded(0.8, 0.64, 0.44),
        lambda: make_smd_fuse(0.85, 0.44, 0.24),
    ]),
]