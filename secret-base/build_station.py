"""Rebuild the workshop island's fence line and workstation.

Unlike build_deck.py this one only touches its own objects, so it can be re-run
on the live scene without wiping the rest of the deck.

The workstation is a long, thin three-sided desk: one straight centre run with a
shorter wing angled in at each end, a 30 mm slab on six round legs, a lit strip
along the whole front edge that turns back across each wing's end, and a glowing
interface panel let into each wing. Keyboard, trackpad and volume knob sit on the
centre run. Everything else stands on the deck floor behind it — a two-fan cube,
a watercooled tower with drive sleds beside its fans, an open-frame bench, a
five-bay drive stack and a rack of network gear, each on a lit plinth, with a
floor-standing speaker closing each end of the row and toed in at the seat.

Each unit's readable detail lives above h = 0.50, because that is where the
worktop crosses it; anything below that line is behind the desk whatever it is.
Where a unit stands is not a free choice either — stand() puts it as far back as
its own back corners allow before they foul the parapet.

The deck is polar but this desk is not, so section 4 works in its own (u, v)
frame — out from the deck centre, and across — and converts to world late.

It replaces the earlier arc console and its overhead screen bank, at 1.5x the
size; the objects those left behind are deleted at the end of section 4.

Run:  exec(open("/Users/danielku/mywebsite/secret-base/build_station.py").read())
"""

import bpy, bmesh, math

F = 6.8552                             # floor level in world Z
TAU, D = math.tau, math.radians

# --- the rim --------------------------------------------------------------
# The deck is a true circle, so S() is flat. If you deform the islands with
# organic_islands.py, flip ORGANIC to True here as well and the station will be
# built to hug the wavy rim instead. The two must agree — these are the same
# numbers organic_islands.py uses for the workshop island.
ORGANIC = False
AMP = 0.13
HARMONICS = [(2, 0.35, 1.00), (3, 2.10, 0.65), (5, 4.40, 0.40)]
_NORM = sum(w for _, _, w in HARMONICS)


def S(a):
    """Radial multiplier taking a nominal radius to the island's actual outline."""
    if not ORGANIC:
        return 1.0
    return 1.0 + AMP * sum(w * math.sin(k * a + ph) for k, ph, w in HARMONICS) / _NORM


coll = bpy.data.collections["deck_workshop"]
host = bpy.data.objects["island_pillar_workshop"]
# The deck centre is wherever clone_pillar() in build_deck.py put the pillar -
# read it off the host rather than hard-coding it, or the station is built to
# one centre and the floor under it to another.
CX, CY = host.location.x, host.location.y      # deck centre, in world X/Y


# --- bmesh kit (same conventions as build_deck.py) ------------------------
def revolve(bm, profile, a0, a1, seg):
    rings = []
    for i in range(seg + 1):
        t = a0 + (a1 - a0) * (i / seg)
        s, c, sn = S(t), math.cos(t), math.sin(t)
        rings.append([bm.verts.new((r * s * c, r * s * sn, z)) for (r, z) in profile])
    m = len(profile)
    for i in range(seg):
        A, B = rings[i], rings[i + 1]
        for j in range(m):
            k = (j + 1) % m
            try:
                bm.faces.new((A[j], B[j], B[k], A[k]))
            except ValueError:
                pass
    for ring, rev in ((rings[0], False), (rings[-1], True)):
        try:
            bm.faces.new(list(reversed(ring)) if rev else ring)
        except ValueError:
            pass


def tube(bm, r0, r1, h0, h1, a0, a1, seg=20):
    """Curved band. Radii nominal, heights relative to the floor."""
    revolve(bm, [(r0, F + h0), (r1, F + h0), (r1, F + h1), (r0, F + h1)], a0, a1, seg)


def polar(a, r, h):
    s = S(a)
    return (r * s * math.cos(a), r * s * math.sin(a), F + h)


def box(bm, pos, size, rz=0.0):
    """size is (radial, tangential, vertical) when rz is the item's own angle."""
    px, py, pz = pos
    sx, sy, sz = (v * 0.5 for v in size)
    c, s = math.cos(rz), math.sin(rz)
    vs = []
    for dz in (-sz, sz):
        for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            vs.append(bm.verts.new((px + dx * c - dy * s, py + dx * s + dy * c, pz + dz)))
    b, t = vs[:4], vs[4:]
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((b[i], b[j], t[j], t[i]))


MATDEF = {
    "graphite":     ((0.075, 0.093, 0.135), 0.45, 0.4, None, 0.0),
    "rockDark":     ((0.028, 0.040, 0.078), 1.0, 0.0, None, 0.0),
    "neonCyan":     ((0.004, 0.055, 0.075), 0.4, 0.0, (0.06, 0.55, 1.0), 1.9),
    "purpleGlow":   ((0.055, 0.020, 0.110), 0.4, 0.0, (0.55, 0.16, 1.0), 2.6),
    "lampWarm":     ((0.120, 0.070, 0.030), 0.4, 0.0, (1.0, 0.62, 0.26), 3.0),
    "screenBlue":   ((0.006, 0.030, 0.100), 0.30, 0.0, (0.05, 0.26, 1.0), 1.6),
    "displayPanel": ((0.010, 0.022, 0.048), 0.22, 0.0, (0.05, 0.14, 0.30), 0.35),
    # the workstation's own palette: one hot LED blue, smoked glass, brushed metal
    "ledBlue":      ((0.010, 0.070, 0.180), 0.35, 0.0, (0.02, 0.26, 1.0), 2.6),
    "hudBlue":      ((0.006, 0.040, 0.110), 0.40, 0.0, (0.06, 0.42, 1.0), 1.25),
    "glassPane":    ((0.012, 0.016, 0.030), 0.08, 0.0, None, 0.0, 0.20),
    "metalDark":    ((0.045, 0.050, 0.062), 0.30, 0.85, None, 0.0),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    spec = MATDEF[name]
    base, rough, metal, emit, stren = spec[:5]
    alpha = spec[5] if len(spec) > 5 else 1.0
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Emission Color"].default_value = (*(emit or (0, 0, 0)), 1)
    b.inputs["Emission Strength"].default_value = stren
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        # EEVEE renamed this between versions; set whichever this build has
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = 'BLENDED'
        if hasattr(m, "blend_method"):
            m.blend_method = 'BLEND'
        m.show_transparent_back = False
    return m


def finish(name, bm, matname):
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    old = bpy.data.objects.get(name)
    if old:
        d = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if isinstance(d, bpy.types.Mesh) and d.users == 0:
            bpy.data.meshes.remove(d)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat(matname))
    ob.location = (CX, CY, 0)
    coll.objects.link(ob)
    ob.parent = host
    ob.matrix_parent_inverse = host.matrix_world.inverted()
    return ob


def light(name, ltype, a, r, h, energy, color, size=0.4, tilt=0.85, radius=0.08):
    old = bpy.data.objects.get(name)
    if old:
        d = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if d.users == 0:
            bpy.data.lights.remove(d)
    ld = bpy.data.lights.new(name, ltype)
    ld.energy = energy
    ld.color = color
    if ltype == 'AREA':
        ld.size = size
    else:
        ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    s = S(a)
    ob.location = (CX + r * s * math.cos(a), CY + r * s * math.sin(a), F + h)
    ob.rotation_euler = (tilt, 0.0, a + math.pi / 2)      # tilted down, facing in
    coll.objects.link(ob)
    ob.parent = host
    ob.matrix_parent_inverse = host.matrix_world.inverted()
    return ob


def drop(*names):
    """Delete objects this script used to build and no longer does."""
    for n in names:
        ob = bpy.data.objects.get(n)
        if not ob:
            continue
        d = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if isinstance(d, (bpy.types.Mesh, bpy.types.Light)) and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh)
             else bpy.data.lights).remove(d)


# ---------------------------------------------------------------- placement
R = 2.78                       # deck radius — same constant build_deck.py uses
BACK0, BACK1 = D(-6), D(118)   # the arc build_deck.py leaves for the back wall
DA0, DA1 = D(20), D(92)        # the desk arc
CA = D(56)                     # centre line — the camera looks in along this

# ------------------------------------------------------------- 1. the fence
# There is no wall behind the station: the rim is railed the whole way round.
# build_deck.py builds the railing over the front arc only and walls the back,
# so this run continues the same fence across the arc the wall used to take.
# Its posts, radius and rail heights are copied from build_deck.py's railing so
# the two runs meet flush at the newels it already puts at BACK0 and BACK1.
bm = bmesh.new()
MERLONS = 26                                          # parapet crenellations
for j in range(2, MERLONS, 2):                        # posts, threaded between them
    a = BACK0 + (BACK1 - BACK0) * j / MERLONS
    box(bm, polar(a, R - 0.068, 0.405), (0.05, 0.05, 0.345), a)
for h in (0.33, 0.525):                               # rails
    tube(bm, R - 0.088, R - 0.05, h, h + 0.026, BACK0, BACK1, 48)
finish("deck_railing_back_b", bm, "mcWood")

# the wall, its pylons and its neon strip that used to stand here
drop("deck_backwall_b", "deck_pylons_b", "deck_wall_neon_b", "deckLight_wall_b")


# ------------------------------------------------- 4. the workstation
# A long, thin three-sided desk - one straight centre run with a shorter wing
# angled in at each end - with the machines standing on the deck floor behind
# it rather than on the worktop. Everything here is written at final size: the
# whole station is 1.5x the arc console it replaces, and every part of it that
# meets the floor (legs, machines, speakers) sits on it at h = 0.

PHI = D(38)                    # how far each wing turns in from the centre line
U_BACK = 1.76                  # the desk's back edge, out from the deck centre
                               # (the machines cannot come back any further -
                               # stand() already has them against the parapet -
                               # so the gap to them is opened by moving the desk)
DEPTH = 0.55                   # front to back
WC = 1.90                      # the straight centre run
LW = 0.95                      # each wing
TOP = 0.50                     # work surface height
TT = 0.030                     # slab thickness: a plank, not a plinth
MITRE = DEPTH * math.tan(PHI / 2)      # where a wing's front corner falls

gm = bmesh.new()   # graphite   bodies, frames, keycaps
dm = bmesh.new()   # rockDark   inserts, cabinets, drawer faces
nm = bmesh.new()   # neonCyan   the calmer glows: HUD graphics, indicators
hm = bmesh.new()   # ledBlue    the hot strip along the desk edge
glm = bmesh.new()  # glassPane  the tower's smoked front
mm = bmesh.new()   # metalDark  knob, driver cones, fasteners
um = bmesh.new()   # hudBlue    the flat artwork in the wing panels


# --- the station's own frame ----------------------------------------------
# The deck is polar but this desk is not: it is three straight runs. So the
# station works in (u, v) - u out from the deck centre along the station's
# centre line, v across it, left in frame positive - and only converts to world
# at the last moment. `at()` then hands back a local frame for anything that
# has to be built on a vertical plane facing the camera, like a fan or a driver.
def uvp(u, v, h):
    c, s = math.cos(CA), math.sin(CA)
    return (u * c - v * s, u * s + v * c, F + h)


def at(u, v, h, yaw=None):
    """Point function for an item at (u, v): P(depth, across, up) -> world."""
    yaw = CA if yaw is None else yaw
    x, y, z = uvp(u, v, h)
    c, s = math.cos(yaw), math.sin(yaw)

    def P(du=0.0, dv=0.0, dw=0.0):
        return (x + du * c - dv * s, y + du * s + dv * c, z + dw)
    return P


def quad(bm, va, vb, vc, vd):
    try:
        bm.faces.new((va, vb, vc, vd))
    except ValueError:
        pass


def prism(bm, pts, h0, h1):
    """Vertical solid from a footprint given as (u, v) points."""
    bot = [bm.verts.new(uvp(u, v, h0)) for u, v in pts]
    top = [bm.verts.new(uvp(u, v, h1)) for u, v in pts]
    try:
        bm.faces.new(bot[::-1])
        bm.faces.new(top)
    except ValueError:
        pass
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        quad(bm, bot[i], bot[j], top[j], top[i])


def post(bm, u, v, h0, h1, rad, seg=16, rad_top=None):
    """Upright cylinder - desk legs, the volume knob, cable runs."""
    rt = rad if rad_top is None else rad_top
    P = at(u, v, 0.0)
    bot, top = [], []
    for i in range(seg):
        c, s = math.cos(TAU * i / seg), math.sin(TAU * i / seg)
        bot.append(bm.verts.new(P(rad * c, rad * s, h0)))
        top.append(bm.verts.new(P(rt * c, rt * s, h1)))
    for i in range(seg):
        j = (i + 1) % seg
        quad(bm, bot[i], bot[j], top[j], top[i])
    try:
        bm.faces.new(bot[::-1])
        bm.faces.new(top)
    except ValueError:
        pass


def disc(bm, ctr, r0, r1, z, seg=32, t0=0.0, t1=TAU):
    """Flat ring lying on the desk. r0 = 0 fills it. z is absolute."""
    cx, cy = ctr[0], ctr[1]
    seg = max(2, seg)
    if r0 <= 1e-6:
        c = bm.verts.new((cx, cy, z))
        rim = [bm.verts.new((cx + r1 * math.cos(t0 + (t1 - t0) * i / seg),
                             cy + r1 * math.sin(t0 + (t1 - t0) * i / seg), z))
               for i in range(seg + 1)]
        for i in range(seg):
            try:
                bm.faces.new((c, rim[i], rim[i + 1]))
            except ValueError:
                pass
        return
    inner, outer = [], []
    for i in range(seg + 1):
        t = t0 + (t1 - t0) * i / seg
        c_, s_ = math.cos(t), math.sin(t)
        inner.append(bm.verts.new((cx + r0 * c_, cy + r0 * s_, z)))
        outer.append(bm.verts.new((cx + r1 * c_, cy + r1 * s_, z)))
    for i in range(seg):
        quad(bm, inner[i], outer[i], outer[i + 1], inner[i + 1])


def vring(bm, P, r0, r1, seg=24, t0=0.0, t1=TAU, du=0.0):
    """Ring standing in the plane facing the camera - fan rims, driver surrounds."""
    seg = max(2, seg)
    rows = []
    for rad in (r0, r1):
        rows.append([P(du, rad * math.cos(t0 + (t1 - t0) * i / seg),
                       rad * math.sin(t0 + (t1 - t0) * i / seg))
                     for i in range(seg + 1)])
    rows = [[bm.verts.new(p) for p in row] for row in rows]
    for i in range(seg):
        quad(bm, rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1])


def vdisc(bm, P, rad, seg=24, du=0.0):
    c = bm.verts.new(P(du))
    rim = [bm.verts.new(P(du, rad * math.cos(TAU * i / seg),
                          rad * math.sin(TAU * i / seg))) for i in range(seg)]
    for i in range(seg):
        try:
            bm.faces.new((c, rim[i], rim[(i + 1) % seg]))
        except ValueError:
            pass


def vplate(bm, P, corners, du=0.0, thick=0.006):
    """Four (across, up) corners, given depth along the facing direction."""
    A = [bm.verts.new(P(du, dv, dw)) for dv, dw in corners]
    B = [bm.verts.new(P(du + thick, dv, dw)) for dv, dw in corners]
    try:
        bm.faces.new(A[::-1])
        bm.faces.new(B)
    except ValueError:
        pass
    for i in range(4):
        quad(bm, A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i])


# --- the three desk sections ----------------------------------------------
# Section -1 and +1 are the wings, 0 is the centre. Each has an origin at its
# inboard back corner, an axis running along its length and one running back.
def sec(i):
    if i == 0:
        return (U_BACK, 0.0), (0.0, 1.0), (1.0, 0.0)
    g = 1 if i > 0 else -1
    return ((U_BACK, g * WC / 2),
            (-math.sin(PHI), g * math.cos(PHI)),
            (math.cos(PHI), g * math.sin(PHI)))


def suv(i, along, depth):
    (ou, ov), (tu, tv), (nu, nv) = sec(i)
    return (ou + along * tu - depth * nu, ov + along * tv - depth * nv)


def spt(i, along, depth, h):
    u, v = suv(i, along, depth)
    return uvp(u, v, h)


def syaw(i):
    return CA + (0.0 if i == 0 else (PHI if i > 0 else -PHI))


def foot(i):
    """The section's footprint. The three tile the top exactly at the mitres."""
    if i == 0:
        return [suv(0, -WC / 2, 0.0), suv(0, WC / 2, 0.0),
                suv(0, WC / 2 - MITRE, DEPTH), suv(0, -(WC / 2 - MITRE), DEPTH)]
    return [suv(i, 0.0, 0.0), suv(i, LW, 0.0), suv(i, LW, DEPTH), suv(i, MITRE, DEPTH)]


# --- 4a. the slab ---------------------------------------------------------
for i in (-1, 0, 1):
    prism(gm, foot(i), TOP - TT, TOP)
    prism(dm, foot(i), TOP - TT - 0.007, TOP - TT)       # shadow line under it

# the lit front edge, and the same line turning back along each wing's end
EZ = TOP - 0.024
for i in (-1, 0, 1):
    ln = (WC - 2 * MITRE) if i == 0 else (LW - MITRE)
    mid = 0.0 if i == 0 else (MITRE + LW) / 2
    box(hm, spt(i, mid, DEPTH + 0.005, EZ), (0.010, ln, 0.020), syaw(i))
for i in (-1, 1):
    box(hm, spt(i, LW + 0.005, DEPTH / 2, EZ), (DEPTH - 0.05, 0.010, 0.020), syaw(i))

# --- 4b. legs, standing on the deck ---------------------------------------
for i, along, depth in ((0, -0.78, 0.30), (0, 0.78, 0.30),
                        (-1, 0.30, 0.30), (-1, 0.84, 0.30),
                        (1, 0.30, 0.30), (1, 0.84, 0.30)):
    u, v = suv(i, along, depth)
    post(gm, u, v, 0.014, TOP - TT, 0.036, 20)
    post(dm, u, v, 0.000, 0.016, 0.052, 20)                 # foot pad
    post(gm, u, v, TOP - TT - 0.030, TOP - TT, 0.048, 20)   # collar under the slab

# --- 4c. the two lit interface panels, one in each wing --------------------
PANEL_Z = F + TOP + 0.005
PW = 0.40


def hud_cluster(bm, ctr, s, phase):
    disc(bm, ctr, 0.051 * s, 0.0535 * s, PANEL_Z, 40)
    disc(bm, ctr, 0.036 * s, 0.0378 * s, PANEL_Z, 28, phase + 0.22, phase + 4.30)
    disc(bm, ctr, 0.036 * s, 0.0378 * s, PANEL_Z, 10, phase + 4.85, phase + 5.95)
    disc(bm, ctr, 0.019 * s, 0.0208 * s, PANEL_Z, 24)
    disc(bm, ctr, 0.000, 0.005 * s, PANEL_Z, 16)
    for k in range(16):                                   # tick ring
        t = phase + k * TAU / 16
        w = 0.040 if k % 4 == 0 else 0.020
        disc(bm, ctr, 0.059 * s, (0.069 if k % 4 == 0 else 0.064) * s,
             PANEL_Z, 2, t - w, t + w)
    for k in range(3):                                    # spokes into the core
        t = phase + 1.1 + k * TAU / 3
        disc(bm, ctr, 0.023 * s, 0.033 * s, PANEL_Z, 2, t - 0.009, t + 0.009)


for i, ph in ((1, 0.0), (-1, 0.7)):
    P = at(*suv(i, LW * 0.54, DEPTH * 0.5), TOP, syaw(i))
    box(dm, P(0, 0, 0.002), (PW, PW, 0.004), syaw(i))                     # inset plate
    for du, dv, sz in ((PW / 2 - 0.004, 0.0, (0.006, PW - 0.008, 0.005)),
                       (-(PW / 2 - 0.004), 0.0, (0.006, PW - 0.008, 0.005)),
                       (0.0, PW / 2 - 0.004, (PW - 0.008, 0.006, 0.005)),
                       (0.0, -(PW / 2 - 0.004), (PW - 0.008, 0.006, 0.005))):
        box(um, P(du, dv, 0.0045), sz, syaw(i))                           # lit border
    for g in (-1, 1):
        hud_cluster(um, P(0.014, g * 0.096), 1.15, ph + 0.4 * g)
        hud_cluster(um, P(-0.135, g * 0.122), 0.34, ph + 1.9 * g)
    for k in range(6):                                                    # data blocks
        box(um, P(-0.170, -0.148 + k * 0.059, 0.0045), (0.011, 0.030, 0.005), syaw(i))
    for k in range(4):
        box(um, P(0.158 - 0.027 * k, 0.155, 0.0045),
            (0.008, 0.048 + 0.019 * k, 0.005), syaw(i))

# --- 4d. keyboard, trackpad, volume knob, on the centre run ---------------
U = 0.0249                          # key unit
KB_ALONG, KB_DEPTH = 0.10, DEPTH - 0.175
KEY_Z = TOP + 0.023

box(gm, spt(0, KB_ALONG, KB_DEPTH, TOP + 0.009), (0.177, 0.588, 0.018), CA)   # tray
box(dm, spt(0, KB_ALONG, KB_DEPTH, TOP + 0.0185), (0.159, 0.570, 0.005), CA)  # plate


def key(row, x0, w=1.0, tall=1):
    """row 0 is the function row at the back; x runs 0..22.5 left to right."""
    along = KB_ALONG + (11.25 - (x0 + w / 2)) * U
    depth = KB_DEPTH + (row + (tall - 1) / 2 - 2.5) * U
    box(dm, spt(0, along, depth, KEY_Z),
        (U * tall - 0.0042, w * U - 0.0042, 0.012), CA)


x = 0.0                                                   # function row
for i, w in enumerate([1] * 13):
    if i in (1, 5, 9):
        x += 0.5
    key(0, x, w)
    x += w
for row, widths in ((1, [1] * 13 + [2]),
                    (2, [1.5] + [1] * 12 + [1.5]),
                    (3, [1.75] + [1] * 11 + [2.25]),
                    (4, [2.25] + [1] * 10 + [2.75]),
                    (5, [1.25] * 3 + [6.25] + [1.25] * 4)):
    x = 0.0
    for w in widths:
        key(row, x, w)
        x += w
for row, xs in ((1, (15.25, 16.25, 17.25)), (2, (15.25, 16.25, 17.25)),
                (4, (16.25,)), (5, (15.25, 16.25, 17.25))):
    for x0 in xs:
        key(row, x0)
for row in range(1, 5):                                   # numpad
    for c in range(4):
        if row == 3 and c == 3:
            continue                                      # the tall + covers it
        key(row, 18.5 + c, 1.0, 2 if (row == 2 and c == 3) else 1)
key(5, 18.5, 2.0)
key(5, 20.5, 1.0)
key(5, 21.5, 1.0)

TP = KB_ALONG - 0.415                                     # trackpad
box(gm, spt(0, TP, KB_DEPTH - 0.008, TOP + 0.009), (0.123, 0.168, 0.018), CA)
box(dm, spt(0, TP, KB_DEPTH - 0.008, TOP + 0.020), (0.105, 0.150, 0.006), CA)
box(nm, spt(0, TP, KB_DEPTH - 0.083, TOP + 0.017), (0.006, 0.135, 0.003), CA)

KN = KB_ALONG + 0.425                                     # volume knob
KU, KV = suv(0, KN, KB_DEPTH + 0.018)
post(gm, KU, KV, TOP, TOP + 0.008, 0.042, 24)
post(mm, KU, KV, TOP + 0.008, TOP + 0.032, 0.034, 24, rad_top=0.0352)
disc(nm, uvp(KU, KV, 0), 0.0368, 0.0412, F + TOP + 0.0082, 24)
for k in range(20):                                       # knurling
    t = TAU * k / 20
    box(mm, at(KU, KV, TOP + 0.020)(0.0348 * math.cos(t), 0.0348 * math.sin(t)),
        (0.006, 0.006, 0.022), CA + t)

# --- 4e. the machines, standing in a row on the deck floor -----------------
# Five units, left to right: a two-fan cube, a watercooled tower with its drive
# sleds beside the fans, the open-frame bench, a five-bay drive stack, and a
# rack of network gear. They stand on the paving, not on the desk.
GZ = 0.022                          # top of a unit's lit plinth


def stand(v, w):
    """How far back a unit of this width can stand without fouling the parapet.
    It is the unit's BACK CORNERS that hit, so the wider it is and the further
    off the centre line, the further forward it has to sit."""
    return min(2.56, math.sqrt(2.60 ** 2 - (abs(v) + w / 2) ** 2))


def plinth(P, dep, wid):
    """Feet with light spilling from under them - the reference's signature."""
    box(hm, P(0, 0, 0.010), (dep + 0.012, wid + 0.012, 0.011), CA)
    for du in (-dep / 2 + 0.042, dep / 2 - 0.042):
        for dv in (-wid / 2 + 0.036, wid / 2 - 0.036):
            box(gm, P(du, dv, 0.011), (0.038, 0.038, 0.022), CA)


def shell(P, w, d, h, post=0.032, tray=True):
    """Corner posts, top and bottom caps, and a solid back panel. The tray is
    what stopped the old bench reading as a machine: without something behind
    it the board and its lights just hang in a void."""
    for du in (-d / 2, d / 2):
        for dv in (-w / 2, w / 2):
            box(gm, P(du, dv, GZ + h / 2), (post, post, h), CA)
            box(gm, P(du, dv, GZ + post * 0.8), (post * 1.5, post * 1.5, post * 1.5), CA)
            box(gm, P(du, dv, GZ + h - post * 0.8), (post * 1.5, post * 1.5, post * 1.5), CA)
    if tray:
        box(dm, P(d / 2 - 0.014, 0, GZ + h / 2), (0.022, w - 0.008, h - 0.008), CA)
    box(gm, P(0, 0, GZ + h + 0.014), (d + 0.012, w + 0.012, 0.028), CA)      # top cap
    box(gm, P(0, 0, GZ - 0.004), (d + 0.012, w + 0.012, 0.022), CA)          # bottom cap


def sides(P, w, d, h, mat=None):
    """Smoked side panels, so a unit reads as a box rather than a wireframe."""
    for dv in (-w / 2 + 0.004, w / 2 - 0.004):
        box(mat if mat is not None else glm, P(0, dv, GZ + h / 2),
            (d - 0.048, 0.007, h - 0.048), CA)


def grille(P, du, w, h, nx, ny):
    """Perforated front - a grid of punched slots."""
    for i in range(nx):
        for j in range(ny):
            box(dm, P(du, -w / 2 + w * (i + 0.5) / nx, GZ + h * (j + 0.5) / ny),
                (0.006, w / nx * 0.55, h / ny * 0.55), CA)


def fan(mu, mv, fz, rad, du):
    """A case fan on the front plane: shroud, lit rim, nine blades and a hub."""
    P = at(mu, mv, fz)
    vring(gm, P, rad, rad * 1.17, 28, du=du - 0.018)
    vring(hm, P, rad * 0.86, rad, 28, du=du - 0.014)
    vring(dm, P, rad * 0.81, rad * 0.86, 24, du=du - 0.011)
    for b in range(9):
        t = TAU * b / 9
        pts = [(rad * 0.28 * math.cos(t), rad * 0.28 * math.sin(t)),
               (rad * 0.82 * math.cos(t + 0.42), rad * 0.82 * math.sin(t + 0.42)),
               (rad * 0.82 * math.cos(t + 0.74), rad * 0.82 * math.sin(t + 0.74)),
               (rad * 0.28 * math.cos(t + 0.34), rad * 0.28 * math.sin(t + 0.34))]
        vplate(gm, P, pts, du=du - 0.008, thick=0.009)
    vdisc(gm, P, rad * 0.30, 16, du=du - 0.004)
    vring(hm, P, rad * 0.10, rad * 0.20, 12, du=du - 0.001)
    for c in range(4):
        t = TAU * c / 4 + TAU / 8
        box(gm, P(du - 0.018, rad * 1.07 * math.cos(t), rad * 1.07 * math.sin(t)),
            (0.014, 0.026, 0.026), CA)


def sled(P, du, dv, dz, w, h):
    """A hot-swap drive tray: face, latch and its own activity LED."""
    box(gm, P(du + 0.010, dv, dz), (0.021, w, h), CA)
    box(dm, P(du - 0.003, dv, dz), (0.012, w - 0.024, h - 0.024), CA)
    box(gm, P(du - 0.008, dv - w / 2 + 0.024, dz), (0.011, 0.019, h * 0.52), CA)
    box(hm, P(du - 0.008, dv + w / 2 - 0.019, dz), (0.009, 0.010, h * 0.48), CA)


def hose(P, a, b, c, rad=0.013, n=20):
    """Coolant line: a bead chain along a quadratic through three points. At
    this scale overlapping beads read as tube and cost a fraction of a sweep."""
    for k in range(n + 1):
        t = k / n
        m, q, r = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        box(dm, P(m * a[0] + q * b[0] + r * c[0],
                  m * a[1] + q * b[1] + r * c[1],
                  m * a[2] + q * b[2] + r * c[2]),
            (rad * 2, rad * 2, rad * 2), CA)


# ---- 1. the two-fan cube
CB_W, CB_D, CB_H, CB_V = 0.300, 0.300, 0.780, 1.10
CB_U = stand(CB_V, CB_W)
CB = at(CB_U - CB_D / 2, CB_V, 0.0)
CB_F = -CB_D / 2
plinth(CB, CB_D, CB_W)
shell(CB, CB_W, CB_D, CB_H)
sides(CB, CB_W, CB_D, CB_H)
grille(CB, CB_F - 0.002, CB_W - 0.070, CB_H - 0.060, 5, 14)
for k in range(2):
    fan(CB_U - CB_D / 2, CB_V, GZ + 0.440 + k * 0.215, 0.088, CB_F + 0.030)
for k in range(7):                                                    # top vents
    box(dm, CB(-CB_D / 2 + 0.048 + k * 0.034, 0, GZ + CB_H + 0.030),
        (0.014, CB_W - 0.086, 0.007), CA)
box(nm, CB(CB_F - 0.004, CB_W / 2 - 0.034, GZ + 0.044), (0.006, 0.017, 0.008), CA)

# ---- 2. the watercooled tower: fans down one side, drive sleds down the other
TW_W, TW_D, TW_H, TW_V = 0.340, 0.360, 1.000, 0.64
TW_U = stand(TW_V, TW_W)
TW = at(TW_U - TW_D / 2, TW_V, 0.0)
TW_F = -TW_D / 2
plinth(TW, TW_D, TW_W)
shell(TW, TW_W, TW_D, TW_H)
sides(TW, TW_W, TW_D, TW_H)
for k in range(3):
    fan(TW_U - TW_D / 2, TW_V + 0.072, GZ + 0.440 + k * 0.200, 0.078, TW_F + 0.034)
for k in range(3):
    sled(TW, TW_F + 0.030, -0.090, GZ + 0.460 + k * 0.180, 0.130, 0.110)
box(glm, TW(TW_F + 0.004, 0, GZ + TW_H / 2),
    (0.008, TW_W - 0.062, TW_H - 0.062), CA)                          # smoked front
for dv in (-(TW_W - 0.062) / 2, (TW_W - 0.062) / 2):
    box(mm, TW(TW_F + 0.004, dv, GZ + TW_H / 2), (0.014, 0.011, TW_H - 0.062), CA)
for dw in (-(TW_H - 0.062) / 2, (TW_H - 0.062) / 2):
    box(mm, TW(TW_F + 0.004, 0, GZ + TW_H / 2 + dw), (0.014, TW_W - 0.062, 0.011), CA)
# the radiator sits up top and its two lines loop out over the side
box(gm, TW(0.02, 0, GZ + TW_H - 0.050), (TW_D - 0.070, TW_W - 0.070, 0.060), CA)
# they have to bulge past TW_F or they run inside the case, behind the pane
for off in (0.026, -0.008):
    hose(TW, (-0.100, TW_W / 2 - 0.020 + off, GZ + TW_H - 0.055),
         (-0.265, TW_W / 2 + 0.100 + off, GZ + TW_H - 0.200),
         (-0.195, TW_W / 2 - 0.050 + off, GZ + 0.580))
for k in range(7):                                                    # top vents
    box(dm, TW(-TW_D / 2 + 0.054 + k * 0.038, 0, GZ + TW_H + 0.030),
        (0.014, TW_W - 0.098, 0.007), CA)
box(nm, TW(TW_F - 0.004, TW_W / 2 - 0.038, GZ + 0.056), (0.006, 0.019, 0.009), CA)

# ---- 3. the open-frame bench in the middle
RG_W, RG_D, RG_H, RG_V = 0.560, 0.460, 1.220, 0.0
RG_U = stand(RG_V, RG_W)
RG = at(RG_U - RG_D / 2, RG_V, 0.0)
RG_F = -RG_D / 2
plinth(RG, RG_D, RG_W)
shell(RG, RG_W, RG_D, RG_H, post=0.036)
sides(RG, RG_W, RG_D, RG_H)
for dw in (0.020, RG_H - 0.020):                                      # top/bottom rails
    for dv in (-RG_W / 2, RG_W / 2):
        box(gm, RG(0, dv, GZ + dw), (RG_D, 0.030, 0.030), CA)
    for du in (-RG_D / 2, RG_D / 2):
        box(gm, RG(du, 0, GZ + dw), (0.030, RG_W, 0.030), CA)
box(dm, RG(0.010, 0, GZ + 0.082), (RG_D - 0.060, RG_W - 0.052, 0.100), CA)   # PSU shroud
for k in range(9):
    box(gm, RG(RG_F + 0.014, -0.196 + k * 0.049, GZ + 0.082), (0.012, 0.028, 0.050), CA)
box(hm, RG(RG_F + 0.006, 0.150, GZ + 0.082), (0.008, 0.090, 0.010), CA)      # shroud strip

MB = RG_D / 2 - 0.040                 # the board hangs on the tray at the back
MZ = GZ + 0.300                       # its bottom edge, clear of the worktop
MBW, MBH = 0.470, 0.840
box(dm, RG(MB, 0, MZ + MBH / 2), (0.014, MBW, MBH), CA)                      # the board
box(gm, RG(MB - 0.012, 0, MZ + MBH / 2 + 0.060), (0.022, 0.112, 0.112), CA)  # socket frame
box(gm, RG(MB - 0.026, 0, MZ + MBH / 2 + 0.060), (0.014, 0.076, 0.076), CA)  # IHS
for k in range(4):                                                            # RAM
    dv = -0.118 - k * 0.028
    box(gm, RG(MB - 0.012, dv, MZ + 0.470), (0.022, 0.015, 0.190), CA)
    box(dm, RG(MB - 0.026, dv, MZ + 0.470), (0.009, 0.010, 0.172), CA)
for k in range(2):                                                            # M.2 covers
    box(gm, RG(MB - 0.016, 0.030, MZ + 0.190 - k * 0.062), (0.017, 0.190, 0.034), CA)
box(gm, RG(MB - 0.016, -0.118, MZ + 0.086), (0.022, 0.104, 0.062), CA)       # chipset
box(gm, RG(MB - 0.016, 0.062, MZ + MBH - 0.052), (0.026, 0.280, 0.084), CA)  # VRM bank
box(gm, RG(MB - 0.016, 0.198, MZ + MBH / 2 + 0.040), (0.026, 0.068, 0.330), CA)  # side VRM
box(dm, RG(MB - 0.012, -0.192, MZ + 0.600), (0.017, 0.028, 0.108), CA)       # 24-pin
box(dm, RG(MB - 0.012, 0.130, MZ + 0.038), (0.017, 0.120, 0.017), CA)        # PCIe slot
box(dm, RG(MB - 0.052, 0.120, MZ + 0.078), (0.070, 0.230, 0.052), CA)        # the card in it
box(gm, RG(MB - 0.090, 0.120, MZ + 0.078), (0.010, 0.230, 0.060), CA)
for k in range(10):                                                           # caps
    box(gm, RG(MB - 0.022, -0.176 + (k % 5) * 0.030,
               MZ + 0.286 + (k // 5) * 0.034), (0.013, 0.013, 0.026), CA)
for k in range(14):                                                           # header pins
    box(gm, RG(MB - 0.012, -0.196 + k * 0.024, MZ + 0.022), (0.012, 0.010, 0.021), CA)
for g in (-1, 1):                                                             # the blue bars
    box(hm, RG(MB - 0.070, g * 0.252, MZ + MBH / 2), (0.016, 0.024, MBH - 0.080), CA)
box(nm, RG(MB - 0.022, -0.176, MZ + 0.124), (0.009, 0.062, 0.009), CA)
box(nm, RG(MB - 0.022, -0.184, MZ + 0.090), (0.009, 0.046, 0.009), CA)
box(glm, RG(RG_F + 0.008, 0, GZ + RG_H / 2),
    (0.008, RG_W - 0.078, RG_H - 0.078), CA)                                  # front pane

# ---- 4. the five-bay drive stack
DS_W, DS_D, DS_H, DS_V = 0.340, 0.360, 0.960, -0.62
DS_U = stand(DS_V, DS_W)
DS = at(DS_U - DS_D / 2, DS_V, 0.0)
DS_F = -DS_D / 2
plinth(DS, DS_D, DS_W)
box(dm, DS(0, 0, GZ + DS_H / 2), (DS_D, DS_W, DS_H), CA)
box(gm, DS(0, 0, GZ + DS_H + 0.020), (DS_D - 0.022, DS_W - 0.022, 0.040), CA)   # crown
box(gm, DS(0, 0, GZ + DS_H + 0.052), (DS_D - 0.100, DS_W - 0.100, 0.024), CA)   # handle
for k in range(5):
    sled(DS, DS_F, 0.0, GZ + 0.340 + k * 0.135, DS_W - 0.038, 0.112)
box(gm, DS(DS_F + 0.006, 0, GZ + 0.900), (0.016, DS_W - 0.034, 0.056), CA)      # top panel
box(nm, DS(DS_F - 0.008, DS_W / 2 - 0.040, GZ + 0.900), (0.009, 0.016, 0.016), CA)
for k in range(5):
    box(dm, DS(DS_F - 0.006, -0.098 + k * 0.022, GZ + 0.900), (0.008, 0.010, 0.024), CA)
box(gm, DS(DS_F + 0.004, 0, GZ + 0.034), (0.016, DS_W - 0.034, 0.034), CA)      # plinth trim

# ---- 5. the network rack: router over patch panel over UPS
RK_W, RK_D, RK_H, RK_V = 0.380, 0.340, 0.900, -1.08
RK_U = stand(RK_V, RK_W)
RK = at(RK_U - RK_D / 2, RK_V, 0.0)
RK_F = -RK_D / 2
plinth(RK, RK_D, RK_W)
for dv in (-RK_W / 2, RK_W / 2):                                       # rack rails
    box(gm, RK(0, dv, GZ + RK_H / 2), (RK_D, 0.026, RK_H), CA)
box(dm, RK(RK_D / 2 - 0.012, 0, GZ + RK_H / 2), (0.020, RK_W, RK_H), CA)
box(gm, RK(0, 0, GZ + RK_H + 0.014), (RK_D + 0.012, RK_W + 0.012, 0.028), CA)
box(gm, RK(0, 0, GZ - 0.004), (RK_D + 0.012, RK_W + 0.012, 0.022), CA)

RZ = GZ + 0.790                                                        # the router, on top
box(dm, RK(0, 0, RZ), (RK_D - 0.040, RK_W - 0.034, 0.110), CA)
box(gm, RK(RK_F + 0.010, 0, RZ), (0.014, RK_W - 0.034, 0.110), CA)
for k in range(6):
    box(hm, RK(RK_F + 0.002, -0.088 + k * 0.032, RZ + 0.020), (0.008, 0.014, 0.010), CA)
for k in range(4):
    box(dm, RK(RK_F + 0.002, -0.082 + k * 0.036, RZ - 0.026), (0.008, 0.024, 0.020), CA)
for g in (-1, 1):                                                      # antennas
    for k in range(9):
        box(gm, RK(0.090, g * 0.125, RZ + 0.062 + k * 0.024), (0.014, 0.014, 0.024), CA)

PZ = GZ + 0.630                                                        # the patch panel
box(dm, RK(0, 0, PZ), (RK_D - 0.040, RK_W - 0.034, 0.130), CA)
box(gm, RK(RK_F + 0.010, 0, PZ), (0.014, RK_W - 0.034, 0.130), CA)
for row in range(2):
    for k in range(12):
        box(dm, RK(RK_F + 0.002, -0.152 + k * 0.0276, PZ + 0.030 - row * 0.048),
            (0.008, 0.019, 0.026), CA)
box(hm, RK(RK_F + 0.002, 0.152, PZ + 0.006), (0.008, 0.012, 0.086), CA)

UZ = GZ + 0.420                                                        # the UPS
box(dm, RK(0, 0, UZ), (RK_D - 0.040, RK_W - 0.034, 0.230), CA)
box(gm, RK(RK_F + 0.010, 0, UZ), (0.014, RK_W - 0.034, 0.230), CA)
box(dm, RK(RK_F + 0.000, 0.048, UZ + 0.010), (0.010, 0.130, 0.078), CA)   # display bezel
for k in range(4):
    box(hm, RK(RK_F - 0.004, 0.088 - k * 0.026, UZ + 0.010), (0.007, 0.018, 0.050), CA)
box(gm, RK(RK_F - 0.002, -0.098, UZ + 0.010), (0.012, 0.052, 0.052), CA)  # power button
box(hm, RK(RK_F - 0.008, -0.098, UZ + 0.010), (0.007, 0.026, 0.026), CA)
# --- 4f. the speakers, at the outboard ends of the machine row -------------
# They stand behind the desk with the machines rather than out in front of the
# wings, so stand() places them the same way. Being the widest things in the row
# and the furthest off the centre line, the parapet pushes them furthest
# forward - which is why the row curves toward the camera at its ends.
SP_W, SP_D = 0.300, 0.280
SP_BW, SP_BD = SP_W + 0.068, SP_D + 0.085                # the base is the widest part
SP_Z0, SP_Z1 = 0.360, 1.150                              # cabinet, above the floor
SP_TOE = D(26)                                           # toed in at the desk
for g in (1, -1):
    SV = g * 1.50
    SU = stand(SV, SP_BW)                                # its back edge
    SO = SU - SP_BD / 2                                  # the cabinet's centre line
    # Everything else in the row faces straight down the centre line, but these
    # sit 1.5 m off it, so square-on they would fire past the desk entirely.
    # at()'s yaw points BACKWARD (the baffle is at -du), so adding the toe on
    # the same sign as g swings each front in toward the seat.
    sy = CA + g * SP_TOE
    S_ = at(SO, SV, 0.0, sy)
    sf = -SP_D / 2                                       # baffle, in its frame
    box(dm, S_(0, 0, 0.017), (SP_BD, SP_BW, 0.034), sy)                          # base
    box(gm, S_(0, 0, 0.046), (SP_D + 0.038, SP_W + 0.023, 0.026), sy)
    box(gm, S_(0, 0, (0.059 + SP_Z0) / 2),
        (SP_D - 0.076, SP_W - 0.086, SP_Z0 - 0.059), sy)                         # column
    box(gm, S_(0, 0, SP_Z0 - 0.011), (SP_D + 0.019, SP_W + 0.011, 0.026), sy)    # top plate
    box(dm, S_(0, 0, (SP_Z0 + SP_Z1) / 2), (SP_D, SP_W, SP_Z1 - SP_Z0), sy)      # cabinet
    box(gm, S_(0, 0, SP_Z1 + 0.011), (SP_D + 0.015, SP_W + 0.015, 0.022), sy)    # top cap
    box(gm, S_(0, 0, SP_Z0 - 0.008), (SP_D + 0.015, SP_W + 0.015, 0.019), sy)    # bottom cap
    box(dm, S_(sf + 0.008, 0, (SP_Z0 + SP_Z1) / 2),
        (0.019, SP_W - 0.042, SP_Z1 - SP_Z0 - 0.038), sy)                        # baffle inset
    for dw, rad in ((1.010, 0.038), (0.862, 0.058), (0.670, 0.083)):             # drivers
        P = at(SO, SV, dw, sy)
        vring(gm, P, rad, rad + 0.017, 28, du=sf - 0.004)                        # chassis
        vring(mm, P, rad * 0.72, rad, 28, du=sf - 0.008)                         # surround
        vdisc(dm, P, rad * 0.74, 24, du=sf - 0.015)                              # cone
        vdisc(mm, P, rad * 0.30, 20, du=sf - 0.023)                              # dust cap
        for k in range(4):                                                       # screws
            t = TAU * k / 4 + TAU / 8
            box(mm, P(sf - 0.002, (rad + 0.011) * math.cos(t),
                      (rad + 0.011) * math.sin(t)), (0.008, 0.010, 0.010), sy)
    P = at(SO, SV, 0.520, sy)
    vring(dm, P, 0.0, 0.030, 20, du=sf - 0.008)                                  # bass port
    vring(gm, P, 0.030, 0.038, 20, du=sf - 0.004)

finish("deck_desk_b", gm, "graphite")
finish("deck_desk_dark_b", dm, "rockDark")
finish("deck_desk_neon_b", nm, "neonCyan")
finish("deck_desk_led_b", hm, "ledBlue")
_glass = finish("deck_desk_glass_b", glm, "glassPane")
_glass.visible_shadow = False
finish("deck_desk_metal_b", mm, "metalDark")
finish("deck_desk_hud_b", um, "hudBlue")

# the old console's screen bank and its warm/violet accents are gone with it
drop("deck_desk_warm_b", "deck_desk_violet_b", "deck_screens_b",
     "deck_screens_violet_b", "deck_displays_b")

# ---------------------------------------------------------------- 5. lights
# Three-quarter rig around the station. `tilt` is measured from straight down;
# a NEGATIVE tilt leans the light the other way, so a fill can sit on the deck
# side of the desk and throw back at it.
BLUE = (0.42, 0.66, 1.0)
HOT = (0.30, 0.58, 1.0)
COOL = (0.52, 0.64, 1.0)


def luv(name, ltype, u, v, h, energy, color, **kw):
    """light() in the station's own (u, v) frame."""
    return light(name, ltype, CA + math.atan2(v, u), math.hypot(u, v), h,
                 energy, color, **kw)


# key: one broad soft source over the whole station, angled in at the machines
luv("deckLight_desk_0_b", 'AREA', 1.95, 0.0, 1.75, 5.0, BLUE, size=2.4, tilt=0.62)
# fill from the deck side, or the desk front, the legs and the keyboard go black
luv("deckLight_desk_1_b", 'AREA', 1.05, 0.0, 1.45, 2.0, BLUE, size=2.8, tilt=-0.70)
# rim from behind. The wall used to bounce light back into the machines; with
# the fence there instead they sit against open cave, so they need their own
# edge or they read as three black slabs.
luv("deckLight_desk_2_b", 'AREA', 2.60, 0.0, 1.05, 3.2, COOL, size=2.0, tilt=1.75)

# the machines' own glow, one apiece
for k, (mv, mh) in enumerate(((CB_V, 0.56), (TW_V, 0.66), (RG_V, 0.80),
                             (DS_V, 0.64), (RK_V, 0.62))):
    luv(f"deckLight_desk_{3 + k}_b", 'POINT', 2.02, mv, mh, 0.8, HOT, radius=0.20)
# inside the bench, in front of the board - the one unit whose detail is deep
# enough in that the outside lamps never reach it
luv("deckLight_desk_12_b", 'POINT', RG_U - 0.20, RG_V, 0.78, 1.1, COOL, radius=0.16)
# the front edge strip, washing the floor the way it does in the reference
luv("deckLight_desk_8_b", 'AREA', U_BACK - DEPTH - 0.05, 0.0, 0.42, 1.5, HOT,
    size=2.0, tilt=0.0)
# each wing's HUD panel lifting its own patch of desk
for k, i in enumerate((1, -1)):
    u, v = suv(i, LW * 0.54, DEPTH * 0.5)
    luv(f"deckLight_desk_{9 + k}_b", 'POINT', u, v, TOP + 0.14, 0.5, BLUE, radius=0.22)
# under the slab, so the legs sit in light rather than in a black band
luv("deckLight_desk_11_b", 'AREA', U_BACK - DEPTH * 0.5, 0.0, 0.40, 0.8, BLUE,
    size=3.0, tilt=0.0)

# build_deck.py aims these at the old console's gantry, screen wall and side
# clusters - all of which this script replaces, so they light nothing now
drop("deckLight_rail_b", "deckLight_side_0_b", "deckLight_side_1_b",
     "deckLight_speaker_0_b", "deckLight_speaker_1_b")

print("station rebuilt: %.2f m desk, 5 machines and 2 speakers on the floor"
      % (WC + 2 * LW))
