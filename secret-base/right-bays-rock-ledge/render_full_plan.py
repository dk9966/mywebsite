"""Render the entire connected cave contour without modifying the saved scene."""
import math
from pathlib import Path
import bpy
from mathutils import Matrix

folder=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(folder/'rock-ledge-bays.blend'))
scene=bpy.context.scene
frame=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
camera=bpy.data.objects.new('Full cave plan inspection',bpy.data.cameras.new('Full cave plan inspection'))
scene.collection.objects.link(camera)
camera.matrix_world=frame@Matrix.Translation((1,-5,40))
camera.data.type='ORTHO';camera.data.ortho_scale=39;camera.data.clip_end=150
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
for obj in scene.objects:
    if 'Atmosphere' in obj.name:obj.hide_render=True
scene.render.filepath=str(folder/'rock-ledge-bays-full-plan.png')
bpy.ops.render.render(write_still=True)
