import bpy,sys
from pathlib import Path
P=Path(__file__).resolve().parent;S=bpy.context.scene
S.camera=bpy.data.objects['150 | main cave camera']
S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1800;S.render.resolution_y=1008;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG';S.render.filepath=str(P/'scene-view.png')
if '--close' in sys.argv:
 S.render.resolution_x=2600;S.render.resolution_y=1456;S.cycles.samples=24
 S.render.use_border=True;S.render.use_crop_to_border=True;S.render.border_min_x=.65;S.render.border_max_x=1.;S.render.border_min_y=.30;S.render.border_max_y=.97;S.render.filepath=str(P/'upper-right-detail.png')
bpy.ops.render.render(write_still=True)
