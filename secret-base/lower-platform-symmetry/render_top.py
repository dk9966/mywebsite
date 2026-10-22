"""Render the saved floor in isolation without altering the live scene."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix

P = Path('/Users/danielku/mywebsite/secret-base/lower-platform-symmetry')
S = bpy.context.scene
report = json.loads((P/'verification.json').read_text())
cx,cy = report['center_room']
frame = Matrix.Translation((21.299999237,0,0)) @ Matrix.Rotation(-math.atan2(12,19),4,'Z')
prefixes = ('Lower | fitted turntable surface','Lower | fitted brass registration band',
            'Lower | fitted inner metal rim','Lower | fitted outer recessed channel',
            'Lower | fitted broad perimeter apron','Lower | fitted outer circle',
            'Lower | fitted perimeter groove','Lower | fitted center disc',
            'Lower | fitted radial turntable seam','Lower | registration band fastener',
            'Lower | symmetric outer deck seam')
for o in S.objects:
    o.hide_render = not (o.name == 'Lower | plain octagon' or o.name.startswith(prefixes))
data = bpy.data.cameras.new('Symmetry inspection')
camera = bpy.data.objects.new('Symmetry inspection',data)
S.collection.objects.link(camera)
camera.matrix_world = frame @ Matrix.Translation((cx,cy,report['floor_height']+15))
data.type = 'ORTHO'
data.ortho_scale = 8.2
S.camera = camera
S.render.engine = 'BLENDER_WORKBENCH'
S.display.shading.light = 'STUDIO'
S.display.shading.studiolight_rotate_z = .4
S.display.shading.color_type = 'MATERIAL'
S.display.shading.show_shadows = False
S.display.shading.show_cavity = True
S.display.shading.cavity_type = 'BOTH'
S.display.shading.background_type = 'WORLD'
S.world.color = (.025,.025,.025)
S.render.resolution_x = 1200
S.render.resolution_y = 1200
S.render.resolution_percentage = 100
S.render.use_border = False
S.render.use_crop_to_border = False
S.render.image_settings.file_format = 'PNG'
S.render.filepath = str(P/'top-down-symmetry.png')
bpy.ops.render.render(write_still=True)
