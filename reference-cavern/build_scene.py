"""Deterministic, from-scratch reference cavern. Blender 5.x, metres.
Run: blender -b -t 8 --python build_scene.py -- --pass 1
"""
import bpy, bmesh, math, random, os, sys, json, argparse
from mathutils import Vector, Matrix
from math import sin, cos, pi
ROOT=os.path.dirname(os.path.abspath(__file__))
args=argparse.ArgumentParser(); args.add_argument('--pass',dest='stage',type=int,default=1); args.add_argument('--samples',type=int,default=32); args.add_argument('--width',type=int,default=1440)
opt=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
random.seed(28)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
S.unit_settings.system='METRIC'
COL=None
def collection(n):
 global COL
 COL=bpy.data.collections.new(n); S.collection.children.link(COL); print('BUILD',n,flush=True); return COL
def material(n,c,metal=0,rough=.5,emit=0):
 m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*c,1); p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
 if emit: p.inputs['Emission Color'].default_value=(*c,1); p.inputs['Emission Strength'].default_value=emit
 return m
steel=material('STRUCTURE | graphite powdercoat',(.057,.072,.088),.52,.55)
edge=material('FRAME | worn gunmetal',(.17,.21,.24),.55,.48)
deck=material('DECK | titanium panels',(.073,.085,.103),.48,.56)
dark=material('RECESSES | deep charcoal',(.016,.026,.04),.45,.52)
silver=material('HARDWARE | brushed aluminium',(.48,.57,.62),.72,.28)
ivory=material('ANTENNA | ceramic white',(.68,.73,.70),.35,.35)
orange=material('LIGHT | amber', (1,.18,.017),.15,.25,7)
cyan=material('LIGHT | cyan',(.008,.40,.85),.15,.24,3)
white=material('LIGHT | white',(.50,.7,1),.1,.2,2.5)
yellow=material('SAFETY | ochre yellow',(.72,.39,.055),.5,.4)
screen=material('DISPLAY | midnight glass',(.008,.042,.085),.4,.22,.12)
blueglass=material('DISPLAY | luminous blue surface',(.002,.18,.43),.03,.48,.8)
wood=material('PROPS | tan cases',(.27,.16,.075),.15,.65)
green=material('MINECRAFT | grass',(.09,.29,.045),0,.95)
greens=[material('MINECRAFT | pixel green %02d'%i,(.04+i*.014,.17+i*.023,.027+i*.004),0,.9) for i in range(7)]
stone=[material('ROCK | basalt facet %02d'%i,(.031+i*.0015,.045+i*.002,.060+i*.0025),.06,.89) for i in range(9)]
stonebg=[material('ROCK | distant blue %02d'%i,(.045+i*.005,.10+i*.007,.16+i*.009),0,1,.05) for i in range(7)]
for m in [steel,deck,edge]:
 nt=m.node_tree; p=nt.nodes.get('Principled BSDF'); tex=nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=42; tex.inputs['Detail'].default_value=2
 bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.14; bump.inputs['Distance'].default_value=.035; nt.links.new(tex.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
for m in stone:
 nt=m.node_tree; p=nt.nodes.get('Principled BSDF'); tex=nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=7; tex.inputs['Detail'].default_value=3;geo=nt.nodes.new('ShaderNodeNewGeometry');nt.links.new(geo.outputs['Position'],tex.inputs['Vector'])
 bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.25; bump.inputs['Distance'].default_value=.045; nt.links.new(tex.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
CACHE={}
def meshob(n,verts,faces,mat=None):
 me=bpy.data.meshes.new(n); me.from_pydata(verts,[],faces); me.update(); ob=bpy.data.objects.new(n,me); COL.objects.link(ob)
 if mat: me.materials.append(mat)
 return ob
def box(n,p,d,mat=steel,bevel=.025):
 key=('box',tuple(round(t,4) for t in d),mat.name,bevel)
 if key in CACHE: ob=bpy.data.objects.new(n,CACHE[key]); COL.objects.link(ob)
 else:
  x,y,z=[v/2 for v in d]; ob=meshob(n,[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat)
  if bevel:
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(d)*.2),segments=1,affect='EDGES');bm.to_mesh(ob.data);bm.free()
  CACHE[key]=ob.data
 ob.location=p; return ob
def cyl(n,p,r,h,mat=steel,N=24,r2=None):
 if r2 is None:r2=r
 key=('cyl',r,h,r2,mat.name,N)
 if key in CACHE:ob=bpy.data.objects.new(n,CACHE[key]); COL.objects.link(ob)
 else:
  v=[(rr*cos(i*2*pi/N),rr*sin(i*2*pi/N),z) for rr,z in [(r,-h/2),(r2,h/2)] for i in range(N)]
  f=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
  ob=meshob(n,v,f,mat);CACHE[key]=ob.data
 ob.location=p;return ob
def beam(n,a,b,r=.055,mat=steel,square=False):
 a,b=Vector(a),Vector(b);v=b-a
 o=box(n,(a+b)/2,(r*2,r*2,v.length),mat,.015) if square else cyl(n,(a+b)/2,r,v.length,mat,8)
 o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return o
def path(n,pts,r=.035,mat=steel):
 cu=bpy.data.curves.new(n,'CURVE'); cu.dimensions='3D'; cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=1
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for pt,co in zip(sp.points,pts):pt.co=(*co,1)
 ob=bpy.data.objects.new(n,cu);COL.objects.link(ob);cu.materials.append(mat);return ob
def ring(n,p,r,width=.035,mat=edge,a=0,b=2*pi,N=80):return path(n,[(p[0]+r*cos(a+(b-a)*i/N),p[1]+r*sin(a+(b-a)*i/N),p[2]) for i in range(N+1)],width,mat)
def area(n,p,target,power,color,size=5):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
 ob=bpy.data.objects.new(n,d);COL.objects.link(ob);ob.location=p;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();return ob
def point(n,p,power=70,color=(1,.22,.035),radius=.25):
 d=bpy.data.lights.new(n,'POINT');d.energy=power;d.color=color;d.shadow_soft_size=radius;o=bpy.data.objects.new(n,d);COL.objects.link(o);o.location=p
def text(n,body,p,size=.44,mat=white,rotation=(pi/2,0,0)):
 cu=bpy.data.curves.new(n,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.align_y='CENTER';cu.extrude=.002;cu.bevel_depth=.001;cu.space_character=1.08
 font='/System/Library/Fonts/Supplemental/Arial Narrow.ttf'
 if font not in CACHE:CACHE[font]=bpy.data.fonts.load(font)
 cu.font=CACHE[font];ob=bpy.data.objects.new(n,cu);COL.objects.link(ob);ob.location=p;ob.rotation_euler=rotation;cu.materials.append(mat);return ob
def label(body,p,w=4.2,size=.48):
 box(body+' | sign frame',p,(w,.16,.66),edge);box(body+' | sign inset',(p[0],p[1]-.09,p[2]),(w-.14,.045,.53),dark)
 text(body+' | lettering',body,(p[0],p[1]-.12,p[2]),size*1.22)
def bolt(p,axis='Y'):
 o=cyl('Fastener | M16',p,.042,.033,silver,6)
 if axis=='Y':o.rotation_euler.x=pi/2
def railseg(a,b,posts=True):
 a,b=Vector(a),Vector(b);L=(b-a).length
 for h in [.12,.53,1.05]:beam('Railing | tubular horizontal',a+Vector((0,0,h)),b+Vector((0,0,h)),.025 if h<1 else .039)
 if posts:
  for i in range(max(1,math.ceil(L/1.45))+1):
   p=a.lerp(b,i/max(1,math.ceil(L/1.45)));beam('Railing | stanchion',p,p+Vector((0,0,1.12)),.046);box('Railing | mounting shoe',p,(.17,.17,.09),edge)
def railarc(cx,cy,z,r,start,end,N=16):
 pts=[(cx+r*cos(start+(end-start)*i/N),cy+r*sin(start+(end-start)*i/N),z) for i in range(N+1)]
 for h in [.12,.53,1.05]:path('Railing | curved tube',[(x,y,zz+h) for x,y,zz in pts],.03,steel)
 for p in pts:beam('Railing | curved upright',p,(p[0],p[1],p[2]+1.12),.041)
def beacon(p):
 box('Bollard | base',p,(.22,.22,.2));box('Bollard | housing',(p[0],p[1],p[2]+.4),(.18,.18,.65),steel)
 box('Bollard | amber lens',(p[0],p[1]-.096,p[2]+.48),(.075,.028,.27),orange,.012);point('Bollard | pool',(p[0],p[1],p[2]+.7),32)
def strip(p,w=.35):
 box('Edge lamp | shroud',p,(w+.12,.14,.18),dark);box('Edge lamp | orange lens',(p[0],p[1]-.075,p[2]),(w,.045,.067),orange,.008)
def rock(n,p,rx,ry,h,seed=1,taper=.25,levels=12,N=15,mats=None):
 rng=random.Random(seed);mats=mats or stone;verts=[]
 if mats is stone: levels=int(levels*2.9);N=int(N*2.7)
 biases=[rng.uniform(.87,1.13) for _ in range(N)]
 for j in range(levels+1):
  t=j/levels; rr=(1-t)**(.72 if h < -4 else 1)*(1-taper)+taper
  dx=sin(t*5+seed)*rx*.16;dy=cos(t*4+seed)*ry*.13
  for i in range(N):
   ang=2*pi*(i/N)+sin(j*.75)*.075;fac=biases[i]*(1+.055*sin(j*.85+i*1.23)+.03*cos(j*1.74-i*.45))*rng.uniform(.975,1.025)*rr
   verts.append((p[0]+cos(ang)*rx*fac+dx,p[1]+sin(ang)*ry*fac+dy,p[2]+h*t+rng.uniform(-.085,.085)*(1 if j else 0)))
 faces=[]
 for j in range(levels):
  for i in range(N):
   a=j*N+i;b=j*N+(i+1)%N;c=b+N;d=a+N
   if rng.random()<.5:faces.extend([(a,b,c),(a,c,d)])
   else:faces.extend([(a,b,d),(b,c,d)])
 faces.extend([tuple(reversed(range(N))),tuple(range(levels*N,(levels+1)*N))])
 if h<0:faces=[tuple(reversed(f)) for f in faces]
 ob=meshob(n,verts,faces)
 for m in mats:ob.data.materials.append(m)
 for f in ob.data.polygons:f.material_index=rng.randrange(len(mats))
 return ob
def support(x,y,z,size=1):
 rock('Foundation | basalt buttress',(x,y,-3),2.05*size,2.32*size,z-.2,seed=int(abs(x*31+y*17))+57,taper=.44)
 box('Foundation | steel shoe',(x,y,z-3.15),(1.3*size,1.2*size,.5),edge)
 box('Foundation | vertical pier',(x,y,z-1.5),(.55,.55,3.2),steel)
def disc(cx,cy,z,r,name):
 cyl(name+' | deep structural drum',(cx,cy,z-.62),r,.98,steel,10 if name=='ABOUT ME' else 64)
 cyl(name+' | lower rim',(cx,cy,z-1.08),r+.03,.12,edge,64)
 cyl(name+' | top perimeter coping',(cx,cy,z-.08),r+.045,.17,edge,10 if name=='ABOUT ME' else 80)
 cyl(name+' | floor',(cx,cy,z),r-.13,.1,deck,10 if name=='ABOUT ME' else 80)
 for rr in [r-.4,r-.63,r*.49,r*.45,r*.22]:ring(name+' | concentric floor seam',(cx,cy,z+.063),rr,.010,dark)
 for i in range(24):
  a=i*2*pi/24
  beam(name+' | radial floor seam',(cx+r*.5*cos(a),cy+r*.5*sin(a),z+.065),(cx+(r-.15)*cos(a),cy+(r-.15)*sin(a),z+.065),.008,dark)
  x=cx+(r+.015)*cos(a);y=cy+(r+.015)*sin(a)
  o=box(name+' | skirt ribs',(x,y,z-.55),(.14,.18,1.14),edge);o.rotation_euler.z=a
  for zz in [z-.15,z-.92]:
   o=cyl('Drum | rivet',(x,y,zz),.038,.05,silver,6);o.rotation_euler=(pi/2,0,a)
 for dx,dy in [(-r*.68,-r*.5),(r*.68,-r*.5),(-r*.68,r*.5),(r*.68,r*.5)]:support(cx+dx,cy+dy,z, .83)
 for dx in [-r*.7,r*.7]:beam(name+' | diagonal support',(cx+dx,cy,z-3.8),(cx,cy,z-1),.16,steel,True)
def rectdeck(n,cx,cy,z,w,d):
 radius=.8 if 'Experiences' in n else 0
 outline=[]
 if radius:
  for xx,yy,ang in [(w/2-radius,d/2-radius,0),(-w/2+radius,d/2-radius,pi/2),(-w/2+radius,-d/2+radius,pi),(w/2-radius,-d/2+radius,3*pi/2)]:
   for j in range(5):
    a=ang+j*pi/8;outline.append((xx+radius*cos(a),yy+radius*sin(a)))
 def prism(title,poly,bottom,top,mat):
  k=len(poly);v=[(cx+x,cy+y,zz) for zz in [bottom,top] for x,y in poly]
  f=[tuple(reversed(range(k))),tuple(range(k,2*k))]+[(i,(i+1)%k,(i+1)%k+k,i+k) for i in range(k)]
  return meshob(title,v,f,mat)
 def clipped(poly):
  for a,b in zip(outline,outline[1:]+outline[:1]):
   result=[]
   def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
   if not poly:break
   for p,q in zip(poly,poly[1:]+poly[:1]):
    sp,sq=side(p),side(q)
    if sp>=-1e-7:result.append(p)
    if (sp>=0)!=(sq>=0):
     t=sp/(sp-sq);result.append((p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t))
   poly=result
  return poly
 if radius:prism(n+' | rounded structural frame',outline,z-1,z-.1,steel)
 else:box(n+' | structural frame',(cx,cy,z-.55),(w,d,.9),steel,.07)
 for i in range(math.ceil(w/1.35)):
  for j in range(math.ceil(d/1.25)):
   sx=w/math.ceil(w/1.35);sy=d/math.ceil(d/1.25)
   if radius and i in [0,math.ceil(w/1.35)-1] and j in [0,math.ceil(d/1.25)-1]:
    x=-w/2+sx*(i+.5);y=-d/2+sy*(j+.5);hx=(sx-.028)/2;hy=(sy-.028)/2
    poly=clipped([(x-hx,y-hy),(x+hx,y-hy),(x+hx,y+hy),(x-hx,y+hy)])
    if len(poly)>2:prism(n+' | curved corner floor tile',poly,z-.075,z+.075,deck)
   else:box(n+' | floor tile',(cx-w/2+sx*(i+.5),cy-d/2+sy*(j+.5),z),(sx-.028,sy-.028,.15),deck,.018)
 for x in [cx-w/2+.15,cx+w/2-.15]:
  box(n+' | side rim',(x,cy,z-.02),(.22,d-2*radius,.27),edge)
 for yy in [cy-d/2,cy+d/2]:
  box(n+' | edge beam',(cx,yy,z-.32),(w-2*radius,.2,.68),edge)
  for x in [cx-w/2+1,cx+w/2-1]:strip((x,yy-.12,z-.35))
 if radius:
  for zz in [z-.06,z-.68]:path(n+' | rounded perimeter coping',[(cx+x,cy+y,zz) for x,y in outline+[outline[0]]],.07,edge)
 for x in [cx-w*.36,cx+w*.36]:
  for y in [cy-d*.32,cy+d*.32]:support(x,y,z,1)
  beam(n+' | underframe diagonal',(x,cy-d*.3,z-5),(cx,cy-d*.3,z-.8),.2,steel,True)
def bridge(n,a,b,w=1.65,stair=False):
 a,b=Vector(a),Vector(b);v=b-a;L=Vector((v.x,v.y,0)).length;u=Vector((v.x,v.y,0)).normalized();side=Vector((-u.y,u.x,0));ang=math.atan2(u.y,u.x)
 count=math.ceil(L/(.30 if stair else .72))
 for i in range(count):
  t=(i+.5)/count;p=a.lerp(b,t);p.z=a.z+(b.z-a.z)*(i+1)/count if stair else p.z
  o=box(n+' | '+('stair tread' if stair else 'deck panel'),p,(L/count-.025,w,.12),wood if 'Minecraft' in n else deck,.02);o.rotation_euler.z=ang
  if stair:
   q=p-u*(L/count/2-.04);o=box(n+' | tread nosing',q,(.055,w-.08,.025),silver,.008);o.rotation_euler.z=ang
 for sign in [-1,1]:
  aa=a+side*(w/2)*sign;bb=b+side*(w/2)*sign
  beam(n+' | longitudinal girder',aa-Vector((0,0,.25)),bb-Vector((0,0,.25)),.14,steel,True);railseg(aa,bb)
  for i in range(0,count,3):
   p=a.lerp(b,i/count)+side*(w/2)*sign
   if i%6==0:beacon(p)
 for i in range(max(1,int(L/1.2))):
  p=a.lerp(b,i/max(1,int(L/1.2)));beam(n+' | transverse joist',p-side*w*.55-Vector((0,0,.32)),p+side*w*.55-Vector((0,0,.32)),.075,steel,True)
 for i in range(max(1,int(L/2))):
  p=a.lerp(b,i/max(1,int(L/2)));q=a.lerp(b,(i+1)/max(1,int(L/2)))
  for sign in [-1,1]:beam(n+' | lattice diagonal',p+side*w/2*sign-Vector((0,0,.65)),q+side*w/2*sign-Vector((0,0,.18)),.055,steel)
def cabinet(n,p,w=.8,h=1.55):
 x,y,z=p;box(n+' | carcass',(x,y,z+h/2),(w,.62,h),steel);box(n+' | face',(x,y-.33,z+h/2),(w-.08,.045,h-.09),edge)
 for xx in [x-w*.34,x+w*.34]:
  for zz in [z+.15,z+h-.15]:bolt((xx,y-.36,zz))
 for i in range(5):box(n+' | vent',(x,y-.365,z+.28+i*.07),(w*.55,.022,.025),dark,.003)
 box(n+' | latch',(x+w*.28,y-.385,z+h*.53),(.035,.05,.18),silver,.005)
 for i in range(2):box(n+' | status LED',(x-w*.27+i*.11,y-.373,z+h-.22),(.045,.025,.025),cyan if i else orange,.003)
def monitor(n,p,w,h,ang=0,content=0):
 # parent a complete reusable display assembly, local plane faces -Y.
 before=set(COL.objects);x,y,z=p
 box(n+' | display enclosure',(x,y,z),(w,.12,h),steel,.025);box(n+' | screen',(x,y-.071,z),(w-.10,.015,h-.10),screen,.006)
 for sx in [-1,1]:box(n+' | cyan perimeter',(x+sx*(w/2-.05),y-.083,z),(.018,.015,h-.065),cyan,.002)
 for sz in [-1,1]:box(n+' | cyan perimeter',(x,y-.083,z+sz*(h/2-.045)),(w-.065,.015,.018),cyan,.002)
 rng=random.Random(content+131)
 for i in range(16):
  yy=z+h*.39-i*h*.051;length=w*rng.uniform(.1,.42)
  box(n+' | data row',(x-w*.40+length/2,y-.088,yy),(length,.007,.006 if i%3 else .010),cyan if i%4 else white,.001)
 if content==1:
  for i in range(29):
   v=.08+rng.random()*h*.25;xx=x-w*.35+i*w*.027
   box(n+' | bar graph',(xx,y-.10,z-h*.30+v/2),(.019,.006,v),cyan,.001)
  path(n+' | live graph',[(x-w*.35+i*w*.027,y-.10,z+h*.07+sin(i*.85)*h*.038+rng.random()*.10) for i in range(29)],.007,cyan)
  for zz in [-.3,-.1,.1]:box(n+' | graph rule',(x,y-.105,z+zz*h),(w*.8,.006,.006),silver,.001)
 if ang:
  bpy.context.view_layer.update()
  from mathutils import Matrix
  M=Matrix.Translation(Vector(p))@Matrix.Rotation(ang,4,'Z')@Matrix.Translation(-Vector(p))
  for o in set(COL.objects)-before:o.matrix_world=M@o.matrix_world
def console(p,w=1.3):
 x,y,z=p;box('Console | pedestal',(x,y,z+.35),(w,.72,.7),steel);o=box('Console | sloped upper',(x,y-.12,z+.76),(w+.1,.86,.15),edge);o.rotation_euler.x=math.radians(10)
 box('Console | cyan front strip',(x,y-.51,z+.68),(w*.84,.026,.035),cyan,.004)
 for i in range(6):box('Console | keypad',(x-w*.28+i*.1,y-.37,z+.857),(.052,.1,.015),cyan if i==0 else silver,.003)
def alcove(n,cx,y,z,w,h,depth=3.5):
 # Coherent rear wall, side walls, ceiling and chamfered structural portal.
 box(n+' | rear bulkhead',(cx,y+depth,z+h*.5),(w,.3,h),steel,.04)
 for i in range(6):
  x=cx-w/2+(i+.5)*w/6;box(n+' | recessed rear panel',(x,y+depth-.17,z+h*.5),(w/6-.15,.05,h-.25),dark)
 for sx in [-1,1]:box(n+' | side enclosure',(cx+sx*w/2,y+depth/2,z+h*.47),(.24,depth,h*.94),steel)
 box(n+' | ceiling',(cx,y+depth/2,z+h),(w,depth,.13),steel)
 pts=[(cx-w/2,y,z),(cx-w/2,y,z+h*.69),(cx-w*.35,y,z+h),(cx+w*.36,y,z+h),(cx+w/2,y,z+h*.74),(cx+w/2,y,z)]
 for i in range(len(pts)-1):
  beam(n+' | angular portal frame',pts[i],pts[i+1],.18,edge,True)
  a=Vector(pts[i]);b=Vector(pts[i+1]);a.y-=.2;b.y-=.2;beam(n+' | inset trim',a,b,.05,steel,True)
 for sx in [-.32,0,.32]:
  box(n+' | overhead strip',(cx+sx*w,y+depth*.65,z+h-.17),(1.1,.19,.045),white)
  area(n+' | overhead pool',(cx+sx*w,y+depth*.65,z+h-.3),(cx+sx*w,y+depth*.65,z),140,(.7,.82,1),1.8)

# 01. Canonical comparison camera. Fixed once the first blockout is rendered.
collection('00 | CAMERA & lighting')
cam=bpy.data.cameras.new('Canonical orthographic comparison');camera=bpy.data.objects.new('CAMERA | Reference comparison — locked',cam);COL.objects.link(camera)
camera.location=(0,-64,38);target=Vector((0,5,8.6));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=44.5;cam.lens=47;S.camera=camera;camera.lock_location=(True,True,True);camera.lock_rotation=(True,True,True);camera.lock_scale=(True,True,True)
camera['purpose']='Canonical reference comparison. Do not move between critique passes.';camera['reference']='reference.png';camera['estimated_elevation_degrees']=23.08
S.world=bpy.data.worlds.new('Cavern | dim blue ambient');S.world.use_nodes=True;S.world.node_tree.nodes.get('Background').inputs[0].default_value=(.055,.095,.155,1);S.world.node_tree.nodes.get('Background').inputs[1].default_value=.25
area('Key | broad cool shaft',(0,-10,26),(0,4,3),4600,(.62,.74,1),19)
area('Fill | front softbox',(0,-22,13),(0,7,9),1900,(.65,.78,1),23)
area('Chasm | blue backlight',(0,25,19),(0,4,5),6200,(.20,.40,.72),16)
area('Water | specular shaft',(-4,4,15),(2,-7,-2),1900,(.25,.45,.7),13)

# 02. Large geological masses and hanging formations.
collection('01 | CAVERN • structural geology')
for i,(x,y,rx,ry,h) in enumerate([(-21,8,3.0,7,28),(-17,16,4,6,27),(-11,21,4,5,29),(-9,28,2.0,3,25),(22.5,8,2.9,7,27),(20,19,5,7,30),(13,24,4,4,27),(12,27,2.5,4,23)]):rock('Cavern | massive fluted wall %02d'%i,(x,y,-4),rx,ry,h,100+i,taper=.82,levels=25,N=22)
for i in range(24):
 side=-1 if i<12 else 1;x=side*random.uniform(21,24);y=random.uniform(-13,24)
 rock('Cavern | fractured side spire %02d'%i,(x,y,-5),random.uniform(1.5,3.2),random.uniform(2,4.5),random.uniform(14,30),300+i,.40,20,17)
for i,(x,y,sz,h) in enumerate([(-19,13,3.7,-9),(-15,17,3.5,-7),(-10,24,2.8,-16),(-5,27,3.8,-20.2),(1.8,26,4.2,-20.2),(6.1,25,2.1,-17),(12,25,2.5,-10),(17,20,3,-7),(20,8,3,-6)]):
 rock('Ceiling | hanging tooth %02d'%i,(x,y,28),sz,sz*.9,h,700+i,.045,18,19)
# perimeter canopy pieces, open central cavern vista
for i in range(12):
 x=-23+i*4.2
 rock('Ceiling | roof arch mass %02d'%i,(x,20,27),3.6,7,-random.uniform(2,4),810+i,.8,8,17)
collection('02 | CAVERN • distant depth layers')
for layer in range(3):
 for i in range(9):
  rock('Distant cavern ridge %d.%d'%(layer,i),(-28+i*7+layer*2,36+layer*13,-6),6,5,random.uniform(11,22),1100+layer*40+i,.15,13,15,stonebg)
for i,(x,y,h) in enumerate([(-1.1,19,13),(2,25,14),(-7,28,21),(10,30,18),(0,-3,6.1),(-3,-16,6.4),(3,-3,4.4)]):rock('Chasm | solitary spire %02d'%i,(x,y,-3),(2.4 if i==4 else 1.25) if y<0 else 2.6,(2.4 if i==4 else 1.35) if y<0 else 2.4,h,1200+i,.025,14,16)
collection('03 | WATER • real-time displaced surface')
water=material('WATER | abyss blue',(.018,.075,.135),.36,.28)
nt=water.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['IOR'].default_value=1.333;p.inputs['Coat Weight'].default_value=.20;p.inputs['Coat Roughness'].default_value=.2;p.inputs['Specular IOR Level'].default_value=.5
tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=5.5;tex.inputs['Detail'].default_value=3;tex.inputs['Roughness'].default_value=.72
bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.12;nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
v=[];f=[];nx=220;ny=220
for j in range(ny+1):
 for i in range(nx+1):
  x=-36+i*72/nx;y=-32+j*100/ny;z=.9+.035*sin(x*2.4+y*3.8)+.02*sin(x*6-y*1.5)+.018*sin(x*13+y*11)
  v.append((x,y,z))
for j in range(ny):
 for i in range(nx):
  a=j*(nx+1)+i;f.append((a,a+1,a+nx+2,a+nx+1))
ob=meshob('Water | rippled triangulatable basin',v,f,water)
for poly in ob.data.polygons:poly.use_smooth=True

# 03. Primary platforms, 04. circulation.
collection('10 | PROJECTS • circular hub')
disc(0,0,7.3,5.35,'PROJECTS');cyl('PROJECTS | extended lower drum',(0,0,5.90),5.12,.4,steel,64);railarc(0,0,7.42,5.35,-pi*.75,-pi*.16,20);railarc(0,0,7.42,5.35,.13*pi,.65*pi,15);railarc(0,0,7.42,5.35,.88*pi,1.07*pi,7)
label('PROJECTS',(0,-5.37,6.93),3.65,.47)
for x in [-2.15,2.15]:
 box('Hub | front equipment rib',(x,-5.05,6.98),(.43,.25,1.15),steel)
 for z in [6.65,6.84,7.11]:strip((x,-5.2,z),.28)
ring('Hub | landing bullseye',(0,0,7.365),1.02,.035,silver);cyl('Hub | center plate',(0,0,7.38),.50,.035,edge,48)
collection('11 | EXPERIENCES • two-tier gallery')
rectdeck('Experiences | lower Work',-13,-7,4.85,11.2,4.6)
rectdeck('Experiences | upper Education',-13,-2.8,6.35,11.2,3.8)
label('EXPERIENCES',(-12.8,-9.43,4.5),5.65,.50)
label('WORK',(-17.1,-7.2,5.7),2.0,.4);label('EDUCATION',(-17,-3.75,7.05),2.6,.39)
railseg((-17.7,-9.3,4.95),(-8.2,-9.3,4.95));railseg((-18.5,-8.5,4.95),(-18.5,-5,4.95));railseg((-7.4,-8.5,4.95),(-7.4,-5.1,4.95));railarc(-17.7,-8.5,4.95,.8,pi,1.5*pi,4);railarc(-8.2,-8.5,4.95,.8,1.5*pi,2*pi,4)
bridge('Education → Work | stair',(-8,-2.5,6.42),(-8,-5.8,4.92),1.65,True)
bridge('Experience | left stair',(-18,-2.6,6.43),(-18,-6,4.94),1.15,True)
collection('12 | CONTACT • elevated communications')
rectdeck('Contact',-12.5,11,10.65,7.6,4.8);label('CONTACT',(-12.5,8.47,10.26),3.6,.46)
railseg((-16.2,8.63,10.76),(-9.6,8.63,10.76));railseg((-16.25,8.6,10.75),(-16.25,13.3,10.75));railseg((-16.25,13.3,10.75),(-8.75,13.3,10.75))
collection('13 | ABOUT ME • holographic laboratory')
disc(13.25,-1.2,6.9,5.55,'ABOUT ME');label('ABOUT ME',(13.25,-6.78,6.52),4.8,.48)
railarc(13.25,-1.2,7.01,5.55,-pi*.87,-pi*.25,20)
alcove('About | hangar',13.5,1.1,6.95,10.4,4.5,3.3)
for x in [9,10,16,17.5]:cabinet('About | equipment',(x,3.0,6.99),.9,1.3)
collection('14 | WORKSHOP • carved cave hangar')
rectdeck('Workshop',14.3,14.3,12.3,10.2,6.8);label('WORKSHOP',(14.3,10.76,11.98),4.4,.54)
railseg((9.2,10.96,12.42),(19.3,10.96,12.42));railseg((9.2,10.96,12.42),(9.2,15.6,12.42))
alcove('Workshop | portal',14.3,12.5,12.43,9.9,5.3,3.9)
collection('15 | CIRCULATION • bridges & stairs')
bridge('Projects → Experiences',(-4.65,-2.2,7.35),(-8.2,-2.2,7.09),2.1)
bridge('Projects → About',(4.95,-.8,7.37),(8.5,-2.0,6.96),2.0)
bridge('Projects → Contact | lower span',(-3.8,3.6,7.37),(-7.5,6.0,8.0),1.65)
bridge('Contact | lower stair',(-7.5,6,8),(-7.5,8.1,9.12),1.65,True)
bridge('Contact | turn landing',(-7.5,8.1,9.12),(-6.5,9.1,9.12),1.65)
bridge('Contact | upper stair',(-6.5,9.1,9.12),(-8.85,11.0,10.73),1.65,True)
bridge('Rear connector',(-11,13.2,10.7),(-3,17,9.5),1.35)
bridge('Minecraft | timber approach',(-3,17,9.5),(5.5,18.1,9.55),1.45)
bridge('Workshop | rear access',(7.2,19.2,9.55),(10.0,18.0,12.4),1.35,True)
bridge('About | descending exit',(17.9,-4.1,6.94),(17.9,-8.7,3.8),1.5,True)
bridge('About | lower perimeter path',(17.9,-8.7,3.8),(13.5,-16,2.4),2)

# 05. Hero objects: concave communications dish, multi-segment tower.
collection('20 | CONTACT • antenna & operations')
x=-12.65;y=11.3;z=10.76
cyl('Antenna | heavy footing',(x,y,z+.13),.72,.25,edge,32)
for zz,r,h,mat in [(z+.42,.48,.5,ivory),(z+1.9,.39,2.5,ivory),(z+3.2,.47,.22,steel),(z+3.7,.31,1.0,ivory),(z+4.6,.23,.8,ivory),(z+5.12,.18,.4,ivory),(z+6,.047,1.65,silver)]:cyl('Antenna | stacked mast',(x,y,zz),r,h,mat,20)
for h in [.9,1.4,2.2,2.8,3.65,4.1,4.8]:cyl('Antenna | service collar',(x,y,z+h),.44 if h<3 else .30,.075,silver,24)
for sx in [-1,1]:
 beam('Antenna | side spar',(x+sx*.52,y,z+.6),(x+sx*.52,y,z+3.7),.065,ivory)
 for h in [1,1.7,2.8,3.5]:beam('Antenna | cross bracket',(x,y,z+h),(x+sx*.62,y,z+h),.07,ivory)
 box('Antenna | vertical ceramic panel',(x+sx*.3,y-.4,z+2.15),(.38,.20,1.15),ivory)
 beam('Antenna | ground brace',(x+sx*.8,y-.45,z+.12),(x+sx*.23,y,z+1.6),.07,silver)
for i in range(9):
 xx=x+(i-4)*.08;beam('Antenna | phased array fin',(xx,y,z+6.5-abs(i-4)*.035),(xx,y,z+6.85+(.13 if i%2 else 0)),.012,ivory)
box('Antenna | array crossbar',(x,y,z+6.65),(.78,.04,.045),silver)
# Dish faces front/left/up, with actual parabolic bowl, radial ribs and feed boom.
dc=Vector((-15,11.5,13.6));direction=Vector((-.48,-.65,.63)).normalized();Q=direction.to_track_quat('Z','Y');verts=[];faces=[];NR=8;NN=48
for j in range(NR+1):
 rr=1.2*j/NR
 for i in range(NN):
  a=2*pi*i/NN;verts.append(tuple(dc+Q@Vector((rr*cos(a),rr*sin(a),.33*(rr/1.2)**2))))
for j in range(NR):
 for i in range(NN):a=j*NN+i;b=j*NN+(i+1)%NN;faces.append((a,b,b+NN,a+NN))
meshob('Dish | parabolic reflector',verts,faces,silver)
path('Dish | rolled rim',[tuple(dc+Q@Vector((1.2*cos(i*2*pi/NN),1.2*sin(i*2*pi/NN),.33))) for i in range(NN+1)],.045,edge)
for i in range(12):
 a=i*2*pi/12;path('Dish | radial rib',[tuple(dc+Q@Vector((1.2*t/8*cos(a),1.2*t/8*sin(a),.33*(t/8)**2-.028))) for t in range(9)],.017,steel)
beam('Dish | mounting pedestal',(-15,11.5,z),dc,.16,steel,True)
for i in range(3):
 a=i*2*pi/3;beam('Dish | feed tripod',dc+Q@Vector((1.05*cos(a),1.05*sin(a),.26)),dc+direction*1.1,.029,steel)
cyl('Dish | receiver',dc+direction*1.12,.095,.22,dark,12).rotation_euler=Q.to_euler()
for px in [-15.3,-10.4]:
 console((px,9.8,z),1.25);monitor('Contact | blue command display',(px,10.0,z+1.3),1.15,.83,0,1)
cabinet('Contact | server',(-9.45,11.1,z),.95,1.6)

collection('21 | PROJECTS • panoramic workstation')
for px,py,w,ang in [(-2.45,2.30,1.5,-.38),(0,2.65,3.15,0),(2.45,2.30,1.5,.38)]:
 console((px,py,7.37),w);monitor('Projects | holographic monitor',(px,py+.12,9.18),w,1.8,ang,1 if px==0 else 2)
 beam('Projects | monitor stalk',(px,py,8.15),(px,py,8.55),.06,silver)
box('Projects | central underlight',(0,2.10,7.62),(1.4,.075,.05),cyan)
area('Projects | cyan screen spill',(0,1.8,9),(0,-1,7.3),100,(.025,.48,1),4)

collection('22 | ABOUT ME • circular holographic table')
x=13.2;y=-1.9;z=6.97
cyl('Holo table | plinth',(x,y,z+.18),1.62,.3,steel,64);cyl('Holo table | undercut pedestal',(x,y,z+.48),1.42,.65,dark,64)
cyl('Holo table | outer drum',(x,y,z+.95),2.36,.59,steel,64);cyl('Holo table | upper lip',(x,y,z+1.28),2.43,.11,edge,64)
cyl('Holo table | luminous inset',(x,y,z+1.33),2.12,.035,blueglass,64);ring('Holo table | cyan rim',(x,y,z+1.36),2.17,.035,cyan)
for i in range(16):
 a=i*2*pi/16;xx=x+2.35*cos(a);yy=y+2.35*sin(a)
 o=box('Holo table | segmented drum panel',(xx,yy,z+.94),(.41,.1,.38),edge,.018);o.rotation_euler.z=a-pi/2
 if i%2==0:
  o=box('Holo table | blue vent',(x+2.41*cos(a),y+2.41*sin(a),z+.97),(.075,.024,.26),cyan,.008);o.rotation_euler.z=a-pi/2
 ring('Holo table | trim ring',(x,y,z+.69),2.31,.025,silver)
ring('About | safety annulus',(x,y,z+.045),3.9,.035,yellow)
area('Hologram | cyan spill',(x,y,z+1.7),(x,y,z),260,(.015,.55,1),3.3)

collection('23 | EXPERIENCES • gallery & cabinets')
alcove('Education | open storage shelter',-13.7,-.5,6.46,9.6,3.15,2.1)
for i in range(6):cabinet('Education | archive cabinet',(-17.4+i*1.0,.8,6.45),.86,random.choice([.65,1.2,1.6]))
for row,y,z,mat in [('Education',-2.4,6.46,cyan),('Work',-6.2,4.95,orange)]:
 box(row+' | continuous exhibit bench',(-12.7,y,z+.92),(7.7,.47,.16),steel)
 box(row+' | luminous timeline',(-12.7,y-.245,z+.92),(7.4,.035,.035),mat,.003)
 for i in range(5):
  xx=-16+i*1.65
  cyl(row+' | exhibit pedestal',(xx,y,z+.42),.085,.8,silver,12);cyl(row+' | pedestal foot',(xx,y,z+.08),.23,.09,steel,16)
  monitor(row+' | milestone screen',(xx,y+.035,z+1.34),.56,.65,0,3+i)
  # Individual emissive corner and image motif geometry.
  path(row+' | milestone mountain',[(xx-.19,y-.045,z+1.30),(xx-.09,y-.045,z+1.45),(xx+.02,y-.045,z+1.37),(xx+.16,y-.045,z+1.54)],.014,mat)
 for xx in [-16.5,-9]:point(row+' | exhibit glow',(xx,y-.4,z+1.15),32,(.04,.33,1) if row=='Education' else (1,.25,.055),.45)

collection('24 | WORKSHOP • workbench machinery & tools')
# Warm back wall and layered service cabinetry.
box('Workshop | rear tool board',(14.5,17.11,15.2),(5.5,.15,1.85),wood)
for x in [11.3,12.6,14,15.4,17]:
 box('Workshop | bench cabinet',(x,15.7,13.05),(1.2,.95,1.2),edge)
 for j in range(4):
  box('Workshop | drawer',(x,15.19,12.65+j*.25),(1.1,.035,.20),steel,.01);box('Workshop | drawer pull',(x,15.14,12.68+j*.25),(.32,.045,.024),silver,.004)
box('Workshop | solid worktop',(14.3,15.55,13.71),(7.2,1.5,.16),silver)
for i in range(21):
 x=12.05+i*.24;h=random.uniform(.4,.8);z=15.5
 beam('Workshop | hanging tool shaft',(x,16.03,z),(x,16.03,z-h),.027,silver)
 box('Workshop | hanging tool handle',(x,16.03,z-h+.09),(.075,.06,.22),yellow if i%3 else steel,.014)
 ringob=cyl('Workshop | wrench head',(x,16.01,z),.075,.045,silver,8);ringob.rotation_euler.x=pi/2
for x in [12.7,15.7]:
 box('Workshop | amber task lamp',(x,15.92,16.24),(2.0,.2,.05),orange)
 area('Workshop | warm task wash',(x,15.5,16.1),(x,15.7,13.5),230,(1,.43,.13),2.2)
# Left supply rack with shelves and small reusable containers.
for x in [9.9,11.35]:beam('Workshop | shelf upright',(x,14.2,12.5),(x,14.2,16.25),.055,edge,True)
for h in [12.55,13.3,14.05,14.8,15.55,16.25]:
 box('Workshop | shelf',(10.65,14.42,h),(1.7,.7,.09),edge)
 for i in range(3):
  if h<16:box('Workshop | parts bin',(10.15+i*.45,14.35,h+.22),(.34,.43,.35),wood if i%2 else steel)
# Robotics arm with articulated joints and two-finger gripper.
base=Vector((17,14.75,13.85));cyl('Robot | swivel base',base,.37,.18,steel,24)
pts=[base+Vector((0,0,.12)),base+Vector((-.2,0,.8)),base+Vector((-.75,-.05,1.35)),base+Vector((-1.1,-.3,.85))]
for a,b in zip(pts[:-1],pts[1:]):
 beam('Robot | articulated ochre arm',a,b,.11,yellow,True)
 o=cyl('Robot | pivot bearing',a,.17,.21,steel,20);o.rotation_euler.x=pi/2
for sx in [-1,1]:beam('Robot | gripper jaw',pts[-1]+Vector((sx*.09,0,0)),pts[-1]+Vector((sx*.09,0,-.24)),.035,silver)
# Rolling machine trolley in front of back wall.
for x in [13.6,15.1]:
 for yy in [13.25,14.1]:
  beam('Workshop | cart leg',(x,yy,12.55),(x,yy,13.7),.055,steel,True);o=cyl('Workshop | caster',(x,yy,12.58),.12,.08,dark,12);o.rotation_euler.x=pi/2
for z in [12.76,13.62]:box('Workshop | trolley shelf',(14.35,13.67,z),(1.8,1.1,.12),edge)
for x in [13.95,14.5]:
 o=cyl('Workshop | engine cylinder',(x,13.65,13.91),.24,.43,steel,20);o.rotation_euler.y=pi/2
 for dx in [-.18,-.10,0,.1,.18]:o=cyl('Workshop | engine cooling rib',(x+dx,13.65,13.91),.28,.028,silver,20);o.rotation_euler.y=pi/2
for i in range(5):
 x=12.1+i*.74;path('Workshop | hanging service cable',[(x,15.5,17.3),(x,15.5,16.8),(x+.13,15.45,16.42),(x+.40,15.5,16.45),(x+.52,15.5,17.2)],.023,dark)

collection('25 | MINECRAFT • hidden block shrine')
rock('Minecraft | foundation cliff',(6.5,19,-3),2.75,3.4,12.55,1401,.72,20,16)
for ix in range(7):
 for iy in range(5):
  zz=9.6+(1 if ix in [0,6] and iy>1 else 0)*.52
  box('Minecraft | terrain cube',(4.9+ix*.57,17.9+iy*.57,zz-.28),(.56,.56,.56),greens[(ix+iy)%7],.008)
# Block doorway leaves a real portal opening.
for j in range(7):
 for i in range(8):
  if 2<=i<=5 and j<4:continue
  box('Minecraft | masonry voxel',(4.4+i*.58,20.3,9.85+j*.57),(.56,.66,.55),stone[(i+j*3)%len(stone)],.025)
box('Minecraft | dark mine opening',(6.45,20.7,10.8),(2.3,.16,2.5),dark)
# Recognizable pixel creeper.
x=8.0;y=18.8;z=10
box('Creeper | head',(x,y,z+1.23),(.54,.53,.53),green,.008);box('Creeper | body',(x,y,z+.62),(.34,.35,.72),green,.005)
for dx in [-.15,.15]:
 for dy in [-.16,.16]:box('Creeper | foot',(x+dx,y+dy,z+.15),(.22,.23,.3),greens[3],.004)
for dx in [-.14,.14]:box('Creeper | square eye',(x+dx,y-.27,z+1.32),(.115,.01,.115),dark,0)
for dx,dz,w,h in [(0,1.19,.10,.16),(-.085,1.08,.11,.16),(.085,1.08,.11,.16)]:box('Creeper | pixel mouth',(x+dx,y-.272,z+dz),(w,.013,h),dark,0)
box('Minecraft | crafting crate',(6.1,18.1,9.97),(.7,.7,.7),wood)
for i in [-1,0,1]:
 box('Minecraft | crafting grid',(6.1+i*.19,18.1,10.33),(.027,.69,.014),dark,0);box('Minecraft | crafting grid',(6.1,18.1+i*.19,10.33),(.69,.027,.014),dark,0)
for x,y,z in [(5.3,19.5,11),(7.2,20,11.8)]:
 beam('Minecraft | torch stick',(x,y,z-.4),(x,y-.15,z),.06,wood,True);cyl('Minecraft | flame',(x,y-.15,z+.1),.085,.25,orange,5,r2=.015);point('Minecraft | warm torch',(x,y-.4,z+.2),100)

collection('26 | SECONDARY • service details')
for x,y,z in [(-17,-7,4.95),(-7,-7,4.95),(-17.5,-1,6.2),(-9.4,9,10.76),(9.5,-5,7.03),(16.4,-5.5,7.03),(9.5,11.5,12.4),(18.8,11.5,12.4)]:beacon((x,y,z))
for x,y,z in [(-18,0,6.2),(16,3,7.05),(17,2.7,7.05),(10.8,15,12.5),(-10.7,12,10.76)]:
 box('Cargo | transport case',(x,y,z+.25),(.58,.48,.5),wood)
 for dx in [-.19,.19]:box('Cargo | reinforcing strap',(x+dx,y-.25,z+.25),(.043,.025,.48),steel,.006)
for x,y,z in [(-17,-8,4.99),(-14,-8,4.99),(-11,-8,4.99),(11,-5.5,7.03),(15,-5.5,7.03)]:box('Safety | floor dash',(x,y,z),(.65,.035,.012),yellow,.001)
for x,y,z in [(-17,1.2,7.8),(11,3.9,8.7)]:
 path('Service | bundled pipe',[(x,y,z),(x+1,y,z),(x+1.2,y,z-.2),(x+1.2,y,z-1.4)],.065,steel)

exec(compile(open(os.path.join(ROOT,'enrich_scene.py')).read(),'enrich_scene.py','exec'))

# Calibrated composition pass: retain canonical camera, relocate the architecture.
bpy.context.view_layer.update()
def compose(prefixes,pivot,angle=0,delta=(0,0,0),sx=1,sy=1):
 M=Matrix.Translation(Vector(delta))@Matrix.Translation(Vector(pivot))@Matrix.Rotation(math.radians(angle),4,'Z')@Matrix.Diagonal((sx,sy,1,1))@Matrix.Translation(-Vector(pivot))
 for co in list(bpy.data.collections):
  if any(co.name.startswith(t) for t in prefixes):
   for ob in list(co.objects):ob.matrix_world=M@ob.matrix_world
 return M
MP=compose(['10 |','21 |'],(0,0,7.3),delta=(0,5.4,.35),sx=1.08,sy=1.08)
ME=compose(['11 |','23 |'],(-13,-5,5.5),28,delta=(-.7,0,0),sx=1.18,sy=1.08)
MC=compose(['12 |','20 |'],(-12.5,11,10.65),10,delta=(0,0,.7))
MA=compose(['13 |','22 |'],(13.25,-1.2,6.9),-14,delta=(.5,0,.8),sx=1.13,sy=1.02)
MW=compose(['14 |','24 |'],(14.3,14.3,12.3),-9,delta=(.4,-.2,-.85))
# Rebuild connecting spans to their transformed endpoints, with uninterrupted landings.
co=bpy.data.collections.get('15 | CIRCULATION • bridges & stairs')
for ob in list(co.objects):bpy.data.objects.remove(ob,do_unlink=True)
COL=co
def tx(M,p):return tuple(M@Vector(p))
bridge('Projects → Experiences',tx(MP,(-4.72,-2.1,7.36)),tx(ME,(-7.42,-2.4,6.44)),2.1)
bridge('Projects → About',tx(MP,(4.92,-1.3,7.37)),tx(MA,(8.65,-1.5,6.96)),2.0)
bridge('Projects → Contact | lower span',tx(MP,(-3.6,3.8,7.37)),(-7.5,8,8.0),1.65)
bridge('Contact | lower stair',(-7.5,8,8),(-7.5,10.1,9.12),1.65,True)
bridge('Contact | turn landing',(-7.5,10.1,9.12),(-6.5,11.1,9.12),1.65)
bridge('Contact | upper stair',(-6.5,11.1,9.12),tx(MC,(-8.85,11.0,10.73)),1.65,True)
bridge('Rear connector',tx(MC,(-11,13.2,10.7)),(-9,24,4.9),1.2)
bridge('Rear hidden causeway',(-9,24,4.9),(-3,24,4.9),1.2)
bridge('Minecraft | approach',(-3,24,4.9),(5.5,18.1,9.55),1.3,True)
bridge('Workshop | rear access',(7.2,19.2,9.55),tx(MW,(10.0,18.0,12.4)),1.35,True)
bridge('About | descending exit',tx(MA,(17.9,-4.1,6.94)),(17.9,-8.7,3.8),1.5,True)
bridge('About | lower perimeter path',(17.9,-8.7,3.8),(13.5,-16,2.4),2)
# Secondary scattered props track the nearby station's transform.
bpy.context.view_layer.update()
for ob in bpy.data.collections['26 | SECONDARY • service details'].objects:
 p=ob.location
 M=ME if p.x < -5 and p.y<5 else MC if p.x<0 else MW if p.y>9 else MA
 ob.matrix_world=M@ob.matrix_world

# Render and export metadata.

collection('99 | metadata')
anchors={'Projects':tx(MP,(0,0,7.3)),'Experiences':tx(ME,(-13,-5,5.5)),'Education':tx(ME,(-13,-2.8,6.35)),'Work':tx(ME,(-13,-7,4.85)),'Contact':tx(MC,(-12.5,11,10.65)),'About Me':tx(MA,(13.25,-1.2,6.9)),'Workshop':tx(MW,(14.3,14.3,12.3)),'Minecraft':(6.5,18.5,9.6)}
for name,p in anchors.items():
 empty=bpy.data.objects.new('NAV | '+name,None);COL.objects.link(empty);empty.location=p;empty.empty_display_type='CIRCLE';empty.empty_display_size=.5;empty['portfolio_section']=name
S['area_anchors_json']=json.dumps(anchors)
S['build_source']='build_scene.py';S['reference_image']='//reference.png';S['units']='metres';S['navigation']='Projects → Experiences / Contact / About; rear Contact → Minecraft → Workshop; About → lower exit'
S.render.engine='CYCLES';S.cycles.samples=opt.samples;S.cycles.use_denoising=True;S.cycles.max_bounces=6;S.cycles.diffuse_bounces=3;S.cycles.glossy_bounces=3
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
 for dev in prefs.devices:dev.use=dev.type=='METAL'
 S.cycles.device='GPU'
except Exception as e:print('CPU fallback',e)
S.render.resolution_x=opt.width;S.render.resolution_y=round(opt.width*927/1696);S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG';S.render.film_transparent=False
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=.1
nt=bpy.data.node_groups.new('Cavern finishing','CompositorNodeTree');S.compositing_node_group=nt;nt.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor');rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.inputs['Type'].default_value='Fog Glow';gl.inputs['Quality'].default_value='High';gl.inputs['Threshold'].default_value=1.7;gl.inputs['Strength'].default_value=.22
out=nt.nodes.new('NodeGroupOutput');nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],out.inputs['Image'])
for a in bpy.data.screens:
 for space in a.areas:
  if space.type=='VIEW_3D':space.spaces.active.region_3d.view_perspective='CAMERA';space.spaces.active.clip_end=500
S.render.filepath=os.path.join(ROOT,'renders','pass-%02d.png'%opt.stage)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'cavern-portfolio.blend'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'checkpoint-%02d.blend'%opt.stage),copy=True)
stats={'objects':len(S.objects),'meshes':len(bpy.data.meshes),'unique_triangles':sum(sum(len(p.vertices)-2 for p in m.polygons) for m in bpy.data.meshes),'instance_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in S.objects if o.type=='MESH'),'materials':len(bpy.data.materials),'camera_matrix':[list(r) for r in camera.matrix_world],'camera_ortho_scale':cam.ortho_scale,'stage':opt.stage}
with open(os.path.join(ROOT,'scene-stats.json'),'w') as f:json.dump(stats,f,indent=2)
print('SCENE_STATS',json.dumps(stats));bpy.ops.render.render(write_still=True)
