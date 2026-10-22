"""Inspection render in a background Blender process; no scene save."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent
S=bpy.context.scene
deck=bpy.data.objects['Upper | beveled square gallery'];F=deck.matrix_world;H=deck['deck_height_m']
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1500;S.render.resolution_y=1000;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False
S.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('Gallery inspection');cam=bpy.data.objects.new('Gallery inspection',data)
S.collection.objects.link(cam);S.camera=cam
data.type='PERSP';data.lens=42
# Camera looks into all four wall planes, from the same open edge as the user's reference.
target=F@Vector((.35,.4,H+1.0));cam.location=F@Vector((-11.0,-5.0,H+6.2))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
# Broad inspection fill makes the roof's connection visible without altering the saved scene.
ld=bpy.data.lights.new('Temporary inspection fill','AREA');lo=bpy.data.objects.new(ld.name,ld)
S.collection.objects.link(lo);ld.energy=850;ld.shape='DISK';ld.size=7
lo.location=F@Vector((-3,-3,H+7));lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
if '--base' in sys.argv:
    target=F@Vector((.12,2.70,H+.42));cam.location=F@Vector((-1.25,-.6,H+1.40));data.lens=62
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    S.render.resolution_x=1200;S.render.resolution_y=1000
    S.render.filepath=str(P/'support-base-detail.png')
else:
    S.render.filepath=str(P/'completed-gallery.png')
bpy.ops.render.render(write_still=True)
