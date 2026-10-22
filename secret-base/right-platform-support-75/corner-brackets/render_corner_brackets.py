import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;S=bpy.context.scene
F=Matrix(json.loads((P.parent/'surface-before.json').read_text())['frame']);IV=F.inverted()

from bpy_extras.object_utils import world_to_camera_view
S.camera=bpy.data.objects['150 | main cave camera'];S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=2200;S.render.resolution_y=1500;S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG'
points=[F@Vector((x,y,z)) for x in [4.3,11.8] for y in [-6.7,.2] for z in [4.1,7.5]]
coords=[world_to_camera_view(S,S.camera,v) for v in points]
S.render.use_border=True;S.render.use_crop_to_border=True
S.render.border_min_x=max(0,min(v.x for v in coords)-.025);S.render.border_max_x=min(1,max(v.x for v in coords)+.025)
S.render.border_min_y=max(0,min(v.y for v in coords)-.025);S.render.border_max_y=min(1,max(v.y for v in coords)+.025)
S.render.filepath=str(P/'main-camera-corner-brackets.png');bpy.ops.render.render(write_still=True)

for o in S.objects:
 if o.type=='MESH' and not(o.name.startswith(('Lower |','Lower right |','Workshop |')) or o.name=='150 | continuous cave with oblique carved rooms'):o.hide_render=True
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev);r.data=me
for m in list(r.modifiers):r.modifiers.remove(m)
bm=bmesh.new();bm.from_mesh(me);mx=IV@r.matrix_world
remove=[v for v in bm.verts if not(3<(mx@v.co).x<14 and -8<(mx@v.co).y<2.7 and -.5<(mx@v.co).z<10)]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(me);bm.free()
S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True;S.cycles.device='CPU';S.render.resolution_x=1280;S.render.resolution_y=960;S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Right foundation inspection');cam=bpy.data.objects.new(cd.name,cd);S.collection.objects.link(cam);S.camera=cam;cd.type='ORTHO';cd.ortho_scale=11.5
target=F@Vector((8,-3.2,4.6));cam.location=F@Vector((-.5,-14,10));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for i,(xyz,energy,size) in enumerate([((3,-11,10),2400,9),((14,-8,8),1800,7),((5,2,6),900,6)]):
 ld=bpy.data.lights.new('Inspection softbox %d'%i,'AREA');lo=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(lo);lo.location=F@Vector(xyz);lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=energy;ld.shape='DISK';ld.size=size
S.render.filepath=str(P/'corner-brackets-inspection.png');bpy.ops.render.render(write_still=True)
cam.location=F@Vector((0,-9,6.6));target=F@Vector((8,-3,5.0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=10.3
S.render.filepath=str(P/'corner-brackets-underside.png');bpy.ops.render.render(write_still=True)
