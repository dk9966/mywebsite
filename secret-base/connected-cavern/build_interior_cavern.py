"""Single interior-facing rock surface; original scene geometry stays exact.

No solid shell, outside skin, remesh, smoothing, or Boolean union is used.
The approved rock/materials are loaded directly from the pre-enclosure file.
Only the missing inside walls and upper-bay finish details are added.
"""
import argparse,ast,hashlib,importlib.util,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
SOURCE=P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend'
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.name='Cave interior | original terrain and refined upper bay'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.871178627
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH'}
upper_mouth_changed=[]
def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
GEO=collection('13 | Interior wall surface only');DETAIL=collection('14 | Upper bay finish');RIG=collection('15 | Interior views and supplementary light');DECK=DETAIL
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','box','cylinder'}],type_ignores=[]),'metal_helpers','exec'),globals())
steel=bpy.data.materials['Metal | satin blue steel'];panel=bpy.data.materials['Metal | outer walkway alloy'];dark=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Metal | machined edge highlights'];warm=bpy.data.materials['Metal | amber lamp diffusers'];white=bpy.data.materials['Bays | cool strip light'];cyan=bpy.data.materials['Bays | control tower glass'];wallmat=bpy.data.materials['Bays | inset steel wall']
def beam(name,p,q,width,depth,ma):
    p,q=Vector(p),Vector(q);v=q-p
    ob=box('Upper finish | '+name,(0,0,0),(width,depth,v.length),ma,DETAIL,bevel=.003)
    ob.matrix_world=FRAME@Matrix.Translation((p+q)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return ob
def area(name,pos,target,power,size=2,size_y=1,color=(.59,.73,.88)):
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='RECTANGLE';ld.size=size;ld.size_y=size_y;ld.color=color
    ob=bpy.data.objects.new(name,ld);RIG.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();return ob
def camera(name,pos,target,lens=24,ortho=None):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));RIG.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;ob.data.sensor_width=36;ob.data.clip_end=200
    if ortho:ob.data.type='ORTHO';ob.data.ortho_scale=ortho
    return ob

# Reuse the original cross-column step-wall topology, retaining only its inside
# faces. The outer dummy radius is discarded before a Blender mesh is created.
spec=importlib.util.spec_from_file_location('pillar_field',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)
rng=np.random.default_rng(76183);N=192;M=64;theta=np.linspace(0,math.tau,N+1);zv=np.linspace(-6.15,16.8,M+1);zv[1:-1]+=rng.uniform(-.06,.06,M-1)
sites=[]
for row in range(-1,10):
    for col in range(15):sites.append((col*N/15+rng.uniform(-3,3),row*M/9+rng.uniform(-2,2),rng.uniform(.04,.35)))
ii=np.arange(N)[:,None];jj=np.arange(M)[None,:];dist=np.full((N,M),1e12);relief=np.zeros((N,M))
for x,y,depth in sites:
    dx=np.minimum(np.abs(ii-x)%N,N-np.abs(ii-x)%N);d=(dx/9)**2+((jj-y)/5.3)**2;sel=d<dist;relief[sel]=depth;dist[sel]=d[sel]
inner=6-np.round(relief/.065)*.065
# Broad, staggered planes instead of small repeated tiles or rounded lobes.
for center,width,low,high,depth in [(137,26,-4,1.2,.30),(161,24,.8,4.9,.34),(177,26,4.7,7.4,.30),(187,25,9.0,14.4,.34),(207,26,-2,3.6,.38),(230,30,7.2,11.8,.35),(110,25,11.5,15.7,.38),(88,31,-2.5,2.2,.31),(76,23,2.,7.,.30),(267,34,-3,2.5,.30),(279,25,7,12,.38),(94,24,7.2,11.,.40),(76,19,10.2,13.6,.36)]:
    for i in range(N):
        dx=abs((math.degrees(theta[i])+180-center)%360-180)
        if dx>width/2:continue
        for j in range(M):
            if low+(dx>width*.31)*.30<zv[j]<high-(dx>width*.35)*.40:inner[i,j]-=depth
# Faceted recesses have discrete ledges and angled shoulders, not a smoothed
# radial displacement. They are part of the same zero-thickness surface.
for center,halfwidth,floor,roof,depth in [(159,27,7.4,12.5,1.28),(210,23,2.5,6.9,1.42),(110,21,7.1,12.0,.92)]:
    for i in range(N):
        dx=abs((math.degrees(theta[i])+180-center)%360-180)
        for j in range(M):
            z=(zv[j]+zv[j+1])/2
            w=halfwidth-(4 if z>roof-.7 else 0)
            if floor<z<roof and dx<w:
                inner[i,j]+=depth*(1 if dx<w*.72 else .60)
outer=np.full((N,M),20.)
active=(theta[:-1]>=math.radians(45))&(theta[:-1]<=math.radians(333))
inner[~active,:]=0;outer[~active,:]=0
# Resolve diagonally touching height-field corners, preserving wide ledges.
for _ in range(12):
    fixes=0
    for i in range(N):
        k=(i+1)%N
        if not active[i] or not active[k]:continue
        for j in range(M-1):
            aa,bb,cc,dd=inner[i,j],inner[k,j],inner[i,j+1],inner[k,j+1]
            if min(aa,dd)>max(bb,cc)+1e-7:
                if bb>=cc:inner[k,j]=min(aa,dd)
                else:inner[i,j+1]=min(aa,dd)
                fixes+=1
            elif min(bb,cc)>max(aa,dd)+1e-7:
                if aa>=dd:inner[i,j]=min(bb,cc)
                else:inner[k,j+1]=min(bb,cc)
                fixes+=1
    if not fixes:break
tri,raw=shape.mesh_field(theta,zv,np.ones(M+1),inner,outer).arrays()
rad=np.hypot(raw[:,0],raw[:,2]);inside=np.all(rad[tri]<10.,axis=1)
caps=(np.all(abs(raw[tri,1]-zv[0])<1e-7,axis=1)|np.all(abs(raw[tri,1]-zv[-1])<1e-7,axis=1))
tri=tri[inside&~caps];used=np.unique(tri);remap=np.full(len(raw),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];raw=raw[used]
stations=[(0,13),(36,18),(45,17),(55,15.8),(65,12.2),(74,8.8),(86,7.6),(99,8.1),(115,8.5),(131,7.3),(144,6.1),(157,5.4),(174,4.95),(190,5.45),(203,7.1),(218,9.0),(234,11.0),(252,12.4),(270,12.55),(287,12.4),(307,11.8),(320,11.0),(334,10.8),(350,12.5)]
ang=np.radians([d for d,r in stations]);rr=np.array([r for d,r in stations]);poly=np.column_stack((np.cos(ang)*rr,np.sin(ang)*rr))
def plan_radius(t):
    direction=np.array((math.cos(t),math.sin(t)));hits=[]
    for p,q in zip(poly,np.roll(poly,-1,axis=0)):
        e=q-p;den=direction[0]*e[1]-direction[1]*e[0]
        if abs(den)<1e-9:continue
        u=(p[0]*direction[1]-p[1]*direction[0])/den;r=(p[0]*e[1]-p[1]*e[0])/den
        if r>0 and -1e-6<=u<=1.000001:hits.append(r)
    return min(hits)
verts=[]
for x,z,y in raw:
    t=math.atan2(y,x);h=(z-zv[0])/(zv[-1]-zv[0]);r=plan_radius(t)+math.hypot(x,y)-6
    # Upright faceted contour with a broken top; no global smoothing operation.
    z+=max(0.,h)**6*(.45*math.sin(t*5)-1.0*max(0.,-math.sin(t)))
    verts.append((r*math.cos(t),r*math.sin(t),z))
me=bpy.data.meshes.new('Interior only | sharp cross-column wall surface');me.from_pydata(verts,[],tri.tolist());me.update()
rockmat=bpy.data.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0];me.materials.append(rockmat)
wall=bpy.data.objects.new('Cave | single interior wall surface',me);GEO.objects.link(wall);wall.matrix_world=FRAME
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.dissolve_limit(bm,angle_limit=.00005,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'});bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=False
wall['surface_only']=True;wall['thickness']=0.;wall['source_mesher']='meshes/pillars/island_pillar_src/shape.py::mesh_field';wall['no_exterior_or_caps']=True
print('INTERIOR_SURFACE',len(me.vertices),len(me.polygons),flush=True)

# Upper-right finishing is additive: architecture, rock and their materials
# remain exactly as they were. Match the central platform's metal vocabulary.
audit=json.loads((P.parent/'right-cave-bays/right-bays-audit.json').read_text());hp=[Vector(p) for p in audit['upper_floor_polygon']];H=audit['upper_floor_height'];u=(hp[1]-hp[0]).normalized();v=Vector((-u.y,u.x));origin=(hp[0]+hp[1])/2;width=(hp[1]-hp[0]).length;angle=math.atan2(u.y,u.x)
def at(x,y,z):return Vector((origin.x+u.x*x+v.x*y,origin.y+u.y*x+v.y*y,z))
normal=Vector((-v.x,-v.y,0))
# A local cut removes the old thin hanging blade across the upper entrance.
# This is the sole permitted edit to existing rock; the remainder is untouched.
section=[(-2.10,H+.50),(-2.10,H+1.45),(-.75,H+2.20),(.20,H+2.60),(.35,H+2.60),(.35,H+.50)]
mouth_depth=[-4.,5.9]
cv=[tuple(at(x,y,z)) for y in mouth_depth for x,z in section];nn=len(section)
cf=[tuple(reversed(range(nn))),tuple(range(nn,2*nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
cut=mesh('Upper finish | temporary mouth clearance',cv,cf,dark,DETAIL,0)
for rock in bpy.data.collections['07 | Continuous approved-style cave wall'].objects:
    if not any(name in rock.name for name in ['continuous cave wall','left broken cave return']):continue
    before=fingerprint(rock);mod=rock.modifiers.new('Upper entrance blade cleanup only','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.context.view_layer.objects.active=rock;bpy.ops.object.modifier_apply(modifier=mod.name)
    if fingerprint(rock)!=before:upper_mouth_changed.append(rock.name)
bpy.data.objects.remove(cut,do_unlink=True)
# A layered, bolted balcony fascia and three inset warm lamps.
box('Upper finish | balcony fascia',at(0,-.035,H-.18),(width,.10,.23),steel,DETAIL,angle,.004)
for z in [H-.07,H-.28]:beam('balcony edge trim',at(-width/2,-.095,z),at(width/2,-.095,z),.017,.021,trim)
for j in range(9):
    x=-width/2+width*j/8;p=at(x,-.10,H-.18)
    box('Upper finish | fascia strap',p,(.08,.026,.27),dark,DETAIL,angle,.003)
    for dz in [-.09,.09]:cylinder('Upper finish | fascia bolt',p+normal*.020+Vector((0,0,dz)),.013,.010,trim,DETAIL,normal,6)
for t in [.08,.50,.92]:
    x=-width/2+t*width;p=at(x,-.017,H)
    box('Upper finish | lamp armor',p+Vector((0,0,.265)),(.115,.12,.53),dark,DETAIL,angle,.006)
    for z in [.17,.36]:box('Upper finish | warm inset lens',at(x,-.084,H+z),(.065,.018,.12),warm,DETAIL,angle,.002)
    box('Upper finish | lamp cap',p+Vector((0,0,.545)),(.15,.15,.035),trim,DETAIL,angle,.003)
    area('Upper | warm balcony pool',at(x,-.05,H+.52),at(x,.6,H),7,.30,.24,(1.,.58,.26))
# Add a neat metal face and short integrated lights to the existing portal.
arches=[o for o in bpy.data.collections['06 | Upper recessed aircraft hangar'].objects if 'embedded polygonal arch rib' in o.name]
arches.sort(key=lambda ob:ob.name)
for index,ob in enumerate(arches[:16]):
    T=INV@ob.matrix_world;low=min(v.co.z for v in ob.data.vertices);high=max(v.co.z for v in ob.data.vertices)
    p=T@Vector((0,0,low));q=T@Vector((0,0,high));shift=normal*(.05 if index<8 else .035)
    beam('portal brushed steel face',p+shift,q+shift,.090 if index<8 else .055,.028,steel)
    if index<8:
        for f in [.08,.92]:cylinder('Upper finish | portal fixing',p.lerp(q,f)+shift+normal*.022,.012,.012,trim,DETAIL,normal,6)
        if index in [1,3,5,7]:beam('short recessed portal light',p.lerp(q,.22)+shift+normal*.022,p.lerp(q,.73)+shift+normal*.022,.017,.012,white)
# Window mullions and restrained equipment detail make the control booth read
# as a finished station rather than a plain blue block.
tower=at(-width/2+.40,1.0,H)
for z in [H+.95,H+1.30]:
    center=Vector((tower.x,tower.y-.405,z))
    for dx in [-.322,0,.322]:box('Upper finish | booth mullion',center+Vector((u.x*dx,u.y*dx,0)),(.020,.026,.255),dark,DETAIL,angle,.001)
    for dz in [-.128,.128]:box('Upper finish | booth window frame',center+Vector((0,0,dz)),(.665,.026,.021),trim,DETAIL,angle,.001)
for x in [-.22,-.12,-.02,.08,.18]:box('Upper finish | booth vent',Vector((tower.x+u.x*x,tower.y-.410+u.y*x,H+.62)),(.045,.021,.095),dark,DETAIL,angle,.001)
box('Upper finish | booth header light',Vector((tower.x,tower.y-.432,H+1.49)),(.40,.016,.025),white,DETAIL,angle,.001)
# A small bank of inset service cabinets along the existing rear wall.
rear_u=(hp[2]-hp[3]).normalized();rear_v=Vector((-rear_u.y,rear_u.x));rear_angle=math.atan2(rear_u.y,rear_u.x)
for j,t in enumerate([.27,.50,.73]):
    c=hp[3].lerp(hp[2],t)-rear_v*.23
    box('Upper finish | rear service cabinet',(*c,H+.53),(.70,.31,1.06),wallmat,DETAIL,rear_angle,.006)
    front=c-rear_v*.168
    box('Upper finish | rear cabinet face',(*front,H+.55),(.62,.035,.89),panel,DETAIL,rear_angle,.003)
    for zz in [.21,.36,.51]:box('Upper finish | cabinet recessed seam',(*(front-rear_v*.022),H+zz),(.55,.012,.016),dark,DETAIL,rear_angle,.001)
    box('Upper finish | cabinet status glass',(*(front-rear_v*.024),H+.88),(.30,.014,.085),cyan,DETAIL,rear_angle,.001)
    for k in range(3):box('Upper finish | status readout',(*(front+rear_u*(-.10+k*.10)-rear_v*.034),H+.89),(.025,.010,.032),white,DETAIL,rear_angle,.001)
# Grazing local light brings out portal depth without retuning old materials.
area('Upper | portal soft reveal',at(.7,1.7,H+2.35),at(1.1,5.8,H+.25),180,2.2,.65)
area('Upper | rear wall bounce',(*((hp[2]+hp[3])/2-rear_v*1.5),H+2.1),(*((hp[2]+hp[3])/2),H+.75),110,2.5,.55)
area('Interior | left restrained bounce',(-2,-3,11),(-6,1,8),180,3,4)
area('Interior | rear grazing fill',(1,2,12),(-2,7,8),160,2,3)

hero=camera('Interior | overview',(.35,-11.45,11.65),(1.6,.8,7.5),20.5);hero.data.shift_y=.015
reverse=camera('Interior | reverse',(-.6,5.5,10.4),(.3,-2.2,6.8),19)
plan=camera('Interior | single surface inspection',(2,1,42),(2,1,6),ortho=34);plan.matrix_world=FRAME@Matrix.Translation((2,1,42))
S.camera=hero
for ob in S.objects:
    if 'Atmosphere' in ob.name:ob.hide_set(True);ob.display_type='WIRE'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.render.engine='CYCLES';S.cycles.samples=64 if a.final else 24;S.cycles.use_denoising=True;S.render.resolution_x=2000 if a.final else 1400;S.render.resolution_y=round(S.render.resolution_x*.60);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.overlay.show_extras=False
bpy.ops.object.select_all(action='DESELECT')
for name in ['build_interior_cavern.py']:
    if name in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts[name])
    tx=bpy.data.texts.new(name);tx.write((P/name).read_text())
changed=[n for n,h in protected.items() if n not in upper_mouth_changed and (n not in S.objects or fingerprint(S.objects[n])!=h)]
assert not changed,changed
bm=bmesh.new();bm.from_mesh(me);boundary=sum(e.is_boundary for e in bm.edges);bad=sum(not e.is_manifold and not e.is_boundary for e in bm.edges);bm.free()
report={'source':str(SOURCE),'protected_meshes':len(protected)-len(upper_mouth_changed),'unexpected_changed_meshes_or_materials':changed,'new_wall_vertices':len(me.vertices),'new_wall_polygons':len(me.polygons),'new_wall_thickness':0,'new_wall_modifiers':len(wall.modifiers),'boundary_edges_expected_for_open_surface':boundary,'nonmanifold_nonboundary_edges':bad,'original_rock_restored_except_local_upper_entrance_cut':True,'upper_mouth_rock_objects':upper_mouth_changed,'upper_mouth_cut_section':section,'upper_mouth_cut_depth':mouth_depth,'new_exterior_shell':False,'upper_bay_changes':'Local removal of the hanging entrance blade, plus brushed-metal portal faces, short inset lights, balcony fascia and warm lamps, booth mullions, and rear service cabinets.'}
(P/'interior-preservation.json').write_text(json.dumps(report,indent=2));print('PRESERVATION',json.dumps(report),flush=True)
tag='interior' if a.final else 'preview-interior';output=P/('connected-cavern.blend' if a.final else 'preview-interior.blend')
S.render.filepath=str(P/(tag+'-overview.png'));bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True);bpy.ops.render.render(write_still=True)
old=(S.render.resolution_x,S.render.resolution_y)
S.render.resolution_x=3600 if a.final else 2600;S.render.resolution_y=round(S.render.resolution_x*.60);S.render.use_border=True;S.render.use_crop_to_border=True;S.render.border_min_x=.57;S.render.border_max_x=.98;S.render.border_min_y=.47;S.render.border_max_y=.99;S.render.filepath=str(P/(tag+'-upper-bay.png'));bpy.ops.render.render(write_still=True)
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.resolution_x,S.render.resolution_y=old;S.camera=reverse;S.render.filepath=str(P/(tag+'-reverse.png'));bpy.ops.render.render(write_still=True)
S.camera=plan;S.render.engine='BLENDER_WORKBENCH';S.display.shading.light='STUDIO';S.display.shading.color_type='MATERIAL';S.display.shading.show_cavity=True;S.display.shading.cavity_type='BOTH';S.render.resolution_x=1450;S.render.resolution_y=1450
hidden=[]
for ob in S.objects:
    if 'Atmosphere' in ob.name and not ob.hide_render:hidden.append(ob);ob.hide_render=True
S.render.filepath=str(P/(tag+'-surface-plan.png'));bpy.ops.render.render(write_still=True)
for ob in hidden:ob.hide_render=False
S.camera=hero;S.render.engine='CYCLES';S.render.resolution_x,S.render.resolution_y=old;S.render.filepath=str(P/(tag+'-overview.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
print('INTERIOR_CAVERN_COMPLETE',flush=True)
