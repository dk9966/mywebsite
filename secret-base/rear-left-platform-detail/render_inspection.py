"""Temporary inspection lighting and rock cutaway, never saved to the scene."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;S=bpy.context.scene
F=Matrix(json.loads((P/'verification.json').read_text())['frame']);iv=F.inverted()
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
for o in S.objects:
    if o.type=='LIGHT':o.hide_render=True
    if o.type=='MESH' and not (o.name.startswith(('Rear left |','Metal |','Rail |','Support |')) or o==rock):o.hide_render=True
e=rock.evaluated_get(bpy.context.evaluated_depsgraph_get());rock.data=bpy.data.meshes.new_from_object(e)
for mod in list(rock.modifiers):rock.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(rock.data);mx=iv@rock.matrix_world
remove=[v for v in bm.verts if not(-6<(mx@v.co).x<6 and -8.3<(mx@v.co).y<9.5 and 2.5<(mx@v.co).z<11.2)]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(rock.data);bm.free()
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1400;S.render.resolution_y=1100;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
S.world.color=(.12,.12,.12)
for i,(xyz,power,size,color) in enumerate([((0,-4,16),2000,9,(.75,.85,1)),((-7,3,12),1700,7,(.65,.79,1)),((4,6,13),1500,6,(1,.86,.70))]):
    ld=bpy.data.lights.new('Review area %d'%i,'AREA');o=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(o);o.location=F@Vector(xyz);o.rotation_euler=(F@Vector((0,1,7.5))-o.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size;ld.color=color
d=bpy.data.cameras.new('Rear left review');c=bpy.data.objects.new(d.name,d);S.collection.objects.link(c);S.camera=c;d.type='ORTHO'
views=[('perspective',(10,-15,17),(0,.5,7.2),14.5),('top',(0,0,28),(0,0,7),19.0),('junction',(7,-10,13),(0,-3,6.9),9.5)]
if '--quick' in sys.argv:
    views=views[:1];S.cycles.samples=12;S.render.resolution_x=1100;S.render.resolution_y=900
for name,eye,target,scale in views:
    rock.hide_render=name=='top';c.location=F@Vector(eye);c.rotation_euler=(F@Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale
    S.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
