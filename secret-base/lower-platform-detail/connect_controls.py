"""Keep the newly connected rails and bridge responsive to existing controls."""
import bpy,math
from mathutils import Vector
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
S=bpy.context.scene;ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
w0=float(cm['Socket_7']);h0=float(cm['Socket_3'])
g=bpy.data.node_groups.new('Lower bridge | preserve live connections','GeometryNodeTree')
g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
rd=g.interface.new_socket(name='Main radial shift',in_out='INPUT',socket_type='NodeSocketFloat')
hs=g.interface.new_socket(name='Railing height delta',in_out='INPUT',socket_type='NodeSocketFloat')
nodes=g.nodes;links=g.links
gi=nodes.new('NodeGroupInput');go=nodes.new('NodeGroupOutput');pos=nodes.new('GeometryNodeInputPosition')
weight=nodes.new('GeometryNodeInputNamedAttribute');weight.data_type='FLOAT';weight.inputs['Name'].default_value='main_connection'
height=nodes.new('GeometryNodeInputNamedAttribute');height.data_type='FLOAT';height.inputs['Name'].default_value='rail_height'
xy=nodes.new('ShaderNodeVectorMath');xy.operation='MULTIPLY';xy.inputs[1].default_value=(1,1,0);links.new(pos.outputs[0],xy.inputs[0])
unit=nodes.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';links.new(xy.outputs[0],unit.inputs[0])
amount=nodes.new('ShaderNodeMath');amount.operation='MULTIPLY';links.new(weight.outputs['Attribute'],amount.inputs[0]);links.new(gi.outputs['Main radial shift'],amount.inputs[1])
rad=nodes.new('ShaderNodeVectorMath');rad.operation='SCALE';links.new(unit.outputs[0],rad.inputs[0]);links.new(amount.outputs[0],rad.inputs['Scale'])
dz=nodes.new('ShaderNodeMath');dz.operation='MULTIPLY';links.new(height.outputs['Attribute'],dz.inputs[0]);links.new(gi.outputs['Railing height delta'],dz.inputs[1])
z=nodes.new('ShaderNodeCombineXYZ');links.new(dz.outputs[0],z.inputs['Z'])
add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';links.new(rad.outputs[0],add.inputs[0]);links.new(z.outputs[0],add.inputs[1])
sp=nodes.new('GeometryNodeSetPosition');links.new(gi.outputs['Geometry'],sp.inputs['Geometry']);links.new(add.outputs[0],sp.inputs['Offset']);links.new(sp.outputs[0],go.inputs['Geometry'])
d=Vector((1,-.625,0)).normalized();n=Vector((-d.y,d.x,0));t=math.sqrt(3.620207**2-.67**2)
objects=list(bpy.data.collections['158 | Connected bridge and railings'].objects)+list(bpy.data.collections['159 | Hidden architectural cutters'].objects)
for ob in objects:
    if ob.type!='MESH':continue
    wa=ob.data.attributes.new('main_connection','FLOAT','POINT')
    ha=ob.data.attributes.new('rail_height','FLOAT','POINT')
    ismain='main rim' in ob.name or 'gate aperture' in ob.name
    israil=any(k in ob.name for k in ['rail','stanchion','main rim']) and 'base shoe' not in ob.name
    for i,v in enumerate(ob.data.vertices):
        sx=t*d.x+v.co.dot(n)*n.x
        weight=1 if ismain else min(1,max(0,(4.621191-v.co.x)/max(.01,4.621191-sx)))
        wa.data[i].value=weight
        level=6.824491024+(6.871178627-6.824491024)*weight
        ha.data[i].value=max(0,v.co.z-level) if israil else 0
    mod=ob.modifiers.new('Follow main width and railing height','NODES');mod.node_group=g
    mod[rd.identifier]=0.;mod[hs.identifier]=0.
    for socket,key,expr in [(rd.identifier,'Socket_7',f'(v-{w0:.12f})*{3.271620750427246*1.0848522186279297:.12f}'),(hs.identifier,'Socket_3',f'v/{h0:.12f}-1')]:
        driver=mod.driver_add('["'+socket+'"]').driver;driver.expression=expr
        var=driver.variables.new();var.name='v';var.type='SINGLE_PROP';var.targets[0].id=ctrl;var.targets[0].data_path='modifiers["Scene Sliders"]["'+key+'"]'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/platform-controls/cave-platform-sliders.blend',compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'detailed-workshop.blend'),copy=True,compress=True)
result={'connected_objects':len(objects),'preserved_width':w0,'preserved_railing_size':h0}
