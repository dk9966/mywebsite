"""Recess About Me into approved rock, remove Workshop, and refine its holo table."""
import argparse, ast, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
INPUT = P/'cavern-original-holo-table.blend'
OUTPUT = P/'cavern-recessed-about.blend'
ap = argparse.ArgumentParser()
ap.add_argument('--pass', dest='stage', type=int, default=1)
ap.add_argument('--final', action='store_true')
ap.add_argument('--verify', action='store_true')
ap.add_argument('--details', action='store_true')
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--width', type=int, default=1600)
a = ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(INPUT))
bpy.context.preferences.filepaths.save_version = 0
S = bpy.context.scene
FRAME = Matrix.Translation((21.299999237,0,0)) @ Matrix.Rotation(-math.atan2(12,19),4,'Z')
INV = FRAME.inverted()
F, Z = 6.871178627, 6.016

def digest(o):
    h=hashlib.sha256(np.array(o.matrix_world,dtype=np.float64).tobytes())
    if o.type=='MESH':
        for group,field,n,ty in [('vertices','co',3,np.float32),('loops','vertex_index',1,np.int32),('polygons','material_index',1,np.int32)]:
            data=getattr(o.data,group);v=np.empty(len(data)*n,dtype=ty);data.foreach_get(field,v);h.update(v.tobytes())
        for m in o.data.materials:
            if m and m.use_nodes:
                for node in m.node_tree.nodes:
                    for socket in node.inputs:
                        if hasattr(socket,'default_value'):
                            val=socket.default_value
                            try:val=list(val)
                            except TypeError:val=str(val)
                            h.update(str((node.name,socket.identifier,val)).encode())
    return h.hexdigest()

# The newly requested bridge opening is the only permitted center edit.
protect_names=[o.name for o in bpy.data.collections['01 | Original central island - protected'].objects if o.type=='MESH' and o.name!='deck_railing_b']
for cname in ['Platform | Contact','Platform | Experiences']:
    protect_names.extend(o.name for o in bpy.data.collections[cname].objects)
for o in bpy.data.collections['06 | Matching tiled terraces and timber railings'].objects:
    if o.name.startswith(('Contact |','Education |','Work |')):protect_names.append(o.name)
protect_names.extend(['Contact | approved rock foundation','Experiences | approved rock foundation'])
protected={n:digest(bpy.data.objects[n]) for n in set(protect_names)}

if a.verify:
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT));bpy.context.view_layer.update()
    changed=[n for n,d in protected.items() if n not in bpy.context.scene.objects or digest(bpy.data.objects[n])!=d]
    workshop=[o.name for o in bpy.context.scene.objects if not o.hide_render and ('workshop' in o.name.lower() or o.name.startswith('Rear passage |'))]
    report={'passed':not changed and not workshop,'protected_center_and_left_objects':len(protected),'changed_protected_objects':changed,'remaining_workshop_objects':workshop,'center_change_scope':'Only relocate the About bridge railing opening','output_sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}
    (P/'recessed-preservation.json').write_text(json.dumps(report,indent=2));print('RECESSED_VERIFICATION',json.dumps(report),flush=True);assert report['passed'];sys.exit(0)

def col(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
DECK=col('10 | Recessed About floor and architecture')
BRIDGE=col('11 | Frontward straight About bridge')
ROCK=col('12 | About cave opening - approved terrain')
TABLE=bpy.data.collections['09 | Original base hologram table']
LIGHT=col('13 | Recessed bay practical lights')
stone=bpy.data.objects['deck_floor_b'].data.materials[0]
wood=bpy.data.objects['deck_railing_b'].data.materials[0]
graphite=bpy.data.objects['deck_desk_b'].data.materials[0]
dark=bpy.data.objects['deck_desk_dark_b'].data.materials[0]
metal=bpy.data.objects['deck_desk_metal_b'].data.materials[0]
cream=bpy.data.materials['Layout | warm walkway lamp']
CACHE={};paths=[]
# Reuse the proven mesh, paving, and continuous-walkway builders without running
# the preceding scene generator's top-level edits.
names={'mesh','prism','box','beam','hull','offset','area','perimeter','onpoly','poly_length','atdist','railpost','walkway','sample_bezier'}
tree=ast.parse((P/'harmonize_islands.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'shared_layout_geometry','exec'),globals())

removed=[]
def remove(o):
    removed.append(o.name)
    # Work only in this output; source blend files remain untouched.
    bpy.data.objects.remove(o,do_unlink=True)

for o in list(bpy.data.collections['Platform | Workshop'].all_objects):
    remove(o)
for o in list(S.objects):
    if 'workshop' in o.name.lower() or o.name.startswith(('Workshop rear passage','Rear passage |')):
        remove(o)
for name in ['Cavern | Rear rock landing','Cavern | Rear landing buttress']:
    o=bpy.data.objects.get(name)
    if o:
        for mod in list(o.modifiers):
            if mod.name=='Recessed walkway entrance':o.modifiers.remove(mod)
for o in list(bpy.data.collections['06 | Matching tiled terraces and timber railings'].objects):
    if o.name.startswith('About |'):remove(o)
for o in list(bpy.data.collections['07 | Continuous bridges and fitted landings'].objects):
    if o.name.startswith(('Projects to About','About exit')):remove(o)

label_material=bpy.data.objects['ABOUT ME | lettering'].data.materials[0]
about=bpy.data.collections['Platform | About']
for o in list(about.objects):
    n=o.name
    if n.startswith(('About | hangar |','About | ceiling light','About | rear overhead','About | rear wall','About | rear chamber','About | hatch','ABOUT ME |','Drum |')):
        remove(o)
    else:
        # Keep the existing consoles and cabinets as equipment along the bay's rear.
        o.matrix_world=FRAME @ Matrix.Translation((0,2.30,0)) @ INV @ o.matrix_world
for o in list(S.objects):
    if o.type=='LIGHT' and (o.name.startswith('About |') or o.name.startswith('Satin | About')):remove(o)
    elif o.name.startswith('About | ceiling |'):remove(o)

poly=[Vector(p) for p in [(4.95,-3.35),(5.75,-4.25),(10.25,-4.25),(11.55,-3.55),(11.7,-1.7),(11.7,2.45),(10.8,3.05),(5.9,3.05),(4.95,2.15)]]
tc=Vector((8.20,-1.25,Z))
prism('Bay | anchored lower plinth',poly,Z-.65,Z-.19,graphite,bevel=.028)
prism('Bay | satin deck lip',poly,Z-.19,Z-.045,stone,bevel=.016)
prism('Bay | dark paving substrate',offset(poly,.055),Z-.050,Z-.008,dark,bevel=.003)

def clip(subject,boundary):
    out=subject
    for i,p in enumerate(boundary):
        q=boundary[(i+1)%len(boundary)];n=Vector((p.y-q.y,q.x-p.x));d=n.dot(p);res=[]
        if not out:break
        for x,y in zip(out,out[1:]+out[:1]):
            a0=n.dot(x)-d;a1=n.dot(y)-d
            if a0>=-1e-7:res.append(x)
            if (a0>=0)!=(a1>=0):res.append(x+(y-x)*a0/(a0-a1))
        out=res
    return out

# Concentric courses around the holo table broaden into a faceted recessed forecourt.
vs=[];fs=[]
for band in range(17):
    r0=band*.35+.006;r1=(band+1)*.35-.006
    count=48 if band<8 else 32
    phase=(band%2)*math.pi/count
    for j in range(count):
        t0=j*math.tau/count+phase+.003;t1=(j+1)*math.tau/count+phase-.003
        shape=[tc.xy+Vector((math.cos(t)*r,math.sin(t)*r)) for r,t in [(r0,t0),(r1,t0),(r1,t1),(r0,t1)]]
        shape=clip(shape,offset(poly,.07))
        if len(shape)<3 or abs(area(shape))<.0005:continue
        N=len(shape);k=len(vs)
        for z in [Z-.028,Z]:vs.extend((p.x,p.y,z) for p in shape)
        fs.extend([tuple(k+i for i in reversed(range(N))),tuple(k+N+i for i in range(N))])
        fs.extend((k+i,k+(i+1)%N,k+N+(i+1)%N,k+N+i) for i in range(N))
mesh('Bay | circular courses and clipped floor panels',vs,fs,stone,bevel=.003)

def material(name,color,metallic=.3,rough=.5,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m
panel=material('Bay | recessed graphite wall',(.027,.039,.052),.35,.55)
white=material('Bay | cool practical strips',(.52,.80,1),.05,.4,3.2)
blue=material('Bay | restrained holo accents',(.008,.25,.46),.15,.36,.65)

def light(name,p,target,power,size=1.8,color=(.53,.76,.93)):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='RECTANGLE';d.size=size;d.size_y=.35
    o=bpy.data.objects.new(name,d);LIGHT.objects.link(o);o.location=FRAME@Vector(p);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

walls=[((5.25,1.9),(6.1,3.42)),((6.1,3.42),(10.65,3.42)),((10.65,3.42),(11.48,1.95))]
for k,(aa,bb) in enumerate(walls):
    aa=Vector((*aa,0));bb=Vector((*bb,0));d=bb-aa;u=d.normalized();c=(aa+bb)/2;ang=math.atan2(d.y,d.x)
    box('Bay | inset service wall',c+Vector((0,0,Z+1.32)),(d.length,.16,2.64),panel,rot=ang,bev=.018)
    for t in [0,1]:
        q=aa.lerp(bb,t);beam('Bay | vertical bulkhead rib',q+Vector((0,0,Z+.03)),q+Vector((0,0,Z+2.7)),.055,graphite)
    for h in [.12,2.60]:beam('Bay | recessed wall frame',aa+Vector((0,0,Z+h)),bb+Vector((0,0,Z+h)),.05,graphite)
    count=max(1,round(d.length/.85))
    for j in range(1,count):
        q=aa.lerp(bb,j/count);beam('Bay | narrow service rib',q+Vector((0,-.1,Z+.08)),q+Vector((0,-.1,Z+2.56)),.024,metal)
    begin=aa.lerp(bb,.16)+Vector((0,-.12,Z+2.40));end=aa.lerp(bb,.84)+Vector((0,-.12,Z+2.40))
    beam('Bay | recessed light bar housing',begin,end,.055,metal)
    beam('Bay | recessed cool light bar',begin+Vector((0,-.025,-.025)),end+Vector((0,-.025,-.025)),.021,white)
    light('Bay | service strip illumination',c+Vector((0,-.22,Z+2.30)),(tc.x,tc.y,Z),105 if k==1 else 75,d.length*.55)

# Approved rock geometry supplies a real carved alcove and overhang, with no metal roof.
stone_mesh=bpy.data.objects['About | approved rock foundation'].data
shell=bpy.data.objects.new('Bay | continuous approved-rock cave shell',stone_mesh);ROCK.objects.link(shell)
shell.matrix_world=FRAME @ Matrix.Translation((8.35,2.9,-5.5)) @ Matrix.Rotation(.13,4,'Z') @ Matrix.Diagonal((2.05,1.48,22,1))
section=[(4.70,Z-.16),(12.0,Z-.16),(12.0,Z+2.45),(10.85,Z+3.65),(5.85,Z+3.65),(4.70,Z+2.6)]
verts=[(x,y,z) for y in [-3.0,3.75] for x,z in section];N=len(section)
faces=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
cutter=mesh('Bay | editable vaulted excavation',verts,faces,dark,ROCK);cutter.hide_render=True;cutter.hide_set(True);cutter.display_type='WIRE'
for o in [shell,bpy.data.objects['Cavern | Right wall'],bpy.data.objects['Cavern | Right foreground']]:
    mod=o.modifiers.new('Recessed About cave opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
light('Bay | soft overhead practical',(7.5,.1,Z+3.0),(8,-1.2,Z),125,2.1)
beam('Bay | overhang inset lamp',(6.6,.2,Z+3.03),(8.45,.2,Z+3.03),.025,white)

# Relocate only the center railing opening for the About bridge.
railing=bpy.data.objects['deck_railing_b'];railing.data=railing.data.copy()
bm=bmesh.new();bm.from_mesh(railing.data);seen=set(bm.verts);kill=[];theta=math.radians(-44)
while seen:
    v=seen.pop();todo=[v];component=[v]
    while todo:
        v=todo.pop()
        for edge in v.link_edges:
            w=edge.other_vert(v)
            if w in seen:seen.remove(w);todo.append(w);component.append(w)
    pts=[INV@(railing.matrix_world@v.co) for v in component];c=sum(pts,Vector())/len(pts)
    if c.xy.length>2.50 and abs(math.atan2(c.y,c.x)-theta)<math.radians(14.0):kill.extend(component)
bmesh.ops.delete(bm,geom=kill,context='VERTS');bm.to_mesh(railing.data);bm.free()
for h in [.292,.424]:
    for j in range(44):
        t0=math.radians(9.0+21.6*j/44);t1=math.radians(9.0+21.6*(j+1)/44)
        beam('Center | closed former About opening',(2.712*math.cos(t0),2.712*math.sin(t0),F+h),(2.712*math.cos(t1),2.712*math.sin(t1),F+h),.017,wood,BRIDGE)
for degrees in [14.5,25.0]:
    t=math.radians(degrees);railpost('Center | restored rear-right post',Vector((2.712*math.cos(t),2.712*math.sin(t),F)),BRIDGE)

n=Vector((math.cos(theta),math.sin(theta),0));start=n*2.59;end=Vector((5.95,-3.65,0))
bridge_u=(end-start).normalized();bridge_t=Vector((-bridge_u.y,bridge_u.x,0))
rim=offset(poly,.06)
def cross2(u,v):return u.x*v.y-u.y*v.x
joins={};rail_limits={}
for side in [-1,1]:
    origin=(start+bridge_t*.475*side).xy;candidates=[]
    for i,aa in enumerate(rim):
        vv=rim[(i+1)%len(rim)]-aa;den=cross2(bridge_u.xy,vv)
        if abs(den)<1e-8:continue
        ss=cross2(aa-origin,vv)/den;tt=cross2(aa-origin,bridge_u.xy)/den
        if ss>=0 and 0<=tt<=1:candidates.append((ss,origin+bridge_u.xy*ss,i))
    ss,point,edge=min(candidates,key=lambda x:x[0]);rail_limits[side]=ss;joins[side]=(point,edge)
walkway('Projects to recessed About | straight front bridge',[start,end],F,Z,1.02,False,'about-front','About',arrival_landing=1.48,rail_limits=rail_limits,paving_lift=.006)
for side in [-1,1]:
    angle=theta+math.radians(14.1)*side
    anchor=Vector((2.712*math.cos(angle),2.712*math.sin(angle),F))
    join=start+bridge_t*.475*side;join.z=F
    for h in [.292,.424]:beam('Center | fitted front opening rail',anchor+Vector((0,0,h)),join+Vector((0,0,h)),.017,wood,BRIDGE)
exit_start=Vector((10.92,-3.90,0));exit_end=Vector((10.75,-6.6,0))
walkway('About bay | upper exit stair',[exit_start,exit_end],Z,4.18,.86,True,dest='About')
walkway('About bay | lower exit stair',[exit_end,Vector((10.75,-7.25,0)),Vector((7.1,-9.3,0))],4.18,2.1,.96,True,midlanding=True)

def opening(p):
    for path in paths:
        for aa,bb in zip(path['points'],path['points'][1:]):
            aa=Vector(aa[:2]);bb=Vector(bb[:2]);v=bb-aa;t=max(0,min(1,(p-aa).dot(v)/max(v.length_squared,1e-7)))
            if (p-aa-v*t).length<path['width']/2+.055:return True
    return False
for i,aa in enumerate(rim):
    bb=rim[(i+1)%len(rim)]
    if (aa.y+bb.y)/2>.4:continue
    if abs(aa.x-bb.x)<.10 and aa.x<5.1:continue
    # The chamfer and front edge beside this bridge are fitted exactly below.
    if i in [0,1]:continue
    L=(bb-aa).length
    for j in range(max(1,math.ceil(L/.13))):
        p=aa.lerp(bb,j/math.ceil(L/.13));q=aa.lerp(bb,(j+1)/math.ceil(L/.13))
        if (p.y+q.y)/2>-.9 or opening(p) or opening(q) or opening((p+q)/2):continue
        for h in [.292,.424]:beam('Bay | front timber rail',(*p,Z+h),(*q,Z+h),.017,wood)
        beam('Bay | satin edge coping',(*p,Z+.032),(*q,Z+.032),.031,stone)
    for j in range(math.ceil(L/.66)+1):
        p=aa.lerp(bb,j/math.ceil(L/.66))
        if p.y<=-.9 and not opening(p):railpost('Bay | front rail post',Vector((*p,Z)),DECK,light=j%5==2)
assert joins[1][1]==len(rim)-1 and joins[-1][1]==0,'Unexpected receiving edge'
joined_segments=[(Vector((5.01,-1.10)),joins[1][0]),(joins[-1][0],rim[1]),(rim[1],rim[2])]
for aa,bb in joined_segments:
    for h in [.292,.424]:beam('Bay | joined receiving guard',(*aa,Z+h),(*bb,Z+h),.017,wood)
    beam('Bay | joined edge coping',(*aa,Z+.032),(*bb,Z+.032),.031,stone)
    N=max(1,math.ceil((bb-aa).length/.66))
    for j in range(1,N):
        pp=aa.lerp(bb,j/N);railpost('Bay | receiving guard post',Vector((*pp,Z)),DECK)
for pp in [Vector((5.01,-1.10)),rim[1],rim[2]]:railpost('Bay | receiving corner post',Vector((*pp,Z)),DECK)

box('Bay | About nameplate',(8.0,-4.31,Z-.30),(3.0,.075,.35),graphite,bev=.025)
box('Bay | About nameplate inset',(8.0,-4.355,Z-.30),(2.88,.012,.28),dark,bev=.012)
font=bpy.data.curves.new('About bay lettering','FONT');font.body='ABOUT ME';font.align_x='CENTER';font.align_y='CENTER';font.size=.235;font.extrude=.001;font.materials.append(label_material)
sign=bpy.data.objects.new('Bay | ABOUT ME',font);DECK.objects.link(sign);sign.matrix_world=FRAME @ Matrix.Translation((8.0,-4.37,Z-.30)) @ Matrix.Rotation(math.pi/2,4,'X')

# Move the original table into the bay; slope its control annulus toward the center.
oldcenter=Vector(json.loads((P/'holo-audit.json').read_text())['target_center']);shift=tc-oldcenter
for o in TABLE.objects:o.matrix_world=FRAME @ Matrix.Translation(shift) @ INV @ o.matrix_world
bpy.context.view_layer.update()
table_radius=float(json.loads((P/'holo-audit.json').read_text())['target_radius'])
inner,outer=table_radius*.825,table_radius*.994
sloped_parts=('armor_','console_','key_','fastener_','inner_bezel','rim_light_','upper_lip')
for o in TABLE.objects:
    name=o.name.removeprefix('Original holo | ')
    if name.startswith(sloped_parts):
        o.data=o.data.copy();to_local=o.matrix_world.inverted()
        for v in o.data.vertices:
            p=INV@(o.matrix_world@v.co);r=(p-tc).xy.length;t=max(0,min(1,(r-inner)/(outer-inner)))
            p.z+=.12*(1-t)-.045*t;v.co=to_local@(FRAME@p)
        o.data.update()

rim_material=material('Holo | dark sloped alloy',(.032,.045,.064),.55,.43)
rim_metal=material('Holo | subdued bezel metal',(.025,.042,.061),.65,.40)
for o in TABLE.objects:
    name=o.name.removeprefix('Original holo | ')
    if name.startswith(('armor_','fascia_','console_')):
        o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(rim_material)
    elif name.startswith(('upper_lip','inner_bezel','lower_lip','drum')):
        o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(rim_metal)
    elif name.startswith(('key_','rim_light_','fascia_light_')):
        o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(blue)

def cylinder(name,radius,depth,z,mat,collection=DECK,segments=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=FRAME@Vector((tc.x,tc.y,z)))
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    collection.objects.link(o);o.data.materials.append(mat)
    return o

well=bpy.data.objects['Original holo | projection_well']
wellpts=[INV@(well.matrix_world@v.co) for v in well.data.vertices]
surface_z=max(v.z for v in wellpts)+.108
wellradius=max((p-tc).xy.length for p in wellpts)
for o in list(TABLE.objects):
    if o.name.removeprefix('Original holo | ').startswith(('projection_well','display_ring_','display_tick_')):remove(o)
bore=cylinder('Holo | editable recessed optical well',wellradius*.997,.48,Z+.64,dark,ROCK)
bore.hide_render=True;bore.hide_set(True);bore.display_type='WIRE'
for name in ['Original holo | drum','Original holo | upper_lip','Original holo | lower_lip']:
    o=bpy.data.objects[name];mod=o.modifiers.new('Hollow optical chamber','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=bore

optic=material('Holo | translucent blue projection glass',(.008,.075,.18),0,.56)
bs=optic.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=0;bs.inputs['IOR'].default_value=1.16;bs.inputs['Specular IOR Level'].default_value=.04;bs.inputs['Coat Weight'].default_value=0
bs.inputs['Emission Color'].default_value=(.002,.035,.09,1);bs.inputs['Emission Strength'].default_value=.32
nt=optic.node_tree;transparent=nt.nodes.new('ShaderNodeBsdfTransparent');transparent.inputs['Color'].default_value=(.35,.72,.90,1)
mix=nt.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.32
nt.links.new(transparent.outputs[0],mix.inputs[1]);nt.links.new(bs.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
lens=cylinder('Holo | translucent blue lens',wellradius*.992,.018,surface_z-.009,optic,TABLE)
for polyface in lens.data.polygons:polyface.use_smooth=abs(polyface.normal.z)<.5
optical_base=material('Holo | submerged blue optical field',(.006,.055,.11),.05,.72,.40)
nt=optical_base.node_tree;noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.2;noise.inputs['Detail'].default_value=2.0
ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(.002,.018,.045,1);ramp.color_ramp.elements[1].position=.79;ramp.color_ramp.elements[1].color=(.015,.16,.25,1)
nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color']);nt.links.new(ramp.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Emission Color'])
cylinder('Holo | deep optical backing',wellradius*.99,.016,surface_z-.19,optical_base,TABLE)
line=material('Holo | faint submerged reticle',(.008,.24,.38),.05,.50,.45)
for rr in [.34,.70,1.01]:
    pts=[(tc.x+rr*math.cos(i*math.tau/96),tc.y+rr*math.sin(i*math.tau/96),surface_z-.15) for i in range(97)]
    for p,q in zip(pts,pts[1:]):beam('Holo | submerged reticle ring',p,q,.0023,line,TABLE)

# Verify the relocated center opening and the straight route against actual geometry.
bpy.context.view_layer.update()
assert protected=={name:digest(bpy.data.objects[name]) for name in protected},'Protected center or left stations changed'
rb=BVHTree.FromObject(railing,bpy.context.evaluated_depsgraph_get());ri=railing.matrix_world.inverted();gate_clear=True
for side in [-.46,0,.46]:
    for h in [.292,.424]:
        aa=ri@(FRAME@(start-bridge_u*.2+bridge_t*side+Vector((0,0,F+h))));bb=ri@(FRAME@(start+bridge_u*.65+bridge_t*side+Vector((0,0,F+h))));v=bb-aa
        if rb.ray_cast(aa,v.normalized(),v.length)[0] is not None:gate_clear=False
assert gate_clear,'The moved center railing opening is obstructed'
body_hits=[]
for ob in [shell,bpy.data.objects['Cavern | Right wall'],bpy.data.objects['Cavern | Right foreground']]:
    bv=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get());mi=ob.matrix_world.inverted()
    for p,q in zip(paths[0]['points'],paths[0]['points'][1:]):
        for side in [-.39,0,.39]:
            for height in [.18,.7,1.4]:
                aa=mi@(FRAME@(Vector(p)+bridge_t*side+Vector((0,0,height))));bb=mi@(FRAME@(Vector(q)+bridge_t*side+Vector((0,0,height))));dv=bb-aa
                if bv.ray_cast(aa,dv.normalized(),dv.length)[0] is not None:body_hits.append(ob.name)
assert not body_hits,('Rock intersects the bridge walking corridor',sorted(set(body_hits)))
landing_flat=all(abs(p[2]-Z)<1e-5 for p in paths[0]['points'] if (Vector(p).xy-start.xy).dot(bridge_u.xy)>=min(rail_limits.values()))
assert landing_flat,'The bridge must level before either side meets the bay'
assert not [o for o in S.objects if not o.hide_render and ('workshop' in o.name.lower() or o.name.startswith('Rear passage |'))], 'Workshop remnants remain'
tag='recessed' if a.final else f'recessed-preview-{a.stage:02d}'
S['about_revision']='Recessed rock bay; no Workshop; blue optical table; frontward straight bridge'
S['water_added']=False
text=bpy.data.texts.get('build_recessed_about.py') or bpy.data.texts.new('build_recessed_about.py');text.clear();text.write(Path(__file__).read_text())
S.camera=bpy.data.objects['Camera | reference composition'];S.cycles.samples=a.samples;S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*927/1696);S.render.resolution_percentage=100;S.render.filepath=str(P/(tag+'-overview.png'))
output=OUTPUT if a.final else P/(tag+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True);bpy.ops.render.render(write_still=True)
if a.final or a.details:
    for name,label,scale,target in [('Camera | About cave bay','about-bay',9.2,Vector((8.2,-.6,6.8))),('Camera | Original hologram table close-up','table-closeup',4.8,tc+Vector((0,0,.42)))]:
        camera=bpy.data.objects.get(name)
        if camera is None:
            camera=bpy.data.objects.new(name,bpy.data.cameras.new(name));S.collection.objects.link(camera)
        camera.location=FRAME@(target+Vector((0,-12,7.3)));camera.rotation_euler=(FRAME@target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=scale
        S.camera=camera;S.cycles.samples=64 if a.final else 32;S.render.resolution_x=S.render.resolution_y=1400 if a.final else 1100;S.render.filepath=str(P/(tag+'-'+label+'.png'));bpy.ops.render.render(write_still=True)
    S.camera=bpy.data.objects['Camera | reference composition'];S.cycles.samples=a.samples;S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*927/1696);S.render.filepath=str(P/(tag+'-overview.png'))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
audit={'source':str(INPUT),'output':str(output),'workshop_removed':True,'removed_objects':len(removed),'protected_objects':len(protected),'center_edit':'Railing opening moved from +19.75 degrees to -44 degrees','bridge_straight':True,'bridge_gate_clear':gate_clear,'bridge_rock_clearance':not body_hits,'bridge_landing_flat':landing_flat,'bridge_paving_lift':.006,'bridge_rail_joins':{str(side):list(point) for side,(point,edge) in joins.items()},'bridge':paths[0],'about_floor_height':Z,'table_center':list(tc),'table_surface_z':surface_z,'projection_transparent_mix':.68,'projection_emission':.32,'water_added':False}
(P/(tag+'-audit.json')).write_text(json.dumps(audit,indent=2));print('RECESSED_RESULT',json.dumps(audit),flush=True)
