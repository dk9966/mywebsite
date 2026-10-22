"""Replace the blockwork aesthetic with a bumpy, faceted sculpting base."""
import bpy,bmesh,json,math,array,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,noise
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source-live-snapshot.blend'))
S=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.preferences.filepaths.save_version=0
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
fit=json.loads((P.parent/'right-bays-user-fit/coherent-bays-checks.json').read_text())
R=np.array([[math.cos(math.radians(-72)),-math.sin(math.radians(-72))],[math.sin(math.radians(-72)),math.cos(math.radians(-72))]])
ORIGIN=np.array(fit['origin']);lo=fit['bay_info']['lower'];up=fit['bay_info']['upper']
wall=S.objects['150 | continuous cave with oblique carved rooms'];pillar=S.objects['Central rock mound | continuous cross-column extrusions']
def signature(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        a=array.array('f',[0.])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
protected={o.name:signature(o) for o in S.objects if o not in (wall,pillar)}
def xy(x,y):return ORIGIN+R@np.array((x,y))
plan=np.array([xy(8.6,.25),xy(3.75,.25),xy(-7.35,.25),(3.8,10.6),(0,10.4),(-3.7,10.15),(-6.5,7.6),(-8.2,4.0),(-8.5,.7),(-9,-3.6),(-10.4,-7.6),(-11,-13),(-8.5,-19),(0,-23),(8.5,-20),(10.5,-16.2),xy(11.2,.25)])
lengths=np.linalg.norm(np.roll(plan,-1,axis=0)-plan,axis=1);cum=np.r_[0,np.cumsum(lengths)];total=cum[-1]
def path(s):
    s=s%total;i=min(len(plan)-1,max(0,np.searchsorted(cum,s+1e-8)-1));u=(s-cum[i])/lengths[i]
    p=plan[i]*(1-u)+plan[(i+1)%len(plan)]*u
    t=(plan[(i+1)%len(plan)]-plan[i])/lengths[i];n=np.array((t[1],-t[0]))
    # Smooth plan corners over a short span, retaining the long bay facade.
    if i not in (0,1,16):
        prev=plan[i-1];a=plan[i];b=plan[(i+1)%len(plan)];nxt=plan[(i+2)%len(plan)]
        p=.5*((2*a)+(-prev+b)*u+(2*prev-5*a+4*b-nxt)*u*u+(-prev+3*a-3*b+nxt)*u*u*u)
        tangent=.5*((-prev+b)+2*(2*prev-5*a+4*b-nxt)*u+3*(-prev+3*a-3*b+nxt)*u*u)
        tangent/=np.linalg.norm(tangent);n=np.array((tangent[1],-tangent[0]))
    return p,n,i
def smooth(a,b,x):
    t=min(1.,max(0.,(x-a)/(b-a)));return t*t*(3-2*t)
def nval(x,y,z,scale):return noise.noise_vector(Vector((x*scale+17.2,y*scale-8.3,z*scale+4.1)))[0]
def base_depth(s,z):
    p,n,seg=path(s)
    d=.76*nval(*p,z,.38)+.31*nval(*p,z,.87)+.12*math.sin(s*1.5+z*1.9)
    if seg==1:
        xx=(R.T@(p-ORIGIN))[0];bx=xx-lo['offset_x'];below=1-smooth(lo['z']-.24,lo['z']-.03,z)
        # One rounded continuous foundation, not tiered or stepped masonry.
        foot=(2.75*math.exp(-((bx+.12)/2.4)**4)+1.2*math.exp(-((bx+3.7)/1.8)**4))
        d-=foot*below*(.87+.13*math.cos((z-lo['z'])*.45))
        # Broad shoulder beside the left wing carries the previous extension.
        d-=.85*math.exp(-((xx+6.25)/1.5)**2-((z-8.5)/3.5)**2)
    return d
rooms=[(lo,-5.36,2.53,3.837,2.16),(up,-4.70,2.68,3.210,2.05)]
def carve(s,z,d):
    p,n,seg=path(s)
    if seg!=1:return d
    xx=(R.T@(p-ORIGIN))[0]
    for b,left,right,depth,h in rooms:
        x=xx-b['offset_x'];floor=b['z'];roof=floor+h
        mask=smooth(left-.75,left+.015,x)*(1-smooth(right-.015,right+.75,x))
        mask*=smooth(floor-.22,floor-.065,z)*(1-smooth(roof+.015,roof+.85,z))
        d=d*(1-mask)+depth*mask
    return d

# Preserve exact attachment positions using broad smooth bumps in the new rock.
anchor_constraints=[]
for ob in S.objects:
    if 'rock bolting shoe' in ob.name:
        q=INV@ob.matrix_world.translation;local=R.T@(np.array(q[:2])-ORIGIN)
        ss=cum[1]+3.75-local[0]
        anchor_constraints.append((ss,q.z,local[1]-.25+.01))
A=np.array([[math.exp(-((s-t)/.78)**2-((z-w)/.85)**2) for t,w,_ in anchor_constraints] for s,z,_ in anchor_constraints])
rhs=np.array([d-carve(s,z,base_depth(s,z)) for s,z,d in anchor_constraints])
weights=np.linalg.solve(A+np.eye(len(A))*1e-8,rhs)
def depth(s,z):
    d=carve(s,z,base_depth(s,z))
    # Anchor corrections lie below the floors, away from standing areas.
    for w,(t,h,_) in zip(weights,anchor_constraints):d+=w*math.exp(-((s-t)/.78)**2-((z-h)/.85)**2)
    return d

# Delaunay triangles on a jittered parameter sheet avoid masonry-like rows.
rng=np.random.default_rng(85261);pts=[];edges=[]
def add(s,z):
    pts.append((float(s),float(z)));return len(pts)-1
zmin,zmax=-6.15,17.2
zs=np.linspace(zmin,zmax,26)
boundary=[]
for s in np.linspace(0,total,math.ceil(total/.95)+1):boundary.append(add(s,zmin))
for z in zs[1:]:boundary.append(add(total,z))
for s in np.linspace(total,0,math.ceil(total/.95)+1)[1:]:boundary.append(add(s,zmax))
for z in zs[-2:0:-1]:boundary.append(add(0,z))
edges.extend((boundary[i],boundary[(i+1)%len(boundary)]) for i in range(len(boundary)))
for s in np.arange(.55,total-.4,.95):
    for z in np.arange(zmin+.6,zmax-.3,.95):add(s+rng.uniform(-.22,.22),z+rng.uniform(-.22,.22))
# Local inset constraints keep alcove floor/roof transitions and corners fitted.
for b,left,right,dep,h in rooms:
    x0=left+b['offset_x'];x1=right+b['offset_x']
    zlevels=[b['z']-.22,b['z']-.065,b['z']+.10,b['z']+h,b['z']+h+.85]
    for z in zlevels:
        ids=[]
        for x in np.linspace(x0-.76,x1+.76,math.ceil((x1-x0+1.52)/.48)+1):ids.append(add(cum[1]+3.75-x,z))
        edges.extend(zip(ids,ids[1:]))
    for x in [x0-.76,x0+.02,x1-.02,x1+.76]:
        ids=[add(cum[1]+3.75-x,z) for z in np.linspace(b['z']-.22,b['z']+h+.85,9)]
        edges.extend(zip(ids,ids[1:]))
for s,z,d in anchor_constraints:add(s,z)
uv,_,faces,*_=delaunay_2d_cdt([Vector(v) for v in pts],edges,[],0,1e-5)
verts=[]
for s,z in uv:
    p,n,i=path(s);q=p+n*depth(s,z);verts.append((*q,z))

# A simple matte material lets the large triangular planes define the surface.
ma=bpy.data.materials.new('Terrain | matte blue-gray facets');ma.use_nodes=True
bs=ma.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.115,.155,.184,1);bs.inputs['Roughness'].default_value=.86
ma.diffuse_color=(.30,.37,.42,1)
def install(ob,vv,ff,label):
    me=bpy.data.meshes.new(label);me.from_pydata(vv,[],ff);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free();me.update();me.materials.append(ma)
    ob.data=me;ob.matrix_world=FRAME
    for m in list(ob.modifiers):ob.modifiers.remove(m)
    for f in me.polygons:f.use_smooth=False
    ob.use_mesh_mirror_x=False;ob.use_mesh_mirror_y=False;ob.use_mesh_mirror_z=False
    ob['terrain_style']='Broad natural bumps; flat triangular faces; no blockwork or shader bump.'
    return me
install(wall,verts,faces,'Faceted cave | continuous inner skin')

# The central support uses irregular staggered rings with broad noisy lobes.
# Its top remains directly beneath the accepted platform; the bottom widens.
vv=[];ff=[];N=21;M=12;bottom=-.66;top=6.651
for j in range(M+1):
    t=j/M;z=bottom+(top-bottom)*t
    for i in range(N):
        a=math.tau*(i+.32*(j%2)+rng.uniform(-.13,.13))/N
        zz=z+(rng.uniform(-.20,.20) if 0<j<M else 0)
        radius=2.13+.43*(1-t)**1.6
        bump=.29*nval(math.cos(a)*2.2,math.sin(a)*2.2,zz,.68)+.16*math.sin(3*a+.4*zz)+.11*math.cos(5*a-.7*zz)
        bump*=min(1.,(top-zz)/.75)
        r=radius+bump
        vv.append((r*math.cos(a),r*math.sin(a),zz))
for j in range(M):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;c=(j+1)*N+i;d=(j+1)*N+(i+1)%N
        ff.extend([(a,b,c),(b,d,c)] if j%2 else [(a,b,d),(a,d,c)])
vv.extend([(0,0,bottom),(0,0,top)])
for i in range(N):ff.extend([(len(vv)-2,(i+1)%N,i),(len(vv)-1,M*N+i,M*N+(i+1)%N)])
install(pillar,vv,ff,'Faceted pillar | broad irregular triangular bumps')

def topo(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);seen=set();parts=[]
    for v in bm.verts:
        if v in seen:continue
        queue=[v];seen.add(v);count=0
        while queue:
            v=queue.pop();count+=1
            for e in v.link_edges:
                q=e.other_vert(v)
                if q not in seen:seen.add(q);queue.append(q)
        parts.append(count)
    r={'vertices':len(bm.verts),'triangles':len(bm.faces),'components':parts,'invalid_edges':sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges)};bm.free();return r
report={'terrain':{o.name:topo(o) for o in [wall,pillar]},'platform_changes':[n for n,h in protected.items() if signature(S.objects[n])!=h]}
tree=BVHTree.FromPolygons([v.co for v in wall.data.vertices],[tuple(f.vertices) for f in wall.data.polygons])
def inside(x,y,poly):
    yes=False
    for p,q in zip(poly,poly[1:]+poly[:1]):
        if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:yes=not yes
    return yes
bad=[]
for label,b in fit['bay_info'].items():
    for x in np.arange(min(p[0] for p in b['poly'])+.15,max(p[0] for p in b['poly']),.22):
        for y in np.arange(min(p[1] for p in b['poly'])+.15,max(p[1] for p in b['poly']),.22):
            if inside(x,y,b['poly']):
                p=Vector((*xy(x+b['offset_x'],y+b['offset_y']),b['z']+.09))
                hit=tree.ray_cast(p,Vector((0,0,1)),1.75)
                if hit[0] is not None:bad.append([label,float(x),float(y),list(hit[0])])
report['standing_intrusions']=bad
report['anchor_gaps']=[float(tree.find_nearest(INV@ob.matrix_world.translation)[3]) for ob in S.objects if 'rock bolting shoe' in ob.name]
report['passed']=not report['platform_changes'] and not bad and max(report['anchor_gaps'])<.065 and all(t['invalid_edges']==0 and len(t['components'])==1 for t in report['terrain'].values())
(P/'checks.json').write_text(json.dumps(report,indent=2));print('CHECKS',json.dumps(report),flush=True)
# Write a candidate even if a fit check identifies a local area to correct.
bpy.ops.object.select_all(action='DESELECT');wall.select_set(True);bpy.context.view_layer.objects.active=wall
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.shading.type='SOLID';sp.shading.light='STUDIO';sp.shading.color_type='MATERIAL';sp.shading.show_cavity=True;sp.shading.cavity_type='BOTH'
S.name='Cave | natural faceted terrain sculpt base'
S.camera=S.objects['150 | main cave camera'];S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True
S.render.resolution_x=1600;S.render.resolution_y=896;S.render.resolution_percentage=100
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'cave-faceted-sculpt.blend'),compress=True)
for name,suffix in [('150 | main cave camera','overview'),('150 | same azimuth detail','detail')]:
    S.camera=S.objects[name];S.render.filepath=str(P/('faceted-'+suffix+'.png'));bpy.ops.render.render(write_still=True)
print('DONE',flush=True)
