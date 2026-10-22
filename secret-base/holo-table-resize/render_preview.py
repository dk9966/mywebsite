"""Render the actual refined meshes in an isolated neutral review scene."""
import bpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
with bpy.data.libraries.load(str(P.parent/'platform-controls/cave-platform-sliders.blend'),link=False) as (src,dst):
    dst.collections=['175 | Lower bay holo table']
COL=dst.collections[0];S.collection.children.link(COL)
origin=bpy.data.objects['Holo table | floor plinth'].location.copy()
for o in COL.objects:o.location-=origin
S.render.engine='CYCLES';S.cycles.samples=16;S.cycles.use_denoising=True
S.render.resolution_x=900;S.render.resolution_y=675;S.render.resolution_percentage=100
S.world=bpy.data.worlds.new('Review studio world');S.world.use_nodes=True
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.13,.19,1)
S.world.node_tree.nodes['Background'].inputs[1].default_value=.45
S.view_settings.view_transform='AgX'

def area(name,where,power,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=where
    o.rotation_euler=(Vector((0,0,.2))-o.location).to_track_quat('-Z','Y').to_euler()
area('Large softbox',(-3,-4,5),420,5,(.78,.86,1))
area('Rim softbox',(1.5,3,4),550,3,(.30,.65,1))
area('Soft neutral fill',(4,-1,2.5),190,4,(1,.86,.75))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006))
floor=bpy.context.object;floor.name='Review ground'
m=bpy.data.materials.new('Review ground');m.use_nodes=True
bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.022,.031,.048,1)
bs.inputs['Roughness'].default_value=.52;bs.inputs['Metallic'].default_value=.2
floor.data.materials.append(m)
d=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',d)
S.collection.objects.link(cam);S.camera=cam;d.type='ORTHO';d.ortho_scale=4.2
for filename,eye,target in [('table-preview.png',(1.5,-3.7,2.65),(0,0,.12)),
                             ('rim-profile.png',(1.0,-4,1.5),(0,0,.15))]:
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    S.render.filepath=str(P/filename)
    bpy.ops.render.render(write_still=True)
