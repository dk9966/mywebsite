"""Bake and export the cave scene for the website (`/cave`).

The cave is lit by 55 Cycles lights with soft shadows, light linking, GI and
volumetric mist. Direct light is shaded live in the browser (every light, with
shadow maps for the strong ones), so nothing view- or light-dependent is
frozen into the textures. Only what three.js cannot compute is baked, per
opaque surface, into a few texture atlases:

  * albedo-N     base colour (sRGB) + coverage (alpha, the deck grates' holes)
  * detail-N     shading normal (octahedral, glTF space), roughness,
                 metallic / specular strength (see DETAIL ALPHA)
  * light-N      Cycles' *indirect* diffuse light only (multi-bounce GI, no
                 direct light, so no hard shadows), log-encoded, half size

and the rest is exported as data:

  * emissive fixtures   exported with their exact emission colour x strength
                        (they stay HDR for the bloom pass)
  * transparent glass   exported with a simple translucent material
  * lights              type, power (watts), colour, cone, size, linking
  * mist volumes        exported as boxes + density parameters (manifest),
                        ray-marched in the browser against the light list
  * compositor bloom    reproduced in the browser (amber-only fog glow)
  * view transform      `gen_view_lut.py` (AgX look, exposure) as a 3D LUT

Never touches the source file: run it on a copy in a background Blender.

  Blender --background SNAPSHOT.blend --python export_cave.py -- [--quick]

Outputs, in secret-base/models/cave/:
  cave.glb            geometry (Draco), one material per bake chunk
  albedo/detail/light-N.png   chunk atlases, converted to webp
  manifest.json       camera, lights, mist volumes, voxel hole frame, atlases
"""
import bpy, bmesh, json, math, os, sys, time
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("CAVE_OUT", os.path.join(HERE, "..", "models", "cave"))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS                     # low samples / small atlases for pipeline tests
ONLY = next(({int(x) for x in a.split("=")[1].split(",")} for a in ARGS if a.startswith("--only=")), None)

ATLAS = 2048 if QUICK else 4096
SAMPLES = 16 if QUICK else 512                # indirect light (the only noisy bake)
MATERIAL_SAMPLES = 2 if QUICK else 8          # albedo / parameters / normal (anti-aliasing only)
PACK_EFFICIENCY = 0.62                        # usable fraction of an atlas after packing
DENSITY = {"cave": 52.0, "default": 105.0}   # target texels per metre
# Indirect light is smooth: baked at 1/LIGHT_DIVISOR of the material atlas size.
LIGHT_DIVISOR = 2
# UV island gap, in texels of the (smaller) light atlas.
ISLAND_GAP = 4
# Light atlases store log2(value / scale) over LOG_STOPS stops in 8 bits; 0 = black.
LOG_STOPS = 18.0
# DETAIL ALPHA: metals (metallic >= 0.5) store 0.5 + 0.5 * metallic; other
# surfaces 0.02 + 0.47 * min(2 * Specular IOR Level, 1), their specular
# strength (Blender's 0.5 = 1). WebP drops the colour of fully transparent
# texels, so a channel stored in alpha must never reach 0.
CAMERA_NAME = "150 | main cave camera"
CAVE_WALL = "150 | continuous cave with oblique carved rooms"
TRANSPARENT = {"glassPane", "holoTable_CW_original_misty_glass"}

scene = bpy.context.scene
os.makedirs(OUT, exist_ok=True)
t0 = time.time()


def log(*parts):
    print(f"[cave-export {time.time() - t0:7.1f}s]", *parts, flush=True)


# ---------------------------------------------------------------- helpers ---

def to_gltf(v):
    """Blender Z-up -> glTF Y-up."""
    return [v[0], v[2], -v[1]]


def is_volume_only(mat):
    if not mat or not mat.node_tree:
        return False
    out = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output), None)
    return bool(out and out.inputs["Volume"].is_linked and not out.inputs["Surface"].is_linked)


def principled(mat):
    if not mat or not mat.node_tree:
        return None
    return next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)


def emission_of(mat):
    """Linear emission colour * strength, or None for non-emitters."""
    p = principled(mat)
    if not p:
        return None
    strength = p.inputs["Emission Strength"].default_value
    color = p.inputs["Emission Color"].default_value
    if strength <= 0 or p.inputs["Emission Strength"].is_linked or max(color[:3]) <= 0:
        return None
    return [c * strength for c in color[:3]]


def mesh_area(obj):
    me = obj.data
    scale = abs(obj.matrix_world.to_3x3().determinant()) ** (2 / 3)
    return sum(p.area for p in me.polygons) * scale


def select_only(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


# ------------------------------------------------------- render settings ---

prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("METAL", "OPTIX", "CUDA", "HIP"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = True
            scene.cycles.device = "GPU"
            log("bake device", kind)
            break
    except TypeError:
        continue
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = False
camera = bpy.data.objects[CAMERA_NAME]
scene.camera = camera
bake = scene.render.bake
bake.target = "IMAGE_TEXTURES"
bake.margin = 6
bake.margin_type = "EXTEND"
bake.use_clear = True
bake.view_from = "ABOVE_SURFACE"
bake.use_selected_to_active = False
# DIFFUSE bakes: indirect light only, without the surface colour.
bake.use_pass_direct = False
bake.use_pass_indirect = True
bake.use_pass_color = False

# ------------------------------------------------- collect source objects ---

def render_collections():
    """Collections that render: not excluded from the view layer, not render-disabled."""
    found = set()

    def walk(lc):
        if lc.exclude or lc.collection.hide_render:
            return
        found.add(lc.collection)
        for child in lc.children:
            walk(child)
    walk(bpy.context.view_layer.layer_collection)
    return found


# Render visibility, not viewport visibility: the cave's main haze volume is
# hidden in the viewport but renders.
RENDERED = render_collections()


def renders(o):
    return not o.hide_render and any(c in RENDERED for c in o.users_collection)


for o in scene.objects:
    if renders(o):
        o.hide_set(False)
        o.hide_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
sources = [o for o in scene.objects
           if o.type in {"MESH", "CURVE", "FONT", "SURFACE", "META"} and renders(o)]
volumes = [o for o in sources if o.type == "MESH" and o.material_slots
           and all(is_volume_only(s.material) for s in o.material_slots if s.material)]
# Principled volumes have no surface either; is_volume_only covers them too.
sources = [o for o in sources if o not in volumes]
log(len(sources), "surface objects,", len(volumes), "mist volumes")

work = bpy.data.collections.new("WEB | baked copies")
scene.collection.children.link(work)

# Light linking: a few fills only light their receiver collections. Copies must
# join the same collections, and a bake chunk must never mix memberships
# (linking is per object, and a chunk becomes one object).
linking = {L.light_linking.receiver_collection for L in scene.objects
           if L.type == "LIGHT" and L.light_linking.receiver_collection}
linking |= {L.light_linking.blocker_collection for L in scene.objects
            if L.type == "LIGHT" and L.light_linking.blocker_collection}
linking.discard(None)
signature = {}

copies = []
for src in sources:
    ev = src.evaluated_get(dg)
    try:
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    except RuntimeError:
        continue
    if not me or not me.polygons:
        continue
    obj = bpy.data.objects.new("WEB|" + src.name, me)
    obj.matrix_world = src.matrix_world
    work.objects.link(obj)
    # Effective materials: the evaluated mesh carries geometry-node materials,
    # but 2,000+ slots here are linked to the object ("Right steel | ...") and
    # override the older mesh-data material at that index.
    for i, slot in enumerate(src.material_slots):
        if slot.link == "OBJECT" and slot.material:
            if i < len(me.materials):
                me.materials[i] = slot.material
            else:
                me.materials.append(slot.material)
    if not me.materials and src.material_slots:
        for slot in src.material_slots:
            me.materials.append(slot.material)
    member = tuple(sorted(c.name for c in linking if src.name in c.all_objects))
    for name in member:
        bpy.data.collections[name].objects.link(obj)
    signature[obj.name] = member
    copies.append(obj)
    src.hide_render = True          # the copy stands in for it from now on
    src.hide_set(True)
log(len(copies), "evaluated copies")

# Procedural steel and rock materials read Object / Generated texture
# coordinates. Joining objects into bake chunks (and applying transforms) would
# change both, so each copy stores its own as attributes first, and those
# materials are rewired (in this scratch copy of the scene only) to read them.
OBJECT_ATTR, GENERATED_ATTR = "web_object", "web_generated"
for obj in copies:
    me = obj.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    pts = co.reshape(-1, 3)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    gen = (pts - lo) / np.maximum(hi - lo, 1e-6)
    for name, values in ((OBJECT_ATTR, pts), (GENERATED_ATTR, gen)):
        attr = me.attributes.new(name, "FLOAT_VECTOR", "POINT")
        attr.data.foreach_set("vector", values.astype(np.float32).ravel())

IMPLICIT_GENERATED = {"ShaderNodeTexNoise", "ShaderNodeTexVoronoi", "ShaderNodeTexWave", "ShaderNodeTexMagic",
                      "ShaderNodeTexGradient", "ShaderNodeTexChecker", "ShaderNodeTexBrick", "ShaderNodeTexWhiteNoise"}


def rewire_coordinates(mat):
    nt = mat.node_tree
    if not nt:
        return 0
    attrs = {}

    def attribute(name):
        if name not in attrs:
            node = nt.nodes.new("ShaderNodeAttribute")
            node.attribute_name = name
            attrs[name] = node
        return attrs[name].outputs["Vector"]
    changed = 0
    for node in list(nt.nodes):
        if node.bl_idname == "ShaderNodeTexCoord":
            for out_name, attr_name in (("Object", OBJECT_ATTR), ("Generated", GENERATED_ATTR)):
                for link in list(node.outputs[out_name].links):
                    nt.links.new(attribute(attr_name), link.to_socket)
                    changed += 1
        elif node.bl_idname in IMPLICIT_GENERATED and "Vector" in node.inputs and not node.inputs["Vector"].is_linked:
            nt.links.new(attribute(GENERATED_ATTR), node.inputs["Vector"])
            changed += 1
    return changed


surface_materials = {s.material for o in copies for s in o.material_slots if s.material}
rewired = sum(rewire_coordinates(m) for m in surface_materials)
log(rewired, "texture-coordinate links rewired to attributes")

# Every transform goes into the mesh data, so no chunk inherits a mirrored
# matrix (Cycles bakes negative-scale objects from behind: black).
select_only(copies)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def split_by_material(obj, predicate):
    """Move faces whose material matches `predicate` into their own object."""
    me = obj.data
    idx = [i for i, m in enumerate(me.materials) if predicate(m)]
    if not idx:
        return None
    if len(idx) == len(me.materials):
        return obj
    select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(me)
    for f in bm.faces:
        f.select = f.material_index in idx
    bmesh.update_edit_mesh(me)
    if not any(f.select for f in bm.faces):
        bpy.ops.object.mode_set(mode="OBJECT")
        return None
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    part = next(o for o in bpy.context.selected_objects if o is not obj)
    return part


def is_transparent(m):
    return m is not None and m.name in TRANSPARENT


def is_emissive(m):
    return emission_of(m) is not None


def only(obj, predicate):
    used = {p.material_index for p in obj.data.polygons}
    return bool(used) and all(i < len(obj.data.materials) and predicate(obj.data.materials[i]) for i in used)


# Whole-object emitters and glass skip the bake. Mixed objects are baked whole
# (splitting first would change their Generated coordinates) and their
# emissive/glass faces are separated afterwards.
emissive, transparent, opaque = [], [], []
for obj in copies:
    # Glass is split off first (texture coordinates are already stored), so the
    # camera projection can see through it to the console behind.
    part = split_by_material(obj, is_transparent)
    if part is obj:
        transparent.append(obj)
        continue
    if part:
        transparent.append(part)
    if only(obj, is_emissive):
        emissive.append(obj)
    else:
        opaque.append(obj)
log(len(opaque), "baked,", len(emissive), "emissive,", len(transparent), "transparent")

# --------------------------------------------------------- chunk + unwrap ---

def morton(x, y, z):
    def spread(v):
        v &= 0x3FF
        v = (v | (v << 16)) & 0x30000FF
        v = (v | (v << 8)) & 0x300F00F
        v = (v | (v << 4)) & 0x30C30C3
        return (v | (v << 2)) & 0x9249249
    return spread(x) | (spread(y) << 1) | (spread(z) << 2)


capacity = ATLAS * ATLAS * PACK_EFFICIENCY
entries = []
for obj in opaque:
    kind = "cave" if obj.name == "WEB|" + CAVE_WALL else "default"
    texels = mesh_area(obj) * DENSITY[kind] ** 2
    c = obj.matrix_world @ (sum((Vector(b) for b in obj.bound_box), Vector()) / 8)
    group = (kind, signature.get(obj.name, ()))
    entries.append((group, morton(int(c.x / 3 + 200), int(c.y / 3 + 200), int(c.z / 3 + 200)), texels, obj))

chunks = []
chunk_texels = []
for kind in sorted({e[0] for e in entries}, key=lambda g: (g[0] != "cave", g)):
    group = sorted((e for e in entries if e[0] == kind), key=lambda e: e[1])
    current, used = [], 0.0
    for _, _, texels, obj in group:
        if current and used + texels > capacity:
            chunks.append(current)
            chunk_texels.append(used)
            current, used = [], 0.0
        current.append(obj)
        used += texels
    if current:
        chunks.append(current)
        chunk_texels.append(used)


def atlas_size(texels):
    """Smallest power-of-two atlas that holds the chunk at the target density."""
    side = math.sqrt(texels / PACK_EFFICIENCY)
    return int(min(ATLAS, max(512, 2 ** math.ceil(math.log2(max(side, 1))))))

log(len(chunks), "bake chunks")

baked = []          # (atlas index, joined chunk object, atlas size)
chunk_links = []    # light-linking collections each chunk belongs to
for i, members in enumerate(chunks):
    target = members[0]
    chunk_links.append(signature.get(target.name, ()))
    if len(members) > 1:
        select_only(members, target)
        bpy.ops.object.join()
    target.name = f"WEB bake {i}"
    me = target.data
    render_uv = next((uv.name for uv in me.uv_layers if uv.active_render), None)
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")       # shaders using default UVs need one
    bake_uv = me.uv_layers.new(name="BakeUV")
    me.uv_layers.active = bake_uv
    # Bake into BakeUV, but keep shading (image textures without an explicit
    # UV node) on the original map.
    me.uv_layers[render_uv or 0].active_render = True
    select_only([target])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.0,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    size = atlas_size(chunk_texels[i])
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=ISLAND_GAP * LIGHT_DIVISOR / size)
    bpy.ops.object.mode_set(mode="OBJECT")
    log(f"chunk {i}: {len(members)} objects, {len(me.polygons)} faces, {mesh_area(target):.0f} m², {size}px")
    baked.append((i, target, size))

SAVE_PREPARED = next((a.split("=", 1)[1] for a in ARGS if a.startswith("--save-prepared=")), None)
if SAVE_PREPARED:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_PREPARED, copy=True)
    log("prepared scene saved to", SAVE_PREPARED)
    if "--prepare-only" in ARGS:
        sys.exit(0)

# ------------------------------------------------------------------- bake ---

def surface_output(nt):
    return next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output)


def feed(nt, socket, target):
    """Drive `target` with whatever drives `socket` (a link or its constant)."""
    if socket.is_linked:
        nt.links.new(socket.links[0].from_socket, target)
    elif target.type == "RGBA" and socket.type == "VALUE":
        v = socket.default_value
        target.default_value = (v, v, v, 1)
    else:
        target.default_value = socket.default_value


def rewire_surface(build):
    """A material rewire for one bake pass: `build(nt, principled, new)` returns
    the shader socket that temporarily drives the surface output. Returns a
    callable that applies it to a material and returns the undo."""
    def apply(mat):
        nt = mat.node_tree
        out = surface_output(nt)
        socket = out.inputs["Surface"]
        previous = socket.links[0].from_socket if socket.is_linked else None
        added = []

        def new(kind):
            node = nt.nodes.new(kind)
            added.append(node)
            return node
        nt.links.new(build(nt, principled(mat), previous, new), socket)

        def undo():
            for node in added:
                nt.nodes.remove(node)
            if previous:
                nt.links.new(previous, socket)
        return undo
    return apply


def emission_of_inputs(names, defaults):
    """Emission whose colour is the Principled inputs `names` (one colour input,
    or up to three scalars packed as RGB)."""
    def build(nt, p, previous, new):
        emit = new("ShaderNodeEmission")
        emit.inputs["Strength"].default_value = 1.0
        if len(names) == 1:
            target = emit.inputs["Color"]
            if p:
                feed(nt, p.inputs[names[0]], target)
            else:
                target.default_value = defaults
        else:
            pack = new("ShaderNodeCombineXYZ")
            for i, name in enumerate(names):
                if p:
                    feed(nt, p.inputs[name], pack.inputs[i])
                else:
                    pack.inputs[i].default_value = defaults[i]
            nt.links.new(pack.outputs["Vector"], emit.inputs["Color"])
        return emit.outputs["Emission"]
    return rewire_surface(build)


def white_at_bake_point(nt, p, previous, new):
    """The baked texel sees a white diffuse surface (metals have no diffuse
    lobe, so their light pass would be black); every bounce still sees the
    real material."""
    is_camera = new("ShaderNodeLightPath").outputs["Is Camera Ray"]
    mix = new("ShaderNodeMixShader")
    white = new("ShaderNodeBsdfDiffuse")
    white.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(is_camera, mix.inputs["Fac"])
    if previous:
        nt.links.new(previous, mix.inputs[1])
    nt.links.new(white.outputs["BSDF"], mix.inputs[2])
    return mix.outputs["Shader"]


BASE_COLOR = emission_of_inputs(["Base Color"], (0.5, 0.5, 0.5, 1))
PARAMETERS = emission_of_inputs(["Roughness", "Metallic", "Alpha"], (0.5, 0, 1))
SPECULAR = emission_of_inputs(["Specular IOR Level"], (0.5, 0.5, 0.5, 1))
WHITE_DIFFUSE = rewire_surface(white_at_bake_point)


def bake_pass(obj, size, kind, label, samples, rewire=None):
    """One Cycles bake of `obj` into a float image, returned as size x size x 4."""
    image = bpy.data.images.new(f"{label}-{obj.name}", size, size, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    undo = []
    for mat in {s.material for s in obj.material_slots if s.material}:
        if not mat.use_nodes:
            mat.use_nodes = True
        nt = mat.node_tree
        node = nt.nodes.get("WEB bake target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "WEB bake target"
        node.image = image
        nt.nodes.active = node
        if rewire:
            undo.append(rewire(mat))
    select_only([obj])
    scene.cycles.samples = samples
    log(f"baking {label} of {obj.name} at {size}px, {samples} samples")
    bpy.ops.object.bake(type=kind, use_clear=True, margin=bake.margin, target="IMAGE_TEXTURES",
                        normal_space="OBJECT")
    for restore in undo:
        restore()
    pixels = np.empty(size * size * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return push_pull(fill_gaps(pixels.reshape(size, size, 4)))


def fill_gaps(px, rounds=3):
    """Fill texels the bake left empty (alpha 0) next to baked ones with the
    mean of their baked neighbours, in place. Sliver faces leave texel centres
    outside every triangle *inside* UV islands, where the bake margin does not
    reach; unfilled they read as zeros (black, roughness 0, no normal)."""
    valid = px[..., 3] > 0.5
    offsets = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    for _ in range(rounds):
        total = np.zeros(px.shape[:2] + (3,), np.float32)
        count = np.zeros(px.shape[:2], np.float32)
        for dy, dx in offsets:
            ok = np.roll(valid, (dy, dx), axis=(0, 1))
            total += np.roll(px[..., :3], (dy, dx), axis=(0, 1)) * ok[..., None]
            count += ok
        grow = ~valid & (count > 0)
        if not grow.any():
            break
        px[grow, :3] = total[grow] / count[grow, None]
        px[grow, 3] = 1.0
        valid |= grow
    return px


def push_pull(px):
    """Fill every remaining empty texel (alpha 0) from a pyramid of the baked
    ones, in place: coarse mip levels of small UV islands (the stair tread
    tiles) then average real neighbouring data instead of black. Filled
    texels get alpha 0.5, so `alpha > 0.75` still marks the baked surface."""
    weight = (px[..., 3] > 0.5).astype(np.float32)
    levels = [(px[..., :3] * weight[..., None], weight)]
    while levels[-1][1].shape[0] > 1:
        c, w = levels[-1]
        h = w.shape[0] // 2
        levels.append((c.reshape(h, 2, h, 2, 3).sum(axis=(1, 3)), w.reshape(h, 2, h, 2).sum(axis=(1, 3))))
    color = levels[-1][0] / np.maximum(levels[-1][1], 1e-6)[..., None]
    for c, w in reversed(levels[:-1]):
        parent = np.repeat(np.repeat(color, 2, axis=0), 2, axis=1)
        color = np.where(w[..., None] > 0, c / np.maximum(w, 1e-6)[..., None], parent)
    empty = px[..., 3] <= 0.5
    px[empty, :3] = color[empty]
    px[empty, 3] = 0.5
    return px


def save_png(name, rgba):
    """Write 8-bit data as-is (no colour management) and return the file name."""
    size = rgba.shape[0]
    out = bpy.data.images.new(name, size, size, alpha=True)
    out.colorspace_settings.name = "Non-Color"
    out.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    out.filepath_raw = os.path.join(OUT, f"{name}.png")
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    return f"{name}.png"


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def octahedral(n):
    """Unit vectors -> [0, 1]² (z folded). In glTF space -Z points away from
    the scene camera, so the fold's seam lands on faces nobody sees."""
    n = n / np.maximum(np.abs(n).sum(axis=-1, keepdims=True), 1e-9)
    xy = n[..., :2]
    sign = np.where(xy >= 0, 1.0, -1.0)
    folded = (1 - np.abs(xy[..., ::-1])) * sign
    xy = np.where(n[..., 2:3] < 0, folded, xy)
    return xy * 0.5 + 0.5


def encode_light(i, rgb):
    peak = rgb.max(axis=2)
    lit = peak[peak > 0]
    scale = float(np.percentile(lit, 99.98)) if lit.size else 1.0
    scale = max(scale, 1e-3)
    floor = 2.0 ** -LOG_STOPS
    v = np.clip(rgb / scale, 0, 1)
    code = np.where(v > floor, 1 + np.round((np.log2(np.maximum(v, floor)) + LOG_STOPS) / LOG_STOPS * 254), 0)
    code = np.clip(code, 0, 255) / 255.0
    rgba = np.concatenate([code, np.ones(code.shape[:2] + (1,))], axis=2)
    return {"light": save_png(f"light-{i}", rgba), "scale": scale, "stops": LOG_STOPS, "lightSize": rgb.shape[0]}


def bake_chunk(i, obj, size):
    color = bake_pass(obj, size, "EMIT", "albedo", MATERIAL_SAMPLES, BASE_COLOR)
    params = bake_pass(obj, size, "EMIT", "parameters", MATERIAL_SAMPLES, PARAMETERS)
    specular = bake_pass(obj, size, "EMIT", "specular", MATERIAL_SAMPLES, SPECULAR)[..., 0]
    normal = bake_pass(obj, size, "NORMAL", "normal", MATERIAL_SAMPLES)
    light = bake_pass(obj, size // LIGHT_DIVISOR, "DIFFUSE", "light", SAMPLES, WHITE_DIFFUSE)
    roughness, metallic, alpha = params[..., 0], params[..., 1], params[..., 2]
    # Coverage never quite reaches 0 (see DETAIL ALPHA): holes keep their base
    # colour, so mipmaps of the grates average colour, not black. Texels no
    # surface uses are opaque, so mipmaps never open cracks along UV seams.
    used = color[..., 3] > 0.75
    coverage = np.where(used, np.clip(alpha, 1 / 255, 1), 1.0)
    albedo = save_png(f"albedo-{i}", np.concatenate([srgb(color[..., :3]), coverage[..., None]], axis=2))
    # Transforms are applied, so object space is world space (Blender Z-up).
    n = normal[..., :3] * 2 - 1
    n = np.stack([n[..., 0], n[..., 2], -n[..., 1]], axis=-1)
    reflect = np.where(metallic >= 0.5, 0.5 + 0.5 * np.clip(metallic, 0, 1),
                       0.02 + 0.47 * np.clip(2 * specular, 0, 1))
    detail = np.concatenate([octahedral(n), roughness[..., None], reflect[..., None]], axis=2)
    meta = {"name": f"WEB bake {i}", "size": size, "albedo": albedo, "detail": save_png(f"detail-{i}", detail),
            "receivers": list(chunk_links[i])}
    meta.update(encode_light(i, light[..., :3]))
    return meta


atlases = []
for i, obj, size in baked:
    if ONLY is not None and i not in ONLY:
        continue
    meta = bake_chunk(i, obj, size)
    atlases.append(meta)
    log(f"chunk {i} encoded, light scale {meta['scale']:.3f}")

# ----------------------------------------------------------- manifest data ---

def light_entry(o):
    L = o.data
    mw = o.matrix_world
    forward = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    entry = {
        "name": o.name, "type": L.type, "power": L.energy,
        "color": list(L.color), "position": to_gltf(mw.translation),
        "direction": to_gltf(forward),
        # Per-light contribution factors (several fills are dimmed for surfaces only).
        "diffuse": L.diffuse_factor, "specular": L.specular_factor,
    }
    receivers = o.light_linking.receiver_collection
    if receivers:
        # Light-linked: lights only these objects, never the mist volumes.
        entry["linked"] = not any(v.name in receivers.all_objects for v in volumes)
        entry["receivers"] = receivers.name
    if L.type == "SPOT":
        entry.update(angle=L.spot_size, blend=L.spot_blend, radius=L.shadow_soft_size)
    elif L.type == "AREA":
        sx = L.size * mw.to_scale().x
        sy = (L.size_y if L.shape in {"RECTANGLE", "ELLIPSE"} else L.size) * mw.to_scale().y
        entry.update(size=[sx, sy], shape=L.shape)
    else:
        entry.update(radius=L.shadow_soft_size)
    return entry


def mist_entry(o):
    mat = o.material_slots[0].material
    nt = mat.node_tree
    conv = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
    principled = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeVolumePrincipled"), None)
    if principled:
        # Uniform Principled Volume: scatter = density * colour, absorption =
        # density * (1 - colour) * (1 - absorption colour).
        # The mesh is not a unit cube; fold its bounds into the matrix.
        lo = Vector(o.bound_box[0])
        hi = Vector(o.bound_box[6])
        cube = Matrix.Translation((lo + hi) / 2) @ Matrix.Diagonal((*(hi - lo), 1))
        m = conv @ o.matrix_world @ cube
        absorb = [1 - c for c in principled.inputs["Absorption Color"].default_value[:3]]
        color = list(principled.inputs["Color"].default_value)[:3]
        return {
            "name": o.name,
            "matrix": [m[r][c] for c in range(4) for r in range(4)],
            "density": principled.inputs["Density"].default_value,
            "uniform": True,
            "radialStart": 0, "edge": 0,
            "color": color,
            "absorption": [max(1 - c, 0) * a for c, a in zip(color, absorb)],
            "anisotropy": principled.inputs["Anisotropy"].default_value,
            "noise": None,
        }
    radial = next(n for n in nt.nodes if n.name == "Map Range")
    vertical = next(n for n in nt.nodes if n.name == "Map Range.001")
    density_node = nt.nodes.get("Under-platform density") or nt.nodes.get("Math.003")
    noise = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeTexNoise"), None)
    noise_map = nt.nodes.get("Map Range.002")
    scatter = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeVolumeScatter")
    # Blender's object matrix maps the unit cube (-0.5..0.5) to the volume.
    m = conv @ o.matrix_world
    return {
        "name": o.name,
        "matrix": [m[r][c] for c in range(4) for r in range(4)],   # column-major, glTF space
        "density": density_node.inputs[1].default_value,
        "radialStart": radial.inputs["From Min"].default_value,
        "edge": vertical.inputs["From Max"].default_value,
        "color": list(scatter.inputs["Color"].default_value)[:3],
        "anisotropy": scatter.inputs["Anisotropy"].default_value,
        "noise": None if not noise else {
            "scale": noise.inputs["Scale"].default_value,
            "detail": noise.inputs["Detail"].default_value,
            "roughness": noise.inputs["Roughness"].default_value,
            "from": [noise_map.inputs["From Min"].default_value, noise_map.inputs["From Max"].default_value],
            "to": [noise_map.inputs["To Min"].default_value, noise_map.inputs["To Max"].default_value],
        },
    }


def hole_frame():
    """The rear opening behind the central platform, in glTF space.

    voxel-entry-hole/cut_recess.py opened the rear sculpt bowl; the rim has been
    re-sculpted since, so find it as the open boundary loop at the back of the
    cave mesh rather than trusting the original Y = 14.2 cut plane.
    """
    wall = bpy.data.objects[CAVE_WALL]
    mw = wall.matrix_world
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    edges = [e for e in bm.edges if e.is_boundary]
    remaining = {v for e in edges for v in e.verts}
    loops = []
    while remaining:
        seed = remaining.pop()
        comp, todo = {seed}, [seed]
        while todo:
            v = todo.pop()
            for e in v.link_edges:
                if e.is_boundary and e.other_vert(v) in remaining:
                    o = e.other_vert(v)
                    remaining.remove(o)
                    comp.add(o)
                    todo.append(o)
        loops.append([v.co.copy() for v in comp])
    bm.free()
    rim = max(loops, key=lambda loop: sum(v.y for v in loop) / len(loop))
    lo = Vector((min(v.x for v in rim), min(v.y for v in rim), min(v.z for v in rim)))
    hi = Vector((max(v.x for v in rim), max(v.y for v in rim), max(v.z for v in rim)))
    rot = mw.to_3x3().normalized()
    return {
        # Wall-local frame: right = +X, into the rock = +Y, up = +Z.
        "origin": to_gltf(mw @ Vector(((lo.x + hi.x) / 2, hi.y, lo.z))),
        "right": to_gltf(rot @ Vector((1, 0, 0))),
        "up": to_gltf(rot @ Vector((0, 0, 1))),
        "into": to_gltf(rot @ Vector((0, 1, 0))),
        "width": hi.x - lo.x, "height": hi.z - lo.z, "depth": hi.y - lo.y,
        "rim": [to_gltf(mw @ v) for v in rim],
    }


cam = camera
cam_dir = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
cam_up = (cam.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
manifest = {
    "source": bpy.data.filepath,
    "exported": time.strftime("%Y-%m-%d %H:%M:%S"),
    "camera": {
        "position": to_gltf(cam.matrix_world.translation),
        "direction": to_gltf(cam_dir), "up": to_gltf(cam_up),
        "lens": cam.data.lens, "sensor": cam.data.sensor_width,
        "shift": [cam.data.shift_x, cam.data.shift_y],
        "clipStart": cam.data.clip_start, "clipEnd": cam.data.clip_end,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    },
    "view": {"transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
             "exposure": scene.view_settings.exposure},
    "world": {"color": list(scene.world.node_tree.nodes["Background"].inputs[0].default_value)[:3],
              "strength": scene.world.node_tree.nodes["Background"].inputs[1].default_value},
    "lights": [light_entry(o) for o in scene.objects
               if o.type == "LIGHT" and renders(o) and o.data.energy > 0],
    "mists": [mist_entry(o) for o in volumes],
    "hole": hole_frame(),
    "atlases": atlases,
    "emissive": {},
    "transparent": {},
}

# -------------------------------------------------------- prepare export ---

chunk_objects = []
for i, obj, size in baked:
    e = split_by_material(obj, is_emissive)
    if e and e is not obj:
        emissive.append(e)
    me = obj.data
    for uv in [u for u in me.uv_layers if u.name != "BakeUV"]:
        me.uv_layers.remove(uv)
    mat = bpy.data.materials.new(f"bake_{i}")
    me.materials.clear()
    me.materials.append(mat)
    obj.name = f"bake_{i}"
    chunk_objects.append(obj)

for obj in emissive:
    for slot in obj.material_slots:
        m = slot.material
        if m and emission_of(m):
            manifest["emissive"][m.name] = emission_of(m)
    me = obj.data
    for uv in list(me.uv_layers):
        me.uv_layers.remove(uv)
for obj in transparent:
    for slot in obj.material_slots:
        m = slot.material
        if not m:
            continue
        p = principled(m)
        manifest["transparent"][m.name] = {
            "color": list(p.inputs["Base Color"].default_value)[:3] if p else [0.35, 0.62, 0.85],
            "alpha": p.inputs["Alpha"].default_value if p else 0.25,
            "roughness": p.inputs["Roughness"].default_value if p else 0.1,
        }

export = list(chunk_objects)
for group, name in ((emissive, "emissive"), (transparent, "transparent")):
    if not group:
        continue
    select_only(group)
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    export.append(joined)

select_only(export)
glb = os.path.join(OUT, "cave.glb")
bpy.ops.export_scene.gltf(
    filepath=glb, export_format="GLB", use_selection=True,
    export_apply=True, export_normals=False, export_tangents=False,
    export_materials="EXPORT", export_image_format="NONE",
    export_cameras=False, export_lights=False, export_extras=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
    export_draco_position_quantization=16, export_draco_texcoord_quantization=14,
)
with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=1)
log("EXPORT_DONE", glb, os.path.getsize(glb) // 1024, "KiB")
