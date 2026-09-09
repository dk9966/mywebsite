"""Live spec sliders for the island pillars.

Adds a "Pillars" tab to the 3D View sidebar (N key).

Size sliders (width / height / yaw) drive the object transform. Profile sliders
reshape the mesh itself, using the same radial maths as
meshes/pillars/island_pillar_src/build_pillar.py:

    fill  ->  m = 1 + fill  * (1 - |2t-1| ** fill_power)      fat waist, ends pinned
    flare ->  m = 1 + flare * (     |2t-1| ** flare_power)     fat ends, waist pinned

where t is normalised height. Each pillar keeps a pristine copy of its
un-deformed vertices in a mesh attribute, so the sliders are absolute rather
than cumulative and survive save / reload.

Run from the Text Editor (Alt+P), or tick Register so it loads with the file.
"""

bl_info = {
    "name": "Island Pillar Specs",
    "author": "secret-base",
    "version": (2, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Pillars",
    "description": "Live size and profile controls for the island pillars",
    "category": "Object",
}

import bpy
import numpy as np

PREFIX = "islandPillar"
BASE_ATTR = "pillar_base_co"
TPL_PREFIX = "pillarTpl_"

ISLAND = {
    "islandPillar": "projects (central)",
    "islandPillar.001": "about",
    "islandPillar.002": "workshop",
    "islandPillar.003": "experiences",
    "islandPillar.004": "contact",
    "islandPillar.005": "garage",
}
SUFFIX = {
    "islandPillar": "_projects", "islandPillar.001": "_about",
    "islandPillar.002": "_workshop", "islandPillar.003": "_experiences",
    "islandPillar.004": "_contact", "islandPillar.005": "_garage",
}

_guard = False
_dims = {}
_enum_cache = []


# ----------------------------------------------------------------- helpers
def pillars(scene):
    return [o for o in scene.objects if o.type == 'MESH' and o.name.startswith(PREFIX)]


def templates():
    return sorted([m for m in bpy.data.meshes if m.name.startswith(TPL_PREFIX)],
                  key=lambda m: np.ptp(base_co(m)[:, 2]))


def base_co(me):
    """Pristine local coordinates, stored on the mesh so they persist."""
    a = me.attributes.get(BASE_ATTR)
    n = len(me.vertices)
    if a is None:
        buf = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        a = me.attributes.new(BASE_ATTR, 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set("vector", buf)
    buf = np.empty(n * 3, dtype=np.float32)
    a.data.foreach_get("vector", buf)
    return buf.reshape(n, 3)


def native(me):
    key = (me.name, me.get("_shape_rev", 0), len(me.vertices))
    d = _dims.get(key)
    if d is None:
        buf = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        co = buf.reshape(-1, 3)
        d = tuple((co.max(axis=0) - co.min(axis=0)).tolist())
        _dims[key] = d
    return d


def variant_items(self, context):
    _enum_cache.clear()
    labels = ["Small", "Mid", "Large", "XL", "XXL", "XXXL"]
    for i, me in enumerate(templates()):
        co = base_co(me)
        w = float(np.hypot(co[:, 0], co[:, 1]).max() * 2.0)
        h = float(np.ptp(co[:, 2]))
        nm = labels[i] if i < len(labels) else me.name
        _enum_cache.append((me.name, "%s  (%.2f x %.1f)" % (nm, w, h), me.name))
    if not _enum_cache:
        _enum_cache.append(("NONE", "none", ""))
    return _enum_cache


def band_max(r, t, lo, hi):
    m = (t >= lo) & (t <= hi)
    return float(r[m].max()) if m.any() else 0.0


# ----------------------------------------------------------------- core
def reshape(obj):
    """Rebuild the mesh from its pristine base using the profile sliders."""
    global _guard
    if _guard or not obj.data:
        return
    me = obj.data
    co = base_co(me).copy()
    z = co[:, 2]
    span = z.max() - z.min()
    if span <= 0:
        return
    t = (z - z.min()) / span
    u = np.abs(2.0 * t - 1.0)

    r0 = np.hypot(co[:, 0], co[:, 1])
    base_plinth = band_max(r0, t, 0.0, 0.06)
    base_waist = band_max(r0, t, 0.42, 0.58)

    # waist/plinth target -> the fill the pipeline would need
    fill = 0.0
    if base_waist > 1e-9 and base_plinth > 1e-9:
        fill = (obj.pillar_waist_ratio * base_plinth) / base_waist - 1.0
        fill = max(-0.95, fill)

    m = 1.0 + fill * (1.0 - u ** obj.pillar_waist_falloff)
    rmax_prefill = float((r0 * m).max())
    if obj.pillar_end_flare:
        m = m * (1.0 + obj.pillar_end_flare * (u ** obj.pillar_flare_falloff))
        if obj.pillar_flare_renorm:
            rmax_now = float((r0 * m).max())
            if rmax_now > 1e-9:
                m = m * (rmax_prefill / rmax_now)
    if obj.pillar_taper:
        m = m * (1.0 + obj.pillar_taper * (2.0 * t - 1.0))

    co[:, 0] *= m
    co[:, 1] *= m
    me.vertices.foreach_set("co", co.reshape(-1))
    me["_shape_rev"] = me.get("_shape_rev", 0) + 1
    me.update()
    # resize first: the readouts below convert to metres using the new scale
    apply_size(obj)

    # readouts, measured on the reshaped mesh
    r = np.hypot(co[:, 0], co[:, 1])
    plinth = band_max(r, t, 0.0, 0.06)
    waist = band_max(r, t, 0.42, 0.58)
    top = band_max(r, t, 0.94, 1.0)
    lower = band_max(r, t, 0.30, 0.38)
    upper = band_max(r, t, 0.62, 0.70)
    scale = obj.scale.x
    obj["stat_fill"] = round(fill, 4)
    obj["stat_plinth"] = round(plinth * 2 * scale, 3)
    obj["stat_waist"] = round(waist * 2 * scale, 3)
    obj["stat_top"] = round(top * 2 * scale, 3)
    obj["stat_ratio"] = round(waist / plinth, 4) if plinth > 1e-9 else 0.0
    obj["stat_top_ratio"] = round(top / plinth, 4) if plinth > 1e-9 else 0.0
    obj["stat_bulge"] = round((waist - min(lower, upper)) * 2 * scale, 4)


def apply_size(obj):
    global _guard
    if _guard or not obj.data:
        return
    nw, _, nh = native(obj.data)
    if nw <= 0.0 or nh <= 0.0:
        return
    _guard = True
    try:
        s = obj.pillar_width / nw
        obj.scale = (s, s, obj.pillar_height / nh)
        obj.rotation_euler.z = obj.pillar_yaw
        if obj.pillar_pin_top:
            obj.location.z = obj.pillar_top_z - obj.pillar_height
        else:
            obj.pillar_top_z = obj.location.z + obj.pillar_height
    finally:
        _guard = False


def _upd_size(self, context):
    apply_size(self)


def _upd_shape(self, context):
    reshape(self)


def _upd_variant(self, context):
    global _guard
    tpl = bpy.data.meshes.get(self.pillar_variant)
    if not tpl or not tpl.name.startswith(TPL_PREFIX):
        return
    if self.data.get("_tpl") == tpl.name:
        return
    _guard = True
    try:
        me = tpl.copy()
        me.name = "pillarMesh%s" % SUFFIX.get(self.name, "_" + self.name)
        me["_tpl"] = tpl.name
        me.use_fake_user = False
        old = self.data
        self.data = me
        if old.users == 0 and not old.name.startswith(TPL_PREFIX):
            bpy.data.meshes.remove(old)
    finally:
        _guard = False
    reshape(self)


def sync(obj):
    global _guard
    if not obj.data:
        return
    nw, _, nh = native(obj.data)
    _guard = True
    try:
        obj.pillar_width = nw * obj.scale.x
        obj.pillar_height = nh * obj.scale.z
        obj.pillar_yaw = obj.rotation_euler.z
        obj.pillar_top_z = obj.location.z + nh * obj.scale.z
        tpl = obj.data.get("_tpl")
        if tpl and obj.pillar_variant != tpl:
            obj.pillar_variant = tpl
    finally:
        _guard = False


def setup(scene):
    """Give every pillar its own mesh and keep the three source meshes as templates."""
    made = []
    for o in pillars(scene):
        me = o.data
        if me.get("_tpl") is not None:
            base_co(me)
            continue
        # this object still points at a shared/source mesh: promote it to a
        # template and hand the object its own copy to deform
        tpl = me
        if not tpl.name.startswith(TPL_PREFIX):
            tpl.name = TPL_PREFIX + tpl.name.replace("island_pillar", "v").replace(".", "_")
        tpl.use_fake_user = True
        base_co(tpl)
        copy = tpl.copy()
        copy.name = "pillarMesh%s" % SUFFIX.get(o.name, "_" + o.name)
        copy["_tpl"] = tpl.name
        copy.use_fake_user = False
        o.data = copy
        base_co(copy)
        made.append((o.name, tpl.name, copy.name))

    # canonical template names, ordered by height
    tpls = sorted([m for m in bpy.data.meshes if m.name.startswith(TPL_PREFIX)],
                  key=lambda m: np.ptp(base_co(m)[:, 2]))
    canon = ["pillarTpl_small", "pillarTpl_mid", "pillarTpl_large", "pillarTpl_xl"]
    for i, m in enumerate(tpls):
        want = canon[i] if i < len(canon) else m.name
        if m.name != want and want not in bpy.data.meshes:
            was = m.name
            m.name = want
            for o in pillars(scene):
                if o.data.get("_tpl") == was:
                    o.data["_tpl"] = want
    return made


# ----------------------------------------------------------------- operators
class PILLAR_OT_sync(bpy.types.Operator):
    bl_idname = "pillar.sync"
    bl_label = "Sync"
    bl_description = "Read current object transforms back into the sliders"

    def execute(self, context):
        for o in pillars(context.scene):
            sync(o)
        return {'FINISHED'}


class PILLAR_OT_reset_profile(bpy.types.Operator):
    bl_idname = "pillar.reset_profile"
    bl_label = "Reset Profile"
    bl_description = "Return every pillar's profile to its as-built shape"

    def execute(self, context):
        for o in pillars(context.scene):
            co = base_co(o.data)
            t = (co[:, 2] - co[:, 2].min()) / max(1e-12, np.ptp(co[:, 2]))
            r = np.hypot(co[:, 0], co[:, 1])
            p, w = band_max(r, t, 0.0, 0.06), band_max(r, t, 0.42, 0.58)
            o.pillar_end_flare = 0.0
            o.pillar_taper = 0.0
            o.pillar_waist_ratio = (w / p) if p > 1e-9 else 0.6
        return {'FINISHED'}


class PILLAR_OT_copy_variants(bpy.types.Operator):
    bl_idname = "pillar.copy_variants"
    bl_label = "Copy VARIANTS Block"
    bl_description = "Copy a config.py VARIANTS block matching the sliders to the clipboard"

    def execute(self, context):
        tpls = templates()
        if not tpls:
            self.report({'ERROR'}, "no pillar templates found")
            return {'CANCELLED'}
        co = base_co(tpls[0])
        bw = float(np.hypot(co[:, 0], co[:, 1]).max() * 2.0)
        bh = float(np.ptp(co[:, 2]))
        lines, tapered = ["VARIANTS = ["], []
        for o in sorted(pillars(context.scene), key=lambda o: o.name):
            parts = ["suffix='%s'" % SUFFIX.get(o.name, "_" + o.name.replace(".", "_")),
                     "width=%.3f" % (o.pillar_width / bw),
                     "height=%.3f" % (o.pillar_height / bh)]
            fill = float(o.get("stat_fill", 0.0))
            if abs(fill) > 1e-4:
                parts += ["fill=%.3f" % fill, "fill_power=%.2f" % o.pillar_waist_falloff]
            if o.pillar_end_flare > 1e-4:
                parts += ["flare=%.3f" % o.pillar_end_flare,
                          "flare_power=%.2f" % o.pillar_flare_falloff]
            lines.append("    dict(%s)," % ", ".join(parts))
            if abs(o.pillar_taper) > 1e-4:
                tapered.append(o.name)
        lines.append("]")
        block = "\n".join(lines)
        if tapered:
            block += ("\n# NOTE: taper is a viewport-only control with no config.py\n"
                      "# equivalent; ignored above for: %s" % ", ".join(tapered))
        context.window_manager.clipboard = block
        print(block)
        self.report({'INFO'}, "VARIANTS block copied to clipboard")
        return {'FINISHED'}


# ----------------------------------------------------------------- panel
class PILLAR_PT_specs(bpy.types.Panel):
    bl_label = "Pillar Specs"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pillars"

    def draw(self, context):
        layout = self.layout
        objs = sorted(pillars(context.scene), key=lambda o: o.name)
        if not objs:
            layout.label(text="No islandPillar objects in scene", icon='ERROR')
            return
        row = layout.row(align=True)
        row.operator("pillar.sync", icon='FILE_REFRESH')
        row.operator("pillar.reset_profile", icon='LOOP_BACK')
        layout.operator("pillar.copy_variants", icon='COPYDOWN')

        for o in objs:
            box = layout.box()
            head = box.row(align=True)
            head.prop(o, "pillar_show", text="", emboss=False,
                      icon='DISCLOSURE_TRI_DOWN' if o.pillar_show else 'DISCLOSURE_TRI_RIGHT')
            head.label(text="%s   %.1f x %.1f   waist %.2f"
                       % (ISLAND.get(o.name, o.name), o.pillar_width, o.pillar_height,
                          o.get("stat_ratio", 0.0)))
            head.prop(o, "pillar_pin_top", text="",
                      icon='PINNED' if o.pillar_pin_top else 'UNPINNED')
            if not o.pillar_show:
                continue

            col = box.column(align=True)
            col.label(text="Size")
            col.prop(o, "pillar_width")
            col.prop(o, "pillar_height")
            col.prop(o, "pillar_yaw")
            box.prop(o, "pillar_variant", text="Variant")

            col = box.column(align=True)
            col.label(text="Profile")
            col.prop(o, "pillar_waist_ratio", slider=True)
            col.prop(o, "pillar_waist_falloff", slider=True)
            col.separator()
            col.prop(o, "pillar_end_flare", slider=True)
            col.prop(o, "pillar_flare_falloff", slider=True)
            col.prop(o, "pillar_flare_renorm")
            col.separator()
            col.prop(o, "pillar_taper", slider=True)

            grid = box.column(align=True)
            grid.label(text="Measured (metres)")
            grid.label(text="plinth %.2f    waist %.2f    top %.2f"
                       % (o.get("stat_plinth", 0.0), o.get("stat_waist", 0.0),
                          o.get("stat_top", 0.0)))
            grid.label(text="waist/plinth %.2f    top/plinth %.2f"
                       % (o.get("stat_ratio", 0.0), o.get("stat_top_ratio", 0.0)))
            r = grid.row()
            r.alert = o.get("stat_bulge", 0.0) > 0.0
            r.label(text="mid bulge %+.3f    fill %+.3f"
                    % (o.get("stat_bulge", 0.0), o.get("stat_fill", 0.0)))


CLASSES = (PILLAR_OT_sync, PILLAR_OT_reset_profile, PILLAR_OT_copy_variants, PILLAR_PT_specs)

PROPS = ("pillar_width", "pillar_height", "pillar_yaw", "pillar_pin_top", "pillar_top_z",
         "pillar_variant", "pillar_show", "pillar_waist_ratio", "pillar_waist_falloff",
         "pillar_end_flare", "pillar_flare_falloff", "pillar_flare_renorm", "pillar_taper")


def register():
    unregister()
    for c in CLASSES:
        bpy.utils.register_class(c)
    O = bpy.types.Object
    P = bpy.props
    O.pillar_width = P.FloatProperty(name="Width", description="Widest diameter, metres",
                                     default=5.0, min=0.1, soft_max=25.0, unit='LENGTH',
                                     update=_upd_size)
    O.pillar_height = P.FloatProperty(name="Height", description="Base to top, metres",
                                      default=20.0, min=0.5, soft_max=45.0, unit='LENGTH',
                                      update=_upd_size)
    O.pillar_yaw = P.FloatProperty(name="Yaw", default=0.0, subtype='ANGLE',
                                   unit='ROTATION', update=_upd_size)
    O.pillar_pin_top = P.BoolProperty(name="Pin Top", default=True,
                                      description="Hold the top face at a fixed height",
                                      update=_upd_size)
    O.pillar_top_z = P.FloatProperty(name="Top Z", default=0.0)
    O.pillar_variant = P.EnumProperty(name="Variant", items=variant_items, update=_upd_variant)
    O.pillar_show = P.BoolProperty(name="Expand", default=False)
    O.pillar_waist_ratio = P.FloatProperty(
        name="Waist / Plinth", description="How wide the middle is relative to the base",
        default=0.60, min=0.20, max=1.30, update=_upd_shape)
    O.pillar_waist_falloff = P.FloatProperty(
        name="Waist Falloff", description="Higher spreads the widening further toward the ends",
        default=2.0, min=1.0, max=4.0, update=_upd_shape)
    O.pillar_end_flare = P.FloatProperty(
        name="End Flare", description="Push top and bottom outward, deepening the hourglass",
        default=0.0, min=0.0, max=1.5, update=_upd_shape)
    O.pillar_flare_falloff = P.FloatProperty(
        name="Flare Falloff", description="Higher keeps the flare tight to the very ends",
        default=1.7, min=1.0, max=4.0, update=_upd_shape)
    O.pillar_flare_renorm = P.BoolProperty(
        name="Renormalise Flare", default=True,
        description="Rescale after flaring so overall width is unchanged", update=_upd_shape)
    O.pillar_taper = P.FloatProperty(
        name="Taper (top vs base)", description="Positive widens the top, negative widens the base",
        default=0.0, min=-0.6, max=0.6, update=_upd_shape)

    scene = getattr(bpy.context, "scene", None)
    if scene:
        setup(scene)
        for o in pillars(scene):
            sync(o)
            co = base_co(o.data)
            t = (co[:, 2] - co[:, 2].min()) / max(1e-12, np.ptp(co[:, 2]))
            r = np.hypot(co[:, 0], co[:, 1])
            p, w = band_max(r, t, 0.0, 0.06), band_max(r, t, 0.42, 0.58)
            o.pillar_waist_ratio = (w / p) if p > 1e-9 else 0.6


def unregister():
    for c in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    for p in PROPS:
        if hasattr(bpy.types.Object, p):
            try:
                delattr(bpy.types.Object, p)
            except Exception:
                pass


if __name__ == "__main__":
    register()
