import bpy,bmesh,json,math,random
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;S=bpy.context.scene
D=json.loads((P.parent/'surface-before.json').read_text());F=Matrix(D['frame']);IV=F.inverted()
ROCK=bpy.data.objects['150 | continuous cave with oblique carved rooms'];FLOOR=bpy.data.objects['Lower | plain octagon']
ps=[Vector(v) for v in D['floor_vertices']];B=min(v.z for v in ps);TOP=max(v.z for v in ps)
poly=[Vector((v.x,v.y,0)) for v in ps[:8]]
COL=bpy.data.collections['168 | Right platform rock shoulder and compact supports']
STEEL=bpy.data.materials['Metal | dark structural steel'];TRIM=bpy.data.materials['Lower | aligned architectural trim']
def tree(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
 t=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
bpy.context.view_layer.update();rt=tree(ROCK);ft=tree(FLOOR)
cam=IV@bpy.data.objects['150 | main cave camera'].matrix_world.translation
def visible(p):
 d=(p-cam).normalized();length=(p-cam).length
 return all(t.ray_cast(cam,d,length-.04)[0] is None for t in [rt,ft])
BOX=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def objmesh(name,vs,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],BOX);me.materials.append(mat);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new('Lower right | '+name,me);COL.objects.link(ob);ob.parent=FLOOR;ob.matrix_world=F
 mod=ob.modifiers.new('Small fabricated edge','BEVEL');mod.width=.004;mod.segments=2;ob.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
 return ob
def beam(name,a,b,width=.14,depth=.16):
 axis=(b-a).normalized();guide=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))
 u=axis.cross(guide).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 return objmesh(name,[tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],STEEL)
def plate(name,c,u,v,n):
 return objmesh(name,[tuple(c+n*d+su*u+sv*v) for d in [-.04,.04] for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],TRIM)
def clear(a,b):
 axis=(b-a).normalized();length=(b-a).length
 if rt.ray_cast(a+axis*.15,axis,length-.22)[0] is not None:return False
 return min(rt.find_nearest(a.lerp(b,t))[3] for t in [.2,.4,.6,.8])>.08
plans=[];skipped=[];attempts=[]
labels=['front left clipped corner','front edge','front right clipped corner','right edge','rear right clipped corner','rear edge','rear left clipped corner','left edge']
for ei,a in enumerate(poly):
 b=poly[(ei+1)%8];edge=(b-a).normalized();out=Vector((edge.y,-edge.x,0))
 positions=([.25,.50] if ei==1 else [.33,.67]) if (b-a).length>3 else [.5]
 for pi,t in enumerate(positions):
  rim=a.lerp(b,t);end=rim+out*.005;end.z=B-.068;candidates=[]
  for drop in [2.0,1.8,2.15,1.65,1.5,2.3,1.35,1.2,1.05,.9,.75]:
   origin=rim+out*2;origin.z=B-drop
   hit,n,_,_=rt.ray_cast(origin,-out,5.5)
   if hit is None:attempts.append([ei,pi,drop,'no_hit']);continue
   inset=(rim-hit).dot(out)
   if not .15<inset<1.5:attempts.append([ei,pi,drop,'inset',inset]);continue
   if n.dot(out)<0:n=-n
   n.normalize();anchor=hit+n*.065;delta=end-anchor
   angle=math.degrees(math.atan2(math.hypot(delta.x,delta.y),delta.z))
   if angle>30 or not clear(anchor,end):attempts.append([ei,pi,drop,'angle_or_clear',angle,clear(anchor,end)]);continue
   seen=sum(visible(anchor.lerp(end,t)) for t in [.2,.4,.6,.8])/4
   # Prefer around two metres long and nearly upright; visibility breaks ties.
   score=abs(drop-2.0)+max(0,angle-18)*.04-seen*.12
   candidates.append((score,hit,n,anchor,end,angle,seen))
  if not candidates:
   skipped.append({'side':labels[ei],'position':t});continue
  _,hit,n,anchor,end,angle,seen=min(candidates,key=lambda x:x[0])
  plans.append({'name':'%02d-%02d'%(ei+1,pi+1),'side':labels[ei],'hit':hit,'n':n,'anchor':anchor,'end':end,'edge':edge,'out':out,'angle':angle,'visible':seen})
(P/'support-attempts.json').write_text(json.dumps({'plans':[{k:list(v) if isinstance(v,Vector) else v for k,v in p.items()} for p in plans],'attempts':attempts},indent=2))
assert len(plans)>=6,len(plans)
assert sum(p['visible']>.4 for p in plans)>=3,[(p['name'],p['visible']) for p in plans]
old=[]
for ob in list(COL.objects):
 if ob.name.startswith('Lower right | ') and any(s in ob.name for s in ['brace','anchor plate','underside bearer','rim connection plate']):
  old.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
report=[]
for p in plans:
 name=p['name'];hit=p['hit'];n=p['n'];edge=p['edge'];out=p['out'];a=p['anchor'];b=p['end']
 u=(edge-n*edge.dot(n)).normalized()*.16;v=n.cross(u).normalized()*.20
 plate(name+' rock anchor plate',hit+n*.02,u,v,n)
 ob=beam(name+' upright brace',a,b);ob['angle_from_vertical']=p['angle'];ob['length_m']=(b-a).length
 start=hit-out*.07;start.z=B-.035;finish=b.copy();finish.z=B-.035
 beam(name+' underside bearer',start,finish,.12,.16)
 plate(name+' rim connection plate',Vector((b.x,b.y,B-.002)),edge*.16,out*.125,Vector((0,0,1)))
 report.append({'name':ob.name,'side':p['side'],'anchor':list(a),'top':list(b),'surface':list(hit),'angle_from_vertical':p['angle'],'length':(b-a).length,'visible_fraction_from_main_camera':p['visible']})
# Confirm the welded rock still bears on the requested fraction of the floor.
rng=random.Random(75);covered=total=0
for i in range(177):
 for j in range(162):
  q=Vector((4.62119+(i+rng.random())*.04,-6.42314+(j+rng.random())*.04,TOP+.1))
  if ft.ray_cast(q,Vector((0,0,-1)),.6)[0] is None:continue
  total+=1;h=rt.ray_cast(q,Vector((0,0,-1)),.55)[0]
  if h is not None and B-.02<=h.z<=TOP+.005:covered+=1
ratio=covered/total;assert .74<ratio<.76,ratio
out={'connections':report,'skipped_occluded_positions':skipped,'replaced_objects':old,'rock_bearing_fraction':ratio,'coverage_samples':total}
(P/'upright-supports-check.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
COL.name='168 | Right platform supports'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'welded-platform-upright-supports.blend'),compress=True)
