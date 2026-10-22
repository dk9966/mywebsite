"""Inspect the full landing in a separate Blender process."""
import bpy
from mathutils import Vector
from pathlib import Path

P=Path(__file__).resolve().parent
s=bpy.context.scene
s.render.engine='CYCLES'
s.cycles.samples=24
s.cycles.use_denoising=True
s.cycles.device='CPU'
s.render.resolution_x=1400
s.render.resolution_y=1050
s.render.resolution_percentage=100
s.render.use_border=False
s.render.use_crop_to_border=False
s.render.image_settings.file_format='PNG'
# Isolate the landing and stairs for inspection; the cave blocks a close camera.
visible={o.name for name in ['167 | Left platform matching steel railings',
                            '166 | Left bridge and right-turn steel stairs']
         for o in bpy.data.collections[name].objects if not o.hide_render}
visible.add('Front left | beveled rectangle landing')
for o in s.objects:
    if o.type=='MESH':o.hide_render=o.name not in visible
target=Vector((12.3,3.3,3.3))
data=bpy.data.cameras.new('Left railing inspection')
cam=bpy.data.objects.new(data.name,data)
s.collection.objects.link(cam)
cam.location=target+Vector((11,-13,12))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=17.5
s.camera=cam
ld=bpy.data.lights.new('Railing inspection softbox','AREA')
lo=bpy.data.objects.new(ld.name,ld)
s.collection.objects.link(lo)
lo.location=target+Vector((4,-3,9))
lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
ld.energy=1500;ld.shape='DISK';ld.size=9
s.render.filepath=str(P/'railings-detail.png')
bpy.ops.render.render(write_still=True)
