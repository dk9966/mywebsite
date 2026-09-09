"""Export the workshop pillar + deck to secret-base/models/pillar.glb.

Places four empties the Three.js loader parents screens onto:

  holoLocator_left / holoLocator_right  — above each wing HUD
  holoLocator_main                      — floating over the keyboard
  holoLocator_seat                      — look-at target (no mesh)

Run from Blender:
  exec(open("/Users/danielku/mywebsite/secret-base/export_pillar.py").read())
"""

import bpy
import math
import os
from mathutils import Vector

ROOT = "/Users/danielku/mywebsite/secret-base"
OUT = os.path.join(ROOT, "models", "pillar.glb")
HOST_NAME = "island_pillar_workshop"
LOCATOR_NAMES = (
    "holoLocator_main",
    "holoLocator_left",
    "holoLocator_right",
    "holoLocator_seat",
)

CA = math.radians(56)
F = 6.8552
PHI = math.radians(38)
U_BACK = 1.76
DEPTH = 0.55
WC = 1.90
LW = 0.95
TOP = 0.50


def uvp(cx, cy, u, v, h):
    c, s = math.cos(CA), math.sin(CA)
    return Vector((cx + u * c - v * s, cy + u * s + v * c, F + h))


def sec(i):
    if i == 0:
        return (U_BACK, 0.0), (0.0, 1.0), (1.0, 0.0)
    g = 1 if i > 0 else -1
    return (
        (U_BACK, g * WC / 2),
        (-math.sin(PHI), g * math.cos(PHI)),
        (math.cos(PHI), g * math.sin(PHI)),
    )


def suv(i, along, depth):
    (ou, ov), (tu, tv), (nu, nv) = sec(i)
    return (ou + along * tu - depth * nu, ov + along * tv - depth * nv)


def ensure_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def make_empty(name, loc, coll, host):
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.18
    empty.hide_render = True
    coll.objects.link(empty)
    empty.parent = host
    empty.matrix_parent_inverse = host.matrix_world.inverted()
    empty.location = loc
    return empty


host = bpy.data.objects.get(HOST_NAME)
if host is None:
    raise RuntimeError("missing %s — open base.blend first" % HOST_NAME)

cx, cy = host.location.x, host.location.y
coll = ensure_collection("holo_locators")

left = uvp(cx, cy, *suv(1, LW * 0.54, DEPTH * 0.5), TOP + 0.58)
right = uvp(cx, cy, *suv(-1, LW * 0.54, DEPTH * 0.5), TOP + 0.58)
main = uvp(cx, cy, U_BACK - DEPTH * 0.55, 0.0, TOP + 0.82)
seat = uvp(cx, cy, 0.55, 0.0, 1.15)

make_empty("holoLocator_left", left, coll, host)
make_empty("holoLocator_right", right, coll, host)
make_empty("holoLocator_main", main, coll, host)
make_empty("holoLocator_seat", seat, coll, host)

bpy.ops.object.select_all(action="DESELECT")
host.select_set(True)
for obj in list(bpy.data.objects):
    if obj.parent is host and obj.type in {"MESH", "EMPTY"}:
        obj.select_set(True)
    # Workshop lamps live in the same file; they are not all parented to the pillar.
    if obj.type == "LIGHT" and obj.name.endswith("_b"):
        obj.select_set(True)
bpy.context.view_layer.objects.active = host

os.makedirs(os.path.dirname(OUT), exist_ok=True)

kwargs = dict(
    filepath=OUT,
    use_selection=True,
    export_format="GLB",
    export_cameras=False,
    export_yup=True,
)
optional = {
    "export_lights": False,
    "export_apply": False,
    "export_extras": False,
    "export_animations": False,
    "export_skins": False,
    "export_morph": False,
    "export_draco_mesh_compression_enable": False,
}

# Drop flags this Blender build does not recognise.
try:
    rna = bpy.types.EXPORT_SCENE_OT_gltf.bl_rna
    known = set(rna.properties.keys())
    for key, value in optional.items():
        if key in known:
            kwargs[key] = value
except Exception:
    pass

try:
    bpy.ops.export_scene.gltf(**kwargs)
except TypeError:
    bpy.ops.export_scene.gltf(
        filepath=OUT,
        use_selection=True,
        export_format="GLB",
    )

print("exported %s (%d selected)" % (OUT, sum(1 for o in bpy.data.objects if o.select_get())))
