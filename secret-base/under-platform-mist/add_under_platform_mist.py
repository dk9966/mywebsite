"""Subtle reference-blue atmosphere confined beneath the existing platforms."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
S = bpy.context.scene
assert '182 | Subtle under-platform mist' not in bpy.data.collections
ctrl = bpy.data.objects['LIGHTING CONTROLS']
mod = ctrl.modifiers['Reference Lighting']
ids = json.loads(ctrl['socket_ids'])
group = mod.node_group
for label, value, description in [
    ('Under-platform glow', 1.0, 'Faint blue reflected light in the chasm. 1 is the subtle reference setting; 0 disables it.'),
    ('Under-platform mist', 1.0, 'Soft, patchy atmosphere below the decks. Independent of overhead beam mist; 0 clears it.'),
]:
    socket = group.interface.new_socket(name=label, in_out='INPUT', socket_type='NodeSocketFloat')
    socket.default_value = value
    socket.min_value = 0.0
    socket.max_value = 3.0
    socket.description = description
    ids[label] = socket.identifier
    mod[socket.identifier] = value
ctrl['socket_ids'] = json.dumps(ids)
col = bpy.data.collections.new('182 | Subtle under-platform mist')
S.collection.children.link(col)

def drive(owner, prop, control, factor):
    d = owner.driver_add(prop).driver
    d.type = 'SCRIPTED'
    d.expression = f'{factor}*amount'
    v = d.variables.new()
    v.name = 'amount'
    v.type = 'SINGLE_PROP'
    v.targets[0].id = ctrl
    v.targets[0].data_path = f'modifiers["Reference Lighting"]["{ids[control]}"]'

def math_node(nodes, links, operation, a, b):
    n = nodes.new('ShaderNodeMath')
    n.operation = operation
    for i, value in enumerate((a, b)):
        if isinstance(value, (int, float)):
            n.inputs[i].default_value = value
        else:
            links.new(value, n.inputs[i])
    return n.outputs[0]

def mist(label, parent, center, dimensions, density):
    mat = bpy.data.materials.new('Under-platform mist | ' + label)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (900, 80)
    scatter = nodes.new('ShaderNodeVolumeScatter')
    scatter.location = (670, 80)
    scatter.inputs['Color'].default_value = (.48, .66, .83, 1)
    scatter.inputs['Anisotropy'].default_value = .18
    links.new(scatter.outputs[0], output.inputs['Volume'])
    tex = nodes.new('ShaderNodeTexCoord')
    tex.location = (-1100, 50)
    shift = nodes.new('ShaderNodeVectorMath')
    shift.operation = 'SUBTRACT'
    links.new(tex.outputs['Generated'], shift.inputs[0])
    shift.inputs[1].default_value = (.5, .5, .5)
    scale = nodes.new('ShaderNodeVectorMath')
    scale.operation = 'MULTIPLY'
    links.new(shift.outputs[0], scale.inputs[0])
    scale.inputs[1].default_value = (2, 2, 0)
    radius = nodes.new('ShaderNodeVectorMath')
    radius.operation = 'LENGTH'
    links.new(scale.outputs[0], radius.inputs[0])
    radial = nodes.new('ShaderNodeMapRange')
    radial.interpolation_type = 'SMOOTHERSTEP'
    radial.inputs['From Min'].default_value = .2
    radial.inputs['From Max'].default_value = 1.0
    radial.inputs['To Min'].default_value = 1.0
    radial.inputs['To Max'].default_value = 0.0
    links.new(radius.outputs['Value'], radial.inputs['Value'])
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    links.new(tex.outputs['Generated'], xyz.inputs[0])
    zmin = math_node(nodes, links, 'MINIMUM', xyz.outputs['Z'], math_node(nodes, links, 'SUBTRACT', 1.0, xyz.outputs['Z']))
    zfade = nodes.new('ShaderNodeMapRange')
    zfade.interpolation_type = 'SMOOTHERSTEP'
    zfade.inputs['From Min'].default_value = 0.0
    zfade.inputs['From Max'].default_value = .30
    links.new(zmin, zfade.inputs['Value'])
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.1
    noise.inputs['Detail'].default_value = 2.0
    noise.inputs['Roughness'].default_value = .6
    links.new(tex.outputs['Generated'], noise.inputs['Vector'])
    texture = nodes.new('ShaderNodeMapRange')
    texture.inputs['From Min'].default_value = .25
    texture.inputs['From Max'].default_value = .75
    texture.inputs['To Min'].default_value = .28
    texture.inputs['To Max'].default_value = 1.0
    links.new(noise.outputs['Fac'], texture.inputs['Value'])
    mask = math_node(nodes, links, 'MULTIPLY', radial.outputs['Result'], zfade.outputs['Result'])
    textured = math_node(nodes, links, 'MULTIPLY', mask, texture.outputs['Result'])
    density_node = nodes.new('ShaderNodeMath')
    density_node.name = 'Under-platform density'
    density_node.operation = 'MULTIPLY'
    links.new(textured, density_node.inputs[0])
    drive(density_node.inputs[1], 'default_value', 'Under-platform mist', density)
    links.new(density_node.outputs[0], scatter.inputs['Density'])
    # Data API avoids disturbing the user's active object and selection.
    mesh = bpy.data.meshes.new('Under-platform volume bounds | ' + label)
    verts = [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('UM | ' + label + ' | softly faded mist', mesh)
    col.objects.link(obj)
    obj.parent = parent
    obj.location = center
    obj.scale = dimensions
    obj.data.materials.append(mat)
    obj.display_type = 'WIRE'
    obj.hide_select = True
    obj['Role'] = 'Volume only; feathered boundaries and broad noise, confined below platform level.'
    return obj

def light(label, parent, location, target, power, size):
    data = bpy.data.lights.new('UM | ' + label + ' | dim reflected blue', 'AREA')
    obj = bpy.data.objects.new(data.name, data)
    col.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = (Vector(target)-Vector(location)).to_track_quat('-Z','Y').to_euler()
    data.shape = 'DISK'
    data.size = size
    data.color = (.35, .60, .85)
    data.diffuse_factor = .35
    data.specular_factor = .10
    data.volume_factor = 1.5
    drive(data, 'energy', 'Under-platform glow', power)
    obj['Role'] = 'Low-powered broad bounce; volume-biased to preserve dark supports and deck lighting.'
    obj['Base power W'] = power
    return obj

roots = {label: bpy.data.objects['RL | '+label+' | move lighting group'] for label in ('Center','Front left','Rear left','Lower right','Upper right')}
mist('Center chasm', roots['Center'], (0,0,-6.0), (17,17,11), .024)
mist('Front left chasm', roots['Front left'], (0,-1,-4.2), (10,17,8), .021)
mist('Rear left chasm', roots['Rear left'], (0,-2,-4.5), (9,10,8), .018)
mist('Lower right chasm', roots['Lower right'], (0,0,-7.5), (11,11,9), .022)
mist('Upper right recess', roots['Upper right'], (0,-.4,-3.2), (7.4,7.4,1.8), .012)

light('Center left depth', roots['Center'], (-5,-1,-5), (-1,2,-7), 120, 5.0)
light('Center right depth', roots['Center'], (5,-1,-5), (1,2,-7), 120, 5.0)
light('Front left depth', roots['Front left'], (3,-1,-3), (0,2,-5), 85, 4.0)
light('Rear left depth', roots['Rear left'], (0,-4,-3), (0,0,-5), 80, 4.0)
light('Lower right depth', roots['Lower right'], (0,-4,-6), (0,0,-8), 110, 4.5)
light('Upper right recess', roots['Upper right'], (0,-3,-3.1), (0,0,-3.4), 25, 3.0)

ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
S['under_platform_mist_revision'] = 'Subtle cool-blue chasm mist matched to the camera reference; 5 feathered local volumes and 6 dim reflected fills.'
text = bpy.data.texts.new('READ ME - Under-platform mist')
text.write('Select LIGHTING CONTROLS > Modifiers > Reference Lighting. Under-platform glow and Under-platform mist are independent native sliders. Both default to 1 for the subtle reference look; set either to 0 to disable it. All added objects live in 182 | Subtle under-platform mist. Complete pre-edit backup: '+str(P/'before-under-platform-mist.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-01.blend'), copy=True, compress=True)
result = {'candidate':str(P/'candidate-01.blend'),'new_objects':len(col.objects),'controls':['Under-platform glow','Under-platform mist']}
