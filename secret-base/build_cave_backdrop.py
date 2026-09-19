"""Faceted cave surround and luminous mist. Existing station geometry is untouched."""
import bpy, math, random
from mathutils import Vector

random.seed(81)
s=bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
col=bpy.data.collections.get('Cave_Backdrop')
if col:
    for o in list(col.objects): bpy.data.objects.remove(o,do_unlink=True)
else:
    col=bpy.data.collections.new('Cave_Backdrop'); s.collection.children.link(col)
def link(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    return o
old=bpy.data.objects['station_three_islands_camera']
cam=bpy.data.objects.get('Cave_Composition_Camera')
if not cam:
    cam=bpy.data.objects.new('Cave_Composition_Camera',old.data.copy());s.collection.objects.link(cam)
cam.rotation_euler=old.rotation_euler
R=old.matrix_world.to_quaternion()@Vector((1,0,0))
U=old.matrix_world.to_quaternion()@Vector((0,1,0))
D=old.matrix_world.to_quaternion()@Vector((0,0,1))
C=Vector((21,-.3,4.0))
cam.location=C+D*38
cam.data.type='ORTHO';cam.data.ortho_scale=28
s.camera=cam
def p(x,y,d): return C+R*x+U*y+D*d
def mesh(name,v,f,mats):
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update()
    o=bpy.data.objects.new(name,me);col.objects.link(o)
    for m in mats: me.materials.append(m)
    from mathutils import noise as rock_noise
    for poly in me.polygons:
        # Spatially coherent mineral variation, instead of random triangle colors.
        n=rock_noise.noise(poly.center*.62)
        poly.material_index=max(0,min(len(mats)-1,int((.5+n*.48)*(len(mats)-1))+random.choice([-1,0,0,1])))
    return o
rocks=[]
for i in range(12):
    m=bpy.data.materials.new('Cave • basalt facet %02d'%i);m.diffuse_color=(.015+i*.0024,.027+i*.0035,.044+i*.005,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.89
    rocks.append(m)
exec(compile(open('/Users/danielku/mywebsite/secret-base/cave_geology.py').read(), 'cave_geology.py', 'exec'))
# A procedural luminous cloud field replaces distant scenery entirely.
m=bpy.data.materials.new('Cave | distant luminous blue mist');m.use_nodes=True
nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission')
tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=.29;tex.inputs['Detail'].default_value=4;tex.inputs['Roughness'].default_value=.68
coord=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(coord.outputs['Position'] if 'Position' in coord.outputs else coord.outputs['Object'],tex.inputs['Vector'])
ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
for idx,(pos,color) in enumerate([(.15,(.004,.012,.035,1)),(.4,(.009,.065,.16,1)),(.6,(.025,.23,.46,1)),(.83,(.12,.52,.8,1))]):
    el=ramp.color_ramp.elements[0] if idx==0 else ramp.color_ramp.elements.new(pos);el.position=pos;el.color=color
nt.links.new(tex.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs['Color'],em.inputs[0]);em.inputs[1].default_value=.85;nt.links.new(em.outputs[0],out.inputs['Surface'])
geo=nt.nodes.new('ShaderNodeNewGeometry');last=None
for x,y,radius,strength in [(0,6.8,6.5,.72),(-8,-4,5,.8),(8,-4,6,1.05)]:
    dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=p(x,y,-13);nt.links.new(geo.outputs['Position'],dist.inputs[0])
    fall=nt.nodes.new('ShaderNodeMapRange');fall.inputs['From Min'].default_value=0;fall.inputs['From Max'].default_value=radius;fall.inputs['To Min'].default_value=strength;fall.inputs['To Max'].default_value=.035;nt.links.new(dist.outputs['Value'],fall.inputs[0])
    if last:
        mx=nt.nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';nt.links.new(last,mx.inputs[0]);nt.links.new(fall.outputs[0],mx.inputs[1]);last=mx.outputs[0]
    else:last=fall.outputs[0]
nt.links.new(last,em.inputs[1])
mesh('Cave | mist horizon (no distant structures)',[p(-30,-24,-13),p(30,-24,-13),p(30,24,-13),p(-30,24,-13)],[(0,1,2,3)],[m])
def fog(name,loc,scale,density,emission):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.13,.4,.68,1);vol.inputs['Anisotropy'].default_value=.15
    vol.inputs['Emission Color'].default_value=(.015,.22,.55,1)
    co=nt.nodes.new('ShaderNodeTexCoord');noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5;noise.inputs['Detail'].default_value=3
    nt.links.new(co.outputs['Generated'],noise.inputs['Vector'])
    dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,.5);nt.links.new(co.outputs['Generated'],dist.inputs[0])
    fall=nt.nodes.new('ShaderNodeMapRange');fall.inputs['From Min'].default_value=.18;fall.inputs['From Max'].default_value=.52;fall.inputs['To Min'].default_value=1;fall.inputs['To Max'].default_value=0;nt.links.new(dist.outputs['Value'],fall.inputs[0])
    mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';nt.links.new(noise.outputs['Fac'],mul.inputs[0]);nt.links.new(fall.outputs[0],mul.inputs[1])
    for socket,factor in [('Density',density),('Emission Strength',emission)]:
        n=nt.nodes.new('ShaderNodeMath');n.operation='MULTIPLY';n.inputs[1].default_value=factor;nt.links.new(mul.outputs[0],n.inputs[0]);nt.links.new(n.outputs[0],vol.inputs[socket])
    nt.links.new(vol.outputs[0],out.inputs['Volume'])
    bpy.ops.mesh.primitive_cube_add(size=2,location=loc);o=link(bpy.context.object);o.name=name;o.scale=scale;o.data.materials.append(mat);return o
o=fog('Cave | rear illuminated mist volume',p(0,0,-9),(17,12,3),.06,.02);o.rotation_euler=cam.rotation_euler
fog('Cave | deep chasm mist',(21,1,-7),(19,16,7),.38,.07)
fog('Cave | drifting mist over foundations',(21,1,-3.5),(17,14,2.7),.16,.035)
def area(name,loc,target,color,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Cave | glacial vault wash',p(0,5,-8),p(0,8,-3),(.12,.48,1),650,5)
area('Cave | left blue bounce',p(-8,-2,-6),p(-13,1,-3),(.08,.35,1),450,5)
area('Cave | right blue bounce',p(8,-2,-6),p(13,1,-3),(.1,.43,1),550,5)
area('Cave | front soft facet fill',p(0,4,15),p(0,3,-2),(.38,.52,.7),290,13)
area('Cave | recessed rock blue edge',p(.2,3,-4.8),p(4.8,4,-8),(.12,.45,1),220,3)
area('Cave | recessed rock west edge',p(-1,3,-4.8),p(-4.2,4,-8),(.13,.4,1),180,3)
area('Cave | foundation grazing light',p(0,-2,7),p(0,-8,-1),(.16,.36,.65),1100,9)
area('Cave | left wall grazing light',p(-6,-1,4),p(-11,-3,2),(.18,.36,.55),800,7)
area('Cave | right wall grazing light',p(6,0,4),p(11,-2,2),(.15,.36,.6),950,7)
s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.eevee.taa_render_samples=64
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA'
s['cave_backdrop_notes']='Low-poly cave shell, hanging shards and luminous mist only. Original four pillars remain independent on deep bedrock foundations. Ceiling folds share the cave mesh.'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
