"""Native Blender modifier sliders with persistent, expression-only drivers."""
import bpy,json,math,hashlib,array
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.871178627
TERRAIN=['150 | continuous cave with oblique carved rooms','Central rock mound | continuous cross-column extrusions']
def fingerprint(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        a=array.array('f',[0.])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P/'latest-live-sculpt.blend'))
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
(P/'live-source-hashes.json').write_text(json.dumps({o.name:fingerprint(o) for o in bpy.context.scene.objects}))
terrain_expected={n:[bpy.data.objects[n].matrix_world@v.co for v in bpy.data.objects[n].data.vertices] for n in TERRAIN}
terrain_matrices={n:bpy.data.objects[n].matrix_world.copy() for n in TERRAIN}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'platform-blockout/cave-octagon-platforms.blend'))
S=bpy.context.scene
with bpy.data.libraries.load(str(P/'latest-live-sculpt.blend'),link=False) as (src,dst):dst.objects=list(TERRAIN)
for name,imported in zip(TERRAIN,dst.objects):
    target=S.objects[name];target.data=imported.data;target.matrix_world=terrain_matrices[name]
    bpy.data.objects.remove(imported,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0
COL=bpy.data.collections.new('00 | Scene sliders');S.collection.children.link(COL)
RIG=bpy.data.collections.new('00 | Slider rig');S.collection.children.link(RIG)
def group(name,inputs):
    g=bpy.data.node_groups.new(name,'GeometryNodeTree');g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    sockets={}
    for name,typ,default,minimum,maximum,desc in inputs:
        s=g.interface.new_socket(name=name,in_out='INPUT',socket_type=typ);s.description=desc
        if typ=='NodeSocketFloat':s.default_value=default;s.min_value=minimum;s.max_value=maximum;s.subtype='FACTOR'
        elif typ=='NodeSocketVector':s.default_value=default
        elif typ=='NodeSocketBool':s.default_value=default
        sockets[name]=s.identifier
    a=g.nodes.new('NodeGroupInput');b=g.nodes.new('NodeGroupOutput');return g,a,b,sockets
mid0=2.806*1.2
lower=S.objects['Lower | plain octagon'];upper=S.objects['Upper | plain octagon - 90 percent radius']
low0=float(lower['circumradius']);up0=float(upper['circumradius'])
settings=[('Table & machinery size',.5,.1,2.,'Uniform size relative to the original console. Current half-size arrangement is 0.5.'),('Railing size',1.,.35,2.5,'Changes railing height and thickness while following the middle platform perimeter.'),('Middle radius (m)',mid0,1.,5.,'Middle deck radius in metres. Railing, console placement and bridge follow.'),('Lower radius (m)',low0,.5,5.,'Lower octagon circumradius in metres. Bridge end follows.'),('Upper radius (m)',up0,.5,5.,'Upper octagon circumradius in metres.')]
g,gi,go,ids=group('Scene Sliders',[(n,'NodeSocketFloat',v,lo,hi,d) for n,v,lo,hi,d in settings]);g.links.new(gi.outputs['Geometry'],go.inputs['Geometry'])
ctrl=bpy.data.objects.new('SCENE SLIDERS',bpy.data.meshes.new('Empty slider controller'));COL.objects.link(ctrl);ctrl.hide_render=True
control=ctrl.modifiers.new('Scene Sliders','NODES');control.node_group=g
for name,value,_,_,_ in settings:control[ids[name]]=value
ctrl['How to use']='Drag the five sliders in this pinned modifier panel. These controls and drivers are native to the blend file; no Python autorun or add-on is needed.'
def drive(owner,path,key,expression='v',index=None):
    fc=owner.driver_add(path) if index is None else owner.driver_add(path,index)
    d=fc.driver;d.type='SCRIPTED';d.expression=expression
    var=d.variables.new();var.name='v';var.type='SINGLE_PROP';var.targets[0].id=ctrl;var.targets[0].data_path='modifiers["Scene Sliders"]["'+ids[key]+'"]'
    return fc
def empty(name,matrix):
    o=bpy.data.objects.new(name,None);RIG.objects.link(o);o.matrix_world=matrix;o.empty_display_type='PLAIN_AXES';o.empty_display_size=.12;o.hide_render=True;return o
def parent_keep(ob,par):
    mw=ob.matrix_world.copy();ob.parent=par;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_world=mw
def refresh():
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
def evaluated_points(ob):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=[INV@(ev.matrix_world@v.co) for v in me.vertices];ev.to_mesh_clear();return p
def bounds(ob):
    p=evaluated_points(ob);return [max(v[i] for v in p)-min(v[i] for v in p) for i in range(3)]
samples=['Metal | continuous support drum','deck_desk_b',lower.name,upper.name,'Bridge | floating rectangle']
initial={n:bounds(S.objects[n]) for n in samples}

middle=empty('Rig | middle radius',FRAME)
for axis in [0,1]:drive(middle,'scale','Middle radius (m)',f'v/{mid0:.12f}',axis)
refresh()
for ob in list(bpy.data.collections['02 | Machined rings and eight recessed grates'].objects):parent_keep(ob,middle)

# All rails use a native geometry-node field: local bars grow around their
# footings, while full circular guardrails grow around their centre radius.
railg,ri,ro,rids=group('Railing height and thickness',[('Size','NodeSocketFloat',1.,.1,4.,''),('Pivot','NodeSocketVector',(0,0,F),0,0,''),('Circular','NodeSocketBool',False,0,0,''),('Radius','NodeSocketFloat',3.27,0,10,'')])
nodes=railg.nodes;links=railg.links
pos=nodes.new('GeometryNodeInputPosition');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(pos.outputs['Position'],sep.inputs[0])
xy=nodes.new('ShaderNodeCombineXYZ');links.new(sep.outputs['X'],xy.inputs['X']);links.new(sep.outputs['Y'],xy.inputs['Y'])
def vm(op,a=None,b=None):
    n=nodes.new('ShaderNodeVectorMath');n.operation=op
    if a is not None:links.new(a,n.inputs[0])
    if b is not None:links.new(b,n.inputs[1])
    return n
def mathnode(op,a=None,b=None,constant=None):
    n=nodes.new('ShaderNodeMath');n.operation=op
    if a is not None:links.new(a,n.inputs[0])
    if b is not None:links.new(b,n.inputs[1])
    elif constant is not None:n.inputs[1].default_value=constant
    return n
pivotxy=nodes.new('ShaderNodeVectorMath');pivotxy.operation='MULTIPLY';links.new(ri.outputs['Pivot'],pivotxy.inputs[0]);pivotxy.inputs[1].default_value=(1,1,0)
offset=vm('SUBTRACT',xy.outputs[0],pivotxy.outputs[0]);scaled=vm('SCALE',offset.outputs[0]);links.new(ri.outputs['Size'],scaled.inputs['Scale']);local=vm('ADD',scaled.outputs[0],pivotxy.outputs[0])
length=vm('LENGTH',xy.outputs[0]);radialoff=mathnode('SUBTRACT',length.outputs['Value'],ri.outputs['Radius']);radscale=mathnode('MULTIPLY',radialoff.outputs[0],ri.outputs['Size']);radius=mathnode('ADD',radscale.outputs[0],ri.outputs['Radius']);unit=vm('NORMALIZE',xy.outputs[0]);circular=vm('SCALE',unit.outputs[0]);links.new(radius.outputs[0],circular.inputs['Scale'])
switch=nodes.new('GeometryNodeSwitch');switch.input_type='VECTOR';links.new(ri.outputs['Circular'],switch.inputs['Switch']);links.new(local.outputs[0],switch.inputs['False']);links.new(circular.outputs[0],switch.inputs['True'])
zoff=mathnode('SUBTRACT',sep.outputs['Z'],constant=F);zs=mathnode('MULTIPLY',zoff.outputs[0],ri.outputs['Size']);zfinal=mathnode('ADD',zs.outputs[0],constant=F)
newxy=nodes.new('ShaderNodeSeparateXYZ');links.new(switch.outputs[0],newxy.inputs[0]);newp=nodes.new('ShaderNodeCombineXYZ');links.new(newxy.outputs['X'],newp.inputs['X']);links.new(newxy.outputs['Y'],newp.inputs['Y']);links.new(zfinal.outputs[0],newp.inputs['Z'])
setpos=nodes.new('GeometryNodeSetPosition');links.new(ri.outputs['Geometry'],setpos.inputs['Geometry']);links.new(newp.outputs[0],setpos.inputs['Position']);links.new(setpos.outputs[0],ro.inputs['Geometry'])
rail_count=0
for ob in list(bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects):
    if ob.type!='MESH' or not len(ob.data.vertices):continue
    points=evaluated_points(ob)
    if max(p.z for p in points)>F+.04:
        dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
        mx=INV@ob.matrix_world
        for v in me.vertices:v.co=mx@v.co
        for mod in list(ob.modifiers):ob.modifiers.remove(mod)
        ob.data=me;ob.matrix_world=FRAME
        cx=(min(p.x for p in points)+max(p.x for p in points))*.5;cy=(min(p.y for p in points)+max(p.y for p in points))*.5
        radii=[math.hypot(p.x,p.y) for p in points]
        arc='guardrail' in ob.name
        mod=ob.modifiers.new('Railing size','NODES');mod.node_group=railg;mod[rids['Pivot']]=(cx,cy,F);mod[rids['Circular']]=arc;mod[rids['Radius']]=(min(radii)+max(radii))*.5
        drive(mod,'["'+rids['Size']+'"]','Railing size');rail_count+=1
    parent_keep(ob,middle)
for ob in S.objects:
    if ob.name.startswith('Metal | amber floor pool'):
        parent_keep(ob,middle);z=ob.location.z;drive(ob,'location','Railing size',f'{F:.12f}+(v*{z-F:.12f})',2)

props=[o for o in S.objects if o.name.startswith('deck_desk') and o.type=='MESH'];pp=[v for o in props for v in evaluated_points(o)]
pivot=Vector(((min(p.x for p in pp)+max(p.x for p in pp))*.5,(min(p.y for p in pp)+max(p.y for p in pp))*.5,min(p.z for p in pp)))
console=empty('Rig | table and machinery',FRAME@Matrix.Translation(pivot))
for ob in props:parent_keep(ob,console)
for axis in range(3):drive(console,'scale','Table & machinery size','v/0.5',axis)
# A separate radius parent keeps the console near the back as the deck grows.
console_mount=empty('Rig | console placement',FRAME)
mw=console.matrix_world.copy();parent_keep(console,console_mount)
for axis in [0,1]:drive(console,'location','Middle radius (m)',f'{pivot[axis]:.12f}*v/{mid0:.12f}',axis)
for ob,base,key in [(lower,low0,'Lower radius (m)'),(upper,up0,'Upper radius (m)')]:
    for axis in [0,1]:drive(ob,'scale',key,f'v/{base:.12f}',axis)

# Bridge stays freely movable as an object; its mesh endpoints follow radii.
bridge=S.objects['Bridge | floating rectangle'];L=max(v.co.x for v in bridge.data.vertices)
base_start=INV@bridge.matrix_world.translation;axis=(INV@bridge.matrix_world).to_3x3()@Vector((1,0,0));flat=Vector((axis.x,axis.y,0)).normalized();lower_center=INV@lower.matrix_world.translation
near_radius=(lower_center-(base_start+axis*L)).dot(flat)+.12
bg,bi,bo,bids=group('Bridge follows platform radii',[('Middle delta','NodeSocketFloat',0,-10,10,''),('Lower edge delta','NodeSocketFloat',0,-10,10,'')])
nodes=bg.nodes;links=bg.links
bp=nodes.new('GeometryNodeInputPosition');bs=nodes.new('ShaderNodeSeparateXYZ');links.new(bp.outputs[0],bs.inputs[0]);t=mathnode('DIVIDE',bs.outputs['X'],constant=L)
one=mathnode('SUBTRACT',b=t.outputs[0]);one.inputs[0].default_value=1
a=mathnode('MULTIPLY',one.outputs[0],bi.outputs['Middle delta']);b=mathnode('MULTIPLY',t.outputs[0],bi.outputs['Lower edge delta']);delta=mathnode('SUBTRACT',a.outputs[0],b.outputs[0]);shift=vm('SCALE');shift.inputs[0].default_value=(math.hypot(axis.x,axis.y),0,-axis.z);links.new(delta.outputs[0],shift.inputs['Scale'])
sp=nodes.new('GeometryNodeSetPosition');links.new(bi.outputs['Geometry'],sp.inputs['Geometry']);links.new(shift.outputs[0],sp.inputs['Offset']);links.new(sp.outputs[0],bo.inputs['Geometry'])
mod=bridge.modifiers.new('Follow platform radii','NODES');mod.node_group=bg
drive(mod,'["'+bids['Middle delta']+'"]','Middle radius (m)',f'v-{mid0:.12f}')
drive(mod,'["'+bids['Lower edge delta']+'"]','Lower radius (m)',f'(v/{low0:.12f}-1)*{near_radius:.12f}')
refresh()
default_errors={n:max(abs(a-b) for a,b in zip(initial[n],bounds(S.objects[n]))) for n in samples}
assert max(default_errors.values())<2e-4,default_errors

# Exercise all controls and restore the accepted defaults before saving.
checks={}
tests=[('Table & machinery size',.75,'deck_desk_b',1.5,2),('Middle radius (m)',mid0*1.08,'Metal | continuous support drum',1.08,0),('Lower radius (m)',low0*1.1,lower.name,1.1,0),('Upper radius (m)',up0*.85,upper.name,.85,0)]
for key,value,obj,expected,component in tests:
    old=control[ids[key]];before=bounds(S.objects[obj]);control[ids[key]]=value;refresh();after=bounds(S.objects[obj]);ratio=after[component]/before[component]
    checks[key]={'measured_ratio':ratio,'expected_ratio':expected};assert abs(ratio-expected)<1e-4,(key,ratio)
    control[ids[key]]=old;refresh()
rail=S.objects['Metal | perimeter post'];p0=evaluated_points(rail);h0=max(p.z for p in p0)-F
control[ids['Railing size']]=1.4;refresh();p1=evaluated_points(rail);ratio=(max(p.z for p in p1)-F)/h0
checks['Railing size']={'measured_height_ratio':ratio,'expected_ratio':1.4};assert abs(ratio-1.4)<1e-4
control[ids['Railing size']]=1.;refresh()
terrain_error={n:max((S.objects[n].matrix_world@v.co-p).length for v,p in zip(S.objects[n].data.vertices,points)) for n,points in terrain_expected.items()}
report={'controls':{n:float(control[ids[n]]) for n,*_ in settings},'driver_tests':checks,'default_geometry_errors':default_errors,'terrain_max_vertex_error':terrain_error,'terrain_changed':[n for n,e in terrain_error.items() if e>1e-5],'rail_objects_controlled':rail_count,'requires_addon':False,'requires_python_autorun':False}
print('TERRAIN_PRECISION',json.dumps(terrain_error),flush=True)
assert not report['terrain_changed']
report['passed']=True;(P/'checks.json').write_text(json.dumps(report,indent=2));print('SLIDER_CHECKS',json.dumps(report),flush=True)

bpy.ops.object.select_all(action='DESELECT');ctrl.select_set(True);bpy.context.view_layer.objects.active=ctrl
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='PROPERTIES':
            area.spaces.active.pin_id=ctrl;area.spaces.active.use_pin_id=True
            try:area.spaces.active.context='MODIFIER'
            except TypeError:pass
S.name='Cave | platform and console sliders'
readme=bpy.data.texts.new('READ ME - Scene Sliders');readme.write('The Properties editor is pinned to SCENE SLIDERS > Modifiers > Scene Sliders. Drag the five fields to change the table/machinery scale, railing size, and three platform radii. Radius values are in metres. The railings and console position follow the middle radius. The floating bridge mesh follows the middle/lower radii but its object transform stays editable. These are native Geometry Nodes inputs and simple drivers: no add-on or Python autorun is required. Terrain is preserved from the latest live sculpt snapshot.')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'cave-platform-sliders.blend'),compress=True)
print('SAVED_SLIDERS',str(P/'cave-platform-sliders.blend'),flush=True)
