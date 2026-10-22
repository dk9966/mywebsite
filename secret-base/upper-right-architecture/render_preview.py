"""Render previews in a background process; never save temporary settings."""
import bpy, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=2600;S.render.resolution_y=1456;S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG'
S.render.use_border=True;S.render.use_crop_to_border=True
S.render.border_min_x=.65;S.render.border_max_x=1.;S.render.border_min_y=.43;S.render.border_max_y=.99
S.camera=bpy.data.objects['150 | main cave camera']
S.render.filepath=str(P/'gallery-in-scene.png')
if '--detail' in sys.argv:
    S.render.use_border=False;S.render.use_crop_to_border=False
    S.render.resolution_x=1400;S.render.resolution_y=1000
    F=bpy.data.objects['Upper | beveled square gallery'].matrix_world
    H=bpy.data.objects['Upper | beveled square gallery']['deck_height_m']
    cam=S.camera;cam.data=cam.data.copy();cam.data.type='PERSP';cam.data.lens=31
    target=F@Vector((.0,.45,H+1.0));cam.location=F@Vector((-7.3,-10.9,H+5.8))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    S.render.filepath=str(P/'gallery-detail.png')
bpy.ops.render.render(write_still=True)
