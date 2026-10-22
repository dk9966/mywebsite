"""Aligned beveled square deck and reversible local cliff shoulder."""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;S=bpy.context.scene
F=Matrix(json.loads((P/'layout-before.json').read_text())['frame']);IV=F.inverted()
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
upper=bpy.data.objects['Upper | plain octagon - 90 percent radius']
assert bpy.context.mode=='OBJECT'
assert bpy.data.collections.get('171 | Upper right square gallery') is None
COL=bpy.data.collections.new('171 | Upper right square gallery');S.collection.children.link(COL)
ARCH=bpy.data.collections.new('Archive | upper right octagon');S.collection.children.link(ARCH);ARCH.hide_viewport=ARCH.hide_render=True
old=upper.copy();old.data=upper.data.copy();ARCH.objects.link(old);old.name='Archive | upper right octagon'
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':h.update(str([tuple(v.co) for v in o.data.vertices]).encode())
 return h.hexdigest()
protected={o.name:fingerprint(o) for o in S.objects if o not in (wall,upper,old)}
(P/'protected-before.json').write_text(json.dumps(protected))
STEEL=bpy.data.materials['Metal | dark structural steel'];FLOOR=bpy.data.materials['Metal | satin blue steel'];FRAME=bpy.data.materials['Bridge | blue gunmetal panel frames'];EDGE=bpy.data.materials['Metal | machined edge highlights'];BRASS=bpy.data.materials['Lower | muted brass floor registration'];GRATE=bpy.data.materials['Bridge | graphite open steel grating'];LIGHT=bpy.data.materials['Lower | cool white practical diffuser']
H=float(upper.location.z);SIDE=6.125;A=SIDE/2;BEVEL=.30
UP=Vector((0,0,1));made=[]
def outline(a,b):return [(-a+b,-a),(a-b,-a),(a,-a+b),(a,a-b),(a-b,a),(-a+b,a),(-a,a-b),(-a,-a+b)]
def mesh(name,vs,fs,mat,bevel=0):
 me=bpy.data.meshes.new('Upper right | '+name);me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new('Upper right | '+name,me);COL.objects.link(o);o.matrix_world=F;me.materials.append(mat)
 if bevel:
  m=o.modifiers.new('Fabricated edge bevel','BEVEL');m.width=bevel;m.segments=2;o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
 made.append(o);return o

def prism(name,p,z0,z1,mat,bevel=0):
 n=len(p);return mesh(name,[(x,y,z) for z in (z0,z1) for x,y in p],[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,bevel)
def append_beam(vs,fs,a,b,w,h):
 a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(UP if abs(d.z)<.95 else Vector((0,1,0))).normalized()*w/2;v=d.cross(u).normalized()*h/2;k=len(vs)
 vs.extend([tuple(p+u*i+v*j) for p in (a,b) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]])
 fs.extend([tuple(k+i for i in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
def beam(name,a,b,w,h,mat=STEEL,bevel=.002):
 v,f=[],[];append_beam(v,f,a,b,w,h);return mesh(name,v,f,mat,bevel)
def clip(poly,edge):
 for a,b in zip(edge,edge[1:]+edge[:1]):
  out=[]
  def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
  for p,q in zip(poly,poly[1:]+poly[:1]):
   sp,sq=side(p),side(q)
   if sp>=-1e-8:out.append(p)
   if (sp>=0)!=(sq>=0):
    t=sp/(sp-sq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
  poly=out
  if not poly:break
 return poly
poly=outline(A,BEVEL)
deck=prism('beveled square structural deck',poly,H-.20,H-.020,STEEL,.009)
upper.data=deck.data;upper.matrix_world=F;upper.name='Upper | beveled square gallery'
for m in deck.modifiers:
 n=upper.modifiers.new(m.name,m.type)
 if m.type=='BEVEL':n.width=m.width;n.segments=m.segments
bpy.data.objects.remove(deck,do_unlink=True);made.remove(deck)
upper['shape']='Square with four short 0.30 m corner bevels';upper['side_m']=SIDE;upper['corner_bevel_m']=BEVEL;upper['deck_height_m']=H;upper['parallel_to']='Lower platform main edges; world-space floor normals identical'
inside=outline(A-.085,BEVEL)
for j in range(7):
 for i in range(7):
  step=(2*A-.17)/7;x=-A+.085+i*step;y=-A+.085+j*step;g=.008
  p=clip([(x+g,y+g),(x+step-g,y+g),(x+step-g,y+step-g),(x+g,y+step-g)],inside)
  if len(p)>2:prism('satin floor plate %02d %02d'%(i,j),p,H-.019,H,FLOOR if (i+j)%5 else FRAME,.003)
# Recessed central rectangular service zone; seams keep the floor quiet and functional.
for y in (-2.12,2.12):
 for x0,x1 in [(-2.10,-.16),(.16,2.10)]:beam('broken brass service boundary',(x0,y,H+.001),(x1,y,H+.001),.022,.002,BRASS,0)
for x in (-2.12,2.12):
 for y0,y1 in [(-2.1,-.24),(.24,2.1)]:beam('broken brass service boundary',(x,y0,H+.001),(x,y1,H+.001),.022,.002,BRASS,0)
for x in (-1,1):
 for y in (-1,1):
  beam('service corner registration',(x*1.82,y*1.90,H+.002),(x*1.98,y*1.90,H+.002),.045,.002,BRASS,0)
  beam('service corner registration',(x*1.90,y*1.82,H+.002),(x*1.90,y*1.98,H+.002),.045,.002,BRASS,0)
# Narrow inset side drains with actual crossbars.
for x in (-2.57,2.57):
 prism('drain dark recess',[(x-.07,-2.55),(x+.07,-2.55),(x+.07,2.55),(x-.07,2.55)],H-.004,H+.001,STEEL)
 v,f=[],[]
 for j in range(114):
  y=-2.52+j*5.04/113;append_beam(v,f,(x-.058,y,H+.002),(x+.058,y,H+.002),.009,.012)
 mesh('drain crossbar cassette',v,f,GRATE,.0008)
 for s in (-1,1):beam('drain edge',(x+s*.073,-2.57,H+.001),(x+s*.073,2.57,H+.001),.015,.010,FRAME,.001)
# Continuous rim and dark fascia. Rail sizes match the scene's existing .354 m system.
railpoly=outline(A-.075,BEVEL-.025)
for i,(a,b) in enumerate(zip(railpoly,railpoly[1:]+railpoly[:1])):
 a,b=Vector((*a,H)),Vector((*b,H));d=b-a
 beam('machined perimeter cap %02d'%i,a-UP*.023,b-UP*.023,.092,.036,FRAME,.003)
 beam('lower perimeter reveal %02d'%i,a-UP*.165,b-UP*.165,.035,.025,EDGE,.001)
 for z in (.19,.345):beam('continuous guardrail %02d'%i,a+UP*z,b+UP*z,.025,.018)
 n=max(1,math.ceil(d.length/.68))
 for k in range(n):
  q=a.lerp(b,k/n);beam('railing upright',q,q+UP*.354,.027,.029)
  prism('railing bolted shoe',[(q.x-.028,q.y-.028),(q.x+.028,q.y-.028),(q.x+.028,q.y+.028),(q.x-.028,q.y+.028)],H-.006,H+.013,EDGE,.0015)
 if d.length>2:
  for t in (.18,.50,.82):
   p=a.lerp(b,t);u=d.normalized()
   beam('recessed edge light housing',p-u*.21-UP*.104,p+u*.21-UP*.104,.028,.065,STEEL,.003)
   beam('cool white edge diffuser',p-u*.17-UP*.105,p+u*.17-UP*.105,.031,.018,LIGHT,.001)
# Preserve the existing sculpt keys while adding local contour rows and a new sculpt.
source=wall.data;source.use_fake_user=True;wall.data=source.copy();wall.data.name='Cave | fitted upper-right gallery shoulder'
key=wall.shape_key_add(name='Upper-right | fitted shoulder and square recess');key.value=0
bm=bmesh.new();bm.from_mesh(wall.data);layers={name:bm.verts.layers.shape[name] for name in bm.verts.layers.shape.keys()};basis=layers['Basis'];MX=IV@wall.matrix_world;IMX=MX.inverted()
values={k.name:k.value for k in wall.data.shape_keys.key_blocks if k.name not in ('Basis',key.name)}
for v in bm.verts:
 p=v[basis].copy()
 for name,val in values.items():p+=(v[layers[name]]-v[basis])*val
 v.co=MX@p
def overlaps(f):
 return all(min(v.co[i] for v in f.verts)<hi and max(v.co[i] for v in f.verts)>lo for i,lo,hi in [(0,-5.0,5.7),(1,-4.7,5.7),(2,9.62,14.7)])
for _ in range(5):
 local={e for f in bm.faces if overlaps(f) for e in f.edges}
 edges=[e for e in local if e.calc_length()>.46]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
for z in (9.67,10.1,10.6,11.1,H-.213,H-.199,H+.015,12.3,13.4,14.45):
 faces=[f for f in bm.faces if min(v.co.z for v in f.verts)<z<max(v.co.z for v in f.verts) and overlaps(f)]
 edges={e for f in faces for e in f.edges};verts={v for f in faces for v in f.verts}
 if faces:bmesh.ops.bisect_plane(bm,geom=list(verts)+list(edges)+faces,plane_co=(0,0,z),plane_no=(0,0,1),dist=1e-6,clear_inner=False,clear_outer=False)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
anchor=Vector((-8,-8));support=outline(A-.12,.24);recess=outline(A+.16,.32)
def ray_interval(p,poly):
 d=Vector((p.x,p.y))-anchor;lo=0.;hi=100.
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ex,ey=b[0]-a[0],b[1]-a[1];s=ex*(anchor.y-a[1])-ey*(anchor.x-a[0]);q=ex*d.y-ey*d.x
  if abs(q)<1e-9:
   if s<0:return None
  elif q>0:lo=max(lo,-s/q)
  else:hi=min(hi,-s/q)
 return (lo,hi) if hi>=lo else None
# Bisect/subdivide do not consistently interpolate shape coordinates. Reconcile
# the interpolated live surface before storing the new additive sculpt delta.
for v in bm.verts:
 current=v[basis].copy()
 for name,val in values.items():current+=(v[layers[name]]-v[basis])*val
 correction=IMX@v.co-current
 for layer in layers.values():v[layer]+=correction
changed=0;maxdelta=0
for v in bm.verts:
 p=v.co.copy();new=p.copy();x,y,z=p
 if -5.2<x<5.8 and -4.9<y<5.8 and 9.67<z<14.45:
  hit=ray_interval(p,support);opening=ray_interval(p,recess)
  if opening:
   lo,hi=hit if hit else (1.,1.);ole,ohi=opening
   if z<=H-.213:
    weight=smooth((z-9.67)/.92);t=min(1.,lo)
    rough=(.048*math.sin(y*3.4+z*2.1)+.035*math.sin(x*4.1-z*2.3))*smooth((H-.38-z)/.5)
    t+=rough/max(1.,(Vector((x,y))-anchor).length)
   elif z<H-.199:
    f=(z-(H-.213))/.014;t=min(1.,lo)*(1-f)+max(1.,ohi)*f;weight=1
   else:t=max(1.,ohi);weight=1-smooth((z-13.35)/1.10)
   # Blend only in a narrow margin around this wall patch.
   weight*=smooth((5.8-max(x,y))/1.05)*smooth((min(x,y)+5.1)/1.0)
   d=Vector((x,y))-anchor;new.x=anchor.x+d.x*(1+(t-1)*weight);new.y=anchor.y+d.y*(1+(t-1)*weight)
 delta=IMX.to_3x3()@(new-p)
 v[layers[key.name]]=v[basis]+delta;v.co=v[basis]
 if delta.length>1e-7:changed+=1;maxdelta=max(maxdelta,delta.length)
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(wall.data);bm.free();wall.data.update();key=wall.data.shape_keys.key_blocks[key.name];key.value=1
# The upper bearing must not be lowered by the separate workshop-roof slider.
ks=wall.data.shape_keys.key_blocks;basis_key=ks['Basis'];attr=wall.data.attributes['roof_clearance_follow']
for i,v in enumerate(wall.data.vertices):
 if (key.data[i].co-basis_key.data[i].co).length>1e-6:
  co=basis_key.data[i].co.copy()
  for k in ks:
   if k!=basis_key:co+=(k.data[i].co-k.relative_key.data[i].co)*k.value
  if (MX@co).z>9.67:attr.data[i].value=0
wall.data.update()
wall['before_upper_right_mesh']=source.name;wall['upper_right_support']='Continuous local faceted shoulder; top bears against beveled square deck; square gallery recess. Reversible shape key.'
bpy.context.view_layer.update()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in protected.items())
report={'side_m':SIDE,'corner_bevel_m':BEVEL,'height':H,'frame':[list(r) for r in F],'rock_vertices_changed':changed,'maximum_sculpt_delta':maxdelta,'preserved_objects':len(protected),'shape_key':key.name,'mesh_vertices':len(wall.data.vertices)}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'upper-right-platform-candidate.blend'),copy=True)
result=report
