import bpy
import json
from mathutils import Vector
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
col = bpy.data.collections['180 | Reference soft spotlight lighting']
ctrl = bpy.data.objects['LIGHTING CONTROLS']
ids = json.loads(ctrl['socket_ids'])

def watts(name, value):
    o = bpy.data.objects[name]
    fc = o.data.animation_data.drivers.find('energy')
    fc.driver.expression = str(value) + '*' + '*'.join(fc.driver.expression.split('*')[1:])
    o['Calibrated power W'] = value
    return o

# Restrict the center reflection cards to the platform, preventing bright spill on nearby rock/railings.
receivers = bpy.data.collections.new('RL receivers | Center reflection fill')
for name in ['02 | Machined rings and eight recessed grates', '03 | Uniform slender steel railings']:
    for o in bpy.data.collections[name].objects:
        if o.type == 'MESH' and o.name not in receivers.objects:
            receivers.objects.link(o)
for o in bpy.context.scene.objects:
    if o.name.startswith('deck_desk') and o.type=='MESH' and o.name not in receivers.objects:
        receivers.objects.link(o)
for side in [-1, 1]:
    o = watts(f'RL | Center | soft fill {side:+d}', 280)
    o.location = (side*1.65, 5.0, 4.5)
    o.rotation_euler = (-o.location).to_track_quat('-Z', 'Y').to_euler()
    o.data.size = 4.4
    o.light_linking.receiver_collection = receivers
watts('RL | Center | soft overhead spot', 3600).data.volume_factor = 1.1

def wall_fill(label, side, watts_value, target_z):
    src = bpy.data.objects[f'RL | {label} | soft fill {side:+d}']
    o = src.copy()
    o.data = src.data.copy()
    o.name = f'RL | {label} | wall bounce {side:+d}'
    col.objects.link(o)
    # Coordinates relative to the ceiling fixture; symmetry is retained in local X.
    o.location = (side*1.55, -1.4, -.6)
    target = Vector((side*.8, 1.6, target_z))
    o.rotation_euler = (target-o.location).to_track_quat('-Z', 'Y').to_euler()
    o.data.size = 2.5
    o['Lighting role'] = 'Symmetric soft room bounce; controlled by Soft fill'
    watts(o.name, watts_value)
    return o

for side in [-1, 1]:
    wall_fill('Upper right', side, 75, -1.1)
    wall_fill('Lower right', side, 45, -1.4)
    o = watts(f'RL | Upper right | soft fill {side:+d}', 140)
    o.location.y = .65
    o.rotation_euler = (Vector((0, 0, -2.2))-o.location).to_track_quat('-Z', 'Y').to_euler()
    watts(f'RL | Rear left | soft fill {side:+d}', 150)
watts('RL | Rear left | soft overhead spot', 1450)
watts('RL | Rear left | stair spill', 180)
watts('RL | Upper right | soft overhead spot', 1200)
ctrl.modifiers['Reference Lighting'][ids['Haze density']] = .0045
ctrl.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-03.blend'), copy=True)
result = {'candidate': str(P/'candidate-03.blend')}
