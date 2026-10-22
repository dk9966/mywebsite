import bpy, sys
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/octagon-wall-alignment')
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.cycles.device='CPU'
s.render.resolution_x=2400;s.render.resolution_y=1344;s.render.resolution_percentage=100
s.render.use_border=True;s.render.use_crop_to_border=True
s.render.border_min_x=.66;s.render.border_max_x=1.;s.render.border_min_y=.06;s.render.border_max_y=.61
s.render.filepath=str(P/'aligned-walls.png')
s.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
