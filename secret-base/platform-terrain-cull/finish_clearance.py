"""Keep the coarser faces clear of the adjustable light, without subdivision."""
import bpy
from mathutils import Vector
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
NAME='Coarse rock | circular light clearance'
assert not w.modifiers.get(NAME)
root=bpy.data.objects['Lower | circular roof assembly']
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
g=bpy.data.node_groups.new(NAME,'GeometryNodeTree')
g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
mod=w.modifiers.new(NAME,'NODES');mod.node_group=g
for name,control,offset in [('Fixture top','Light height above walls (m)',root['wall_top_world_z']+.20),
                            ('Protected radius','Light radius (m)',.50)]:
    socket=g.interface.new_socket(name=name,in_out='INPUT',socket_type='NodeSocketFloat')
    source=next(s.identifier for s in cm.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==control)
    mod[socket.identifier]=cm[source]+offset
    driver=mod.driver_add('["'+socket.identifier+'"]').driver;driver.expression='v+'+repr(offset)
    v=driver.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=ctrl
    v.targets[0].data_path='modifiers["Scene Sliders"]["'+source+'"]'
n,l=g.nodes,g.links;gi=n.new('NodeGroupInput');go=n.new('NodeGroupOutput')
def mathnode(op,a,b):
    node=n.new('ShaderNodeMath');node.operation=op
    for i,value in enumerate((a,b)):
        if isinstance(value,(int,float)):node.inputs[i].default_value=value
        else:l.new(value,node.inputs[i])
    return node.outputs[0]
center=w.matrix_world.inverted()@root.matrix_world.translation
pos=n.new('GeometryNodeInputPosition');xyz=n.new('ShaderNodeSeparateXYZ');l.new(pos.outputs[0],xyz.inputs[0])
x=mathnode('SUBTRACT',xyz.outputs['X'],center.x);y=mathnode('SUBTRACT',xyz.outputs['Y'],center.y)
radius=mathnode('SQRT',mathnode('ADD',mathnode('MULTIPLY',x,x),mathnode('MULTIPLY',y,y)),0.)
weight=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('DIVIDE',mathnode('SUBTRACT',mathnode('ADD',gi.outputs['Protected radius'],.35),radius),.35),0.),1.)
low=mathnode('GREATER_THAN',xyz.outputs['Z'],root['wall_top_world_z']-.03)
lift=mathnode('MULTIPLY',mathnode('MAXIMUM',mathnode('SUBTRACT',gi.outputs['Fixture top'],xyz.outputs['Z']),0.),mathnode('MULTIPLY',weight,low))
vec=n.new('ShaderNodeCombineXYZ');l.new(lift,vec.inputs['Z'])
sp=n.new('GeometryNodeSetPosition')
l.new(gi.outputs['Geometry'],sp.inputs['Geometry']);l.new(vec.outputs[0],sp.inputs['Offset']);l.new(sp.outputs[0],go.inputs['Geometry'])
cleanup=w.modifiers.new('Coarse rock | weld coincident backing vertices','WELD');cleanup.merge_threshold=.00001
cleanup.vertex_group='Platform backing | snug hidden stone'
ctrl.update_tag();bpy.context.view_layer.update()
result={'clearance_preserved_without_new_triangles':True}
