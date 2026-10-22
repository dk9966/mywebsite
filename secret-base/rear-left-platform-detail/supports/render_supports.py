"""Inspection renders only; no lighting/visibility changes are saved."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;S=bpy.context.scene
F=Matrix(json.loads((P/'verification.json').read_text())['frame']);IV=F.inverted()
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
for o in S.objects:
 if o.type=='LIGHT':o.hide_render=True
 if o.type=='MESH' and not (o.name.startswith(('Rear left |','Rear support |')) or o==rock):o.hide_render=True
e=rock.evaluated_get(bpy.context.evaluated_depsgraph_get());rock.data=bpy.data.meshes.new_from_object(e)
for mod in list(rock.modifiers):rock.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(rock.data);mx=IV@rock.matrix_world
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not(-5<(mx@v.co).x<5 and -5<(mx@v.co).y<8 and 2<(mx@v.co).z<11)],context='VERTS');bm.to_mesh(rock.data);bm.free()
S.render.engine='CYCLES';S.cycles.samples=20;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1200;S.render.resolution_y=1000;S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
for i,(xyz,power,size,color) in enumerate([((3,-8,11),1800,7,(.76,.86,1)),((-5,-4,7),1400,6,(.70,.82,1)),((4,1,11),1600,5,(1,.88,.74))]):
 ld=bpy.data.lights.new('Support review light','AREA');o=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(o);o.location=F@Vector(xyz);o.rotation_euler=(F@Vector((0,-1.5,5.5))-o.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size;ld.color=color
d=bpy.data.cameras.new('Support inspection');c=bpy.data.objects.new(d.name,d);S.collection.objects.link(c);S.camera=c;d.type='ORTHO'
for label,eye,target,scale in [('support-detail',(8,-12,7.9),(0,-2.2,5.75),6.9),('supported-platform',(9,-14,14),(0,.5,6.8),12.5)]:
 c.location=F@Vector(eye);c.rotation_euler=(F@Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale;S.render.filepath=str(P/(label+'.png'));bpy.ops.render.render(write_still=True)
