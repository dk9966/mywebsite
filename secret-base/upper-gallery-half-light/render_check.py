"""Render only for inspection; never save temporary presentation changes."""
import bpy, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
deck=bpy.data.objects['Upper | beveled square gallery'];F=deck.matrix_world;H=deck['deck_height_m']
S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1200;S.render.resolution_y=900;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('Temporary gallery review');cam=bpy.data.objects.new(data.name,data)
S.collection.objects.link(cam);S.camera=cam;data.type='PERSP';data.lens=44
target=F@Vector((.3,0,H+1.1));cam.location=F@Vector((-8.5,-3,H+2.4));data.lens=32
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
ld=bpy.data.lights.new('Temporary gallery inspection fill','AREA');lo=bpy.data.objects.new(ld.name,ld)
S.collection.objects.link(lo);ld.energy=850;ld.shape='DISK';ld.size=7
lo.location=F@Vector((-3,-3,H+7));lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
if '--cutaway' in sys.argv:
    cam.location=F@Vector((-11,-4,H+6.3));data.lens=44
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    allowed={o.name for o in bpy.data.collections['173 | Upper gallery architecture'].all_objects}
    allowed.update(o.name for o in bpy.data.collections['171 | Upper right square gallery'].all_objects)
    allowed.add(deck.name)
    for o in S.objects:
        if o.type=='MESH' and o.name not in allowed:o.hide_render=True
    S.render.filepath=str(P/'half-light-cutaway.png')
else:
    S.render.filepath=str(P/'half-light-review.png')
bpy.ops.render.render(write_still=True)
