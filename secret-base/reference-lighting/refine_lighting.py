"""Camera-reviewed refinements to the reference lighting rig."""
import bpy
from mathutils import Vector
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')

def watts(name, value):
    o = bpy.data.objects[name]
    fc = o.data.animation_data.drivers.find('energy')
    fc.driver.expression = str(value) + '*' + '*'.join(fc.driver.expression.split('*')[1:])
    o['Calibrated power W'] = value
    return o

rear = watts('RL | Rear left | soft overhead spot', 950)
rear.location.z = 3.15
rear.data.animation_data.drivers.find('spot_size').driver.expression = 'min(3.10,1.8325957146*w)'
for side in [-1, 1]:
    o = bpy.data.objects[f'RL | Rear left | soft fill {side:+d}']
    o.location.z = 2.55

watts('RL | Center | soft overhead spot', 4500)
for side in [-1, 1]:
    o = watts(f'RL | Center | soft fill {side:+d}', 650)
    o.location = (side*2.6, 5.0, 4.5)
    o.rotation_euler = (-o.location).to_track_quat('-Z', 'Y').to_euler()
    o.data.size = 5.0
    watts(f'RL | Upper right | soft fill {side:+d}', 100)
    watts(f'RL | Lower right | soft fill {side:+d}', 90)
    watts(f'RL | Front left | soft overhead spot {side:+d}', 1200)
    watts(f'RL | Front left | soft fill {side:+d}', 120)
watts('RL | Upper right | soft overhead spot', 900)
watts('RL | Lower right | soft overhead spot', 1050)

bpy.data.objects['LIGHTING CONTROLS'].update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-02.blend'), copy=True)
result = {'candidate': str(P/'candidate-02.blend')}
