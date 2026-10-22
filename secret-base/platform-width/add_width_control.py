import bpy, math
from mathutils import Vector, Matrix
rig=bpy.data.objects['Rig | middle radius']
ctrl=bpy.data.objects['SCENE SLIDERS']; control=ctrl.modifiers['Scene Sliders']
assert not any(s.name=='Middle platform width' for s in control.node_group.interface.items_tree)
# Snapshot evaluated geometry, so a neutral control can be verified.
def points(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me=ev.to_mesh(); out=[ev.matrix_world@v.co for v in me.vertices]; ev.to_mesh_clear(); return out
meshes=[o for o in rig.children if o.type=='MESH']
before={o.name:points(o) for o in meshes}
s=control.node_group.interface.new_socket(name='Middle platform width',in_out='INPUT',socket_type='NodeSocketFloat')
s.default_value=1.; s.min_value=.5; s.max_value=2.; s.description='Deck width multiplier; attached details keep their size. Use the middle rig to move the assembly.'
control[s.identifier]=1.
source=control.path_from_id()+'["'+s.identifier+'"]'
def drive(owner,path,expr='w',index=None):
    f=owner.driver_add(path) if index is None else owner.driver_add(path,index)
    d=f.driver;d.type='SCRIPTED';d.expression=expr
    v=d.variables.new();v.name='w';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path=source

def group(mode):
    g=bpy.data.node_groups.new('Platform width | '+mode,'GeometryNodeTree')
    for name,typ,io in [('Geometry','NodeSocketGeometry','INPUT'),('Geometry','NodeSocketGeometry','OUTPUT'),('Width','NodeSocketFloat','INPUT'),('Center','NodeSocketVector','INPUT'),('Offset','NodeSocketVector','INPUT'),('Radius','NodeSocketFloat','INPUT')]:
        g.interface.new_socket(name=name,in_out=io,socket_type=typ)
    ids={s.name:s.identifier for s in g.interface.items_tree if s.in_out=='INPUT'}
    n=g.nodes; l=g.links; i=n.new('NodeGroupInput'); out=n.new('NodeGroupOutput'); pos=n.new('GeometryNodeInputPosition')
    def vm(op,a=None,b=None):
        x=n.new('ShaderNodeVectorMath');x.operation=op
        if a is not None:l.new(a,x.inputs[0])
        if b is not None:l.new(b,x.inputs[1])
        return x
    minus=n.new('ShaderNodeMath');minus.operation='SUBTRACT';l.new(i.outputs['Width'],minus.inputs[0]);minus.inputs[1].default_value=1.
    if mode=='detail': base=i.outputs['Offset']
    else:
        delta=vm('SUBTRACT',pos.outputs['Position'],i.outputs['Center'])
        xy=vm('MULTIPLY',delta.outputs[0]);xy.inputs[1].default_value=(1,1,0)
        if mode=='ring':
            unit=vm('NORMALIZE',xy.outputs[0]); rad=vm('SCALE',unit.outputs[0]);l.new(i.outputs['Radius'],rad.inputs['Scale']);base=rad.outputs[0]
        else:base=xy.outputs[0]
    off=vm('SCALE',base);l.new(minus.outputs[0],off.inputs['Scale'])
    sp=n.new('GeometryNodeSetPosition');l.new(i.outputs['Geometry'],sp.inputs['Geometry']);l.new(off.outputs[0],sp.inputs['Offset']);l.new(sp.outputs['Geometry'],out.inputs['Geometry'])
    return g,ids

groups={mode:group(mode) for mode in ['deck','ring','detail']}
counts={k:0 for k in groups}
for o in meshes:
    name=o.name.lower()
    detail=any(k in name for k in ['fastener','bolt','post','lamp','diffuser','reinforcement strap','service plate'])
    ring=any(k in name for k in ['guardrail','rolled rim','concentric machined trim'])
    mode='detail' if detail else ('ring' if ring else 'deck')
    g,ids=groups[mode]
    inv=o.matrix_world.inverted(); center=inv@rig.matrix_world.translation
    local=[inv@p for p in before[o.name]]
    pivot=Vector(tuple((min(p[a] for p in local)+max(p[a] for p in local))/2 for a in range(3)))
    offset=pivot-center;offset.z=0
    radii=[math.hypot(p.x-center.x,p.y-center.y) for p in local]
    mod=o.modifiers.new('Platform width — preserve detail size','NODES');mod.node_group=g
    mod[ids['Width']]=1.;mod[ids['Center']]=center;mod[ids['Offset']]=offset;mod[ids['Radius']]=(min(radii)+max(radii))/2
    drive(mod,'["'+ids['Width']+'"]')
    counts[mode]+=1
# Parent the console under the same movement control, keeping its world transform.
console=bpy.data.objects['Rig | table and machinery']
mw=console.matrix_world.copy();console.parent=rig;console.matrix_parent_inverse=Matrix.Identity(4);console.matrix_world=mw
for o in [console]+[x for x in rig.children if x.type=='LIGHT']:
    for a in [0,1]:drive(o,'location',repr(float(o.location[a]))+'*w',a)
ctrl.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
error=max((a-b).length for o in meshes for a,b in zip(before[o.name],points(o)))
rig['Width control']='SCENE SLIDERS > Modifiers > Middle platform width. 1.0 is the current width; G moves the assembly.'
# Show the requested slider without changing selection.
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type=='PROPERTIES':
            a.spaces.active.pin_id=ctrl;a.spaces.active.use_pin_id=True
            try:a.spaces.active.context='MODIFIER'
            except TypeError:pass
result={'counts':counts,'neutral_max_geometry_error':error,'socket':s.identifier}
