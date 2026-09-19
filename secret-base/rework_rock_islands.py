"""Reference-directed rocky islands, reversible through saved source backup."""
import bpy, math, random, os
from mathutils import Vector
random.seed(273)
s=bpy.context.scene
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-rock-rework.blend'
if not os.path.exists(backup): bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
col=bpy.data.collections.get('Rock_Island_Rework')
if col:
    for o in list(col.objects): bpy.data.objects.remove(o,do_unlink=True)
else:
    col=bpy.data.collections.new('Rock_Island_Rework');s.collection.children.link(col)
def mesh(name,vs,fs,mats):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    o=bpy.data.objects.new(name,me);col.objects.link(o)
    for m in mats:me.materials.append(m)
    for p in me.polygons:p.material_index=random.randrange(len(mats))
    return o
rocks=[]
for i in range(9):
    m=bpy.data.materials.get('Rework basalt %02d'%i) or bpy.data.materials.new('Rework basalt %02d'%i)
    m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(.016+i*.0028,.025+i*.0035,.039+i*.0042,1)
    bs.inputs['Roughness'].default_value=.48
    tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=18;tex.inputs['Detail'].default_value=3
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.065
    nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    rocks.append(m)
def prism(vs,fs,x,y,z0,z1,rx,ry,angle):
    n=5;start=len(vs);phase=random.random()*.35
    radial=[random.uniform(.82,1.16) for _ in range(n)]
    for z,sc in [(z0,random.uniform(.9,1.12)),(z1,random.uniform(.84,1.08))]:
        for j in range(n):
            a=math.tau*j/n+phase;dx=math.cos(a)*rx*radial[j]*sc;dy=math.sin(a)*ry*radial[j]*sc
            vs.append((x+dx*math.cos(angle)-dy*math.sin(angle),y+dx*math.sin(angle)+dy*math.cos(angle),z+random.uniform(-.07,.07)))
    fs.append(tuple(start+j for j in reversed(range(n))));fs.append(tuple(start+n+j for j in range(n)))
    for j in range(n):fs.append((start+j,start+(j+1)%n,start+n+(j+1)%n,start+n+j))
def crag(name,cx,cy,r,top,bottom,hero=True):
    vs=[];fs=[]
    # Interlocking vertical columns run through the shoulder to the chasm.
    for ring,count in [(0,1),(.46,12),(.78,26),(.96,42)]:
        for j in range(count):
            a=math.tau*j/count+random.uniform(-.035,.035)
            rr=r*ring*(1+.045*math.sin(a*5)+.035*math.cos(a*3))
            x=cx+math.cos(a)*rr;y=cy+math.sin(a)*rr
            crown=top+random.uniform(-.15,.06) if ring>.9 else top-random.uniform(.22,.55)
            if not hero:crown=top+random.uniform(-1.8,1.4)
            width=r*(.17 if ring>.9 else .29)
            z=bottom+random.uniform(-1.2,1.2)
            while z<crown-.08:
                znext=min(crown,z+random.uniform(.28,.95))
                t=(z-bottom)/(top-bottom)
                spread=(.90+.10*t+.12*math.sin(t*15+a*2)+.07*math.sin(a*5))*(1+max(0,.58-t)*1.2)
                prism(vs,fs,cx+(x-cx)*spread+random.uniform(-.07,.07),cy+(y-cy)*spread+random.uniform(-.07,.07),z,znext,width*random.uniform(.8,1.15),width*random.uniform(.75,1.05),a)
                z=znext+.012
    return mesh(name,vs,fs,rocks)
specs=[]
for key in ['project','about','experience','contact']:
    old=bpy.data.objects['island_pillar_'+key];cx,cy=old.matrix_world.translation.xy
    floor=next(o for o in bpy.data.collections['deck_'+key].objects if o.name.startswith('deck_floor'))
    top=max((floor.matrix_world@v.co).z for v in floor.data.vertices)
    r=floor.dimensions.x/2
    specs.append((key,cx,cy,r,top))
    old.hide_render=True;old.hide_set(True)
    foundation=bpy.data.objects.get('Cave | bedrock foundation '+old.name)
    if foundation:foundation.hide_render=True;foundation.hide_set(True)
    crag('Rock | '+key+' continuous fractured body',cx,cy,r,top-.04,-26)
    for o in bpy.data.collections['deck_'+key].objects:
        if 'pillar_veins' in o.name:o.hide_render=True;o.hide_set(True)
# Broaden the cave behind the islands while keeping the foreground arch.
cam=s.camera;Q=cam.matrix_world.to_quaternion();R=Q@Vector((1,0,0));U=Q@Vector((0,1,0));D=Q@Vector((0,0,1));C=Vector((21,-.3,4))
def p(x,y,d):return C+R*x+U*y+D*d
vault=bpy.data.objects['Cave | continuous sculpted walls and hanging roof']
if not vault.get('rework_opened'):
    for v in vault.data.vertices:
        delta=v.co-C;x=delta.dot(R);d=delta.dot(D)
        influence=max(0,min(1,(5-d)/12))
        v.co+=R*x*.3*influence-D*2*influence
    vault['rework_opened']=True
# Offset silhouettes at two depths create a varied cavern beyond the station.
for i,(x,y,d,r) in enumerate([(-9,1,-9,1.4),(-6.4,3,-10,1.1),(-3.1,4,-11,1.3),(.4,5,-11,1.25),(3.4,2.8,-10,1.6),(7,3.4,-9,1.2),(9.7,-.3,-8,1.4),(-4,-6,-5,1.0),(5,-7,-5,1.3)]):
    pt=p(x,y,d);crag('Rock | distant spire %02d'%i,pt.x,pt.y,r,pt.z,-19,False)
# Independent lighting controls; preserve baseline values for repeat runs.
for o in s.objects:
    if o.type!='LIGHT':continue
    n=o.name
    factor=1
    if 'shaft' in n:factor=.38 if 'back' not in n and 'rim' not in n else .7
    if 'foundation grazing' in n:factor=.35
    if 'wall grazing' in n:factor=.58
    if 'front soft facet fill' in n:factor=.65
    if factor!=1:
        if 'rock_original_power' not in o:o['rock_original_power']=o.data.energy
        o.data=o.data.copy();o.data.energy=o['rock_original_power']*factor;o.data.color=(.10,.32,.75)
def area(name,loc,target,power,color,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Rock | distant blue illumination',p(0,7,-5),p(0,1,-11),1000,(.08,.38,1),10)
area('Rock | blue chasm separation',p(0,-5,-3),p(0,-2,3),280,(.04,.35,1),8)
for key,x,y,r,top in specs:
    area('Rock | '+key+' deck softbox',(x-1,y-2,top+4),(x,y,top),160,(.32,.56,1),4)
# Add small interrupted luminous mineral seams to the outer rock columns.
em=bpy.data.materials.get('Rock cyan mineral') or bpy.data.materials.new('Rock cyan mineral');em.use_nodes=True
bs=em.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.005,.15,.22,1);bs.inputs['Emission Color'].default_value=(.005,.48,1,1);bs.inputs['Emission Strength'].default_value=3
for key,x,y,r,top in specs:
    for j in range(13):
        a=math.tau*j/13+.15;z=random.uniform(-8,top-1);radius=r*1.065
        cu=bpy.data.curves.new('fracture','CURVE');cu.dimensions='3D';cu.bevel_depth=.009;cu.bevel_resolution=0
        sp=cu.splines.new('POLY');sp.points.add(3)
        for k,pt in enumerate(sp.points):
            aa=a+(0 if k<2 else .022);pt.co=(x+math.cos(aa)*radius,y+math.sin(aa)*radius,z+k*.24,1)
        o=bpy.data.objects.new('Rock | '+key+' mineral seam',cu);col.objects.link(o);cu.materials.append(em)
# Existing mist volumes are placed entirely beneath walking surfaces.
o=bpy.data.objects.get('Cave | drifting mist over foundations')
if o:o.location.z=-.8;o.scale.z=3.6
o=bpy.data.objects.get('Cave | deep chasm mist')
if o:o.location.z=-6;o.scale.z=7.5
exec(compile(open(ROOT+'polish_rock_islands.py').read(),'polish_rock_islands.py','exec'))
s['rock_rework_notes']='Fractured basalt climbs to deck perimeter; distant spires; reduced shaft grazing; below-deck mist; no waterfalls.'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'saved':bpy.data.filepath,'objects':len(col.objects),'specs':specs}
