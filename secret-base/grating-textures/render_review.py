"""Render the live camera and detail views in a disposable background process."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
label = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'after'
S = bpy.context.scene
S.render.engine = 'CYCLES'
S.cycles.device = 'CPU'
S.cycles.samples = 32 if '--scene-only' in sys.argv else 20
S.cycles.use_denoising = True
S.render.resolution_x = 1400
S.render.resolution_y = 1100
S.render.resolution_percentage = 100
S.render.use_border = False
S.render.image_settings.file_format = 'PNG'
if '--details' not in sys.argv:
    S.render.filepath = str(P / (label + '-scene.png'))
    bpy.ops.render.render(write_still=True)
cam = S.camera.copy()
cam.data = S.camera.data.copy()
S.collection.objects.link(cam)
S.camera = cam
cam.data.type = 'ORTHO'
center = bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy()
center.z = 6.87
views = [('center', center + Vector((3, -5, 9)), center, 8.7)]
names = [o for o in S.objects if o.visible_get() and o.name.startswith('Left stairs |') and 'open grating' in o.name]
pts = [o.matrix_world @ Vector(p) for o in names for p in o.bound_box]
target = Vector(tuple((min(p[a] for p in pts)+max(p[a] for p in pts))/2 for a in range(3)))
views.append(('stairs', target+Vector((1,-7,8)), target, 8.0))
if '--scene-only' in sys.argv:
    views=[]
for name, eye, target, scale in views:
    cam.location = eye
    cam.rotation_euler = (target-eye).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale = scale
    S.render.filepath = str(P / (label+'-'+name+'.png'))
    bpy.ops.render.render(write_still=True)
