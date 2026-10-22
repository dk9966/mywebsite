"""Isolate the approved central pillar and replace the tiled deck with machined metal."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'mound-study/central-platform-rock-mound-balanced.blend'
OUTPUT = P / 'central-metal-platform.blend'
ap = argparse.ArgumentParser()
ap.add_argument('--final', action='store_true')
ap.add_argument('--verify', action='store_true')
ap.add_argument('--pass', dest='stage', type=int, default=1)
ap.add_argument('--samples', type=int, default=32)
a = ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
bpy.context.window.scene = bpy.data.scenes['01 Central mound - platform close-up']
bpy.context.view_layer.update()

def fingerprint(o):
    h = hashlib.sha256(np.array(o.matrix_world, dtype=np.float64).tobytes())
    for prop, key, count, dtype in [('vertices','co',3,np.float32), ('loops','vertex_index',1,np.int32), ('polygons','material_index',1,np.int32)]:
        data = getattr(o.data, prop)
        arr = np.empty(len(data)*count, dtype=dtype)
        data.foreach_get(key,arr)
        h.update(arr.tobytes())
    for m in o.data.materials:
        for n in m.node_tree.nodes:
            for socket in n.inputs:
                if hasattr(socket,'default_value'):
                    val = socket.default_value
                    try: val = list(val)
                    except TypeError: val = str(val)
                    h.update(str((n.name,socket.identifier,val)).encode())
    return h.hexdigest()

kept = [o for o in bpy.data.collections['deck_project'].objects if o.type=='MESH' and o.name.startswith('deck_desk')]
rock = bpy.data.objects['Central rock mound | continuous cross-column extrusions']
kept.append(rock)
protected = {o.name: fingerprint(o) for o in kept}
if a.verify:
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
    bpy.context.view_layer.update()
    changed = [n for n,h in protected.items() if n not in bpy.context.scene.objects or fingerprint(bpy.data.objects[n])!=h]
    unexpected = [o.name for o in bpy.context.scene.objects if not (o.name in protected or o.name.startswith('Metal |'))]
    report = {'passed': not changed and not unexpected and len(bpy.data.scenes)==1,
              'preserved_rock_and_console_meshes': len(protected), 'changed':changed,
              'unexpected_objects':unexpected, 'scenes':[s.name for s in bpy.data.scenes],
              'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}
    (P/'preservation.json').write_text(json.dumps(report,indent=2))
    print('METAL_VERIFY',json.dumps(report),flush=True)
    assert report['passed']
    sys.exit(0)

cx,cy=21.299999237,0
F=6.871178627
FRAME=Matrix.Translation((cx,cy,0)) @ Matrix.Rotation(-math.atan2(12,19),4,'Z')
S=bpy.data.scenes.new('Central pillar | machined metal platform')
bpy.context.window.scene=S
def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
KEEP=collection('01 | Approved rock and original console')
DECK=collection('02 | Machined rings and eight recessed grates')
RAIL=collection('03 | Steel perimeter and warm inset lamps')
RIG=collection('04 | Presentation cameras and studio lights')
for o in kept:
    mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw
    KEEP.objects.link(o);o.hide_render=False;o.hide_viewport=False
for o in list(bpy.data.objects):
    if o not in kept:bpy.data.objects.remove(o,do_unlink=True)
for scene in list(bpy.data.scenes):
    if scene!=S:bpy.data.scenes.remove(scene)
for c in list(bpy.data.collections):
    if c not in [KEEP,DECK,RAIL,RIG]:bpy.data.collections.remove(c)
for t in list(bpy.data.texts):bpy.data.texts.remove(t)
bpy.context.view_layer.update()
assert protected=={o.name:fingerprint(o) for o in kept}

def material(name,color,metallic,rough,texture=False):
    m=bpy.data.materials.new('Metal | '+name);m.use_nodes=True
    nt=m.node_tree;p=nt.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=rough
    if texture:
        coord=nt.nodes.new('ShaderNodeTexCoord')
        noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=16;noise.inputs['Detail'].default_value=2
        nt.links.new(coord.outputs['Object'],noise.inputs['Vector'])
        ramp=nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[0].color=(*(v*.95 for v in color),1)
        ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(*(v*1.05 for v in color),1)
        nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],p.inputs['Base Color'])
        roughness=nt.nodes.new('ShaderNodeMapRange');roughness.inputs['To Min'].default_value=rough-.014;roughness.inputs['To Max'].default_value=rough+.018
        nt.links.new(noise.outputs['Fac'],roughness.inputs['Value']);nt.links.new(roughness.outputs[0],p.inputs['Roughness'])
        grain=nt.nodes.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=155;grain.inputs['Detail'].default_value=2
        nt.links.new(coord.outputs['Object'],grain.inputs['Vector'])
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.0012
        nt.links.new(grain.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
steel=material('satin blue steel',(.055,.071,.088),.82,.32,True)
panelsteel=material('outer walkway alloy',(.040,.052,.065),.78,.36,True)
dark=material('dark structural steel',(.019,.025,.034),.75,.42,True)
grate=material('brushed grating steel',(.019,.026,.033),.70,.46)
trim=material('machined edge highlights',(.15,.20,.25),.88,.26)
cavity=material('unlit grate recess',(.007,.010,.014),.25,.73)
warm=material('amber lamp diffusers',(.95,.54,.19),.15,.32)
wp=warm.node_tree.nodes.get('Principled BSDF');wp.inputs['Emission Color'].default_value=(1,.43,.11,1);wp.inputs['Emission Strength'].default_value=2.6

def mesh(name,verts,faces,mat,c=DECK,bevel=0):
    me=bpy.data.meshes.new('Metal | '+name);me.from_pydata(verts,[],faces);me.update();me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new('Metal | '+name,me);c.objects.link(o);o.matrix_world=FRAME
    if bevel:
        mod=o.modifiers.new('Fine machined edge','BEVEL');mod.width=bevel;mod.segments=2
        mod=o.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return o

def annulus(name,ri,ro,zlo,zhi,mat,aa=0,bb=math.tau,c=DECK,bevel=.002):
    N=max(3,math.ceil((bb-aa)/math.tau*192));vs=[];fs=[]
    for z in [zlo,zhi]:
        for r in [ri,ro]:
            vs.extend((r*math.cos(aa+(bb-aa)*i/N),r*math.sin(aa+(bb-aa)*i/N),z) for i in range(N+1))
    K=N+1
    for i in range(N):
        fs.extend([(i,i+1,K+i+1,K+i),(2*K+i,3*K+i,3*K+i+1,2*K+i+1),
                   (i,2*K+i,2*K+i+1,i+1),(K+i,K+i+1,3*K+i+1,3*K+i)])
    fs.extend([(0,K,3*K,2*K),(N,2*K+N,3*K+N,K+N)])
    return mesh(name,vs,fs,mat,c,bevel)

def box(name,p,size,mat,c=DECK,angle=0,bevel=.003):
    sx,sy,sz=size;vs=[(i*sx/2,j*sy/2,k*sz/2) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    o=mesh(name,vs,faces,mat,c,bevel);o.matrix_world=FRAME@Matrix.Translation(p)@Matrix.Rotation(angle,4,'Z');return o

def cylinder(name,p,r,depth,mat,c=DECK,axis=None,segments=12):
    vs=[(r*math.cos(i*math.tau/segments),r*math.sin(i*math.tau/segments),z) for z in [-depth/2,depth/2] for i in range(segments)]
    fs=[tuple(reversed(range(segments))),tuple(range(segments,2*segments))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    o=mesh(name,vs,fs,mat,c,.001)
    rot=axis.to_track_quat('Z','Y').to_matrix().to_4x4() if axis else Matrix.Identity(4)
    o.matrix_world=FRAME@Matrix.Translation(p)@rot;return o

def radial_box(name,r,t,z,size,mat,c=DECK,bevel=.003):
    return box(name,(r*math.cos(t),r*math.sin(t),z),size,mat,c,t,bevel)

# A continuous shallow drum replaces the old brick floor and bridge ports.
annulus('continuous support drum',.001,2.79,F-.405,F-.055,dark,bevel=.008)
annulus('lower rolled rim',2.735,2.812,F-.40,F-.36,trim,bevel=.004)
annulus('upper rolled rim',2.731,2.806,F-.051,F+.004,trim,bevel=.003)
annulus('grate recess backing',1.195,2.30,F-.108,F-.096,cavity,bevel=0)

# Broad panels, fine seams, and concentric machined trim replace masonry courses.
for i in range(4):
    aa=i*math.pi/2+.0025;bb=(i+1)*math.pi/2-.0025
    annulus('central four-part plate',.001,.751,F-.035,F,steel,aa,bb)
for ri,ro in [(.758,.794),(1.008,1.027),(1.097,1.113),(1.295,1.320),(2.256,2.289)]:
    annulus('concentric machined trim',ri,ro,F-.025,F+.002,trim)
for ri,ro in [(.801,1.000),(1.035,1.090),(1.121,1.287)]:
    for i in range(8):annulus('large concentric alloy plate',ri,ro,F-.031,F,steel,i*math.pi/4+.0019,(i+1)*math.pi/4-.0019)
for i in range(24):
    aa=i*math.tau/24+.0013;bb=(i+1)*math.tau/24-.0013
    annulus('outer walkway plate',2.300,2.723,F-.04,F,panelsteel,aa,bb)
    annulus('vertical drum service plate',2.782,2.794,F-.343,F-.063,panelsteel,aa,bb,bevel=.001)

# Actual open steel lattice: bars are clipped analytically to each annular sector.
grate_bar_count=0
for sector in range(8):
    aa=sector*math.pi/4+(.075 if sector%2 else .020)
    bb=(sector+1)*math.pi/4-(.075 if (sector+1)%2 else .020)
    angle=(aa+bb)/2;half=(bb-aa)/2
    ri,ro=1.337,2.247;vs=[];fs=[]
    def lattice_box(uc,vc,du,dv,z):
        global grate_bar_count
        k=len(vs)
        for zz in [z-.022,z]:
            for u,v in [(uc-du/2,vc-dv/2),(uc+du/2,vc-dv/2),(uc+du/2,vc+dv/2),(uc-du/2,vc+dv/2)]:
                vs.append((u*math.cos(angle)-v*math.sin(angle),u*math.sin(angle)+v*math.cos(angle),zz))
        fs.extend([tuple(k+j for j in [0,3,2,1]),tuple(k+j for j in [4,5,6,7])]+[(k+j,k+(j+1)%4,k+(j+1)%4+4,k+j+4) for j in range(4)])
        grate_bar_count+=1
    pitch=.026
    limit=math.ceil(ro*math.sin(half)/pitch)
    for j in range(-limit,limit+1):
        v=j*pitch
        if abs(v)>=ro:continue
        u0=max(math.sqrt(max(0,ri*ri-v*v)),abs(v)/math.tan(half))+.003
        u1=math.sqrt(ro*ro-v*v)-.003
        if u1-u0>.01:lattice_box((u0+u1)/2,v,u1-u0,.005,F-.008)
    for j in range(math.floor(ri*math.cos(half)/pitch),math.ceil(ro/pitch)):
        u=j*pitch
        if u>=ro:continue
        vmax=min(u*math.tan(half),math.sqrt(ro*ro-u*u))-.003
        vmin=math.sqrt(max(0,ri*ri-u*u))+.003 if u<ri else 0
        if vmax<=vmin:continue
        intervals=[(-vmax,vmax)] if vmin==0 else [(-vmax,-vmin),(vmin,vmax)]
        for lo,hi in intervals:lattice_box(u,(lo+hi)/2,.005,hi-lo,F-.012)
    mesh('recessed open grate %02d'%sector,vs,fs,grate,bevel=.0008)
    for edge in [-half,half]:
        radial_box('grate radial edge frame',(ri+ro)/2,angle+edge,F-.010,(ro-ri,.014,.022),trim)
for i in range(8):
    t=i*math.pi/4
    if i%2:annulus('broad diagonal steel wedge',1.326,2.252,F-.030,F,steel,t-.070,t+.070)
    else:radial_box('narrow cardinal structural spoke',1.787,t,F-.015,(.930,.065,.030),steel)
    for r in [1.38,2.20]:
        for dt in [-.020,.020]:
            p=Vector((r*math.cos(t)-dt*math.sin(t),r*math.sin(t)+dt*math.cos(t),F+.003))
            cylinder('spoke countersunk fastener',p,.012,.006,dark)
for r,count in [(1.25,16),(2.33,32),(2.67,32)]:
    for i in range(count):
        t=i*math.tau/count
        cylinder('flush deck fastener',(r*math.cos(t),r*math.sin(t),F+.002),.010,.005,dark)

# Continuous two-rail steel fence with inset amber lamps every fourth post.
for height in [.235,.427]:
    annulus('continuous steel guardrail',2.712,2.741,F+height-.011,F+height+.011,dark,c=RAIL,bevel=.004)
    annulus('guardrail polished top edge',2.714,2.739,F+height+.008,F+height+.011,trim,c=RAIL,bevel=.001)
for i in range(32):
    t=i*math.tau/32;r=2.731
    lamp=i%4==0
    radial_box('perimeter post',r,t,F+.217,(.061,.055,.445),dark,RAIL)
    radial_box('post bolted foot',r,t,F+.011,(.145,.110,.022),dark,RAIL)
    if i%2==0:
        radial_box('outer rim reinforcement strap',2.799,t,F-.178,(.032,.087,.405),dark,RAIL)
        for zz in [F-.330,F-.059]:cylinder('rim strap bolt',(2.819*math.cos(t),2.819*math.sin(t),zz),.012,.009,trim,RAIL,Vector((math.cos(t),math.sin(t),0)))
    if lamp:
        radial_box('warm lamp armor',r,t,F+.244,(.105,.102,.48),dark,RAIL,.006)
        radial_box('lamp cap',r,t,F+.493,(.126,.120,.028),trim,RAIL)
        for rr in [r-.055,r+.055]:
            for z in [F+.149,F+.341]:radial_box('inset amber diffuser',rr,t,z,(.008,.054,.131),warm,RAIL,.002)
        data=bpy.data.lights.new('Metal | amber floor pool','POINT');data.energy=5;data.color=(1,.43,.15);data.shadow_soft_size=.075
        obj=bpy.data.objects.new(data.name,data);RIG.objects.link(obj);obj.location=FRAME@Vector(((r-.13)*math.cos(t),(r-.13)*math.sin(t),F+.24))

def area(name,pos,target,power,color,size,size_y=None):
    d=bpy.data.lights.new('Metal | '+name,'AREA');d.energy=power;d.color=color
    d.shape='RECTANGLE';d.size=size;d.size_y=size_y or size
    o=bpy.data.objects.new(d.name,d);RIG.objects.link(o);o.location=FRAME@Vector(pos)
    o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('soft overhead steel reflection',(-3,-4,12.8),(0,0,F),650,(.74,.84,1),4.5,5)
area('long back edge reflection',(0,3,11.5),(0,0,F),850,(.54,.70,1),4.5,2)
area('broad rock fill',(4,-6,3.4),(0,0,3.0),600,(.63,.72,.87),6)
area('left rock key',(-5,-4,5.0),(0,0,3.5),650,(.70,.79,.94),5)
area('soft console fill',(1,-5,10),(0,1,7.4),140,(.70,.83,1),4)
S.world=bpy.data.worlds.new('Metal | charcoal studio');S.world.use_nodes=True
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.022,.029,.038,1)
S.world.node_tree.nodes['Background'].inputs[1].default_value=.25

def camera(name,pos,target,scale):
    d=bpy.data.cameras.new('Metal | '+name);o=bpy.data.objects.new(d.name,d);RIG.objects.link(o)
    o.location=FRAME@Vector(pos);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO';d.ortho_scale=scale;return o
hero=camera('pillar hero camera',(0,-18,12.4),(0,0,3.6),10.95)
detail=camera('deck detail camera',(0,-10,14.8),(0,0,F+.37),7.1)
S.render.engine='CYCLES';S.cycles.device='CPU';S.cycles.samples=a.samples;S.cycles.use_denoising=True;S.cycles.max_bounces=8
S.render.image_settings.file_format='PNG';S.render.resolution_percentage=100
S.render.film_transparent=False;S.render.use_compositing=False
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=-.15
S['design']='Only the original approved central rock and console, with a machined-metal deck; no surrounding scene or bridge stubs.'
S['reference_floor']='Eight open grates, broad concentric metal plates, continuous steel rail, eight warm inset lamps.'
tag='metal' if a.final else 'preview-%02d'%a.stage
out=OUTPUT if a.final else P/(tag+'.blend')
source=bpy.data.texts.new('build_metal_platform.py');source.write(Path(__file__).read_text())
S.camera=hero;S.render.resolution_x=1500 if a.final else 1000;S.render.resolution_y=1740 if a.final else 1160
S.render.filepath=str(P/(tag+'-hero.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
bpy.ops.render.render(write_still=True)
S.camera=detail;S.render.resolution_x=1800 if a.final else 1300;S.render.resolution_y=1400 if a.final else 1011
S.render.filepath=str(P/(tag+'-deck.png'));bpy.ops.render.render(write_still=True)
S.camera=hero;S.render.resolution_x=1500 if a.final else 1000;S.render.resolution_y=1740 if a.final else 1160
S.render.filepath=str(P/(tag+'-hero.png'))
bpy.context.view_layer.update()
assert protected=={o.name:fingerprint(o) for o in kept}
assert len(bpy.data.scenes)==1
assert not [o for o in S.objects if not(o in kept or o.name.startswith('Metal |'))]
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
audit={'source':str(SOURCE),'output':str(out),'preserved':protected,'scene_count':len(bpy.data.scenes),'remaining_bridge_objects':0,'other_islands':0,'rock_unchanged':True,'console_unchanged':True,'grate_sectors':8,'physical_grate_bars':grate_bar_count,'lamp_count':8,'floor_height':F}
(P/(tag+'-audit.json')).write_text(json.dumps(audit,indent=2))
print('METAL_RESULT',json.dumps(audit),flush=True)
