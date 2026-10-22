"""Local, reversible rock refinement; preserve architecture and live controls."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
S=bpy.context.scene
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
MOD='Close rock follows light height and radius'
KEY='Between platforms | natural connected rock'
if 'interplatform_source_mesh' not in w:
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-refinement-with-controls.blend'),copy=True,compress=True)
    w.data.use_fake_user=True
    w['interplatform_source_mesh']=w.data.name
    w["interplatform_source_nodes"]=w.modifiers[MOD].node_group.name
    w.modifiers[MOD].node_group.use_fake_user=True
source=bpy.data.meshes[w['interplatform_source_mesh']]
w.data=source.copy();w.data.name='Cave | broad connected inter-platform shoulder'
w.modifiers[MOD].node_group=bpy.data.node_groups[w['interplatform_source_nodes']].copy()
g=w.modifiers[MOD].node_group;g.name='Cave | rock in contact with adjustable roof'
for m in list(w.modifiers):
    if m.name.startswith('Between platforms |'):w.modifiers.remove(m)
def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3.-2.*t)
def xyweight(p):
    return smooth((p.x-3.25)/1.25)*smooth((14.1-p.x)/1.2)*smooth((p.y+7.0)/1.0)*smooth((4.0-p.y)/1.2)
ks=w.data.shape_keys.key_blocks;basis=ks['Basis']
co=[]
for i in range(len(w.data.vertices)):
    p=basis.data[i].co.copy()
    for k in ks:
        if k!=basis:p+=(k.data[i].co-k.relative_key.data[i].co)*k.value
    co.append(p)
weights=[xyweight(p)*smooth((p.z-8.98)/.4)*(1-smooth((p.z-10.82)/.50)) for p in co]
neighbors=[[] for _ in co]
for e in w.data.edges:
    a,b=e.vertices;neighbors[a].append(b);neighbors[b].append(a)
active=[i for i,v in enumerate(weights) if v>1e-6]
new=[p.copy() for p in co]
for step in range(35):
    moves=[]
    for i in active:
        if not neighbors[i]:continue
        avg=sum((new[j] for j in neighbors[i]),Vector())/len(neighbors[i])
        d=(avg-new[i])*.48*weights[i]
        # Relax slender triangles into broad rock planes without collapsing height.
        d.z*=.5
        moves.append((i,d))
    for i,d in moves:new[i]+=d
key=w.shape_key_add(name=KEY,from_mix=False);key.value=1
key.relative_key=basis
for i,p in enumerate(new):
    delta=p-co[i]
    # Meter-scale relief, rather than noise on individual triangles.
    a=weights[i]
    delta.y+=a*(.16*math.sin(p.x*1.6+p.z*.7)+.10*math.sin(p.x*.72-p.z*2.2))
    delta.x+=a*.055*math.sin(p.y*1.4+p.z*1.7)
    key.data[i].co=basis.data[i].co+delta

# The existing roof field already matches its height/radius controls exactly.
# Put the contact surface just inside the metal skin to eliminate daylight seams.
g.nodes['Math.039'].inputs[1].default_value=bpy.data.objects['Lower | circular roof assembly']['wall_top_world_z']-.018
g.nodes['Math.044'].inputs[1].default_value=0
n,l=g.nodes,g.links
def mathnode(op,a,b):
    v=n.new('ShaderNodeMath');v.operation=op
    for i,s in enumerate((a,b)):
        if isinstance(s,(float,int)):v.inputs[i].default_value=s
        else:l.new(s,v.inputs[i])
    return v.outputs[0]
def attr(name,values):
    a=w.data.attributes.get(name) or w.data.attributes.new(name,'FLOAT','POINT')
    for v,x in zip(a.data,values):v.value=x
    node=n.new('GeometryNodeInputNamedAttribute');node.data_type='FLOAT';node.inputs['Name'].default_value=name
    return node.outputs['Attribute']
mask=[];drop=[]
for p in co:
    mask.append(xyweight(p)*smooth((p.z-8.96)/.18)*(1-smooth((p.z-10.72)/.5)))
    drop.append(.78*(1-smooth((p.z-9.9)/.94)))
ma=attr('interplatform_contact',mask);da=attr('interplatform_lowering',drop)
z=next(v for v in n if v.bl_idname=='ShaderNodeSeparateXYZ').outputs['Z']
height=n['Math.045'].outputs[0]
target=mathnode('MAXIMUM',mathnode('SUBTRACT',z,da),height)
dz=mathnode('MULTIPLY',mathnode('SUBTRACT',target,z),ma)
vec=n.new('ShaderNodeCombineXYZ');l.new(dz,vec.inputs['Z'])
out=next(v for v in n if v.bl_idname=='NodeGroupOutput');old=out.inputs['Geometry'].links[0].from_socket
sp=n.new('GeometryNodeSetPosition');sp.label='Continuous rock meets roof';l.new(old,sp.inputs['Geometry']);l.new(vec.outputs[0],sp.inputs['Offset']);l.new(sp.outputs[0],out.inputs['Geometry'])

# Leave the circular light opening exposed as the rock settles onto the roof.
gi=next(v for v in n if v.bl_idname=='NodeGroupInput')
rho=next(v for v in n if v.bl_idname=='ShaderNodeVectorMath' and v.operation=='LENGTH').outputs['Value']
unit=next(v for v in n if v.bl_idname=='ShaderNodeVectorMath' and v.operation=='NORMALIZE').outputs[0]
radius=mathnode('ADD',gi.outputs['Light radius'],1.)
inside=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('DIVIDE',mathnode('SUBTRACT',radius,rho),.55),0.),1.)
fixture_top=mathnode('ADD',gi.outputs['Light height'],bpy.data.objects['Lower | circular roof assembly']['wall_top_world_z']+.16)
raise_by=mathnode('MAXIMUM',mathnode('SUBTRACT',fixture_top,z),0.)
clear_mask=attr('interplatform_clear_fixture',[xyweight(p)*smooth((p.z-8.8)/.2) for p in co])
raise_by=mathnode('MULTIPLY',raise_by,mathnode('MULTIPLY',clear_mask,inside))
arch=n.new('ShaderNodeCombineXYZ');l.new(raise_by,arch.inputs['Z'])
sp2=n.new('GeometryNodeSetPosition');sp2.label='Natural arch above circular light';l.new(sp.outputs[0],sp2.inputs['Geometry']);l.new(arch.outputs[0],sp2.inputs['Offset']);l.new(sp2.outputs[0],out.inputs['Geometry'])

# Keep the source keys editable. Collapse triangles primarily in the densely
# tessellated local shoulder, with strong protection for its contact anchors.
vg=w.vertex_groups.get('Between platforms | simplification') or w.vertex_groups.new(name='Between platforms | simplification')
vg.remove(list(range(len(co))))
for i,p in enumerate(co):
    wt=xyweight(p)*smooth((p.z-8.9)/.24)*(1-smooth((p.z-11.23)/.12))
    if wt>0:vg.add([i],wt,'REPLACE')
dec=w.modifiers.new('Between platforms | broad low-poly rock','DECIMATE')
dec.ratio=.67;dec.vertex_group=vg.name;dec.vertex_group_factor=1.;dec.use_collapse_triangulate=False

# Blend shallow facets only in this patch; retain real rock breaks as sharp edges.
attr('interplatform_soft_faces',[xyweight(p)*smooth((p.z-8.98)/.35)*(1-smooth((p.z-11.20)/.18)) for p in co])
sg=bpy.data.node_groups.new('Cave | broad stone shading','GeometryNodeTree')
sg.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
sg.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
sn,sl=sg.nodes,sg.links
si=sn.new('NodeGroupInput');so=sn.new('NodeGroupOutput')
sa=sn.new('GeometryNodeInputNamedAttribute');sa.data_type='FLOAT';sa.inputs['Name'].default_value='interplatform_soft_faces'
sel=sn.new('ShaderNodeMath');sel.operation='GREATER_THAN';sel.inputs[1].default_value=.15;sl.new(sa.outputs['Attribute'],sel.inputs[0])
sf=sn.new('GeometryNodeSetShadeSmooth');sf.domain='FACE';sf.inputs['Shade Smooth'].default_value=True
sl.new(si.outputs[0],sf.inputs['Geometry']);sl.new(sel.outputs[0],sf.inputs['Selection'])
angle=sn.new('GeometryNodeInputMeshEdgeAngle')
test=sn.new('ShaderNodeMath');test.operation='LESS_THAN';test.inputs[1].default_value=math.radians(38)
sl.new(angle.outputs['Unsigned Angle'],test.inputs[0])
se=sn.new('GeometryNodeSetShadeSmooth');se.domain='EDGE'
sl.new(sf.outputs[0],se.inputs['Geometry']);sl.new(sel.outputs[0],se.inputs['Selection']);sl.new(test.outputs[0],se.inputs['Shade Smooth']);sl.new(se.outputs[0],so.inputs[0])
sh=w.modifiers.new('Between platforms | soften shallow rock facets','NODES');sh.node_group=sg
w['interplatform_terrain']='Continuous natural shoulder; native roof contact; reversible local sculpt and polygon reduction.'
w['roof_clearance_m']=0.
w.data.update();bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
report={'source_triangles':sum(len(p.vertices)-2 for p in source.polygons),'evaluated_triangles':sum(len(p.vertices)-2 for p in e.data.polygons),'smoothed_vertices':len(active),'retained_shape_keys':[k.name for k in w.data.shape_keys.key_blocks]}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
result=report
