import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'cave-platform-sliders.blend'))
c=bpy.data.objects['SCENE SLIDERS'];m=c.modifiers['Scene Sliders'];ids={x.name:x.identifier for x in m.node_group.interface.items_tree if x.item_type=='SOCKET' and x.in_out=='INPUT'}
def update():c.update_tag();bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
update()
lower=bpy.data.objects['Lower | plain octagon'];old=m[ids['Lower radius (m)']]
m[ids['Lower radius (m)']]=old*1.2;update();measured=lower.scale.x
assert abs(measured-1.2)<1e-5,measured
m[ids['Lower radius (m)']]=old;update()
invalid=[(o.name,f.data_path) for o in bpy.context.scene.objects if o.animation_data for f in o.animation_data.drivers if not f.driver.is_valid]
assert not invalid,invalid
print('REOPEN_CHECK',json.dumps({'radius_slider_after_reload':measured,'invalid_drivers':invalid,'python_autorun_enabled':bpy.context.preferences.filepaths.use_scripts_auto_execute,'pinned_panel':[a.spaces.active.context for sc in bpy.data.screens for a in sc.areas if a.type=='PROPERTIES']}),flush=True)
