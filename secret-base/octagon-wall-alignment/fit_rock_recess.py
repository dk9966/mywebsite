"""Open the existing connected rock recess around the upright wall planes."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path('/Users/danielku/mywebsite/secret-base/octagon-wall-alignment')
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
ob=bpy.data.objects['150 | continuous cave with oblique carved rooms']
F=6.824491024; TOP=F+2.03
if 'octagon_recess_source_mesh' in ob:
    raise RuntimeError('Rock recess already fitted.')
ob.data.use_fake_user=True;ob['octagon_recess_source_mesh']=ob.data.name
ob.data=ob.data.copy();ob.data.name='Cave | connected octagon wall recess'
mx=FRAME.inverted()@ob.matrix_world;back=mx.inverted()
bm=bmesh.new();bm.from_mesh(ob.data)
def inside(p):
    return 5.2<p.x<12.6 and -4.1<p.y<1.4 and F-.6<p.z<TOP+1.0
edges=[e for e in bm.edges if any(inside(mx@v.co) for v in e.verts)]
if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=2,use_grid_fill=True)
bm.to_mesh(ob.data);bm.free()
changed=0
def clamp(v):return min(1,max(0,v))
for v in ob.data.vertices:
    p=mx@v.co
    if not inside(p):continue
    wx=min(clamp((p.x-5.2)/.45),clamp((12.6-p.x)/.65))
    wz=min(clamp((p.z-(F-.6))/.40),clamp((TOP+1.-p.z)/.70))
    wy=clamp((p.y+4.1)/.6)
    boundary=.028201 if p.x<=10.426321 else .028201-(p.x-10.426321)
    target=boundary+.34
    delta=max(0,target-p.y)*wx*wz*wy
    if delta>1e-7:
        p.y+=delta;v.co=back@p;changed+=1
ob.data.update();bpy.context.view_layer.update()
ob['octagon_recess_note']='Local continuous rock opening follows the two rear bays and 45-degree corner bay.'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'aligned-walls.blend'),copy=True,compress=True)
result={'rock_vertices_adjusted':changed,'local_edges_subdivided':len(edges)}
