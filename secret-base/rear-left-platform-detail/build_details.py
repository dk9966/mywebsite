"""Detail the existing rear-left platform from the saved live scene.

Original blockouts are archived. Rock changes use an additive shape key.
All dimensions are derived in a frame fitted to the existing stair flight.
"""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
S=bpy.context.scene
assert bpy.context.mode=='OBJECT'
assert bpy.data.collections.get('170 | Rear-left connected platform') is None
F=Matrix(json.loads((P/'layout-before.json').read_text())['frame']); IV=F.inverted()
DG=bpy.context.evaluated_depsgraph_get()
COL=bpy.data.collections.new('170 | Rear-left connected platform');S.collection.children.link(COL)
ARCH=bpy.data.collections.new('Archive | rear-left platform before details');S.collection.children.link(ARCH)
ARCH.hide_viewport=ARCH.hide_render=True
old_names=['Back left | upper rectangular platform','Back left | broad stair flight','Back left | lower stair landing','Back left | short connection to center']
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
def signature(o):
    h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        h.update(str([tuple(v.co) for v in o.data.vertices]).encode())
    return h.hexdigest()
protected={o.name:signature(o) for o in S.objects if o.name not in old_names and o!=wall}
(P/'protected-before.json').write_text(json.dumps(protected))
STEEL=bpy.data.materials['Metal | dark structural steel']
FRAME=bpy.data.materials['Bridge | blue gunmetal panel frames']
GRATE=bpy.data.materials['Bridge | graphite open steel grating']
ALLOY=bpy.data.materials['Bridge | restrained silver fasteners']
FLOOR=bpy.data.materials['Metal | satin blue steel']
ACCENT=FLOOR.copy();ACCENT.name='Rear left | subtly varied floor panels'
bs=ACCENT.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.061,.078,.095,1);bs.inputs['Roughness'].default_value=.35
ACCENT.diffuse_color=(.061,.078,.095,1)
WARM=bpy.data.materials['Metal | amber lamp diffusers']
UP=Vector((0,0,1)); made=[]

def mesh(name,vs,fs,mat,bevel=0):
    me=bpy.data.meshes.new('Rear left | '+name);me.from_pydata(vs,[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new('Rear left | '+name,me);COL.objects.link(o);o.matrix_world=F;me.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Fabricated edge radius','BEVEL');m.width=bevel;m.segments=2
        o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
    made.append(o);return o

def prism(name,poly,z0,z1,mat,bevel=0):
    n=len(poly);vs=[(x,y,z) for z in (z0,z1) for x,y in poly]
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vs,fs,mat,bevel)

def append_beam(vs,fs,a,b,w,h):
    a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(UP if abs(d.z)<.95 else Vector((0,1,0))).normalized()*w/2;v=d.cross(u).normalized()*h/2;k=len(vs)
    vs.extend([tuple(p+u*i+v*j) for p in (a,b) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    fs.extend([tuple(k+i for i in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])

def beam(name,a,b,w,h,mat=STEEL,bevel=.002):
    vs,fs=[],[];append_beam(vs,fs,a,b,w,h);return mesh(name,vs,fs,mat,bevel)

def clip(poly,outline):
    for a,b in zip(outline,outline[1:]+outline[:1]):
        out=[]
        def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        if not poly:break
        for p,q in zip(poly,poly[1:]+poly[:1]):
            sp,sq=side(p),side(q)
            if sp>=-1e-8:out.append(p)
            if (sp>=0)!=(sq>=0):
                t=sp/(sp-sq);out.append((p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t))
        poly=out
    return poly

def panels(name,outline,z,dx=1.08,dy=.86):
    x0,x1=min(p[0] for p in outline),max(p[0] for p in outline);y0,y1=min(p[1] for p in outline),max(p[1] for p in outline)
    nx=math.ceil((x1-x0)/dx);ny=math.ceil((y1-y0)/dy);gap=.016
    for j in range(ny):
        for i in range(nx):
            a=x0+i*(x1-x0)/nx+gap;b=x0+(i+1)*(x1-x0)/nx-gap;c=y0+j*(y1-y0)/ny+gap;d=y0+(j+1)*(y1-y0)/ny-gap
            p=clip([(a,c),(b,c),(b,d),(a,d)],outline)
            if len(p)>2:prism(name+' panel %02d %02d'%(i,j),p,z-.022,z,FLOOR if (i+j)%4 else ACCENT,.003)

def edge_trim(name,poly,z):
    for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        beam(name+' perimeter %02d'%i,(*a,z-.017),(*b,z-.017),.045,.036,FRAME)

def grate(name,x0,x1,y0,y1,z):
    vs,fs=[],[]
    for a,b in [((x0,y0,z-.023),(x1,y0,z-.023)),((x0,y1,z-.023),(x1,y1,z-.023)),((x0,y0,z-.023),(x0,y1,z-.023)),((x1,y0,z-.023),(x1,y1,z-.023))]:append_beam(vs,fs,a,b,.035,.046)
    frame=mesh(name+' cassette frame',vs,fs,FRAME,.0015)
    vs,fs=[],[]
    for i in range(1,max(2,round((x1-x0)/.036))):
        x=x0+(x1-x0)*i/max(2,round((x1-x0)/.036));append_beam(vs,fs,(x,y0+.018,z-.017),(x,y1-.018,z-.017),.0042,.030)
    for i in range(1,max(2,round((y1-y0)/.037))):
        y=y0+(y1-y0)*i/max(2,round((y1-y0)/.037));append_beam(vs,fs,(x0+.018,y,z-.009),(x1-.018,y,z-.009),.0032,.014)
    grid=mesh(name+' open grating',vs,fs,GRATE)
    return frame,grid

for n in old_names:
    o=bpy.data.objects[n];ARCH.objects.link(o)
    for c in list(o.users_collection):
        if c!=ARCH:c.objects.unlink(o)

plate=bpy.data.objects['Metal | outer walkway plate'].evaluated_get(DG)
H=max((plate.matrix_world@v.co).z for v in plate.data.vertices)
TOP=8.7;RUN=2.99614;COUNT=18;half=1.96
center=IV@bpy.data.objects['Rig | middle radius'].matrix_world.translation;center.z=H
rim=bpy.data.objects['Metal | upper rolled rim'].evaluated_get(DG)
R=max(math.hypot(*(IV@rim.matrix_world@v.co-center)[:2]) for v in rim.data.vertices)
mouth=Vector((0,-1.35,H));D=(mouth-center);D.z=0;D.normalize();U=Vector((D.y,-D.x,0));BW=.59
def bp(s,u,z=H):
    p=center+D*s+U*u;p.z=z;return p
END=(Vector((0,-2.35,H))-center).dot(D)
START=math.sqrt(R*R-BW*BW)-.05
left=bp(END,-BW);right=bp(END,BW)
landing=[(-2.02,.035),(-2.02,-1.17),(-1.86,-1.38),(left.x,left.y),(right.x,right.y),(1.86,-1.38),(2.02,-1.17),(2.02,.035)]
upper=[(-2.12,2.982),(2.20,2.982),(2.34,3.122),(2.34,6.54),(2.20,6.68),(-2.12,6.68),(-2.26,6.54),(-2.26,3.122)]
prism('one-piece chamfered T landing',landing,H-.25,H-.014,STEEL,.009)
panels('T landing',landing,H);edge_trim('T landing',landing,H)
prism('upper connected platform',upper,TOP-.25,TOP-.014,STEEL,.009)
panels('upper deck',upper,TOP);edge_trim('upper deck',upper,TOP)

# Welded, closed stair body follows the existing width/run and meets both floors.
profile=[(0,H-.25),(RUN,TOP-.25),(RUN,TOP)]
rise=(TOP-H)/COUNT
for i in range(COUNT-1,-1,-1):
    y=i*RUN/COUNT;profile.append((y,H+(i+1)*rise));profile.append((y,H+i*rise))
n=len(profile);vs=[(x,y,z) for x in (-half,half) for y,z in profile]
fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
stair=mesh('connected broad stair body',vs,fs,STEEL,.002)
for i in range(COUNT):
    a=i*RUN/COUNT;b=(i+1)*RUN/COUNT;z=H+(i+1)*rise
    prism('stair tread %02d'%i,[(-half,a+.005),(half,a+.005),(half,b-.005),(-half,b-.005)],z-.013,z,FLOOR,.002)
    beam('stair tread %02d nosing'%i,(-half,a+.014,z-.002),(half,a+.014,z-.002),.017,.008,FRAME,.001)
    for x in (-1.36,0,1.36):beam('stair tread %02d joint'%i,(x,a+.025,z+.0006),(x,b-.012,z+.0006),.006,.001,STEEL,0)
for x in (-half,half):
    beam('stair side channel',(x,0,H-.07),(x,RUN,TOP-.07),.065,.145,FRAME)

# Straight radial open-grating bridge, same fabrication and proportions as peers.
BF=Matrix(((U.x,D.x,0,center.x),(U.y,D.y,0,center.y),(0,0,1,0),(0,0,0,1)))
def transform_new(start):
    for o in made[start:]:o.matrix_world=F@BF
N=max(3,round((END-START)/.92));cuts=[START+(END-START)*i/N for i in range(N+1)]
for i in range(N):
    start=len(made);grate('bridge bay %02d'%i,-BW,BW,cuts[i],cuts[i+1],H);transform_new(start)
for x in (-BW,BW):
    start=len(made);beam('bridge edge stringer',(x,START,H-.09),(x,END,H-.09),.06,.16);beam('bridge edge cap',(x,START,H-.018),(x,END,H-.018),.055,.036,FRAME);transform_new(start)
for y in cuts:
    start=len(made);beam('bridge cross bearer',(-BW,y,H-.10),(BW,y,H-.10),.047,.09);transform_new(start)
for a,b in zip(cuts,cuts[1:]):
    for sign in (-1,1):
        start=len(made);beam('bridge underdeck X brace',(sign*(BW-.05),a,H-.11),(-sign*(BW-.05),b,H-.11),.028,.034);transform_new(start)
# Curved threshold follows the round platform exactly, with full-width overlap.
v=[]
for i in range(33):
    x=-BW+2*BW*i/32;y=math.sqrt(R*R-x*x)
    v.extend([(x,y-.11,H-.035),(x,y+.02,H-.035),(x,y-.11,H),(x,y+.02,H)])
f=[]
for i in range(32):
    k=i*4;l=k+4;f.extend([(k+2,l+2,l+3,k+3),(k,k+1,l+1,l),(k,k+2,l+2,l),(k+1,l+1,l+3,k+3)])
f.extend([(0,2,3,1),(128,129,131,130)])
o=mesh('curved flush center threshold',v,f,FRAME,.001);o.matrix_world=F@BF

# Railings continue across the diagonal T shoulders and along the stair edges.
def rails(name,path):
    for a,b in zip(path,path[1:]):
        a,b=Vector(a),Vector(b);count=max(1,math.ceil((b-a).length/.68))
        for h in (.19,.345):beam(name+' continuous rail',a+UP*h,b+UP*h,.025,.018)
        for k in range(count):
            q=a.lerp(b,k/count);beam(name+' upright',q,q+UP*.354,.027,.029)
            prism(name+' bolted shoe',[(q.x-.026,q.y-.026),(q.x+.026,q.y-.026),(q.x+.026,q.y+.026),(q.x-.026,q.y+.026)],q.z-.012,q.z+.010,ALLOY,.001)
    q=Vector(path[-1]);beam(name+' end upright',q,q+UP*.354,.027,.029)
for side,sgn in enumerate((-1,1)):
    path=[bp(START+.025,sgn*BW),bp(END,sgn*BW),Vector((sgn*1.86,-1.38,H)),Vector((sgn*2.02,-1.17,H)),Vector((sgn*2.02,.02,H)),Vector((sgn*half,RUN,TOP))]
    rails('side %d'%side,path)
    # Recessed narrow grating tracks on the upper platform.
    grate('upper side drain %d'%side,sgn*1.97-.055,sgn*1.97+.055,3.10,6.43,TOP+.002)
    for i,y in enumerate((-.9,.65,2.25,3.35,5.95)):
        z=H if y<0 else H+(TOP-H)*min(1,y/RUN)
        x=sgn*(2.04 if y<3 else 2.23)
        prism('amber edge marker housing',[(x-.047,y-.055),(x+.047,y-.055),(x+.047,y+.055),(x-.047,y+.055)],z+.015,z+.095,STEEL,.006)
        prism('amber edge marker lens',[(x-.031,y-.037),(x+.031,y-.037),(x+.031,y+.037),(x-.031,y+.037)],z+.095,z+.105,WARM,.003)

# Reversible rail aperture at the new exact radial entrance.
cut=prism('hidden central rail entrance cutter',[(-BW-.04,START-.42),(BW+.04,START-.42),(BW+.04,START+.25),(-BW-.04,START+.25)],H+.035,H+.70,STEEL)
cut.matrix_world=F@BF;cut.hide_render=True;cut.hide_set(True);cut.display_type='WIRE'
affected=[];world_inv=(F@BF).inverted()
for o in bpy.data.collections['03 | Uniform slender steel railings'].objects:
    if o.type!='MESH' or o.hide_render:continue
    e=o.evaluated_get(DG);pts=[world_inv@e.matrix_world@v.co for v in e.data.vertices]
    if any(abs(v.x)<BW+.15 and START-.5<v.y<START+.32 and v.z>H+.025 for v in pts):
        m=o.modifiers.new('Rear-left bridge opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cut;affected.append(o.name)

# Raise the existing continuous rock in a U around the deck; preserve its keys.
key=wall.shape_key_add(name='Rear-left | raised enclosing rock walls',from_mix=True)
key.relative_key=wall.data.shape_keys.key_blocks['Basis']
# New key stores only this sculpt's delta; the previous live sculpts remain active.
baseline=[p.co.copy() for p in key.data]
basis=wall.data.shape_keys.key_blocks['Basis']
for i,p in enumerate(key.data):p.co=basis.data[i].co
mx=IV@wall.matrix_world;inv=mx.inverted();changed=0;max_raise=0;carved=0
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for i,co in enumerate(baseline):
    p=mx@co;x,y,z=p
    if not (-5.3<x<5.3 and -2.4<y<9.2 and 5.4<z<10.5):continue
    delta=0.;edge=2.02 if y<0 else (2.03 if y<RUN else 2.40)
    side=smooth((abs(x)-edge)/.48)*smooth((5.1-abs(x))/1.4)*smooth((y+1.5)/1.2)*smooth((8.6-y)/1.4)
    rear=smooth((y-6.70)/.50)*smooth((9.1-y)/1.0)*smooth((4.1-abs(x))/1.3)
    weight=max(side,rear)*smooth((z-5.4)/1.15)*smooth((10.5-z)/.9)
    grade=H+(TOP-H)*max(0,min(1,y/RUN))
    target=grade+1.25+.22*math.sin(x*2.1+y*1.6)+.12*math.sin(y*3.4-x)
    if rear>side:target=TOP+1.85+.26*math.sin(x*1.9)
    delta=max(0,target-z)*weight
    # Keep the actual walking area and the lowest stair approach clear.
    if -1.4<y<.04 and abs(x)<2.03:delta=min(delta,H-.255-z)
    elif 0<=y<=RUN and abs(x)<half+.035:
        underside=H+(TOP-H)*y/RUN-.255;delta=min(delta,underside-z)
    elif 2.98<y<6.69 and -2.27<x<2.35:delta=min(delta,TOP-.255-z)
    if abs(delta)>1e-5:
        q=p+UP*delta;key.data[i].co=basis.data[i].co+(inv@q-co);changed+=1;max_raise=max(max_raise,delta);carved+=delta<0
final_sculpt=P/'final-rock-deltas.json'
if final_sculpt.exists():
    sculpt=json.loads(final_sculpt.read_text());assert sculpt['vertex_count']==len(key.data)
    for i,p in enumerate(key.data):p.co=basis.data[i].co
    for i,delta in sculpt['deltas']:key.data[i].co=basis.data[i].co+Vector(delta)
key.value=1.;wall.active_shape_key_index=len(wall.data.shape_keys.key_blocks)-1
bpy.context.view_layer.update()
assert all(signature(bpy.data.objects[n])==sig for n,sig in protected.items())
report={'frame':[list(r) for r in F],'bridge_frame':[list(r) for r in BF],'floor_height':H,'upper_height':TOP,'bridge_width':BW*2,'bridge_length':END-START,'bridge_radial_dot':D.dot((mouth-center).normalized()),'bridge_start':START,'bridge_end':END,'center_radius':R,'stair_run':RUN,'stair_rise':rise,'stair_count':COUNT,'terrain_vertices_changed':changed,'terrain_max_raise':max_raise,'terrain_underdeck_clearance_vertices':carved,'aperture_objects':affected,'new_objects':len(made),'protected_object_geometry_unchanged':len(protected),'upper_polygon':upper,'landing_polygon':landing,'archive_collection':ARCH.name}
(P/'verification.json').write_text(json.dumps(report,indent=2))
COL['description']='Connected rear-left stairs and panel floors; flat radial grating bridge; diagonal T shoulders; local enclosing rock shape key.'
S['rear_left_platform_revision']='Connected steel floor and radial grating bridge with angled T landing and raised surrounding rock'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'rear-left-platform-detailed.blend'),copy=True)
result=report
