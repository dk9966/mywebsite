import bpy,json
from mathutils import Matrix,Vector
from pathlib import Path
P=Path(__file__).resolve().parent
S=bpy.context.scene
f=Matrix(json.loads((P/'surface-before.json').read_text())['frame'])
S.render.engine='CYCLES';S.cycles.samples=20;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1440;S.render.resolution_y=1080;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False
S.render.image_settings.file_format='PNG'
camd=bpy.data.cameras.new('Left support inspection');cam=bpy.data.objects.new(camd.name,camd);S.collection.objects.link(cam)
target=f@Vector((2.5,4.1,.6));cam.location=f@Vector((17,-12,11))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=16.2;S.camera=cam
for i,(xyz,energy,size) in enumerate([((9,-6,10),2100,9),((9,8,7),1400,8),((4,2,-2),350,5)]):
    ld=bpy.data.lights.new('Inspection softbox %d'%i,'AREA');lo=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(lo)
    lo.location=f@Vector(xyz);lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=energy;ld.shape='DISK';ld.size=size
S.render.filepath=str(P/'left-support-detail.png');bpy.ops.render.render(write_still=True)
cam.location=f@Vector((16,4.5,5.4));target=f@Vector((2.7,5.5,.6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=16.6
S.render.filepath=str(P/'left-support-side.png');bpy.ops.render.render(write_still=True)
