"""Broad stepped cave strata in the established pillar stone language."""
import bpy,math,random,os
from mathutils import Vector
random.seed(841)
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-environment-style-match.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
s=bpy.context.scene;cam=s.camera;Q=cam.matrix_world.to_quaternion()
R=Q@Vector((1,0,0));U=Q@Vector((0,1,0));D=Q@Vector((0,0,1));C=Vector((21,-.3,4))
def p(x,y,d):return C+R*x+U*y+D*d
col=bpy.data.collections.get('Environment_Stepped_Stone')
if col:
 for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
 col=bpy.data.collections.new('Environment_Stepped_Stone');s.collection.children.link(col)
old=bpy.data.objects.get('Cave | broad stone relief')
if old:old.hide_render=True;old.hide_set(True)
mats=[]
for j in range(5):
 m=bpy.data.materials.get('Environment unified slate %d'%j) or bpy.data.materials.new('Environment unified slate %d'%j)
 m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');f=.94+j*.03
 bs.inputs['Base Color'].default_value=(.018*f,.024*f,.032*f,1)
 bs.inputs['Roughness'].default_value=.76;bs.inputs['Specular IOR Level'].default_value=.28
 tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=6;tex.inputs['Detail'].default_value=2
 bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17;bump.inputs['Distance'].default_value=.04
 nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
 mats.append(m)
hosts=[]
for cname in ['Cave_Backdrop','Cave_Ceiling_Teeth']:
 for o in bpy.data.collections[cname].objects:
  if o.type=='MESH' and ('walls' in o.name or 'bedrock' in o.name or 'hanging formations' in o.name):
   hosts.append(o);o.data.materials.clear()
   for m in mats:o.data.materials.append(m)
   for face in o.data.polygons:face.material_index=2
vs=[];fs=[]
def slab(center,N,H,V,w,h,depth):
 # Clipped, unequal corners and a shallow broken face; broad forms, not tiny tiles.
 cut=random.uniform(.09,.19)
 outline=[(-.5+cut,-.5),(.5-cut,-.5),(.5,-.5+cut),(.5,.5-cut),(.5-cut,.5),(-.5+cut,.5),(-.5,.5-cut),(-.5,-.5+cut)]
 start=len(vs)
 for layer in [0,1]:
  for x,y in outline:
   offset=(-.11 if layer==0 else depth*(1+.15*x-.12*y))
   vs.append(center+H*(x*w)+V*(y*h)+N*offset)
 fs.append(tuple(start+8+j for j in range(8)))
 for j in range(8):fs.append((start+j,start+(j+1)%8,start+8+(j+1)%8,start+8+j))
vault=bpy.data.objects['Cave | continuous sculpted walls and hanging roof'];inv=vault.matrix_world.inverted()
for side in [-1,1]:
 for row in range(13):
  y=-13+row*1.45
  for k in range(7):
   if random.random()<.32:continue
   d=-5+k*2.5+random.uniform(-.85,.85)
   origin=p(0,y+random.uniform(-.3,.3),d);direction=R*side
   hit,loc,normal,idx=vault.ray_cast(inv@origin,(inv.to_3x3()@direction).normalized())
   if not hit:continue
   point=vault.matrix_world@loc;N=(vault.matrix_world.to_3x3()@normal).normalized()
   if N.dot(-direction)<0:N=-N
   H=N.cross(Vector((0,0,1))).normalized();V=H.cross(N).normalized()
   slab(point,N,H,V,random.uniform(.45,1.1),random.uniform(.6,1.65),random.uniform(.025,.07))
# Sparse shallow ceiling fractures connect the side-wall treatment to the roots.
for i in range(32):
 x=random.uniform(-9,9);d=random.uniform(-5,8);origin=p(x,2,d)
 hit,loc,normal,idx=vault.ray_cast(inv@origin,(inv.to_3x3()@U).normalized())
 if hit:
  point=vault.matrix_world@loc;N=(vault.matrix_world.to_3x3()@normal).normalized()
  if N.dot(-U)<0:N=-N
  H=(R-N*R.dot(N)).normalized();V=H.cross(N).normalized()
  slab(point,N,H,V,random.uniform(.55,1.1),random.uniform(.4,.9),random.uniform(.02,.06))
# Chunkier stratified surfaces on the lower foundations, retaining their outline.
for host in hosts:
 if 'foundation' not in host.name:continue
 center=sum((host.matrix_world@Vector(v) for v in host.bound_box),Vector())/8
 inv=host.matrix_world.inverted()
 for i in range(42):
  a=random.random()*math.tau;z=random.uniform(-11,-.15);N=Vector((math.cos(a),math.sin(a),0));origin=Vector((center.x,center.y,z))+N*12
  hit,loc,normal,idx=host.ray_cast(inv@origin,(inv.to_3x3()@(-N)).normalized())
  if hit:
   point=host.matrix_world@loc;H=Vector((-N.y,N.x,0));slab(point,N,H,Vector((0,0,1)),random.uniform(.5,.9),random.uniform(.8,1.6),random.uniform(.03,.08))
me=bpy.data.meshes.new('Environment stepped stone strata');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('Cave | broad vertical stepped strata',me);col.objects.link(o)
for m in mats:me.materials.append(m)
for i,face in enumerate(me.polygons):face.material_index=(i//9)%5
receivers=bpy.data.collections.get('Cave ceiling light receivers')
if receivers:receivers.objects.link(o)
import bmesh
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'stepped_rock_pieces':len(vs)//16,'pillar_assets_unchanged':True}
