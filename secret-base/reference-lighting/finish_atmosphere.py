"""Visible, feathered shafts plus a restrained cave bounce; no new geometry."""
import bpy
import json
from mathutils import Vector
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
S = bpy.context.scene
ctrl = bpy.data.objects['LIGHTING CONTROLS']
mod = ctrl.modifiers['Reference Lighting']
group = mod.node_group
ids = json.loads(ctrl['socket_ids'])
socket = group.interface.new_socket(name='Beam visibility', in_out='INPUT', socket_type='NodeSocketFloat')
socket.default_value = 1.
socket.min_value = 0.
socket.max_value = 3.
socket.description = 'Scales spotlight contribution to the existing haze without changing surface brightness.'
ids['Beam visibility'] = socket.identifier
mod[socket.identifier] = 1.
ctrl['socket_ids'] = json.dumps(ids)
col = bpy.data.collections['180 | Reference soft spotlight lighting']

def variable(driver, alias, obj, path):
    v = driver.variables.new()
    v.name = alias
    v.type = 'SINGLE_PROP'
    v.targets[0].id = obj
    v.targets[0].data_path = path

for o in col.objects:
    if o.type != 'LIGHT' or o.data.type != 'SPOT':
        continue
    base = 2.8 if 'Center' in o.name else 5. if 'Rear left' in o.name else 2.4 if 'Front left' in o.name else 8.
    d = o.data.driver_add('volume_factor').driver
    d.type = 'SCRIPTED'
    d.expression = f'{base}*v'
    variable(d, 'v', ctrl, f'modifiers["Reference Lighting"]["{ids["Beam visibility"]}"]')

receivers = bpy.data.collections.new('RL receivers | Cave bounce')
for name in ['150 | continuous cave with oblique carved rooms', 'Central rock mound | continuous cross-column extrusions']:
    receivers.objects.link(bpy.data.objects[name])
parent = bpy.data.objects['RL | Cave | move lighting group']
for side in [-1, 1]:
    src = bpy.data.objects[f'RL | Cave | soft side bounce {side:+d}']
    o = src.copy()
    o.data = src.data.copy()
    o.name = f'RL | Cave | lower reflected bounce {side:+d}'
    col.objects.link(o)
    o.location = (side*4.5, -6, 3.5)
    o.rotation_euler = (Vector((side*2., 1, 3.5))-o.location).to_track_quat('-Z', 'Y').to_euler()
    o.data.size = 7.
    o.data.specular_factor = .3
    o.light_linking.receiver_collection = receivers
    o.data.animation_data.drivers.find('energy').driver.expression = '180*a'
    o['Calibrated power W'] = 180.
    o['Lighting role'] = 'Faint symmetric lower cave bounce, linked only to terrain'

# Expose an editable base power on every new light, while retaining shared controls.
for o in col.objects:
    if o.type != 'LIGHT':
        continue
    fc = o.data.animation_data.drivers.find('energy')
    pieces = fc.driver.expression.split('*')
    base = float(pieces[0])
    o['Base power (W)'] = base
    o.id_properties_ui('Base power (W)').update(min=0., soft_min=0., soft_max=max(1000.,base*3), description='Base lamp power before shared multipliers. Keep mirrored partners equal.')
    variable(fc.driver, 'p', o, '["Base power (W)"]')
    fc.driver.expression = 'p*' + '*'.join(pieces[1:])
    del o['Calibrated power W']

ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-04.blend'), copy=True)
result = {'candidate': str(P/'candidate-04.blend'), 'lights': sum(o.type=='LIGHT' for o in col.objects)}
