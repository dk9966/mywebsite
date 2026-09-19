"""One-shot symmetric station layout, preserving the authored bridge and light rigs."""
import bpy, math
from mathutils import Matrix, Vector
from pathlib import Path

scene = bpy.context.scene
assert not scene.get('three_island_layout'), 'Three-island layout already applied'
root = Path(bpy.data.filepath).parent
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'base.before-three-islands.blend'), copy=True)
project = bpy.data.objects['island_pillar_project']
experience = bpy.data.objects['island_pillar_experience']
bridge = bpy.data.collections['bridge_project_experience']
origin = project.matrix_world.translation.copy()
# Screen-right for the existing station camera. Its opposite is screen-left.
angle = math.atan2(11.194, 8.295)
def rotation(a):
    return Matrix.Translation(origin) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation(-origin)
right, left = rotation(angle), rotation(angle + math.pi)
source = set([experience, *experience.children_recursive, *bridge.objects])
worlds = {o: o.matrix_world.copy() for o in source}
hidden = {o: (o.hide_get(), o.hide_render, o.hide_viewport) for o in source}
about_collection = bpy.data.collections.new('deck_about')
scene.collection.children.link(about_collection)
about_bridge = bpy.data.collections.new('bridge_project_about')
scene.collection.children.link(about_bridge)
copies = {}
for src in source:
    ob = src.copy()
    if src.data: ob.data = src.data.copy()
    ob.name = src.name.replace('experience', 'about') if 'experience' in src.name else 'bridge_about_' + src.name.removeprefix('bridge_')
    (about_bridge if src in bridge.objects.values() else about_collection).objects.link(ob)
    copies[src] = ob
for src, ob in copies.items():
    ob.parent = copies.get(src.parent, src.parent)
# Parent-first assignment avoids applying the layout twice to child objects.
def depth(ob):
    d = 0
    while ob.parent: d += 1; ob = ob.parent
    return d
for src in sorted(source, key=depth):
    src.matrix_world = right @ worlds[src]
    copies[src].matrix_world = left @ worlds[src]
    h, r, v = hidden[src]
    copies[src].hide_set(h); copies[src].hide_render = r; copies[src].hide_viewport = v
    bpy.context.view_layer.update()
about = copies[experience]
experience['station_role'] = 'Experiences'
about['station_role'] = 'About Me'
# Rotate the existing opening, perimeter posts, bulbs and lamps together.
for name in ['deck_railing_b', 'deck_parapet_b', 'deck_lantern_posts_b', 'deck_lantern_glass_b']:
    ob = bpy.data.objects[name]
    ob.matrix_world = right @ ob.matrix_world
for ob in bpy.data.collections['deck_project'].objects:
    if ob.type == 'LIGHT' and ob.name.startswith('deckLight_lantern_'):
        ob.matrix_world = right @ ob.matrix_world
project['station_rim_rotation'] = angle
bpy.context.view_layer.update()
# Cut the second entrance into the narrow perimeter strips. Preserve original
# meshes in the backup; only faces crossing the new bridge opening are removed.
import bmesh
outward = (left @ worlds[experience]).translation - origin
outward.z = 0; outward.normalize()
tangent = Vector((-outward.y, outward.x, 0))
for name in ['deck_railing_b', 'deck_parapet_b', 'deck_lantern_posts_b', 'deck_lantern_glass_b']:
    ob = bpy.data.objects[name]
    ob.data = ob.data.copy()
    bm = bmesh.new(); bm.from_mesh(ob.data)
    remove = []
    for face in bm.faces:
        points = [ob.matrix_world @ v.co - origin for v in face.verts]
        if any(p.dot(outward) > 2.45 and abs(p.dot(tangent)) < .49 for p in points): remove.append(face)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
# Retain all unused pillars as hidden editable geometry.
for name in ['island_pillar', 'island_pillar_large', 'island_pillar_huge']:
    ob = bpy.data.objects.get(name)
    if ob:
        for item in [ob, *ob.children_recursive]:
            item.hide_set(True); item.hide_render = True
bpy.data.collections['deck_huge'].hide_viewport = True
bpy.data.collections['deck_huge'].hide_render = True
scene['three_island_layout'] = True
scene['station_layout'] = 'About Me — Projects — Experiences'
bpy.context.view_layer.update()
# Keep a named camera and viewport framing that show all three islands.
cam = bpy.data.objects.get('station_three_islands_camera')
if cam is None:
    cam = bpy.data.objects.new('station_three_islands_camera', bpy.data.cameras.new('station_three_islands_camera'))
    scene.collection.objects.link(cam)
target = origin + Vector((0, 0, 4.5))
cam.location = origin + Vector((-17.5, -23.62, 24.5))
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 25
scene.camera = cam
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        region = area.spaces.active.region_3d
        region.view_rotation = cam.rotation_euler.to_quaternion()
        region.view_location = target
        region.view_distance = 28
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'base.blend'))
result = {'experience':list(experience.matrix_world.translation), 'about':list(about.matrix_world.translation), 'copied_objects':len(copies), 'angle':angle}
