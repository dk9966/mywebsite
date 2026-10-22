"""Reference composition around the unchanged approved central island.

Headless: Blender --background --factory-startup --python this.py -- --pass 1
The source Blender files are read-only inputs. All output is written here.
"""
import argparse, hashlib, json, math, random, sys
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--pass',dest='stage',type=int,default=1)
ap.add_argument('--final',action='store_true')
ap.add_argument('--samples',type=int,default=32)
ap.add_argument('--width',type=int,default=1500)
opt=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
APPROVED=ROOT/'secret-base/mound-study/central-platform-rock-mound-balanced.blend'
ASSETS=ROOT/'reference-cavern/cavern-portfolio.blend'
bpy.ops.wm.open_mainfile(filepath=str(APPROVED))
bpy.context.preferences.filepaths.save_version=0
old_scene=bpy.context.scene
cx,cy=bpy.data.objects['island_pillar_project'].matrix_world.translation.xy
F=6.87117862701416
angle=-math.atan2(12,19)
FRAME=Matrix.Translation((cx,cy,0))@Matrix.Rotation(angle,4,'Z')
INV=FRAME.inverted()
def W(p):return FRAME@Vector(p)

island=[o for o in bpy.data.collections['deck_project'].objects if not o.hide_render and o.type in {'MESH','CURVE','FONT'}]
rock=bpy.data.objects['Central rock mound | continuous cross-column extrusions']
island.append(rock)
def fingerprint(ob):
    h=hashlib.sha256()
    h.update(np.array(ob.matrix_world,dtype=np.float64).tobytes())
    if ob.type=='MESH':
        positions=np.empty(len(ob.data.vertices)*3,dtype=np.float32)
        ob.data.vertices.foreach_get('co',positions)
        h.update(positions.tobytes())
        indices=np.empty(len(ob.data.loops),dtype=np.int32)
        ob.data.loops.foreach_get('vertex_index',indices)
        h.update(indices.tobytes())
        h.update(str([(m.name if m else None) for m in ob.data.materials]).encode())
    return h.hexdigest()
protected={o.name:fingerprint(o) for o in island}
gate_names={'contact':'bridge_about_threshold_project','experiences':'bridge_about_threshold_project_contact','about':'bridge_threshold_project'}
gates={}
for role,name in gate_names.items():
    ob=bpy.data.objects.get(name)
    if ob:
        p=INV@(sum((ob.matrix_world@Vector(v) for v in ob.bound_box),Vector())/8)
        p.z=F
        gates[role]=p
assert len(gates)==3,gate_names

S=bpy.data.scenes.new('Cavern | approved island and reference composition')
bpy.context.window.scene=S
def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
CENTRAL=collection('01 | Original central island - protected')
for o in island:CENTRAL.objects.link(o)
for o in island:
    parent=o.parent
    while parent:
        if parent.name not in CENTRAL.objects:CENTRAL.objects.link(parent)
        parent=parent.parent
ARCH=collection('02 | New connecting bridges and stairs')
GEO=collection('03 | Approved rock - foundations and cavern')
LIGHT=collection('04 | Reference lighting and mist')
CAM=collection('05 | Presentation cameras')

# Reuse the already modeled antenna/dish, gallery, laboratory and workshop.
prefixes=('11','12','13','14','20','22','23','24')
with bpy.data.libraries.load(str(ASSETS),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n[:2] in prefixes]
imports={c.name[:2]:c for c in dst.collections}
placements={
    'contact':{'collections':['12','20'],'source':(-12.5,11,11.35),'target':(-7.3,3.0,8.55),'scale':.53},
    'experiences':{'collections':['11','23'],'source':(-13.7,-5,5.5),'target':(-7.6,-4.0,5.49),'scale':.54},
    'about':{'collections':['13','22'],'source':(13.75,-1.2,7.7),'target':(8.25,-2.3,5.98),'scale':.53},
    'workshop':{'collections':['14','24'],'source':(14.7,14.1,11.45),'target':(8.1,3.8,8.35),'scale':.54},
}
asset_counts={}
for role,cfg in placements.items():
    dest=collection('Platform | '+role.title())
    T=FRAME@Matrix.Translation(cfg['target'])@Matrix.Scale(cfg['scale'],4)@Matrix.Translation(-Vector(cfg['source']))
    # Library-loaded object matrices are not evaluated until the collections
    # participate in a scene. Resolve the saved transforms before detaching.
    for prefix in cfg['collections']:S.collection.children.link(imports[prefix])
    bpy.context.view_layer.update()
    objects={o for prefix in cfg['collections'] for o in imports[prefix].all_objects}
    worlds={o:o.matrix_world.copy() for o in objects}
    count=0
    for o in objects:
        if o.hide_render or o.type not in {'MESH','CURVE','FONT'}:continue
        if o.name.startswith(('Foundation |','Water |','Cavern |','Ceiling |')):continue
        if 'underframe diagonal' in o.name:continue
        if o.type=='MESH' and any(m and m.name.startswith(('ROCK |','GEOLOGY','V4 | smooth')) for m in o.data.materials):continue
        o.parent=None;o.matrix_world=T@worlds[o]
        dest.objects.link(o);o.hide_set(False)
        count+=1
    for prefix in cfg['collections']:S.collection.children.unlink(imports[prefix])
    asset_counts[role]=count

def mat(name,color,metal=.0,rough=.6,emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m
steel=mat('Layout | charcoal steel',(.033,.045,.058),.65,.52)
floor=mat('Layout | deck metal',(.065,.080,.10),.65,.43)
edge=mat('Layout | steel edges',(.11,.135,.16),.7,.40)
white=mat('Layout | cold fixture strip',(.72,.85,1),.2,.28,5)
warm=mat('Layout | warm walkway lamp',(1,.63,.30),.1,.3,4)
sign=mat('Layout | blue-white station lettering',(.32,.54,1),.1,.4,2.4)
pool=mat('Layout | luminous hologram pool',(.004,.07,.22),.0,.57,.50)
pool.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.12
for role in placements:
    for o in bpy.data.collections['Platform | '+role.title()].objects:
        if o.type=='FONT' or o.name.startswith('Holo table | luminous inset'):
            o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(sign if o.type=='FONT' else pool)
CACHE={}
def box(name,p,d,material=steel,bevel=.015,col=ARCH,rot=0):
    key=(tuple(d),material.name,bevel)
    if key not in CACHE:
        bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
        for v in bm.verts:v.co=Vector((v.co.x*d[0],v.co.y*d[1],v.co.z*d[2]))
        if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(d)*.20),segments=1,affect='EDGES')
        me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();me.materials.append(material);CACHE[key]=me
    o=bpy.data.objects.new(name,CACHE[key]);col.objects.link(o)
    o.matrix_world=FRAME@Matrix.Translation(p)@Matrix.Rotation(rot,4,'Z');return o
def beam(name,a,b,r=.025,material=steel,col=ARCH):
    a,b=Vector(a),Vector(b);v=b-a
    o=box(name,(a+b)/2,(r*2,r*2,v.length),material,.006,col)
    o.matrix_world=FRAME@Matrix.Translation((a+b)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return o
def lamp(name,p,target,power,color=(.72,.83,1),kind='AREA',size=2,cone=.75):
    d=bpy.data.lights.new(name,kind);d.energy=power;d.color=color
    if kind=='AREA':d.shape='DISK';d.size=size
    if kind=='SPOT':d.spot_size=cone;d.spot_blend=.65;d.shadow_soft_size=.10
    o=bpy.data.objects.new(name,d);LIGHT.objects.link(o);o.location=W(p);o.rotation_euler=(W(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
def fixture(name,p,target,power,cone=.8):
    box(name+' | casing',p,(.66,.35,.085),steel,.015,LIGHT)
    for dy in [-.1,.1]:box(name+' | luminous tube',(p[0],p[1]+dy,p[2]-.045),(.53,.035,.022),white,.005,LIGHT)
    for dz in [-.013,.014]:box(name+' | visible strip',(p[0],p[1]-.177,p[2]+dz),(.53,.012,.012),white,.002,LIGHT)
    lamp(name,(p[0],p[1],p[2]-.13),target,power,kind='SPOT',cone=cone)

paths=[]
def bridge(name,points,width=.86,stairs=False):
    points=[Vector(p) for p in points]
    paths.append({'name':name,'points':[list(p) for p in points],'width':width,'stairs':stairs})
    for seg,(a,b) in enumerate(zip(points[:-1],points[1:])):
        dv=b-a;flat=Vector((dv.x,dv.y,0));length=flat.length;u=flat.normalized();side=Vector((-u.y,u.x,0));rot=math.atan2(u.y,u.x)
        count=math.ceil(length/(.19 if stairs else .38))
        for i in range(count):
            q=a.lerp(b,(i+.5)/count)
            if stairs:q.z=a.z+dv.z*(i+1)/count
            panel=box(name+' | tread' if stairs else name+' | floor panel',q,((length if stairs else dv.length)/count+.01,width,.07),floor,.01,rot=rot)
            if not stairs:panel.matrix_world=FRAME@Matrix.Translation(q)@Matrix.Rotation(rot,4,'Z')@Matrix.Rotation(-math.atan2(dv.z,length),4,'Y')
            if stairs:box(name+' | tread edge',q-u*(length/count*.44)+Vector((0,0,.04)),(.025,width-.055,.012),edge,.002,rot=rot)
        for sign in [-1,1]:
            aa=a+side*width*.5*sign;bb=b+side*width*.5*sign
            beam(name+' | edge girder',aa-Vector((0,0,.12)),bb-Vector((0,0,.12)),.065)
            for z in [.10,.29,.53]:beam(name+' | handrail',aa+Vector((0,0,z)),bb+Vector((0,0,z)),.016)
            npoles=max(1,math.ceil(length/.7))
            for k in range(npoles+1):
                q=aa.lerp(bb,k/npoles)
                beam(name+' | upright',q,q+Vector((0,0,.57)),.022)
                if k%4==1:
                    box(name+' | marker',q+Vector((0,0,.50)),(.045,.045,.065),warm,.004)
            nbraces=max(1,math.ceil(length/.95))
            for k in range(nbraces):
                beam(name+' | underframe diagonal',aa.lerp(bb,k/nbraces)-Vector((0,0,.36)),aa.lerp(bb,(k+1)/nbraces)-Vector((0,0,.10)),.021)
        for k in range(max(1,int(length/.8))):
            q=a.lerp(b,k/max(1,int(length/.8)))-Vector((0,0,.16))
            beam(name+' | crossmember',q-side*width*.52,q+side*width*.52,.037)

# Existing central gate coordinates define bridge starts exactly; the deck
# railing and parapet meshes are never cut or regenerated.
bridge('Projects to Experiences',[gates['experiences'],(-3.25,-2.45,F-.43),(-4.9,-2.65,5.95)],.89)
bridge('Projects to Contact - lower span',[gates['contact'],(-4.20,1.30,F)],.87)
bridge('Contact - lower stair',[(-4.20,1.30,F),(-4.20,2.20,7.75)],.87,True)
bridge('Contact - switchback landing',[(-4.20,2.20,7.75),(-4.72,2.20,7.75)],.87)
bridge('Contact - upper stair',[(-4.72,2.20,7.75),(-5.32,3.35,8.60)],.87,True)
bridge('Projects to About',[gates['about'],(4.0,-.8,6.63),(5.60,-2.0,6.02)],.95)
bridge('Workshop - rear gallery',[(-1.0,5.35,8.40),(-.45,4.80,8.40),(0,4.30,8.40),(3.1,4.30,8.40),(5.50,4.30,8.42)],.75)
box('Workshop | rear landing',(0,4.3,8.32),(.95,.88,.14),floor)
bridge('About - descending stair',[(10.55,-3.6,6.04),(10.55,-6.30,4.05)],.90,True)
bridge('About - lower exit',[(10.55,-6.30,4.05),(7.1,-9.3,2.1)],1.10)

# All new geological masses use the approved evaluated rock surface/material.
# Its local axis stays straight; only footprint, height and orientation vary.
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
ev=rock.evaluated_get(dg)
stone_mesh=bpy.data.meshes.new_from_object(ev,depsgraph=dg)
coords=[rock.matrix_world@v.co for v in stone_mesh.vertices]
zmin=min(p.z for p in coords);zmax=max(p.z for p in coords)
for v,p in zip(stone_mesh.vertices,coords):v.co=(p.x-cx,p.y-cy,(p.z-zmin)/(zmax-zmin))
stone_mesh.name='Approved balanced terrain | shared unit-height geology'
terrain=[]
def terrain_mass(name,p,scale=(1,1,9),rot=0,inverted=False):
    o=bpy.data.objects.new(name,stone_mesh);GEO.objects.link(o)
    turn=Matrix.Rotation(math.pi,4,'X') if inverted else Matrix.Identity(4)
    o.matrix_world=FRAME@Matrix.Translation(p)@Matrix.Rotation(rot,4,'Z')@Matrix.Diagonal((*scale,1))@turn
    terrain.append({'name':name,'position':list(p),'scale':list(scale),'rotation':rot,'inverted':inverted})
    return o
terrain_mass('Contact | approved rock foundation',(-7.3,3,-5),(1.16,.88,12.98),.28)
terrain_mass('Experiences | approved rock foundation',(-7.6,-4.0,-5),(1.80,1.22,9.57),-.08)
terrain_mass('About | approved rock foundation',(8.25,-2.3,-5),(1.72,1.35,10.39),.16)
terrain_mass('Workshop | approved rock foundation',(8.1,3.8,-5),(1.70,1.22,12.74),-.24)
for n,p,sc,rot in [
    ('Left foreground',(-13.4,-3.8,-6),(1.22,1.50,22),.30),
    ('Left wall',(-13.4,4.5,-6),(1.50,2.20,24),.07),
    ('Left rear',(-11.7,11,-6),(1.60,2.10,25),-.35),
    ('Right foreground',(13.8,-3.9,-6),(1.24,1.65,23),-.15),
    ('Right wall',(13.3,5.8,-6),(1.43,2.15,24),.3),
    ('Right rear',(12.8,12.5,-6),(1.52,2.0,25),-.10),
    ('Back left buttress',(-5.3,12.6,-6),(1.50,1.48,24),.36),
    ('Back right buttress',(5.35,14.5,-6),(1.28,1.60,23),-.22),
    ('Distant left',(-9.4,23,-7),(2.2,1.75,27),.16),
    ('Distant center',(0.3,27,-7),(2.0,1.65,27),.55),
    ('Distant right',(10.4,24,-7),(2.2,1.80,28),-.13),
    ('Rear rock landing',(-.6,6.1,-5),(.43,.51,13.35),.2),
    ('Rear landing buttress',(-1.0,7.0,-6),(.45,.52,24),.37),
]:terrain_mass('Cavern | '+n,p,sc,rot)
for k,(x,y,z,dx,dy,h) in enumerate([(-11,4,15,1.5,2.0,3.0),(-6.5,6,15,1.55,2.0,3.2),(-1.5,7,15.3,1.55,2.0,3.0),(3.5,7.5,15.5,1.55,2.0,3.2),(8.4,6,14.8,1.6,1.8,2.8),(12.5,4.5,14.8,1.4,2.0,3.2)]):
    terrain_mass('Cavern | hanging roof %02d'%k,(x,y,z+1.3),(dx,dy,h),.2*k,True)
def rock_brow(name,p,length,depth,height):
    o=bpy.data.objects.new(name,stone_mesh);GEO.objects.link(o)
    o.matrix_world=FRAME@Matrix.Translation(p)@Matrix.Diagonal((length,depth/5.5,height/5.5,1))@Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Translation((0,0,-.5))
    terrain.append({'name':name,'position':list(p),'horizontal':True,'dimensions':[length,depth,height]})
# Existing alcove roofs nest into the vertical approved rock supports.


# A recessed service passage makes the rear walkway's destination explicit.
# The cutter affects only this new outer buttress, never the protected island.
void=mat('Layout | passage darkness',(.002,.003,.005),0,1)
cut=box('Rear passage | editable rock opening',(-1.0,6.35,9.37),(1.15,2.7,2.02),steel,0)
cut.hide_render=True;cut.hide_set(True);cut.display_type='WIRE'
mod=bpy.data.objects['Cavern | Rear landing buttress'].modifiers.new('Recessed walkway entrance','BOOLEAN')
mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
box('Rear passage | dark recess',(-1,7.61,9.37),(1.15,.05,2.02),void,0)
box('Rear passage | threshold',(-1,6.3,8.365),(1.15,2.1,.07),floor,.01)
for x in [-1.65,-.35]:box('Rear passage | jamb',(x,5.30,9.39),(.12,.20,2.13),steel,.015)
box('Rear passage | lintel',(-1,5.30,10.45),(1.42,.20,.14),steel,.015)
box('Rear passage | amber entry marker',(-.32,5.18,9.8),(.035,.018,.10),warm,.003)
lamp('Rear passage | small warm recess',(-1,5.20,10.18),(-1,6.55,8.65),18,(1,.68,.39),size=.55)

# A dark, cool atmosphere with small localized pools and warm workshop tasks.
S.world=bpy.data.worlds.new('Cavern | cool near-black world');S.world.use_nodes=True
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.11,.16,.24,1)
S.world.node_tree.nodes['Background'].inputs[1].default_value=.055
fixture('Contact | overhead',(-7.4,3.0,12.7),(-6.8,3.0,7.5),650,.78)
fixture('Chasm | overhead',(0,3.1,12.9),(0,3.1,-3),1800,.76)
fixture('Workshop | overhead',(8.0,3.0,11.12),(8.1,3.8,8.2),600,.93)
fixture('Education | ceiling',(-8.5,-2.0,8.35),(-7.5,-4.2,5.7),380,1.08)
fixture('About | ceiling',(8.6,.10,8.18),(8.25,-2.3,6.0),430,1.02)
lamp('Projects | broad overhead',(0,-1.1,11.8),(0,0,F),650,(.58,.73,1),size=4)
lamp('Projects | cool reflected pool',(0,-.7,7.4),(0,1,7.6),26,(.05,.45,1),size=2.1)
lamp('Workshop | warm task wash',(8.2,4.75,10.5),(8.2,5.3,9.0),190,(1,.58,.30),size=1.8)
lamp('Workshop | warm floor bounce',(7.7,3.0,10.4),(8.1,3.8,8.4),65,(1,.57,.30),size=2.2)
lamp('Workshop | low warm fill',(7.0,2.7,9.8),(8.1,4.8,9.4),55,(1,.69,.42),size=2.8)
lamp('About | blue table bounce',(8.15,-2.2,7.0),(8.15,-2.2,5.95),30,(.025,.40,1),size=1.8)
lamp('Cavern | very soft camera bounce',(0,-12,12),(0,3,6),380,(.55,.63,.75),size=14)
lamp('Rock | central soft grazing',(-2.5,-6,4.8),(0,0,3.6),350,(.49,.58,.70),size=7)
lamp('Rock | left support grazing',(-3.5,-5,6),(-8,-3,3),230,(.50,.59,.72),size=5)
lamp('Rock | right support grazing',(4,-5,6),(8,-1,3),235,(.48,.59,.72),size=5)
lamp('Contact | operations fill',(-7.6,-.3,10.4),(-7.3,3,9.1),105,(.68,.76,.86),size=3)
lamp('Education | cool counter wash',(-8,-4.1,8.1),(-8,-2.8,5.9),130,(.69,.77,.88),size=3)
lamp('About | room soft fill',(7,-3.1,8.2),(8.5,-.3,6.4),150,(.65,.76,.90),size=3)
lamp('About | deck and stairs',(8.5,-5.8,8.5),(9,-3.0,6.0),110,(.66,.75,.87),size=4)
lamp('Bridges | left arrival',(-3.8,-2.0,9),(-4.1,-2.6,6.1),40,(.69,.77,.86),size=2.5)
lamp('Bridges | right arrival',(4.5,-1.0,9),(4.5,-1.2,6.2),35,(.68,.78,.90),size=2.5)
lamp('Cavern | distant haze',(0,21,14),(0,10,5),950,(.35,.51,.72),size=7)
lamp('Cavern | left rock grazing',(-9.5,-.5,12),(-13.5,4,7),200,(.40,.52,.68),size=5)
lamp('Cavern | right rock grazing',(10.2,-.5,12),(13.3,5.8,7),200,(.40,.52,.68),size=5)

fog=bpy.data.materials.new('Cavern | subtle volumetric haze');fog.use_nodes=True
fog.node_tree.nodes.clear();out=fog.node_tree.nodes.new('ShaderNodeOutputMaterial');v=fog.node_tree.nodes.new('ShaderNodeVolumePrincipled')
v.inputs['Density'].default_value=.009;v.inputs['Color'].default_value=(.60,.66,.74,1);v.inputs['Anisotropy'].default_value=.28
fog.node_tree.links.new(v.outputs['Volume'],out.inputs['Volume'])
box('Cavern | atmosphere volume',(0,6,6),(35,44,30),fog,0,LIGHT)

def camera(name,p,target,scale):
    o=bpy.data.objects.new(name,bpy.data.cameras.new(name));CAM.objects.link(o)
    o.location=W(p);o.rotation_euler=(W(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.type='ORTHO';o.data.ortho_scale=scale;o.data.lens=48;return o
cam=camera('Camera | reference composition',(0,-40,25.2),(0,1.2,6.95),26.8)
detail_cameras=[]
for label,target,scale in [('Contact and Experiences',(-6.0,-.4,6.8),13.8),('Workshop and About',(7.3,.4,7.2),13.8)]:
    t=Vector(target);detail_cameras.append(camera('Camera | '+label,t+Vector((0,-41.2,18.25)),t,scale))
S.camera=cam
S.render.engine='CYCLES';S.cycles.device='CPU';S.cycles.samples=opt.samples;S.cycles.use_denoising=True
S.cycles.max_bounces=7;S.cycles.volume_bounces=1;S.cycles.transparent_max_bounces=6
S.render.resolution_x=opt.width;S.render.resolution_y=round(opt.width*927/1696);S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG';S.render.film_transparent=False
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=.15
nt=bpy.data.node_groups.new('Layout | restrained glow','CompositorNodeTree');S.compositing_node_group=nt
nt.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
rl=nt.nodes.new('CompositorNodeRLayers');rl.scene=S
glare=nt.nodes.new('CompositorNodeGlare');glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High';glare.inputs['Threshold'].default_value=1.8;glare.inputs['Strength'].default_value=.18
comp=nt.nodes.new('NodeGroupOutput');nt.links.new(rl.outputs['Image'],glare.inputs['Image']);nt.links.new(glare.outputs['Image'],comp.inputs['Image'])
S.render.use_compositing=True

bpy.context.view_layer.update()
after={o.name:fingerprint(o) for o in island}
assert protected==after,'The approved central island was modified'
audit={'source':str(APPROVED),'central_island_unchanged':True,'protected_objects':protected,'gates':{k:list(v) for k,v in gates.items()},'platforms':placements,'imported_objects':asset_counts,'bridges':paths,'terrain':terrain,'stage':opt.stage}
tag='final' if opt.final else f'iteration-{opt.stage:02d}'
output=HERE/('cavern-approved-terrain.blend' if opt.final else f'{tag}.blend')
S['central_island_geometry_locked']=True
S['reference_image']=str(ROOT/'design-references/misty-abyss/blockwork-cavern-central-light-v4.png')
S['terrain_source']=str(APPROVED)
text=bpy.data.texts.new('reference_layout_generator.py');text.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(output))
S.render.filepath=str(HERE/f'{tag}-overview.png')
bpy.ops.render.render(write_still=True,scene=S.name)
if opt.final:
    for detail,label in zip(detail_cameras,['contact-experiences','workshop-about']):
        S.camera=detail;S.render.resolution_x=1400;S.render.resolution_y=1400;S.cycles.samples=72
        S.render.filepath=str(HERE/f'final-{label}.png')
        bpy.ops.render.render(write_still=True,scene=S.name)
    S.camera=cam;S.render.resolution_x=opt.width;S.render.resolution_y=round(opt.width*927/1696);S.cycles.samples=opt.samples
    S.render.filepath=str(HERE/'final-overview.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.color_type='MATERIAL'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(HERE/f'{tag}-audit.json').write_text(json.dumps(audit,indent=2))
print('LAYOUT_RESULT',json.dumps({'blend':str(output),'image':S.render.filepath,'center_unchanged':protected==after,'assets':asset_counts,'terrain_masses':len(terrain)}),flush=True)
