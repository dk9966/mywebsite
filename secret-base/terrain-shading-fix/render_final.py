import bpy
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/terrain-shading-fix')
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=96;s.cycles.use_denoising=True
s.render.resolution_x=1600;s.render.resolution_y=896;s.render.resolution_percentage=100
s.render.use_border=False;s.render.use_crop_to_border=False
s.render.image_settings.file_format='PNG';s.render.filepath=str(P/'final-camera.png')
bpy.ops.render.render(write_still=True)
