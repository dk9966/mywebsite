import bpy
import json
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/reference-lighting')
S = bpy.context.scene
ctrl = bpy.data.objects['LIGHTING CONTROLS']
mod = ctrl.modifiers['Reference Lighting']
ids = json.loads(ctrl['socket_ids'])
for socket in mod.node_group.interface.items_tree:
    if socket.name in ids and socket.in_out == 'INPUT':
        socket.default_value = mod[ids[socket.name]]
readme = bpy.data.texts.get('READ ME - Reference Lighting') or bpy.data.texts.new('READ ME - Reference Lighting')
readme.clear()
readme.write((P/'README.md').read_text())
for name in ['build_reference_lighting.py','refine_lighting.py','polish_lighting.py','finish_atmosphere.py','local_beam_mist.py','lift_environment.py']:
    text = bpy.data.texts.get('Reference lighting - '+name) or bpy.data.texts.new('Reference lighting - '+name)
    text.clear();text.write((P/name).read_text())

bpy.ops.object.select_all(action='DESELECT')
ctrl.select_set(True)
bpy.context.view_layer.objects.active = ctrl
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='PROPERTIES':
            area.spaces.active.pin_id=ctrl
            area.spaces.active.use_pin_id=True
            try:
                area.spaces.active.context='MODIFIER'
            except TypeError:
                pass
        elif area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.overlay.show_overlays=False
S.cycles.samples = 64
S.cycles.use_denoising = True
S.render.filepath = str(P/'final-camera.png')
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
settings={name:list(mod[key]) if name=='Cool light tint' else mod[key] for name,key in ids.items()}
report={'controls':settings,'lights':[{'name':o.name,'type':o.data.type,'power_w':o.data.energy,'base_power_w':o['Base power (W)'],'local_position':list(o.location),'parent':o.parent.name if o.parent else None} for o in bpy.data.collections['180 | Reference soft spotlight lighting'].objects if o.type=='LIGHT']}
(P/'final-lighting-settings.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P.parent/'platform-controls/cave-platform-sliders.blend'),compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'reference-soft-spotlights.blend'),copy=True,compress=True)
result={'saved':bpy.data.filepath,'lighting_copy':str(P/'reference-soft-spotlights.blend'),'controls':settings}
