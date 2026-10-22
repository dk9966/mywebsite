"""A connected, zero-thickness cave surface built from the pillar step mesher.

The right-hand wall is a new height field, not an extracted/warped solid.
The left-wall field and material are reused, with two deliberate bay recesses.
"""
import argparse,ast,hashlib,importlib.util,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=P/'connected-cavern-single-surface.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.name='Cave | rebuilt continuous right terrain'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
old=S.objects['Cavern | single connected interior surface'];COL=old.users_collection[0]
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH' and o!=old}
rockmat=S.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0]

# Reuse the accepted left wall's exact broad patch field.
code=(P/'build_interior_cavern.py').read_text()
ns={'np':np,'math':math}
exec(code[code.index('rng=np.random.default_rng(76183)'):code.index('outer=np.full((N,M),20.)')],ns)
old_theta,old_z,old_field=ns['theta'],ns['zv'],ns['inner']
stations=[(0,13),(36,18),(45,17),(55,15.8),(65,12.2),(74,8.8),(86,7.6),(99,8.1),(115,8.5),(131,7.3),(144,6.1),(157,5.4),(174,4.95),(190,5.45),(203,7.1),(218,9.0),(234,11.0),(252,12.4),(270,12.55),(287,12.4),(307,11.8),(320,11.0),(334,10.8),(350,12.5)]
ang=np.radians([d for d,r in stations]);rad=np.array([r for d,r in stations]);poly=np.column_stack((np.cos(ang)*rad,np.sin(ang)*rad))
def plan_radius(t):
    direction=np.array((math.cos(t),math.sin(t)));hits=[]
    for p,q in zip(poly,np.roll(poly,-1,axis=0)):
        e=q-p;den=direction[0]*e[1]-direction[1]*e[0]
        if abs(den)<1e-9:continue
        u=(p[0]*direction[1]-p[1]*direction[0])/den;r=(p[0]*e[1]-p[1]*e[0])/den
        if r>0 and -1e-6<=u<=1.000001:hits.append(r)
    return min(hits)
def old_plan(deg):
    t=math.radians(deg);r=plan_radius(t);return np.array((math.cos(t)*r,math.sin(t)*r))
audit=json.loads((P.parent/'right-cave-bays/right-bays-audit.json').read_text());Z=audit['lower_floor_height'];H=audit['upper_floor_height']
anchors=json.loads(S['engineered_supports_revision'])['brackets']
knots=[(300,old_plan(300)),(305,(6.75,-9.7)),(310,(7.1,-8.2)),(315,(7.3,-6.8)),(320,(7.0,-5.9))]
knots += [(322+4*k,b['rock_anchor'][:2]) for k,b in enumerate(anchors)]
knots += [(346,(3.65,-1.85)),(350,(4.35,-1.05)),(354,(5.3,.1)),(360,(7.3,1.45)),(365,(9.98,2.22)),(370,(9.45,2.4)),(380,(7.5,2.57)),(390,(5.6,2.75)),(395,(4.6,2.9)),(400,(4.2,4.2)),(410,(3.6,6.9)),(420,(3.8,8.3)),(435,old_plan(75))]
kd=np.array([k for k,p in knots]);kp=np.array([p for k,p in knots],dtype=float)
def virtual(deg):return deg+360 if deg<75.000001 else deg
def on_right(deg):return deg<75.000001 or deg>299.999999
def base_plan(deg):
    if not on_right(deg):return old_plan(deg)
    u=virtual(deg);return np.array([np.interp(u,kd,kp[:,k]) for k in range(2)])
CENTER=np.array((-3.,-1.))
def convex_hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves=[]
    for order in [pts,list(reversed(pts))]:
        half=[]
        for p in order:
            while len(half)>=2 and cross(half[-2],half[-1],p)<=0:half.pop()
            half.append(p)
        halves.append(half[:-1])
    return np.array(halves[0]+halves[1])
rooms=[]
for key,padding in [('lower_floor_polygon',.45),('upper_floor_polygon',.55)]:
    footprint=np.array(audit[key]);center=footprint.mean(axis=0);delta=footprint-center
    expanded=footprint+delta/np.linalg.norm(delta,axis=1)[:,None]*padding
    # Include the open approach through the main chamber. This prevents a
    # radial return cheek from screening the bay when viewed from the front.
    rooms.append(convex_hull(np.vstack([expanded,CENTER,(.35,-11.45),(0.,0.)])))
def depth_at(deg,room):
    p=base_plan(deg);length=np.linalg.norm(p-CENTER);direction=(p-CENTER)/length;hits=[]
    for a,b in zip(room,np.roll(room,-1,axis=0)):
        edge=b-a;den=direction[0]*edge[1]-direction[1]*edge[0]
        if abs(den)<1e-9:continue
        v=a-CENTER;r=(v[0]*edge[1]-v[1]*edge[0])/den;t=(v[0]*direction[1]-v[1]*direction[0])/den
        if r>0 and -.00001<=t<=1.00001:hits.append(r)
    return max(0.,max(hits,default=0)-length)

# Extra boundaries occur only at architectural transitions and support seats.
theta=np.unique(np.round(np.r_[old_theta,np.radians([k%360 for k,p in knots]),np.radians(np.array([322,324,342,344,367,369,391,393])%360)],12));theta.sort();theta[0]=0;theta[-1]=math.tau
assert np.all(np.diff(theta)>1e-8) and theta[-1]==math.tau
zv=np.unique(np.r_[old_z,[5.15,6.40,Z-.18,Z+1.75,Z+2.05,Z+2.32,H-.39,H+2.55,H+2.95,H+3.35]]);zv.sort()
N,M=len(theta)-1,len(zv)-1
field=np.zeros((N,M));bay_mask=np.zeros((N,M),dtype=int)
for i in range(N):
    deg=math.degrees((theta[i]+theta[i+1])/2);u=virtual(deg);oi=min(len(old_theta)-2,np.searchsorted(old_theta,(theta[i]+theta[i+1])/2)-1)
    for j in range(M):
        z=(zv[j]+zv[j+1])/2;oj=min(len(old_z)-2,max(0,np.searchsorted(old_z,z)-1));d=old_field[oi,oj]
        # Broad, restrained steps through the rebuilt right section.
        if on_right(deg):d=6+(d-6)*.68
        if 320<=u<=346 and 5.15<=z<=6.40:d=6
        lower=on_right(deg) and Z-.18<z<Z+2.32 and depth_at(deg,rooms[0])>.06
        upper=on_right(deg) and H-.39<z<H+3.35 and depth_at(deg,rooms[1])>.06
        if lower or upper:
            length=depth_at(deg,rooms[0 if lower else 1]);d=14+(d-6)*8/max(.8,length)*.16;bay_mask[i,j]=1 if lower else 2
        field[i,j]=d
# Resolve four-cell corner saddles with the same topology rule as the pillar.
for _ in range(12):
    fixes=0
    for i in range(N):
        k=(i+1)%N
        for j in range(M-1):
            aa,bb,cc,dd=field[i,j],field[k,j],field[i,j+1],field[k,j+1]
            if min(aa,dd)>max(bb,cc)+1e-7:
                if bb>=cc:field[k,j]=min(aa,dd)
                else:field[i,j+1]=min(aa,dd)
                fixes+=1
            elif min(bb,cc)>max(aa,dd)+1e-7:
                if aa>=dd:field[i,j]=min(bb,cc)
                else:field[k,j+1]=min(bb,cc)
                fixes+=1
    if not fixes:break

# Emit the inside skin directly using the pillar's welded strip triangulator.
# No outside skin, caps, Boolean solids, visibility extraction, or smoothing.
spec=importlib.util.spec_from_file_location('pillar_steps',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)
plans=[base_plan(math.degrees(t)) for t in theta[:-1]];directions=[(p-CENTER)/np.linalg.norm(p-CENTER) for p in plans]
room_depths=[[max(.035,depth_at(math.degrees(t),room)) for t in theta[:-1]] for room in rooms]
def point(d,i,j):
    k=i%N;deg=math.degrees(theta[k]);p=plans[k];delta=d-6
    if not on_right(deg):xy=p+np.array((math.cos(theta[k]),math.sin(theta[k])))*delta
    else:
        vec=directions[k];room=0 if zv[j]<(Z+2.32+H-.39)/2 else 1
        def ramp(a,b,z):return max(0.,min(1.,(z-a)/(b-a)))
        # The cliff carries the projecting apron below, then steps back to the
        # service-wall line above it. The upper balcony likewise stays open in
        # front of its recessed rock mouth instead of getting a deep stone hood.
        setback=max(room_depths[0][k]*.68*ramp(Z-.10,Z+2.32,zv[j]),room_depths[1][k]*.30*ramp(H-.30,H+3.35,zv[j]))
        depth=max(.035,room_depths[room][k]-setback)
        xy=p+vec*(setback+(delta*depth/8 if delta>=0 else delta))
    z=zv[j];h=(z-zv[0])/(zv[-1]-zv[0]);warp=h**6*(.45*math.sin(theta[k]*5)-max(0.,-math.sin(theta[k])))
    if on_right(deg):warp*=max(0.,min(1.,(z-13.5)/3.3))
    return np.array((xy[0],xy[1],z+warp))
surf=shape.mesh_field(theta,zv,np.ones(M+1),field,np.full_like(field,30.))
tri,raw=surf.arrays();rad=np.hypot(raw[:,0],raw[:,2]);inside=np.all(rad[tri]<20,axis=1)
caps=np.all(abs(raw[tri,1]-zv[0])<1e-8,axis=1)|np.all(abs(raw[tri,1]-zv[-1])<1e-8,axis=1)
tri=tri[inside&~caps];used=np.unique(tri);remap=np.full(len(raw),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];raw=raw[used]
verts=[]
for x,z,y in raw:
    t=math.atan2(y,x)%math.tau;i=int(np.argmin(np.abs(np.angle(np.exp(1j*(theta[:-1]-t))))));j=int(np.argmin(abs(zv-z)));verts.append(point(math.hypot(x,y),i,j))
me=bpy.data.meshes.new('Cave | direct continuous step surface');me.from_pydata([tuple(p) for p in verts],[],tri.tolist());me.update();me.materials.append(rockmat)
bm=bmesh.new();bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.00002,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'});bm.to_mesh(me);bm.free()
wall=bpy.data.objects.new('Cavern | rebuilt continuous interior wall',me);COL.objects.link(wall);wall.matrix_world=FRAME;bpy.data.objects.remove(old,do_unlink=True)
wall['construction']='One directly generated interior step surface; shared vertices throughout. Same broad patch field and material as the left wall, using the original pillar mesher. Two integrated bay recesses.'
wall['surface_only']=True;wall['thickness']=0.;wall['source_mesher']='meshes/pillars/island_pillar_src/shape.py::Surface';wall['right_wall_rebuilt']=True
for p in me.polygons:p.use_smooth=False
bpy.context.view_layer.update();changed=[n for n,h in protected.items() if fingerprint(S.objects[n])!=h];assert not changed,changed

def inspect():
    bm=bmesh.new();bm.from_mesh(me);tree=BVHTree.FromBMesh(bm);seen=set();parts=[]
    for v in bm.verts:
        if v in seen:continue
        seen.add(v);stack=[v];n=0
        while stack:
            p=stack.pop();n+=1
            for e in p.link_edges:
                q=e.other_vert(p)
                if q not in seen:seen.add(q);stack.append(q)
        parts.append(n)
    boundary=sum(e.is_boundary for e in bm.edges);bad=sum(len(e.link_faces)>2 for e in bm.edges);loose=sum(not e.link_faces for e in bm.edges)
    todo={e for e in bm.edges if e.is_boundary};boundary_loops=[]
    while todo:
        e=todo.pop();stack=[e];count=0
        while stack:
            edge=stack.pop();count+=1
            for vertex in edge.verts:
                for other in vertex.link_edges:
                    if other in todo:todo.remove(other);stack.append(other)
        boundary_loops.append(count)
    degenerate=sum(f.calc_area()<1e-10 for f in bm.faces)
    contact=[tree.find_nearest(Vector(b['rock_anchor']))[3] for b in anchors]
    geo=json.loads(S['right_bay_geometry']);start,end=Vector(geo['start']),Vector(geo['end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0));blocked=[]
    for lane in [-.36,0,.36]:
        for z in [.12,.5,1.]:
            p=start-axis*.10+side*lane+Vector((0,0,z));q=end+axis*.10+side*lane+Vector((0,0,z));hit=tree.ray_cast(p,(q-p).normalized(),(q-p).length)
            if hit[0] is not None:blocked.append([lane,z,tuple(hit[0])])
    gaps=[]
    for z in [0,3,7.15,10.5,14]:
        for deg in range(360):
            t=math.radians(deg)
            if tree.ray_cast(Vector((0,0,z)),Vector((math.cos(t),math.sin(t),0)),60)[0] is None:gaps.append([z,deg])
    report={'source':str(SOURCE),'non_wall_meshes_preserved':len(protected),'changed_non_wall_meshes':changed,'vertices':len(me.vertices),'faces':len(me.polygons),'connected_components':parts,'boundary_edges':boundary,'nonmanifold_edges':bad,'loose_edges':loose,'support_anchor_distances':contact,'bridge_obstructions':blocked,'sampled_enclosure_gaps':gaps,'exterior_layers':0,'modifiers':len(wall.modifiers),'smooth_faces':sum(p.use_smooth for p in me.polygons)}
    report.update({'boundary_loops':boundary_loops,'degenerate_faces':degenerate})
    report['passed']=len(parts)==1 and len(boundary_loops)==2 and bad==0 and loose==0 and degenerate==0 and max(contact)<.001 and not blocked and not gaps and not changed
    bm.free();return report
report=inspect();tag='right-wall-rebuilt' if args.final else 'preview-right-wall'
(P/(tag+'-verification.json')).write_text(json.dumps(report,indent=2));print('REBUILD_CHECK',json.dumps(report),flush=True)
if args.final:assert report['passed'],report

rig=bpy.data.collections.new('16 | Rebuilt wall inspection cameras');S.collection.children.link(rig)
def camera(name,pos,target,lens=25,ortho=None):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));rig.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;ob.data.clip_end=200
    if ortho:ob.data.type='ORTHO';ob.data.ortho_scale=ortho
    return ob
under=camera('Rebuilt wall | under platform',(-.5,-10.8,6.3),(5.4,-2.5,2.8),32)
comparison=camera('Rebuilt wall | wall and pillar comparison',(-1.5,-10.7,9.2),(2.8,-.1,3.),26)
overview=S.objects['Interior | overview'];plan=S.objects['Interior | single surface inspection']
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.camera=overview;S.render.engine='CYCLES';S.cycles.samples=64 if args.final else 24;S.render.resolution_x=2000 if args.final else 1400;S.render.resolution_y=round(S.render.resolution_x*.6);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False
S.render.filepath=str(P/(tag+'-overview.png'));out=P/('connected-cavern-right-wall-rebuilt.blend' if args.final else 'preview-right-wall.blend')
tx=bpy.data.texts.get('rebuild_right_wall.py') or bpy.data.texts.new('rebuild_right_wall.py');tx.clear();tx.write(Path(__file__).read_text());tx.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True);bpy.ops.render.render(write_still=True)
S.camera=under;S.render.filepath=str(P/(tag+'-under-platform.png'));bpy.ops.render.render(write_still=True)
S.camera=comparison;S.render.filepath=str(P/(tag+'-comparison.png'));bpy.ops.render.render(write_still=True)
S.camera=plan;S.render.resolution_x=1500;S.render.resolution_y=1500;S.render.engine='BLENDER_WORKBENCH';sh=S.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';S.world.color=(.055,.065,.08)
for ob in S.objects:
    if ob.type=='MESH':ob.color=(.31,.37,.43,1) if ob==wall else (.64,.68,.73,1)
    if 'Atmosphere' in ob.name:ob.hide_render=True
S.render.filepath=str(P/(tag+'-plan.png'));bpy.ops.render.render(write_still=True)
print('REBUILT_WALL_SAVED',str(out),flush=True)
