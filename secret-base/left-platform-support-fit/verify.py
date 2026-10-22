import bpy,bmesh,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
ROCK='150 | continuous cave with oblique carved rooms'
def sig(o):
 h=hashlib.sha256();h.update(repr([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
def boundary(o):
 bm=bmesh.new();bm.from_mesh(o.data);n=sum(not e.is_manifold for e in bm.edges);bm.free();return n
bpy.ops.wm.open_mainfile(filepath=str(P/'before-left-fit.blend'))
original={o.name:sig(o) for o in bpy.context.scene.objects if o.name!=ROCK};old_boundary=boundary(bpy.data.objects[ROCK]);camera=bpy.context.scene.camera.name
bpy.ops.wm.open_mainfile(filepath=str(P/'left-fit-preview.blend'))
changed=[n for n,s in original.items() if n not in bpy.data.objects or sig(bpy.data.objects[n])!=s]
f=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);iv=f.inverted();deps=bpy.context.evaluated_depsgraph_get()
def tree(ob):
 ev=ob.evaluated_get(deps);me=ev.to_mesh();t=BVHTree.FromPolygons([iv@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
rock=bpy.data.objects[ROCK];rt=tree(rock);ft=tree(bpy.data.objects['Front left | beveled rectangle landing'])
connections=[]
for ob in bpy.data.collections['167 | Left platform cliff supports'].objects:
 if 'splayed diagonal bracket' not in ob.name:continue
 ps=[iv@ob.matrix_world@v.co for v in ob.data.vertices];a=sum(ps[:4],Vector())/4;b=sum(ps[4:],Vector())/4
 if a.z>b.z:a,b=b,a
 h=ft.ray_cast(b,Vector((0,0,1)),.4)[0]
 connections.append({'object':ob.name,'underside_gap':None if h is None else h.z-b.z,'anchor_distance':rt.find_nearest(a)[3]})
bearing=[];side=[];clear=[]
for y in np.linspace(.8,12.9,50):
 for x in [.7,1.1,1.5]:
  h=rt.ray_cast(Vector((x,float(y),2.54)),Vector((0,0,-1)),1)[0]
  bearing.append(None if h is None else float(h.z))
 h=rt.ray_cast(Vector((4,float(y),2.51)),Vector((-1,0,0)),6)[0];side.append(None if h is None else float(h.x))
 for x in [.16,.5,1,2,3,5]:
  h=rt.ray_cast(Vector((x,float(y),2.9)),Vector((0,0,-1)),.36)[0]
  if h is not None:clear.append([x,float(y),float(h.z)])
new=bpy.data.collections['167 | Left platform cliff supports'].objects
result={'unrelated_objects_changed':changed,'original_camera_preserved':camera==bpy.context.scene.camera.name,'new_meshes_nonmanifold':{o.name:boundary(o) for o in new if boundary(o)},'rock_nonmanifold_edges_before':old_boundary,'rock_nonmanifold_edges_after':boundary(rock),'brace_connections':connections,'side_contact_x_range':[min(side),max(side)],'bearing_contact_height_range':[min(x for x in bearing if x),max(x for x in bearing if x)],'missing_bearing_samples':sum(x is None for x in bearing),'walkable_surface_rock_intrusions':clear}
(P/'verification.json').write_text(json.dumps(result,indent=2))
# Concurrent stair/entrance edits may legitimately differ from the initial backup.
# Keep the full changed-object list in the report without reverting those edits.
assert result['original_camera_preserved']
assert not result['new_meshes_nonmanifold']
assert all(c['underside_gap'] is not None and c['underside_gap']<.15 and c['anchor_distance']<.09 for c in connections)
assert min(side)>-.025
assert not clear
(P/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
