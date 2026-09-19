"""Add a centered, exportable hologram table; reruns replace only this rig."""
import bpy, math
from mathutils import Vector
host = bpy.data.objects['island_pillar_about']
floor = bpy.data.objects['deck_floor_about']
bpy.context.view_layer.update()
pts = [floor.matrix_world @ Vector(v) for v in floor.bound_box]
cx = (min(p.x for p in pts)+max(p.x for p in pts))/2
cy = (min(p.y for p in pts)+max(p.y for p in pts))/2
fz = max(p.z for p in pts)
coll = bpy.data.collections.get('about_holo_table')
if coll:
    for o in list(coll.objects): bpy.data.objects.remove(o, do_unlink=True)
else:
    coll = bpy.data.collections.new('about_holo_table'); bpy.context.scene.collection.children.link(coll)
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
metal = bpy.data.materials['metalDark']; graphite = bpy.data.materials['graphite']; cyan = bpy.data.materials['neonCyan_workshop_cyan']
def material(name, color, emission=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Metallic'].default_value=.4; p.inputs['Roughness'].default_value=.36
    p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emission
    return m
surface=material('aboutHolo_projection',(0.025,.22,.34),1.7)
lines=material('aboutHolo_reticle',(.16,.51,.65),1.1)
def finish(o,name,mat,bevel=.008):
    o.name='aboutHolo_'+name
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o); o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Machined soft edges','BEVEL'); b.width=bevel; b.segments=2
        o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    world=o.matrix_world.copy(); o.parent=host; o.matrix_world=world
    return o

def cylinder(name,r,depth,z,mat,vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=(cx,cy,fz+z))
    return finish(bpy.context.object,name,mat)

def arc(name,ri,ro,z0,z1,a0,a1,mat,steps=8):
    verts=[]
    for z,r in [(z0,ri),(z0,ro),(z1,ri),(z1,ro)]:
        verts += [(cx+r*math.cos(a0+(a1-a0)*i/steps),cy+r*math.sin(a0+(a1-a0)*i/steps),fz+z) for i in range(steps+1)]
    n=steps+1; faces=[]
    for i in range(steps):
        faces += [(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)]
    faces += [(0,n,3*n,2*n),(steps,2*n+steps,3*n+steps,n+steps)]
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); coll.objects.link(o); return finish(o,name,mat,.003)
def box(name,r,a,z,sz,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(cx+r*math.cos(a),cy+r*math.sin(a),fz+z))
    o=bpy.context.object; o.rotation_euler.z=a; o.scale=sz
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat,.004)
cylinder('foot',.58,.08,.04,metal)
cylinder('pedestal',.39,.49,.305,graphite,32)
cylinder('pedestal_collar',.43,.065,.51,metal)
cylinder('lower_lip',1.06,.06,.57,metal)
cylinder('drum',1.035,.25,.705,metal)
cylinder('upper_lip',1.075,.045,.843,metal)
cylinder('projection_well',.855,.025,.867,surface)
arc('inner_bezel',.85,.883,.866,.895,0,math.tau,metal,96)
for i in range(16):
    a=i*math.tau/16
    arc('armor_%02d'%i,.89,1.067,.858,.883,a+.015,a+math.tau/16-.015,graphite)
    arc('fascia_%02d'%i,1.032,1.047,.613,.807,a+.014,a+math.tau/16-.014,graphite)
    if i%2==0:
        arc('rim_light_%02d'%i,.855,.868,.896,.906,a+.045,a+.29,cyan)
        box('lamp_socket_%02d'%i,1.052,a+.19,.701,(.025,.076,.156),metal)
        box('fascia_light_%02d'%i,1.069,a+.19,.701,(.01,.027,.114),cyan)
    if i%4==1:
        mid=a+.19
        box('console_%02d'%i,.978,mid,.895,(.134,.22,.022),metal)
        for j in range(3):
            for k in range(2):
                box('key_%d_%d_%d'%(i,j,k),.945+k*.045,mid+(j-1)*.061,.911,(.026,.042,.008),cyan)
    else:
        for r in [.92,1.035]:
            box('fastener_%d_%s'%(i,r),r,a+.06,.893,(.016,.016,.008),metal)
# A quiet, geometric projected reticle; solid-color materials survive glTF export.
for i,r in enumerate([.26,.54,.77]): arc('display_ring_%d'%i,r,r+.003,.882,.884,0,math.tau,lines,96)
for i in range(24):
    a=i*math.tau/24
    box('display_tick_%02d'%i,.735,a,.885,(.028,.004,.002),lines)
bpy.context.view_layer.update()
print('About holo table centered at',cx,cy,fz,'objects',len(coll.objects))

# Match the Projects worktop's height above its own deck. The islands sit at
# different world elevations, so absolute Z would make this table taller.
project_floor = bpy.data.objects['deck_floor_b']
project_hud = bpy.data.objects['deck_desk_hud_b']
project_floor_z = max((project_floor.matrix_world @ Vector(v)).z for v in project_floor.bound_box)
# The HUD starts 2 mm above the physical worktop.
project_worktop_z = min((project_hud.matrix_world @ Vector(v)).z for v in project_hud.bound_box) - .002
surface_height = project_worktop_z - project_floor_z
height_scale = surface_height / (.867 + .025 / 2)
for o in coll.objects:
    world = o.matrix_world.copy()
    inverse = world.inverted()
    for v in o.data.vertices:
        p = world @ v.co
        p.z = fz + (p.z - fz) * height_scale
        v.co = inverse @ p
    o.data.update()
    for mod in o.modifiers:
        if mod.type == 'BEVEL': mod.width *= height_scale
bpy.context.view_layer.update()
print('Matched worktop height:', surface_height, 'vertical scale:', height_scale)
