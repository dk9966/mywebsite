"""Inspect roof top and the underside connection without saving render settings."""
import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
deck=bpy.data.objects['Upper | beveled square gallery'];F=deck.matrix_world;H=deck['deck_height_m']
S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1200;S.render.resolution_y=900;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
allowed={o.name for o in bpy.data.collections['173 | Upper gallery architecture'].all_objects}
allowed.update(o.name for o in bpy.data.collections['171 | Upper right square gallery'].all_objects)
allowed.add(deck.name)
for o in S.objects:
    if o.type=='MESH' and o.name not in allowed:o.hide_render=True
data=bpy.data.cameras.new('Temporary connection inspection');cam=bpy.data.objects.new(data.name,data)
S.collection.objects.link(cam);S.camera=cam;data.type='PERSP'
ld=bpy.data.lights.new('Temporary roof inspection fill','AREA');lo=bpy.data.objects.new(ld.name,ld)
S.collection.objects.link(lo);ld.energy=850;ld.shape='DISK';ld.size=7
lo.location=F@Vector((-3,-3,H+7));lo.rotation_euler=((F@Vector((.3,0,H+1.1)))-lo.location).to_track_quat('-Z','Y').to_euler()
for name,location,target,lens in [
    ('connected-roof-overview',(-9,-4,H+7.8),(.1,0,H+1.25),44),
    ('connected-roof-underside',(-4.8,-1.1,H+.65),(-.15,0,H+2.24),48),
]:
    cam.location=F@Vector(location);data.lens=lens
    cam.rotation_euler=((F@Vector(target))-cam.location).to_track_quat('-Z','Y').to_euler()
    if 'underside' in name:
        lo.location=F@Vector((-3,-1,H+.8));ld.energy=170;ld.size=3
        lo.rotation_euler=((F@Vector(target))-lo.location).to_track_quat('-Z','Y').to_euler()
    S.render.filepath=str(P/(name+'.png'))
    bpy.ops.render.render(write_still=True)
