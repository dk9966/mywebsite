import bpy, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
root=bpy.data.objects['Lower | circular roof assembly']
target=root.matrix_world.translation+Vector((0,0,.82))
d=bpy.data.cameras.new('Inter-platform inspection')
cam=bpy.data.objects.new(d.name,d);S.collection.objects.link(cam)
cam.location=target+Vector((-8,-3.44,2.8))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
d.lens=44;S.camera=cam
S.render.engine='CYCLES';S.cycles.samples=20;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1200;S.render.resolution_y=840;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False
S.render.image_settings.file_format='PNG';S.render.filepath=str(P/('before.png' if '--before' in sys.argv else 'after.png'))
bpy.ops.render.render(write_still=True)
