"""Softly bounded local mist reveals short overhead cones inside the platforms."""
import bpy
import json
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
ctrl = bpy.data.objects['LIGHTING CONTROLS']
ids = json.loads(ctrl['socket_ids'])
col = bpy.data.collections['180 | Reference soft spotlight lighting']

def mist(label, center, dims, density):
    mat = bpy.data.materials.new('RL mist | '+label)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    output = nodes.new('ShaderNodeOutputMaterial')
    scatter = nodes.new('ShaderNodeVolumeScatter')
    scatter.inputs['Color'].default_value = (.62,.76,.90,1.)
    scatter.inputs['Anisotropy'].default_value = .15
    links.new(scatter.outputs['Volume'],output.inputs['Volume'])
    tex = nodes.new('ShaderNodeTexCoord')
    shift = nodes.new('ShaderNodeVectorMath')
    shift.operation = 'SUBTRACT'
    links.new(tex.outputs['Generated'],shift.inputs[0])
    shift.inputs[1].default_value = (.5,.5,.5)
    flatten = nodes.new('ShaderNodeVectorMath')
    flatten.operation = 'MULTIPLY'
    links.new(shift.outputs[0],flatten.inputs[0])
    flatten.inputs[1].default_value = (2,2,0)
    radius = nodes.new('ShaderNodeVectorMath')
    radius.operation = 'LENGTH'
    links.new(flatten.outputs[0],radius.inputs[0])
    radial = nodes.new('ShaderNodeMapRange')
    radial.interpolation_type = 'SMOOTHERSTEP'
    radial.inputs['From Min'].default_value = .35
    radial.inputs['From Max'].default_value = 1.
    radial.inputs['To Min'].default_value = 1.
    radial.inputs['To Max'].default_value = 0.
    links.new(radius.outputs['Value'],radial.inputs['Value'])
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    links.new(tex.outputs['Generated'],xyz.inputs[0])
    invz = nodes.new('ShaderNodeMath');invz.operation='SUBTRACT';invz.inputs[0].default_value=1
    links.new(xyz.outputs['Z'],invz.inputs[1])
    zmin = nodes.new('ShaderNodeMath');zmin.operation='MINIMUM'
    links.new(xyz.outputs['Z'],zmin.inputs[0]);links.new(invz.outputs[0],zmin.inputs[1])
    zfade = nodes.new('ShaderNodeMapRange');zfade.interpolation_type='SMOOTHERSTEP'
    zfade.inputs['From Min'].default_value=0.;zfade.inputs['From Max'].default_value=.18
    links.new(zmin.outputs[0],zfade.inputs['Value'])
    mask=nodes.new('ShaderNodeMath');mask.operation='MULTIPLY'
    links.new(radial.outputs['Result'],mask.inputs[0]);links.new(zfade.outputs['Result'],mask.inputs[1])
    strength=nodes.new('ShaderNodeMath');strength.operation='MULTIPLY'
    links.new(mask.outputs[0],strength.inputs[0])
    driver=strength.inputs[1].driver_add('default_value').driver
    driver.type='SCRIPTED';driver.expression=f'{density}*b*h/0.0045'
    for alias,key in [('b','Beam visibility'),('h','Haze density')]:
        v=driver.variables.new();v.name=alias;v.type='SINGLE_PROP'
        v.targets[0].id=ctrl;v.targets[0].data_path=f'modifiers["Reference Lighting"]["{ids[key]}"]'
    links.new(strength.outputs[0],scatter.inputs['Density'])
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object;o.name='RL | '+label+' | soft local beam mist'
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o)
    o.parent=bpy.data.objects['RL | '+label+' | move lighting group']
    o.location=center;o.scale=dims;o.data.materials.append(mat)
    o.display_type='WIRE';o.hide_select=True
    o['Lighting role']='Volume only. Radial and vertical falloff; no visible solid surface. Beam visibility controls density.'

mist('Center',(0,0,3.5),(10.8,10.8,7.0),.013)
mist('Rear left',(0,-.5,1.58),(5.5,6.5,3.16),.027)
mist('Front left',(0,0,3.1),(8.,14.,6.2),.010)
mist('Upper right',(0,0,-1.12),(6.3,6.3,2.2),.020)
mist('Lower right',(0,0,-1.34),(7.5,7.5,2.62),.024)
for o in col.objects:
    if o.type=='LIGHT' and o.data.type=='SPOT':
        o.data.driver_remove('volume_factor')
        o.data.volume_factor=1.
ctrl.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-05.blend'),copy=True)
result={'candidate':str(P/'candidate-05.blend')}
