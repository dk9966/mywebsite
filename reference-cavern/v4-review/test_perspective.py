import bpy,math
from mathutils import Vector
R='/Users/danielku/mywebsite/reference-cavern/v4-review'
bpy.ops.wm.open_mainfile(filepath=R+'/pass-08.blend');s=bpy.context.scene
s.camera.location=(0,-31.48,22.66);s.camera.rotation_euler.x=math.radians(69.5);s.camera.data.type='PERSP';s.camera.data.lens=29.27;s.camera.data.sensor_width=36;s.camera.data.sensor_fit='HORIZONTAL'
s.render.filepath=R+'/pass-09.png'
bpy.ops.wm.save_as_mainfile(filepath=R+'/pass-09.blend');bpy.ops.render.render(write_still=True)
