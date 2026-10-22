import bpy, math, collections, json
from mathutils import Vector
from pathlib import Path

P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
mx=deck.matrix_world.inverted()@w.matrix_world
mods=list(w.modifiers)
states=[m.show_viewport for m in mods]
for m in mods[8:]:m.show_viewport=False
bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert len(e.data.vertices)==len(w.data.vertices)
coords=[mx@v.co for v in e.data.vertices]

def ss(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def band(v,lo,hi,fade):
    return ss((v-lo)/fade)*ss((hi-v)/fade)
def group(name,weights):
    vg=w.vertex_groups.get(name) or w.vertex_groups.new(name=name)
    vg.remove(list(range(len(w.data.vertices))))
    bins=collections.defaultdict(list)
    for i,a in enumerate(weights):
        q=round(a*100)
        if q:bins[q].append(i)
    for q,ids in bins.items():vg.add(ids,q/100,'REPLACE')
    return vg

shoulder=[];roof=[];lower=[]
for p in coords:
    shoulder.append(band(p.y,-6.8,-2.78,.85)*band(p.z,9.3,15.5,1.)*band(p.x,-3.5,5.5,1.2))
    roof.append(band(p.x,-3.6,4.2,.7)*band(p.y,-3.5,3.5,.6)*band(p.z,13.98,15.65,.4))
    lower.append(band(p.x,-3.6,2.9,.8)*band(p.y,-4.65,.7,.8)*band(p.z,9.0,11.38,.45))
g1=group('Surround repair | upper shoulder',shoulder)
g2=group('Surround repair | roof contact',roof)
g3=group('Surround repair | lower light rock',lower)
for m,state in zip(mods,states):m.show_viewport=state

name='Surround repair | relax upper shoulder'
sm=w.modifiers.get(name) or w.modifiers.new(name,'SMOOTH')
sm.factor=.7;sm.iterations=24;sm.vertex_group=g1.name

name='Surround repair | forward shoulder and lower light'
mod=w.modifiers.get(name)
if mod:
    g=mod.node_group
    g.nodes.clear()
else:
    g=bpy.data.node_groups.new(name,'GeometryNodeTree')
    g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    mod=w.modifiers.new(name,'NODES');mod.node_group=g
n,l=g.nodes,g.links
gi=n.new('NodeGroupInput');go=n.new('NodeGroupOutput')
def mathnode(op,a,b):
    nd=n.new('ShaderNodeMath');nd.operation=op
    for i,val in enumerate((a,b)):
        if isinstance(val,(float,int)):nd.inputs[i].default_value=val
        else:l.new(val,nd.inputs[i])
    return nd.outputs[0]
def attribute(name):
    nd=n.new('GeometryNodeInputNamedAttribute');nd.data_type='FLOAT';nd.inputs['Name'].default_value=name
    return nd.outputs['Attribute']
pos=n.new('GeometryNodeInputPosition')
axis=n.new('ShaderNodeVectorMath');axis.operation='DOT_PRODUCT'
axis.inputs[1].default_value=mx.to_3x3().row[0]
l.new(pos.outputs[0],axis.inputs[0])
x=mathnode('ADD',axis.outputs['Value'],mx.translation.x)
# Pull the side toward the viewer. Extend the lower rock to the front of the
# light footprint, with the existing source surface providing the connection.
upper=mathnode('MULTIPLY',attribute(g1.name),.62)
pull=mathnode('MAXIMUM',mathnode('ADD',x,1.85),0.)
lower_pull=mathnode('MULTIPLY',pull,attribute(g3.name))
amount=mathnode('MAXIMUM',upper,lower_pull)
vec=n.new('ShaderNodeVectorMath');vec.operation='SCALE'
vec.inputs[0].default_value=mx.inverted().to_3x3()@Vector((-1,0,0))
l.new(amount,vec.inputs['Scale'])
sp=n.new('GeometryNodeSetPosition');l.new(gi.outputs['Geometry'],sp.inputs['Geometry'])
l.new(vec.outputs[0],sp.inputs['Offset'])
xyz=n.new('ShaderNodeSeparateXYZ');l.new(pos.outputs[0],xyz.inputs[0])
roof_heights=[]
for objname in ['Upper roof | continuous fitted crown panels','Upper light | broad chamfered housing']:
    info=n.new('GeometryNodeObjectInfo');info.transform_space='RELATIVE';info.inputs['Object'].default_value=bpy.data.objects[objname]
    bbox=n.new('GeometryNodeBoundBox');l.new(info.outputs['Geometry'],bbox.inputs['Geometry'])
    sep=n.new('ShaderNodeSeparateXYZ');l.new(bbox.outputs['Max'],sep.inputs[0]);roof_heights.append(sep.outputs['Z'])
roof_top=mathnode('ADD',mathnode('MAXIMUM',*roof_heights),.025)
dz=mathnode('SUBTRACT',roof_top,xyz.outputs['Z'])
dz=mathnode('MULTIPLY',dz,attribute(g2.name))
zvec=n.new('ShaderNodeCombineXYZ');l.new(dz,zvec.inputs['Z'])
roofpos=n.new('GeometryNodeSetPosition');l.new(sp.outputs[0],roofpos.inputs['Geometry'])
l.new(zvec.outputs[0],roofpos.inputs['Offset'])
# Keep the front-right return outside the upper platform's walking area.
yaxis=n.new('ShaderNodeVectorMath');yaxis.operation='DOT_PRODUCT'
yaxis.inputs[1].default_value=mx.to_3x3().row[1];l.new(pos.outputs[0],yaxis.inputs[0])
y=mathnode('ADD',yaxis.outputs['Value'],mx.translation.y)
def smoothfield(value):
    t=mathnode('MINIMUM',mathnode('MAXIMUM',value,0.),1.)
    return mathnode('MULTIPLY',mathnode('MULTIPLY',t,t),mathnode('SUBTRACT',3.,mathnode('MULTIPLY',2.,t)))
def bandfield(v,lo,hi,fade):
    return mathnode('MULTIPLY',smoothfield(mathnode('DIVIDE',mathnode('SUBTRACT',v,lo),fade)),smoothfield(mathnode('DIVIDE',mathnode('SUBTRACT',hi,v),fade)))
safe=mathnode('MULTIPLY',bandfield(x,-2.5,2.5,.5),bandfield(y,-3.5,-2.,.35))
safe=mathnode('MULTIPLY',safe,bandfield(xyz.outputs['Z'],11.40,13.98,.15))
dy=mathnode('MULTIPLY',safe,mathnode('MINIMUM',mathnode('SUBTRACT',-3.04,y),0.))
yvec=n.new('ShaderNodeVectorMath');yvec.operation='SCALE';yvec.inputs[0].default_value=mx.inverted().to_3x3()@Vector((0,1,0));l.new(dy,yvec.inputs['Scale'])
wallpos=n.new('GeometryNodeSetPosition');l.new(roofpos.outputs[0],wallpos.inputs['Geometry']);l.new(yvec.outputs[0],wallpos.inputs['Offset']);l.new(wallpos.outputs[0],go.inputs['Geometry'])

obsolete=w.modifiers.get('Surround repair | snug upper roof')
if obsolete:w.modifiers.remove(obsolete)

name='Surround repair | blend lower light shoulder'
blend=w.modifiers.get(name) or w.modifiers.new(name,'SMOOTH')
blend.vertex_group=g3.name;blend.factor=.6;blend.iterations=25

# The same native light-clearance field must run after this new sculpt.
name='Surround repair | preserve circular light clearance'
clear=w.modifiers.get(name) or w.modifiers.new(name,'NODES')
clear.node_group=w.modifiers['Coarse rock | circular light clearance'].node_group
w.modifiers.move(list(w.modifiers).index(clear),len(w.modifiers)-1)
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
root=bpy.data.objects['Lower | circular roof assembly']
for label,control,offset in [('Fixture top','Light height above walls (m)',root['wall_top_world_z']+.14),('Protected radius','Light radius (m)',.85)]:
    socket=next(s for s in clear.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==label)
    source=next(s for s in cm.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==control)
    clear[socket.identifier]=cm[source.identifier]+offset
    path='["'+socket.identifier+'"]'
    try:clear.driver_remove(path)
    except:pass
    driver=clear.driver_add(path).driver;driver.expression='v+'+repr(offset)
    v=driver.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=ctrl
    v.targets[0].data_path='modifiers["Scene Sliders"]["'+source.identifier+'"]'
    if label=='Fixture top':
        radius_socket=next(s for s in cm.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name=='Light radius (m)')
        rv=driver.variables.new();rv.name='r';rv.type='SINGLE_PROP';rv.targets[0].id=ctrl
        rv.targets[0].data_path='modifiers["Scene Sliders"]["'+radius_socket.identifier+'"]'
        driver.expression+=' + max(0,r-0.93)*0.6'
ctrl.update_tag();bpy.context.view_layer.update()
result={'upper_group':sum(v>0 for v in shoulder),'roof_group':sum(v>0 for v in roof),'lower_group':sum(v>0 for v in lower)}
(P/'surround-report.json').write_text(json.dumps(result,indent=2))
