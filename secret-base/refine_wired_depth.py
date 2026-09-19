import bpy,math,random,bmesh,ast
from mathutils import Vector,noise
random.seed(954)
s=bpy.context.scene;col=bpy.data.collections['Wired_Cavern'];cam=s.camera
C=Vector((21,-.3,4));Q=cam.matrix_world.to_quaternion();R=Q@Vector((1,0,0));U=Q@Vector((0,1,0));D=Q@Vector((0,0,1))
rocks=[bpy.data.materials['Wired basalt %02d'%i] for i in range(9)]
metal=bpy.data.materials['Wired dark titanium'];edge=bpy.data.materials['Wired titanium bevels'];black=bpy.data.materials['Wired recessed void'];cyan=bpy.data.materials['Wired cyan luminous core'];dim=bpy.data.materials['Wired cyan dim indicators']
tree=ast.parse(open('/Users/danielku/mywebsite/secret-base/build_wired_cavern.py').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'helpers','exec'))
# Remove unsupported scattered debris; rebuild talus on solid rock surfaces.
for o in list(col.objects):
 if any(k in o.name for k in ['talus field','abyss rock tooth','bottom cavern rim']):bpy.data.objects.remove(o,do_unlink=True)
# Geological spires, with root extending beyond the visible chasm.
for i in range(36):
 x=random.uniform(-13,13);top=random.uniform(-4.2,-11);depth=random.uniform(-18,-6);height=random.uniform(4,8)
 crag('Wired | rooted chasm crag',(x,top-height,depth),(random.uniform(.45,1.2),height+ .6,random.uniform(.5,1.5)),2)
# Foreground rim naturally crops out of image, and contains no floating boulders.
for i in range(14):
 x=-17+i*2.6
 crag('Wired | grounded foreground rim',(x,-12+random.uniform(-1.4,.2),8),(random.uniform(1.6,2.3),2.7,2.2),2)
# Talus is raycast onto the physical tops/fronts of pedestals and ledges.
from mathutils.bvhtree import BVHTree
vs=[];fs=[]
for o in list(col.objects)+[o for o in bpy.data.objects if 'bedrock foundation island' in o.name]:
 if o.type!='MESH' or not any(k in o.name for k in ['service ledge','grounded foreground','rooted chasm','bedrock foundation']):continue
 off=len(vs);vs.extend([o.matrix_world@v.co for v in o.data.vertices]);fs.extend([tuple(off+j for j in f.vertices) for f in o.data.polygons])
bvh=BVHTree.FromPolygons(vs,fs)
for i in range(270):
 x=random.uniform(-14,14);y=random.uniform(-11,-4.8);hit,n,idx,dist=bvh.ray_cast(p(x,y,30),-D,70)
 if hit:
  v=hit-C;r=random.uniform(.08,.28)
  crag('Wired | grounded fractured rubble',(v.dot(R),v.dot(U),v.dot(D)),(r,r*random.uniform(.6,1.3),r*.6),1)
# Pale blue atmosphere between successive wall layers, and a winding high rear opening.
def fog(name,xyz,scale,density,emit):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.14,.3,.46,1);vol.inputs['Anisotropy'].default_value=.18;vol.inputs['Emission Color'].default_value=(.025,.13,.25,1)
 co=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4;tex.inputs['Detail'].default_value=3;nt.links.new(co.outputs['Generated'],tex.inputs['Vector'])
 dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,.5);nt.links.new(co.outputs['Generated'],dist.inputs[0]);fall=nt.nodes.new('ShaderNodeMapRange');fall.inputs['From Min'].default_value=.18;fall.inputs['From Max'].default_value=.6;fall.inputs['To Min'].default_value=1;fall.inputs['To Max'].default_value=0;nt.links.new(dist.outputs['Value'],fall.inputs[0]);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';nt.links.new(tex.outputs['Fac'],mul.inputs[0]);nt.links.new(fall.outputs[0],mul.inputs[1])
 for sock,f in [('Density',density),('Emission Strength',emit)]:
  n=nt.nodes.new('ShaderNodeMath');n.operation='MULTIPLY';n.inputs[1].default_value=f;nt.links.new(mul.outputs[0],n.inputs[0]);nt.links.new(n.outputs[0],vol.inputs[sock])
 nt.links.new(vol.outputs[0],out.inputs['Volume']);o=box(name,xyz,scale,m);return o
fog('Wired | high distant blue haze',(0,5,-24),(19,19,12),.075,.055)
fog('Wired | middle cavern aerial perspective',(0,0,-13),(27,24,9),.032,.022)
fog('Wired | low curling chasm mist',(0,-8,-1),(29,9,12),.10,.055)
# Distant basalt remains visible within atmospheric layers.
for xyz,target,pow,size in [((0,4,-5),(0,4,-17),850,8),((-7,2,-5),(-7,3,-16),400,6),((6,1,-5),(6,2,-16),450,6)]:
 o=area('Wired | depth layer soft bounce',xyz,target,pow,size,(.18,.4,.65));o.data.volume_factor=.25;o.data.specular_factor=.2
# Restore matte gray floor construction rings rather than graphic luminous circles.
for o in bpy.data.objects:
 if o.type=='MESH' and any('Wired subtle deck engraved rings'==m.name for m in o.data.materials if m):
  m=bpy.data.materials['Wired subtle deck engraved rings'];bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.06,.085,.10,1);bs.inputs['Emission Strength'].default_value=.2
# Small lamps need a warm, bright readable pin-light silhouette.
for m in bpy.data.materials:
 if m.use_nodes and any(k in m.name.lower() for k in ['lantern','warm','amber']):
  for n in m.node_tree.nodes:
   if n.type=='BSDF_PRINCIPLED' and n.inputs['Emission Strength'].default_value>0:n.inputs['Emission Strength'].default_value*=1.25
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-3.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
