"""Capture the simplified platform surrounds without changing the scene camera."""
import bpy
from pathlib import Path
from mathutils import Vector, Quaternion
P=Path(__file__).resolve().parent
s=bpy.context.scene
win=next(w for w in bpy.context.window_manager.windows if any(a.type=='VIEW_3D' for a in w.screen.areas))
a=next(a for a in win.screen.areas if a.type=='VIEW_3D')
r=next(r for r in a.regions if r.type=='WINDOW')
space=a.spaces.active;v=space.region_3d
settings=(s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format)
view=(v.view_location.copy(),v.view_rotation.copy(),v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays)
try:
    d=bpy.data.objects['Upper | beveled square gallery']
    v.view_location=d.matrix_world@Vector((0,-.6,10.5))
    v.view_rotation=(d.matrix_world.to_3x3()@Vector((-.98,-.12,.14))).to_track_quat('Z','Y')
    v.view_distance=15
    v.view_perspective='PERSP';v.update()
    s.render.resolution_x=1100;s.render.resolution_y=1000;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'
    for mode,filename,overlays in [('WIREFRAME','after-wire.png',True),('MATERIAL','after-material.png',False)]:
        space.shading.type=mode;space.overlay.show_overlays=overlays
        s.render.filepath=str(P/filename)
        with bpy.context.temp_override(window=win,area=a,region=r):
            bpy.ops.render.opengl(write_still=True,view_context=True)
finally:
    s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format=settings
    v.view_location,v.view_rotation,v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays=view
    v.update()
result={'wire':str(P/'after-wire.png'),'material':str(P/'after-material.png')}
