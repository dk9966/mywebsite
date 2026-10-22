import bpy, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_ray_tri
from bpy_extras.object_utils import world_to_camera_view
P=Path('/Users/danielku/mywebsite/secret-base/lower-reference-alignment')
S=bpy.context.scene;CAM=S.camera;lower=bpy.data.objects['Lower | plain octagon']
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.824491024;H=2.03
W=1697;IH=927;RH=W*S.render.resolution_y/S.render.resolution_x;PAD=(RH-IH)/2
vp=CAM.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=S.render.resolution_x,y=S.render.resolution_y)@CAM.matrix_world.inverted();ivp=vp.inverted()
def ray(uv):
 p=ivp@Vector((2*uv[0]/W-1,1-2*(uv[1]+PAD)/RH,-1,1));p=p.xyz/p.w
 return CAM.matrix_world.translation.copy(),(p-CAM.matrix_world.translation).normalized()
def at_z(uv,z):
 a,d=ray(uv);return a+d*((z-a.z)/d.z)
def uv(p):
 q=world_to_camera_view(S,CAM,p);return Vector((q.x*W,(1-q.y)*RH-PAD))
def col(name):
 c=bpy.data.collections.get(name)
 if not c:c=bpy.data.collections.new(name);S.collection.children.link(c)
 return c
ARCH=col('160 | Reference aligned workshop architecture')
DETAIL=col('161 | Reference aligned service pad and brackets')
bpy.data.collections['156 | Lower workshop walls and canopy'].hide_viewport=True
bpy.data.collections['156 | Lower workshop walls and canopy'].hide_render=True
steel=bpy.data.materials['Metal | dark structural steel'];black=bpy.data.materials['Metal | unlit grate recess'];alloy=bpy.data.materials['Metal | outer walkway alloy'];edge=bpy.data.materials['Metal | machined edge highlights'];white=bpy.data.materials['Lower | cool white practical diffuser'];paint=bpy.data.materials['Lower | muted brass floor registration']
def mat(name,color,metal=.65,rough=.42):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
wall=mat('Lower | aligned blue graphite panels',(.085,.115,.135),.55,.46)
turn=mat('Lower | radial satin turntable',(.10,.14,.17),.72,.37)
trim=mat('Lower | aligned architectural trim',(.055,.082,.10),.65,.40)
roofmat=bpy.data.materials['Lower | matte roof cassette']
def mesh(name,verts,faces,material,c=ARCH,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(material);me.update()
 o=bpy.data.objects.new(name,me);c.objects.link(o)
 o.parent=lower;o.matrix_world=Matrix.Identity(4)
 if bevel:
  m=o.modifiers.new('Small fabricated edge','BEVEL');m.width=bevel;m.segments=2
  o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
 return o

def beam(name,a,b,width,depth,material=steel,c=ARCH,bevel=.003):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();help=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0));u=axis.cross(help).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 vs=[tuple(p+su*u+sv*v) for p in(a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 return mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,c,bevel)
def plate(name,points,normal,depth,material,c=ARCH,bevel=.004):
 vs=[tuple(p-normal*d) for d in (0,depth) for p in points];n=len(points)
 fs=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,vs,fs,material,c,bevel)
