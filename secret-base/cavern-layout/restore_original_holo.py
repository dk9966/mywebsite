"""Restore the original base.blend hologram table in the satin cavern scene."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'base.blend'
SCENE = HERE / 'cavern-satin-lighting.blend'
OUTPUT = HERE / 'cavern-original-holo-table.blend'
ap = argparse.ArgumentParser()
ap.add_argument('--final', action='store_true')
ap.add_argument('--verify', action='store_true')
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--width', type=int, default=1400)
args = ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def mesh_hash(obj):
    h = hashlib.sha256()
    if obj.type == 'MESH':
        for prop, field, size, dtype in [('vertices', 'co', 3, np.float32), ('loops', 'vertex_index', 1, np.int32), ('polygons', 'material_index', 1, np.int32)]:
            data = getattr(obj.data, prop)
            values = np.empty(len(data)*size, dtype=dtype)
            data.foreach_get(field, values)
            h.update(values.tobytes())
    return h.hexdigest()


def value(v):
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    if isinstance(v, bpy.types.ID):
        return {'type': v.bl_rna.identifier, 'name': v.name}
    try:
        return [value(x) for x in v]
    except TypeError:
        return str(v)


def shader_hash(obj):
    result = []
    if not hasattr(obj.data, 'materials'):
        return ''
    for material in obj.data.materials:
        if not material:
            result.append(None)
            continue
        nodes = {n.name: {'type': n.bl_idname, 'inputs': {s.identifier: value(s.default_value) for s in n.inputs if hasattr(s, 'default_value')}} for n in material.node_tree.nodes}
        links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in material.node_tree.links)
        result.append({'nodes': nodes, 'links': links})
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()


def object_hash(obj):
    h = hashlib.sha256(np.array(obj.matrix_world, dtype=np.float64).tobytes())
    h.update(mesh_hash(obj).encode())
    h.update(shader_hash(obj).encode())
    h.update(str(obj.hide_render).encode())
    return h.hexdigest()


def original_parts():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.view_layer.update()
    collection = bpy.data.collections['about_holo_table']
    objects = sorted(collection.all_objects, key=lambda o: o.name)
    points = [o.matrix_world @ v.co for o in objects if o.type == 'MESH' for v in o.data.vertices]
    center = Vector(((min(p.x for p in points)+max(p.x for p in points))/2, (min(p.y for p in points)+max(p.y for p in points))/2, min(p.z for p in points)))
    radius = max((p-center).xy.length for p in points)
    parts = {o.name: {'world': [list(row) for row in o.matrix_world], 'mesh': mesh_hash(o), 'shader': shader_hash(o), 'modifiers': [(m.name, m.type) for m in o.modifiers]} for o in objects}
    return parts, center, radius


parts, original_center, original_radius = original_parts()
bpy.ops.wm.open_mainfile(filepath=str(SCENE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
bpy.context.view_layer.update()
old_table = [o for o in scene.objects if o.name.startswith('Holo table |')]
assert old_table, 'Current table assembly was not found'
removed_names = sorted(o.name for o in old_table)
preserved = {o.name: object_hash(o) for o in scene.objects if o not in old_table}
frame = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
inverse = frame.inverted()
points = [inverse @ (o.matrix_world @ v.co) for o in old_table if o.type == 'MESH' for v in o.data.vertices]
target = Vector(((min(p.x for p in points)+max(p.x for p in points))/2, (min(p.y for p in points)+max(p.y for p in points))/2, 6.016))
target_radius = max((p-target).xy.length for p in points)
scale = target_radius / original_radius
transform = frame @ Matrix.Translation(target) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-original_center)


def verify_parts():
    found = {o.get('original_holo_source'): o for o in bpy.context.scene.objects if o.get('original_holo_source')}
    errors = []
    for name, source in parts.items():
        obj = found.get(name)
        if obj is None:
            errors.append(name + ': missing')
            continue
        if mesh_hash(obj) != source['mesh']:
            errors.append(name + ': source mesh changed')
        if shader_hash(obj) != source['shader']:
            errors.append(name + ': source shader changed')
        expected = transform @ Matrix(source['world'])
        if max(abs(obj.matrix_world[r][c] - expected[r][c]) for r in range(4) for c in range(4)) > 1e-5:
            errors.append(name + ': placement mismatch')
    return errors


if args.verify:
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
    bpy.context.view_layer.update()
    changed = [name for name, fingerprint in preserved.items() if name not in bpy.context.scene.objects or object_hash(bpy.data.objects[name]) != fingerprint]
    errors = verify_parts()
    leftovers = [name for name in removed_names if name in bpy.context.scene.objects]
    report = {'passed': not changed and not errors and not leftovers, 'preserved_scene_objects': len(preserved), 'changed_outside_table': changed, 'original_components': len(parts), 'table_errors': errors, 'replaced_table_leftovers': leftovers, 'source_sha256': hashlib.sha256(BASE.read_bytes()).hexdigest(), 'input_scene_sha256': hashlib.sha256(SCENE.read_bytes()).hexdigest(), 'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}
    (HERE/'holo-preservation.json').write_text(json.dumps(report, indent=2))
    print('HOLO_VERIFICATION', json.dumps(report), flush=True)
    assert report['passed'], report
    sys.exit(0)

for obj in old_table:
    # Only remove this scene's table; earlier source scenes remain available.
    for collection in list(obj.users_collection):
        if collection.name == 'Platform | About':
            collection.objects.unlink(obj)
assert not any(name in scene.objects for name in removed_names), 'Old table is still linked'

collection = bpy.data.collections.new('09 | Original base hologram table')
scene.collection.children.link(collection)
names = list(parts)
with bpy.data.libraries.load(str(BASE), link=False) as (source, destination):
    destination.objects = names.copy()
for name, obj in zip(names, destination.objects):
    assert obj is not None, name
    collection.objects.link(obj)
    obj.parent = None
    obj.matrix_world = transform @ Matrix(parts[name]['world'])
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
    obj['original_holo_source'] = name
    obj.name = 'Original holo | ' + name.removeprefix('aboutHolo_')
bpy.context.view_layer.update()
assert not verify_parts(), verify_parts()
assert preserved == {name: object_hash(bpy.data.objects[name]) for name in preserved}, 'An unrelated scene object changed'

detail = bpy.data.objects.new('Camera | Original hologram table close-up', bpy.data.cameras.new('Original hologram table close-up'))
scene.collection.objects.link(detail)
look_at = target + Vector((0, 0, .38))
detail.location = frame @ (look_at + Vector((0, -9, 5.7)))
detail.rotation_euler = (frame @ look_at - detail.location).to_track_quat('-Z', 'Y').to_euler()
detail.data.type = 'ORTHO'
detail.data.ortho_scale = 4.8

scene['round_table_source'] = str(BASE)
scene['round_table_original_components'] = len(parts)
scene['water_added'] = False
text = bpy.data.texts.get('restore_original_holo.py') or bpy.data.texts.new('restore_original_holo.py')
text.clear()
text.write(Path(__file__).read_text())
tag = 'holo' if args.final else 'holo-preview'
output = OUTPUT if args.final else HERE/'holo-preview.blend'
scene.camera = bpy.data.objects['Camera | reference composition' if args.final else 'Camera | Workshop and About']
scene.cycles.samples = args.samples
scene.render.resolution_x = args.width
scene.render.resolution_y = round(args.width * 927 / 1696) if args.final else args.width
scene.render.resolution_percentage = 100
scene.render.filepath = str(HERE/(tag+'-overview.png' if args.final else tag+'-about.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
bpy.ops.render.render(write_still=True)
if args.final:
    scene.camera = bpy.data.objects['Camera | Workshop and About']
    scene.cycles.samples = 64
    scene.render.resolution_x = scene.render.resolution_y = 1400
    scene.render.filepath = str(HERE/'holo-workshop-about.png')
    bpy.ops.render.render(write_still=True)
    scene.camera = detail
    scene.render.resolution_x = scene.render.resolution_y = 1400
    scene.render.filepath = str(HERE/'holo-table-closeup.png')
    bpy.ops.render.render(write_still=True)
    scene.camera = bpy.data.objects['Camera | reference composition']
    scene.cycles.samples = args.samples
    scene.render.resolution_x = args.width
    scene.render.resolution_y = round(args.width * 927 / 1696)
    scene.render.filepath = str(HERE/'holo-overview.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
audit = {'source': str(BASE), 'scene_input': str(SCENE), 'output': str(output), 'original_table_components': len(parts), 'source_meshes_and_shaders_preserved': True, 'uniform_scale_to_existing_footprint': scale, 'original_radius': original_radius, 'target_radius': target_radius, 'target_center': list(target), 'removed_table_objects': removed_names, 'other_scene_objects_preserved': len(preserved)}
(HERE/(tag+'-audit.json')).write_text(json.dumps(audit, indent=2))
print('HOLO_RESULT', json.dumps(audit), flush=True)
