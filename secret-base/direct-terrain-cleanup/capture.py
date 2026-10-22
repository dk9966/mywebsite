import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
s=bpy.context.scene
source=bpy.data.objects['150 | continuous cave with oblique carved rooms']
candidate=bpy.data.objects['Candidate | direct terrain cleanup']
deck=bpy.data.objects['Upper | beveled square gallery']
win=bpy.context.window;a=next(a for a in win.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
space=a.spaces.active;v=space.region_3d
view=(v.view_location.copy(),v.view_rotation.copy(),v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays,source.hide_get(),candidate.hide_get())
render=(s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format)
try:
    s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
    space.overlay.show_overlays=False
    for angle,vec in [('front',(-.98,-.12,.14)),('oblique',(-.8,-.5,.27))]:
        v.view_location=deck.matrix_world@Vector((0,-1.1,10.9))
        v.view_rotation=(deck.matrix_world.to_3x3()@Vector(vec)).to_track_quat('Z','Y');v.view_distance=13.5;v.view_perspective='PERSP';v.update()
        for after in (False,True):
            source.hide_set(after);candidate.hide_set(not after)
            space.shading.type='SOLID'
            s.render.filepath=str(P/(('after-' if after else 'before-')+angle+'.png'))
            bpy.context.view_layer.update()
            with bpy.context.temp_override(window=win,area=a,region=r):bpy.ops.render.opengl(write_still=True,view_context=True)
finally:
    s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format=render
    v.view_location,v.view_rotation,v.view_distance,v.view_perspective,space.shading.type,space.overlay.show_overlays,h1,h2=view
    source.hide_set(h1);candidate.hide_set(h2);v.update()
result={'front':str(P/'after-front.png'),'oblique':str(P/'after-oblique.png')}
