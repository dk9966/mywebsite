import bpy
import bmesh
import math
import random
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
mesh=wall.data
bm=bmesh.new(); bm.from_mesh(mesh)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
t_layer=bm.verts.layers.float['wall_path_t']
v_layer=bm.verts.layers.float['wall_height_v']
patch=set(f for f in bm.faces if all(40-1e-4<=v[t_layer]<=105+1e-4 for v in f.verts))
boundary_edges=[e for e in bm.edges if sum(f in patch for f in e.link_faces)==1]
boundary=set(v for e in boundary_edges for v in e.verts)
assert all(sum(e in boundary_edges for e in v.link_edges)==2 for v in boundary)
bottom=sorted([v for v in boundary if v[v_layer]<.0001],key=lambda v:v[t_layer])
top=sorted([v for v in boundary if v[v_layer]>.9999],key=lambda v:v[t_layer])
def side_chain(start,end):
    forbidden=set(bottom+top)-{start,end}
    chain=[start];previous=None;current=start
    while current!=end:
        nxt=[e.other_vert(current) for e in current.link_edges if e in boundary_edges and e.other_vert(current)!=previous and e.other_vert(current) not in forbidden]
        assert len(nxt)==1
        previous,current=current,nxt[0];chain.append(current)
        assert len(chain)<len(boundary)
    return chain
left=side_chain(bottom[0],top[0])
right=side_chain(bottom[-1],top[-1])
assert set(bottom+top+left+right)==boundary

def curve(chain):
    distances=[0.]
    for a,b in zip(chain,chain[1:]):distances.append(distances[-1]+(b.co-a.co).length)
    length=distances[-1]
    normalized=[d/length for d in distances]
    points=[v.co.copy() for v in chain]
    def sample(t):
        t=max(0,min(1,t))
        for j in range(len(normalized)-1):
            if t<=normalized[j+1]+1e-9:
                f=(t-normalized[j])/(normalized[j+1]-normalized[j])
                return points[j].lerp(points[j+1],f)
        return points[-1].copy()
    return sample,normalized,length

B,bs,bl=curve(bottom);T,ts,tl=curve(top)
L,ls,ll=curve(left);R,rs,rl=curve(right)
width=(bl+tl)*.5;height=((top[0].co-bottom[0].co).length+(top[-1].co-bottom[-1].co).length)*.5
param={}
for v,s in zip(bottom,bs):param[v]=(s,0)
for v,s in zip(top,ts):param[v]=(s,1)
for v,h in zip(left,ls):param[v]=(0,h)
for v,h in zip(right,rs):param[v]=(1,h)

def surface(s,h):
    base=B(s)*(1-h)+T(s)*h
    def fade(x):
        x=max(0,min(1,x));return x*x*(3-2*x)
    left_correction=L(h)-(B(0)*(1-h)+T(0)*h)
    right_correction=R(h)-(B(1)*(1-h)+T(1)*h)
    return base+left_correction*fade((.075-s)/.075)+right_correction*fade((s-.925)/.075)

original_boundary=sorted(boundary,key=lambda v:v.index)
points=[Vector((param[v][0]*width,param[v][1]*height)) for v in original_boundary]
boundary_lookup={v:i for i,v in enumerate(original_boundary)}
constraints=[(boundary_lookup[e.verts[0]],boundary_lookup[e.verts[1]]) for e in boundary_edges]
rng=random.Random(240926)
spacing=1.05
row=1
y=spacing*.866
while y<height-spacing*.35:
    x=spacing*(.5 if row%2 else 1)
    while x<width-spacing*.35:
        xx=x+rng.uniform(-.14,.14)*spacing
        yy=y+rng.uniform(-.14,.14)*spacing
        if min(xx,width-xx,yy,height-yy)>.3:
            points.append(Vector((xx,yy)))
        x+=spacing
    row+=1;y+=spacing*.866

out_verts,out_edges,out_faces,orig_verts,_,_=delaunay_2d_cdt(points,constraints,[],1,1e-7,True)
# Remove the bad interior while retaining exact shared perimeter vertices.
old_interior=set(v for f in patch for v in f.verts)-boundary
bmesh.ops.delete(bm,geom=list(patch),context='FACES_ONLY')
loose_edges=[e for e in bm.edges if not e.link_faces and e not in boundary_edges]
if loose_edges:bmesh.ops.delete(bm,geom=loose_edges,context='EDGES')
loose_verts=[v for v in old_interior if v.is_valid and not v.link_edges]
if loose_verts:bmesh.ops.delete(bm,geom=loose_verts,context='VERTS')

out_to_bm=[]
for xy,ids in zip(out_verts,orig_verts):
    preserved=next((i for i in ids if i<len(original_boundary)),None)
    if preserved is not None:
        out_to_bm.append(original_boundary[preserved]);continue
    s=xy.x/width;h=xy.y/height
    co=surface(s,h)
    du=surface(min(1,s+.001),h)-surface(max(0,s-.001),h)
    dv=surface(s,min(1,h+.001))-surface(s,max(0,h-.001))
    normal=du.cross(dv).normalized()
    fade=min(1,min(xy.x,width-xy.x,xy.y,height-xy.y)/2)
    # Broad rock variation, with flat face shading and no repetitive ribs.
    bump=(.19*math.sin(co.x*.81+co.z*.47)*math.cos(co.y*.63-co.z*.22)
          +.09*math.sin(co.x*1.47-co.y*.73+co.z*.87))
    co+=normal*(bump*fade)
    v=bm.verts.new(co);v[t_layer]=40+65*s;v[v_layer]=h
    out_to_bm.append(v)
created=[]
for ids in out_faces:
    face=bm.faces.new([out_to_bm[i] for i in ids]);face.smooth=False;created.append(face)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(mesh);bm.free();mesh.update()
for f in mesh.polygons:f.use_smooth=False
wall['body_rebuild_note']='Rebuilt complete front-side wall body with arc-length-distributed triangulation; accepted top contour and shared perimeter preserved exactly.'
bpy.context.view_layer.update()
result={'replaced_faces':len(patch),'new_patch_faces':len(created),'preserved_boundary_vertices':len(original_boundary),'wall_faces':len(mesh.polygons),'wall_vertices':len(mesh.vertices),'patch_size':[width,height]}
