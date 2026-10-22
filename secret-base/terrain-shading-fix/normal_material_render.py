import bpy
from pathlib import Path
P=Path('/Users/danielku/mywebsite/secret-base/terrain-shading-fix')
s=bpy.context.scene
s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1100;s.render.resolution_y=616;s.render.resolution_percentage=100
s.render.use_border=False;s.render.use_crop_to_border=False;s.render.image_settings.file_format='PNG'
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
wall.data.flip_normals();wall.data.update()
s.render.filepath=str(P/'normals-corrected.png');bpy.ops.render.render(write_still=True)
for o in [wall,bpy.data.objects['Central rock mound | continuous cross-column extrusions']]:
    nt=o.data.materials[0].node_tree
    nt.nodes['Weathered broad relief'].inputs['Strength'].default_value=.16
    nt.nodes['Weathered broad relief'].inputs['Distance'].default_value=.045
    nt.nodes['Subtle stone grain'].inputs['Strength'].default_value=.12
    nt.nodes['Subtle stone grain'].inputs['Distance'].default_value=.008
    nt.nodes['Matte charcoal slate'].inputs['Roughness'].default_value=.90
    nt.nodes['Matte charcoal slate'].inputs['Specular IOR Level'].default_value=.18
for m in bpy.data.materials:
    if m.name.startswith('RL mist | '):
        scale=.22 if m.name in ['RL mist | Center','RL mist | Front left'] else .6
        for fc in m.node_tree.animation_data.drivers:
            fc.driver.expression='('+fc.driver.expression+')*'+str(scale)
s.frame_set(s.frame_current);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate-01.blend'),copy=True,compress=True)
s.render.filepath=str(P/'candidate-01.png');bpy.ops.render.render(write_still=True)
