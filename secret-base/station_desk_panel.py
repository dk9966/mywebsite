"""Live position slider for the workshop desk.

Adds a "Station" tab to the 3D View sidebar (N key).

build_station.py writes the desk and the machines standing behind it into the
same seven meshes, split by material and by nothing else, so neither one is an
object you can click. This panel splits them by where they are instead. Every
loose part of every deck_desk_*_b mesh is classified once, by whether its
centroid falls in front of or behind u = U_SPLIT on the station's own axis, and
the front group is the desk. The geometry leaves a clean 150 mm gap there - the
desk's back trim ends at u = 1.79 and the nearest machine plinth starts at 1.94
- so no part straddles the line and nothing is torn in half. The two speakers
are the exception: they are toed in at the seat, which brings them forward of
that line and in among the wings, so they are cut out by their own footprint.

The slider then slides that group along u, the same axis U_BACK is measured on.
Each mesh keeps a pristine copy of its vertices in an attribute, so the slider
is absolute rather than cumulative and survives save / reload. The lights and
holo locators that belong to the desk rather than to the machines ride along
while Carry fittings is on.

None of this is permanent: build_station.py rebuilds these meshes from U_BACK
and would wipe it. Write U_BACK puts the slider's value into the script, so
re-running it keeps the move. After that rebuild, press Rescan.

Run from the Text Editor (Alt+P), or tick Register so it loads with the file.
"""

bl_info = {
    "name": "Station Desk Position",
    "author": "secret-base",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Station",
    "description": "Slide the workshop desk without dragging the machines with it",
    "category": "Object",
}

import bpy
import math
import re
import numpy as np
from mathutils import Vector

CA = math.radians(56)                  # the station's centre line, from build_station.py
CC, SS = math.cos(CA), math.sin(CA)

U_SPLIT = 1.87                         # desk in front of this, machines behind it
U_BACK_DEFAULT = 1.76                  # what build_station.py ships with

# The speakers of section 4f stand on the floor with the machines, but they are
# toed in at the seat, which carries them forward of U_SPLIT and in among the
# desk's wings - by u alone they read as desk. They are picked off by distance
# from their own centres instead, which is unambiguous: the furthest speaker
# part sits 0.17 out, the nearest desk part 0.46. These are build_station.py's
# own numbers, so stand() below has to agree with the one over there.
SP_V = 1.50
SP_BW, SP_BD = 0.300 + 0.068, 0.280 + 0.085
SP_U = min(2.56, math.sqrt(2.60 ** 2 - (SP_V + SP_BW / 2) ** 2)) - SP_BD / 2
SP_R = 0.30

DESKS = ("deck_desk_b", "deck_desk_dark_b", "deck_desk_neon_b", "deck_desk_led_b",
         "deck_desk_glass_b", "deck_desk_metal_b", "deck_desk_hud_b")
FITTINGS = ("deckLight_desk_", "holoLocator_")

BASE_ATTR = "station_base_co"
TABLE_ATTR = "station_is_table"
BASE_LOC = "station_base_loc"

SCRIPT = "/Users/danielku/mywebsite/secret-base/build_station.py"

_guard = False


# ----------------------------------------------------------------- helpers
def desks(scene):
    return [scene.objects[n] for n in DESKS if n in scene.objects]


def uv_origin(ob):
    """Where the object's own frame puts the station's (u, v) = 0."""
    t = ob.matrix_world.translation
    return t.x * CC + t.y * SS, -t.x * SS + t.y * CC


def in_edit(scene):
    """Attribute data is empty while a mesh is open in Edit Mode - its
    vertices live in the BMesh until the mode is left."""
    return [o.name for o in desks(scene) if o.mode == 'EDIT']


def base_co(me):
    """Pristine local coordinates, stored on the mesh so they persist."""
    a = me.attributes.get(BASE_ATTR)
    n = len(me.vertices)
    if a is None:
        buf = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        a = me.attributes.new(BASE_ATTR, 'FLOAT_VECTOR', 'POINT')
        # the handle new() hands back can be stale in 5.x - fetch it again
        a = me.attributes[a.name]
        a.data.foreach_set("vector", buf)
    buf = np.empty(n * 3, dtype=np.float32)
    a.data.foreach_get("vector", buf)
    return buf.reshape(n, 3)


def roots(me):
    """Union-find over the edges: which loose part each vertex belongs to."""
    n = len(me.vertices)
    par = np.arange(n)

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    ed = np.empty(len(me.edges) * 2, dtype=np.int32)
    me.edges.foreach_get("vertices", ed)
    for i in range(0, len(ed), 2):
        a, b = find(ed[i]), find(ed[i + 1])
        if a != b:
            par[a] = b
    return np.fromiter((find(i) for i in range(n)), dtype=np.int32, count=n)


def table_mask(ob):
    """True for vertices of the desk, False for the machines behind it.

    Classified per loose part, on the part's centroid - a threshold applied
    vertex by vertex would cut through anything spanning the line. A part is
    desk if it is in front of U_SPLIT and clear of both speakers.
    """
    me = ob.data
    n = len(me.vertices)
    a = me.attributes.get(TABLE_ATTR)
    if a is None or len(a.data) != n:
        if a is not None:
            me.attributes.remove(a)
        co = base_co(me)
        mw = np.array(ob.matrix_world)
        w = co @ mw[:3, :3].T + mw[:3, 3]
        u0, v0 = uv_origin(ob)
        u = w[:, 0] * CC + w[:, 1] * SS - u0
        v = -w[:, 0] * SS + w[:, 1] * CC - v0
        r = roots(me)
        mask = np.zeros(n, dtype=bool)
        for k in np.unique(r):
            sel = r == k
            cu, cv = float(u[sel].mean()), float(v[sel].mean())
            speaker = math.hypot(cu - SP_U, abs(cv) - SP_V) < SP_R
            mask[sel] = cu < U_SPLIT and not speaker
        a = me.attributes.new(TABLE_ATTR, 'BOOLEAN', 'POINT')
        a = me.attributes[a.name]
        a.data.foreach_set("value", mask.tolist())
    buf = np.empty(n, dtype=bool)
    a.data.foreach_get("value", buf)
    return buf


def fittings(scene):
    """Lights and locators that sit over the desk, not over the machines.

    Their untouched world position is stashed on the object the first time we
    see them, so this must first run with the slider at zero.
    """
    out = []
    ref = desks(scene)
    if not ref:
        return out
    o0, _ = uv_origin(ref[0])
    for ob in scene.objects:
        if not any(ob.name.startswith(p) for p in FITTINGS):
            continue
        if BASE_LOC not in ob:
            t = ob.matrix_world.translation
            ob[BASE_LOC] = [t.x, t.y, t.z]
        b = Vector(ob[BASE_LOC])
        if b.x * CC + b.y * SS - o0 < U_SPLIT:
            out.append((ob, b))
    return out


def forget(scene):
    """Drop the pristine coordinates, the split and the fittings' home
    positions. The desk is left wherever it currently sits."""
    for ob in desks(scene):
        for name in (BASE_ATTR, TABLE_ATTR):
            a = ob.data.attributes.get(name)
            if a is not None:
                ob.data.attributes.remove(a)
    for ob in scene.objects:
        if any(ob.name.startswith(p) for p in FITTINGS) and BASE_LOC in ob:
            del ob[BASE_LOC]


def script_u_back(path):
    try:
        with open(path) as f:
            m = re.search(r"^U_BACK = ([0-9.]+)", f.read(), re.M)
        return float(m.group(1)) if m else U_BACK_DEFAULT
    except OSError:
        return U_BACK_DEFAULT


# ------------------------------------------------------------------- apply
def apply_offset(scene):
    global _guard
    if _guard:
        return
    if in_edit(scene):
        return
    off = scene.station_desk_offset
    ax = Vector((CC, SS, 0.0))

    for ob in desks(scene):
        me = ob.data
        co = base_co(me).copy()
        m = table_mask(ob)
        if m.any():
            # the meshes are unrotated and unscaled in world, but do not
            # assume it - convert the axis into the object's own frame
            local = ob.matrix_world.to_3x3().inverted() @ ax
            co[m] += np.array(local, dtype=np.float32) * off
        me.vertices.foreach_set("co", co.reshape(-1))
        me.update()

    carry = off if scene.station_desk_carry else 0.0
    for ob, base in fittings(scene):
        m = ob.matrix_world.copy()
        m.translation = base + ax * carry
        ob.matrix_world = m


def _upd(self, context):
    apply_offset(context.scene)


# --------------------------------------------------------------- operators
class STATION_OT_desk_reset(bpy.types.Operator):
    bl_idname = "station.desk_reset"
    bl_label = "Reset"
    bl_description = "Put the desk back where the mesh was built"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not in_edit(context.scene)

    def execute(self, context):
        context.scene.station_desk_offset = 0.0
        return {'FINISHED'}


class STATION_OT_desk_rescan(bpy.types.Operator):
    bl_idname = "station.desk_rescan"
    bl_label = "Rescan"
    bl_description = ("Forget the stored desk / machine split and the pristine "
                      "coordinates, and read them off the meshes again. Use "
                      "after re-running build_station.py")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not in_edit(context.scene)

    def execute(self, context):
        global _guard
        scene = context.scene
        _guard = True
        scene.station_desk_offset = 0.0
        _guard = False
        forget(scene)
        scene.station_desk_built = script_u_back(scene.station_desk_script)
        n = sum(int(table_mask(o).sum()) for o in desks(scene))
        self.report({'INFO'}, "desk = %d verts across %d meshes, U_BACK = %.3f"
                    % (n, len(desks(scene)), scene.station_desk_built))
        return {'FINISHED'}


class STATION_OT_desk_clear(bpy.types.Operator):
    bl_idname = "station.desk_clear"
    bl_label = "Clear cache"
    bl_description = ("Put the desk back and remove the stored coordinates and "
                      "split from the meshes, leaving the file as the builder "
                      "left it")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not in_edit(context.scene)

    def execute(self, context):
        global _guard
        scene = context.scene
        scene.station_desk_offset = 0.0       # restores before we forget how
        _guard = True
        scene.station_desk_carry = True
        _guard = False
        forget(scene)
        self.report({'INFO'}, "desk restored, stored data removed")
        return {'FINISHED'}


class STATION_OT_desk_write(bpy.types.Operator):
    bl_idname = "station.desk_write"
    bl_label = "Write U_BACK"
    bl_description = ("Put the slider's position into build_station.py so the "
                      "next rebuild keeps it")
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        path = bpy.path.abspath(scene.station_desk_script)
        target = scene.station_desk_built + scene.station_desk_offset
        try:
            with open(path) as f:
                src = f.read()
        except OSError as e:
            self.report({'ERROR'}, "cannot read %s: %s" % (path, e))
            return {'CANCELLED'}

        num = ("%.4f" % target).rstrip("0").rstrip(".")

        def sub(m):
            # keep the comment in its column so the block stays aligned
            pad = max(1, len(m.group(2)) + len(m.group(3)) - len(num))
            return m.group(1) + num + " " * pad + (m.group(4) or "")

        new, count = re.subn(r"^(U_BACK = )([0-9.]+)([ \t]*)(#.*)?$", sub, src,
                             count=1, flags=re.M)
        if not count:
            self.report({'ERROR'}, "no U_BACK assignment found in %s" % path)
            return {'CANCELLED'}
        with open(path, "w") as f:
            f.write(new)
        self.report({'INFO'}, "U_BACK = %s written - re-run build_station.py, "
                              "then Rescan" % num)
        return {'FINISHED'}


# ------------------------------------------------------------------- panel
class STATION_PT_desk(bpy.types.Panel):
    bl_label = "Desk position"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Station"

    def draw(self, context):
        scene = context.scene
        col = self.layout.column()
        if not desks(scene):
            col.label(text="no deck_desk_*_b meshes in this scene", icon='ERROR')
            return

        edit = in_edit(scene)
        if edit:
            col.label(text="leave Edit Mode to use the slider", icon='EDITMODE_HLT')
        sub = col.column()
        sub.enabled = not edit
        col = sub

        col.prop(scene, "station_desk_offset", slider=True)
        col.prop(scene, "station_desk_carry")

        target = scene.station_desk_built + scene.station_desk_offset
        box = col.box().column(align=True)
        box.label(text="U_BACK  %.3f  →  %.3f" % (scene.station_desk_built, target))
        on_disk = script_u_back(bpy.path.abspath(scene.station_desk_script))
        if abs(on_disk - target) > 1e-4:
            box.label(text="script says %.3f" % on_disk, icon='DOT')
        else:
            box.label(text="script matches", icon='CHECKMARK')

        row = col.row(align=True)
        row.operator("station.desk_reset", icon='LOOP_BACK')
        row.operator("station.desk_rescan", icon='FILE_REFRESH')
        row.operator("station.desk_clear", icon='TRASH')
        col.operator("station.desk_write", icon='TEXT')
        col.prop(scene, "station_desk_script", text="")


CLASSES = (STATION_OT_desk_reset, STATION_OT_desk_rescan, STATION_OT_desk_clear,
           STATION_OT_desk_write, STATION_PT_desk)
PROPS = ("station_desk_offset", "station_desk_carry", "station_desk_built",
         "station_desk_script")


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)

    bpy.types.Scene.station_desk_offset = bpy.props.FloatProperty(
        name="Desk offset", unit='LENGTH', default=0.0,
        min=-1.2, max=1.2, soft_min=-0.6, soft_max=0.6, step=1, precision=3,
        description=("Slide the desk along the station's centre line. Positive "
                     "moves it back toward the machines, negative pulls it in "
                     "toward the deck centre and opens the gap"),
        update=_upd)
    bpy.types.Scene.station_desk_carry = bpy.props.BoolProperty(
        name="Carry fittings", default=True,
        description=("Move the desk's own lights and the holo locators with it. "
                     "The machines' plinth lights stay put"),
        update=_upd)
    bpy.types.Scene.station_desk_built = bpy.props.FloatProperty(
        name="Built U_BACK", default=U_BACK_DEFAULT,
        description="The U_BACK the meshes in this file were built with")
    bpy.types.Scene.station_desk_script = bpy.props.StringProperty(
        name="Script", subtype='FILE_PATH', default=SCRIPT,
        description="build_station.py, for Write U_BACK")

    scene = getattr(bpy.context, "scene", None)
    if scene and not in_edit(scene):
        for ob in desks(scene):
            table_mask(ob)
        fittings(scene)


def unregister():
    for c in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    for p in PROPS:
        if hasattr(bpy.types.Scene, p):
            try:
                delattr(bpy.types.Scene, p)
            except Exception:
                pass


if __name__ == "__main__":
    register()
