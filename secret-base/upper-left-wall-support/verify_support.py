import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
inv=wall.matrix_world.inverted()
u=Vector((.764548,.644567,0)).normalized()
v=Vector((-u.y,u.x,0)); origin=Vector((-11.321278,9.82563,0))
def uv(p):
 d=p-origin;return Vector((d.dot(u),d.dot(v),p.z))
def tree_for(obj,evaluated=True):
 ob=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else obj
 me=ob.to_mesh(); mx=inv@ob.matrix_world
 tree=BVHTree.FromPolygons([uv(mx@p.co) for p in me.vertices],[list(p.vertices) for p in me.polygons])
 ob.to_mesh_clear();return tree
after=tree_for(wall)
key=wall.data.shape_keys.key_blocks['Upper-left | broad inward rock support']
key.value=0;bpy.context.view_layer.update();before=tree_for(wall)
key.value=1;bpy.context.view_layer.update()
def front(tree,x,z):
 hit,_,_,_=tree.ray_cast(Vector((x,-12,z)),Vector((0,1,0)),30)
 return hit.y if hit else 100
samples={}
for name in ['Back left | upper rectangular platform','Back left | broad stair flight','Back left | lower stair landing']:
 obj=bpy.data.objects[name];tree=tree_for(obj)
 points=[uv(inv@obj.matrix_world@p.co) for p in obj.data.vertices]
 xmin,xmax=min(p.x for p in points),max(p.x for p in points)
 ymin,ymax=min(p.y for p in points),max(p.y for p in points)
 count=supported=original=intrusions=0;gaps=[]
 for ix in range(1,24):
  for iy in range(1,32):
   x=xmin+(xmax-xmin)*ix/24;y=ymin+(ymax-ymin)*iy/32
   top,_,_,_=tree.ray_cast(Vector((x,y,15)),Vector((0,0,-1)),30)
   low,_,_,_=tree.ray_cast(Vector((x,y,0)),Vector((0,0,1)),15)
   if not top or not low:continue
   count+=1
   # Probe immediately below the slab, within a 5.5 cm bearing tolerance.
   supported+=front(after,x,low.z-.055)<=y
   original+=front(before,x,low.z-.055)<=y
   new_front=front(after,x,top.z+.035);old_front=front(before,x,top.z+.035)
   intrusions+=new_front<y-.03 and old_front>=y-.03
 samples[name]={'samples':count,'support_before_percent':round(100*original/count,2),
                'support_after_percent':round(100*supported/count,2),'new_walking_surface_intrusions':intrusions}
bm=bmesh.new();bm.from_mesh(wall.data)
seen=set();components=0
for vert in bm.verts:
 if vert in seen:continue
 components+=1;stack=[vert];seen.add(vert)
 while stack:
  a=stack.pop()
  for e in a.link_edges:
   other=e.other_vert(a)
   if other not in seen:seen.add(other);stack.append(other)
mesh_checks={'components':components,'loose_edges':sum(not e.link_faces for e in bm.edges),
             'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),
             'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces)}
bm.free()
def fingerprint(obj):
 h=hashlib.sha256();h.update(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(str([tuple(v.co) for v in obj.data.vertices]).encode())
  h.update(str([tuple(p.vertices) for p in obj.data.polygons]).encode())
 return h.hexdigest()
protected=json.loads((OUT/'protected-before.json').read_text())
changed=[name for name,h in protected.items() if fingerprint(bpy.data.objects[name])!=h]
result={'support_samples':samples,'mesh_checks':mesh_checks,'unrelated_objects_changed':changed,
        'file':bpy.data.filepath}
(OUT/'verification.json').write_text(json.dumps(result,indent=2))
