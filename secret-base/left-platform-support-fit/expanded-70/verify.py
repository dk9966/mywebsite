import bpy,bmesh,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;P=Q.parent;S=bpy.context.scene
F=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);IV=F.inverted()
report=json.loads((Q/'build-report.json').read_text())
def sig(o):
 h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
preview=bpy.data.filepath
protected_names=json.loads((Q/'protected-originals.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(Q/'before-expansion.blend'))
bpy.context.view_layer.update()
protected={n:sig(bpy.data.objects[n]) for n in protected_names}
bpy.ops.wm.open_mainfile(filepath=preview)
bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if n not in bpy.data.objects or sig(bpy.data.objects[n])!=h]
deps=bpy.context.evaluated_depsgraph_get()
def tree(o):
 ev=o.evaluated_get(deps);me=ev.to_mesh();t=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
rt=tree(bpy.data.objects['150 | continuous cave with oblique carved rooms']);ft=tree(bpy.data.objects['Front left | beveled rectangle landing'])
connections=[]
for c in report['connections']:
 a=Vector(c['anchor']);top=Vector(c['top']);h=ft.ray_cast(top,Vector((0,0,1)),.25)[0]
 # A centerline that crosses back into the rock would hide a brace.
 clearance=[]
 for t in [.1,.25,.5,.75,.9]:
  p=a.lerp(top,t);clearance.append(rt.find_nearest(p)[3])
 connections.append({'name':c['name'],'side':c['side'],'anchor_distance':rt.find_nearest(a)[3],'upper_bearer_distance':None if h is None else h.z-top.z,'minimum_rock_clearance':min(clearance)})
nonmanifold={}
for o in bpy.data.collections['167 | Left platform cliff supports'].objects:
 bm=bmesh.new();bm.from_mesh(o.data);n=sum(not e.is_manifold for e in bm.edges);bm.free()
 if n:nonmanifold[o.name]=n
intrusions=[]
for y in np.arange(.3,13.5,.25):
 for x in np.arange(.15,5.85,.25):
  p=Vector((float(x),float(y),2.95));floor_hit=ft.ray_cast(p,Vector((0,0,-1)),.7)[0]
  if floor_hit is None:continue
  rock_hit=rt.ray_cast(p,Vector((0,0,-1)),.412)[0]
  if rock_hit is not None:intrusions.append(list(rock_hit))
result={'measured_rock_coverage_percent':report['measured_coverage']*100,'unrelated_objects_changed':changed,'long_braces':sum(c['side']=='long' for c in connections),'front_short_braces':sum(c['side']=='short' for c in connections),'connections':connections,'new_mesh_nonmanifold_edges':nonmanifold,'walking_surface_intrusions':intrusions}
assert not changed,changed
assert 69<result['measured_rock_coverage_percent']<71
assert not nonmanifold
# Keep pre-existing rear cave intersections outside this under-platform edit.
new_intrusions=[]
if intrusions:
 bpy.ops.wm.open_mainfile(filepath=str(Q/'before-expansion.blend'))
 bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
 before_rt=tree(bpy.data.objects['150 | continuous cave with oblique carved rooms'])
 for p in intrusions:
  old=before_rt.ray_cast(Vector((p[0],p[1],2.95)),Vector((0,0,-1)),.412)[0]
  if old is None or p[2]>old.z+.015:new_intrusions.append(p)
result['preexisting_rear_wall_intersections']=result.pop('walking_surface_intrusions')
result['new_walking_surface_intrusions']=new_intrusions
assert not new_intrusions,new_intrusions[:8]
assert all(c['anchor_distance']<.09 and c['upper_bearer_distance'] is not None and c['upper_bearer_distance']<.1 for c in connections)
result['all_checks_passed']=True
(Q/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
