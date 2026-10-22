"""Replace the right landing's individual struts with reference-style V trusses."""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;S=bpy.context.scene
D=json.loads((P.parent/'surface-before.json').read_text());F=Matrix(D['frame']);IV=F.inverted()
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms'];floor=bpy.data.objects['Lower | plain octagon']
poly=[Vector((v[0],v[1],0)) for v in D['floor_vertices'][:8]];B=min(v[2] for v in D['floor_vertices'])
col=bpy.data.collections['168 | Right platform supports']
steel=bpy.data.materials['Metal | dark structural steel']
old_active=bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None;old_mode=bpy.context.mode;selected=[o.name for o in bpy.context.selected_objects]
def fingerprint(ob):
 h=hashlib.sha256();h.update(str([list(x) for x in ob.matrix_world]).encode())
 if ob.type=='MESH':
  for v in ob.data.vertices:h.update(str(tuple(v.co)).encode())
  for p in ob.data.polygons:h.update(str(tuple(p.vertices)).encode())
 return h.hexdigest()
protected={o.name:fingerprint(o) for o in S.objects if o.name not in col.objects}
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
def tree(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
 t=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(f.vertices) for f in me.polygons]);ev.to_mesh_clear();return t
bpy.context.view_layer.update();rt=tree(rock);ft=tree(floor)
cam=IV@bpy.data.objects['150 | main cave camera'].matrix_world.translation
def visible(p):
 v=p-cam;length=v.length;v.normalize()
 return all(t.ray_cast(cam,v,length-.06)[0] is None for t in [rt,ft])
def clear(a,b):
 v=b-a;length=v.length;v.normalize()
 if rt.ray_cast(a+v*.18,v,length-.23)[0] is not None:return False
 return min(rt.find_nearest(a.lerp(b,t))[3] for t in [.15,.25,.4,.55,.7,.85])>.068
plans=[];diagnostics=[]
specs=[(0,.5,.80,'front chamfer'),(1,.37,.68,'front long side'),(6,.5,.80,'rear chamfer'),(7,.5,.88,'left long side')]
for ei,preferred_t,preferred_span,label in specs:
 a=poly[ei];b=poly[(ei+1)%8];edge=(b-a).normalized();out=Vector((edge.y,-edge.x,0));candidates=[]
 for center_t in [preferred_t,preferred_t-.04,preferred_t+.04]:
  for span_ratio in [preferred_span,preferred_span-.10,preferred_span-.20]:
   if center_t-span_ratio/2<.03 or center_t+span_ratio/2>.97:continue
   rim=a.lerp(b,center_t);top=rim+out*.025;top.z=B-.13
   ends=[top-edge*(b-a).length*span_ratio/2,top,top+edge*(b-a).length*span_ratio/2]
   for drop in [1.95,1.8,1.65,2.1,1.5,2.25]:
    origin=rim+out*2;origin.z=B-drop;hit,n,_,_=rt.ray_cast(origin,-out,5.5)
    if hit is None:continue
    inset=(rim-hit).dot(out)
    if not .2<inset<1.05:continue
    if n.dot(out)<0:n=-n
    n.normalize();anchor=hit+n*.072;d=top-anchor
    lean=math.degrees(math.atan2((top-anchor).dot(out),d.z))
    if not 10<lean<24:continue
    clears=[clear(anchor,end) for end in ends]
    if not all(clears):
     diagnostics.append([label,center_t,span_ratio,drop,clears]);continue
    visible_frac=sum(visible(anchor.lerp(end,t)) for end in ends for t in [.25,.5,.75])/9
    score=abs(drop-1.85)*.25+(preferred_span-span_ratio)*3+abs(center_t-preferred_t)*2+abs(lean-17)*.009-visible_frac*.08
    candidates.append((score,dict(edge_index=ei,label=label,edge=edge,out=out,hit=hit,n=n,anchor=anchor,ends=ends,lean=lean,span=(b-a).length*span_ratio,visible_fraction=visible_frac)))
 if candidates:plans.append(min(candidates,key=lambda x:x[0])[1])
 else:diagnostics.append([label,'NO VALID FRAME'])
(P/'layout-search.json').write_text(json.dumps({'planned':[{k:([list(q) for q in v] if k=='ends' else list(v) if isinstance(v,Vector) else v) for k,v in p.items()} for p in plans],'rejected':diagnostics},indent=2))
assert len(plans)==4,[(p['label'],p['span']) for p in plans]
assert sum(p['visible_fraction']>.5 for p in plans)>=3
old_names=[o.name for o in col.objects if o.name.startswith('Lower right | ')]
for name in old_names:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
BOX=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
created=[]
def mesh_object(name,vs,fs,bevel=.005):
 me=bpy.data.meshes.new('V bracket | '+name);me.from_pydata(vs,[],fs);me.materials.append(steel);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new('Lower right | V '+name,me);col.objects.link(ob);ob.parent=floor;ob.matrix_world=F
 if bevel:
  mod=ob.modifiers.new('Steel edge radius','BEVEL');mod.width=bevel;mod.segments=2;ob.modifiers.new('Steel surface normals','WEIGHTED_NORMAL')
 created.append(ob.name);return ob
def box(name,c,u,v,n):
 return mesh_object(name,[tuple(c+su*u+sv*v+sn*n) for sn in [-1,1] for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],BOX,.004)
def i_beam(name,a,b,normal,width=.17,depth=.14):
 axis=(b-a).normalized();v=(normal-axis*normal.dot(axis)).normalized();u=v.cross(axis).normalized()
 w=width/2;d=depth/2;tw=.027/2;fl=.028
 profile=[(-w,-d),(w,-d),(w,-d+fl),(tw,-d+fl),(tw,d-fl),(w,d-fl),(w,d),(-w,d),(-w,d-fl),(-tw,d-fl),(-tw,-d+fl),(-w,-d+fl)]
 vs=[tuple(p+u*x+v*y) for p in [a,b] for x,y in profile];n=len(profile)
 fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
 return mesh_object(name,vs,fs,.003)
report=[]
for idx,p in enumerate(plans,1):
 key='%02d'%idx;edge=p['edge'];out=p['out'];anchor=p['anchor'];ends=p['ends'];n=p['n'];hit=p['hit']
 up=(ends[1]-anchor).normalized();normal=edge.cross(up).normalized()
 if normal.dot(out)<0:normal=-normal
 # Full-width diagonal steel arms plus a slender central tie meet at one rock foot.
 for j,end in enumerate([ends[0],ends[2]]):i_beam(key+' diagonal '+str(j+1),anchor,end,normal,.18,.15)
 i_beam(key+' center member',anchor,ends[1],normal,.105,.115)
 # A continuous header physically ties all three upper ends into the floor rim.
 c=(ends[0]+ends[2])/2;c.z=B-.06
 box(key+' underside header',c,edge*(p['span']/2+.11),out*.105,Vector((0,0,.075)))
 # Compact dark steel foot and a triangular gusset at the shared lower junction.
 u=(edge-n*edge.dot(n)).normalized();v=n.cross(u).normalized()
 box(key+' rock anchor',hit+n*.024,u*.20,v*.255,n*.052)
 tri=[anchor-up*.07,anchor+up*.33-edge*.24,anchor+up*.33+edge*.24]
 vs=[tuple(q+normal*d) for d in [-.019,.019] for q in tri]
 mesh_object(key+' lower gusset',vs,[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],.003)
 # Small rectangular end shoes remain under the fascia instead of covering its face.
 for j,end in enumerate([ends[0],ends[2]]):
  c=end.copy();c.z=B-.024;box(key+' upper shoe '+str(j+1),c,edge*.14,out*.16,Vector((0,0,.03)))
 report.append({'side':p['label'],'anchor':list(anchor),'top_connections':[list(e) for e in ends],'inward_lean_degrees':p['lean'],'span':p['span'],'vertical_drop':ends[1].z-anchor.z,'visible_fraction':p['visible_fraction']})
bpy.context.view_layer.update()
changed=[name for name,h in protected.items() if fingerprint(bpy.data.objects[name])!=h];assert not changed,changed
for ob in bpy.context.selected_objects:ob.select_set(False)
for name in selected:
 ob=bpy.data.objects.get(name)
 if ob:ob.select_set(True)
if old_active and bpy.data.objects.get(old_active):
 bpy.context.view_layer.objects.active=bpy.data.objects[old_active]
 if old_mode=='SCULPT':bpy.ops.object.mode_set(mode='SCULPT')
result={'v_frames':report,'created_objects':created,'replaced_objects':old_names,'other_geometry_unchanged':True,'terrain_unchanged':True}
(P/'v-braces-check.json').write_text(json.dumps(result,indent=2))
if bpy.app.background:bpy.ops.wm.save_as_mainfile(filepath=str(P/'v-braces-candidate.blend'),compress=True)
else:bpy.ops.wm.save_as_mainfile(filepath=str(P/'reference-v-braces-preview.blend'),copy=True,compress=True)
