import bpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
s=bpy.context.scene
s.render.engine='CYCLES'
s.cycles.samples=24
s.cycles.use_denoising=True
s.cycles.device='CPU'
s.render.resolution_x=1440
s.render.resolution_y=1080
s.render.resolution_percentage=100
s.render.use_border=False
s.render.use_crop_to_border=False
s.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('Stair detail inspection')
cam=bpy.data.objects.new(data.name,data)
s.collection.objects.link(cam)
target=Vector((14.1,-.25,4.6))
cam.location=target+Vector((6,4,6))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO'
data.ortho_scale=9.1
s.camera=cam
# Extra soft light for inspecting the actual steel geometry.
ld=bpy.data.lights.new('Inspection softbox','AREA')
lo=bpy.data.objects.new(ld.name,ld)
s.collection.objects.link(lo)
lo.location=target+Vector((0,-3,7))
lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
ld.energy=650
ld.shape='DISK'
ld.size=7
s.render.filepath=str(P/'stairs-detail.png')
bpy.ops.render.render(write_still=True)
if '--overview' in __import__('sys').argv:
    s.camera=bpy.data.objects['150 | main cave camera']
    s.render.resolution_x=1600
    s.render.resolution_y=896
    s.render.filepath=str(P/'stairs-overview.png')
    bpy.ops.render.render(write_still=True)
