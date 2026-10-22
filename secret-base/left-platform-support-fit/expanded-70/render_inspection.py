import bpy,bmesh,json
from mathutils import Matrix,Vector
from pathlib import Path
Q=Path(__file__).resolve().parent;P=Q.parent;S=bpy.context.scene
f=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);iv=f.inverted()
# Inspection-only isolation; this background process never saves scene changes.
for o in S.objects:
 if o.type=='MESH' and not (o.name.startswith(('Left platform |','Left stairs |')) or o.name in ['Front left | beveled rectangle landing','150 | continuous cave with oblique carved rooms']):o.hide_render=True
r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev);r.data=me
for m in list(r.modifiers):r.modifiers.remove(m)
bm=bmesh.new();bm.from_mesh(me);mx=iv@r.matrix_world
remove=[v for v in bm.verts if not(-5<(mx@v.co).x<5.4 and -3<(mx@v.co).y<15 and -5.5<(mx@v.co).z<9)]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(me);bm.free()
S.render.engine='CYCLES';S.cycles.samples=28;S.cycles.use_denoising=True;S.cycles.device='CPU';S.render.resolution_x=1600;S.render.resolution_y=1200;S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
camd=bpy.data.cameras.new('Left support inspection');cam=bpy.data.objects.new(camd.name,camd);S.collection.objects.link(cam);S.camera=cam
camd.type='ORTHO';camd.ortho_scale=16.3
target=f@Vector((2.4,5.6,1.0));cam.location=f@Vector((16,-9,10));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for i,(xyz,energy,size) in enumerate([((10,-5,10),2500,10),((9,10,7),2200,8),((8,4,-.5),500,6)]):
 ld=bpy.data.lights.new('Inspection softbox %d'%i,'AREA');lo=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(lo);lo.location=f@Vector(xyz);lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=energy;ld.shape='DISK';ld.size=size
S.render.filepath=str(Q/'expanded-platform-inspection.png');bpy.ops.render.render(write_still=True)
cam.location=f@Vector((18,4.5,4.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=15.8
S.render.filepath=str(Q/'expanded-platform-underside.png');bpy.ops.render.render(write_still=True)
