"""Fresh construction of the reference's oblique, two-storey rock bays.

Only the approved central island and its existing material vocabulary are loaded.
No objects or builder code from the rejected right-bay reconstruction are used.
The rock uses the original pillar's shared-edge step mesher, mapped onto a new
cliff contour with an actual near cheek and a broad return face.
"""
import argparse, ast, hashlib, importlib.util, json, math, sys
from pathlib import Path
import bpy, bmesh, numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent; ROOT=P.parents[1]
ap=argparse.ArgumentParser(); ap.add_argument('--final',action='store_true'); ap.add_argument('--blockout',action='store_true'); args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=P.parent/'connected-cavern/connected-cavern-open-chamber.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); S=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z'); INV=FRAME.inverted(); F=6.871178627
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for cn in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates'] for o in bpy.data.collections[cn].objects if o.type=='MESH'}
rockmat=S.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0]
oldwall=S.objects['Cave | one continuous spacious wall']; bpy.data.objects.remove(oldwall,do_unlink=True)
for o in list(S.objects):
    if o.type in {'CAMERA','LIGHT'} and not any(c.name in ['03 | Steel perimeter and warm inset lamps','04 | Presentation cameras and studio lights'] for c in o.users_collection):bpy.data.objects.remove(o,do_unlink=True)

def coll(n):
    c=bpy.data.collections.new(n); S.collection.children.link(c); return c
ROCK=coll('150 | One continuous inside cliff'); LOW=coll('151 | Octagonal service apron'); UP=coll('152 | Clipped upper gallery'); BR=coll('153 | Wing connection'); RIG=coll('154 | New lighting and views')
steel=bpy.data.materials['Metal | satin blue steel']; trim=bpy.data.materials['Metal | machined edge highlights']; dark=bpy.data.materials['Metal | dark structural steel']; panel=bpy.data.materials['Metal | outer walkway alloy']; amber=bpy.data.materials['Metal | amber lamp diffusers']
def mat(n,color,metal=.6,rough=.36,emission=0):
    m=bpy.data.materials.new('150 | '+n); m.use_nodes=True; p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission;return m
lining=mat('satin graphite room lining',(.033,.044,.052),.72,.36); inset=mat('deep joints',(.004,.007,.010),.35,.6); brass=mat('faded yellow registration',(.33,.265,.095),.55,.36); white=mat('neutral cool practical glass',(.73,.87,1),.1,.24,5); copper=mat('oxidized conduit',(.16,.075,.031),.68,.4); red=mat('fire equipment paint',(.23,.052,.032),.35,.39); glass=mat('restrained status glass',(.023,.13,.16),.2,.24,.5)

def mesh(n,verts,faces,ma,c,bevel=0):
    me=bpy.data.meshes.new(n);me.from_pydata([tuple(v) for v in verts],[],faces);me.update();me.materials.append(ma);o=bpy.data.objects.new(n,me);c.objects.link(o);o.matrix_world=FRAME
    if bevel:
        mod=o.modifiers.new('Small fabricated edge radius','BEVEL');mod.width=bevel;mod.segments=2
        mod=o.modifiers.new('Weighted plate normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return o
def box(n,p,d,ma=dark,c=LOW,angle=0,bevel=.003):
    x,y,z=np.array(d)/2;vv=[(a*x,b*y,e*z) for a,b,e in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    o=mesh(n,vv,[tuple(reversed(f)) for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]],ma,c,bevel);o.matrix_world=FRAME@Matrix.Translation(Vector(p))@Matrix.Rotation(angle,4,'Z');return o
def beam(n,p,q,w=.04,ma=dark,c=LOW,d=None):
    p,q=Vector(p),Vector(q);v=q-p;o=box(n,(0,0,0),(w,d or w,v.length),ma,c,bevel=min(.003,w*.08));o.matrix_world=FRAME@Matrix.Translation((p+q)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return o
def slab(n,poly,z0,z1,ma,c,bevel=.003):
    nn=len(poly);return mesh(n,[(*p,z) for z in [z0,z1] for p in poly],[tuple(reversed(range(nn))),tuple(range(nn,2*nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)],ma,c,bevel)
def ring(n,center,r0,r1,z,ma,c):
    pts=[];faces=[];N=128
    for r in [r0,r1]:
        pts += [(center[0]+r*math.cos(i*math.tau/N),center[1]+r*math.sin(i*math.tau/N),z) for i in range(N)]
    for i in range(N):j=(i+1)%N;faces.append((i,i+N,j+N,j))
    return mesh(n,pts,faces,ma,c)
def light(n,p,target,watts,size=1,size_y=.5,color=(.7,.83,1)):
    d=bpy.data.lights.new(n,'AREA');d.energy=watts;d.shape='RECTANGLE';d.size=size;d.size_y=size_y;d.color=color;o=bpy.data.objects.new(n,d);RIG.objects.link(o);o.location=FRAME@Vector(p);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
YAW=math.radians(-84); ORIGIN=np.array((7.8,-3.0)); R=np.array([[math.cos(YAW),-math.sin(YAW)],[math.sin(YAW),math.cos(YAW)]])
def xy(x,y):return ORIGIN+R@np.array((x,y))
def pt(x,y,z):return Vector((*xy(x,y),z))
class Bay:
    def __init__(self,name,z,poly,c,height,offset_y=0):self.name=name;self.z=z;self.poly=poly;self.c=c;self.h=height;self.offset_y=offset_y
    def p(self,x,y,z=0):return pt(x,y+self.offset_y,z+self.z)
    def box(self,n,p,d,ma=dark,bevel=.003):return box(self.name+' | '+n,self.p(*p),d,ma,self.c,YAW,bevel)
    def beam(self,n,p,q,w=.03,ma=dark,d=None):return beam(self.name+' | '+n,self.p(*p),self.p(*q),w,ma,self.c,d)

A=2.5;S8=A*(math.sqrt(2)-1);W=1.10;LEFT=-5.10;JOIN=-A+(W-S8)
LP=[(LEFT,-W),(JOIN,-W),(-S8,-A),(S8,-A),(A,-S8),(A,S8),(S8,A),(-S8,A),(JOIN,W),(LEFT,W)]
UPOLY=[(-4.15,.05),(-3.65,-.45),(1.70,-.45),(2.20,.05),(2.20,3.0),(-4.15,3.0)]
lo=Bay('Lower',F-.035,LP,LOW,2.16,-1.10);up=Bay('Upper',F+3.35,UPOLY,UP,2.05)

# New perimeter: the near right rock return is a real contour segment. It is
# not an extra box or a separate shell attached over the cave wall.
plan=[tuple(xy(3.75,5.1)),tuple(xy(3.75,.25)),tuple(xy(-6.45,.25)),(3.8,10.6),(0,10.4),(-3.7,10.15),(-6.5,7.6),(-8.2,4.0),(-8.5,.7),(-9,-3.6),(-10.4,-7.6),(-11,-13),(-8.5,-19),(0,-23),(8.5,-20),(13.0,-14),(14,-7)]
plan=np.array(plan);lengths=np.linalg.norm(np.roll(plan,-1,axis=0)-plan,axis=1);cum=np.r_[0,np.cumsum(lengths)];total=cum[-1]
param=[]
for i,L in enumerate(lengths):param.extend((cum[i]+np.linspace(0,L,max(2,math.ceil(L/.24)),endpoint=False)).tolist())
# Sample exact mouth jamb coordinates on the planar facade (segment index 1).
for x in [-5.36,-5.10,-4.70,-4.55,-4.37,-4.15,-3.8,1.95,2.20,2.53,2.68,2.85]:param.append(cum[1]+(3.75-x))
ss=np.array(sorted(set(round(v,8) for v in param))+[total]);theta=ss/total*math.tau;N=len(theta)-1
zv=np.unique(np.r_[np.linspace(-6.15,17.2,89),lo.z-.06,lo.z,lo.z+lo.h-.50,lo.z+lo.h,lo.z+lo.h+.24,lo.z+lo.h+.55,up.z-.06,up.z,up.z+up.h-.48,up.z+up.h]);M=len(zv)-1
def path(s):
    s=s%total;i=min(len(plan)-1,np.searchsorted(cum,s+1e-7)-1);u=(s-cum[i])/lengths[i];p=plan[i]*(1-u)+plan[(i+1)%len(plan)]*u;t=(plan[(i+1)%len(plan)]-plan[i])/lengths[i];normal=np.array((t[1],-t[0]))
    for j in [i,(i+1)%len(plan)]:
        if abs(s-cum[j])<1e-6 or abs(s-total)<1e-6:
            t0=(plan[j]-plan[j-1])/lengths[j-1];t1=(plan[(j+1)%len(plan)]-plan[j])/lengths[j];n0=np.array((t0[1],-t0[0]));n1=np.array((t1[1],-t1[0]));normal=(n0+n1)/(1+np.dot(n0,n1));break
    return p,normal,i
rng=np.random.default_rng(190721);field=np.zeros((N,M));mid=(ss[:-1]+ss[1:])/2;zm=(zv[:-1]+zv[1:])/2
# Broad irregular cross-column plates. Features have different boundaries by
# height; there are no stacked isolated cubes and no repeating straight courses.
sites=[(s,z,rng.uniform(-.40,.25)) for s in np.arange(-2,total+2,1.65) for z in np.arange(-7,19,1.52)+rng.uniform(-.4,.4)]
dist=np.full((N,M),1e10)
for s,z,depth in sites:
    ds=np.minimum(abs(mid-s)%total,total-abs(mid-s)%total);dd=(ds[:,None]/1.35)**2+((zm[None,:]-z)/1.05)**2;sel=dd<dist;field[sel]=round(depth/.055)*.055;dist[sel]=dd[sel]
for i,s in enumerate(mid):
    p,n,seg=path(s)
    if seg==1:
        xx=3.75-(s-cum[1])
        for j,z in enumerate(zm):
            for b,left,right,depth in [(lo,-5.36,2.53,2.55),(up,-4.70,2.68,3.04)]:
                if left<xx<right and b.z-.06<z<b.z+b.h:field[i,j]=depth
            # A small continuous rock overhang houses the centered lower lamp.
            # Its two broken strata are part of the cave skin, not an added roof.
            if lo.z+lo.h<z<lo.z+lo.h+.24 and -1.45<xx<1.32:field[i,j]=-1.53
            elif lo.z+lo.h+.24<=z<lo.z+lo.h+.55 and -1.79<xx<1.62:field[i,j]=-.82
# Resolve four-cell saddle contacts before asking the pillar mesher for faces.
for _ in range(15):
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
spec=importlib.util.spec_from_file_location('accepted_pillar_mesher',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)
tri,raw=shape.mesh_field(theta,zv,np.ones(M+1),field+6,np.full_like(field,30)).arrays();radii=np.hypot(raw[:,0],raw[:,2]);keep=np.all(radii[tri]<15,axis=1)&~(np.all(abs(raw[tri,1]-zv[0])<1e-7,axis=1)|np.all(abs(raw[tri,1]-zv[-1])<1e-7,axis=1));tri=tri[keep];used=np.unique(tri);remap=np.full(len(raw),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];raw=raw[used]
verts=[]
for x,z,y in raw:
    t=math.atan2(y,x)%math.tau;ii=int(np.argmin(abs(np.angle(np.exp(1j*(theta[:-1]-t))))));p,n,seg=path(ss[ii]);delta=math.hypot(x,y)-6;q=p+n*delta
    if seg==1:
        local=R.T@(p-ORIGIN);xx=local[0]
        for b,left,right in [(lo,-5.36,2.53),(up,-4.70,2.68)]:
            if b.z+b.h-.50<z<=b.z+b.h+.01:
                rise=min(.48,z-(b.z+b.h-.50));dx=rise*(max(0,1-abs(xx-left)/.65)-max(0,1-abs(xx-right)/.65));q+=R[:,0]*dx
    # Chipped, slightly uneven stone beds without softened step boundaries.
    zz=z
    if delta<.7:
        # Broad tilted strata plus angular chips. This changes geometry, not
        # the approved basalt shader; no smoothing or isolated rock boxes.
        wave=.075*math.sin(ss[ii]*1.32+z*.71)+.038*math.sin(ss[ii]*3.7-z*.93)
        along=.095*math.sin(z*1.27+ss[ii]*.24)+.032*math.sin(z*3.4+ss[ii]*2.1)
        fade=min(1.,abs(z-lo.z)/.30,abs(z-up.z)/.30)
        zz+=fade*(.09*math.sin(ss[ii]*1.37+z*.39)+.025*math.sin(ss[ii]*4.2-z*.5))
        tangent=np.array((-n[1],n[0]));tangent/=np.linalg.norm(tangent)
        q+=fade*(n*wave+tangent*along)
    verts.append((*q,zz))
wall=mesh('150 | continuous cave with oblique carved rooms',verts,tri.tolist(),rockmat,ROCK)
bm=bmesh.new();bm.from_mesh(wall.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.000005,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'});bm.to_mesh(wall.data);bm.free();wall['single_inside_surface']=True;wall['source_mesher']='meshes/pillars/island_pillar_src/shape.py';wall['new_right_face_yaw']=-84

# Confine the surface finish to the newly built bay cliff. Copy the approved
# basalt shader rather than editing a material shared with the middle island.
bayrock=rockmat.copy();bayrock.name='150 | fractured bay basalt';nt=bayrock.node_tree;bs=nt.nodes.get('Principled BSDF');coords=next(n for n in nt.nodes if n.type=='TEX_COORD')
coarse=nt.nodes.new('ShaderNodeTexNoise');coarse.name='Coarse fractured stone relief';coarse.inputs['Scale'].default_value=5.2;coarse.inputs['Detail'].default_value=3.5;coarse.inputs['Roughness'].default_value=.78;coarse.inputs['Distortion'].default_value=.22;nt.links.new(coords.outputs['Object'],coarse.inputs['Vector'])
oldnormal=bs.inputs['Normal'].links[0].from_socket if bs.inputs['Normal'].links else None
relief=nt.nodes.new('ShaderNodeBump');relief.name='Angular stone face relief';relief.inputs['Strength'].default_value=.43;relief.inputs['Distance'].default_value=.12;nt.links.new(coarse.outputs['Fac'],relief.inputs['Height'])
if oldnormal:nt.links.new(oldnormal,relief.inputs['Normal'])
nt.links.new(relief.outputs['Normal'],bs.inputs['Normal'])
rough=nt.nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.15;rough.inputs['From Max'].default_value=.85;rough.inputs['To Min'].default_value=.70;rough.inputs['To Max'].default_value=.93;nt.links.new(coarse.outputs['Fac'],rough.inputs['Value']);nt.links.new(rough.outputs['Result'],bs.inputs['Roughness'])
for node in nt.nodes:
    if node.type=='BUMP' and node!=relief and node.inputs['Distance'].default_value>.03:node.inputs['Strength'].default_value=.29;node.inputs['Distance'].default_value=.066
wall.data.materials.append(bayrock)
for f in wall.data.polygons:
    center=sum((wall.data.vertices[v].co for v in f.vertices),Vector())/len(f.vertices)
    if center.x>5.35 and -10<center.y<6.6:f.material_index=1
bm=bmesh.new();bm.from_mesh(wall.data)
chipedges=[e for e in bm.edges if len(e.link_faces)==2 and all(f.material_index==1 for f in e.link_faces) and e.calc_face_angle(0)>.55]
if chipedges:bmesh.ops.bevel(bm,geom=chipedges,offset=.017,segments=1,affect='EDGES',profile=.5,clamp_overlap=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wall.data);bm.free()

# New manufactured decks: the floor union is a single native polygonal prism.
for b in [lo,up]:
    poly=[xy(p[0],p[1]+b.offset_y) for p in b.poly];slab(b.name+' | one-piece structural deck',poly,b.z-.21,b.z-.026,dark,b.c,.006);o=slab(b.name+' | continuous floor footprint',poly,b.z-.026,b.z,panel,b.c,.002);o['local_floor_polygon']=json.dumps(b.poly)
    for p,q in zip(b.poly,b.poly[1:]+b.poly[:1]):
        for z,w,ma in [(-.02,.014,trim),(-.19,.018,steel)]:b.beam('folded perimeter edge',(*p,z),(*q,z),w,ma)
        if (p[1]+q[1])/2<.6:
            le=np.linalg.norm(np.array(q)-p);steps=max(1,math.ceil(le/.72))
            for j in range(steps):
                a=np.array(p)+(np.array(q)-p)*(j+.5)/steps;b.box('fascia bolt strap',(*a,-.11),(.047,.04,.18),steel)
                if j%2==0:
                    e=(np.array(q)-p)/le*.14;b.beam('recessed amber edge light',(*(a-e),-.12),(*(a+e),-.12),.009,amber)
for ri,ro,ma in [(0,1.72,steel),(1.735,1.76,inset),(1.77,1.792,trim),(1.95,1.979,brass),(2.05,2.065,trim)]:ring('Lower | octagon-centered registration',xy(0,lo.offset_y),ri,ro,lo.z+.008,ma,LOW)

def rail(b,p,q,lights=False):
    p,q=np.array(p),np.array(q);nn=max(1,math.ceil(np.linalg.norm(q-p)/.67))
    for h in [.21,.48]:b.beam('slender continuous guard',(*p,h),(*q,h),.018,steel)
    for i in range(nn+1):
        v=p+(q-p)*i/nn;b.beam('rail stanchion',(*v,0),(*v,.50),.028,dark);b.box('stanchion sole plate',(*v,.01),(.085,.085,.025),steel)
    if lights:
        v=(p+q)/2;b.box('low marker casing',(*v,.21),(.05,.05,.21),dark);b.box('warm marker face',(v[0],v[1]-.029,.22),(.022,.009,.10),amber)
for i in [1,2,3,4]:rail(lo,LP[i],LP[(i+1)%len(LP)],i in [2,4])
GATE_X=-3.70
rail(lo,LP[0],(GATE_X-.55,-W));rail(lo,(GATE_X+.55,-W),LP[1]);rail(lo,(LEFT,W),(LEFT,-W))
for i in [0,1,2]:rail(up,UPOLY[i],UPOLY[(i+1)%6],i==1)

# Portals and lining are freshly dimensioned around the new carved mouths.
def portal(b,left,right,y,height):
    v=[(left,y,.02),(left,y,height-.48),(left+.45,y,height),(right-.45,y,height),(right,y,height-.48),(right,y,.02)]
    for p,q in zip(v,v[1:]):
        b.beam('recessed portal web',p,q,.11,dark,.14);pp=np.array(p);qq=np.array(q);pp[1]-=.079;qq[1]-=.079;b.beam('portal chamfer face',pp,qq,.048,steel,.025)
for b,left,right in [(lo,-5.20,2.39),(up,-4.56,2.54)]:portal(b,left,right,.38-b.offset_y,b.h-.07)

def back_panel(b,x0,x1,y,h):
    b.box('flush back lining',((x0+x1)/2,y,h/2),(x1-x0,.075,h),lining)
    for x in np.arange(x0+.1,x1,.58):b.box('vertical panel reveal',(x,y-.041,h/2),(.012,.007,h-.05),inset,.0)
    for z in [.12,h-.13]:b.beam('service bulkhead seam',(x0,y-.051,z),(x1,y-.051,z),.022,steel)
back_panel(lo,-.99,.99,2.47,1.99);back_panel(lo,-5.01,-2.36,1.09,1.99)
back_panel(up,-4.04,2.11,2.95,1.90)
for b,segs in [(lo,[((-2.36,1.09),(-.99,2.47)),((.99,2.47),(2.43,1.0))]),(up,[((-4.09,.5),(-4.09,2.94)),((2.16,.5),(2.16,2.94))])]:
    for p,q in segs:
        p,q=np.array(p),np.array(q);m=(p+q)/2;t=math.atan2(q[1]-p[1],q[0]-p[0]);box(b.name+' | angled room side',b.p(*m,b.h*.47),(np.linalg.norm(q-p),.06,b.h*.94),lining,b.c,YAW+t)

for b,y in [(lo,0),(up,1.25)]:
    h=b.h-.04;b.box('wide overhead fixture',(0,y,h),(1.16,.55,.075),dark)
    for off in [-.17,0,.17]:b.box('overhead lens',(0,y+off,h-.044),(1.04,.028,.016),white,.001)
    for xx in [-.45,.45]:b.beam('short ceiling mount',(xx,y,h+.035),(xx,y,b.h+.09),.021,steel)
    light(b.name+' | primary room practical',b.p(0,y,h-.08),b.p(0,y-.2,0),210,1.12,.5)
    b.box('front fixture lens',(0,y-.281,h-.016),(.92,.014,.021),white,.001)

if not args.blockout:
    # Lower: asymmetric maintenance alcove, access hatch, exposed pipes, small
    # tool bench and fire cabinet. No reused drawer/tool-wall assemblies.
    lo.box('pressure access door',(-3.37,1.025,.94),(.89,.10,1.86),dark)
    for x in [-3.79,-2.95]:lo.box('door brushed jamb',(x,.954,.94),(.045,.035,1.87),trim)
    lo.box('door inset',(-3.37,.961,1.01),(.68,.028,1.42),lining)
    lo.box('door upper glass',(-3.37,.94,1.65),(.39,.014,.14),glass)
    lo.box('door handle',(-3.07,.92,1.07),(.05,.06,.17),trim)
    for k in range(4):lo.box('door lower vent',(-3.37,.936,.32+k*.06),(.52,.016,.022),inset,.001)
    # Center rear workbench and separate suspended drawers.
    lo.box('wide machined worktop',(-.07,2.07,.74),(1.55,.58,.065),steel)
    for x in [-.66,.54]:
        lo.box('open bench pedestal',(x,2.15,.35),(.11,.37,.70),dark)
        lo.beam('bench foot',(x-.17,1.96,.03),(x+.17,1.96,.03),.06,steel)
    lo.box('underbench instrument drawer',(-.1,2.13,.58),(.82,.42,.24),lining)
    for x in [-.27,.23]:lo.box('bench test instrument',(x,2.16,.9),(.3,.22,.24),dark);lo.box('instrument screen',(x,2.042,.93),(.20,.01,.09),glass)
    lo.box('inset diagnostic board',(0,2.411,1.53),(1.55,.045,.60),dark)
    for k in range(7):
        x=-.60+k*.2;lo.box('diagnostic switch',(x,2.38,1.47),(.06,.033,.075),steel);lo.box('small readout',(x,2.37,1.69),(.038,.017,.033),amber)
    for x in [-2.12,-1.95]:
        lo.beam('vertical oxidized service pipe',(x,1.41,.08),(x,1.41,1.90),.032,copper)
        for z in [.3,1.1,1.8]:lo.box('pipe fixing clip',(x,1.415,z),(.075,.048,.037),steel)
    lo.box('fire service cabinet',(1.84,1.30,.51),(.32,.32,1.02),red,.014)
    lo.box('fire cabinet label',(1.84,1.13,.75),(.19,.009,.15),panel)
    for j in range(3):lo.box('low service crate',(-2.72+j*.25,.61,.17),(.22,.33,.34),lining)
    # Upper: storage gallery with a gantry and a slim operator desk.
    for x in [-3.32,-2.10,-.86,.38,1.51]:
        up.box('recessed equipment cabinet',(x,2.72,.61),(.70,.38,1.22),lining)
        for z in [.22,.52,.84]:up.box('cabinet panel seam',(x,2.516,z),(.60,.015,.01),inset,.001)
        up.box('cabinet latch',(x+.24,2.50,.62),(.024,.022,.13),trim)
        for xx in [-.12,.02,.16]:up.box('amber relay label',(x+xx,2.49,1.06),(.07,.01,.03),amber,.001)
    up.box('slender operator console',(-3.21,.91,.62),(.85,.48,.11),steel)
    for x in [-3.55,-2.87]:up.box('console upright',(x,.99,.31),(.06,.09,.62),dark)
    up.box('operator screen',(-3.20,1.07,.94),(.63,.065,.39),dark)
    up.box('operator glass',(-3.20,1.029,.96),(.54,.012,.27),glass)
    for x in [-3.7,1.65]:up.beam('gantry support',(x,1.87,0),(x,1.87,1.79),.065,steel)
    up.beam('gantry track',(-3.7,1.87,1.79),(1.65,1.87,1.79),.12,dark,.19)
    up.box('gantry carriage',(-.60,1.87,1.70),(.44,.36,.22),steel)
    up.beam('empty hoist chain',(-.60,1.87,1.58),(-.60,1.87,1.04),.017,dark)
    for x in [-1.15,-.57,.01]:
        up.box('ribbed storage case',(x,1.92,.20),(.49,.51,.40),lining,.015)
        for off in [-.16,.16]:up.box('case reinforcing band',(x+off,1.92,.22),(.027,.53,.42),steel)
    for b,positions in [(lo,[(-3.45,.82,1.89),(0,2.28,1.89),(1.69,1.32,1.87)]),(up,[(-2.92,2.76,1.81),(.59,2.76,1.81)])]:
        for x,y,z in positions:
            b.box('strip light socket',(x,y,z),(.89,.075,.068),dark);b.box('strip diffuser',(x,y-.043,z),(.77,.012,.029),white,.001);light(b.name+' | wall grazing practical',b.p(x,y-.08,z),b.p(x,y-1,.35),36,.8,.12)

# Rock seated triangular brackets; steel does not terminate in mid air.
bpy.context.view_layer.update();tree=BVHTree.FromPolygons([v.co for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons]);anchors=[]
for b,points in [(lo,[(-3.8,-1.04),(-2.6,-1.04),(-1.5,-2.03),(0,-2.43),(1.55,-2.0),(2.35,-.9)]),(up,[(-3.65,-.40),(-2.2,-.43),(-.5,-.43),(1.65,-.40)])]:
    for x,y in points:
        p=b.p(x,y,-.2);probe=b.p(x,.1,-1.10 if b==lo else -.83);hit=tree.find_nearest(probe);q=Vector(hit[0]);beam(b.name+' | engineered diagonal bracket',p,q,.085,dark,b.c,.13);beam(b.name+' | upper bracket flange',p,Vector((q.x,q.y,p.z)),.068,steel,b.c,.09)
        plate=box(b.name+' | rock bolting shoe',(0,0,0),(.25,.33,.044),steel,b.c);n=Vector(hit[1]);n=n if n.dot(p-q)>0 else -n;plate.matrix_world=FRAME@Matrix.Translation(q+n*.012)@n.to_track_quat('Z','Y').to_matrix().to_4x4();anchors.append(tree.find_nearest(q)[3])

# New straight wing bridge with a matching gate in the accepted center railing.
end=lo.p(GATE_X,-W+.15,.006);axis=Vector((end.x,end.y,0)).normalized();start=axis*2.63;start.z=F;axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();bw=.9
cut=box('temporary railing aperture',(0,0,0),(1.7,1.16,1.5),dark,BR,bevel=0);cut.matrix_world=FRAME@Matrix.Translation(start+axis*.12+Vector((0,0,.32)))@Matrix.Rotation(math.atan2(axis.y,axis.x),4,'Z')
bpy.context.view_layer.update()
rail_changes=[]
for o in list(bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects):
    if o.name.startswith(('Metal | continuous steel guardrail','Metal | guardrail polished top edge')):
        bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('New wing bridge opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);rail_changes.append(o.name)
    elif o.type=='MESH':
        p=INV@o.matrix_world.translation;delta=p-start
        if abs(delta.dot(side))<.51 and abs(delta.dot(axis))<.5 and p.z>F-.5:rail_changes.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
bpy.data.objects.remove(cut,do_unlink=True)
poly=[(start-side*bw/2).xy,(end-side*bw/2).xy,(end+side*bw/2).xy,(start+side*bw/2).xy];slab('Bridge | continuous deck',poly,lo.z-.12,F+.003,panel,BR)
for sign in [-1,1]:
    p=start+side*bw/2*sign;q=end+side*bw/2*sign;beam('Bridge | main steel girder',p-Vector((0,0,.16)),q-Vector((0,0,.16)),.08,dark,BR,.15)
    for h in [.21,.48]:beam('Bridge | continuous guard',p+Vector((0,0,h)),q+Vector((0,0,h)),.022,steel,BR)
    nn=math.ceil((q-p).length/.63)
    for i in range(nn+1):v=p.lerp(q,i/nn);beam('Bridge | stanchion',v,v+Vector((0,0,.50)),.03,dark,BR)
    for i in range(nn):
        p0=p.lerp(q,i/nn);p1=p.lerp(q,(i+1)/nn);beam('Bridge | side truss',p0-Vector((0,0,.28 if i%2 else .10)),p1-Vector((0,0,.10 if i%2 else .28)),.024,steel,BR)
for j in range(1,math.ceil((end-start).length/.11)):
    t=j/math.ceil((end-start).length/.11);v=start.lerp(end,t)+Vector((0,0,.008));beam('Bridge | transverse grip bar',v-side*.36,v+side*.36,.009,dark,BR,.014)

def camera(n,p,target,lens=30,ortho=None):
    o=bpy.data.objects.new(n,bpy.data.cameras.new(n));RIG.objects.link(o);o.location=FRAME@Vector(p);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens;o.data.clip_end=180
    if ortho:o.data.type='ORTHO';o.data.ortho_scale=ortho
    return o
hero=camera('150 | main cave camera',(0,-20,13.8),(1.3,.9,8.05),30)
detail=camera('150 | same azimuth detail',(.6,-17.5,12.8),(7.4,-2.1,8.8),44)
plan_cam=camera('150 | top-down arrangement',(2,-1,40),(2,-1,0),ortho=29)
for o in S.objects:
    if o.type=='LIGHT' and o not in RIG.objects.values():o.data.energy*=.38
light('150 | cave overhead shaft',(-1,2,16),(0,0,5),750,2,2,(.48,.66,.86))
light('150 | cliff edge grazing',(3,-7,14),(9,-2,9),330,1.4,3,(.55,.72,.91))
light('150 | far ambient fill',(-4,-7,10),(-8,3,7),32,3,4,(.44,.59,.73))
light('150 | right return faint rim',(13,-5,12),pt(3.6,2.1,9),170,1,4,(.37,.52,.66))
S.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.035
S.camera=hero;S.name='Cave | newly built 150 degree right bays'
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_extras=False
for ob in S.objects:
    if 'Atmosphere' in ob.name:ob.hide_set(True);ob.display_type='WIRE'
bpy.context.view_layer.update();changed=[n for n,h in protected.items() if fingerprint(S.objects[n])!=h];assert not changed,changed
bm=bmesh.new();bm.from_mesh(wall.data);seen=set();parts=[]
for v in bm.verts:
    if v in seen:continue
    todo=[v];seen.add(v);num=0
    while todo:
        p=todo.pop();num+=1
        for e in p.link_edges:
            q=e.other_vert(p)
            if q not in seen:seen.add(q);todo.append(q)
    parts.append(num)
bad=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges);bm.free()
view=R.T@(np.array((0,-20))-ORIGIN);azimuth=math.degrees(math.atan2(view[0],-view[1]))
report={'source':str(SOURCE),'new_architecture_built_from_scratch':True,'lower_polygon':LP,'upper_polygon':UPOLY,'common_yaw_degrees':-84,'camera_angle_from_facade_normal':azimuth,'middle_protected_count':len(protected),'middle_changes':changed,'wall_components':parts,'wall_invalid_edges':bad,'support_anchor_distances':anchors,'bridge_start':list(start),'bridge_end':list(end),'center_rail_gate_edits':rail_changes,'lower_marking_center':list(xy(0,lo.offset_y)),'lower_overhead_light_center':list(xy(0,lo.offset_y)),'origin':list(ORIGIN),'lower_offset_y':lo.offset_y,'lower_floor_z':lo.z,'upper_floor_z':up.z,'no_water':True,'no_vehicles':True}
report['passed']=not changed and len(parts)==1 and bad==0
tag='bays-150' if args.final else 'blockout-150' if args.blockout else 'preview-150';(P/(tag+'-checks.json')).write_text(json.dumps(report,indent=2));print('FRESH_150_CHECK',json.dumps(report),flush=True)
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.render.engine='CYCLES';S.cycles.samples=80 if args.final else 24;S.cycles.use_denoising=True;S.render.resolution_x=2400 if args.final else 1600;S.render.resolution_y=round(S.render.resolution_x*.56);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
tx=bpy.data.texts.new('build_bays_150.py');tx.write(Path(__file__).read_text());S.render.filepath=str(P/(tag+'-overview.png'));bpy.ops.wm.save_as_mainfile(filepath=str(P/(tag+'.blend')),compress=True);bpy.ops.render.render(write_still=True)
S.camera=detail;S.render.filepath=str(P/(tag+'-detail.png'));bpy.ops.render.render(write_still=True)
S.camera=plan_cam;S.render.engine='BLENDER_WORKBENCH';S.render.resolution_x=1400;S.render.resolution_y=1400;S.display.shading.light='STUDIO';S.display.shading.color_type='MATERIAL';S.display.shading.show_cavity=True
for o in S.objects:
    if 'Atmosphere' in o.name:o.hide_render=True
S.render.filepath=str(P/(tag+'-plan.png'));bpy.ops.render.render(write_still=True)
if args.final:
    # Local top views prove floor boundaries without rock or props covering them.
    floorcam=camera('150 | local floor inspection',(0,0,40),(0,0,0),ortho=10)
    for b in [lo,up]:
        for ob in S.objects:
            if ob.type=='MESH':ob.hide_render=not (ob.name.startswith(b.name+' | continuous floor footprint') or (b==lo and ob.name.startswith('Lower | octagon-centered registration')))
        cx=(min(v[0] for v in b.poly)+max(v[0] for v in b.poly))/2;cy=(min(v[1] for v in b.poly)+max(v[1] for v in b.poly))/2+b.offset_y
        floorcam.matrix_world=FRAME@Matrix.Translation((*xy(cx,cy),40))@Matrix.Rotation(YAW,4,'Z');S.camera=floorcam;S.render.resolution_x=1600;S.render.resolution_y=1100;S.render.filepath=str(P/(tag+'-'+b.name.lower()+'-footprint.png'));bpy.ops.render.render(write_still=True)
print('FRESH_150_SAVED',str(P/(tag+'.blend')),flush=True)
