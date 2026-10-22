import bpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
s=bpy.context.scene
root=bpy.data.objects['Lower | circular roof assembly']
target=root.matrix_world.translation+Vector((0,0,-.3))
d=bpy.data.cameras.new('Circular roof inspection camera')
cam=bpy.data.objects.new(d.name,d)
s.collection.objects.link(cam)
cam.location=target+Vector((-10,-4.3,3.9))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
d.type='PERSP'
d.lens=48
s.camera=cam
s.render.engine='CYCLES'
s.cycles.samples=24
s.cycles.use_denoising=True
s.cycles.device='CPU'
s.render.resolution_x=1400
s.render.resolution_y=1100
s.render.resolution_percentage=100
s.render.use_border=False
s.render.image_settings.file_format='PNG'
s.render.filepath=str(P/'circular-roof-preview.png')
bpy.ops.render.render(write_still=True)
