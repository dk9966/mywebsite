"""Lift the cave and connecting structures while preserving the soft spotlight hierarchy."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
S = bpy.context.scene
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-environment-lift.blend'), copy=True, compress=True)
ctrl = bpy.data.objects['LIGHTING CONTROLS']
mod = ctrl.modifiers['Reference Lighting']
ids = json.loads(ctrl['socket_ids'])
col = bpy.data.collections['180 | Reference soft spotlight lighting']
parent = bpy.data.objects['RL | Cave | move lighting group']

# The existing rock fill remains directional; large camera-side sources fill its deep gaps.
mod[ids['Cave ambience']] = 1.8
mod[ids['Soft fill']] = 1.08
mod[ids['Spot edge softness']] = .92
mod[ids['Beam width']] = 1.04
mod[ids['Beam visibility']] = .9

for side in [-1, 1]:
    d = bpy.data.lights.new(f'RL | Cave | broad environment fill {side:+d}', 'AREA')
    o = bpy.data.objects.new(d.name, d)
    col.objects.link(o)
    o.parent = parent
    o.location = (side*6.5, -10., 10.5)
    target = Vector((side*3., 6., 7.))
    o.rotation_euler = (target-o.location).to_track_quat('-Z', 'Y').to_euler()
    d.shape = 'DISK'
    d.size = 12.
    d.color = (.56,.76,1.)
    d.volume_factor = .035
    d.specular_factor = .3
    o['Base power (W)'] = 620.
    o['Lighting role'] = 'Broad symmetric environment fill for rock, bridges, rails, and supports; preserves the spotlight pools.'
    o.id_properties_ui('Base power (W)').update(min=0., soft_min=0., soft_max=2500., description='Base fill power before Cave ambience multiplier. Keep mirrored partners equal.')
    fc = d.driver_add('energy')
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = 'p*a'
    for alias, obj, path in [('p',o,'["Base power (W)"]'),('a',ctrl,f'modifiers["Reference Lighting"]["{ids["Cave ambience"]}"]')]:
        v=fc.driver.variables.new();v.name=alias;v.type='SINGLE_PROP';v.targets[0].id=obj;v.targets[0].data_path=path
    for i in range(3):
        fc=d.driver_add('color',i);fc.driver.type='SCRIPTED';fc.driver.expression='c'
        v=fc.driver.variables.new();v.name='c';v.type='SINGLE_PROP';v.targets[0].id=ctrl
        v.targets[0].data_path=f'modifiers["Reference Lighting"]["{ids["Cool light tint"]}"][{i}]'

ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'environment-candidate.blend'), copy=True, compress=True)
result={'candidate':str(P/'environment-candidate.blend'),'ambient_multiplier':mod[ids['Cave ambience']], 'new_fill_power_each':bpy.data.objects['RL | Cave | broad environment fill +1'].data.energy}
