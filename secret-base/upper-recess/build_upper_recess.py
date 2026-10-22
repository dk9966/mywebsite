"""Rebuild the upper alcove in world geometry, retaining the approved cave below it."""
import argparse,ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
SOURCE=P/'preview-source.blend'
BASE=P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene
H=9.671178627;JOIN=H-.43
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH'}
removed=[]
for cname in ['06 | Upper recessed aircraft hangar','14 | Upper bay finish']:
    c=bpy.data.collections.get(cname)
    if c:
        for o in list(c.objects):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)
for o in list(S.objects):
    if o.type=='LIGHT' and (o.name.startswith('Upper |') or 'hangar' in o.name.lower()):bpy.data.objects.remove(o,do_unlink=True)
def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
DECK=collection('16 | Clean recessed upper balcony');RIG=collection('17 | Upper alcove views');TEMP=collection('Upper temporary construction')
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','box','cylinder'}],type_ignores=[]),'metal_helpers','exec'),globals())
steel=bpy.data.materials['Metal | satin blue steel'];panel=bpy.data.materials['Metal | outer walkway alloy'];dark=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Metal | machined edge highlights'];white=bpy.data.materials['Bays | cool strip light'];rockmat=bpy.data.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0]
def apply(ob,mod):
    bpy.context.view_layer.objects.active=ob;ob.hide_set(False);bpy.ops.object.modifier_apply(modifier=mod.name)
def boolean(ob,cut,operation):
    mod=ob.modifiers.new('True three dimensional alcove boundary','BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=cut;apply(ob,mod)
def clip_z(me,z,above):
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=above,clear_outer=not above)
    bm.to_mesh(me);bm.free();me.update()
# Regenerate the original unexcavated rock at the upper level. The old screen-
# projected excavation cannot be made coherent by adding more trim to its lips.
# Join at a height below that excavation; the lower bay stays byte-for-byte exact.
cache=P/'preview-original-upper-rock.blend'
if not cache.exists():
    rock=bpy.data.objects['Central rock mound | continuous cross-column extrusions'];dg=bpy.context.evaluated_depsgraph_get();ev=rock.evaluated_get(dg);base_mesh=bpy.data.meshes.new_from_object(ev)
    zmin=min((INV@(rock.matrix_world@vv.co)).z for vv in base_mesh.vertices)
    for vv in base_mesh.vertices:vv.co=INV@(rock.matrix_world@vv.co);vv.co.z-=zmin
    base_mesh.update()
    ns={'bpy':bpy,'FRAME':FRAME,'Matrix':Matrix,'GEO':TEMP,'base_mesh':base_mesh}
    orig=ast.parse((P.parent/'right-cave-bays/build_right_bays.py').read_text())
    exec(compile(ast.Module(body=[n for n in orig.body if isinstance(n,ast.FunctionDef) and n.name in {'rock_mass','stacked_rock'}],type_ignores=[]),'original_terrain_mesher','exec'),ns)
    masses=[ns['stacked_rock']('RESTORE main',(10.1,6.),(1.95,3.2),.10),ns['stacked_rock']('RESTORE left',(5.4,4.),(.57,1.95),-.16),ns['stacked_rock']('RESTORE right',(12.25,1.),(.72,1.5),.32)]
    cam=bpy.data.objects['Bays | wide reference camera'];oldres=(S.render.resolution_x,S.render.resolution_y);S.render.resolution_x=1199;S.render.resolution_y=654
    contour=[(993,-160),(969,-5),(953,28),(962,54),(932,80),(922,117),(901,149),(883,180),(889,201),(856,218),(837,244),(844,274),(826,302),(819,337),(827,359),(808,383),(820,421),(822,454),(807,494),(826,535),(821,575),(846,615),(872,690),(880,1000),(2000,1000),(2000,-160)]
    fr=cam.data.view_frame(scene=S);xs=[p.x for p in fr];ys=[p.y for p in fr];zz=fr[0].z
    rays=[Vector((min(xs)+(max(xs)-min(xs))*x/1199,min(ys)+(max(ys)-min(ys))*(1-y/654),zz))/(-zz) for x,y in contour]
    vs=[tuple(ray*depth) for depth in [8,65] for ray in rays];n=len(rays);fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cut=mesh('temporary original boundary',vs,fs,rockmat,TEMP);cut.matrix_world=cam.matrix_world.copy()
    for ob in masses:
        boolean(ob,cut,'INTERSECT');T=INV@ob.matrix_world
        for vertex in ob.data.vertices:vertex.co=T@vertex.co
        ob.matrix_world=FRAME;clip_z(ob.data,JOIN,True)
    bpy.data.objects.remove(cut,do_unlink=True);S.render.resolution_x,S.render.resolution_y=oldres
    bpy.data.libraries.write(str(cache),set(masses),compress=True)
else:
    with bpy.data.libraries.load(str(cache),link=False) as (f,t):t.objects=[n for n in f.objects if 'RESTORE' in n]
    masses=t.objects
    for ob in masses:TEMP.objects.link(ob)
original_names=['Bays | continuous cave wall | stratum 0','Bays | left broken cave return | stratum 0','Bays | right overlapping cave cheek | stratum 0']
changed_rock=[]
restore_lookup={key:next(o for o in masses if key in o.name) for key in ['RESTORE main','RESTORE left','RESTORE right']}
for key,name in zip(['RESTORE main','RESTORE left','RESTORE right'],original_names):
    old=bpy.data.objects[name];restored=restore_lookup[key]
    clip_z(old.data,JOIN,False)
    bm=bmesh.new();bm.from_mesh(old.data);bm.from_mesh(restored.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
    bm.to_mesh(old.data);bm.free();old.data.update();bpy.data.objects.remove(restored,do_unlink=True);changed_rock.append(name)
    print('RESTORED_ORIGINAL_UPPER',name,len(old.data.vertices),flush=True)
# Entire bay uses one orthonormal frame, moved right and back relative to the old
# balcony. The aperture and every metal profile derive from the same section.
origin=Vector((8.40,3.35));angle=math.radians(-22.5);u=Vector((math.cos(angle),math.sin(angle)));v=Vector((-u.y,u.x))
def at(x,y,z):
    x*=1.10
    return Vector((origin.x+u.x*x+v.x*y,origin.y+u.y*x+v.y*y,z))
def prism(name,section,depths,ma,c=DECK):
    nn=len(section);vs=[tuple(at(x,y,z)) for y in depths for x,z in section]
    fs=[tuple(reversed(range(nn))),tuple(range(nn,2*nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
    return mesh(name,vs,fs,ma,c)
section=[(-2.64,H-.33),(-2.64,H+2.10),(-1.86,H+3.06),(1.82,H+3.06),(2.64,H+2.10),(2.64,H-.33)]
cut=prism('Upper | temporary coherent excavation',section,[-14.,5.10],rockmat,TEMP)
for name in original_names:boolean(bpy.data.objects[name],cut,'DIFFERENCE')
bpy.data.objects.remove(cut,do_unlink=True)
# A minimal stone lining bridges natural variations in the rock to a coherent
# polygonal mouth. It is a single interior sheet, with no outside skin.
inside=[(-2.61,H-.03),(-2.61,H+2.08),(-1.84,H+3.03),(1.80,H+3.03),(2.61,H+2.08),(2.61,H-.03)]
vs=[tuple(at(x,y,z)) for y in [.72,2.7,5.08] for x,z in inside];nn=len(inside)
fs=[(j*nn+i,j*nn+i+1,(j+1)*nn+i+1,(j+1)*nn+i) for j in range(2) for i in range(nn-1)]
fs.append(tuple(range(2*nn,3*nn)))
lining=mesh('Upper | connected rock reveal and rear',vs,fs,rockmat,DECK)
# Floor: one clipped slab, restrained large panel seams, no props or markings.
poly=[(-2.60,-.16),(2.60,-.16),(2.60,5.06),(-2.60,5.06)]
nn=len(poly);vs=[tuple(at(x,y,z)) for z in [H-.33,H] for x,y in poly];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
deck=mesh('Upper | single seated balcony slab',vs,fs,panel,DECK,.003)
def beam(name,p,q,width,depth,ma=dark):
    p,q=Vector(p),Vector(q);d=q-p;ob=box('Upper | '+name,(0,0,0),(width,depth,d.length),ma,DECK,bevel=.0015)
    ob.matrix_world=FRAME@Matrix.Translation((p+q)/2)@d.to_track_quat('Z','Y').to_matrix().to_4x4();return ob
for x in [-1.3,0,1.3]:beam('broad floor plate joint',at(x,-.13,H+.001),at(x,5.06,H+.001),.008,.004,dark)
for y in [1.10,2.40,3.70]:beam('broad floor plate joint',at(-2.6,y,H+.001),at(2.6,y,H+.001),.008,.004,dark)
beam('balcony continuous face girder',at(-2.6,-.13,H-.15),at(2.6,-.13,H-.15),.21,.16,steel)
beam('balcony machined edge',at(-2.6,-.175,H-.008),at(2.6,-.175,H-.008),.027,.035,trim)
# One welded mitered U-profile instead of independent beams with free ends.
def profile(name,outer,inner,y0,y1,ma):
    n=len(outer);verts=[tuple(at(x,y,z)) for y in [y0,y1] for loop in [outer,inner] for x,z in loop];faces=[]
    for i in range(n-1):
        faces.extend([(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)])
    faces.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)])
    return mesh(name,verts,faces,ma,DECK,.0015)
outer=[(-2.615,H),(-2.615,H+2.085),(-1.845,H+3.035),(1.805,H+3.035),(2.615,H+2.085),(2.615,H)]
inner=[(-2.49,H),(-2.49,H+2.04),(-1.785,H+2.91),(1.745,H+2.91),(2.49,H+2.04),(2.49,H)]
portal=profile('Upper | continuous mitered entrance frame',outer,inner,.63,.77,steel)
# Front rails return all the way into the portal legs, with shared corner posts.
path=[(-2.52,.68),(-2.52,-.09),(2.52,-.09),(2.52,.68)]
for aa,bb in zip(path,path[1:]):
    for zz,ww in [(H+.21,.020),(H+.45,.029),(H+.035,.026)]:beam('connected guardrail',at(*aa,zz),at(*bb,zz),ww,ww,dark)
postpoints=[]
for aa,bb in zip(path,path[1:]):
    aa,bb=Vector(aa),Vector(bb);count=max(1,math.ceil((bb-aa).length/.53))
    for j in range(count):postpoints.append(aa.lerp(bb,j/count))
postpoints.append(Vector(path[-1]))
for p in postpoints:
    beam('guard upright',at(*p,H),at(*p,H+.47),.036,.036,steel)
    box('Upper | post foot',at(*p,H+.014),(.075,.075,.028),dark,DECK,angle,.002)
for x in [-2.52,2.52]:
    for zz in [H+.21,H+.45]:box('Upper | rail end connection',at(x,.69,zz),(.075,.075,.07),steel,DECK,angle,.002)
# Single ceiling luminaire, seated against the actual ceiling reveal.
box('Upper | overhead luminaire housing',at(0,2.05,H+2.97),(1.82,.30,.105),dark,DECK,angle,.008)
box('Upper | overhead diffuser',at(0,2.05,H+2.91),(1.62,.21,.015),white,DECK,angle,.003)
ld=bpy.data.lights.new('Upper | sole ceiling practical','AREA');ld.energy=260;ld.shape='RECTANGLE';ld.size=1.60;ld.size_y=.22;ld.color=(.63,.80,1.)
lo=bpy.data.objects.new(ld.name,ld);RIG.objects.link(lo);lo.location=FRAME@at(0,2.05,H+2.88);lo.rotation_euler=(FRAME@at(0,2.10,H)-lo.location).to_track_quat('-Z','Y').to_euler()
for ob in list(TEMP.objects):bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.collections.remove(TEMP)
# True different viewpoints, including both ends of the railing and a low view.
def camera(name,pos,target,lens):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));RIG.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;ob.data.clip_end=150;return ob
hero=bpy.data.objects['Interior | overview']
front=camera('Upper | front inspection',at(0,-3.8,H+2.50),at(0,1.8,H+1.20),24)
left=camera('Upper | left oblique inspection',at(-4.7,-3.6,H+2.25),at(0,2.,H+1.2),28)
right=camera('Upper | right oblique inspection',at(2.3,-1.1,H+1.90),at(-.3,2.4,H+1.1),20)
S.camera=hero;S.render.engine='CYCLES';S.cycles.samples=64 if a.final else 24;S.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG';S.render.resolution_percentage=100
for name in ['build_upper_recess.py']:
    tx=bpy.data.texts.new(name);tx.write((P/name).read_text())
changed=[n for n,h in protected.items() if n not in removed and n not in changed_rock and (n not in S.objects or fingerprint(S.objects[n])!=h)]
assert not changed,changed
report={'source':str(SOURCE),'unchanged_original_meshes':len(protected)-len(set(removed)&set(protected))-len(changed_rock),'unexpected_changes':changed,'removed_upper_objects':removed,'upper_rock_objects':changed_rock,'rock_edit_min_z':JOIN,'upper_origin':list(origin),'floor_z':H,'aperture':section,'bay_angle_degrees':-22.5,'bay_x_scale':1.1,'deck_width':5.72,'deck_depth':5.22,'recess_depth':5.1,'shift_from_original_front_center':[1.1269,.7737],'upper_props':[],'upper_light_count':1,'arch_frame_single_connected_mesh':portal.name}
S['clean_upper_bay']=json.dumps(report);(P/'upper-recess-preservation.json').write_text(json.dumps(report,indent=2))
tag='upper-recess' if a.final else 'preview-upper-recess';out=P/(tag+'.blend')
S.render.resolution_x=2000 if a.final else 1400;S.render.resolution_y=round(S.render.resolution_x*.6);S.render.filepath=str(P/(tag+'-overview.png'));bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
for cam,suffix in [(hero,'overview'),(front,'front'),(left,'left'),(right,'right')]:
    S.camera=cam;S.render.resolution_x=(2000 if a.final else 1400) if cam==hero else (1600 if a.final else 1200);S.render.resolution_y=round(S.render.resolution_x*(.6 if cam==hero else .75));S.render.filepath=str(P/(tag+'-'+suffix+'.png'));bpy.ops.render.render(write_still=True)
S.camera=hero;S.render.resolution_x=2000 if a.final else 1400;S.render.resolution_y=round(S.render.resolution_x*.6);S.render.filepath=str(P/(tag+'-overview.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True);print('UPPER_RECESS_COMPLETE',flush=True)
