"""Organic island outlines — a reversible deformation.

Turns the islands' perfect circles into slightly irregular, weathered-rock
outlines, and takes them back again. Nothing is baked in: the deformation is a
pure radial scale keyed on the angle around each island's own axis,

    r' = r * (1 + AMP * wobble(angle))

so it never changes a point's angle or its height. That is what makes it exactly
invertible — dividing by the same factor restores the circle — and what makes it
safe: every vertex at a given angle is scaled by the same amount, so radial gaps
and clearances are preserved. Furniture cannot end up poking through a wall or
hanging off the rim.

Each island gets its own harmonic phases so no two silhouettes repeat. Pillars
also get a slow twist up the shaft that fades to nothing at the top, so a pillar
still lines up with the deck sitting on it.

Usage, from Blender's Python console:

    ns = {}
    exec(open("/Users/danielku/mywebsite/secret-base/organic_islands.py").read(), ns)
    ns["set_organic"](True)     # deform
    ns["set_organic"](False)    # back to round circles

The current state is remembered on the scene (`scene["organic_islands"]`), so
calling it twice the same way is a no-op rather than a double deformation.

Note: build_station.py has its own ORGANIC switch. Keep the two in step, or the
console station will be built for a rim shape the deck no longer has.
"""

import bpy
import math
import numpy as np
import mathutils

AMP = 0.13          # peak radial deviation, as a fraction of the nominal radius
TWIST = 0.45        # radians the pillar profile rotates over its height
FLAG = "organic_islands"

# island -> harmonic terms (frequency, phase, weight). Low frequencies only:
# a handful of broad lobes reads as weathered rock, high frequencies read as a gear.
SEEDS = {
    "workshop": [(2, 0.35, 1.00), (3, 2.10, 0.65), (5, 4.40, 0.40)],
    "library":  [(2, 1.90, 1.00), (3, 5.05, 0.65), (5, 0.80, 0.40)],
    "central":  [(2, 3.40, 1.00), (3, 0.60, 0.65), (5, 2.75, 0.40)],
    "large":    [(2, 5.60, 1.00), (3, 3.30, 0.65), (5, 1.15, 0.40)],
}

# object / collection -> (centre x, centre y, seed)
PILLARS = (
    ("island_pillar",          0.0, 0.0, "central"),
    ("island_pillar_large",    5.0, 0.0, "large"),
    ("island_pillar_huge",    12.0, 0.0, "library"),
    ("island_pillar_workshop", 20.0, 0.0, "workshop"),
)
DECKS = (
    ("deck_huge",     12.0, 0.0, "library"),
    ("deck_workshop", 20.0, 0.0, "workshop"),
)


def wobble(seed, ang):
    """Smooth periodic [-1, 1] function of angle. Accepts scalars or arrays."""
    harm = SEEDS[seed]
    norm = sum(w for _, _, w in harm)
    return sum(w * np.sin(k * ang + ph) for k, ph, w in harm) / norm


def factor(seed, ang, on):
    s = 1.0 + AMP * wobble(seed, ang)
    return s if on else 1.0 / s


def _mesh(obj, cx, cy, seed, on, twist=0.0):
    me = obj.data
    n = len(me.vertices)
    if n == 0:
        return
    buf = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", buf)
    co = buf.reshape(n, 3).astype(np.float64)
    M = np.array(obj.matrix_world)
    Rm, T = M[:3, :3], M[:3, 3]
    w = co @ Rm.T + T
    dx, dy = w[:, 0] - cx, w[:, 1] - cy
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    if twist:
        zmin, zmax = w[:, 2].min(), w[:, 2].max()
        t = (w[:, 2] - zmin) / max(zmax - zmin, 1e-9)
        ang = ang + twist * (1.0 - t) ** 1.2      # fades out at the top
    f = factor(seed, ang, on)
    live = r > 1e-6
    w[live, 0] = cx + dx[live] * f[live]
    w[live, 1] = cy + dy[live] * f[live]
    me.vertices.foreach_set("co", ((w - T) @ np.linalg.inv(Rm).T).astype(np.float32).reshape(-1))
    me.update()


def _light(obj, cx, cy, seed, on):
    p = obj.matrix_world.translation
    dx, dy = p.x - cx, p.y - cy
    if math.hypot(dx, dy) < 1e-6:
        return
    f = float(factor(seed, np.array([math.atan2(dy, dx)]), on)[0])
    obj.location = mathutils.Vector((cx + dx * f, cy + dy * f, p.z))


def set_organic(on=True, scene=None):
    """Deform the islands (on=True) or restore perfect circles (on=False)."""
    scene = scene or bpy.context.scene
    if bool(scene.get(FLAG, False)) == bool(on):
        print("organic_islands: already %s" % ("on" if on else "off"))
        return 0
    touched = 0
    for name, cx, cy, seed in PILLARS:
        o = bpy.data.objects.get(name)
        if o and o.type == 'MESH':
            _mesh(o, cx, cy, seed, on, TWIST)
            touched += 1
    for cname, cx, cy, seed in DECKS:
        coll = bpy.data.collections.get(cname)
        if not coll:
            continue
        for o in coll.objects:
            if o.type == 'MESH':
                _mesh(o, cx, cy, seed, on)
                touched += 1
            elif o.type == 'LIGHT':
                _light(o, cx, cy, seed, on)
                touched += 1
    scene[FLAG] = bool(on)
    print("organic_islands: %s, %d objects" % ("applied" if on else "removed", touched))
    return touched


print(__doc__.splitlines()[0])
print("call set_organic(True) to deform, set_organic(False) to go back to circles")
