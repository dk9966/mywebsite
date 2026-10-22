import bpy
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/terrain-shading-fix')
s=bpy.context.scene
s.cycles.device='CPU'
s.cycles.samples=24
s.cycles.use_denoising=True
s.render.resolution_x=1000
s.render.resolution_y=560
s.render.resolution_percentage=100
s.render.use_border=False
s.render.use_crop_to_border=False
s.render.image_settings.file_format='PNG'
for variant in ['before','without-local-mist']:
    if variant=='without-local-mist':
        for o in s.objects:
            if 'soft local beam mist' in o.name:
                o.hide_render=True
    s.render.filepath=str(P/(variant+'.png'))
    bpy.ops.render.render(write_still=True)
