"""Two reference-shaped recessed bays, integrated into one inside cave skin."""
import argparse,ast,hashlib,importlib.util,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

P=Path(__file__).resolve().parent;ROOT=P.parents[1];CAVE=P.parent/'connected-cavern'
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');ap.add_argument('--geometry-only',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(CAVE/'connected-cavern-open-chamber.blend'));S=bpy.context.scene;S.name='Cave | reference-shaped right bays';bpy.context.preferences.filepaths.save_version=0
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.871178627
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for c in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates'] for o in bpy.data.collections[c].objects if o.type=='MESH'}
def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
LOW=collection('20 | Octagon and left wing');UP=collection('21 | Six-sided upper bay');BR=collection('22 | Connected bridge');RIG=collection('23 | Reference camera and practicals');DECK=LOW
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','box','cylinder','annulus'}],type_ignores=[]),'metal_helpers','exec'),globals())
steel=bpy.data.materials['Metal | satin blue steel'];panel=bpy.data.materials['Metal | outer walkway alloy'];dark=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Metal | machined edge highlights'];warm=bpy.data.materials['Metal | amber lamp diffusers'];grate=bpy.data.materials['Metal | brushed grating steel']
def material(name,color,metal=.5,rough=.4,emission=0):
    m=bpy.data.materials.new('Rebuilt bays | '+name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission;return m
lining=material('gunmetal service lining',(.023,.032,.043),.65,.37);black=material('recess charcoal',(.006,.009,.012),.3,.58);white=material('cool practical lens',(.60,.81,1),.05,.3,3.4);yellow=material('muted brass alignment',(.36,.29,.11),.72,.34);status=material('blue status glass',(.016,.14,.23),.3,.32,.7)
def beam(name,p,q,width=.025,depth=None,ma=dark,c=LOW):
    p,q=Vector(p),Vector(q);v=q-p;o=box(name,(0,0,0),(width,depth or width,v.length),ma,c,bevel=min(.004,width*.12));o.matrix_world=FRAME@Matrix.Translation((p+q)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return o
def prism(name,poly,zlo,zhi,ma,c,bevel=.004):
    n=len(poly);verts=[(*p,z) for z in [zlo,zhi] for p in poly];faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh(name,verts,faces,ma,c,bevel)
def area(name,p,target,power,size=1.0,size_y=.3,color=(.63,.77,.91)):
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='RECTANGLE';ld.size=size;ld.size_y=size_y;ld.color=color
    ob=bpy.data.objects.new(name,ld);RIG.objects.link(ob);ob.location=FRAME@Vector(p);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();return ob
class Bay:
    def __init__(self,name,origin,rotation,z,poly,col,height):
        self.name=name;self.origin=np.array(origin);self.rotation=math.radians(rotation);self.z=z;self.poly=poly;self.col=col;self.height=height
        self.rot=np.array([[math.cos(self.rotation),-math.sin(self.rotation)],[math.sin(self.rotation),math.cos(self.rotation)]])
    def xy(self,p):return self.origin+self.rot@np.array(p)
    def point(self,x,y,z=0):return Vector((*self.xy((x,y)),self.z+z))
    def box(self,name,xyz,dims,ma=dark,bevel=.004):return box(self.name+' | '+name,self.point(*xyz),dims,ma,self.col,self.rotation,bevel)
    def beam(self,name,p,q,width=.025,ma=dark,depth=None):return beam(self.name+' | '+name,self.point(*p),self.point(*q),width,depth,ma,self.col)
    def outline(self):return [tuple(self.xy(p)) for p in self.poly]

A=2.2;CUT=A*(2-math.sqrt(2));SHORT=A-CUT;WING_Y=1.10;JOIN_X=-A+(WING_Y-SHORT);LEFT=-3.50
lower_poly=[(LEFT,-WING_Y),(JOIN_X,-WING_Y),(-SHORT,-A),(SHORT,-A),(A,-SHORT),(A,SHORT),(SHORT,A),(-SHORT,A),(JOIN_X,WING_Y),(LEFT,WING_Y)]
upper_poly=[(-3.60,.55),(-3.05,0),(1.65,0),(2.20,.55),(2.20,3.60),(-3.60,3.60)]
lower=Bay('Lower', (6.34,-2.75),-35,F-.04,lower_poly,LOW,2.12)
upper=Bay('Upper', (8.30,3.50),-10,9.90,upper_poly,UP,2.65)

# Continuous native floor meshes, with no overlap seam between octagon and wing.
for b in [lower,upper]:
    prism(b.name+' | continuous structural floor',b.outline(),b.z-.30,b.z-.045,dark,b.col,.009)
    floor=prism(b.name+' | continuous satin floor',b.outline(),b.z-.045,b.z,panel,b.col,.003)
    floor['top_down_footprint']=json.dumps(b.poly);floor['single_connected_floor']=True
    for p,q in zip(b.poly,b.poly[1:]+b.poly[:1]):
        for z,width,ma in [(-.035,.025,trim),(-.265,.025,trim),(-.155,.015,steel)]:b.beam('fascia horizontal edge',(*p,z),(*q,z),width,ma)
        length=np.linalg.norm(np.array(q)-p);n=max(1,math.ceil(length/.85))
        for j in range(n):
            t=(j+.5)/n;pt=np.array(p)*(1-t)+np.array(q)*t
            b.box('fascia joint plate',(*pt,-.15),(.065,.075,.22),steel)
            if j%2==0:
                delta=(np.array(q)-p)/length*.19
                b.beam('warm inset edge marker',(*(pt-delta),-.13),(*(pt+delta),-.13),.015,warm)

# Large manufactured panels with restrained seams, using polygon clipping.
def inside(pt,poly):
    odd=False
    for p,q in zip(poly,poly[1:]+poly[:1]):
        if (p[1]>pt[1])!=(q[1]>pt[1]) and pt[0]<(q[0]-p[0])*(pt[1]-p[1])/(q[1]-p[1])+p[0]:odd=not odd
    return odd
def clip_line(p,q,poly):
    p=np.array(p);q=np.array(q);v=q-p;ts=[0,1]
    cross=lambda aa,bb:aa[0]*bb[1]-aa[1]*bb[0]
    for aa,bb in zip(poly,poly[1:]+poly[:1]):
        aa=np.array(aa);e=np.array(bb)-aa;den=cross(v,e)
        if abs(den)<1e-9:continue
        t=cross(aa-p,e)/den;u=cross(aa-p,v)/den
        if 0<t<1 and 0<=u<=1:ts.append(t)
    ts=sorted(set(ts));return [(p+v*t,p+v*u) for t,u in zip(ts,ts[1:]) if inside(p+v*(t+u)/2,poly)]
for b in [lower,upper]:
    for j in range(-4,5):
        for vertical in [False,True]:
            p,q=((-7,j*.95),(7,j*.95)) if not vertical else ((j*1.15,-5),(j*1.15,6))
            for aa,bb in clip_line(p,q,b.poly):b.beam('broad floor seam',(*aa,.0015),(*bb,.0015),.005,black)
# The marking is strictly centered on the octagon, not on the union's centroid.
for ri,ro,ma in [(.001,1.55,steel),(1.557,1.58,black),(1.59,1.605,trim),(1.615,1.78,panel),(1.79,1.815,yellow),(1.83,1.848,trim),(1.86,1.88,black)]:
    ob=annulus('Lower | centered octagon marking',ri,ro,lower.z-.015,lower.z+.008,ma,c=LOW)
    ob.matrix_world=FRAME@Matrix.Translation((*lower.origin,0))
for j in range(16):
    t=math.tau*j/16;p=lower.point(math.cos(t)*1.73,math.sin(t)*1.73,.013);cylinder('Lower | alignment ring fixing',p,.009,.009,dark,LOW,segments=8)

def service_wall(b,x0,x1,y,height,stations):
    b.box('back wall steel lining',((x0+x1)/2,y,height/2),(x1-x0,.10,height),lining,.008)
    for x in np.linspace(x0,x1,stations+1):
        b.box('back wall upright',(x,y-.075,height/2),(.065,.09,height),steel)
    for z in [.11,height-.10]:b.beam('back wall cross rail',(x0,y-.075,z),(x1,y-.075,z),.04,steel)
    for x in np.linspace(x0+.45,x1-.45,stations):
        b.box('recessed service strip',(x,y-.085,height-.31),(.66,.065,.10),black)
        b.box('service light diffuser',(x,y-.125,height-.31),(.54,.012,.035),white,.001)
        area(b.name+' | wall strip pool',b.point(x,y-.25,height-.3),b.point(x,y-1.3,.25),28,.65,.3)
        b.box('bench drawer body',(x,y-.29,.32),(.65,.37,.64),lining)
        b.box('bench satin worktop',(x,y-.38,.67),(.83,.56,.055),steel)
        for z in [.17,.33,.49]:
            b.box('drawer face',(x,y-.493,z),(.59,.025,.13),panel)
            b.box('drawer pull',(x,y-.515,z+.03),(.23,.025,.016),trim,.002)
        b.box('equipment panel',(x,y-.10,1.16),(.68,.025,.60),black)
        for k in range(5):
            xx=x-.24+k*.12
            b.beam('hanging service tool',(xx,y-.13,1.01),(xx,y-.13,1.28+(k%2)*.06),.018,trim)
            b.box('tool head',(xx,y-.132,1.28+(k%2)*.06),(.053,.025,.042),steel,.002)
        for k in [-1,1]:b.box('worktop case',(x+k*.21,y-.33,.77),(.18,.15,.14),dark)
    for x in [x0+.18,x1-.18]:
        b.box('utility locker',(x,y-.26,.68),(.33,.37,1.36),lining)
        for z in [.35,.44,.53,.62]:b.box('locker vent',(x,y-.452,z),(.26,.012,.018),black,.001)
        b.box('locker status',(x+.08,y-.46,1.07),(.03,.012,.06),warm,.001)
service_wall(lower,-.84,1.45,1.97,1.94,2)
service_wall(lower,-3.28,-2.20,.97,1.94,1)
service_wall(upper,-3.33,1.95,3.33,2.34,4)
# Angled octagon rear returns; short upper side walls remain inset into stone.
for b,segments in [(lower,[((SHORT,A),(A,SHORT)),((-A,SHORT),(-SHORT,A))]),(upper,[((2.14,.65),(2.14,3.33)),((-3.53,.68),(-3.53,3.33))])]:
    for p,q in segments:
        pp,qq=b.xy(p),b.xy(q);mid=(pp+qq)/2;angle=math.atan2(qq[1]-pp[1],qq[0]-pp[0]);length=np.linalg.norm(qq-pp)
        box(b.name+' | inset side lining',(*mid,b.z+b.height*.44),(length,.09,b.height*.88),lining,b.col,angle,.006)

# Recessed steel portals: the rock surface is the surrounding enclosure.
def portal(b,left,right,y,h):
    coords=[(left,y,.02),(left,y,h-.42),(left+.45,y,h),(right-.45,y,h),(right,y,h-.42),(right,y,.02)]
    for p,q in zip(coords,coords[1:]):
        b.beam('embedded portal dark rib',p,q,.11,dark,.13)
        p=np.array(p);q=np.array(q);p[1]-=.076;q[1]-=.076;b.beam('portal brushed face',p,q,.026,steel,.07)
portal(lower,-3.45,2.10,.91,2.06)
portal(lower,-1.25,1.80,1.83,2.06)
for y in [.72,2.2]:portal(upper,-3.50,2.10,y,2.57)
# Broad overhead housings centered above each room's principal floor portion.
for b,x,y,z in [(lower,0,0,2.02),(upper,.10,1.95,2.55)]:
    b.box('overhead lamp housing',(x,y,z),(1.30,.48,.09),dark)
    for yy in [-.15,0,.15]:b.box('overhead cool strip',(x,y+yy,z-.051),(1.12,.032,.015),white,.001)
    area(b.name+' | centered overhead pool',b.point(x,y,z-.085),b.point(x,y,0),170 if b==lower else 240,1.1,.5)
    for xx in [-.50,.50]:b.beam('lamp suspension',(x+xx,y,z+.035),(x+xx,y,b.height+.04),.024,steel)
    b.box('visible front lamp diffuser',(x,y-.249,z-.025),(1.08,.014,.026),white,.001)
for xx in [-.50,.50]:
    lower.beam('centered lamp cantilever arm',(xx,.94,2.075),(xx,0,2.075),.045,steel)
    lower.beam('lamp arm diagonal',(xx,.91,1.87),(xx,.22,2.075),.025,dark)
lower.col['circular_marking_center']=list(lower.origin);lower.col['overhead_light_center']=list(lower.origin)
# Upper left control kiosk, compact logistics cabinets and recessed gantry.
upper.box('control kiosk',(-2.82,1.13,.68),(.63,.64,1.36),lining,.012)
for z in [.88,1.15]:
    upper.box('kiosk blue window',(-2.82,.8,z),(.53,.022,.20),status,.002)
    upper.box('kiosk mullion',(-2.82,.779,z),(.018,.015,.21),steel,.001)
upper.box('kiosk crown',(-2.82,1.13,1.4),(.80,.76,.08),steel)
for j in range(3):upper.box('logistics crate',(-1.85+j*.47,2.80,.23),(.39,.42,.46),lining)
for xx in [-1.8,1.4]:upper.beam('rear gantry leg',(xx,2.53,0),(xx,2.53,1.72),.055,steel)
upper.beam('rear gantry header',(-1.8,2.53,1.72),(1.4,2.53,1.72),.10,dark)
for j in range(14):upper.box('gantry brass marker',(-1.68+j*.22,2.47,1.73),(.06,.016,.045),yellow,.001)

def guard(b,p,q):
    p,q=np.array(p),np.array(q);length=np.linalg.norm(q-p);n=max(1,math.ceil(length/.60))
    for h in [.20,.46]:b.beam('guard horizontal rail',(*p,h),(*q,h),.022,dark)
    b.beam('guard polished top',(*p,.465),(*q,.465),.008,trim)
    for j in range(n+1):
        xy=p+(q-p)*j/n;b.beam('guard post',(*xy,0),(*xy,.49),.036,steel)
        b.box('guard bolted foot',(*xy,.018),(.10,.095,.032),dark)
# Leave a real opening in the front of the rectangular wing for the bridge.
gate_y=-.42;gate_half=.52
for i in [0,1,2,3,4,9]:
    p,q=lower.poly[i],lower.poly[(i+1)%len(lower.poly)]
    if i==9:
        guard(lower,p,(LEFT,gate_y+gate_half));guard(lower,(LEFT,gate_y-gate_half),q)
    else:guard(lower,p,q)
for i in [0,1,2]:guard(upper,upper.poly[i],upper.poly[(i+1)%6])
for b,pts in [(lower,[(-3.38,-1.1),(.80,-2.2),(2.20,.35)]),(upper,[(-3.34,.28),(-.60,0),(1.88,.28)])]:
    for x,y in pts:
        b.box('warm guard lamp armor',(x,y,.255),(.095,.095,.49),dark)
        for z in [.15,.34]:b.box('amber guard lens',(x,y-.052,z),(.045,.013,.105),warm,.001)

# Generate one radial wall skin with two deliberately shaped recesses.
oldwall=S.objects['Cave | one continuous spacious wall'];WALLCOL=oldwall.users_collection[0];rockmat=oldwall.data.materials[0]
source=(CAVE/'build_open_chamber.py').read_text();ns={'np':np,'math':math,'Path':Path,'CAVE':CAVE,'P':CAVE}
fieldcode=(CAVE/'build_interior_cavern.py').read_text();exec(fieldcode[fieldcode.index('rng=np.random.default_rng(76183)'):fieldcode.index('outer=np.full((N,M),20.)')],ns)
oldtheta,oldz,oldfield=ns['theta'],ns['zv'],ns['inner'].copy()
for ii in range(len(oldtheta)-1):
    deg=math.degrees(oldtheta[ii])
    if deg<75 or deg>300:oldfield[ii]=6+np.clip(ns['inner'][(ii+(len(oldtheta)-1)//2)%(len(oldtheta)-1)]-6,-.72,.30)
chamber_code=source[source.index('stations='):source.index('spec=importlib.util.spec_from_file_location')]
for before,after in [('(234,13.8)','(234,18.8)'),('(252,15.0)','(252,22.5)'),('(270,15.5)','(270,23.5)'),('(287,15.0)','(287,22.5)'),('(307,14.0)','(307,18.5)')]:chamber_code=chamber_code.replace(before,after)
exec(chamber_code,ns);plan_radius=ns['plan_radius']
def hull(points):
    pts=sorted(set(map(tuple,points)));cross=lambda o,p,q:(p[0]-o[0])*(q[1]-o[1])-(p[1]-o[1])*(q[0]-o[0]);halves=[]
    for seq in [pts,list(reversed(pts))]:
        half=[]
        for p in seq:
            while len(half)>=2 and cross(half[-2],half[-1],p)<=0:half.pop()
            half.append(p)
        halves+=half[:-1]
    return np.array(halves)
rooms=[];approaches=[];rear_profiles=[]
for b in [lower,upper]:
    pp=np.array(b.outline());center=pp.mean(axis=0);v=pp-center
    room=hull(pp+v/np.linalg.norm(v,axis=1)[:,None]*.24);rooms.append(room)
    # A straight architectural entrance corridor creates planar jambs. A hull
    # aimed at the camera instead makes thin triangular frustum-like cheeks.
    xmin=min(p[0] for p in b.poly)-.55;xmax=max(p[0] for p in b.poly)+.55
    approaches.append(hull(np.vstack([room,b.xy((xmin,-9.)),b.xy((xmax,-9.))])))
    # The rock header begins behind the open apron instead of covering the
    # entire floor. A shallow portal surround remains over the service zone.
    x0,x1=min(p[0] for p in b.poly)-.18,max(p[0] for p in b.poly)+.18
    y0=.60 if b==lower else .82;y1=max(p[1] for p in b.poly)+.24
    rear_profiles.append(hull([b.xy(p) for p in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]))
def hits(t,poly):
    ray=np.array((math.cos(t),math.sin(t)));rs=[]
    for p,q in zip(poly,np.roll(poly,-1,axis=0)):
        edge=q-p;den=ray[0]*edge[1]-ray[1]*edge[0]
        if abs(den)<1e-9:continue
        u=(p[0]*ray[1]-p[1]*ray[0])/den;r=(p[0]*edge[1]-p[1]*edge[0])/den
        if -1e-7<=u<=1.0000001 and r>1e-7:rs.append(r)
    return sorted(rs)
boundaries=[math.atan2(p[1],p[0])%math.tau for room in rooms+approaches+rear_profiles for p in room if np.linalg.norm(p)>1e-5]
theta=np.unique(np.r_[oldtheta,np.linspace(0,math.tau,385),boundaries]);theta.sort()
band_start=lower.z+lower.height+.04;band_end=upper.z-.16
terraces=np.linspace(band_start,band_end,4)[1:]
zv=np.unique(np.r_[oldz,lower.z-.12,lower.z+lower.height,upper.z-.12,upper.z+upper.height,*[h+delta for h in terraces for delta in [-.006,.006]]]);N,M=len(theta)-1,len(zv)-1
def profile(t,z):
    base=plan_radius(t);fronts=[]
    for k,b in enumerate([lower,upper]):
        back=hits(t,rear_profiles[k])
        # The natural cliff supports the REAR of the bay. The open apron is
        # a real cantilever. Do not grow a rock cylinder below the whole floor
        # and then flare it outward at eye height; that makes a pinched cheek.
        fronts.append(min(base,back[0]+.10) if len(back)>=2 else base)
    # Broad retreating strata replace a single deep slab between the bays.
    # Nearly coincident height boundaries form horizontal ledges; the faces
    # between them stay upright instead of becoming long slanted triangles.
    if z<band_start:front=min(fronts)
    elif z<band_end+.01:
        blend=sum(z>h for h in terraces)/3
        front=min(fronts)*(1-blend)+fronts[1]*blend
    else:front=fronts[1]
    k=0 if z<(lower.z+lower.height+upper.z-.12)/2 else 1
    rr=hits(t,approaches[k]);rear=max(front+.03,max(rr,default=front)+.16)
    return front,rear
field=np.zeros((N,M))
for i in range(N):
    t=(theta[i]+theta[i+1])/2;oi=min(len(oldtheta)-2,np.searchsorted(oldtheta,t)-1)
    for j in range(M):
        z=(zv[j]+zv[j+1])/2;oj=min(len(oldz)-2,max(0,np.searchsorted(oldz,z)-1));d=oldfield[oi,oj]
        if math.cos(t)>.25:d=6+np.clip(d-6,-.60,.25)
        for center,width,z0,z1,depth in [(344,11,8.85,9.38,.22),(357,13,9.16,9.88,.25),(12,10,9.40,10.15,.19),(28,14,12.52,13.42,.24),(42,11,12.60,14.1,.28)]:
            if abs((math.degrees(t)-center+180)%360-180)<width/2 and z0<z<z1:d-=depth
        for k,b in enumerate([lower,upper]):
            if b.z-.12<z<b.z+b.height:
                front,rear=profile(t,z)
                if hits(t,approaches[k]) and max(hits(t,approaches[k]))>front-1.0:d=14+(d-6)*.10
        field[i,j]=d
for _ in range(12):
    count=0
    for i in range(N):
        k=(i+1)%N
        for j in range(M-1):
            aa,bb,cc,dd=field[i,j],field[k,j],field[i,j+1],field[k,j+1]
            if min(aa,dd)>max(bb,cc)+1e-7:
                if bb>=cc:field[k,j]=min(aa,dd)
                else:field[i,j+1]=min(aa,dd)
                count+=1
            elif min(bb,cc)>max(aa,dd)+1e-7:
                if aa>=dd:field[i,j]=min(bb,cc)
                else:field[k,j+1]=min(bb,cc)
                count+=1
    if not count:break
spec=importlib.util.spec_from_file_location('pillar_steps',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)
tri,raw=shape.mesh_field(theta,zv,np.ones(M+1),field,np.full_like(field,40.)).arrays();r=np.hypot(raw[:,0],raw[:,2]);keep=np.all(r[tri]<30,axis=1)
cap=np.all(abs(raw[tri,1]-zv[0])<1e-8,axis=1)|np.all(abs(raw[tri,1]-zv[-1])<1e-8,axis=1);tri=tri[keep&~cap];used=np.unique(tri);remap=np.full(len(raw),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];raw=raw[used]
vertices=[];point_cache={}
for x,z,y in raw:
    raw_angle=math.atan2(y,x);ii=int(np.argmin(abs(np.angle(np.exp(1j*(theta[:-1]-raw_angle))))));t=theta[ii]
    jj=int(np.argmin(abs(zv-z)));z=zv[jj];key=(ii,jj)
    if key not in point_cache:point_cache[key]=profile(t,z)
    d=math.hypot(x,y)-6;front,rear=point_cache[key];r=front+(d*(rear-front)/8 if d>4 else d)
    deg=math.degrees(t);height=(z-zv[0])/(zv[-1]-zv[0]);zz=z
    if 75<deg<234:zz+=height**6*(.45*math.sin(t*5)-max(0.,-math.sin(t)))
    if band_start<z<band_end:
        zz+=.055*math.sin(t*11+.7)*math.sin(math.pi*(z-band_start)/(band_end-band_start))
    vertices.append((r*math.cos(t),r*math.sin(t),zz))
me=bpy.data.meshes.new('Cave | continuous two-recess surface');me.from_pydata(vertices,[],tri.tolist());me.materials.append(rockmat);me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.00002,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'});bm.to_mesh(me);bm.free()
wall=bpy.data.objects.new('Cave | single wall with two recessed bays',me);WALLCOL.objects.link(wall);wall.matrix_world=FRAME;wall['surface_only']=True;wall['thickness']=0.;bpy.data.objects.remove(oldwall,do_unlink=True)
for p in me.polygons:p.use_smooth=False
bpy.context.view_layer.update();tree=BVHTree.FromPolygons([v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons])

# Engineered apron brackets meet the actual single wall, not a guessed plane.
anchor_checks=[]
for b,edges in [(lower,[1,2,3]),(upper,[0,1,2])]:
    for i in edges:
        p,q=np.array(b.poly[i]),np.array(b.poly[(i+1)%len(b.poly)])
        for frac in [.25,.75]:
            xy=p*(1-frac)+q*frac;tip=b.point(*xy,-.28);probe=b.point(*xy,-1.48 if b==lower else -1.02)
            hit=tree.find_nearest(probe);anchor=hit[0]
            if anchor is None:continue
            # Seat on the nearest wall face and keep metal clear of the deck.
            anchor=Vector(anchor);beam(b.name+' | diagonal rock anchor',tip,anchor,.115,.15,dark,b.col)
            direction=Vector(hit[1]).normalized()
            if direction.dot(tip-anchor)<0:direction=-direction
            plate=box(b.name+' | rock fixing plate',(0,0,0),(.29,.39,.045),steel,b.col,bevel=.006)
            plate.matrix_world=FRAME@Matrix.Translation(anchor+direction*.016)@direction.to_track_quat('Z','Y').to_matrix().to_4x4()
            for sx,sy in [(-.09,-.14),(.09,-.14),(-.09,.14),(.09,.14)]:
                local=INV@(plate.matrix_world@Vector((sx,sy,.03)));cylinder(b.name+' | rock anchor bolt',local,.018,.027,trim,b.col,direction,8)
            beam(b.name+' | apron bearing tie',tip,Vector((anchor.x,anchor.y,tip.z)),.085,.12,dark,b.col)
            anchor_checks.append(tree.find_nearest(anchor)[3])

# A straight bridge enters the rectangular wing and opens the middle railing.
end=lower.point(LEFT+.18,gate_y,.003);angle=math.atan2(end.y,end.x);start=Vector((math.cos(angle)*2.64,math.sin(angle)*2.64,F));axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();width=.88
cut=box('Temporary center bridge gate',(0,0,0),(1.35,width+.10,1.1),black,BR,bevel=0);cut.matrix_world=FRAME@Matrix.Translation(start+axis*.15+Vector((0,0,.35)))@Matrix.Rotation(math.atan2(axis.y,axis.x),4,'Z')
rail_changes=[]
for ob in list(bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects):
    if ob.name.startswith(('Metal | continuous steel guardrail','Metal | guardrail polished top edge')):
        bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Straight bridge gate','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);rail_changes.append(ob.name)
    elif ob.type=='MESH':
        p=INV@ob.matrix_world.translation;relative=p-start
        if abs(relative.dot(side))<width/2+.055 and abs(relative.dot(axis))<.50 and p.z>F-.5:
            rail_changes.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.objects.remove(cut,do_unlink=True)
length=(end-start).length;count=max(2,math.ceil(length/.18))
for j in range(count):
    p=start.lerp(end,j/count);q=start.lerp(end,(j+1)/count);poly=[(p-side*width/2).xy,(q-side*width/2).xy,(q+side*width/2).xy,(p+side*width/2).xy]
    prism('Bridge | satin tread',poly,min(p.z,q.z)-.12,max(p.z,q.z)+.005,panel,BR,.002)
for sign in [-1,1]:
    p=start+side*sign*width/2;q=end+side*sign*width/2
    for h in [.2,.46]:beam('Bridge | uninterrupted guard',p+Vector((0,0,h)),q+Vector((0,0,h)),.023,ma=dark,c=BR)
    beam('Bridge | structural side girder',p-Vector((0,0,.14)),q-Vector((0,0,.14)),.095,.16,dark,BR)
    for j in range(1+math.ceil(length/.5)):
        r=p.lerp(q,j/math.ceil(length/.5));beam('Bridge | post',r,r+Vector((0,0,.48)),.035,ma=steel,c=BR)

def camera(name,pos,target,lens=32,ortho=None):
    o=bpy.data.objects.new(name,bpy.data.cameras.new(name));RIG.objects.link(o);o.location=FRAME@Vector(pos);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens;o.data.clip_end=200
    if ortho:o.data.type='ORTHO';o.data.ortho_scale=ortho
    return o
hero=camera('Rebuilt bays | reference overview',(0,-19.25*math.cos(math.radians(19.5)),F+19.25*math.sin(math.radians(19.5))),(0,0,F),30);hero.data.shift_y=.005;hero.data.shift_x=.015
close=camera('Rebuilt bays | architecture close-up',(-.1,-12.8,11.2),(7.2,1.0,8.65),32)
side=camera('Rebuilt bays | side inspection',(1.0,-7.0,9.3),(8,1.2,8.5),25)
plan=camera('Rebuilt bays | complete plan',(3,-1.5,42),(3,-1.5,0),ortho=29)
floor_plan=camera('Rebuilt bays | local footprint camera',(0,0,40),(0,0,0),ortho=9)
# Retain dry cool atmosphere, but let localized practicals lead the new bays.
for ob in S.objects:
    if ob.type=='LIGHT' and (ob.name.startswith('Interior |') or ob.name.startswith('Cave |')):ob.data.energy*=.28
S.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.10
area('Lower | subtle frontal bounce',lower.point(-2,-3,1.5),lower.point(0,1,.8),48,2,1)
area('Upper | subtle frontal bounce',upper.point(-1,-2,1.8),upper.point(0,2,1),70,2,1)

# Saved-file checks focus on meaningful geometry and preserved central content.
bpy.context.view_layer.update();changed=[n for n,h in protected.items() if fingerprint(S.objects[n])!=h];assert not changed,changed
bm=bmesh.new();bm.from_mesh(me);seen=set();components=[]
for v in bm.verts:
    if v in seen:continue
    seen.add(v);stack=[v];n=0
    while stack:
        p=stack.pop();n+=1
        for e in p.link_edges:
            q=e.other_vert(p)
            if q not in seen:seen.add(q);stack.append(q)
    components.append(n)
bad=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges);bm.free()
intrusions=[]
for b in [lower,upper]:
    for x in np.arange(min(p[0] for p in b.poly)+.15,max(p[0] for p in b.poly),.28):
        for y in np.arange(min(p[1] for p in b.poly)+.15,max(p[1] for p in b.poly),.28):
            if inside((x,y),b.poly):
                hit=tree.ray_cast(b.point(x,y,.10),Vector((0,0,1)),1.70)
                if hit[0] is not None:intrusions.append([b.name,float(x),float(y),list(hit[0])])
report={'protected_middle_meshes':len(protected),'changed_middle_meshes':changed,'wall_components':components,'wall_invalid_edges':bad,'standing_space_rock_intrusions':intrusions,'lower_polygon':lower_poly,'lower_octagon_half_extent':A,'lower_octagon_corner_cut':CUT,'lower_wing_bounds':[LEFT,-1.6,-WING_Y,WING_Y],'upper_polygon':upper_poly,'upper_right_edge_fixed':2.2,'upper_left_extension':1.4,'lower_marking_and_light_center':list(lower.origin),'lower_yaw_degrees':math.degrees(lower.rotation),'upper_yaw_degrees':math.degrees(upper.rotation),'lower_origin':list(lower.origin),'upper_origin':list(upper.origin),'lower_floor_z':lower.z,'upper_floor_z':upper.z,'support_seat_distances':anchor_checks,'central_railing_bridge_changes':rail_changes,'bridge_start':list(start),'bridge_end':list(end),'no_vehicles':True,'no_water':True}
report['passed']=not changed and len(components)==1 and bad==0 and not intrusions
print('REFERENCE_BAYS_CHECK',json.dumps(report),flush=True)
tag='reference-bays' if a.final else 'preview-reference-bays';out=P/(tag+'.blend');(P/(tag+'-verification.json')).write_text(json.dumps(report,indent=2))
if a.final:assert report['passed'],report
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.render.engine='CYCLES';S.cycles.samples=72 if a.final else 24;S.cycles.use_denoising=True;S.render.resolution_x=2200 if a.final else 1500;S.render.resolution_y=round(S.render.resolution_x*654/1199);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.camera=hero;S.render.filepath=str(P/(tag+'-overview.png'))
tx=bpy.data.texts.get('build_reference_bays.py') or bpy.data.texts.new('build_reference_bays.py');tx.clear();tx.write(Path(__file__).read_text());bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
if a.geometry_only:sys.exit(0)
bpy.ops.render.render(write_still=True)
S.camera=close;S.render.filepath=str(P/(tag+'-close.png'));bpy.ops.render.render(write_still=True)
S.camera=side;S.render.filepath=str(P/(tag+'-side.png'));bpy.ops.render.render(write_still=True)
S.camera=plan;S.render.engine='BLENDER_WORKBENCH';S.render.resolution_x=1500;S.render.resolution_y=1400;sh=S.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';S.world.color=(.055,.065,.08)
for ob in S.objects:
    if ob.type=='MESH':ob.color=(.24,.30,.36,1) if ob==wall else (.58,.66,.75,1)
    if 'Atmosphere' in ob.name:ob.hide_render=True
S.render.filepath=str(P/(tag+'-plan.png'));bpy.ops.render.render(write_still=True)
# Isolate each floor in a true local top view: neither roof nor props conceal it.
for b in [lower,upper]:
    for ob in S.objects:
        if ob.type=='MESH':ob.hide_render=ob not in b.col.objects.values() or not any(s in ob.name for s in ['continuous satin floor','centered octagon marking','broad floor seam'])
    centroid=((min(p[0] for p in b.poly)+max(p[0] for p in b.poly))/2,(min(p[1] for p in b.poly)+max(p[1] for p in b.poly))/2)
    floor_plan.matrix_world=FRAME@Matrix.Translation((*b.xy(centroid),40))@Matrix.Rotation(b.rotation,4,'Z');S.camera=floor_plan;S.render.resolution_x=1400;S.render.resolution_y=1000;floor_plan.data.ortho_scale=8
    S.render.filepath=str(P/(tag+'-'+b.name.lower()+'-footprint.png'));bpy.ops.render.render(write_still=True)
print('REFERENCE_BAYS_SAVED',str(out),flush=True)
