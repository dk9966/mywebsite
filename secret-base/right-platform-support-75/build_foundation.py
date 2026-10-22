"""Add a fitted, tapered rock shoulder to the existing right cliff and compact braces."""
import bpy,bmesh,json,math,hashlib,random
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;S=bpy.context.scene
D=json.loads((P/'surface-before.json').read_text());FRAME=Matrix(D['frame']);INV=FRAME.inverted()
ROCK=bpy.data.objects['150 | continuous cave with oblique carved rooms'];FLOOR=bpy.data.objects['Lower | plain octagon']
ps=[Vector(p) for p in D['floor_vertices']];BOTTOM=min(p.z for p in ps);TOP=max(p.z for p in ps)
poly=[Vector((p.x,p.y,0)) for p in ps[:8]];CENTER=sum(poly,Vector())/8
old=[o for o in bpy.data.objects if o.name.startswith(('Lower | reference large diagonal bracket','Lower | reference bracket foot')) and o.visible_get()]
def sig(o):
 h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
protected={o.name:sig(o) for o in S.objects if o not in old}
(P/'protected-originals.json').write_text(json.dumps(protected))
COL=bpy.data.collections.new('168 | Right platform rock shoulder and compact supports');S.collection.children.link(COL)
STONE=ROCK.data.materials[0];STEEL=bpy.data.materials['Metal | dark structural steel'];TRIM=bpy.data.materials['Lower | aligned architectural trim']

def objmesh(name,vs,fs,mat,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);COL.objects.link(o);o.parent=FLOOR;o.matrix_world=FRAME
 if bevel:
  m=o.modifiers.new('Small fabricated edge','BEVEL');m.width=bevel;m.segments=2;o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
 return o

# A closed sculpt volume with its lower/back body embedded into the original cliff.
# All points use the cave's coordinate frame and its exact existing rock material.
NEDGE=7;RINGS=12;ringpts=[]
for i,a in enumerate(poly):
 b=poly[(i+1)%8]
 for j in range(NEDGE):ringpts.append(a.lerp(b,j/NEDGE))
N=len(ringpts)
levels=[(BOTTOM+.014,1,0),(BOTTOM-.20,.998,.025),(BOTTOM-.52,.973,.08),(BOTTOM-.92,.925,.16),(BOTTOM-1.35,.855,.27),(BOTTOM-1.85,.76,.4),(BOTTOM-2.45,.65,.54),(BOTTOM-3.1,.54,.67),(BOTTOM-3.85,.44,.79),(BOTTOM-4.55,.34,.88),(BOTTOM-5.15,.245,.96),(BOTTOM-5.55,.18,1)]
BURY=Vector((10.1,-.8,0))

def foundation_vertices(scale):
 vs=[]
 for k,(z,size,mix) in enumerate(levels):
  center=CENTER.lerp(BURY,mix)
  for j,p in enumerate(ringpts):
   delta=(p-CENTER)*scale*size
   phase=j*math.tau/N
   rough=0 if k<2 else (.024*math.sin(phase*5.0+k*1.4)+.019*math.sin(phase*9.0-k*.7))*math.sin(min(1,k/4)*math.pi/2)
   delta*=1+rough
   q=center+delta;q.z=z+(0 if k<2 else .045*math.sin(phase*4.0+k))
   vs.append(tuple(q))
 return vs
faces=[tuple(range(N-1,-1,-1))]
for k in range(len(levels)-1):
 for j in range(N):
  a=k*N+j;b=k*N+(j+1)%N;c=(k+1)*N+(j+1)%N;d=(k+1)*N+j
  if k<2:faces.append((a,b,c,d))
  elif (j+k)%2:faces.extend([(a,b,d),(b,c,d)])
  else:faces.extend([(a,b,c),(a,c,d)])
faces.append(tuple(range((len(levels)-1)*N,len(levels)*N)))
foundation=objmesh('Lower right | sculpted bearing shoulder',foundation_vertices(math.sqrt(.75)),faces,STONE)
foundation['description']='Broad rock bearing shoulder, embedded into the existing cliff; fitted top carries 75 percent of the deck.'

def tree(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();t=BVHTree.FromPolygons([INV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
bpy.context.view_layer.update();rt=tree(ROCK);ft=tree(FLOOR)
samples=[]
for x in np.arange(4.65,11.67,.075):
 for y in np.arange(-6.40,.03,.075):
  p=Vector((float(x),float(y),TOP+.1))
  if ft.ray_cast(p,Vector((0,0,-1)),.6)[0] is not None:samples.append(p)

def shoulder_tree():
 return BVHTree.FromPolygons([INV@foundation.matrix_world@v.co for v in foundation.data.vertices],[list(p.vertices) for p in foundation.data.polygons])

def coverage(st):
 total=0
 for p in samples:
  # A bearing surface may sit slightly inside the slab but cannot rise above it.
  hs=[t.ray_cast(p,Vector((0,0,-1)),.55)[0] for t in [rt,st]]
  if any(h is not None and BOTTOM-.02<=h.z<=TOP+.005 for h in hs):total+=1
 return total/len(samples)
lo,hi=.78,.92;passes=[]
for _ in range(10):
 scale=(lo+hi)/2
 for v,p in zip(foundation.data.vertices,foundation_vertices(scale)):v.co=p
 foundation.data.update();bpy.context.view_layer.update();ratio=coverage(shoulder_tree());passes.append([scale,ratio])
 if ratio<.75:lo=scale
 else:hi=scale
scale=hi
for v,p in zip(foundation.data.vertices,foundation_vertices(scale)):v.co=p
foundation.data.update();bpy.context.view_layer.update();st=shoulder_tree();ratio=coverage(st)

# Refine the area measurement with stratified jitter to avoid grid/edge aliasing.
rng=random.Random(75);samples=[]
for i in range(177):
 for j in range(162):
  p=Vector((4.62119+(i+rng.random())*.04,-6.42314+(j+rng.random())*.04,TOP+.1))
  if ft.ray_cast(p,Vector((0,0,-1)),.6)[0] is not None:samples.append(p)
for correction in range(3):
 ratio=coverage(shoulder_tree())
 if abs(ratio-.75)<.0005:break
 scale*=math.sqrt(.75/ratio)
 for v,p in zip(foundation.data.vertices,foundation_vertices(scale)):v.co=p
 foundation.data.update();bpy.context.view_layer.update()
st=shoulder_tree();ratio=coverage(st)

# Replaced supports remain intact and reversible in a hidden collection.
ARCH=bpy.data.collections.new('Archive | right platform long front brackets');S.collection.children.link(ARCH);ARCH.hide_viewport=ARCH.hide_render=True
old_lengths=[]
for o in old:
 if 'large diagonal' in o.name:
  pts=[INV@o.matrix_world@v.co for v in o.data.vertices];old_lengths.append(((sum(pts[4:],Vector())-sum(pts[:4],Vector()))/4).length)
 ARCH.objects.link(o)
 for c in list(o.users_collection):
  if c!=ARCH:c.objects.unlink(o)
BOX=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def beam(name,a,b,width=.12,depth=.15):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();help=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0));u=axis.cross(help).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 return objmesh('Lower right | '+name,[tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],BOX,STEEL,.004)
def plate(name,center,u,v,n):
 center,u,v,n=map(Vector,(center,u,v,n))
 return objmesh('Lower right | '+name,[tuple(center+n*d+su*u+sv*v) for d in [-.04,.04] for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],BOX,TRIM,.004)

def nearest_ray(a,d,distance):
 candidates=[t.ray_cast(a,d,distance) for t in [rt,st]];candidates=[h for h in candidates if h[0] is not None]
 return min(candidates,key=lambda h:h[3]) if candidates else (None,None,None,None)

def path_clear(a,b):
 d=(b-a).normalized();length=(b-a).length
 return all(t.ray_cast(a+d*.11,d,max(.01,length-.19))[0] is None for t in [rt,st])

connections=[];skipped=[]
labels=['front left clipped corner','front edge','front right clipped corner','right edge','rear right clipped corner','rear edge','rear left clipped corner','left edge']
for ei,a in enumerate(poly):
 b=poly[(ei+1)%8];edge=(b-a).normalized();out=Vector((edge.y,-edge.x,0));positions=[.33,.67] if (b-a).length>3 else [.5]
 for pi,t in enumerate(positions):
  rim=a.lerp(b,t);end=rim-out*.12;end.z=BOTTOM-.072;chosen=None
  for drop in [.50,.65,.78,1.0,1.23,1.45]:
   origin=rim+out*2.0;origin.z=BOTTOM-drop
   hit,n,_,_=nearest_ray(origin,-out,5.5)
   if hit is None:continue
   inset=(rim-hit).dot(out)
   if not .13<inset<2.1:continue
   if n.dot(out)<0:n=-n
   n.normalize();anchor=hit+n*.055
   if not path_clear(anchor,end):continue
   if min(t.find_nearest(anchor.lerp(end,.55))[3] for t in [rt,st])<.075:continue
   chosen=(hit,n,anchor);break
  if chosen is None:
   skipped.append({'edge':labels[ei],'point':list(rim),'reason':'Existing cliff occupies the rim or leaves no exposed brace run.'});continue
  hit,n,anchor=chosen;name='%02d-%02d'%(ei+1,pi+1)
  u=(edge-n*edge.dot(n)).normalized()*.15;v=n.cross(u).normalized()*.18
  plate(name+' rock anchor plate',hit+n*.02,u,v,n)
  bracket=beam(name+' compact diagonal brace',anchor,end)
  start=hit-out*.05;start.z=BOTTOM-.035;finish=end.copy();finish.z=BOTTOM-.035
  beam(name+' underside bearer',start,finish,.115,.15)
  plate(name+' rim connection plate',(end.x,end.y,BOTTOM-.002),edge*.145,out*.115,(0,0,1))
  connections.append({'name':bracket.name,'side':labels[ei],'anchor':list(anchor),'top':list(end),'length':(end-anchor).length,'surface_point':list(hit)})

bpy.context.view_layer.update();changed=[n for n,h in protected.items() if sig(bpy.data.objects[n])!=h];assert not changed,changed
assert .740<ratio<.760,ratio
report={'supported_fraction':ratio,'sample_count':len(samples),'foundation_scale':scale,'top_height':BOTTOM+.014,'slab_bottom':BOTTOM,'old_brace_lengths':old_lengths,'connections':connections,'skipped_occluded_positions':skipped,'unchanged_original_objects':True,'coverage_iterations':passes,'active_file':bpy.data.filepath}
(P/'build-report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(P/'right-platform-75-preview.blend'),copy=True,compress=True)
result=report
