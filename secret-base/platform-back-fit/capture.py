import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
s=bpy.context.scene;win=bpy.context.window
a=next(a for a in win.screen.areas if a.type=='VIEW_3D')
r=next(r for r in a.regions if r.type=='WINDOW')
space=a.spaces.active;v=space.region_3d
d=bpy.data.objects['Upper | beveled square gallery']
view=(v.view_location.copy(),v.view_rotation.copy(),v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays)
render=(s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format)
try:
    v.view_location=d.matrix_world@Vector((0,-.8,10.4))
    v.view_rotation=(d.matrix_world.to_3x3()@Vector((-.98,-.12,.14))).to_track_quat('Z','Y')
    v.view_distance=15;v.view_perspective='PERSP';v.update()
    s.render.resolution_x=1100;s.render.resolution_y=1000;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';space.overlay.show_overlays=False
    for mode in ['SOLID','WIREFRAME']:
        space.shading.type=mode;s.render.filepath=str(P/('after-'+mode.lower()+'.png'))
        with bpy.context.temp_override(window=win,area=a,region=r):
            bpy.ops.render.opengl(write_still=True,view_context=True)
finally:
    s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format=render
    v.view_location,v.view_rotation,v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays=view
    v.update()
result={'solid':str(P/'after-solid.png'),'wire':str(P/'after-wireframe.png')}
