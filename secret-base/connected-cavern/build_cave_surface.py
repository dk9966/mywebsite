"""Extend the original cave with a sharp, inward-facing surface only.

No original object is remeshed, transformed, or retextured. The new geometry
has no exterior/back layer, wall thickness, top cap, bottom cap, roof or floor.
"""
import argparse,ast,hashlib,importlib.util,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
SOURCE=P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend'
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.871178627
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH'}
oldrocks=list(bpy.data.collections['07 | Continuous approved-style cave wall'].objects)
vs=[];fs=[]
for ob in oldrocks:
    off=len(vs);T=INV@ob.matrix_world;vs.extend(T@v.co for v in ob.data.vertices);fs.extend(tuple(off+i for i in p.vertices) for p in ob.data.polygons)
oldtree=BVHTree.FromPolygons(vs,fs)
GEO=bpy.data.collections.new('13 | Interior cave surface only');S.collection.children.link(GEO)
RIG=bpy.data.collections.new('14 | Interior views and wall lighting');S.collection.children.link(RIG)
module_spec=importlib.util.spec_from_file_location('pillar_field',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(shape)
rng=np.random.default_rng(76183);N=180;M=66;theta=np.linspace(0,math.tau,N+1);zv=np.linspace(-5.8,16,M+1);zv[1:-1]+=rng.uniform(-.04,.04,M-1)
ii=np.arange(N)[:,None];jj=np.arange(M)[None,:];dist=np.full((N,M),1e12);relief=np.zeros((N,M))
for row in range(-1,11):
    for col in range(13):
        x=col*N/13+rng.uniform(-3,3);y=row*M/10+rng.uniform(-2,2);depth=rng.uniform(.03,.27)
        dx=np.abs(ii-x)%N;dx=np.minimum(dx,N-dx);dd=(dx/8)**2+((jj-y)/5)**2;mask=dd<dist;relief[mask]=depth;dist[mask]=dd[mask]
relief=np.round(relief/.065)*.065
# Shallow, connected outcrops with staggered ends. These are depth steps in
# the surface, not detached bricks, and receive no smoothing or voxel pass.
for band in range(8):
    for region in range(8):
        if (band+region)%2:continue
        start=int(region*N/8+rng.integers(-5,5));width=int(rng.integers(9,20));lo=max(0,int(band*M/8+rng.integers(-2,2)));hi=min(M,lo+int(rng.integers(5,11)))
        for u in range(width):
            cap=hi-(1 if u<width*.2 or u>width*.78 else 0)
            relief[(start+u)%N,lo:cap]+=.13
inner=6-relief
for center,width,lo,hi,depth in [(148,24,-3,1.6,.35),(173,24,3.8,7.5,.35),(185,20,9.2,13.4,.42),(226,29,7,11.5,.30),(92,25,8.6,11.3,.42),(110,20,2.8,6.2,.32),(264,30,1,5.5,.30)]:
    for i in range(N):
        d=abs((math.degrees(theta[i])+180-center)%360-180)
        if d>width/2:continue
        for j in range(M):
            if lo<zv[j]<hi-(.33 if d>width*.32 else 0):inner[i,j]-=depth
# Wide planar recesses, with stepped/fractured mouths instead of rounded
# sculpted bays. Their top and side limits are deliberately unequal.
for center,halfwidth,lo,hi,depth in [(157,24,7.45,12.2,1.25),(211,22,2.5,6.8,1.40),(112,18,7.1,11.9,.95)]:
    for i in range(N):
        d=abs((math.degrees(theta[i])+180-center)%360-180)
        if d>halfwidth:continue
        top=hi-(.66 if d>halfwidth*.7 else (.33 if d>halfwidth*.45 else 0))
        for j in range(M):
            if lo<zv[j]<top:inner[i,j]+=depth
# Remove diagonal-only contacts before meshing the exposed side of the field.
for _ in range(12):
    count=0
    for i in range(N):
        k=(i+1)%N
        for j in range(M-1):
            aa,bb,cc,dd=inner[i,j],inner[k,j],inner[i,j+1],inner[k,j+1]
            if min(aa,dd)>max(bb,cc)+1e-7:
                if bb>=cc:inner[k,j]=min(aa,dd)
                else:inner[i,j+1]=min(aa,dd)
                count+=1
            elif min(bb,cc)>max(aa,dd)+1e-7:
                if aa>=dd:inner[i,j]=min(bb,cc)
                else:inner[k,j+1]=min(bb,cc)
                count+=1
    if not count:break
tris,raw=shape.mesh_field(theta,zv,np.ones(M+1),inner,np.full_like(inner,12)).arrays()
# Retain just the inward-facing panels and their connecting ledges. Discard
# the whole outer surface and all end caps before creating any Blender mesh.
radii=np.hypot(raw[:,0],raw[:,2]);used_faces=[]
for tri in tris:
    pts=raw[tri]
    if np.max(radii[tri])>9:continue
    if np.all(np.abs(pts[:,1]-zv[0])<1e-8) or np.all(np.abs(pts[:,1]-zv[-1])<1e-8):continue
    center=pts.mean(axis=0);degrees=math.degrees(math.atan2(center[2],center[0]))%360
    if 44.00001<degrees<321.99999:used_faces.append(tuple(int(i) for i in tri[::-1]))
stations=[(44,12.2),(54,12.0),(64,10.8),(74,8.7),(88,7.5),(104,8.1),(120,8.4),(134,7.0),(146,6.0),(161,5.25),(177,5.15),(190,5.65),(205,7.25),(220,9.6),(239,11.5),(258,12.6),(278,12.8),(299,11.6),(312,10.2),(322,9.2)]
poly=np.array([(r*math.cos(math.radians(d)),r*math.sin(math.radians(d))) for d,r in stations])
def plan_radius(t):
    direction=np.array([math.cos(t),math.sin(t)])
    for p,q in zip(poly,poly[1:]):
        e=q-p;den=direction[0]*e[1]-direction[1]*e[0]
        if abs(den)<1e-9:continue
        rr=(p[0]*e[1]-p[1]*e[0])/den;u=(p[0]*direction[1]-p[1]*direction[0])/den
        if rr>0 and -1e-6<=u<=1.000001:return rr
    return 12.2 if math.degrees(t)%360<50 else 9.2
def blendweight(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
cache={}
def anchor_radius(deg,z):
    key=(deg,round(z,6))
    if key not in cache:
        t=math.radians(deg);d=Vector((math.cos(t),math.sin(t),0));hit=oldtree.ray_cast(Vector((0,0,z)),d,40)
        if hit[0] is None:
            near=oldtree.find_nearest(d*(12 if deg==44 else 9)+Vector((0,0,z)))
            cache[key]=math.hypot(near[0].x,near[0].y)+.12
        else:cache[key]=hit[3]+.12
    return cache[key]
newverts=[];remap={}
for idx in sorted({i for face in used_faces for i in face}):
    x,z,y=raw[idx];t=math.atan2(y,x);deg=math.degrees(t)%360;h=(z-zv[0])/(zv[-1]-zv[0]);r=math.hypot(x,y)
    # Main strata stay planar. Only the topmost edge has irregular height.
    top_offset=.42*math.sin(t*3)+.22*math.cos(t*7)
    z+=top_offset*max(0,(h-.88)/.12)
    rear_w=1-blendweight((deg-44)/13);front_w=blendweight((deg-308)/14)
    z=z*(1-rear_w-front_w)+rear_w*(-5+h*20.55)+front_w*(-5+h*20.0)
    rr=plan_radius(t)+(r-6)
    rr=rr*(1-rear_w-front_w)+rear_w*(anchor_radius(44,z)+(r-6)*.12)+front_w*(anchor_radius(322,z)+(r-6)*.12)
    remap[idx]=len(newverts);newverts.append((rr*math.cos(t),rr*math.sin(t),z))
faces=[tuple(remap[i] for i in face) for face in used_faces]
me=bpy.data.meshes.new('Open inward-facing rock surface');me.from_pydata(newverts,[],faces);me.update()
wall=bpy.data.objects.new('Cavern | single interior rock surface',me);GEO.objects.link(wall);wall.matrix_world=FRAME
me.materials.append(bpy.data.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0])
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
score=sum(f.normal.x*f.calc_center_median().x+f.normal.y*f.calc_center_median().y for f in bm.faces if abs(f.normal.z)<.5)
if score>0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bmesh.ops.dissolve_limit(bm,angle_limit=.00001,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'})
bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=False
wall['construction']='Open inward-facing surface only; no thickness, exterior, smoothing, remesh, subdivision or solidify.'
wall['source_mesher']='meshes/pillars/island_pillar_src/shape.py::mesh_field'
wall['existing_rock']='All four original rock objects and their materials preserved exactly.'

def camera(name,pos,target,lens=20.5,ortho=None):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));RIG.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;ob.data.sensor_width=36;ob.data.clip_end=250
    if ortho:ob.data.type='ORTHO';ob.data.ortho_scale=ortho
    return ob
def area(name,pos,target,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=(.64,.73,.83);data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);RIG.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    # New fill lights illuminate only the extension. Original lights, materials
    # and presentation settings are taken verbatim from the approved scene.
    ob.light_linking.receiver_collection=GEO
area('Surface | left grazing fill',(-1,-2,13),(-5.5,2,8),240,3)
area('Surface | rear grazing fill',(2,2,12),(-1,7.5,7.5),200,3)
area('Surface | low side fill',(-1,-5,3),(-5,-1,2),105,4)
hero=camera('Surface | interior overview',(.35,-11.3,11.55),(1.6,.8,7.5),20.5)
hero.data.shift_y=.015
reverse=camera('Surface | reverse view',(-.6,5.5,10.4),(.3,-2.2,6.8),19)
plan=camera('Surface | overhead inspection',(3,2,42),(3,2,5),ortho=38);plan.matrix_world=FRAME@Matrix.Translation((3,2,42))
elevated=camera('Surface | elevated inspection',(-19,-24,33),(2,2,5),ortho=43)
S.camera=hero;S.name='Cave interior | original rock preserved'
for ob in S.objects:
    if 'Atmosphere' in ob.name:ob.hide_set(True);ob.display_type='WIRE'
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.clip_end=250;ar.spaces.active.overlay.show_extras=False
            ar.spaces.active.shading.type='SOLID';ar.spaces.active.shading.light='STUDIO';ar.spaces.active.shading.color_type='MATERIAL';ar.spaces.active.shading.show_cavity=True
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h];assert not changed,changed
for text in list(bpy.data.texts):
    if text.name.startswith(('build_connected_cavern.py','build_cave_surface.py')):bpy.data.texts.remove(text)
txt=bpy.data.texts.new('build_cave_surface.py');txt.write(Path(__file__).read_text())
bpy.ops.object.select_all(action='DESELECT');wall.select_set(True);bpy.context.view_layer.objects.active=wall
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
for d in prefs.devices:d.use=(d.type=='METAL')
S.cycles.device='GPU';S.render.engine='CYCLES';S.cycles.samples=64 if a.final else 24;S.cycles.use_denoising=True
width=2000 if a.final else 1400;S.render.resolution_x=width;S.render.resolution_y=round(width*.60);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False
prefix='cavern' if a.final else 'preview-surface';output=P/('connected-cavern.blend' if a.final else 'preview-surface.blend')
S.render.filepath=str(P/(prefix+'-overview.png'));bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True);bpy.ops.render.render(write_still=True)
S.camera=reverse;S.render.filepath=str(P/(prefix+'-reverse.png'));bpy.ops.render.render(write_still=True)
# The inspection views expose the zero-thickness extension; no cosmetic
# backing shell is created to make its exterior look solid.
S.render.engine='BLENDER_WORKBENCH';S.display.shading.light='STUDIO';S.display.shading.color_type='MATERIAL';S.display.shading.show_shadows=True;S.display.shading.show_cavity=True;S.display.shading.cavity_type='BOTH';S.display.shading.curvature_ridge_factor=1.15;S.display.shading.curvature_valley_factor=.85
S.render.resolution_x=1600;S.render.resolution_y=1250
colors={m.name:tuple(m.diffuse_color) for m in bpy.data.materials}
for m in bpy.data.materials:
    if m.name.startswith(('Metal |','Bays |')):m.diffuse_color=(.40,.44,.48,1)
for m in me.materials:m.diffuse_color=(.20,.25,.29,1)
volume=[ob for ob in S.objects if 'Atmosphere' in ob.name and not ob.hide_render]
for ob in volume:ob.hide_render=True
for cam,name in [(plan,'plan'),(elevated,'elevated')]:
    S.camera=cam;S.render.filepath=str(P/(prefix+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
for ob in volume:ob.hide_render=False
for n,c in colors.items():bpy.data.materials[n].diffuse_color=c
S.camera=hero;S.render.engine='CYCLES';S.render.resolution_x=width;S.render.resolution_y=round(width*.60);S.render.filepath=str(P/(prefix+'-overview.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
print('SURFACE_COMPLETE',json.dumps({'preserved_original_meshes':len(protected),'changed':changed,'new_surface_vertices':len(me.vertices),'new_surface_faces':len(me.polygons),'output':str(output)}),flush=True)
