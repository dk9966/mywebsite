"""Clear the near rock lip from the three actual wall planes in the main view."""
import bpy,bmesh
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.geometry import intersect_ray_tri
P=Path('/Users/danielku/mywebsite/secret-base/octagon-wall-alignment')
S=bpy.context.scene;camera=S.camera.matrix_world.translation.copy()
ob=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ob.data.use_fake_user=True;ob['octagon_recess_before_lip']=ob.data.name
ob.data=ob.data.copy();ob.data.name='Cave | octagon recess and clear corner lip'
patches=[]
for name in ['rear bay 1','rear bay 2','angled corner bay']:
    wall=bpy.data.objects['Lower | octagon '+name]
    a,b,c,d=[wall.matrix_world@v.co for v in list(wall.data.vertices)[:4]]
    t=(b-a).normalized();u=Vector((0,0,1))
    a-=t*.30+u*.18;b+=t*.30-u*.18
    c+=t*.30+u*.28;d-=t*.30-u*.28
    patches.extend([(a,b,c),(a,c,d)])
def hit(p):
    direction=(p-camera).normalized()
    pts=[q for tri in patches if (q:=intersect_ray_tri(*tri,direction,camera,True)) is not None]
    return min(pts,key=lambda q:(q-camera).length) if pts else None
bm=bmesh.new();bm.from_mesh(ob.data)
mx=ob.matrix_world;inv=mx.inverted()
edges=[e for e in bm.edges if any(hit(mx@v.co) is not None for v in e.verts)]
if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bm.to_mesh(ob.data);bm.free()
changed=0
for v in ob.data.vertices:
    p=mx@v.co;q=hit(p)
    if q is not None and (p-camera).length<(q-camera).length+.45:
        v.co=inv@(q+(q-camera).normalized()*.45);changed+=1
ob.data.update();bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'aligned-walls.blend'),copy=True,compress=True)
result={'corner_lip_vertices_recessed':changed}
