"""Isolated inspection renders, without saving scene changes."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
label=sys.argv[sys.argv.index('--')+1]
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True
s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100
s.render.use_border=False;s.render.use_crop_to_border=False
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
keep=['02 | Machined rings and eight recessed grates','03 | Uniform slender steel railings','158 | Connected bridge and railings','166 | Left bridge and right-turn steel stairs','170 | Rear-left connected platform','174 | Flush circular bridge joints']
visible={o.name for n in keep if n in bpy.data.collections for o in bpy.data.collections[n].objects if not o.hide_render}
for o in s.objects:
 if o.type=='MESH' and o.name not in visible:o.hide_render=True
 if o.type=='LIGHT':o.hide_render=True
world=bpy.data.worlds.new('Joint inspection studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.23,.28,.33,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;s.world=world
cam=bpy.data.objects.new('Joint inspection camera',bpy.data.cameras.new('Joint inspection camera'));s.collection.objects.link(cam)
cam.data.type='ORTHO';s.camera=cam
light=bpy.data.objects.new('Joint inspection softbox',bpy.data.lights.new('Joint inspection softbox','AREA'));s.collection.objects.link(light)
light.data.energy=480;light.data.shape='DISK';light.data.size=4
C=Vector((21.299999237,0,6.871178627))
views=[('front',Vector((.43392,-.90095,0))),('stairs',Vector((-.97625,-.21665,0))),('rear',Vector((-.28458,.95865,0)))]
for name,d in views:
 d.normalize();u=Vector((-d.y,d.x,0));target=C+d*3.79
 cam.location=target+d*.6-u*1.1+Vector((0,0,2.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.15
 light.location=target+d+Vector((0,0,3));light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(P/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
