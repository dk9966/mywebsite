import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
f=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);mx=f.inverted()@r.matrix_world;ix=mx.inverted()
source=bpy.data.meshes[r['before_left_platform_fit_mesh']]
r.data.use_fake_user=True;r.data=source.copy();r.data.name='Cave | fitted left bearing shoulder final'
bm=bmesh.new();bm.from_mesh(r.data)
for v in bm.verts:v.co=mx@v.co
for step in range(5):
 edges=[e for e in bm.edges if all(-5.7<v.co.x<2.6 and -3.1<v.co.y<15 and -5.7<v.co.z<5.7 for v in e.verts) and e.calc_length()>(.14 if any(1.7<v.co.z<3.0 for v in e.verts) else .42)]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bmesh.ops.triangulate(bm,faces=[p for p in bm.faces if len(p.verts)>3 and all(-5.7<v.co.x<2.6 and -3.1<v.co.y<15 and -5.7<v.co.z<5.7 for v in p.verts)])
for v in bm.verts:v.co=ix@v.co
bm.to_mesh(r.data);bm.free();r.data.update()
r.shape_key_add(name='Basis');key=r.shape_key_add(name='Left landing | fitted wall and bearing shoulder');key.value=1
A=np.array([tuple(mx@v.co) for v in r.data.vertices]);O=A.copy()
def sm(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
x,y,z=A.T
w=sm((y+2.4)/2.25)*sm((15-y)/1.5)*sm((z+5.5)/1.7)*sm((5.6-z)/1.9)*sm((x+5.5)/1.7)*sm((2.65-x)/1.1)
tx=np.interp(z,[-5.5,-3.8,-2,-.2,1.25,2.00,2.50,2.70,3.15,3.8,5.6],[-.75,-.05,.4,1.1,2.02,2.25,.018,.018,-.08,-.28,-1.25])
noise=(.065*np.sin(y*1.43+z*.83)+.035*np.sin(y*2.7-z*1.8))*(z<2.0)
tx+=noise
end=sm((y+.05)/.8)*sm((13.75-y)/.8)
tx=np.where(tx>.04,.02+(tx-.02)*end,tx)
tz=z.copy();flat=(z>=2.00)&(z<2.5);tz[flat]=2.1707507
transition=(z>=2.5)&(z<2.7);tz[transition]=2.1707507+(z[transition]-2.5)/.2*(2.7-2.1707507)
A[:,0]+=w*(tx-x);A[:,2]+=w*(tz-z)
# Relax the sculpt transition to remove thin stretched triangular ridges.
edges=np.array([tuple(e.vertices) for e in r.data.edges]);i=np.r_[edges[:,0],edges[:,1]];j=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(i,minlength=len(A))
x,y,z=A.T
front=sm((y+3.0)/.8)*sm((1.0-y)/1.8)
back=sm((y-12.9)/1.0)*sm((15.8-y)/1.0)
bottom=sm((z+6)/.9)*sm((-2.8-z)/1.3)
relax=np.maximum.reduce([front,back,bottom])*sm((x+6)/1.5)*sm((4-x)/1.1)*sm((z+6)/.7)*sm((5.4-z)/1.2)
for step in range(60):
 mean=np.column_stack([np.bincount(i,weights=A[j,k],minlength=len(A))/np.maximum(degree,1) for k in range(3)])
 A+=(mean-A)*(relax*.47)[:,None]
for v,p in zip(key.data,A):
 if -.095<p[0]<.045 and .05<p[1]<13.45 and 2.17<p[2]<2.87:p[0]=.018
 v.co=ix@Vector(p)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'left-fit-preview.blend'),copy=True,compress=True)
result={'vertices':len(A),'local_sculpt_vertices':int(np.count_nonzero(w)),'relaxed_transition_vertices':int(np.count_nonzero(relax))}
(P/'finish-report.json').write_text(json.dumps(result,indent=2))
