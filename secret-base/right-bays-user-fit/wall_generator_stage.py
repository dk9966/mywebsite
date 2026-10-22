"""Integrate a basalt buttress below the lower deck and slide the upper bay left."""
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
ROCK=coll('150 | One continuous inside cliff'); LOW=coll('151 | Octagonal service apron'); UP=coll('152 | Clipped upper gallery'); BR=coll('153 | 125 degree octagon connection'); RIG=coll('154 | New lighting and views')
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
OLD_YAW=math.radians(-84); OLD_R=np.array([[math.cos(OLD_YAW),-math.sin(OLD_YAW)],[math.sin(OLD_YAW),math.cos(OLD_YAW)]])
YAW=math.radians(-72); R=np.array([[math.cos(YAW),-math.sin(YAW)],[math.sin(YAW),math.cos(YAW)]])
INITIAL_ORIGIN=np.array((7.8,-3.0)); PREVIOUS_ORIGIN=INITIAL_ORIGIN-OLD_R[:,0]*2.40
FORWARD_SLIDE=1.10; ORIGIN=PREVIOUS_ORIGIN+OLD_R[:,0]*FORWARD_SLIDE
BRIDGE_BEARING=125.0
def xy(x,y):return ORIGIN+R@np.array((x,y))
def pt(x,y,z):return Vector((*xy(x,y),z))
class Bay:
    def __init__(self,name,z,poly,c,height,offset_y=0,offset_x=0):self.name=name;self.z=z;self.poly=poly;self.c=c;self.h=height;self.offset_y=offset_y;self.offset_x=offset_x
    def p(self,x,y,z=0):return pt(x+self.offset_x,y+self.offset_y,z+self.z)
    def box(self,n,p,d,ma=dark,bevel=.003):return box(self.name+' | '+n,self.p(*p),d,ma,self.c,YAW,bevel)
    def beam(self,n,p,q,w=.03,ma=dark,d=None):return beam(self.name+' | '+n,self.p(*p),self.p(*q),w,ma,self.c,d)

A=2.5;S8=A*(math.sqrt(2)-1);W=1.10;LEFT=-5.10;JOIN=-A+(W-S8)
LP=[(LEFT,-W),(JOIN,-W),(-S8,-A),(S8,-A),(A,-S8),(A,S8),(S8,A),(-S8,A),(JOIN,W),(LEFT,W)]
UPOLY=[(-4.15,.05),(-3.65,-.45),(1.70,-.45),(2.20,.05),(2.20,3.0),(-4.15,3.0)]
UPPER_SHIFT=-1.40
lo=Bay('Lower',F-.035,LP,LOW,2.16,-1.10);up=Bay('Upper',F+3.35,UPOLY,UP,2.05,offset_x=UPPER_SHIFT)

lo.offset_x+=LOW_DELTA_LOCAL[0];lo.offset_y+=LOW_DELTA_LOCAL[1];lo.z+=LOW_DELTA[2]
up.offset_x+=UP_DELTA_LOCAL[0];up.offset_y+=UP_DELTA_LOCAL[1];up.z+=UP_DELTA[2]
LEDGE_TOP=lo.z-.205

end=lo.p(0,-A+.14,.006)
bearing=math.radians(BRIDGE_BEARING);start=Vector((math.sin(bearing)*2.63,math.cos(bearing)*2.63,F))
axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();bw=.9
# The skew landing is trimmed to a line parallel to the octagon edge. Its
# opening is computed at that edge instead of reusing a perpendicular gap.
local_axis=R.T@np.array((axis.x,axis.y));local_side=R.T@np.array((side.x,side.y))
landing_corners=[];edge_crossings=[]
for sign in [-1,1]:
    q=end+side*bw/2*sign
    q-=axis*(local_side[1]*bw/2*sign/local_axis[1])
    landing_corners.append(q)
    edge_crossings.append(-.14*local_axis[0]/local_axis[1]+sign*bw/2*(local_side[0]-local_side[1]*local_axis[0]/local_axis[1]))
gate_left=min(edge_crossings)-.035;gate_right=max(edge_crossings)+.035

# A straight continuation replaces the former 90-degree cheek. Farther toward
# the foreground, two shallow changes of direction join the existing cave.
plan=[tuple(xy(8.6,.25)),tuple(xy(3.75,.25)),tuple(xy(-7.35,.25)),(3.8,10.6),(0,10.4),(-3.7,10.15),(-6.5,7.6),(-8.2,4.0),(-8.5,.7),(-9,-3.6),(-10.4,-7.6),(-11,-13),(-8.5,-19),(0,-23),(8.5,-20),(10.5,-16.2),tuple(xy(11.2,.25))]
def previous_xy(x,y):return PREVIOUS_ORIGIN+OLD_R@np.array((x,y))
reference_plan=[tuple(previous_xy(3.75,5.1)),tuple(previous_xy(3.75,.25)),tuple(previous_xy(-6.45,.25)),(3.8,10.6),(0,10.4),(-3.7,10.15),(-6.5,7.6),(-8.2,4.0),(-8.5,.7),(-9,-3.6),(-10.4,-7.6),(-11,-13),(-8.5,-19),(0,-23),(8.5,-20),(13.0,-14),(14,-7)]
reference_plan=np.array(reference_plan);source_lengths=np.linalg.norm(np.roll(reference_plan,-1,axis=0)-reference_plan,axis=1)
plan=np.array(plan);lengths=np.linalg.norm(np.roll(plan,-1,axis=0)-plan,axis=1);cum=np.r_[0,np.cumsum(source_lengths)];total=cum[-1]
param=[]
for i,L in enumerate(source_lengths):param.extend((cum[i]+np.linspace(0,L,max(2,math.ceil(L/.24)),endpoint=False)).tolist())
# Sample exact mouth jamb coordinates on the planar facade (segment index 1).
for x in [-5.36,-5.10,-4.70,-4.55,-4.37,-4.15,-3.8,1.95,2.20,2.53,2.68,2.85]:param.append(cum[1]+(3.75-x)*source_lengths[1]/lengths[1])
for x in [-4.70,-4.56,-4.22,2.06,2.54,2.68]:param.append(cum[1]+(3.75-x-UPPER_SHIFT)*source_lengths[1]/lengths[1])
for b,left,right in [(lo,-5.36,2.53),(up,-4.70,2.68)]:
    for x in [left,left+.48,right-.48,right]:param.append(cum[1]+(3.75-x-b.offset_x)*source_lengths[1]/lengths[1])
ss=np.array(sorted(set(round(v,8) for v in param))+[total]);theta=ss/total*math.tau;N=len(theta)-1
zv=np.unique(np.r_[np.linspace(-6.15,17.2,89),LEDGE_TOP,lo.z-.06,lo.z,lo.z+lo.h-.50,lo.z+lo.h,lo.z+lo.h+.24,lo.z+lo.h+.55,up.z-.06,up.z,up.z+up.h-.48,up.z+up.h]);M=len(zv)-1
def path(s):
    s=s%total;i=min(len(plan)-1,np.searchsorted(cum,s+1e-7)-1);u=(s-cum[i])/source_lengths[i];p=plan[i]*(1-u)+plan[(i+1)%len(plan)]*u;t=(plan[(i+1)%len(plan)]-plan[i])/lengths[i];normal=np.array((t[1],-t[0]))
    for j in [i,(i+1)%len(plan)]:
        if abs(s-cum[j])<1e-6 or abs(s-total)<1e-6:
            t0=(plan[j]-plan[j-1])/lengths[j-1];t1=(plan[(j+1)%len(plan)]-plan[j])/lengths[j];n0=np.array((t0[1],-t0[0]));n1=np.array((t1[1],-t1[0]));normal=(n0+n1)/(1+np.dot(n0,n1));break
    return p,normal,i
rng=np.random.default_rng(190721);field=np.zeros((N,M));mid=(ss[:-1]+ss[1:])/2;zm=(zv[:-1]+zv[1:])/2
# Basalt megablocks: long staggered rectangular beds cross the old narrow
# columns. A continuous shallow field carries their faces; there is no grout,
# collection of stacked boxes, or additional outer skin.
blocks=[]
row_z=np.array([-6.8,-4.1,-1.6,1.0,3.7,6.0,8.7,11.2,13.9,16.4])
for row,z0 in enumerate(row_z):
    cursor=-rng.uniform(0,5.5)
    while cursor<total:
        width=rng.uniform(3.4,6.8)
        height=rng.uniform(2.35,3.35)
        bottom=z0+rng.uniform(-.40,.26)
        top=bottom+height
        depth=round(rng.uniform(-.34,.13)/.055)*.055
        mask=((mid[:,None]>=cursor)&(mid[:,None]<cursor+width+.20)&(zm[None,:]>=bottom)&(zm[None,:]<top))
        field[mask]=depth
        blocks.append((cursor,width,bottom,top,depth))
        # A few broad substeps create rectangular broken shoulders, never
        # thin vertical strips running through multiple rock beds.
        if rng.random()<.23:
            step_start=cursor+width*rng.uniform(.10,.25);stop=cursor+width*rng.uniform(.72,.97)
            shoulder=top-rng.uniform(.38,.68)
            sub=(mid[:,None]>=step_start)&(mid[:,None]<stop)&(zm[None,:]>=shoulder)&(zm[None,:]<top)
            field[sub]=depth-.11
        cursor+=width
# Medium attached shoulders bridge the scale between huge calm faces and the
# pillar's smaller stepped formations. They never form long vertical channels.
for left,width,bottom,top,depth in blocks:
    if rng.random()>(.36 if width>4.6 else .12):continue
    shoulder_width=min(width*.70,rng.uniform(1.9,3.2))
    shoulder_height=rng.uniform(.85,1.65)
    x0=left if rng.random()<.5 else left+width-shoulder_width
    z0=bottom+rng.uniform(.10,max(.11,top-bottom-shoulder_height))
    mask=(mid[:,None]>=x0)&(mid[:,None]<x0+shoulder_width)&(zm[None,:]>=z0)&(zm[None,:]<z0+shoulder_height)
    field[mask]-=rng.choice([.11,.165])
# Place a few restrained, readable shoulders on the near return and back wall.
for s0,s1,z0,z1 in [(cum[0]+.35,cum[0]+2.5,2.2,4.6),(cum[0]+2.1,cum[0]+4.3,9.4,11.0),
                    (cum[0]+.5,cum[0]+3.1,13.2,14.9),(cum[3]+.4,cum[3]+2.8,8.6,10.1),
                    (cum[4]+1.1,cum[4]+3.5,12.0,13.5),(cum[5]+.2,cum[5]+2.9,4.7,6.2)]:
    mask=(mid[:,None]>=s0)&(mid[:,None]<s1)&(zm[None,:]>=z0)&(zm[None,:]<z1)
    field[mask]-=.165
# Rare tall blocks interrupt the horizontal emphasis without restoring bark.
for k in range(13):
    center=rng.uniform(0,total);z0=rng.uniform(-5.8,13.6);width=rng.uniform(2.2,3.2)
    mask=(abs(mid[:,None]-center)<width/2)&(zm[None,:]>z0)&(zm[None,:]<z0+rng.uniform(3.1,4.0))
    field[mask]=round(rng.uniform(-.27,-.08)/.055)*.055

def buttress_depth(x,z):
    """Broad attached foundation, inset below the floor then stepped outward.

    The upper shoulder follows the continuous octagon/wing footprint. Deeper
    stone beds widen slightly with long rectangular ledges and no outer shell.
    """
    dz=LEDGE_TOP-z
    if dz<0:return 0.
    if dz<1.65:tier=0.;stagger=0.;right_end=2.65
    elif dz<3.45+.22*math.sin(x*.71):tier=.14;stagger=.28;right_end=2.95
    elif dz<6.0+.28*math.sin(x*.58):tier=.03;stagger=-.20;right_end=2.54
    elif dz<8.9+.20*math.sin(x*.81):tier=.25;stagger=.16;right_end=3.08
    else:tier=.32;stagger=-.15;right_end=2.83
    spread=min(.45,max(0.,dz-1.7)*.055)
    if x<-5.25-spread or x>right_end:return 0.
    # Use broad block shoulders. A continuously changing depth per mesher
    # column would turn the diagonal footprint into many thin vertical ribs.
    if x<-3.40+stagger:reach=1.80
    elif x<-1.30+stagger:reach=2.65
    elif x<1.35+stagger:reach=3.43
    else:reach=2.24
    return max(0.,reach+tier-LOW_DELTA_LOCAL[1])

for i,s in enumerate(mid):
    p,n,seg=path(s)
    if seg==1:
        xx=(R.T@(p-ORIGIN))[0]
        for j,z in enumerate(zm):
            reach=buttress_depth(xx-lo.offset_x,z)
            if reach:
                # The old long-block relief becomes shallow detail on the
                # foundation mass; it does not create detached stacked stones.
                field[i,j]=field[i,j]*.75-reach
            # User-selected left bay shoulder: push a broad connected rock
            # mass outward; the actual room carve below keeps the deck clear.
            if -7.14<xx<-3.15 and z<lo.z+lo.h+.72:
                if z<LEDGE_TOP:
                    if -6.48<xx<-3.15:field[i,j]-=.68 if z>lo.z-3.1 else .46
                elif z<lo.z+lo.h:
                    if -7.14<xx<-4.2:field[i,j]-=1.12
                else:
                    field[i,j]-=1.18 if z<lo.z+lo.h+.38 else .69
            for b,left,right,depth in [(lo,-5.36,2.53,2.55),(up,-4.70,2.68,3.04)]:
                if left<xx-b.offset_x<right and b.z-.06<z<b.z+b.h:field[i,j]=depth+(LOW_DELTA_LOCAL[1] if b==lo else UP_DELTA_LOCAL[1])
            # A small continuous rock overhang houses the centered lower lamp.
            # Its two broken strata are part of the cave skin, not an added roof.
            if lo.z+lo.h<z<lo.z+lo.h+.24 and -1.45<xx-lo.offset_x<1.32:field[i,j]=-1.53+LOW_DELTA_LOCAL[1]
            elif lo.z+lo.h+.24<=z<lo.z+lo.h+.55 and -1.79<xx-lo.offset_x<1.62:field[i,j]=-.82+LOW_DELTA_LOCAL[1]
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
                rise=min(.48,z-(b.z+b.h-.50));bx=xx-b.offset_x;dx=rise*(max(0,1-abs(bx-left)/.65)-max(0,1-abs(bx-right)/.65));q+=R[:,0]*dx
    # Chipped, slightly uneven stone beds without softened step boundaries.
    zz=z
    if delta<.7:
        # Broad tilted strata plus angular chips. This changes geometry, not
        # the approved basalt shader; no smoothing or isolated rock boxes.
        wave=.025*math.sin(ss[ii]*.73+z*.41)+.012*math.sin(ss[ii]*2.1-z*.63)
        along=.026*math.sin(z*.77+ss[ii]*.24)+.010*math.sin(z*2.1+ss[ii]*1.4)
        fade=min(1.,abs(z-lo.z)/.30,abs(z-up.z)/.30)
        if seg==1 and -5.4<xx<3.5:fade=min(fade,abs(z-LEDGE_TOP)/.20)
        zz+=fade*(.038*math.sin(ss[ii]*.87+z*.39)+.010*math.sin(ss[ii]*2.2-z*.5))
        tangent=np.array((-n[1],n[0]));tangent/=np.linalg.norm(tangent)
        q+=fade*(n*wave+tangent*along)
    verts.append((*q,zz))
wall=mesh('150 | continuous cave with oblique carved rooms',verts,tri.tolist(),rockmat,ROCK)
bm=bmesh.new();bm.from_mesh(wall.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.000005,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'});bm.to_mesh(wall.data);bm.free();wall['single_inside_surface']=True;wall['source_mesher']='meshes/pillars/island_pillar_src/shape.py';wall['new_right_face_yaw']=math.degrees(YAW)

# Confine the surface finish to the newly built bay cliff. Copy the approved
# basalt shader rather than editing a material shared with the middle island.
bayrock=rockmat.copy();bayrock.name='150 | fractured bay basalt';nt=bayrock.node_tree;bs=nt.nodes.get('Principled BSDF');coords=next(n for n in nt.nodes if n.type=='TEX_COORD')
coarse=nt.nodes.new('ShaderNodeTexNoise');coarse.name='Coarse fractured stone relief';coarse.inputs['Scale'].default_value=3.1;coarse.inputs['Detail'].default_value=2.8;coarse.inputs['Roughness'].default_value=.78;coarse.inputs['Distortion'].default_value=.08;nt.links.new(coords.outputs['Object'],coarse.inputs['Vector'])
oldnormal=bs.inputs['Normal'].links[0].from_socket if bs.inputs['Normal'].links else None
relief=nt.nodes.new('ShaderNodeBump');relief.name='Angular stone face relief';relief.inputs['Strength'].default_value=.28;relief.inputs['Distance'].default_value=.075;nt.links.new(coarse.outputs['Fac'],relief.inputs['Height'])
if oldnormal:nt.links.new(oldnormal,relief.inputs['Normal'])
nt.links.new(relief.outputs['Normal'],bs.inputs['Normal'])
rough=nt.nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.15;rough.inputs['From Max'].default_value=.85;rough.inputs['To Min'].default_value=.78;rough.inputs['To Max'].default_value=.93;nt.links.new(coarse.outputs['Fac'],rough.inputs['Value']);nt.links.new(rough.outputs['Result'],bs.inputs['Roughness'])
for node in nt.nodes:
    if node.type=='BUMP' and node!=relief and node.inputs['Distance'].default_value>.03:node.inputs['Strength'].default_value=.17;node.inputs['Distance'].default_value=.040
wall.data.materials.append(bayrock)
for f in wall.data.polygons:
    center=sum((wall.data.vertices[v].co for v in f.vertices),Vector())/len(f.vertices)
    local=R.T@(np.array((center.x,center.y))-ORIGIN)
    foundation=(-5.9<local[0]<3.5 and -4.8<local[1]<.30 and center.z<LEDGE_TOP+.02)
    if (center.x>5.35 and -10<center.y<6.6) or foundation:f.material_index=1
bm=bmesh.new();bm.from_mesh(wall.data)
chipedges=[e for e in bm.edges if len(e.link_faces)==2 and all(f.material_index==1 for f in e.link_faces) and e.calc_face_angle(0)>.55]
if chipedges:bmesh.ops.bevel(bm,geom=chipedges,offset=.017,segments=1,affect='EDGES',profile=.5,clamp_overlap=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wall.data);bm.free()

