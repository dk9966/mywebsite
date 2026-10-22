"""Inspection-only renders from a saved copy; never saves isolation/camera changes."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent;S=bpy.context.scene
F=Matrix(json.loads((P/'verification.json').read_text())['frame']);iv=F.inverted()
for o in S.objects:
    if o.type=='MESH' and not (o.name.startswith(('Left bay |','Left platform |','Left stairs |','Front left |')) or o.name=='150 | continuous cave with oblique carved rooms'):
        o.hide_render=True
    if o.type=='LIGHT' and not o.name.startswith('Left bay |'):o.hide_render=True
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ev=rock.evaluated_get(bpy.context.evaluated_depsgraph_get());rock.data=bpy.data.meshes.new_from_object(ev)
for mod in list(rock.modifiers):rock.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(rock.data);mx=iv@rock.matrix_world
remove=[v for v in bm.verts if not(-6<(mx@v.co).x<7 and -2.7<(mx@v.co).y<14.8 and -3.5<(mx@v.co).z<9.3)]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(rock.data);bm.free()
S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True;S.cycles.device='CPU'
S.render.resolution_x=1100;S.render.resolution_y=850;S.render.resolution_percentage=100
S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
camd=bpy.data.cameras.new('Left bay inspection');cam=bpy.data.objects.new(camd.name,camd);S.collection.objects.link(cam);S.camera=cam;camd.type='ORTHO';camd.ortho_scale=17.3
target=F@Vector((1.8,6.4,3.85))
for i,(xyz,power,size,color) in enumerate([((9,-2,11),2200,9,(.72,.84,1)),((7,11,9),1800,8,(.63,.78,1)),((4,5,7),500,6,(1,.80,.60))]):
    ld=bpy.data.lights.new('Inspection area %d'%i,'AREA');lo=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(lo);lo.location=F@Vector(xyz)
    lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.shape='DISK';ld.size=size;ld.color=color
for label,xyz,scale in [('perspective',(18,-7,13),17.4),('top',(3,6.8,25),16.0),('support-detail',(8,-2,6.8),7.0)]:
    if label=='support-detail':continue
    rock.hide_render=label=='top'
    if label=='support-detail':target=F@Vector((.3,2.5,4.6))
    elif label=='top':target=F@Vector((3,6.8,2.54))
    cam.location=F@Vector(xyz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale
    if label=='top':
        cam.rotation_euler=(F.to_quaternion() @ Quaternion((0,0,1),math.pi/2)).to_euler()
    S.render.filepath=str(P/(label+'.png'));bpy.ops.render.render(write_still=True)
