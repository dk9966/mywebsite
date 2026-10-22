"""Reduce the cave mesh and make the nearby overhang follow the roof controls."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

P=Path('/Users/danielku/mywebsite/secret-base/rounded-roof-light')
S=bpy.context.scene
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
root=bpy.data.objects['Lower | circular roof assembly']
lower=bpy.data.objects['Lower | plain octagon']
ctrl=bpy.data.objects['SCENE SLIDERS'];control=ctrl.modifiers['Scene Sliders']
assert not rock.get('rounded_roof_low_poly_revision')
old=rock.data;old.use_fake_user=True
rock['before_rounded_roof_terrain_mesh']=old.name
rock.data=old.copy()
prior=bpy.data.meshes[rock['before_circular_roof_clearance_mesh']]
assert len(prior.vertices)==len(rock.data.vertices)
matrix=rock.matrix_world.copy();inv=matrix.inverted()
center=inv@root.matrix_world.translation
foot=[inv@lower.matrix_world@lower.data.vertices[8+i].co for i in range(8)]
wall_z=root['wall_top_world_z']

# Recover the exact overhang patch moved in the previous pass. Feather its
# perimeter over neighboring edges so the refitted area joins the sculpt.
weights=[1. if (v.co-prior.vertices[v.index].co).length>1e-4 else 0. for v in rock.data.vertices]
affected=sum(w>0 for w in weights)
neighbors=[set() for _ in weights]
for e in rock.data.edges:
    a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
for value in [.60,.25]:
    touched=[i for i,w in enumerate(weights) if not w and any(weights[j]>value for j in neighbors[i])]
    for i in touched:
        z=(matrix@rock.data.vertices[i].co).z
        if wall_z+.02<z<wall_z+2.45:weights[i]=value
attr=rock.data.attributes.new('roof_clearance_follow','FLOAT','POINT')
for v,w in zip(attr.data,weights):v.value=w

# Bake the existing displacement/smoothing at their accepted settings, then
# simplify their result. The original sculpt and modifiers are retained.
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
baked=bpy.data.meshes.new_from_object(rock.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
baked.name='Cave | baked sculpt before polygon reduction'
temp=bpy.data.objects.new('Temporary cave simplification',baked)
S.collection.objects.link(temp)
dec=temp.modifiers.new('Reduce sculpt triangles by 84 percent','DECIMATE')
dec.ratio=.16
dec.use_collapse_triangulate=True
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
reduced=bpy.data.meshes.new_from_object(temp.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
reduced.name='Cave | simplified sculpt with close roof clearance'
assert reduced.attributes.get('roof_clearance_follow') is not None
original_triangles=sum(len(p.vertices)-2 for p in old.polygons)
reduced_triangles=sum(len(p.vertices)-2 for p in reduced.polygons)
assert reduced_triangles<original_triangles*.20
bpy.data.objects.remove(temp,do_unlink=True)
rock.data=reduced
for m in rock.modifiers:
    m.show_viewport=False;m.show_render=False
    m.name='Archived baked | '+m.name

# Native Geometry Nodes fit the lower overhang to the current radius and rise.
# All values use the rock's local XY basis (its Z is the world vertical).
g=bpy.data.node_groups.new('Cave | close clearance follows circular roof','GeometryNodeTree')
g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
hi=g.interface.new_socket(name='Light height',in_out='INPUT',socket_type='NodeSocketFloat');hi.default_value=1.49
ri=g.interface.new_socket(name='Light radius',in_out='INPUT',socket_type='NodeSocketFloat');ri.default_value=1.46
n,l=g.nodes,g.links
gi=n.new('NodeGroupInput');go=n.new('NodeGroupOutput')

def mathnode(op,a,b=None):
    v=n.new('ShaderNodeMath');v.operation=op
    if isinstance(a,(float,int)):v.inputs[0].default_value=a
    else:l.new(a,v.inputs[0])
    if b is not None:
        if isinstance(b,(float,int)):v.inputs[1].default_value=b
        else:l.new(b,v.inputs[1])
    return v.outputs[0]

def vm(op,a,b=None):
    v=n.new('ShaderNodeVectorMath');v.operation=op
    if isinstance(a,Vector) or isinstance(a,tuple):v.inputs[0].default_value=a
    else:l.new(a,v.inputs[0])
    if b is not None:
        if isinstance(b,Vector) or isinstance(b,tuple):v.inputs[1].default_value=b
        else:l.new(b,v.inputs[1])
    return v

pos=n.new('GeometryNodeInputPosition')
relative=vm('SUBTRACT',pos.outputs[0],center)
flat=vm('MULTIPLY',relative.outputs[0],(1,1,0))
rho=vm('LENGTH',flat.outputs[0]).outputs['Value']
unit=vm('NORMALIZE',flat.outputs[0]).outputs[0]
boundary=None
for a,b in zip(foot,foot[1:]+foot[:1]):
    e=b-a
    normal=Vector((e.y,-e.x,0)).normalized()
    if (a-center).dot(normal)<0:normal=-normal
    distance=(a-center).dot(normal)
    dot=vm('DOT_PRODUCT',unit,normal).outputs['Value']
    positive=mathnode('MAXIMUM',dot,.00001)
    radius=mathnode('DIVIDE',distance,positive)
    boundary=radius if boundary is None else mathnode('MINIMUM',boundary,radius)
num=mathnode('SUBTRACT',boundary,rho)
den=mathnode('SUBTRACT',boundary,gi.outputs['Light radius'])
t=mathnode('DIVIDE',num,den)
t=mathnode('MINIMUM',mathnode('MAXIMUM',t,0.),1.)
u=mathnode('DIVIDE',mathnode('SUBTRACT',t,.78),.22)
u=mathnode('MINIMUM',mathnode('MAXIMUM',u,0.),1.)
u2=mathnode('MULTIPLY',u,u)
u3=mathnode('MULTIPLY',u2,u)
bump=mathnode('MULTIPLY',mathnode('SUBTRACT',u2,u3),.22)
ease=mathnode('ADD',t,bump)
rise=mathnode('SUBTRACT',gi.outputs['Light height'],.075)
height=mathnode('ADD',mathnode('MULTIPLY',rise,ease),wall_z+.20)
# Broad, shallow variation keeps the rock natural without fine triangular noise.
sep=n.new('ShaderNodeSeparateXYZ');l.new(pos.outputs[0],sep.inputs[0])
phase=mathnode('ADD',mathnode('MULTIPLY',sep.outputs['X'],1.7),mathnode('MULTIPLY',sep.outputs['Y'],1.1))
ripple=mathnode('MULTIPLY',mathnode('SINE',phase),.025)
height=mathnode('ADD',height,ripple)
delta=mathnode('SUBTRACT',height,sep.outputs['Z'])
attr=n.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT';attr.inputs['Name'].default_value='roof_clearance_follow'
offset=mathnode('MULTIPLY',delta,attr.outputs['Attribute'])
vec=n.new('ShaderNodeCombineXYZ');l.new(offset,vec.inputs['Z'])
sp=n.new('GeometryNodeSetPosition');l.new(gi.outputs['Geometry'],sp.inputs['Geometry'])
l.new(vec.outputs[0],sp.inputs['Offset']);l.new(sp.outputs[0],go.inputs['Geometry'])
mod=rock.modifiers.new('Close rock follows light height and radius','NODES');mod.node_group=g
for socket,name in [(hi,'Light height above walls (m)'),(ri,'Light radius (m)')]:
    source=next(i for i in control.node_group.interface.items_tree if i.name==name)
    mod[socket.identifier]=float(control[source.identifier])
    fc=mod.driver_add('["'+socket.identifier+'"]')
    fc.driver.expression='v';v=fc.driver.variables.new();v.name='v';v.type='SINGLE_PROP'
    v.targets[0].id=ctrl;v.targets[0].data_path='modifiers["Scene Sliders"]["'+source.identifier+'"]'
for p in rock.data.polygons:p.use_smooth=False
rock['rounded_roof_low_poly_revision']=True
rock['roof_clearance_m']=.20
rock['simplification_ratio']=.16
rock['circular_roof_clearance']='Close low-poly overhang follows light height and radius with native nodes; source sculpt retained.'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
report={'source_triangles':original_triangles,'reduced_triangles':reduced_triangles,
        'triangle_reduction_percent':100*(1-reduced_triangles/original_triangles),
        'original_vertices':len(old.vertices),'reduced_vertices':len(reduced.vertices),
        'source_overhang_vertices':affected,'roof_clearance_m':.20,
        'clearance_follows_height_and_radius':True,'source_mesh_retained':old.name}
(P/'terrain-build.json').write_text(json.dumps(report,indent=2))
result=report
