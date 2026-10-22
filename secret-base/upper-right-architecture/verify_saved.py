"""Read-only verification in a separate Blender process after saving."""
import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ctrl=bpy.data.objects.get('UPPER PLATFORM SLIDERS') or bpy.data.objects['SCENE SLIDERS']
mod=ctrl.modifiers.get('Upper Platform Sliders') or ctrl.modifiers['Scene Sliders']
values={i.name:mod.get(i.identifier) for i in mod.node_group.interface.items_tree if i.name.startswith('Upper light')}
bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
root=bpy.data.objects['Upper light | adjustable fixture'];deck=bpy.data.objects['Upper | beveled square gallery']
assert abs(root.location.z-deck['deck_height_m']-values['Upper light height (m)'])<.001
light=bpy.data.lights['Upper light | rectangular downlight']
assert abs(light.size-values['Upper light width (m)']+.3)<.001
assert abs(light.size_y-values['Upper light depth (m)']+.3)<.001
archive=bpy.data.collections['Archive | upper gallery all-edge railings']
assert archive.hide_viewport and archive.hide_render
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
assert terrain.modifiers.get('Upper gallery | light and lining ceiling clearance')
bad=[]
for obj in bpy.data.collections['173 | Upper gallery architecture'].all_objects:
    owners=[obj,obj.data]+([obj.data.shape_keys] if obj.type=='MESH' and obj.data.shape_keys else [])
    for owner in owners:
        if owner and owner.animation_data:
            bad += [obj.name for fc in owner.animation_data.drivers if not fc.driver.is_valid]
assert not bad,bad
report={'saved_file':bpy.data.filepath,'controls':values,'invalid_drivers':bad,'native_controls_persist_after_reopen':True,'old_all_edge_railings_archived':True}
(P/'saved-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
