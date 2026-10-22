import bpy
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
S=bpy.context.scene
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True
S.cycles.device='CPU'
S.render.resolution_x=2400;S.render.resolution_y=1344;S.render.resolution_percentage=100
S.camera=bpy.data.objects['150 | main cave camera']
S.render.use_border=True;S.render.use_crop_to_border=True
S.render.border_min_x=.565;S.render.border_max_x=1.0
S.render.border_min_y=.13;S.render.border_max_y=.68
S.render.image_settings.file_format='PNG'
S.render.filepath=str(P/'detail-render.png')
bpy.ops.render.render(write_still=True)
