import bpy
from mathutils import Vector
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/terrain-shading-fix')
for side in [-1,1]:
    o=bpy.data.objects[f'RL | Cave | lower reflected bounce {side:+d}']
    o.location=(side*6.,-12.,4.)
    target=Vector((side*4.,1.,3.5))
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.size=10.
    o['Base power (W)']=500.
    o.data.specular_factor=.15
    o['Lighting role']='Wide camera-side rock bounce, below the decks, to soften abrupt shelf shadows without washing out the platforms.'
bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-02.blend'),copy=True,compress=True)
s=bpy.context.scene
s.render.filepath=str(P/'candidate-02.png')
bpy.ops.render.render(write_still=True)
