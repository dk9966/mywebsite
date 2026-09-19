"""Render an oblique geometry inspection without changing the saved comparison camera."""
import bpy,os,json
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'cavern-portfolio.blend'))
S=bpy.context.scene;canonical=S.camera
cam=bpy.data.cameras.new('QA | oblique perspective');o=bpy.data.objects.new('QA | oblique perspective',cam);S.collection.objects.link(o)
o.location=(18,-37,24);o.rotation_euler=(Vector((0,7,8))-o.location).to_track_quat('-Z','Y').to_euler();cam.lens=38
S.camera=o;S.render.resolution_x=1280;S.render.resolution_y=720;S.cycles.samples=24;S.render.filepath=os.path.join(ROOT,'renders','qa-oblique.png')
bpy.ops.render.render(write_still=True)
S.camera=canonical
assert canonical.name.startswith('CAMERA | Reference')
print('QA: oblique render complete; comparison camera in saved .blend was not altered.')
