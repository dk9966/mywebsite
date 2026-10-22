"""Add cliff-anchored cantilever supports below the rear-left bridge junction."""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;S=bpy.context.scene
assert bpy.context.mode=='OBJECT'
assert bpy.data.collections.get('172 | Rear-left cliff support brackets') is None
r=json.loads((P.parent/'verification.json').read_text());F=Matrix(r['frame']);IV=F.inverted();BF=Matrix(r['bridge_frame'])
H=r['floor_height'];END=r['bridge_end'];UP=Vector((0,0,1))
ROCK=bpy.data.objects['150 | continuous cave with oblique carved rooms'];LAND=bpy.data.objects['Rear left | one-piece chamfered T landing']
def fingerprint(o):
 h=hashlib.sha256(repr(([list(row) for row in o.matrix_world],o.hide_render,o.parent.name if o.parent else None)).encode())
 if o.type=='MESH':
  h.update(repr([tuple(v.co) for v in o.data.vertices]).encode());h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
  if o.data.shape_keys:
   for k in o.data.shape_keys.key_blocks:h.update(repr((k.name,k.value,[tuple(v.co) for v in k.data])).encode())
 return h.hexdigest()
protected={o.name:fingerprint(o) for o in S.objects}
(P/'protected-before.json').write_text(json.dumps(protected))
dg=bpy.context.evaluated_depsgraph_get();e=ROCK.evaluated_get(dg)
rt=BVHTree.FromPolygons([IV@e.matrix_world@v.co for v in e.data.vertices],[list(p.vertices) for p in e.data.polygons])
COL=bpy.data.collections.new('172 | Rear-left cliff support brackets');S.collection.children.link(COL)
STEEL=bpy.data.materials['Metal | dark structural steel'];TRIM=bpy.data.materials['Bridge | blue gunmetal panel frames'];BOLT=bpy.data.materials['Bridge | restrained silver fasteners']
BOX=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
made=[]
def mesh(name,vs,fs,mat=STEEL,bevel=.003):
 me=bpy.data.meshes.new('Rear support | '+name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new('Rear support | '+name,me);COL.objects.link(ob);ob.parent=LAND;ob.matrix_world=F
 if bevel:
  m=ob.modifiers.new('Fabricated edge radius','BEVEL');m.width=bevel;m.segments=2;ob.modifiers.new('Weighted metal normals','WEIGHTED_NORMAL')
 made.append(ob);return ob
def box(name,c,u,v,n,mat=STEEL):
 return mesh(name,[tuple(c+a*u+b*v+d*n) for d in (-1,1) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]],BOX,mat)
def beam(name,a,b,width=.16,depth=.18):
 a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(UP if abs(d.z)<.95 else Vector((0,1,0))).normalized();v=d.cross(u).normalized()
 return box(name,(a+b)/2,u*width/2,v*depth/2,d*(b-a).length/2)
def i_beam(name,a,b,width=.16,depth=.18):
 a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(UP).normalized();v=d.cross(u).normalized()
 w=width/2;h=depth/2;t=.021;web=.012
 profile=[(-w,-h),(w,-h),(w,-h+t),(web,-h+t),(web,h-t),(w,h-t),(w,h),(-w,h),(-w,h-t),(-web,h-t),(-web,-h+t),(-w,-h+t)]
 vs=[tuple(p+u*x+v*y) for p in (a,b) for x,y in profile];n=len(profile)
 fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,vs,fs,STEEL,.002)
def bolt(name,c,u,v,n):
 vs=[tuple(c+n*z+u*(.024*math.cos(i*math.tau/6))+v*(.024*math.sin(i*math.tau/6))) for z in (0,.023) for i in range(6)]
 fs=[tuple(range(5,-1,-1)),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
 return mesh(name,vs,fs,BOLT,.001)
def anchor(name,x,z):
 hit,n,idx,d=rt.ray_cast(Vector((x,-6,z)),Vector((0,1,0)),10);assert hit is not None
 if n.y>0:n=-n
 n.normalize();u=Vector((1,0,0));u=(u-n*u.dot(n)).normalized();v=n.cross(u).normalized()
 if v.z<0:v=-v
 box(name+' embedded rock plate',hit+n*.015,u*.19,v*.245,n*.065,TRIM)
 for i,(a,b) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):bolt(name+' anchor bolt %d'%i,hit+n*.08+u*a*.128+v*b*.178,u,v,n)
 hub=hit+n*.13
 box(name+' clevis block',hub,u*.105,v*.115,n*.10)
 return hit,hub,n
plans=[]
for index,side in enumerate((-1,1)):
 name='%02d'%(index+1);x=side*.49
 hit,foot,n=anchor(name+' lower',x,4.64)
 _,top_anchor,_=anchor(name+' upper',x,6.35)
 tip=BF@Vector((side*.50,END-1.46,H-.25));tip.z=H-.25
 # The upper bearing arm intersects both the landing underside and bridge stringer.
 head_start=top_anchor.copy();head_start.z=H-.245
 head_end=tip.copy();head_end.z=H-.245
 beam(name+' rock spine',foot,head_start,.15,.15)
 arm=i_beam(name+' horizontal bearing arm',head_start,head_end,.17,.19)
 diag=i_beam(name+' main diagonal cantilever',foot,tip,.18,.20)
 box(name+' bridge bearing shoe',tip+UP*.095,Vector((.16,0,0)),Vector((0,.19,0)),UP*.03,TRIM)
 # A splayed secondary wing supports the broad chamfered landing shoulder.
 wing=Vector((side*1.52,-1.72 if side>0 else -1.62,H-.34))
 wing_start=foot+Vector((0,-.035,.06))
 i_beam(name+' splayed landing brace',wing_start,wing,.135,.16)
 box(name+' landing bearing shoe',wing+UP*.055,Vector((.18,0,0)),Vector((0,.16,0)),UP*.045,TRIM)
 # Triangular gusset at the common foot unites the spine and main diagonal.
 a=(tip-foot).normalized();b=UP;normal=a.cross(b).normalized();tri=[foot-UP*.04,foot+a*.36,foot+UP*.34]
 mesh(name+' lower triangular gusset',[tuple(p+normal*t) for t in (-.018,.018) for p in tri],[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],TRIM,.002)
 plans.append({'name':name,'anchor_surface':list(hit),'anchor':list(foot),'tip':list(tip),'wing':list(wing),'top_anchor':list(top_anchor),'main_diagonal_length':(tip-foot).length})
# Cross members tie the pair into a rigid three-dimensional frame.
a,b=[Vector(p['tip']) for p in plans];beam('front transverse header',a,b,.14,.17)
a,b=[Vector(p['anchor']) for p in plans];beam('lower transverse tie',a,b,.095,.10)
a,b=[Vector(p['tip']) for p in plans];c,d=[Vector(p['anchor']) for p in plans]
for i,(p,q) in enumerate([(a.lerp(c,.26),b.lerp(d,.74)),(a.lerp(c,.74),b.lerp(d,.26))]):beam('cross-plane diagonal tie %d'%i,p,q,.055,.055)
bpy.context.view_layer.update()
changed=[n for n,sig in protected.items() if fingerprint(bpy.data.objects[n])!=sig];assert not changed,changed
topology={}
for o in made:
 bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-10 for f in bm.faces);bm.free()
 if bad or zero:topology[o.name]={'nonmanifold':bad,'zero_area':zero}
assert not topology,topology
checks=[]
for p in plans:
 a,b=Vector(p['anchor']),Vector(p['tip']);d=(b-a).normalized();hit,*_=rt.ray_cast(a+d*.16,d,(b-a).length-.27)
 checks.append({'name':p['name'],'main_brace_clear_of_rock':hit is None,'anchor_embedded':rt.find_nearest(Vector(p['anchor_surface']))[3]<.001,'tip_z':b.z,'shoe_top':b.z+.125,'bridge_stringer_bottom':H-.17})
assert all(q['main_brace_clear_of_rock'] and q['anchor_embedded'] for q in checks),checks
report={'frame':[list(row) for row in F],'objects_created':len(made),'supports':plans,'contact_checks':checks,'original_objects_unchanged':len(protected),'terrain_changed':False,'bad_topology':topology}
(P/'verification.json').write_text(json.dumps(report,indent=2))
COL['description']='Twin cliff-anchored cantilevers with spread landing wings, embedded bolted shoes, I-beams, and transverse bracing.'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'rear-left-supported.blend'),copy=True)
result=report
