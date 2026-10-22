"""Lighting-only rig for the current, saved cave camera. Native, persistent drivers."""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector, Matrix

P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
S = bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
assert 'LIGHTING CONTROLS' not in bpy.data.objects, 'Rig already exists'

col = bpy.data.collections.new('180 | Reference soft spotlight lighting')
S.collection.children.link(col)
controls = bpy.data.objects.new('LIGHTING CONTROLS', bpy.data.meshes.new('Lighting control - empty mesh'))
col.objects.link(controls)
controls.hide_render = True
controls['Instructions'] = 'Modifiers > Reference Lighting. Native drivers; no add-on or Python autorun needed. See READ ME - Reference Lighting.'
group = bpy.data.node_groups.new('Reference Lighting', 'GeometryNodeTree')
group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
gi = group.nodes.new('NodeGroupInput')
go = group.nodes.new('NodeGroupOutput')
group.links.new(gi.outputs['Geometry'], go.inputs['Geometry'])
mod = controls.modifiers.new('Reference Lighting', 'NODES')
mod.node_group = group
ids = {}
settings = [
    ('Master brightness', 1., 0., 4., 'Scales all platform keys and soft fills together.'),
    ('Center platform', 1., 0., 4., 'Brightness of the circular central platform.'),
    ('Rear left platform', 1., 0., 4., 'Brightness of the raised rear-left deck and stairs.'),
    ('Front left platform', 1., 0., 4., 'Brightness of the long lower-left platform.'),
    ('Upper right platform', 1., 0., 4., 'Brightness of the upper-right room.'),
    ('Lower right platform', 1., 0., 4., 'Brightness of the lower-right workshop.'),
    ('Spot edge softness', .88, 0., 1., 'Spot Blend. High values feather the pool and beam edge.'),
    ('Beam width', 1., .6, 1.35, 'Scales all calibrated cone angles. Wider pools are softer but less concentrated.'),
    ('Shadow softness', 1., .2, 3., 'Multiplies emitter radius. Higher values soften shadows.'),
    ('Soft fill', 1., 0., 3., 'Gentle paired area lights maintain readability outside the spotlight core.'),
    ('Cave ambience', 1., 0., 3., 'Restrained cool rock illumination, independent of the platform keys.'),
    ('Haze density', .006, 0., .025, 'World-scale atmospheric density. Too much flattens contrast.'),
    ('Warm accents', .5, 0., 2., 'Small existing amber markers; keep subordinate to the cool pools.'),
]
for name, value, low, high, desc in settings:
    socket = group.interface.new_socket(name=name, in_out='INPUT', socket_type='NodeSocketFloat')
    socket.default_value = value
    socket.min_value = low
    socket.max_value = high
    socket.description = desc
    ids[name] = socket.identifier
    mod[socket.identifier] = value
socket = group.interface.new_socket(name='Cool light tint', in_out='INPUT', socket_type='NodeSocketColor')
socket.default_value = (.56, .76, 1., 1.)
socket.description = 'Shared color of all platform keys and fills.'
ids[socket.name] = socket.identifier
mod[socket.identifier] = (.56, .76, 1., 1.)
controls['socket_ids'] = json.dumps(ids)

def drive(owner, path, variables, expression, index=None):
    try:
        owner.driver_remove(path) if index is None else owner.driver_remove(path, index)
    except (TypeError, RuntimeError):
        pass
    fc = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    d = fc.driver
    d.type = 'SCRIPTED'
    for alias, key in variables.items():
        var = d.variables.new()
        var.name = alias
        var.type = 'SINGLE_PROP'
        var.targets[0].id = controls
        suffix = ''
        if isinstance(key, tuple):
            key, component = key
            suffix = f'[{component}]'
        var.targets[0].data_path = f'modifiers["Reference Lighting"]["{ids[key]}"]{suffix}'
    d.expression = expression

def power(light, watts, zone=None, fill=False, ambience=False, warm=False):
    variables = {'m': 'Master brightness'}
    expression = f'{watts:.8f}*m'
    if zone:
        variables['z'] = zone
        expression += '*z'
    if fill:
        variables['f'] = 'Soft fill'
        expression += '*f'
    if ambience:
        variables = {'a': 'Cave ambience'}
        expression = f'{watts:.8f}*a'
    if warm:
        variables = {'w': 'Warm accents'}
        expression = f'{watts:.8f}*w'
    drive(light, 'energy', variables, expression)

# Retain old lights and their transforms for reversibility; disable competing rigs.
old = []
for o in list(S.objects):
    if o.type != 'LIGHT':
        continue
    d = o.data
    old.append({'name': o.name, 'hide_render': o.hide_render, 'hide_viewport': o.hide_viewport, 'energy': d.energy, 'color': list(d.color)})
    o['Reference lighting - previous render visibility'] = not o.hide_render
    if o.hide_render or any(c.hide_render for c in o.users_collection):
        continue
    warm = d.color.r > d.color.b * 1.5
    if warm:
        power(d, d.energy, warm=True)
        d.volume_factor = 0.
    elif 'wall wash' in o.name and o.name.startswith('Lower |'):
        power(d, 12., 'Lower right platform', fill=True)
        d.color = (.56, .76, 1.)
        d.volume_factor = 0.
    elif o.name == 'Holo table | soft glass glow':
        power(d, 4., 'Lower right platform')
        d.volume_factor = 0.
    else:
        o.hide_render = True
        o.hide_viewport = True
(P / 'previous-light-settings.json').write_text(json.dumps(old, indent=2))

def root(name, center, angle=0., follow=None):
    o = bpy.data.objects.new('RL | ' + name + ' | move lighting group', None)
    col.objects.link(o)
    o.empty_display_type = 'CIRCLE'
    o.empty_display_size = .6
    o.location = center
    o.rotation_euler.z = angle
    if follow:
        c = o.constraints.new('COPY_LOCATION')
        c.target = bpy.data.objects[follow]
    return o

def light(name, kind, parent, position, target, watts, zone=None, size=1., angle=90., fill=False, ambience=False):
    d = bpy.data.lights.new('RL | ' + name, kind)
    o = bpy.data.objects.new(d.name, d)
    col.objects.link(o)
    o.parent = parent
    o.location = position
    o.rotation_euler = (Vector(target) - Vector(position)).to_track_quat('-Z', 'Y').to_euler()
    power(d, watts, zone, fill, ambience)
    d.color = (.56, .76, 1.)
    for i in range(3):
        drive(d, 'color', {'c': ('Cool light tint', i)}, 'c', i)
    d.volume_factor = 1.4 if kind == 'SPOT' else 0.
    if kind == 'SPOT':
        drive(d, 'spot_blend', {'b': 'Spot edge softness'}, 'b')
        drive(d, 'spot_size', {'w': 'Beam width'}, f'min(3.10,{math.radians(angle):.10f}*w)')
        drive(d, 'shadow_soft_size', {'r': 'Shadow softness'}, f'{size:.6f}*r')
        d.show_cone = True
    elif kind == 'AREA':
        d.shape = 'DISK'
        d.size = size
    o['Lighting role'] = 'Feathered overhead pool and visible soft beam' if kind == 'SPOT' else 'Soft reflection and shadow fill'
    o['Calibrated power W'] = watts
    return o

# Local X is the left/right symmetry axis of each platform. Paired lights are exact mirrors.
center = root('Center', (21.3, 0., 6.871), -.563316)
light('Center | soft overhead spot', 'SPOT', center, (0, 0, 7.0), (0, 0, 0), 2200, 'Center platform', .65, 87)
for side in [-1, 1]:
    light(f'Center | soft fill {side:+d}', 'AREA', center, (side*2.7, -.6, 4.8), (0, 0, 0), 135, 'Center platform', 4.0, fill=True)

rear = root('Rear left', (17.34, 14.42, 8.7), .24691)
light('Rear left | soft overhead spot', 'SPOT', rear, (0, -.6, 4.7), (0, -.6, 0), 1350, 'Rear left platform', .55, 84)
for side in [-1, 1]:
    light(f'Rear left | soft fill {side:+d}', 'AREA', rear, (side*1.65, -1.2, 3.3), (0, -.6, 0), 85, 'Rear left platform', 2.8, fill=True)
light('Rear left | stair spill', 'AREA', rear, (0, -3.0, 3.1), (0, -3.0, -1), 100, 'Rear left platform', 3.2, fill=True)

# Two overlapping pools along the long platform centerline keep both ends equally lit.
front = root('Front left', (11.38187, 3.63001, 2.537), .421328)
for side in [-1, 1]:
    light(f'Front left | soft overhead spot {side:+d}', 'SPOT', front, (0, side*3.1, 6.2), (0, side*3.1, 0), 1400, 'Front left platform', .7, 82)
    light(f'Front left | soft fill {side:+d}', 'AREA', front, (side*2.0, 0, 4.5), (0, 0, 0), 150, 'Front left platform', 4.5, fill=True)

for label, target_name, floor, watts, spread in [
    ('Upper right', 'Upper light | rectangular downlight', 11.589, 390, 130),
    ('Lower right', 'Lower | circular crown downlight', 6.82449, 520, 131),
]:
    source = bpy.data.objects[target_name]
    h = source.matrix_world.translation.z - floor - .06
    parent = root(label, source.matrix_world.translation, -.563316, follow=target_name)
    light(label+' | soft overhead spot', 'SPOT', parent, (0, 0, -.06), (0, 0, -h), watts, label+' platform', .30, spread)
    for side in [-1, 1]:
        light(f'{label} | soft fill {side:+d}', 'AREA', parent, (side*1.05, 0, -.16), (0, 0, -h), 38, label+' platform', 2.4, fill=True)

ambient = root('Cave', (21.3, 0, 0), -.563316)
light('Cave | restrained overhead fill', 'AREA', ambient, (0, 3, 16), (0, 1, 5), 260, size=7, ambience=True)
for side in [-1, 1]:
    light(f'Cave | soft side bounce {side:+d}', 'AREA', ambient, (side*8, -4, 7.5), (side*5, 3, 5), 110, size=6, ambience=True)

# Neutral-blue scattering reveals the soft cones without an all-over luminous fog.
haze = bpy.data.materials['Bays | dry cave haze']
for node in haze.node_tree.nodes:
    if node.type == 'PRINCIPLED_VOLUME':
        node.inputs['Color'].default_value = (.48, .61, .74, 1)
        node.inputs['Anisotropy'].default_value = .28
        drive(node.inputs['Density'], 'default_value', {'h': 'Haze density'}, 'h')

S.view_settings.view_transform = 'AgX'
S.view_settings.look = 'AgX - Medium High Contrast'
S.view_settings.exposure = .1
controls.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-01.blend'), copy=True)
result = {'lights_added': sum(o.type=='LIGHT' for o in col.objects), 'controls': list(ids), 'candidate': str(P/'candidate-01.blend')}
