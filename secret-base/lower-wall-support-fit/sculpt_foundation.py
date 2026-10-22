import bpy, bmesh, math, json
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/lower-wall-support-fit')
path=bpy.data.filepath
if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-foundation-sculpt.blend'),copy=True,compress=True)
r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
old=r.data;old.use_fake_user=True;r.data=old.copy()
f=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');inv=f.inverted();mx=inv@r.matrix_world;ix=mx.inverted()
bm=bmesh.new();bm.from_mesh(r.data)
for v in bm.verts:v.co=mx@v.co
# Add local sculpt resolution before relaxing the long, stretched triangles.
for iteration in range(3):
 edges=[e for e in bm.edges if e.calc_length()>.48 and all(3.6<v.co.x<12.7 and -9<v.co.y<1.6 and 1.2<v.co.z<7.5 for v in e.verts)]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bm.verts.ensure_lookup_table();bm.verts.index_update()
a=np.array([tuple(v.co) for v in bm.verts]);source=a.copy()
edges=np.array([[e.verts[0].index,e.verts[1].index] for e in bm.edges]);i=np.concatenate((edges[:,0],edges[:,1]));j=np.concatenate((edges[:,1],edges[:,0]));degree=np.bincount(i,minlength=len(a))
def sm(v):
 v=np.clip(v,0,1);return v*v*(3-2*v)
w=sm((a[:,0]-3.6)/1.1)*sm((12.7-a[:,0])/1.1)*sm((a[:,1]+9)/1.2)*sm((1.6-a[:,1])/1.1)*sm((a[:,2]-1.2)/1.6)*sm((7.35-a[:,2])/.75)
for step in range(65):
 mean=np.column_stack([np.bincount(i,weights=a[j,k],minlength=len(a))/np.maximum(degree,1) for k in range(3)])
 a+=(mean-a)*(w*.48)[:,None]
# The shoulder is rounded back beneath the rim; it must not form pointed
# shelves outside the slab. Preserve the deeper cave and upper room walls.
x,y,z=a.T
under=(x>4.35)&(x<11.95)&(y>-9)&(y<.4)&(z>3)&(z<6.66)
front=-6.423+np.maximum(0,5.871-x)+np.maximum(0,x-10.426)
setback=.42+np.clip(6.6-z,0,3)*.18
blend=sm((z-3)/1.3)*sm((x-4.35)/.5)*sm((11.95-x)/.5)
a[:,1]+=np.maximum(0,front+setback-y)*blend*under
# Clear any low rock intrusions from the walkable octagon.
x,y,z=a.T
inside=(x>4.64)&(x<11.65)&(y>front+.03)&(y<.0)&(x+y>3.43)&(y-x<-5.85)
clear=inside&(z>6.50)&(z<7.35)
a[clear,2]=6.50
for v,p in zip(bm.verts,a):v.co=ix@Vector(p)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(r.data);bm.free();r.data.update()
# Suppress displacement on the reshaped foundation to retain its clean silhouette.
vg=r.vertex_groups.new(name='Foundation sculpt displacement falloff')
for idx,weight in enumerate(w):vg.add([idx],float(1-weight),'REPLACE')
for m in r.modifiers:
 if m.type=='DISPLACE':m.vertex_group=vg.name
bpy.context.view_layer.update()
# Seat the existing lower feet against the newly relaxed wall.
ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();tree=BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear()
anchors=[]
for o in sorted([o for o in bpy.data.objects if o.name.startswith('Lower | reference bracket foot')],key=lambda o:o.name):
 ps=[inv@o.matrix_world@v.co for v in o.data.vertices];center=sum(ps,Vector())/len(ps);hit,n,_,_=tree.find_nearest(center);target=hit-n*.03;anchors.append((center,target));local=(inv@o.matrix_world).inverted()
 old=o.data;old.use_fake_user=True;o.data=old.copy()
 for v,p in zip(o.data.vertices,ps):v.co=local@(p+target-center)
for o in [o for o in bpy.data.objects if o.name.startswith('Lower | reference large diagonal bracket')]:
 ps=[inv@o.matrix_world@v.co for v in o.data.vertices];a0=sum(ps[:4],Vector())/4;b0=sum(ps[4:],Vector())/4
 lower=a0 if a0.z<b0.z else b0;old,target=min(anchors,key=lambda pair:(pair[0]-lower).length)
 if a0.z<b0.z:a0=target
 else:b0=target
 axis=(b0-a0).normalized();u=axis.cross(Vector((0,0,1))).normalized()*.06;v=axis.cross(u).normalized()*.075;local=(inv@o.matrix_world).inverted();old=o.data;old.use_fake_user=True;o.data=old.copy()
 for vert,p in zip(o.data.vertices,[p+su*u+sv*v for p in (a0,b0) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]):vert.co=local@p
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='SCULPT')
bpy.ops.wm.save_as_mainfile(filepath=path,compress=True)
result={'smoothed_vertices':int(np.count_nonzero(w)), 'cleared_floor_vertices':int(np.count_nonzero(clear)), 'vertices':len(r.data.vertices),'saved':path}
(P/'sculpt-verification.json').write_text(json.dumps(result,indent=2))
