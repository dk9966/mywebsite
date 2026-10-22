import bpy
from pathlib import Path
from mathutils import Vector, Quaternion

P = Path(__file__).resolve().parent
s = bpy.context.scene
w = bpy.data.objects['150 | continuous cave with oblique carved rooms']
win = bpy.context.window
a = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
r = next(r for r in a.regions if r.type == 'WINDOW')
space = a.spaces.active
v = space.region_3d
render = (s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage,
          s.render.filepath, s.render.image_settings.file_format)
view = (v.view_location.copy(), v.view_rotation.copy(), v.view_distance,
        v.view_perspective, space.shading.type, space.overlay.show_overlays)
repairs = [m for m in w.modifiers if m.name.startswith(('Seam repair |', 'Surround repair |'))]
repair_states = [m.show_viewport for m in repairs]
try:
    deck = bpy.data.objects['Upper | beveled square gallery']
    v.view_location = deck.matrix_world @ Vector((0, -1.1, 11.5))
    v.view_rotation = (deck.matrix_world.to_3x3() @ Vector((-.98,-.12,.14))).to_track_quat('Z','Y')
    v.view_distance = 13
    v.view_perspective = 'PERSP'
    space.shading.type = 'SOLID'
    space.overlay.show_overlays = False
    s.render.resolution_x = 1200
    s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    for enabled, name in [(False, 'before'), (True, 'after')]:
        for m, state in zip(repairs, repair_states):
            m.show_viewport = enabled and state
        bpy.context.view_layer.update()
        v.update()
        s.render.filepath = str(P / (name + '.png'))
        with bpy.context.temp_override(window=win, area=a, region=r):
            bpy.ops.render.opengl(write_still=True, view_context=True)
finally:
    for m, state in zip(repairs, repair_states):
        m.show_viewport = state
    (s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage,
     s.render.filepath, s.render.image_settings.file_format) = render
    (v.view_location, v.view_rotation, v.view_distance,
     v.view_perspective, space.shading.type, space.overlay.show_overlays) = view
    v.update()
result = {'before': str(P / 'before.png'), 'after': str(P / 'after.png')}
