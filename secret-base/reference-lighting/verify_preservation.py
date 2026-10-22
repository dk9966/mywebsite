"""Independently reopen before/after files and check the lighting-only scope."""
import bpy
import array
import hashlib
import json
from pathlib import Path
import sys

P = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
target = args[0] if args else str(P.parent/'platform-controls/cave-platform-sliders.blend')
baseline = args[1] if len(args)>1 else str(P/'before-reference-lighting.blend')

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    bpy.context.view_layer.update()
    objects = {}
    meshes = {}
    for o in bpy.context.scene.objects:
        if o.type == 'LIGHT' or o.name.startswith('RL |') or o.name == 'LIGHTING CONTROLS':
            continue
        content = [o.type, [list(row) for row in o.matrix_world], o.hide_render,
                   [(m.name, m.type) for m in o.modifiers]]
        if o.type == 'MESH':
            if o.data.name not in meshes:
                digest = hashlib.sha256()
                for items, field, count, typecode in [(o.data.vertices, 'co', 3, 'f'), (o.data.loops, 'vertex_index', 1, 'i'), (o.data.polygons, 'material_index', 1, 'i')]:
                    values = array.array(typecode, [0]) * (len(items)*count)
                    items.foreach_get(field, values)
                    digest.update(values.tobytes())
                meshes[o.data.name] = digest.hexdigest()
            content += [meshes[o.data.name], [m.name if m else '' for m in o.data.materials]]
        objects[o.name] = hashlib.sha256(json.dumps(content).encode()).hexdigest()
    materials = {}
    for m in bpy.data.materials:
        if not m.use_nodes or m.name == 'Bays | dry cave haze' or m.name.startswith('RL mist |'):
            continue
        entries = []
        for n in m.node_tree.nodes:
            values = []
            for socket in n.inputs:
                if not hasattr(socket, 'default_value'):
                    continue
                value = socket.default_value
                if not isinstance(value, (str, int, float, bool)):
                    try: value = list(value)
                    except TypeError: value = str(value)
                values.append((socket.identifier, value))
            entries.append((n.name, n.type, values))
        links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in m.node_tree.links)
        materials[m.name] = hashlib.sha256(json.dumps((entries, links)).encode()).hexdigest()
    camera = bpy.context.scene.camera
    return objects, {'name': camera.name, 'lens': camera.data.lens, 'matrix': [list(r) for r in camera.matrix_world]}, materials

before, cam_before, mats_before = snapshot(baseline)
after, cam_after, mats_after = snapshot(target)
changed = [n for n in before if before[n] != after.get(n)]
added = sorted(set(after)-set(before))
changed_materials = [n for n in mats_before if mats_before[n] != mats_after.get(n)]
invalid = []
for data in list(bpy.data.objects)+list(bpy.data.lights)+list(bpy.data.node_groups)+[m.node_tree for m in bpy.data.materials if m.use_nodes]:
    if data.animation_data:
        invalid += [(data.name, f.data_path) for f in data.animation_data.drivers if not f.driver.is_valid]

pairs = []
for o in bpy.data.collections['180 | Reference soft spotlight lighting'].objects:
    if o.type != 'LIGHT' or not o.name.endswith('-1'):
        continue
    other = bpy.data.objects.get(o.name[:-2]+'+1')
    if not other:
        continue
    error_x = max(abs(o.location.x+other.location.x), abs(o.location.y-other.location.y), abs(o.location.z-other.location.z))
    error_y = max(abs(o.location.x-other.location.x), abs(o.location.y+other.location.y), abs(o.location.z-other.location.z))
    error = min(error_x, error_y)
    pairs.append({'pair': o.name[:-2].strip(), 'position_symmetry_error': error,
                  'power_difference': abs(o.data.energy-other.data.energy),
                  'color_difference': max(abs(a-b) for a,b in zip(o.data.color,other.data.color))})

controller = bpy.data.objects['LIGHTING CONTROLS']
ids = json.loads(controller['socket_ids'])
mod = controller.modifiers['Reference Lighting']
spot = bpy.data.objects['RL | Center | soft overhead spot'].data
energy = spot.energy
mod[ids['Master brightness']] = 1.25
controller.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
master_ratio = spot.energy/energy
mod[ids['Master brightness']] = 1.
mod[ids['Spot edge softness']] = .72
controller.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
blend = spot.spot_blend
report = {'file': target, 'existing_non_light_objects_checked': len(before),
          'changed_existing_geometry_or_transforms': changed, 'unexpected_objects': added,
          'camera_unchanged': cam_before == cam_after, 'invalid_drivers': invalid,
          'changed_surface_materials': changed_materials,
          'master_brightness_test_ratio': master_ratio, 'softness_test_value': blend,
          'mirrored_light_pairs': pairs}
report['passed'] = not changed and not added and not invalid and not changed_materials and cam_before == cam_after and abs(master_ratio-1.25)<1e-5 and abs(blend-.72)<1e-5 and all(p['position_symmetry_error']<1e-5 and p['power_difference']<1e-5 and p['color_difference']<1e-5 for p in pairs)
(P/'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
assert report['passed'], report
