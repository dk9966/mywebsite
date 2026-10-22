"""Keep the forward rock clear of the existing adjustable circular light."""
import bpy
from mathutils import Vector
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
mod=w.modifiers['Upper right | continuous forward rock fit']
g=mod.node_group;n,l=g.nodes,g.links
root=bpy.data.objects['Lower | circular roof assembly']
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
if not n.get('Forward fit | fixture clearance'):
    inputs={}
    for name,control,offset in [('Fixture top','Light height above walls (m)',root['wall_top_world_z']+.16),('Fixture radius','Light radius (m)',.10)]:
        socket=g.interface.new_socket(name=name,in_out='INPUT',socket_type='NodeSocketFloat')
        source=next(s.identifier for s in cm.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==control)
        mod[socket.identifier]=cm[source]+offset
        d=mod.driver_add('["'+socket.identifier+'"]').driver;d.type='SCRIPTED';d.expression='v+'+repr(offset)
        v=d.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='modifiers["Scene Sliders"]["'+source+'"]'
        inputs[name]=socket.identifier
    gi=next(v for v in n if v.bl_idname=='NodeGroupInput');go=next(v for v in n if v.bl_idname=='NodeGroupOutput')
    previous=go.inputs['Geometry'].links[0].from_socket
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
    weight=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('DIVIDE',mathnode('SUBTRACT',mathnode('ADD',gi.outputs['Fixture radius'],.20),radius),.16),0.),1.)
    low=mathnode('GREATER_THAN',xyz.outputs['Z'],root['wall_top_world_z']-.03)
    lift=mathnode('MULTIPLY',mathnode('MAXIMUM',mathnode('SUBTRACT',gi.outputs['Fixture top'],xyz.outputs['Z']),0.),mathnode('MULTIPLY',weight,low))
    vec=n.new('ShaderNodeCombineXYZ');l.new(lift,vec.inputs['Z'])
    sp=n.new('GeometryNodeSetPosition');sp.name='Forward fit | fixture clearance'
    l.new(previous,sp.inputs['Geometry']);l.new(vec.outputs[0],sp.inputs['Offset']);l.new(sp.outputs[0],go.inputs['Geometry'])
    ctrl.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
result={'native_light_clearance':True}
