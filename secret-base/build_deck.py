"""Build the secret-base deck on top of island_pillar_huge.

Everything it creates lives in the `deck_huge` collection and is named
`deck_*` / `deckLight_*`, so a re-run wipes only its own output and never
touches the pillars, the original Camera or Light.

Run:  exec(open("<path>/build_deck.py").read())
"""

import bpy, bmesh, math, random, itertools
from mathutils import Vector

TAU = math.tau
D = math.radians

def build_deck(host, coll_name, back_kind="library", suffix=""):
    """Build one island deck on top of `host`. `back_kind` picks what fills
    the back wall: "library" (bookshelves) or "workstation" (desk + gear)."""
    # ---------------------------------------------------------------- placement
    CX, CY = host.location.x, host.location.y
    ZT = host.dimensions.z          # world height of the pillar's flat top
    RTOP = 2.24                     # world radius of the pillar's flat top disc
    R = 2.78                        # deck radius; the overhang rides on corbels
    F = ZT + 0.12                   # finished floor level (everything is F + h)

    BACK0, BACK1 = D(-6), D(118)    # arc taken by the back wall
    FRONT0, FRONT1 = D(118), D(354)  # arc taken by the railing

    # Section 1 fills this with the radius of every joint between two paving
    # courses. Section 4 runs its glowing strips along those joints, so the
    # light is literally down in the cracks between the stones.
    COURSES = []


    # ---------------------------------------------------------------- materials
    def mat(name, base, rough=0.9, metal=0.0, emit=None, strength=0.0, alpha=1.0):
        m = bpy.data.materials.get(name)
        if m is None:
            m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*base, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        b.inputs["Emission Color"].default_value = (*(emit or (0, 0, 0)), 1)
        b.inputs["Emission Strength"].default_value = strength
        if alpha < 1.0:
            b.inputs["Alpha"].default_value = alpha
            m.surface_render_method = 'BLENDED'
        return m


    # names match secret-base/components/scene/materials.ts so the GLB re-skins
    MATS = {
        "rock":          mat("rock", (0.055, 0.072, 0.115), 0.95),
        "rockDark":      mat("rockDark", (0.028, 0.040, 0.078), 1.0),
        "graphite":      mat("graphite", (0.075, 0.093, 0.135), 0.45, 0.4),
        "mcWood":        mat("mcWood", (0.052, 0.030, 0.016), 0.8),
        "neonCyan":      mat("neonCyan", (0.004, 0.055, 0.075), 0.4, emit=(0.06, 0.55, 1.0), strength=1.9),
        "neonCyanFaint": mat("neonCyanFaint", (0.004, 0.055, 0.075), 0.5, emit=(0.05, 0.35, 0.72), strength=1.2),
        # The ground rings. Hot in blue and nowhere else: the strip has to be
        # well above the glare threshold to bloom at all, but a colour with any
        # real green in it goes white as soon as it clears 1.0 and the rings cut
        # the deck to ribbons. Pushing blue alone keeps the core mellow blue
        # under AgX while still carrying the energy the bloom needs.
        "runeGlow":      mat("runeGlow", (0.006, 0.030, 0.055), 0.55, emit=(0.02, 0.13, 1.00), strength=4.2),
        "lampWarm":      mat("lampWarm", (0.12, 0.07, 0.03), 0.4, emit=(1.0, 0.62, 0.26), strength=3.0),
        "purpleGlow":    mat("purpleGlow", (0.055, 0.02, 0.11), 0.4, emit=(0.55, 0.16, 1.0), strength=2.6),
        "crystal":       mat("crystal", (0.10, 0.28, 0.62), 0.15, 0.1, emit=(0.10, 0.42, 0.95), strength=1.8),
        "screenBlue":    mat("screenBlue", (0.006, 0.030, 0.10), 0.30, emit=(0.05, 0.26, 1.0), strength=1.6),
        "mcLeaves":      mat("mcLeaves", (0.035, 0.09, 0.045), 0.9),
    "displayPanel":  mat("displayPanel", (0.010, 0.022, 0.048), 0.22,
                         emit=(0.05, 0.14, 0.30), strength=0.35),
        "crateOrange":   mat("crateOrange", (0.20, 0.075, 0.020), 0.7, 0.1),
        "paperWhite":    mat("paperWhite", (0.30, 0.34, 0.42), 0.9),
        "mcFlowerRed":   mat("mcFlowerRed", (0.24, 0.035, 0.035), 0.85),
    }


    # ---------------------------------------------------------------- bmesh kit
    def revolve(bm, profile, a0=0.0, a1=TAU, seg=64):
        """Sweep an (r, z) profile polygon around the Z axis."""
        closed = abs((a1 - a0) - TAU) < 1e-6
        npts = seg if closed else seg + 1
        rings = []
        for i in range(npts):
            t = a0 + (a1 - a0) * (i / seg)
            c, s = math.cos(t), math.sin(t)
            rings.append([bm.verts.new((r * c, r * s, z)) for (r, z) in profile])
        m = len(profile)
        for i in range(seg):
            A, B = rings[i], rings[(i + 1) % npts]
            for j in range(m):
                k = (j + 1) % m
                try:
                    bm.faces.new((A[j], B[j], B[k], A[k]))
                except ValueError:
                    pass
        if not closed:
            for ring, rev in ((rings[0], False), (rings[-1], True)):
                try:
                    bm.faces.new(list(reversed(ring)) if rev else ring)
                except ValueError:
                    pass


    def rev_at(bm, cx, cy, profile, seg=10):
        """revolve() around a vertical axis through (cx, cy) instead of the origin."""
        sub = bmesh.new()
        revolve(sub, profile, seg=seg)
        sub.verts.index_update()
        for v in sub.verts:
            v.co.x += cx
            v.co.y += cy
        vmap = [bm.verts.new(v.co) for v in sub.verts]
        for f in sub.faces:
            try:
                bm.faces.new([vmap[v.index] for v in f.verts])
            except ValueError:
                pass
        sub.free()


    def tube(bm, r0, r1, z0, z1, a0=0.0, a1=TAU, seg=64):
        revolve(bm, [(r0, z0), (r1, z0), (r1, z1), (r0, z1)], a0, a1, seg)


    def box(bm, pos, size, rz=0.0):
        px, py, pz = pos
        sx, sy, sz = (s * 0.5 for s in size)
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


    def polar(a, r, h):
        return (r * math.cos(a), r * math.sin(a), F + h)


    def finish(name, bm, material, shade_flat=True):
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        name += suffix
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        if shade_flat:
            for p in me.polygons:
                p.use_smooth = False
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(MATS[material])
        ob.location = (CX, CY, 0)
        coll.objects.link(ob)
        ob.parent = host
        ob.matrix_parent_inverse = host.matrix_world.inverted()
        return ob


    # ---------------------------------------------------------------- rebuild
    old = bpy.data.collections.get(coll_name)
    if old:
        for ob in list(old.objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Light) and data.users == 0:
                bpy.data.lights.remove(data)
        coll = old
    else:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)


    # ---------------------------------------------------------------- 1. floor
    bm = bmesh.new()
    tube(bm, 0.0, RTOP + 0.18, ZT - 0.34, ZT - 0.23, seg=96)   # corbel course 1
    tube(bm, 0.0, RTOP + 0.38, ZT - 0.23, ZT - 0.12, seg=96)   # corbel course 2
    tube(bm, 0.0, R, ZT - 0.12, F, seg=96)                 # slab
    tube(bm, R - 0.17, R, F, F + 0.016, seg=96)            # kerb around the rim
    # Paving: concentric courses of irregular flagstones laid onto the slab.
    # Each course starts at its own random angle, so the joints stagger like
    # brickwork instead of lining up into spokes, and every stone gets its own
    # width, depth and thickness - that variation is what stops the surface
    # reading as a machined grid.
    pav = random.Random(4471)
    RIM = R - 0.18                          # where the paving meets the kerb
    COURSES.append(0.30)
    while COURSES[-1] < RIM - 0.115:        # last course must not end up a slit
        COURSES.append(COURSES[-1] + pav.uniform(0.135, 0.215))
    COURSES.append(RIM)
    for c in range(len(COURSES) - 1):
        ri, ro = COURSES[c], COURSES[c + 1]
        rm = (ri + ro) / 2
        a, walked = pav.uniform(0, TAU), 0.0
        while walked < TAU:
            w = min(pav.uniform(0.17, 0.40) / rm, D(30), TAU - walked)
            if w > D(1.5):
                g = 0.009 / rm              # mortar gap, half of it at each end
                # the 0.007 minimum inset is what guarantees a section 4 strip
                # always has joint to sit in, however the widths fall
                tube(bm, ri + pav.uniform(0.007, 0.016),
                     ro - pav.uniform(0.007, 0.016),
                     F - 0.010, F + pav.uniform(0.006, 0.014),
                     a + g, a + w - g, max(2, int(w / D(3.0))))
            a += w
            walked += w
    finish("deck_floor", bm, "rock")

    # ---------------------------------------------------- 2. parapet + railing
    bm = bmesh.new()
    tube(bm, R - 0.125, R, F, F + 0.20, seg=96)                # low wall all round
    tube(bm, R - 0.15, R + 0.012, F + 0.20, F + 0.232, seg=96)    # coping
    for i in range(26):                                     # merlons on the back arc
        a = BACK0 + (BACK1 - BACK0) * (i + 0.5) / 26
        box(bm, polar(a, R - 0.068, 0.286), (0.12, 0.075, 0.108), a)
    finish("deck_parapet", bm, "rockDark")

    bm = bmesh.new()
    span = FRONT1 - FRONT0
    n = 19
    for i in range(n + 1):                                  # posts
        a = FRONT0 + span * i / n
        box(bm, polar(a, R - 0.068, 0.405), (0.05, 0.05, 0.345), a)
    for h in (0.33, 0.525):                                 # rails
        tube(bm, R - 0.088, R - 0.05, F + h, F + h + 0.026, FRONT0, FRONT1, 72)
    for a in (FRONT0, FRONT1):                              # end newels
        box(bm, polar(a, R - 0.068, 0.445), (0.095, 0.095, 0.425), a)
        box(bm, polar(a, R - 0.068, 0.672), (0.125, 0.125, 0.032), a)
    finish("deck_railing", bm, "mcWood")

    # ---------------------------------------------------- 3. back wall + niche
    NICHE0, NICHE1 = D(26), D(86)
    bm = bmesh.new()
    WALL_TOP = 1.52
    tube(bm, R - 0.17, R + 0.02, F + 0.232, F + WALL_TOP, BACK0, NICHE0, 26)   # left pier
    tube(bm, R - 0.17, R + 0.02, F + 0.232, F + WALL_TOP, NICHE1, BACK1, 26)   # right pier
    tube(bm, R - 0.10, R + 0.02, F + 0.232, F + WALL_TOP, NICHE0, NICHE1, 40)  # recessed niche
    tube(bm, R - 0.10, R + 0.02, F + WALL_TOP, F + 1.62, NICHE0, NICHE1, 40)   # niche arch head
    tube(bm, R - 0.20, R + 0.045, F + WALL_TOP, F + 1.62, BACK0, NICHE0, 20)   # coping
    tube(bm, R - 0.20, R + 0.045, F + WALL_TOP, F + 1.62, NICHE1, BACK1, 20)
    for i in range(13):                                             # dentils under the arch
        a_ = NICHE0 + (NICHE1 - NICHE0) * (i + 0.5) / 13
        box(bm, polar(a_, R - 0.104, 1.565), (0.055, 0.058, 0.088), a_)
    for i in range(9):                                              # block relief
        a = BACK0 + (NICHE0 - BACK0) * (i + 0.5) / 9
        box(bm, polar(a, R - 0.005, 0.80 + 0.17 * (i % 2)), (0.10, 0.065, 0.22), a)
        a = NICHE1 + (BACK1 - NICHE1) * (i + 0.5) / 9
        box(bm, polar(a, R - 0.005, 0.80 + 0.17 * (i % 2)), (0.10, 0.065, 0.22), a)
    finish("deck_backwall", bm, "rockDark")

    bm = bmesh.new()                                                # wall neon strip
    tube(bm, R - 0.184, R - 0.17, F + 1.44, F + 1.475, BACK0 + D(2), NICHE0 - D(2), 12)
    tube(bm, R - 0.184, R - 0.17, F + 1.44, F + 1.475, NICHE1 + D(2), BACK1 - D(2), 12)
    tube(bm, R - 0.114, R - 0.10, F + 1.44, F + 1.475, NICHE0, NICHE1, 32)
    for a in (BACK0, BACK1):
        box(bm, polar(a, R - 0.275, 0.80), (0.024, 0.17, 1.02), a)
    finish("deck_wall_neon", bm, "neonCyan")

    # ---- shelving: one unit in the niche, one on each side pier -------------
    SHELF_H = (0.68, 0.96, 1.24)        # top surface of each open shelf
    WORKTOP = 0.40                      # top surface of the cabinet / plinth
    CROWN = 1.40
    BRD = 0.026                         # board thickness
    SA0, SA1 = NICHE0 + D(2.5), NICHE1 - D(2.5)
    BAYS = 5
    BAY_A = [SA0 + (SA1 - SA0) * i / BAYS for i in range(BAYS + 1)]
    # the piers sit 0.07 proud of the niche, so their unit is shifted inward
    PIER_RUNS = ((BACK0 + D(5.5), NICHE0 - D(2.5)), (NICHE1 + D(2.5), BACK1 - D(5.5)))
    PIER_BAYS = 3
    PIER_A = [[a0 + (a1 - a0) * i / PIER_BAYS for i in range(PIER_BAYS + 1)]
              for a0, a1 in PIER_RUNS]

    if back_kind == "library":
        bm = bmesh.new()


        def shelf_run(a0, a1, bays, back, front, cabinet):
            """One run of shelving between two angles, back->front in radius."""
            body = front + 0.010
            if cabinet:
                tube(bm, body, back - 0.002, F + 0.02, F + WORKTOP - 0.035, a0, a1, 26)
                tube(bm, front - 0.012, back + 0.014, F + WORKTOP - 0.035, F + WORKTOP,
                     a0 - D(1), a1 + D(1), 26)
                for i in range(3):
                    d0 = a0 + (a1 - a0) * i / 3 + D(0.8)
                    d1 = a0 + (a1 - a0) * (i + 1) / 3 - D(0.8)
                    tube(bm, front, front + 0.011, F + 0.06, F + WORKTOP - 0.09, d0, d1, 10)
                    box(bm, polar((d0 + d1) / 2, front - 0.010, WORKTOP - 0.15),
                        (0.022, 0.075, 0.018), (d0 + d1) / 2)
            else:
                tube(bm, body, back - 0.002, F + 0.02, F + WORKTOP - BRD, a0, a1, 20)
                tube(bm, front - 0.008, back + 0.010, F + WORKTOP - BRD, F + WORKTOP,
                     a0 - D(1), a1 + D(1), 20)
            # planked back panel with shallow grooves
            tube(bm, back - 0.012, back, F + WORKTOP, F + CROWN, a0, a1, 22)
            for i in range(bays * 2):
                q0 = a0 + (a1 - a0) * i / (bays * 2) + D(0.3)
                q1 = a0 + (a1 - a0) * (i + 1) / (bays * 2) - D(0.3)
                tube(bm, back - 0.024, back - 0.012, F + WORKTOP, F + CROWN, q0, q1, 5)
            # boards, each with a slim proud lip
            for h in SHELF_H + (CROWN,):
                tube(bm, body, back - 0.002, F + h - BRD, F + h, a0, a1, 22)
                tube(bm, front, body + 0.001, F + h - 0.030, F + h - 0.005, a0, a1, 22)
            # side jambs and bay dividers
            edges = [a0 + (a1 - a0) * i / bays for i in range(bays + 1)]
            for k, a_ in enumerate(edges):
                w = 0.030 if k in (0, bays) else 0.018
                box(bm, polar(a_, (back + body) / 2, (WORKTOP + CROWN) / 2),
                    (back - body, w, CROWN - WORKTOP), a_)
            tube(bm, front - 0.008, back + 0.010, F + CROWN, F + CROWN + 0.030,
                 a0 - D(1.5), a1 + D(1.5), 22)


        NICHE_BACK, NICHE_FRONT = R - 0.108, R - 0.228      # against the recessed niche wall
        PIER_BACK, PIER_FRONT = R - 0.178, R - 0.294        # against the piers, 0.07 further in
        shelf_run(SA0, SA1, BAYS, NICHE_BACK, NICHE_FRONT, cabinet=True)
        for (a0, a1) in PIER_RUNS:
            shelf_run(a0, a1, PIER_BAYS, PIER_BACK, PIER_FRONT, cabinet=False)
        finish("deck_shelves", bm, "mcWood")
    else:
        # ---- workstation ----------------------------------------------------
        # Modules of deliberately different footprint and height, sharing one
        # language: graphite bodies, rockDark inserts, thin emissive strips.
        WS = {}

        def wput(key):
            return WS.setdefault(key, bmesh.new())

        def wxy(a, rr):
            return rr * math.cos(a), rr * math.sin(a)

        def slab(a, cr, z0, z1, dep, wid, key="graphite"):
            box(wput(key), polar(a, cr, (z0 + z1) / 2), (dep, wid, z1 - z0), a)

        def ring(a, rr, z0, z1, r0, r1, key, seg=14):
            rev_at(wput(key), *wxy(a, rr),
                   [(r0, F + z0), (r1, F + z0), (r1, F + z1), (r0, F + z1)], seg=seg)

        mid = (SA0 + SA1) / 2
        DT = 0.50                               # desk top surface, above F
        DTT = 0.10                              # top slab thickness
        gm = wput("graphite")
        PIER_R, NICHE_R = R - 0.17, R - 0.10    # inner faces to build against

        # --- a tall stepped column; the tallest ones break the wall silhouette
        def mod_tower(a, top, wid=0.20, dep=0.28, br=None):
            br = PIER_R if br is None else br
            cr = br - dep / 2
            slab(a, cr, 0.00, 0.16, dep + 0.06, wid + 0.08)
            slab(a, cr, 0.16, top - 0.20, dep, wid)
            slab(a, cr, top - 0.20, top - 0.11, dep + 0.05, wid + 0.07)      # collar
            slab(a, cr, top - 0.11, top, dep * 0.62, wid * 0.62)             # cap
            slab(a, cr - dep / 2 - 0.006, 0.28, top - 0.30, 0.012, 0.030, "neonCyan")
            for k in range(int((top - 0.55) / 0.17)):
                z = 0.34 + k * 0.17
                slab(a, cr - dep / 2 - 0.004, z, z + 0.055, 0.010, wid * 0.58, "rockDark")

        # --- a squat cylinder, for a shape that isn't a box
        def mod_drum(a, top, rr=0.17, br=None):
            br = PIER_R if br is None else br
            cr = br - rr - 0.03
            rev_at(gm, *wxy(a, cr),
                   [(0.0, F + 0.02), (rr + 0.045, F + 0.02), (rr + 0.045, F + 0.11),
                    (rr, F + 0.16), (rr, F + top - 0.13), (rr + 0.045, F + top - 0.08),
                    (rr + 0.045, F + top), (0.0, F + top)], seg=16)
            for z in (0.30, 0.56, 0.82):
                if z < top - 0.20:
                    ring(a, cr, z, z + 0.026, rr + 0.002, rr + 0.014, "neonCyan", 16)

        # --- low console with a canted, stepped control face
        def mod_console(a, wid, top=0.74, dep=0.42, br=None):
            br = PIER_R if br is None else br
            cr = br - dep / 2
            slab(a, cr, 0.00, 0.11, dep, wid + 0.05)
            slab(a, cr, 0.11, top - 0.24, dep, wid)
            for k in range(5):
                z = top - 0.24 + k * 0.048
                back = 0.036 * k                        # each slat leans further back
                slab(a, cr - dep / 2 + 0.075 + back, z, z + 0.048, 0.11, wid - 0.03)
                if k % 2 == 0:
                    slab(a, cr - dep / 2 + 0.022 + back, z + 0.013, z + 0.032,
                         0.010, wid * 0.62, ("neonCyan", "lampWarm")[k // 2 % 2])

        # --- horizontal rack of units with an indicator grid
        def mod_rack(a0, a1, z0, rows, br=None):
            br = PIER_R if br is None else br
            for a in (a0, a1):
                slab(a, br - 0.115, z0 - 0.03, z0 + rows * 0.062 + 0.03, 0.19, 0.030)
            for k in range(rows):
                z = z0 + k * 0.062
                tube(gm, br - 0.20, br - 0.02, F + z, F + z + 0.046, a0, a1, 20)
                for j in range(7):
                    aa = a0 + (a1 - a0) * (j + 0.5) / 7
                    key = ("neonCyan", "lampWarm", "purpleGlow", "neonCyan")[(k * 2 + j) % 4]
                    box(wput(key), polar(aa, br - 0.196, z + 0.023), (0.010, 0.020, 0.014), aa)

        # --- bundled conduit climbing the wall
        def mod_conduit(a, z0, top, n=3, br=None):
            br = PIER_R if br is None else br
            for k in range(n):
                aa = a + D(2.4) * (k - (n - 1) / 2)
                rr = br - 0.060 - 0.014 * (k % 2)
                rev_at(gm, *wxy(aa, rr),
                       [(0.028, F + z0), (0.038, F + z0), (0.038, F + top), (0.028, F + top)], seg=8)
                for z in (z0 + 0.22, z0 + 0.60, z0 + 0.98):
                    if z < top - 0.10:
                        ring(aa, rr, z, z + 0.036, 0.028, 0.054, "graphite", 8)

        # --- the emitter that a hologram would rise out of (no screen yet)
        def holo_emitter(a, rr, s=1.0):
            slab(a, rr, DT, DT + 0.020 * s, 0.20 * s, 0.26 * s)               # base plate
            slab(a, rr, DT + 0.020 * s, DT + 0.034 * s, 0.15 * s, 0.20 * s)
            slab(a, rr, DT + 0.034 * s, DT + 0.125 * s, 0.075 * s, 0.085 * s)  # post
            slab(a, rr, DT + 0.125 * s, DT + 0.160 * s, 0.17 * s, 0.30 * s)    # emitter head
            ring(a, rr, DT + 0.160 * s, DT + 0.174 * s, 0.034 * s, 0.062 * s, "neonCyan", 18)
            slab(a, rr - 0.088 * s, DT + 0.136 * s, DT + 0.150 * s, 0.008, 0.20 * s, "neonCyan")

        # ================= desk =================
        tube(gm, R - 0.66, R - 0.10, F + DT - DTT, F + DT, SA0 - D(1.5), SA1 + D(1.5), 44)
        tube(gm, R - 0.66, R - 0.632, F + 0.20, F + DT - DTT, SA0, SA1, 44)        # fascia
        tube(gm, R - 0.60, R - 0.16, F + 0.17, F + 0.20, SA0 + D(3), SA1 - D(3), 40)
        for k in range(4):
            a = SA0 + (SA1 - SA0) * (k + 0.5) / 4
            box(gm, polar(a, R - 0.38, 0.20), (0.52, 0.045, 0.40), a)             # legs
        tube(wput("neonCyan"), R - 0.674, R - 0.650, F + DT - DTT - 0.045,
             F + DT - DTT - 0.017, SA0, SA1, 44)

        # holo emitters where the screens will go - one wide, two flanking
        holo_emitter(mid, R - 0.30, 1.25)
        holo_emitter(mid - D(21), R - 0.28, 0.85)
        holo_emitter(mid + D(21), R - 0.28, 0.85)

        # ================= gantry over the desk =================
        # masts either side of the niche, carrying a truss above the wall line,
        # with the emitter rail slung underneath it
        for ma in (NICHE0 + D(0.5), NICHE1 - D(0.5)):
            slab(ma, R - 0.18, 0.00, 0.14, 0.24, 0.22)
            slab(ma, R - 0.18, 0.14, 2.24, 0.115, 0.115)
            slab(ma, R - 0.18, 2.24, 2.35, 0.19, 0.19)
            slab(ma, R - 0.242, 0.62, 1.60, 0.010, 0.024, "neonCyan")
        tube(gm, R - 0.225, R - 0.135, F + 2.20, F + 2.275, NICHE0, NICHE1, 34)
        for k in range(9):                                        # truss webbing
            a = NICHE0 + (NICHE1 - NICHE0) * (k + 0.5) / 9
            slab(a, R - 0.18, 2.09, 2.20, 0.075, 0.045)
        tube(gm, R - 0.205, R - 0.155, F + 2.04, F + 2.09, NICHE0 + D(2), NICHE1 - D(2), 30)
        tube(gm, R - 0.230, R - 0.130, F + 1.98, F + 2.04, mid - D(24), mid + D(24), 30)
        tube(wput("neonCyan"), R - 0.216, R - 0.144, F + 1.972, F + 1.984,
             mid - D(23), mid + D(23), 30)                        # wash bar over the screens

        # ================= machinery, left pier =================
        mod_tower(D(3.0), 2.15, wid=0.23)
        mod_drum(D(11.5), 1.10)
        mod_console(D(19.5), 0.30, top=0.74)

        # ================= machinery, right pier =================
        mod_console(D(93.0), 0.32, top=0.66)
        mod_rack(D(98.5), D(106.0), 0.44, 6)
        mod_tower(D(110.5), 1.88, wid=0.18)
        mod_conduit(D(114.0), 0.02, 1.46, 2)

        # ================= display wall =================
        # Placeholder panels. Each is its own object (deck_display_NN) carrying
        # the `displayPanel` material, so any of them can be retextured alone.
        # main group: one big panel with a spaced row above it. The flanking
        # panels moved off the wall entirely, into the side clusters below.
        DISPLAYS = ((0.0, 1.30, 0.82, 1.18),        # da deg, width, height, z centre
                    (-25.0, 0.44, 0.26, 1.80),
                    (0.0, 0.52, 0.26, 1.80),
                    (25.0, 0.44, 0.26, 1.80))
        DISP_R = R - 0.22
        # frame the array sits on: two rails and a pair of intermediate posts
        for z0 in (0.66, 1.94):
            tube(gm, R - 0.195, R - 0.135, F + z0, F + z0 + 0.045,
                 mid - D(26), mid + D(26), 30)
        for da in (-D(16.5), D(16.5), -D(25.0), D(25.0)):
            slab(mid + da, R - 0.165, 0.66, 1.985, 0.055, 0.050)
        for i, (dda, wd, hg, zc) in enumerate(DISPLAYS, 1):
            a = mid + D(dda)
            box(gm, polar(a, DISP_R + 0.022, zc), (0.030, wd + 0.048, hg + 0.048), a)
            slab(a, DISP_R - 0.010, zc - hg / 2 - 0.020, zc - hg / 2 - 0.006,
                 0.008, wd * 0.82, "neonCyan")                    # under-bezel strip
            for arm in (-1, 1):                                   # mount arms to the frame
                slab(a + arm * (wd * 0.34) / DISP_R, DISP_R + 0.048, zc - 0.02, zc + 0.02,
                     0.075, 0.035)
            pbm = bmesh.new()
            box(pbm, polar(a, DISP_R, zc), (0.012, wd, hg), a)
            finish(f"deck_display_{i:02d}", pbm, "displayPanel")

        # ---- side screen clusters, freestanding out on the deck ------------
        SIDE_CLUSTERS = (D(12.0), D(100.0))
        SIDE_R = 1.80
        SIDE_PANELS = ((0.0, 0.70, 0.50, 1.22),     # da deg, width, height, z centre
                       (-23.0, 0.34, 0.38, 1.16),
                       (23.0, 0.34, 0.38, 1.16))
        for ci, ca in enumerate(SIDE_CLUSTERS, 1):
            rev_at(gm, *wxy(ca, SIDE_R),
                   [(0.0, F + 0.02), (0.27, F + 0.02), (0.27, F + 0.075),
                    (0.20, F + 0.098), (0.0, F + 0.098)], seg=18)          # foot
            slab(ca, SIDE_R, 0.098, 0.94, 0.16, 0.18)                      # column
            tube(gm, SIDE_R - 0.034, SIDE_R + 0.034, F + 0.930, F + 0.972,
                 ca - D(28), ca + D(28), 18)                               # yoke
            slab(ca, SIDE_R - 0.090, 0.30, 0.80, 0.010, 0.032, "neonCyan")
            for pi, (dda, wd, hg, zc) in enumerate(SIDE_PANELS, 1):
                a = ca + D(dda)
                box(gm, polar(a, SIDE_R + 0.020, zc), (0.028, wd + 0.044, hg + 0.044), a)
                slab(a, SIDE_R - 0.010, zc - hg / 2 - 0.021, zc - hg / 2 - 0.007,
                     0.008, wd * 0.80, "neonCyan")
                pbm = bmesh.new()
                box(pbm, polar(a, SIDE_R, zc), (0.012, wd, hg), a)
                finish(f"deck_display_side{ci}_{pi}", pbm, "displayPanel")

        # ================= floorstanding speakers =================
        for sa in (SA0 - D(5.5), SA1 + D(5.5)):
            box(gm, polar(sa, R - 0.44, 0.360), (0.20, 0.24, 0.72), sa)           # cabinet
            box(gm, polar(sa, R - 0.44, 0.735), (0.24, 0.28, 0.026), sa)          # cap
            for dh, dsz in ((0.22, 0.150), (0.44, 0.100), (0.58, 0.068)):
                box(wput("rockDark"), polar(sa, R - 0.545, dh), (0.012, dsz, dsz), sa)
            box(wput("neonCyan"), polar(sa, R - 0.547, 0.095), (0.007, 0.16, 0.011), sa)
            box(wput("neonCyan"), polar(sa, R - 0.44, 0.752), (0.17, 0.21, 0.008), sa)

        # ================= desk kit =================
        box(wput("rockDark"), polar(mid + D(2), R - 0.43, DT + 0.0015), (0.20, 0.68, 0.003), mid)
        box(gm, polar(mid, R - 0.44, DT + 0.009), (0.135, 0.44, 0.018), mid)           # keyboard
        box(gm, polar(mid + D(9.5), R - 0.42, DT + 0.012), (0.075, 0.048, 0.024), mid) # mouse
        for da, w_, h_ in ((-D(25), 0.16, 0.075), (D(26), 0.13, 0.055)):
            a = mid + da
            box(gm, polar(a, R - 0.34, DT + h_ / 2), (0.13, w_, h_), a)
            box(wput("neonCyan"), polar(a, R - 0.406, DT + h_ / 2), (0.006, w_ * 0.6, 0.010), a)
        rev_at(wput("paperWhite"), *wxy(mid + D(15), R - 0.44),
               [(0.0, F + DT), (0.035, F + DT), (0.035, F + DT + 0.072),
                (0.028, F + DT + 0.072), (0.028, F + DT + 0.010), (0.0, F + DT + 0.010)], seg=10)

        for key in sorted(WS):
            finish(f"deck_ws_{key}", WS[key], key)

    # corner pylons at the ends of the back wall
    bm = bmesh.new()
    for a in (BACK0, BACK1):
        box(bm, polar(a, R - 0.12, 0.84), (0.30, 0.30, 1.36), a)
        box(bm, polar(a, R - 0.12, 1.57), (0.36, 0.36, 0.10), a)
    finish("deck_pylons", bm, "rockDark")

    # --------------------------------------------- 4. ground light pattern
    # Four rings, spread evenly from the hub out to the kerb. They have to sit
    # in a joint between two paving courses, and the courses are not evenly
    # spaced, so the radii are picked evenly and then snapped to the nearest
    # joint - the snap is what reconciles the two.
    #
    # Every strip is narrower than the joint it lies in and fills it flush with
    # the stones either side: drop GZ1 lower and the outer rings disappear
    # behind the stones at grazing angles. The glow around them is bloom, from
    # the glare node in section 11 - not extra geometry.
    RINGS = 4
    RIM_CLEAR = 0.30        # keep the outer ring back off the kerb and the fence
    GZ0, GZ1 = F - 0.020, F + 0.017
    bm = bmesh.new()
    grnd = random.Random(77021)
    # Snapping each evenly-spaced target to its nearest joint gets the nearest
    # joint to each, which is not the same as the most even SET - it left one
    # gap 30% shorter than its neighbours. So the outermost rings are pinned and
    # the inner ones are searched for, taking whichever combination makes the
    # gaps closest to equal.
    joints = [c for c in COURSES[1:-1] if c < RIM - RIM_CLEAR]
    picks = None
    best = None
    for mid in itertools.combinations(joints[1:-1], RINGS - 2):
        rs = [joints[0], *mid, joints[-1]]
        gaps = [b - a for a, b in zip(rs, rs[1:])]
        spread = max(gaps) - min(gaps)
        if best is None or spread < best:
            best, picks = spread, rs
    for rr in picks:
        # each ring draws its arcs and gaps from its own ranges, so one reads as
        # a near-continuous line and the next as two or three dashes
        w = grnd.uniform(0.0038, 0.0060)
        amin, amax = grnd.uniform(9, 22), grnd.uniform(36, 74)
        gmin, gmax = grnd.uniform(8, 20), grnd.uniform(28, 66)
        a = grnd.uniform(0, TAU)
        walked = 0.0
        while walked < TAU:
            arc = D(grnd.uniform(amin, amax))
            arc = min(arc, TAU - walked)
            if arc > D(2):
                tube(bm, rr - w / 2, rr + w / 2, GZ0, GZ1, a, a + arc,
                     max(2, int(arc / D(2.5))))
            step = arc + D(grnd.uniform(gmin, gmax))
            a += step
            walked += step
    finish("deck_runes", bm, "runeGlow")

    # -------------------------------------------------------------- 5. hub
    # A shallow disc, not a stepped dais - 22 mm tall, flush with the pattern.
    bm = bmesh.new()
    tube(bm, 0.0, 0.30, GZ0, F + 0.022, seg=96)
    finish("deck_hub", bm, "rock")

    bm = bmesh.new()
    tube(bm, 0.256, 0.284, F + 0.006, F + 0.026, seg=96)
    tube(bm, 0.0, 0.155, F + 0.022, F + 0.028, seg=72)
    finish("deck_hub_glow", bm, "neonCyan")

    # ------------------------------------------------------------ 6. lanterns
    # The lanterns sit on the railing posts, not on stakes of their own, so their
    # angles are not free: every third post of the front run. The two ends of
    # that run are newels, which are taller than the posts between them, so each
    # lantern is given its own post's top rather than one shared height.
    POST_R = R - 0.068                      # the railing's radius
    POST_TOP, NEWEL_TOP = 0.5775, 0.688
    LANTERNS = []
    for i in range(1, 20, 3):
        a = FRONT0 + (FRONT1 - FRONT0) * i / 19
        LANTERNS.append((a, NEWEL_TOP if i in (0, 19) else POST_TOP))

    bm = bmesh.new()
    for a, top in LANTERNS:
        box(bm, polar(a, POST_R, top + 0.010), (0.060, 0.060, 0.020), a)    # collar
        box(bm, polar(a, POST_R, top + 0.152), (0.104, 0.104, 0.024), a)    # roof
        box(bm, polar(a, POST_R, top + 0.182), (0.052, 0.052, 0.036), a)    # finial
    finish("deck_lantern_posts", bm, "mcWood")

    bm = bmesh.new()
    for a, top in LANTERNS:
        box(bm, polar(a, POST_R, top + 0.080), (0.070, 0.070, 0.120), a)
    finish("deck_lantern_glass", bm, "lampWarm")

    # floor braziers flanking the front
    BRAZIERS = [D(206), D(266), D(150), D(322)]
    bm = bmesh.new()
    for a in BRAZIERS:
        tube(bm, 0.0, 0.082, F + 0.016, F + 0.235, seg=16)
        tube(bm, 0.0, 0.122, F + 0.235, F + 0.278, seg=16)
    finish("deck_braziers", bm, "rock")

    bm = bmesh.new()
    for a in BRAZIERS:
        cx, cy, _ = polar(a, 1.0, 0)
        revolve(bm, [(0.070, F + 0.278), (0.048, F + 0.368), (0.0, F + 0.442)], seg=16)
    finish("deck_brazier_flames", bm, "purpleGlow")

    # braziers/flames are built at the origin, so offset each copy afterwards
    for name in ("deck_braziers", "deck_brazier_flames"):
        ob = bpy.data.objects[name + suffix]
        me = ob.data
        bm = bmesh.new(); bm.from_mesh(me)
        src = [v.co.copy() for v in bm.verts]
        faces = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        bm = bmesh.new()
        for a in BRAZIERS:
            off = Vector(((R - 0.42) * math.cos(a), (R - 0.42) * math.sin(a), 0))
            vs = [bm.verts.new(c + off) for c in src]
            for f in faces:
                try:
                    bm.faces.new([vs[i] for i in f])
                except ValueError:
                    pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = False

    # ------------------------------------------------------------- 7. crystal
    CRY = D(118)
    bm = bmesh.new()
    box(bm, polar(CRY, R - 0.12, 1.69), (0.22, 0.22, 0.14), CRY)
    finish("deck_crystal_base", bm, "rock")

    bm = bmesh.new()
    cx, cy = (R - 0.12) * math.cos(CRY), (R - 0.12) * math.sin(CRY)
    z0 = F + 1.80
    pts = [(0.0, z0 - 0.10)]
    for k, (rr, hh) in enumerate(((0.095, 0.065), (0.110, 0.185), (0.058, 0.285), (0.0, 0.385))):
        pts.append((rr, z0 + hh))
    sub = bmesh.new()
    revolve(sub, pts, seg=6)
    for v in sub.verts:
        v.co.x += cx
        v.co.y += cy
    bmesh.ops.remove_doubles(sub, verts=sub.verts[:], dist=1e-4)
    bmesh.ops.recalc_face_normals(sub, faces=sub.faces[:])
    me = bpy.data.meshes.new("deck_crystal")
    sub.to_mesh(me); sub.free()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("deck_crystal", me)
    ob.data.materials.append(MATS["purpleGlow"])
    ob.location = (CX, CY, 0)
    coll.objects.link(ob)
    ob.parent = host
    ob.matrix_parent_inverse = host.matrix_world.inverted()

    # -------------------------------------------------------------- 8. benches
    BENCHES = [(D(20), R - 0.56, 0.80), (D(92), R - 0.56, 0.80),
               (D(160), R - 0.58, 0.62), (D(312), R - 0.58, 0.62)]
    bm = bmesh.new()
    for a, r, ln in BENCHES:
        box(bm, polar(a, r, 0.492), (ln, 0.30, 0.036), a + math.pi / 2)
        for dx in (-ln / 2 + 0.05, ln / 2 - 0.05):
            for dy in (-0.108, 0.108):
                ca, sa = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
                px = r * math.cos(a) + dx * ca - dy * sa
                py = r * math.sin(a) + dx * sa + dy * ca
                box(bm, (px, py, F + 0.245), (0.034, 0.034, 0.474), a)
    finish("deck_benches", bm, "mcWood")

    bm = bmesh.new()                                        # screens + boxes on top
    for (a, r, ln), kind in zip(BENCHES, ("screen", "screen", "box", "screen")):
        ca, sa = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
        def at(dx, dy, h, sz, rot=0.0):
            px = r * math.cos(a) + dx * ca - dy * sa
            py = r * math.sin(a) + dx * sa + dy * ca
            box(bm, (px, py, F + h), sz, a + math.pi / 2 + rot)
        if kind == "screen":
            at(-0.13, 0.070, 0.632, (0.255, 0.016, 0.185))
            at(0.175, 0.042, 0.585, (0.145, 0.014, 0.100), D(18))
    finish("deck_screens", bm, "screenBlue")

    bm = bmesh.new()                                        # clutter
    for a, r, ln in BENCHES:
        ca, sa = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
        for dx, dy, sz in ((0.24, -0.07, 0.070), (-0.29, -0.055, 0.090), (0.03, -0.085, 0.055)):
            px = r * math.cos(a) + dx * ca - dy * sa
            py = r * math.sin(a) + dx * sa + dy * ca
            box(bm, (px, py, F + 0.510 + sz / 2), (sz, sz, sz), a + D(23))
    finish("deck_clutter", bm, "graphite")

    if back_kind == "library":
        # ---- what stands on the shelves: books ----------------------------------
        # Seeded RNG so a rebuild is reproducible.
        rnd = random.Random(20250830)
        SHELF_BM = {}


        def sput(key):
            return SHELF_BM.setdefault(key, bmesh.new())


        def shelf_xy(a, rr):
            return rr * math.cos(a), rr * math.sin(a)


        BOOK_MATS = (["mcWood"] * 6 + ["mcFlowerRed"] * 5 + ["crateOrange"] * 4
                     + ["graphite"] * 5 + ["paperWhite"] * 2
                     + ["neonCyanFaint"] * 2 + ["purpleGlow"])


        def put_books(b0, b1, z, clear, rmid, dep):
            """A row of upright spines, with the odd gap where one is missing."""
            n = rnd.randint(9, 14)
            for i in range(n):
                if rnd.random() < 0.07:
                    continue
                a = b0 + (b1 - b0) * (i + 0.5) / n
                th = (b1 - b0) / n * rmid * 0.82
                h = min(clear - 0.018, rnd.uniform(0.105, 0.190))
                box(sput(rnd.choice(BOOK_MATS)), (*shelf_xy(a, rmid), z + h / 2), (dep, th, h), a)


        def put_stack(b0, b1, z, clear, rmid, dep):
            """A pile of flat-laid books, with upright ones filling the rest of the bay."""
            cut = b0 + (b1 - b0) * rnd.uniform(0.38, 0.5)
            put_books(cut, b1, z, clear, rmid, dep) if rnd.random() < 0.5 else None
            b1 = cut
            n = rnd.randint(1, 2)
            for j in range(n):
                a = b0 + (b1 - b0) * (j + 0.5) / n
                zz = z
                for _ in range(rnd.randint(2, 4)):
                    t = rnd.uniform(0.016, 0.026)
                    if zz + t > z + clear - 0.010:
                        break
                    box(sput(rnd.choice(BOOK_MATS)),
                        (*shelf_xy(a + D(rnd.uniform(-1.0, 1.0)), rmid), zz + t / 2),
                        (dep * rnd.uniform(0.72, 0.94), (b1 - b0) * rmid * 0.30, t),
                        a + D(rnd.uniform(-5, 5)))
                    zz += t


        def put_crates(b0, b1, z, clear, rmid, dep):
            cut = b0 + (b1 - b0) * 0.45
            put_books(cut, b1, z, clear, rmid, dep)
            b1 = cut
            n = rnd.randint(1, 2)
            for i in range(n):
                a = b0 + (b1 - b0) * (i + 0.5) / n
                h = min(clear - 0.020, rnd.uniform(0.070, 0.110))
                box(sput(rnd.choice(("crateOrange", "mcWood"))),
                    (*shelf_xy(a, rmid), z + h / 2),
                    (dep * 0.9, rnd.uniform(0.055, 0.085), h), a)


        def put_papers(b0, b1, z, clear, rmid, dep):
            for _ in range(rnd.randint(2, 4)):
                a = b0 + (b1 - b0) * rnd.uniform(0.2, 0.8)
                t = rnd.uniform(0.009, 0.018)
                box(sput("paperWhite"), (*shelf_xy(a, rmid), z + t / 2 + 0.001),
                    (dep * 0.8, rnd.uniform(0.045, 0.075), t), a + D(rnd.uniform(-8, 8)))


        KINDS = {"books": put_books, "stack": put_stack, "crates": put_crates, "papers": put_papers}
        MIX = ("books", "books", "books", "books", "books", "books", "stack", "crates")
        LOW_MIX = ("books", "books", "stack", "papers")
        ROWS = ((WORKTOP, SHELF_H[0] - BRD - WORKTOP),
                (SHELF_H[0], SHELF_H[1] - BRD - SHELF_H[0]),
                (SHELF_H[1], SHELF_H[2] - BRD - SHELF_H[1]),
                (SHELF_H[2], CROWN - BRD - SHELF_H[2]))


        def fill_run(edges, rmid, dep, skip=()):
            for row, (base, clear) in enumerate(ROWS):
                for bay in range(len(edges) - 1):
                    if (row, bay) in skip:
                        continue
                    kind = rnd.choice(LOW_MIX if clear < 0.16 else MIX)
                    KINDS[kind](edges[bay] + D(0.8), edges[bay + 1] - D(0.8),
                                F + base, clear, rmid, dep)


        fill_run(BAY_A, R - 0.165, 0.078, skip=((0, 2),))     # worktop centre stays clear
        for edges in PIER_A:
            fill_run(edges, R - 0.232, 0.072)

        # worktop dressing in the bay left free: a mortar, loose papers, a desk lamp
        mid = (SA0 + SA1) / 2
        rev_at(sput("graphite"), *shelf_xy(mid - D(3.5), R - 0.165), [
            (0.0, F + WORKTOP), (0.038, F + WORKTOP), (0.045, F + WORKTOP + 0.038),
            (0.033, F + WORKTOP + 0.040), (0.027, F + WORKTOP + 0.014), (0.0, F + WORKTOP + 0.014)], seg=10)
        for k in range(3):
            box(sput("paperWhite"), (*shelf_xy(mid + D(1.6 + k * 0.5), R - 0.168),
                F + WORKTOP + 0.005 + k * 0.008), (0.070, 0.052, 0.007), mid + D(k * 3))
        lamp_a = mid + D(4.6)
        box(sput("mcWood"), (*shelf_xy(lamp_a, R - 0.168), F + WORKTOP + 0.007), (0.058, 0.058, 0.014), lamp_a)
        box(sput("mcWood"), (*shelf_xy(lamp_a, R - 0.168), F + WORKTOP + 0.068), (0.015, 0.015, 0.108), lamp_a)
        box(sput("lampWarm"), (*shelf_xy(lamp_a, R - 0.168), F + WORKTOP + 0.142), (0.050, 0.050, 0.038), lamp_a)

        # a lantern hung from the arch, in front of the shelf face
        hang_a = mid
        box(sput("mcWood"), (*shelf_xy(hang_a, R - 0.34), F + 1.442), (0.013, 0.013, 0.155), hang_a)
        box(sput("lampWarm"), (*shelf_xy(hang_a, R - 0.34), F + 1.302), (0.062, 0.062, 0.082), hang_a)
        box(sput("mcWood"), (*shelf_xy(hang_a, R - 0.34), F + 1.348), (0.076, 0.076, 0.015), hang_a)
        box(sput("mcWood"), (*shelf_xy(hang_a, R - 0.34), F + 1.253), (0.076, 0.076, 0.015), hang_a)

        for key in sorted(SHELF_BM):
            finish(f"deck_shelf_{key}", SHELF_BM[key], key)

    # --------------------------------------------------------------- 9. plants
    bm = bmesh.new()
    PLANTS = [(D(124), R - 0.40), (D(350), R - 0.40), (D(44), R - 1.05)]
    for a, r in PLANTS:
        cx, cy, _ = polar(a, r, 0)
        sub = bmesh.new()
        revolve(sub, [(0.0, F + 0.016), (0.112, F + 0.016), (0.092, F + 0.175), (0.0, F + 0.175)], seg=12)
        for v in sub.verts:
            v.co.x += cx; v.co.y += cy
        verts = [bm.verts.new(v.co) for v in sub.verts]
        for f in sub.faces:
            try:
                bm.faces.new([verts[v.index] for v in f.verts])
            except ValueError:
                pass
        sub.free()
    finish("deck_pots", bm, "rock")

    bm = bmesh.new()
    for a, r in PLANTS:
        cx, cy, _ = polar(a, r, 0)
        for k in range(7):
            b = TAU * k / 7 + a
            lean = 0.155
            px = cx + math.cos(b) * lean
            py = cy + math.sin(b) * lean
            box(bm, (px, py, F + 0.305), (0.30, 0.042, 0.030), b)
            box(bm, (cx + math.cos(b) * 0.14, cy + math.sin(b) * 0.10, F + 0.385), (0.165, 0.038, 0.030), b)
    finish("deck_fronds", bm, "mcLeaves")


    # ------------------------------------------------------- 9b. pillar veins
    # One connected path per vein, seated on the exposed stone faces and ledges.
    import runpy
    from pathlib import Path
    vein_path = Path(bpy.path.abspath("//pillar_veins.py"))
    if not vein_path.exists():
        vein_path = Path(__file__).resolve().with_name("pillar_veins.py")
    vein_module = runpy.run_path(str(vein_path), run_name="pillar_veins_module")
    vein_module["build_pillar_veins"](host, coll, suffix, TAU / 30 if suffix else 0)

    # ------------------------------------------------------------- 10. lighting
    def light(name, kind, pos, energy, color, radius=0.08, size=1.0, rot=(0, 0, 0)):
        name += suffix
        d = bpy.data.lights.new(name, kind)
        d.energy = energy
        d.color = color
        if kind == 'POINT':
            d.shadow_soft_size = radius
        elif kind == 'AREA':
            d.size = size
        ob = bpy.data.objects.new(name, d)
        ob.location = (CX + pos[0], CY + pos[1], pos[2])
        ob.rotation_euler = rot
        coll.objects.link(ob)
        return ob


    BLUE = (0.30, 0.62, 1.0)
    WARM = (1.0, 0.60, 0.28)
    VIOLET = (0.62, 0.30, 1.0)

    # Everything at deck level is soft and wide. A tight point light sitting a
    # few centimetres above the paving blows a white pool into it; these sit
    # higher, with big shadow radii, so the floor reads as lit rather than hit.
    light("deckLight_core", 'POINT', (0, 0, F + 0.42), 26, BLUE, radius=0.60)
    light("deckLight_core_up", 'POINT', (0, 0, F + 1.90), 30, BLUE, radius=0.70)
    for i, a in enumerate([D(30 + 60 * k) for k in range(6)]):
        light(f"deckLight_rune_{i}", 'POINT', ((R - 0.74) * math.cos(a), (R - 0.74) * math.sin(a), F + 0.24), 2.4, BLUE, radius=0.34)
    for i, (a, top) in enumerate(LANTERNS):
        light(f"deckLight_lantern_{i}", 'POINT',
              (POST_R * math.cos(a), POST_R * math.sin(a), F + top + 0.080),
              7.0, WARM, radius=0.12)
    for i, a in enumerate(BRAZIERS):
        light(f"deckLight_brazier_{i}", 'POINT', ((R - 0.42) * math.cos(a), (R - 0.42) * math.sin(a), F + 0.38), 3.0, VIOLET, radius=0.18)
    light("deckLight_crystal", 'POINT', ((R - 0.12) * math.cos(CRY), (R - 0.12) * math.sin(CRY), F + 1.96), 16, VIOLET, radius=0.16)

    # wall wash: an area light in front of the niche pointing out across the deck
    wa = D(56)
    light("deckLight_wall", 'AREA', ((R - 0.62) * math.cos(wa), (R - 0.62) * math.sin(wa), F + 1.95), 26, BLUE,
          size=2.2, rot=(D(120), 0, wa + math.pi / 2))
    # cool key from high front-left so the silhouette reads against the dark
    light("deckLight_key", 'AREA', (-2.6, -5.2, F + 6.0), 48, (0.55, 0.70, 1.0),
          size=7.0, rot=(D(38), 0, D(-27)))
    # warm wash inside the shelf niche - the warm/cool contrast of the reference
    # a lamp inside the alcove, not a spotlight on it - falloff keeps the back
    # board from out-shining the rune circle
    if back_kind == "library":
        for i, sh in enumerate((0.95, 1.38)):
            light(f"deckLight_niche_{i}", 'POINT',
                  ((R - 0.32) * math.cos(wa), (R - 0.32) * math.sin(wa), F + sh),
                  3.0, (1.0, 0.58, 0.28), radius=0.16)
    if back_kind == "workstation":
        for i, da in enumerate((-D(19), D(19))):
            light(f"deckLight_desk_{i}", 'POINT',
                  ((R - 0.62) * math.cos(wa + da), (R - 0.62) * math.sin(wa + da), F + 0.90),
                  2.4, (0.42, 0.60, 1.0), radius=0.16)
        light("deckLight_rail", 'POINT',
              ((R - 0.30) * math.cos(wa), (R - 0.30) * math.sin(wa), F + 1.20), 5, BLUE, radius=0.12)
        for i, ca in enumerate((D(12.0), D(100.0))):
            light(f"deckLight_side_{i}", 'POINT',
                  (1.45 * math.cos(ca), 1.45 * math.sin(ca), F + 1.15),
                  3.0, (0.42, 0.60, 1.0), radius=0.16)
        for i, sa in enumerate((D(23), D(89))):
            light(f"deckLight_speaker_{i}", 'POINT',
                  ((R - 0.74) * math.cos(sa), (R - 0.74) * math.sin(sa), F + 0.26),
                  1.4, BLUE, radius=0.12)

    # soft cool fill straight down so the paving reads instead of going black
    light("deckLight_fill", 'AREA', (0, -0.2, F + 4.2), 78, (0.34, 0.55, 1.0), size=4.6, rot=(0, 0, 0))
    # The shaft below the deck: the old blanket emission used to light it, so it
    # needs a proper rig. Key down the camera side, rims on both back edges to cut
    # the silhouette out of the black, and an uplight under the tip.
    SHAFT_AZ = D(238)                       # camera side
    for i, (dz, e, sz) in enumerate(((-0.9, 60, 5.0), (-3.2, 58, 6.5), (-5.8, 68, 7.0))):
        light(f"deckLight_shaft_{i}", 'AREA',
              (5.0 * math.cos(SHAFT_AZ), 5.0 * math.sin(SHAFT_AZ), F + dz), e, (0.34, 0.50, 0.88),
              size=sz, rot=(D(78), 0, SHAFT_AZ + math.pi / 2))
    for j, raz in enumerate((D(112), D(8))):
        light(f"deckLight_shaft_rim_{j}", 'AREA',
              (5.4 * math.cos(raz), 5.4 * math.sin(raz), F - 3.2), 44, (0.38, 0.44, 0.98),
              size=5.5, rot=(D(80), 0, raz + math.pi / 2))
    # uplight under the tip, so the island reads as floating
    light("deckLight_shaft_under", 'AREA', (0, 0, -1.0), 180, (0.42, 0.34, 0.95),
          size=6.0, rot=(math.pi, 0, 0))
    # dim violet rim from behind
    light("deckLight_rim", 'AREA', (2.4, 5.0, F + 3.4), 20, (0.45, 0.35, 0.95),
          size=5.0, rot=(D(-52), 0, D(-24)))


    # ----------------------------------------------------------------- camera
    cam = bpy.data.objects.get(f"deck_cam{suffix}")
    if cam is None:
        cd = bpy.data.cameras.new(f"deck_cam{suffix}")
        cam = bpy.data.objects.new(f"deck_cam{suffix}", cd)
        coll.objects.link(cam)
    elif cam.name not in coll.objects:
        coll.objects.link(cam)
    cam.data.lens = 55
    az, dist, height = D(238), 13.2, 11.7
    cam.location = (CX + dist * math.cos(az), CY + dist * math.sin(az), F + height)
    target = Vector((CX, CY, F + 0.22))
    dvec = target - cam.location
    cam.rotation_euler = dvec.to_track_quat('-Z', 'Y').to_euler()

    full = bpy.data.objects.get(f"deck_cam_full{suffix}")
    if full is None:
        fd = bpy.data.cameras.new(f"deck_cam_full{suffix}")
        full = bpy.data.objects.new(f"deck_cam_full{suffix}", fd)
        coll.objects.link(full)
    elif full.name not in coll.objects:
        coll.objects.link(full)
    full.data.lens = 50
    full.location = (CX + 17.0 * math.cos(az), CY + 17.0 * math.sin(az), F + 6.0)
    fvec = Vector((CX, CY, F - 3.4)) - full.location
    full.rotation_euler = fvec.to_track_quat('-Z', 'Y').to_euler()

    bpy.context.view_layer.update()
    return {
            "objects": sorted(o.name for o in coll.objects),
            "tris": sum(len(o.data.polygons) for o in coll.objects if o.type == 'MESH'),
            "floor_level": F, "radius": R,
        }


# ------------------------------------------------------- build the islands
def clone_pillar(src, name, loc, rot_z):
    """A second rock pillar sharing the original's material, yawed a little so
    the masonry and veins don't read as a copy."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = src.copy()
        ob.data = src.data.copy()
        ob.name = name
        ob.data.name = name
        bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (0.0, 0.0, rot_z)
    ob.scale = src.scale
    return ob


BASE = bpy.data.objects["island_pillar_huge"]
WORKSHOP = clone_pillar(BASE, "island_pillar_workshop", (20.0, 0.0, 0.0), D(37))

result = build_deck(BASE, "deck_huge", "library", "")
result_b = build_deck(WORKSHOP, "deck_workshop", "workstation", "_b")
result["workshop"] = {"objects": len(result_b["objects"]), "tris": result_b["tris"]}

# a camera framing both islands together
_pcam = bpy.data.objects.get("deck_cam_pair")
if _pcam is None:
    _pcam = bpy.data.objects.new("deck_cam_pair", bpy.data.cameras.new("deck_cam_pair"))
    bpy.context.scene.collection.objects.link(_pcam)
_pcam.data.lens = 52
_mid = (BASE.location + WORKSHOP.location) / 2.0
_F = result["floor_level"]
_az = D(250)
_pcam.location = (_mid.x + 24.0 * math.cos(_az), _mid.y + 24.0 * math.sin(_az), _F + 11.0)
_pcam.rotation_euler = (Vector((_mid.x, _mid.y, _F - 1.2)) - _pcam.location
                        ).to_track_quat('-Z', 'Y').to_euler()


# ------------------------------------------------------------- 11. bloom
NG = "deck_bloom"
ng = bpy.data.node_groups.get(NG)
if ng is None:
    ng = bpy.data.node_groups.new(NG, "CompositorNodeTree")
ng.nodes.clear()
for item in list(ng.interface.items_tree):
    ng.interface.remove(item)
ng.interface.new_socket("Image", in_out='INPUT', socket_type='NodeSocketColor')
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
gin = ng.nodes.new("NodeGroupInput"); gin.location = (-400, 0)
gout = ng.nodes.new("NodeGroupOutput"); gout.location = (400, 0)
glare = ng.nodes.new("CompositorNodeGlare"); glare.location = (0, 0)
# Blender 5 exposes the glare settings as menu/value sockets, older ones as enums
def _glare_set(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value
    elif hasattr(node, key):
        setattr(node, key, value)

_glare_set(glare, "Type", "Bloom")
_glare_set(glare, "Quality", "High")
# Threshold is in scene-linear radiance, so it has to sit under the peak of
# anything meant to bloom - runeGlow reaches 4.2 in blue - but above the lit
# paving, or the whole floor hazes over. Size is the one that decides whether
# this reads as bloom at all: it is a fraction of the frame, so large values
# smear everything into flat fog. Keep it small enough that the glow hugs the
# thing emitting it.
_glare_set(glare, "Threshold", 0.55)
_glare_set(glare, "Smoothness", 0.45)
_glare_set(glare, "Strength", 0.95)
_glare_set(glare, "Size", 0.25)
rl = ng.nodes.new("CompositorNodeRLayers")
rl.location = (-400, -250)
rl.scene = bpy.context.scene
ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
ng.links.new(glare.outputs[0], gout.inputs[0])
bpy.context.scene.compositing_node_group = ng
result["bloom"] = [(n.type, n.name) for n in ng.nodes]


# ------------------------------------------- 12. pillar edge-glow retune
# The pillars drive Emission Color straight from a 256px `edge_lut` at
# strength 8. That LUT is ~0.35 across most of its area and near-white where
# the cracks are, so the whole rock emitted and the cracks blew out to white.
# Rewire it: take the LUT as a mask, threshold it so only the crack pixels
# survive, and drive Emission Strength with that while the colour stays the
# same neon blue as the deck inlays.
GLOW_TINT = (0.06, 0.55, 1.0)
GLOW_STRENGTH = 0.0        # veins are real geometry now; raise this to
                           # bring the LUT's fine speckle back alongside them
GLOW_LO, GLOW_HI = 0.28, 0.60        # LUT luminance window kept as "a crack"


def retune_edge_glow(m):
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None)
    if not (bsdf and tex):
        return False
    for n in [n for n in nt.nodes if n.name.startswith("glow_")]:
        nt.nodes.remove(n)
    for l in list(nt.links):
        if l.to_node == bsdf and l.to_socket.name in ("Emission Color", "Emission Strength"):
            nt.links.remove(l)

    bw = nt.nodes.new("ShaderNodeRGBToBW")
    bw.name = bw.label = "glow_mask"
    bw.location = (tex.location.x + 200, tex.location.y - 180)
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.name = rng.label = "glow_threshold"
    rng.clamp = True
    rng.location = (bw.location.x + 180, bw.location.y)
    rng.inputs["From Min"].default_value = GLOW_LO
    rng.inputs["From Max"].default_value = GLOW_HI
    rng.inputs["To Min"].default_value = 0.0
    rng.inputs["To Max"].default_value = 1.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.name = mul.label = "glow_strength"
    mul.operation = 'MULTIPLY'
    mul.location = (rng.location.x + 180, rng.location.y)
    mul.inputs[1].default_value = GLOW_STRENGTH

    nt.links.new(tex.outputs["Color"], bw.inputs["Color"])
    nt.links.new(bw.outputs["Val"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], mul.inputs[0])
    nt.links.new(mul.outputs["Value"], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (*GLOW_TINT, 1)
    return True


result["edge_glow"] = sorted(m.name for m in bpy.data.materials
                             if m.name.startswith("dark_slate_edges")
                             and m.use_nodes and retune_edge_glow(m))
