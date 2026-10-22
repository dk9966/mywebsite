import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
S.render.engine='CYCLES';S.cycles.device='CPU';S.cycles.samples=16;S.cycles.use_denoising=True
S.render.resolution_x=900;S.render.resolution_y=700;S.render.resolution_percentage=100;S.render.use_border=False
S.render.image_settings.file_format='PNG'
root=bpy.data.objects['Right half bridge | radial assembly']
target=root.matrix_world@Vector((4.6,0,6.90))
eye=root.matrix_world@Vector((4.0,-4.4,10.6))
cam=S.camera.copy();cam.data=S.camera.data.copy();S.collection.objects.link(cam);S.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=4.5;cam.location=eye;cam.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler()
light=bpy.data.lights.new('Inspection softbox','AREA');light.energy=400;light.shape='DISK';light.size=4
ob=bpy.data.objects.new('Inspection softbox',light);S.collection.objects.link(ob);ob.location=target+Vector((0,-2,4));ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
S.render.filepath=str(P/'textured-half-bridge.png');bpy.ops.render.render(write_still=True)
