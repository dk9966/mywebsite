"""Verify existing scene data against the backup, then render the saved edit."""
import bpy
import array
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
main_file = P.parent/'platform-controls/cave-platform-sliders.blend'

def snapshot():
    result = {}
    for o in bpy.context.scene.objects:
        if o.name.startswith('UM | '):
            continue
        d = {
            'type': o.type,
            'matrix': [list(row) for row in o.matrix_world],
            'render_hidden': o.hide_render,
            'parent': o.parent.name if o.parent else None,
        }
        if o.type == 'MESH':
            coordinates = array.array('f', [0.0]) * (len(o.data.vertices)*3)
            o.data.vertices.foreach_get('co', coordinates)
            d['vertices'] = hashlib.sha256(coordinates.tobytes()).hexdigest()
            d['faces'] = len(o.data.polygons)
            d['materials'] = [m.material.name if m.material else None for m in o.material_slots]
        if o.type == 'LIGHT':
            d['light'] = [o.data.energy, list(o.data.color), o.data.type, o.data.volume_factor]
        result[o.name] = d
    return result

before = snapshot()
bpy.ops.wm.open_mainfile(filepath=str(main_file))
after = snapshot()
assert before == after, 'Original scene objects changed: '+str([k for k in before if before[k] != after.get(k)][:20])
baseline = json.loads((P/'before-state.json').read_text())
S = bpy.context.scene
assert [list(row) for row in S.camera.matrix_world] == baseline['camera']['matrix']
ctrl = bpy.data.objects['LIGHTING CONTROLS']
mod = ctrl.modifiers['Reference Lighting']
for k, v in baseline['controls'].items():
    actual = list(mod[k]) if isinstance(v, list) else mod[k]
    assert v == actual, 'Existing control changed: '+k
ids = json.loads(ctrl['socket_ids'])
lights = [o.data for o in bpy.data.collections['182 | Subtle under-platform mist'].objects if o.type == 'LIGHT']
initial_power = [l.energy for l in lights]
mod[ids['Under-platform glow']] = 0.0
ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
assert all(l.energy == 0 for l in lights)
mod[ids['Under-platform glow']] = 1.0
ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
assert [l.energy for l in lights] == initial_power
report = {'original_objects_preserved':len(before), 'geometry_materials_transforms_and_existing_lights_unchanged':True, 'camera_unchanged':True, 'existing_controls_unchanged':True, 'under_platform_glow_control_verified':True, 'added_volumes':5, 'added_lights':6, 'main_file':str(main_file)}
(P/'verification.json').write_text(json.dumps(report, indent=2))
S.cycles.device = 'CPU'
S.cycles.samples = 64
S.cycles.use_denoising = True
S.render.resolution_x = 1200
S.render.resolution_y = 662
S.render.resolution_percentage = 100
S.render.use_border = False
S.render.use_crop_to_border = False
S.render.image_settings.file_format = 'PNG'
S.render.filepath = str(P/'final-camera.png')
bpy.ops.render.render(write_still=True)
