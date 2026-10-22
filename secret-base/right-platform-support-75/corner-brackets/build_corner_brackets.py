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
# Each support belongs to an actual octagon vertex. Its two wings attach
# to different adjoining sides, so the three beams enclose a tetrahedral volume.
for ci,corner in enumerate(poly):
 prev=poly[(ci-1)%8];nxt=poly[(ci+1)%8]
 pe=(prev-corner).normalized();ne=(nxt-corner).normalized();out=-(pe+ne).normalized()
 pref_l=min((prev-corner).length*.40,1.65);pref_r=min((nxt-corner).length*.40,1.65)
 candidates=[]
 for scale in [1.0,.9,.8,.7]:
  top=corner.copy();top.z=B-.13
  ends=[top+pe*pref_l*scale,top,top+ne*pref_r*scale]
  for drop in [1.95,1.8,1.65,2.1,1.5,2.25,1.35]:
   for twist in [0,-6,6,-12,12]:
    cast=Matrix.Rotation(math.radians(twist),3,'Z')@out
    origin=corner+cast*2;origin.z=B-drop
    hit,n,_,_=rt.ray_cast(origin,-cast,5.5)
    if hit is None:continue
    inset=(corner-hit).dot(out)
    if not .15<inset<1.05:continue
    if n.dot(out)<0:n=-n
    n.normalize();anchor=hit+n*.085;d=top-anchor
    lean=math.degrees(math.atan2(math.hypot(d.x,d.y),d.z))
    if not 8<lean<25:continue
    clears=[clear(anchor,end) for end in ends]
    if not all(clears):continue
    volume=abs((ends[0]-anchor).dot((ends[1]-anchor).cross(ends[2]-anchor)))/6
    if volume<.05:continue
    visible_frac=sum(visible(anchor.lerp(end,t)) for end in ends for t in [.25,.5,.75])/9
    score=(1-scale)*3+abs(drop-1.9)*.3+abs(twist)*.001+abs(lean-17)*.005-visible_frac*.07
    candidates.append((score,dict(corner_index=ci,corner=corner,prev_edge=pe,next_edge=ne,out=out,hit=hit,n=n,anchor=anchor,ends=ends,lean=lean,volume=volume,visible_fraction=visible_frac)))
 if candidates:plans.append(min(candidates,key=lambda x:x[0])[1])
 else:diagnostics.append({'corner_index':ci,'reason':'Terrain occupies the corner or the lower beam paths.'})
(P/'layout-search.json').write_text(json.dumps({'planned':[{k:([list(q) for q in v] if k=='ends' else list(v) if isinstance(v,Vector) else v) for k,v in p.items()} for p in plans],'skipped':diagnostics},indent=2))
assert {0,1,7}.issubset({p['corner_index'] for p in plans}),[p['corner_index'] for p in plans]
assert all(p['volume']>.05 for p in plans)
old_names=[o.name for o in col.objects if o.name.startswith('Lower right | ')]
for name in old_names:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
BOX=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
created=[]
def mesh_object(name,vs,fs,bevel=.005):
 me=bpy.data.meshes.new('Corner bracket | '+name);me.from_pydata(vs,[],fs);me.materials.append(steel);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new('Lower right | Corner '+name,me);col.objects.link(ob);ob.parent=floor;ob.matrix_world=F
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
for p in plans:
 key='%02d'%(p['corner_index']+1);out=p['out'];anchor=p['anchor'];ends=p['ends'];n=p['n'];hit=p['hit']
 # The central beam terminates exactly under the real platform corner.
 center=i_beam(key+' center to corner',anchor,ends[1],out,.15,.15)
 center['attached_platform_corner']=p['corner_index']
 # Each wing lies in a different plane with the center beam.
 for j,end in enumerate([ends[0],ends[2]]):
  normal=(ends[1]-anchor).cross(end-anchor).normalized()
  if normal.dot(out)<0:normal=-normal
  i_beam(key+' wing '+str(j+1),anchor,end,normal,.17,.145)
 # Two header pieces follow the bend in the rim and meet at that corner.
 for j,end in enumerate([ends[0],ends[2]]):
  edge=(end-ends[1]).normalized();side=Vector((edge.y,-edge.x,0))
  c=(end+ends[1])/2;c.z=B-.06
  box(key+' corner header '+str(j+1),c,edge*((end-ends[1]).length/2+.065),side*.095,Vector((0,0,.075)))
 # Compact common foot ties the three different beam planes into the rock.
 u=Vector((out.y,-out.x,0));u=(u-n*u.dot(n)).normalized();v=n.cross(u).normalized()
 box(key+' rock anchor',hit+n*.024,u*.205,v*.255,n*.052)
 box(key+' three way foot hub',anchor+n*.015,u*.135,v*.16,n*.075)
 # Small gussets reinforce each pair of beams without making a flat frame.
 for j,k in [(0,1),(1,2)]:
  a=(ends[j]-anchor).normalized();b=(ends[k]-anchor).normalized();normal=a.cross(b).normalized()
  tri=[anchor-a*.035-b*.035,anchor+a*.32,anchor+b*.32]
  vs=[tuple(q+normal*d) for d in [-.018,.018] for q in tri]
  mesh_object(key+' joint gusset '+str(j),vs,[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],.003)
 for j,end in enumerate(ends):
  edge=p['prev_edge'] if j==0 else p['next_edge'] if j==2 else u
  side=Vector((edge.y,-edge.x,0));c=end.copy();c.z=B-.024
  box(key+' upper shoe '+str(j),c,edge*.12,side*.12,Vector((0,0,.03)))
 assert (Vector(ends[1][:2])-Vector(p['corner'][:2])).length<1e-7
 report.append({'corner_index':p['corner_index'],'anchor':list(anchor),'top_connections':[list(e) for e in ends],'inward_lean_degrees':p['lean'],'enclosed_tetrahedral_volume':p['volume'],'visible_fraction':p['visible_fraction'],'center_attaches_to_actual_corner':True})
bpy.context.view_layer.update()
changed=[name for name,h in protected.items() if fingerprint(bpy.data.objects[name])!=h];assert not changed,changed
for ob in bpy.context.selected_objects:ob.select_set(False)
for name in selected:
 ob=bpy.data.objects.get(name)
 if ob:ob.select_set(True)
if old_active and bpy.data.objects.get(old_active):
 bpy.context.view_layer.objects.active=bpy.data.objects[old_active]
 if old_mode=='SCULPT':bpy.ops.object.mode_set(mode='SCULPT')
result={'corner_supports':report,'created_objects':created,'replaced_objects':old_names,'other_geometry_unchanged':True,'terrain_unchanged':True}
(P/'corner-brackets-check.json').write_text(json.dumps(result,indent=2))
if bpy.app.background:bpy.ops.wm.save_as_mainfile(filepath=str(P/'corner-brackets-candidate.blend'),compress=True)
else:bpy.ops.wm.save_as_mainfile(filepath=str(P/'corner-brackets-preview.blend'),copy=True,compress=True)
