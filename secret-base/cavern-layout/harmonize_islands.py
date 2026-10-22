"""Match the outer stations and circulation to the protected central island.
The approved center is never edited. Input is the completed reference layout.
"""
import bpy,bmesh,math,json,sys,hashlib,argparse
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--pass',dest='stage',type=int,default=1);ap.add_argument('--final',action='store_true');ap.add_argument('--samples',type=int,default=32);ap.add_argument('--width',type=int,default=1500)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(P/'cavern-approved-terrain.blend'))
bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.871178627
CENTRAL=bpy.data.collections['01 | Original central island - protected']
def digest(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype=np.float64).tobytes())
 if o.type=='MESH':
  q=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',q);h.update(q.tobytes())
  q=np.empty(len(o.data.loops),dtype=np.int32);o.data.loops.foreach_get('vertex_index',q);h.update(q.tobytes())
  h.update(str([m.name if m else None for m in o.data.materials]).encode())
 return h.hexdigest()
protected={o.name:digest(o) for o in CENTRAL.objects if o.type=='MESH'}
def col(n):
 c=bpy.data.collections.new(n);S.collection.children.link(c);return c
DECK=col('06 | Matching tiled terraces and timber railings');BRIDGE=col('07 | Continuous bridges and fitted landings')
stone=bpy.data.objects['deck_floor_b'].data.materials[0]
wood=bpy.data.objects['deck_railing_b'].data.materials[0]
graphite=bpy.data.objects['deck_desk_b'].data.materials[0]
dark=bpy.data.objects['deck_desk_dark_b'].data.materials[0]
metal=bpy.data.objects['deck_desk_metal_b'].data.materials[0]
glass=bpy.data.objects['deck_desk_glass_b'].data.materials[0]
ink=bpy.data.objects['deck_desk_hud_b'].data.materials[0].copy()
ink.name='Harmony | restrained console markings'
for node in ink.node_tree.nodes:
 if node.type=='BSDF_PRINCIPLED':node.inputs['Emission Strength'].default_value*=.32
softglow=bpy.data.objects['deck_brazier_flames_b'].data.materials[0]
cream=bpy.data.materials['Layout | warm walkway lamp']
def mesh(n,vs,fs,mat=stone,c=DECK,bevel=0):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update();me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=1,affect='EDGES')
 bm.to_mesh(me);bm.free();o=bpy.data.objects.new(n,me);c.objects.link(o);o.matrix_world=FRAME;return o
def prism(n,xy,zlo,zhi,mat=stone,c=DECK,bevel=.008):
 N=len(xy);vs=[(v[0],v[1],z) for z in [zlo,zhi] for v in xy];fs=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 return mesh(n,vs,fs,mat,c,bevel)
CACHE={}
def box(n,p,sz,mat=stone,c=DECK,rot=0,bev=.008):
 key=(tuple(round(x,6) for x in sz),mat.name,bev)
 if key not in CACHE:
  bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
  for v in bm.verts:v.co=Vector((v.co.x*sz[0],v.co.y*sz[1],v.co.z*sz[2]))
  if bev:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bev,min(sz)*.2),segments=1,affect='EDGES')
  me=bpy.data.meshes.new(n);bm.to_mesh(me);bm.free();me.materials.append(mat);CACHE[key]=me
 o=bpy.data.objects.new(n,CACHE[key]);c.objects.link(o);o.matrix_world=FRAME@Matrix.Translation(p)@Matrix.Rotation(rot,4,'Z');return o
def beam(n,p,q,r=.018,mat=wood,c=DECK):
 p,q=Vector(p),Vector(q);v=q-p;o=box(n,(p+q)/2,(2*r,2*r,v.length),mat,c,bev=.003)
 o.matrix_world=FRAME@Matrix.Translation((p+q)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return o
def points(o):return [INV@(o.matrix_world@v.co) for v in o.data.vertices]
def hull(points):
 pts=sorted(set((round(p[0],6),round(p[1],6)) for p in points))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lo=[];hi=[]
 for p in pts:
  while len(lo)>=2 and cross(lo[-2],lo[-1],p)<=1e-8:lo.pop()
  lo.append(p)
 for p in reversed(pts):
  while len(hi)>=2 and cross(hi[-2],hi[-1],p)<=1e-8:hi.pop()
  hi.append(p)
 return [Vector(p) for p in lo[:-1]+hi[:-1]]
def offset(poly,d):
 # Clip against offset supporting half-planes. Rounded corners disappear
 # cleanly as courses move inward instead of folding into inverted arcs.
 out=[v.copy() for v in poly]
 for i,p in enumerate(poly):
  u=(poly[(i+1)%len(poly)]-p).normalized();n=Vector((-u.y,u.x));bound=n.dot(p)+d
  if not out:return []
  result=[]
  for v,w in zip(out,out[1:]+out[:1]):
   av=n.dot(v)-bound;aw=n.dot(w)-bound
   if av>=-1e-7:result.append(v)
   if (av>=0)!=(aw>=0):result.append(v+(w-v)*(av/(av-aw)))
  out=result
 return out

def perimeter(poly):return sum((poly[(i+1)%len(poly)]-v).length for i,v in enumerate(poly))
def onpoly(poly,f):
 lengths=[(poly[(i+1)%len(poly)]-v).length for i,v in enumerate(poly)];d=(f%1)*sum(lengths)
 for i,L in enumerate(lengths):
  if d<=L:return poly[i].lerp(poly[(i+1)%len(poly)],d/L)
  d-=L
 return poly[0].copy()
def area(poly):return sum(v.x*poly[(i+1)%len(poly)].y-v.y*poly[(i+1)%len(poly)].x for i,v in enumerate(poly))/2
# The two-tier gallery faces the center more directly, while retaining its layout.
rot=Matrix.Translation((.4,0,.15))@Matrix.Translation((-7.6,-4,0))@Matrix.Rotation(math.radians(-14),4,'Z')@Matrix.Translation((7.6,4,0))
for o in bpy.data.collections['Platform | Experiences'].objects:o.matrix_world=FRAME@rot@INV@o.matrix_world
foundation=bpy.data.objects['Experiences | approved rock foundation'];foundation.matrix_world=FRAME@Matrix.Translation((.4,0,.15))@INV@foundation.matrix_world
bpy.context.view_layer.update()
# Capture the authored terrace boundaries before replacing their industrial shells.
specs={
 'Contact':('Contact | structural frame',8.59),
 'Education':('Experiences | upper Education | rounded structural frame',6.14),
 'Work':('Experiences | lower Work | rounded structural frame',5.33),
 'About':('ABOUT ME | deep structural drum',6.016),
 'Workshop':('Workshop | structural frame',8.395),
}
platforms={}
for name,(obj,z) in specs.items():
 o=bpy.data.objects[obj];ps=points(o);poly=hull(ps);mw=INV@o.matrix_world;u=mw.to_3x3()@Vector((1,0,0));u.z=0;u.normalize();v=Vector((-u.y,u.x,0))
 us=[p.dot(u) for p in ps];vs=[p.dot(v) for p in ps];center=u*((min(us)+max(us))/2)+v*((min(vs)+max(vs))/2);center.z=z
 platforms[name]={'poly':poly,'z':z,'center':center,'u':u,'v':v,'halfwidth':(max(us)-min(us))/2,'halfdepth':(max(vs)-min(vs))/2}
# Remove the old circulation only; the recessed passage stays intact.
for o in list(bpy.data.collections['02 | New connecting bridges and stairs'].objects):
 if not o.name.startswith('Rear passage |'):bpy.data.objects.remove(o,do_unlink=True)
# Remove industrial outer floor plates, exposed fascia ribs, fences and old stairs.
removed=[];mapped=0
for role in ['Contact','Experiences','About','Workshop']:
 collection=bpy.data.collections['Platform | '+role]
 for o in list(collection.objects):
  n=o.name.lower()
  remove=(o.name.startswith(('Railing |','Edge lamp |','Fastener |','Bollard |','Structure |','Education → Work |','Experience | left stair')) or any(s in n for s in ['floor tile','floor seam','floor access hatch','hatch latch','safety annulus','inlaid yellow deck stripe','structural frame','deep structural drum','perimeter coping','fascia splice','skirt ribs','diagonal support']))
  remove=remove or (o.name.startswith(('Contact |','Experiences |','Workshop |','ABOUT ME |')) and any(s in n for s in ['side rim','edge beam','lower rim'])) or o.name=='ABOUT ME | floor'
  if remove:
   removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True);continue
  if o.type not in {'MESH','CURVE','FONT'}:continue
  # Copy per-object data to protect shared source and all center datablocks.
  mats=list(o.data.materials);replacement=[]
  for m in mats:
   if not m:replacement.append(m);continue
   mn=m.name
   if mn.startswith(('STRUCTURE |','DECK |','ANTENNA |','PROPS |','SAFETY |')):new=graphite
   elif mn.startswith('FRAME |'):new=stone
   elif mn.startswith('HARDWARE |'):new=metal
   elif mn.startswith('RECESSES |'):new=dark
   elif mn.startswith('DISPLAY |'):new=glass
   elif 'Secondary cyan' in mn:new=ink
   elif mn.startswith('WORKSHOP |'):new=wood
   else:new=m
   replacement.append(new)
  if mats!=replacement:
   o.data=o.data.copy();o.data.materials.clear()
   for m in replacement:o.data.materials.append(m)
   mapped+=1
# Keep the complete communications cabinet behind the arrival walking corridor.
for o in bpy.data.collections['Platform | Contact'].objects:
 if o.name.startswith('Contact | server |'):
  o.matrix_world=FRAME@Matrix.Translation(platforms['Contact']['v']*.70)@INV@o.matrix_world
# All routes use the real center opening axes and exact receiving deck elevations.
paths=[];ports={k:[] for k in platforms}
def closest_port(key,desired):
 p=Vector(desired);poly=platforms[key]['poly'];best=None
 for i,x in enumerate(poly):
  y=poly[(i+1)%len(poly)];v=y-x;t=max(0,min(1,(p-x).dot(v)/v.length_squared));q=x+v*t;d=(q-p).length
  if best is None or d<best[0]:best=(d,q,Vector((v.y,-v.x)).normalized())
 _,q,n=best;port={'p':Vector((q.x,q.y,platforms[key]['z'])),'n':Vector((n.x,n.y,0)),'key':key};ports[key].append(port);return port
def side_port(key,side=1,along=0):
 d=platforms[key];p=d['center']+d['u']*(side*d['halfwidth'])+d['v']*along
 return closest_port(key,p.xy)
def sample_bezier(p0,p1,p2,p3,n=50):
 return [(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3 for t in [i/n for i in range(n+1)]]
def poly_length(ps):return sum((q-p).length for p,q in zip(ps[:-1],ps[1:]))
def atdist(ps,s):
 for p,q in zip(ps[:-1],ps[1:]):
  L=(q-p).length
  if s<=L:return p.lerp(q,s/max(L,1e-8))
  s-=L
 return ps[-1].copy()
def railpost(n,p,c=BRIDGE,light=False):
 box(n+' | square timber post',p+Vector((0,0,.233)),(.055,.055,.414),wood,c,bev=.003)
 box(n+' | slate foot',p+Vector((0,0,.026)),(.082,.082,.052),stone,c,bev=.008)
 box(n+' | capped post',p+Vector((0,0,.456)),(.082,.082,.034),stone,c,bev=.006)
 if light:
  box(n+' | inset path light',p+Vector((0,0,.433)),(.053,.053,.035),cream,c,bev=.003)

def walkway(name,ps,z0,z1,width=.923,stairs=False,center_gate=None,dest=None,midlanding=False,arrival_landing=None,rail_limits=None,paving_lift=0):
 ps=[Vector((p[0],p[1],0)) for p in ps];L=poly_length(ps)
 # Every bridge has flat, overlapping end landings. Stairs contain solid risers.
 first=min(.72 if center_gate=='contact' else .42,L*.20);last=min(.58 if dest else .35,L*.22)
 if arrival_landing is not None:last=min(arrival_landing,L-first-.1)
 if stairs:
  zones=[]
  if midlanding and L>2.4:
   flight=(L-first-last-.58)/2;zones=[(0,first,z0,z0,False),(first,first+flight,z0,(z0+z1)/2,True),(first+flight,first+flight+.58,(z0+z1)/2,(z0+z1)/2,False),(first+flight+.58,L-last,(z0+z1)/2,z1,True),(L-last,L,z1,z1,False)]
  else:zones=[(0,first,z0,z0,False),(first,L-last,z0,z1,True),(L-last,L,z1,z1,False)]
 else:zones=[(0,first,z0,z0,False),(first,L-last,z0,z1,False),(L-last,L,z1,z1,False)]
 sections=[]
 for lo,hi,za,zb,step in zones:
  if hi-lo<1e-6:continue
  count=max(1,math.ceil(abs(zb-za)/.145)) if step else max(1,math.ceil((hi-lo)/.22))
  for k in range(count):
   ss=lo+(hi-lo)*k/count;ee=lo+(hi-lo)*(k+1)/count
   zA=za+(zb-za)*k/count;zB=za+(zb-za)*(k+1)/count
   if step:zA=zB=max(zA,zB)
   sections.append((ss,ee,zA,zB,step))
 def station(s):
  p=atdist(ps,s);u=atdist(ps,min(L,s+.035))-atdist(ps,max(0,s-.035));u.z=0;u.normalize();return p,Vector((-u.y,u.x,0))
 rail_nodes=[]
 for k,(ss,ee,za,zb,step) in enumerate(sections):
  p,n=station(ss);q,m=station(ee)
  vs=[]
  for drop in [-.20 if step else -.115,0]:
   for xyz,z in [(p+n*width/2,za),(p-n*width/2,za),(q-m*width/2,zb),(q+m*width/2,zb)]:vs.append((xyz.x,xyz.y,z+drop+paving_lift))
  mesh(name+' | continuous tread' if step else name+' | fitted paving',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],stone,BRIDGE,.004)
  rail_nodes.append((ss,p,n,za));
  if k==len(sections)-1:rail_nodes.append((ee,q,m,zb))
 # Guardrail height follows a smooth line over treads, with exactly matched ends.
 def height(s):
  for lo,hi,za,zb,step in zones:
   if s<=hi+1e-6:return za+(zb-za)*max(0,min(1,(s-lo)/(hi-lo)))
  return z1
 rail_samples=[i*L/math.ceil(L/.16) for i in range(math.ceil(L/.16)+1)]
 for side in [-1,1]:
  limit=rail_limits[side] if rail_limits else L
  for s0,s1 in zip(rail_samples[:-1],rail_samples[1:]):
   if s0>=limit:continue
   s1=min(s1,limit)
   p,n=station(s0);q,m=station(s1);p+=n*(width/2-.035)*side;q+=m*(width/2-.035)*side;p.z=height(s0);q.z=height(s1)
   beam(name+' | continuous rim',p-Vector((0,0,.125)),q-Vector((0,0,.125)),.045,graphite,BRIDGE)
   for z in [.292,.424]:beam(name+' | timber handrail',p+Vector((0,0,z)),q+Vector((0,0,z)),.017,wood,BRIDGE)
  count=max(1,math.ceil(L/.66))
  for k in range(count+1):
   if dest and k==count:continue
   s=k*L/count
   if rail_limits and s>limit-.08:continue
   p,n=station(s);p+=n*(width/2-.035)*side;p.z=height(s);railpost(name,p,light=(k%4==2))
  if rail_limits:
   p,n=station(limit);p+=n*(width/2-.035)*side;p.z=height(limit);railpost(name+' | joined arrival',p)
 # Broad trim strips bind the threshold into each terrace instead of floating ends.
 for s,z in [(0,z0),(L,z1)]:
  p,n=station(s);p.z=z+.002;beam(name+' | flush threshold seam',p-n*(width/2),p+n*(width/2),.012,metal,BRIDGE)
 paths.append({'name':name,'points':[[p.x,p.y,height(s)] for s in rail_samples for p in [atdist(ps,s)]],'width':width,'length':L,'end_heights':[z0,z1],'center_gate':center_gate,'destination':dest,'stairs':stairs})
 return paths[-1]

for role,key,along in [('contact','Contact',-.12),('experiences','Education',.12),('about','About',0)]:
 if role=='about':port=closest_port(key,(5.35,-.65))
 else:port=side_port(key,1,along)
 gate_name={'contact':'bridge_about_threshold_project','experiences':'bridge_about_threshold_project_contact','about':'bridge_threshold_project'}[role]
 # Hidden legacy thresholds live in another scene and do not have evaluated
 # transforms here. Use the captured source gates, then independently check
 # them against the actual protected railing mesh below.
 g=Vector(json.loads((P/'final-audit.json').read_text())['gates'][role]);g.z=0;n=g.normalized();start=n*2.59;lead=n*3.28
 end=port['p']-port['n']*.16;end.z=0
 tail=sample_bezier(lead,lead+n*.60,end+port['n']*.92,end)
 ps=[start,lead]+tail[1:]
 walkway('Projects to '+key,ps,F,platforms[key]['z'],.923,role=='contact',role,key,role=='contact')
# Both gallery levels receive fitted short stairs with corresponding rail openings.
for side,label in [(1,'right'),(-1,'left')]:
 d=platforms['Education'];e=platforms['Work'];along=side*(min(d['halfwidth'],e['halfwidth'])-.48)
 start=d['center']+d['u']*along-d['v']*(d['halfdepth']-.22)
 end=e['center']+e['u']*along+e['v']*(e['halfdepth']-1.06)
 walkway('Education to Work | '+label,[start,end],d['z'],e['z'],.64,True)
wp=side_port('Workshop',-1,-.42);we=wp['p']-wp['n']*.16;we.z=0
w0=Vector((-1,5.35,0));w1=Vector((0,4.3,0));mid=Vector((3.5,4.3,0))
walkway('Workshop rear passage',[w0]+sample_bezier(w0,Vector((-.5,4.3,0)),Vector((-.2,4.3,0)),w1)[1:]+sample_bezier(w1,mid,we+wp['n']*.85,we)[1:],8.40,platforms['Workshop']['z'],.80,dest='Workshop')
# A real side entrance clears the alcove wall and the shelf behind it.
wd=platforms['Workshop'];u=wd['u'];v=wd['v'];center=wp['p']+u*.16;center.z=wd['z']+.86
cut=box('Workshop | side arrival opening',center,(.95,1.08,1.76),stone,DECK,rot=math.atan2(u.y,u.x),bev=0)
cut.hide_render=True;cut.hide_set(True);cut.display_type='WIRE'
wall=bpy.data.objects['Workshop | portal | side enclosure'];modifier=wall.modifiers.new('Walkable side entrance','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cut
for o in bpy.data.collections['Platform | Workshop'].objects:
 if o.name.startswith(('Workshop | shelf','Workshop | labeled parts drawer','Workshop | parts bin','Workshop | parts label')):
  o.matrix_world=FRAME@Matrix.Translation(v*.43)@INV@o.matrix_world
beam('Workshop | side entry lintel',wp['p']-v*.52+Vector((0,0,1.76)),wp['p']+v*.52+Vector((0,0,1.76)),.05,stone,DECK)

ex=closest_port('About',(10.65,-4.18));p=ex['p']-ex['n']*.16;p.z=0;lead=p+ex['n']*.68;end=Vector((10.75,-6.6,0))
walkway('About exit upper stair',[p]+sample_bezier(p,lead,Vector((10.9,-5.7,0)),end)[1:],platforms['About']['z'],4.18,.86,True,dest='About')
walkway('About exit lower stair',[end,Vector((10.75,-7.25,0)),Vector((7.1,-9.3,0))],4.18,2.1,.96,True,midlanding=True)

# Determine openings from the swept walkway footprints, not approximate labels.
def obstructed(xy,z):
 for path in paths:
  if min(path['end_heights'])>z+1.1 or max(path['end_heights'])<z-.15:continue
  q=Vector((xy.x,xy.y));ps=path['points']
  for p0,p1 in zip(ps[:-1],ps[1:]):
   aa=Vector(p0[:2]);bb=Vector(p1[:2]);v=bb-aa;t=max(0,min(1,(q-aa).dot(v)/max(v.length_squared,1e-8)))
   if (q-aa-v*t).length<path['width']/2+.045:return True
 return False
# A matte tiled finish and continuous two-band skirt replace exposed industrial framing.
for key,d in platforms.items():
 poly=d['poly'];z=d['z'];inner=offset(poly,.10)
 prism(key+' | lower satin skirt',offset(poly,.04),z-.65,z-.20,graphite,bevel=.025)
 prism(key+' | pale upper rim',poly,z-.20,z-.045,stone,bevel=.018)
 prism(key+' | paving substrate',inner,z-.055,z-.020,dark,bevel=.004)
 # Small staggered pavers use the center's scale and satin material.
 # The circular laboratory inherits the exact center floor geometry.
 if key=='About':
  original=bpy.data.objects['deck_floor_b'];me=original.data.copy();me.name='About | inherited central concentric pavers'
  center_points=[INV@(original.matrix_world@v.co) for v in original.data.vertices]
  radius=max(math.hypot(p.x,p.y) for p in center_points)
  for vert,p in zip(me.vertices,center_points):
   xy=d['center']+d['u']*(p.x*d['halfwidth']/radius)+d['v']*(p.y*d['halfdepth']/radius)
   vert.co=(xy.x,xy.y,z+(p.z-F)*1.34)
  o=bpy.data.objects.new('About | exact central floor pattern',me);DECK.objects.link(o);o.matrix_world=FRAME
 else:
  vs=[];fs=[];u=d['u'];v=d['v'];origin=d['center'];clip=offset(poly,.074)
  def clip_to_boundary(subject):
   out=subject
   for i,p in enumerate(clip):
    q=clip[(i+1)%len(clip)];normal=Vector((p.y-q.y,q.x-p.x));bound=normal.dot(p)
    result=[]
    if not out:break
    for aa,bb in zip(out,out[1:]+out[:1]):
     da=normal.dot(aa)-bound;db=normal.dot(bb)-bound
     if da>=-1e-8:result.append(aa)
     if (da>=0)!=(db>=0):result.append(aa+(bb-aa)*da/(da-db))
    out=result
   return out
  dy=.235;dx=.43;rows=math.ceil(d['halfdepth']*2/dy)
  for row in range(rows+1):
   yy=-d['halfdepth']+row*dy
   for cell in range(-1,math.ceil(d['halfwidth']*2/dx)+1):
    xx=-d['halfwidth']+cell*dx+(dx*.5 if row%2 else 0)
    xy=[(origin+u*x+v*y).xy for x,y in [(xx+.006,yy+.006),(xx+dx-.006,yy+.006),(xx+dx-.006,yy+dy-.006),(xx+.006,yy+dy-.006)]]
    xy=clip_to_boundary(xy)
    if len(xy)<3 or abs(area(xy))<.001:continue
    N=len(xy);j0=len(vs)
    for zz in [z-.031,z]:vs.extend((p.x,p.y,zz) for p in xy)
    fs.extend([tuple(j0+i for i in reversed(range(N))),tuple(j0+N+i for i in range(N))]);fs.extend((j0+i,j0+(i+1)%N,j0+(i+1)%N+N,j0+i+N) for i in range(N))
  mesh(key+' | staggered small slate pavers',vs,fs,stone,bevel=.004)
 # Coping and two thin wooden rails match the central island in section/height.
 rp=offset(poly,.065);N=math.ceil(perimeter(rp)/.13)
 for k in range(N):
  p=onpoly(rp,k/N);q=onpoly(rp,(k+1)/N)
  if obstructed((p+q)/2,z):continue
  for h in [.292,.424]:beam(key+' | two-rail timber fence',(p.x,p.y,z+h),(q.x,q.y,z+h),.017,wood,DECK)
  beam(key+' | low satin coping',(p.x,p.y,z+.032),(q.x,q.y,z+.032),.033,stone,DECK)
 N=math.ceil(perimeter(rp)/.66)
 for k in range(N):
  p=onpoly(rp,k/N)
  if not obstructed(p,z) and all((p-port['p'].xy).length>.82 for port in ports[key]):railpost(key,Vector((p.x,p.y,z)),DECK,light=k%5==1)

# Tier labels sit on their fascias, clear of the new railing lines.
for label,key in [('EDUCATION','Education'),('WORK','Work')]:
 d=platforms[key];origin=INV@bpy.data.objects[label+' | sign frame'].matrix_world.translation
 target=d['center']-d['v']*(d['halfdepth']+.075)+d['u']*(-d['halfwidth']+(2.0 if key=='Education' else .98));target.z=d['z']+(.29 if key=='Education' else -.30)
 shift=FRAME@Matrix.Translation(target-origin)@INV
 for o in bpy.data.collections['Platform | Experiences'].objects:
  if o.name.startswith(label+' |'):o.matrix_world=shift@o.matrix_world

# Small entry piers make the receiving side read as a deliberate threshold.
for key,ps in ports.items():
 for port in ps:
  n=port['n'];t=Vector((-n.y,n.x,0));p=port['p']
  for side in [-1,1]:
   q=p+t*.515*side-n*.065
   railpost(key+' | single arrival post',q,DECK)
   start=p-n*.16+t*.4265*side
   for height in [.292,.424]:beam(key+' | joined arrival handrail',start+Vector((0,0,height)),q+Vector((0,0,height)),.017,wood,DECK)

# Validation uses the protected assembly and saved endpoint contracts.
bpy.context.view_layer.update();after={o.name:digest(o) for o in CENTRAL.objects if o.type=='MESH'}
assert protected==after,'The protected center was changed'
from mathutils.bvhtree import BVHTree
rail_obj=bpy.data.objects['deck_railing_b']
rail_bvh=BVHTree.FromObject(rail_obj,bpy.context.evaluated_depsgraph_get())
rail_inv=rail_obj.matrix_world.inverted()
contracts=[]
for path in paths:
 if not path['center_gate']:continue
 p0=Vector(path['points'][0]);p1=Vector(path['points'][1]);g=p0.copy();g.z=0;d=p1-p0;d.z=0
 deviation=math.degrees(g.angle(d))
 n=g.normalized();t=Vector((-n.y,n.x,0));clear=True
 for lateral in [-.43,0,.43]:
  for h in [.292,.424]:
   aa=FRAME@(n*2.45+t*lateral+Vector((0,0,F+h)));bb=FRAME@(n*2.98+t*lateral+Vector((0,0,F+h)))
   local_a=rail_inv@aa;local_b=rail_inv@bb;direction=local_b-local_a
   hit=rail_bvh.ray_cast(local_a,direction.normalized(),direction.length)
   if hit[0] is not None:clear=False
 assert clear,('Existing railing blocks new center entrance',path['name'])
 assert deviation<.15,(path['name'],deviation)
 z=platforms[path['destination']]['z'];assert abs(path['points'][-1][2]-z)<1e-5
 contracts.append({'route':path['name'],'departure_angle_error_deg':deviation,'existing_railing_clear':clear,'arrival_height_error':abs(path['points'][-1][2]-z),'landing_overlap':.16,'width':path['width']})
entry_checks=[]
for key,entries in ports.items():
 role='Experiences' if key in ['Education','Work'] else key
 for port in entries:
  hits=set();n=port['n'];t=Vector((-n.y,n.x,0));z=platforms[key]['z']
  for ob in bpy.data.collections['Platform | '+role].objects:
   if ob.type!='MESH' or ob.hide_render:continue
   bb=[INV@(ob.matrix_world@Vector(v)) for v in ob.bound_box]
   if max(p.z for p in bb)<z+.15 or min(p.z for p in bb)>z+1.45:continue
   if min((Vector((p.x,p.y))-port['p'].xy).length for p in bb)>2.0:continue
   bv=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get());mi=ob.matrix_world.inverted()
   for side in [-.27,0,.27]:
    for height in [.22,.65,1.3]:
     aa=port['p']+n*.22+t*side;bb=port['p']-n*.60+t*side;aa.z=z+height;bb.z=z+height
     pa=mi@(FRAME@aa);pb=mi@(FRAME@bb);direction=pb-pa
     if bv.ray_cast(pa,direction.normalized(),direction.length)[0] is not None:hits.add(ob.name)
  entry_checks.append({'platform':key,'position':list(port['p']),'blocking_props_or_walls':sorted(hits)})
print('ENTRY_CLEARANCE',json.dumps(entry_checks),flush=True)
assert not any(e['blocking_props_or_walls'] for e in entry_checks),'An outer entrance is blocked by scenery'
tag='matched' if a.final else f'harmony-{a.stage:02d}'
output=P/('cavern-matched-islands.blend' if a.final else tag+'.blend')
S['center_unchanged']=True;S['style_revision']='Shared central palette, inset pavers, timber two-rail fences, continuous fitted bridges'
text=bpy.data.texts.get('harmonize_islands.py') or bpy.data.texts.new('harmonize_islands.py');text.clear();text.write(Path(__file__).read_text())
S.camera=bpy.data.objects['Camera | reference composition'];S.cycles.samples=a.samples;S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*927/1696);S.render.resolution_percentage=100
S.render.filepath=str(P/(tag+'-overview.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.render.render(write_still=True)
if a.final:
 for camera,label in [('Camera | Contact and Experiences','contact-experiences'),('Camera | Workshop and About','workshop-about')]:
  S.camera=bpy.data.objects[camera];S.render.resolution_x=1400;S.render.resolution_y=1400;S.cycles.samples=64;S.render.filepath=str(P/(tag+'-'+label+'.png'));bpy.ops.render.render(write_still=True)
 S.camera=bpy.data.objects['Camera | reference composition'];S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*927/1696);S.cycles.samples=a.samples;S.render.filepath=str(P/(tag+'-overview.png'))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
audit={'source':'cavern-approved-terrain.blend','protected_center_unchanged':True,'protected_objects':protected,'style_materials':{'pavers':stone.name,'rails':wood.name,'equipment':graphite.name},'restyled_objects':mapped,'removed_industrial_components':len(removed),'platforms':{k:{'floor_height':v['z'],'outline':[[p.x,p.y] for p in v['poly']]} for k,v in platforms.items()},'connection_contracts':contracts,'entry_clearance':entry_checks,'routes':paths}
(P/(tag+'-audit.json')).write_text(json.dumps(audit,indent=2));print('MATCHED_RESULT',json.dumps({'blend':str(output),'image':S.render.filepath,'connections':contracts}),flush=True)
