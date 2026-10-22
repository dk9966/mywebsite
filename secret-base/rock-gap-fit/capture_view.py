import bpy
from pathlib import Path
from mathutils import Vector
P = Path(__file__).resolve().parent
s = bpy.context.scene
win = next(w for w in bpy.context.window_manager.windows if any(a.type == 'VIEW_3D' for a in w.screen.areas))
a = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
r = next(r for r in a.regions if r.type == 'WINDOW')
old = (s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage, s.render.filepath, s.render.image_settings.file_format, a.spaces.active.overlay.show_overlays)
v=a.spaces.active.region_3d
view_old=(v.view_location.copy(),v.view_rotation.copy(),v.view_distance,v.view_perspective)
try:
    if globals().get('INSPECT',False):
        deck=bpy.data.objects['Upper | beveled square gallery']
        v.view_location=deck.matrix_world@Vector((0,-.6,10.9))
        v.view_rotation=(deck.matrix_world.to_3x3()@Vector(globals().get('DIRECTION',(-.98,-.12,.14)))).to_track_quat('Z','Y')
        v.view_distance=10.5
        v.view_perspective='PERSP'
        v.update()
    s.render.resolution_x = 1100
    s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.filepath = str(P / globals().get('IMAGE_NAME', 'after.png'))
    s.render.image_settings.file_format = 'PNG'
    a.spaces.active.overlay.show_overlays = False
    with bpy.context.temp_override(window=win, area=a, region=r):
        bpy.ops.render.opengl(write_still=True, view_context=True)
finally:
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage, s.render.filepath, s.render.image_settings.file_format, a.spaces.active.overlay.show_overlays = old
    v.view_location,v.view_rotation,v.view_distance,v.view_perspective=view_old
    v.update()
result = {'image': str(P / globals().get('IMAGE_NAME', 'after.png'))}
