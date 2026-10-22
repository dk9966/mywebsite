import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
F=Matrix(json.loads((P/'layout-before.json').read_text())['frame'])
S.render.engine='CYCLES';S.cycles.samples=12;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1200;S.render.resolution_y=1100;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
# Temporary local rock cutaway removes the foreground cave rim for inspection.
w=bpy.data.objects['150 | continuous cave with oblique carved rooms'];e=w.evaluated_get(bpy.context.evaluated_depsgraph_get());w.data=bpy.data.meshes.new_from_object(e)
for m in list(w.modifiers):w.modifiers.remove(m)
bm=bmesh.new();bm.from_mesh(w.data);mx=F.inverted()@w.matrix_world
remove=[v for v in bm.verts if not(-5.3<(mx@v.co).x<6.2 and -5.9<(mx@v.co).y<6.2 and 5.2<(mx@v.co).z<14.8)]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(w.data);bm.free()
# Match the original camera's azimuth.
cam=bpy.data.objects['150 | main cave camera'];d=cam.data.copy();c=bpy.data.objects.new('Upper right | inspection camera',d);S.collection.objects.link(c)
S.camera=c;c.rotation_euler=cam.rotation_euler;d.type='ORTHO';d.ortho_scale=11.7;d.clip_start=.1
q=c.rotation_euler.to_quaternion();target=F@Vector((-.3,-.3,9.8));c.location=target+q@Vector((0,0,24))
# Broad temporary photographic fills, present only in this background process.
for i,(xyz,power,size) in enumerate([((-5,-7,16),2400,9),((-4,3,16),1700,7)]):
 ld=bpy.data.lights.new('Inspection fill '+str(i),'AREA');o=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(o);o.location=F@Vector(xyz);o.rotation_euler=(F@Vector((0,0,10))-o.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size;ld.color=(.73,.84,1)
S.render.filepath=str(P/(sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'inspection.png'))
bpy.ops.render.render(write_still=True)
