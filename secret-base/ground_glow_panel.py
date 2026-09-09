"""Live sliders for the deck's glowing ground rings.

Adds a "Ground Glow" tab to the 3D View sidebar (N key).

Colour and Glow drive the `runeGlow` material and take effect immediately.
Thickness and Height reshape the strip meshes. Each ring is a band at a fixed
radius, so Thickness scales every vertex's offset from its own ring's centre
line; Height moves only the strip's top face, since its underside is buried in
the floor slab and never shows. Each rune mesh keeps a pristine copy of its
vertices in a mesh attribute, so both sliders are absolute rather than
cumulative, survive save / reload, and do not clobber each other.

Bloom is two coupled numbers and the panel exposes both. Glow is the honest
per-line control: the compositor's glare only picks up what clears its
threshold, so raising a line's own radiance is what gives *these* lines more
bloom. The Glare box under it drives the scene's Glare node, which blooms
everything in frame - lanterns, desk strip and all - so reach for it only when
you want the whole render hazier.

These sliders change the live scene. build_deck.py holds the values a rebuild
restores, so once you have settled on a look hit "Values for build_deck.py" and
paste the lines back into the script. They land in a text block named
`ground_glow_values` - pick it from the Text Editor's browse dropdown - because
macOS has no Toggle System Console and print() output goes nowhere visible.

Run from the Text Editor (Alt+P), or tick Register so it loads with the file.
"""

bl_info = {
    "name": "Deck Ground Glow",
    "author": "secret-base",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Ground Glow",
    "description": "Live colour, thickness, height and bloom for the deck's ground rings",
    "category": "Object",
}

import bpy
import numpy as np

PREFIX = "deck_runes"
MATERIAL = "runeGlow"
BASE_ATTR = "rune_base_co"
TEXT_BLOCK = "ground_glow_values"
RING_GAP = 0.02         # radii closer together than this belong to one ring

_guard = False


# ----------------------------------------------------------------- helpers
def rune_meshes(scene):
    seen, out = set(), []
    for o in scene.objects:
        if o.type == 'MESH' and o.name.startswith(PREFIX) and o.data.name not in seen:
            seen.add(o.data.name)
            out.append(o.data)
    return out


def glow_mat():
    return bpy.data.materials.get(MATERIAL)


def emission(mat):
    """The Principled node's emission sockets, or None if this isn't one."""
    if not mat or not mat.node_tree:
        return None
    node = mat.node_tree.nodes.get("Principled BSDF")
    if not node:
        return None
    return node.inputs.get("Emission Color"), node.inputs.get("Emission Strength")


def glare_node():
    ng = getattr(bpy.context.scene, "compositing_node_group", None)
    if not ng:
        return None
    for n in ng.nodes:
        if n.type == 'GLARE':
            return n
    return None


def base_co(me):
    """Pristine vertex positions, stashed on first touch so the slider is absolute."""
    a = me.attributes.get(BASE_ATTR)
    if a is None or len(a.data) != len(me.vertices):
        if a is not None:
            me.attributes.remove(a)
        a = me.attributes.new(BASE_ATTR, 'FLOAT_VECTOR', 'POINT')
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        a.data.foreach_set("vector", co)
    out = np.empty(len(me.vertices) * 3, dtype=np.float32)
    a.data.foreach_get("vector", out)
    return out.reshape(-1, 3)


def ring_centres(r):
    """Mean radius of the ring each vertex belongs to.

    A strip is a band from rr - w/2 to rr + w/2 with the same number of verts on
    each edge, so the mean of a ring's radii is its centre line. Rings are set
    at least 0.26 apart by build_deck.py, far wider than any strip, so sorting
    the radii and cutting wherever the gap jumps separates them cleanly.
    """
    order = np.argsort(r)
    rs = r[order]
    cuts = np.nonzero(np.diff(rs) > RING_GAP)[0]
    starts = np.concatenate(([0], cuts + 1))
    ends = np.concatenate((cuts + 1, [len(rs)]))
    mid = np.empty_like(r)
    for s, e in zip(starts, ends):
        idx = order[s:e]
        mid[idx] = r[idx].mean()
    return mid


def apply_shape(me, thickness, lift):
    """Both mesh sliders at once, always from the pristine copy.

    Applying them separately would mean whichever ran last reset the other, so
    they are deliberately one operation.
    """
    co = base_co(me).astype(np.float64).copy()

    r = np.hypot(co[:, 0], co[:, 1])
    mid = ring_centres(r)
    scale = np.where(r > 1e-9, (mid + (r - mid) * thickness) / np.maximum(r, 1e-9), 1.0)
    co[:, 0] *= scale
    co[:, 1] *= scale

    # A strip is a box between exactly two z levels. Only the upper one is ever
    # seen - the lower sits inside the floor slab - so only it moves.
    z = co[:, 2]
    if len(z):
        top = z > (z.min() + z.max()) * 0.5
        co[top, 2] += lift

    me.vertices.foreach_set("co", co.ravel().astype(np.float32))
    me.update()


# ------------------------------------------------------------- slider hooks
def _upd_look(self, context):
    if _guard:
        return
    col, stren = emission(glow_mat()) or (None, None)
    if col:
        col.default_value = (*context.scene.glow_color, 1.0)
    if stren:
        stren.default_value = context.scene.glow_strength


def _upd_shape(self, context):
    if _guard:
        return
    s = context.scene
    for me in rune_meshes(s):
        apply_shape(me, s.glow_thickness, s.glow_height)


def _upd_glare(self, context):
    if _guard:
        return
    n = glare_node()
    if not n:
        return
    for key, val in (("Strength", context.scene.glow_glare_strength),
                     ("Size", context.scene.glow_glare_size),
                     ("Threshold", context.scene.glow_glare_threshold)):
        if key in n.inputs:
            n.inputs[key].default_value = val


def sync(scene):
    """Pull the sliders back from whatever the scene actually holds."""
    global _guard
    _guard = True
    try:
        col, stren = emission(glow_mat()) or (None, None)
        if col:
            scene.glow_color = col.default_value[:3]
        if stren:
            scene.glow_strength = stren.default_value
        n = glare_node()
        if n:
            for key, prop in (("Strength", "glow_glare_strength"),
                              ("Size", "glow_glare_size"),
                              ("Threshold", "glow_glare_threshold")):
                if key in n.inputs:
                    setattr(scene, prop, n.inputs[key].default_value)
    finally:
        _guard = False


# ------------------------------------------------------------------ operators
class GLOW_OT_sync(bpy.types.Operator):
    bl_idname = "deckglow.sync"
    bl_label = "Reload From Scene"
    bl_description = "Read the sliders back from the material and the glare node"

    def execute(self, context):
        sync(context.scene)
        return {'FINISHED'}


class GLOW_OT_reset_thickness(bpy.types.Operator):
    bl_idname = "deckglow.reset_thickness"
    bl_label = "Reset Shape"
    bl_description = "Put every strip back to the width and height build_deck.py gave it"

    def execute(self, context):
        context.scene.glow_thickness = 1.0
        context.scene.glow_height = 0.0
        return {'FINISHED'}


class GLOW_OT_print(bpy.types.Operator):
    bl_idname = "deckglow.print_values"
    bl_label = "Values for build_deck.py"
    bl_description = ("Collect the current values as the lines to paste back into "
                      "build_deck.py, in a text block you can open in the Text Editor")

    def execute(self, context):
        s = context.scene
        c = tuple(round(v, 3) for v in s.glow_color)
        lo, hi = 0.0038 * s.glow_thickness, 0.0060 * s.glow_thickness
        lines = [
            "",
            "# --- section 2, MATS ---",
            '"runeGlow":      mat("runeGlow", (0.006, 0.030, 0.055), 0.55, '
            f"emit={c}, strength={round(s.glow_strength, 2)}),",
            "# --- section 4, the strip width and top ---",
            f"        w = grnd.uniform({lo:.4f}, {hi:.4f})",
            "    GZ0, GZ1 = F - 0.020, F + %.4f" % (0.017 + s.glow_height),
            "# --- section 11, the glare ---",
            f'_glare_set(glare, "Threshold", {round(s.glow_glare_threshold, 2)})',
            f'_glare_set(glare, "Strength", {round(s.glow_glare_strength, 2)})',
            f'_glare_set(glare, "Size", {round(s.glow_glare_size, 2)})',
            "",
        ]
        body = "\n".join(lines).lstrip("\n")
        # macOS has no Window > Toggle System Console, so print() goes nowhere
        # visible unless Blender was launched from a terminal. The text block is
        # the copy you can actually read.
        txt = bpy.data.texts.get(TEXT_BLOCK) or bpy.data.texts.new(TEXT_BLOCK)
        txt.clear()
        txt.write(body)
        print(body)
        self.report({'INFO'}, f"Written to text block '{TEXT_BLOCK}'")
        return {'FINISHED'}


# ---------------------------------------------------------------------- panel
class GLOW_PT_panel(bpy.types.Panel):
    bl_label = "Ground Glow"
    bl_idname = "GLOW_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Ground Glow"

    def draw(self, context):
        s = context.scene
        lay = self.layout

        if glow_mat() is None:
            lay.label(text=f"No '{MATERIAL}' material", icon='ERROR')
        n = len(rune_meshes(s))
        if not n:
            lay.label(text=f"No '{PREFIX}*' meshes", icon='ERROR')

        col = lay.column(align=True)
        col.prop(s, "glow_color", text="Colour")
        col.prop(s, "glow_thickness")
        col.prop(s, "glow_height")
        col.prop(s, "glow_strength")

        row = lay.row(align=True)
        row.operator(GLOW_OT_reset_thickness.bl_idname, icon='LOOP_BACK')
        row.operator(GLOW_OT_sync.bl_idname, icon='FILE_REFRESH', text="Reload")

        box = lay.box()
        box.label(text="Glare (whole render)", icon='INFO')
        if glare_node() is None:
            box.label(text="No glare node in the compositor", icon='ERROR')
        else:
            c = box.column(align=True)
            c.prop(s, "glow_glare_strength")
            c.prop(s, "glow_glare_size")
            c.prop(s, "glow_glare_threshold")

        lay.operator(GLOW_OT_print.bl_idname, icon='CONSOLE')


CLASSES = (GLOW_OT_sync, GLOW_OT_reset_thickness, GLOW_OT_print, GLOW_PT_panel)
PROPS = ("glow_color", "glow_thickness", "glow_height", "glow_strength",
         "glow_glare_strength", "glow_glare_size", "glow_glare_threshold")


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    S, P = bpy.types.Scene, bpy.props

    S.glow_color = P.FloatVectorProperty(
        name="Colour", description="Emission colour of the ground strips",
        subtype='COLOR', size=3, default=(0.02, 0.13, 1.0), min=0.0, max=1.0,
        update=_upd_look)
    S.glow_thickness = P.FloatProperty(
        name="Thickness",
        description="Strip width, as a multiple of the width build_deck.py laid down",
        default=1.0, min=0.15, max=4.0, soft_max=2.5, update=_upd_shape)
    S.glow_height = P.FloatProperty(
        name="Height", unit='LENGTH',
        description=("How far the strip's top sits above where build_deck.py put "
                     "it. Go far negative and the strips drop below the stones "
                     "either side, and the outer rings vanish at grazing angles"),
        default=0.0, min=-0.020, max=0.060, soft_min=-0.020, soft_max=0.030,
        precision=4, step=0.02, update=_upd_shape)
    S.glow_strength = P.FloatProperty(
        name="Glow",
        description=("Radiance of the strips. This is the per-line bloom control: "
                     "the glare only picks up what clears its threshold"),
        default=4.2, min=0.0, max=20.0, soft_max=10.0, update=_upd_look)

    S.glow_glare_strength = P.FloatProperty(
        name="Strength", description="How much the glare adds back over the image",
        default=0.95, min=0.0, max=4.0, update=_upd_glare)
    S.glow_glare_size = P.FloatProperty(
        name="Size",
        description=("Glare radius as a fraction of the frame. Small values hug "
                     "the emitter; large ones smear the render into flat fog"),
        default=0.25, min=0.01, max=1.0, update=_upd_glare)
    S.glow_glare_threshold = P.FloatProperty(
        name="Threshold",
        description=("Scene-linear level a pixel must clear to bloom at all. Keep "
                     "it under the strips' Glow or they stop blooming entirely"),
        default=0.55, min=0.0, max=4.0, update=_upd_glare)

    scene = getattr(bpy.context, "scene", None)
    if scene:
        sync(scene)


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
