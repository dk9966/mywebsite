"""Fit only concealed nearby terrain to the architecture before simplification."""
import bpy,json,math,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
d=bpy.data.objects['Upper | beveled square gallery']
dec=w.modifiers['Platform surrounds | broad stone triangles']
NAME='Platform backing | snug hidden stone'
TARGET='Platform backing | live fitting surfaces'
assert not w.modifiers.get(NAME), 'Already fitted'
sources=[]
lower=['Lower | octagon rear bay 1','Lower | octagon rear bay 2','Lower | octagon angled corner bay',
       'Lower | opposite bay 1','Lower | opposite bay 2','Lower | far right beveled bay']
for name in lower:sources.append((bpy.data.objects[name],'lower_wall'))
for o in bpy.context.scene.objects:
    if o.name.startswith('Upper wall |') and 'panel course' in o.name:sources.append((o,'upper_wall'))
    if o.name.startswith('Upper wall | rib ') and 'bent channel' in o.name:sources.append((o,'upper_wall'))
    if o.name.startswith('Lower | roof slope '):sources.append((o,'roof'))
for name in ['Lower | plain octagon','Upper | beveled square gallery']:
    sources.append((bpy.data.objects[name],'floor'))

dec.show_viewport=False;bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get();ev=w.evaluated_get(dg)
coords=[v.co.copy() for v in ev.data.vertices]
verts=[];faces=[];kinds=[]
for obj,kind in sources:
    e=obj.evaluated_get(dg);mx=w.matrix_world.inverted()@obj.matrix_world
    start=len(verts);verts.extend(mx@v.co for v in e.data.vertices)
    faces.extend(tuple(start+i for i in p.vertices) for p in e.data.polygons)
    kinds.extend([kind]*len(e.data.polygons))
tree=BVHTree.FromPolygons(verts,faces)
upper_center=w.matrix_world.inverted()@d.matrix_world@Vector((0,0,12.5))
lower_center=w.matrix_world.inverted()@bpy.data.objects['Lower | circular roof assembly'].matrix_world.translation
weights=[];counts=collections.Counter();distances=collections.defaultdict(list)
def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)
for i,p in enumerate(coords):
    q,n,face,dist=tree.find_nearest(p)
    kind=kinds[face];wt=0.
    if (p-q).dot(n)>=-.006:
        if kind.endswith('wall'):
            center=upper_center if kind=='upper_wall' else lower_center
            direction=Vector((q.x-center.x,q.y-center.y,0)).normalized()
            if abs(n.z)<.75 and n.dot(direction)>.45:
                wt=smooth((1.25-dist)/.40)
        elif kind=='floor' and n.z<-.8:
            wt=smooth((.42-dist)/.20)
        elif kind=='roof' and n.z>.2:
            wt=smooth((.38-dist)/.20)
    if wt>0:
        counts[kind]+=1;distances[kind].append(dist)
    weights.append(wt)

# Evaluated targets follow the existing native architecture controls. They are
# a hidden dependency only, and add no visible or rendered triangles.
mesh=bpy.data.meshes.new(TARGET);target=bpy.data.objects.new(TARGET,mesh)
bpy.context.scene.collection.objects.link(target);target.matrix_world=w.matrix_world
g=bpy.data.node_groups.new(TARGET,'GeometryNodeTree')
g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
n,l=g.nodes,g.links;go=n.new('NodeGroupOutput');join=n.new('GeometryNodeJoinGeometry')
for obj,kind in sources:
    info=n.new('GeometryNodeObjectInfo');info.transform_space='RELATIVE'
    info.inputs['Object'].default_value=obj
    l.new(info.outputs['Geometry'],join.inputs['Geometry'])
l.new(join.outputs['Geometry'],go.inputs['Geometry'])
gm=target.modifiers.new('Live architectural back surfaces','NODES');gm.node_group=g
target.hide_render=True;target.hide_set(True);target.hide_select=True
target['purpose']='Hidden shrinkwrap dependency; never render or export as visible geometry.'
vg=w.vertex_groups.new(name=NAME);bins=collections.defaultdict(list)
for i,a in enumerate(weights):
    if round(a*100)>0:bins[round(a*100)].append(i)
for q,ids in bins.items():vg.add(ids,q/100*.99,'REPLACE')
mod=w.modifiers.new(NAME,'SHRINKWRAP');mod.target=target;mod.vertex_group=vg.name
mod.wrap_method='NEAREST_SURFACEPOINT';mod.wrap_mode='ON_SURFACE';mod.offset=.008
w.modifiers.move(len(w.modifiers)-1,list(w.modifiers).index(dec))
dec.show_viewport=True;bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
result={'fitted_source_vertices':dict(counts),'triangles_after':sum(len(p.vertices)-2 for p in e.data.polygons),
        'backing_gap_m':.008,'target_sources':len(sources),
        'original_gap_max_m':{k:max(v) for k,v in distances.items()}}
(P/'snug-report.json').write_text(json.dumps(result,indent=2))
