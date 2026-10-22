"""Keep upper ceiling clearance after the shared terrain's topology modifiers."""
import bpy
from mathutils import Vector
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
ctrl=bpy.data.objects.get('UPPER PLATFORM SLIDERS') or bpy.data.objects['SCENE SLIDERS']
control=ctrl.modifiers.get('Upper Platform Sliders') or ctrl.modifiers['Scene Sliders']
H=deck['deck_height_m']
for key in terrain.data.shape_keys.key_blocks:
    if key.name.startswith('Upper gallery |'):key.mute=True
name='Upper gallery | light and lining ceiling clearance'
previous=terrain.modifiers.get(name)
if previous:
    oldgroup=previous.node_group
    terrain.modifiers.remove(previous)
    if oldgroup.users==0:bpy.data.node_groups.remove(oldgroup)
if True:
    group=bpy.data.node_groups.new(name,'GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    height=group.interface.new_socket(name='Light height',in_out='INPUT',socket_type='NodeSocketFloat');height.default_value=2.25
    n=group.nodes;l=group.links
    gi=n.new('NodeGroupInput');go=n.new('NodeGroupOutput');pos=n.new('GeometryNodeInputPosition')
    def mathnode(op,a,b=None):
        o=n.new('ShaderNodeMath');o.operation=op
        for i,value in enumerate([a,b]):
            if value is None:continue
            if isinstance(value,(int,float)):o.inputs[i].default_value=value
            else:l.new(value,o.inputs[i])
        return o.outputs[0]
    def smooth(value):
        x=mathnode('MINIMUM',mathnode('MAXIMUM',value,0),1)
        return mathnode('MULTIPLY',mathnode('MULTIPLY',x,x),mathnode('SUBTRACT',3,mathnode('MULTIPLY',2,x)))
    mx=deck.matrix_world.inverted()@terrain.matrix_world
    coords=[]
    for i in range(3):
        dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';l.new(pos.outputs[0],dot.inputs[0]);dot.inputs[1].default_value=tuple(mx[i][j] for j in range(3))
        coords.append(mathnode('ADD',dot.outputs['Value'],mx[i][3]))
    x=mathnode('ABSOLUTE',mathnode('ADD',coords[0],.15));y=mathnode('ABSOLUTE',coords[1]);z=mathnode('SUBTRACT',coords[2],H)
    xy=smooth(mathnode('DIVIDE',mathnode('SUBTRACT',4.05,mathnode('MAXIMUM',x,y)),.90))
    low=smooth(mathnode('DIVIDE',mathnode('SUBTRACT',z,1.32),.62))
    high=mathnode('SUBTRACT',1,smooth(mathnode('DIVIDE',mathnode('SUBTRACT',z,3.7),1.4)))
    weight=mathnode('MULTIPLY',mathnode('MULTIPLY',xy,low),high)
    amount=mathnode('ADD',.28,mathnode('MAXIMUM',0,mathnode('SUBTRACT',gi.outputs['Light height'],2.25)))
    lift=mathnode('MULTIPLY',weight,amount)
    scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[0].default_value=mx.inverted().to_3x3()@Vector((0,0,1));l.new(lift,scale.inputs['Scale'])
    # A shallow outward pocket lets the front-right wall return sit ahead of rock.
    px=mathnode('DIVIDE',mathnode('ABSOLUTE',mathnode('SUBTRACT',coords[0],2.90)),1.20)
    py=mathnode('DIVIDE',mathnode('ABSOLUTE',mathnode('ADD',coords[1],2.90)),1.20)
    pocketxy=smooth(mathnode('SUBTRACT',1,mathnode('MAXIMUM',px,py)))
    pocketz=mathnode('MULTIPLY',smooth(mathnode('DIVIDE',z,.22)),mathnode('SUBTRACT',1,smooth(mathnode('DIVIDE',mathnode('SUBTRACT',z,1.35),.85))))
    pocket=mathnode('MULTIPLY',.49,mathnode('MULTIPLY',pocketxy,pocketz))
    outward=n.new('ShaderNodeVectorMath');outward.operation='SCALE';outward.inputs[0].default_value=mx.inverted().to_3x3()@Vector((.70710678,-.70710678,0));l.new(pocket,outward.inputs['Scale'])
    total=n.new('ShaderNodeVectorMath');total.operation='ADD';l.new(scale.outputs['Vector'],total.inputs[0]);l.new(outward.outputs['Vector'],total.inputs[1])
    sp=n.new('GeometryNodeSetPosition');l.new(gi.outputs['Geometry'],sp.inputs['Geometry']);l.new(total.outputs['Vector'],sp.inputs['Offset']);l.new(sp.outputs[0],go.inputs['Geometry'])
    mod=terrain.modifiers.new(name,'NODES');mod.node_group=group;mod[height.identifier]=2.25
    ident=next(i.identifier for i in control.node_group.interface.items_tree if i.name=='Upper light height (m)')
    fc=mod.driver_add('["'+height.identifier+'"]');d=fc.driver;d.type='SCRIPTED';d.expression='h';v=d.variables.new();v.name='h';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='modifiers["'+control.name+'"]["'+ident+'"]'
    ctrl.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
    result={'modifier':name,'works_after_terrain_topology_changes':True}
