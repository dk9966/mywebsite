import bpy
from mathutils import Vector
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/opposite-interior-walls')
s=bpy.context.scene
frame=bpy.data.objects['150 | continuous cave with oblique carved rooms'].matrix_world
cam=bpy.data.objects.new('Wall extension review camera',bpy.data.cameras.new('Wall extension review camera'))
s.collection.objects.link(cam)
cam.location=frame@Vector((-.7,-11.5,13.1))
target=frame@Vector((8.1,-3.1,7.4))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.lens=43
s.camera=cam
s.render.engine='CYCLES'
s.cycles.samples=24
s.cycles.use_denoising=True
s.cycles.device='CPU'
s.render.resolution_x=1152;s.render.resolution_y=800;s.render.resolution_percentage=100
s.render.use_border=False
s.render.image_settings.file_format='PNG'
s.render.filepath=str(P/'extended-interior-walls.png')
bpy.ops.render.render(write_still=True)
