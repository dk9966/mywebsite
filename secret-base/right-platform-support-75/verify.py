import bpy,bmesh,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;preview=bpy.data.filepath;F=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);IV=F.inverted()
report=json.loads((P/'build-report.json').read_text());names=json.loads((P/'protected-originals.json').read_text())
def sig(o):
 h=hashlib.sha256(repr(([list(r) for r in o.matrix_basis],[list(r) for r in o.matrix_parent_inverse])).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
  if o.data.shape_keys:
   for k in o.data.shape_keys.key_blocks:
    a=np.empty(len(k.data)*3,dtype=np.float32);k.data.foreach_get('co',a);h.update(a.tobytes());h.update(repr(k.value).encode())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P/'before-right-75.blend'));before={n:sig(bpy.data.objects[n]) for n in names};camera=bpy.context.scene.camera.name
bpy.ops.wm.open_mainfile(filepath=preview);bpy.context.view_layer.update();changed=[n for n,h in before.items() if sig(bpy.data.objects[n])!=h]
def tree(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();t=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
rt=tree(bpy.data.objects['150 | continuous cave with oblique carved rooms']);st=tree(bpy.data.objects['Lower right | sculpted bearing shoulder']);ft=tree(bpy.data.objects['Lower | plain octagon'])
nonmanifold={}
for o in bpy.data.collections['168 | Right platform rock shoulder and compact supports'].objects:
 bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
 if bad:nonmanifold[o.name]=bad
valid=contact=0;intrusions=[]
for x in np.arange(4.671,11.676,.09):
 for y in np.arange(-6.373,.028,.09):
  p=Vector((float(x),float(y),6.94));h=ft.ray_cast(p,Vector((0,0,-1)),.6)[0]
  if h is None:continue
  valid+=1;hits=[t.ray_cast(p,Vector((0,0,-1)),.6)[0] for t in [rt,st]]
  if any(h is not None and 6.599491<=h.z<=6.829491 for h in hits):contact+=1
  h=st.ray_cast(p,Vector((0,0,-1)),.11)[0]
  if h is not None:intrusions.append(list(h))
connections=[]
for c in report['connections']:
 a=Vector(c['anchor']);b=Vector(c['top']);d=(b-a).normalized();length=(b-a).length
 crossings=[t.ray_cast(a+d*.11,d,max(.01,length-.19))[0] for t in [rt,st]]
 h=ft.ray_cast(b,Vector((0,0,1)),.2)[0]
 connections.append({'name':c['name'],'edge':c['side'],'length':length,'rock_anchor_distance':min(t.find_nearest(a)[3] for t in [rt,st]),'underside_distance':None if h is None else h.z-b.z,'clear_brace_run':all(h is None for h in crossings)})
result={'measured_support_percent':contact/valid*100,'sample_count':valid,'brace_count':len(connections),'supported_edges':sorted(set(c['edge'] for c in connections)),'unchanged_original_objects_and_shape_keys':not changed,'changed_originals':changed,'new_nonmanifold_meshes':nonmanifold,'new_floor_intrusions':intrusions,'connections':connections,'original_camera_preserved':camera==bpy.context.scene.camera.name}
assert not changed,changed
assert not nonmanifold,nonmanifold
assert not intrusions
assert 74<result['measured_support_percent']<76
assert all(c['clear_brace_run'] and c['rock_anchor_distance']<.09 and c['underside_distance'] is not None and c['underside_distance']<.10 for c in connections)
assert len(result['supported_edges'])>=5
result['all_checks_passed']=True;(P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
