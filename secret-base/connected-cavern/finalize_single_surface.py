"""Save and render the integrated cave without replacing the parallel revision."""
import json
from pathlib import Path
import bpy
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'preview-integrated-surface.blend'))
bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.name='Cave | single connected interior surface'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='METAL';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='METAL'
    S.cycles.device='GPU' if any(d.type=='METAL' for d in prefs.devices) else 'CPU'
except Exception:S.cycles.device='CPU'
wall=S.objects['Cavern | single connected interior surface']
report=json.loads(wall['extraction_report']);report['seam_patch_faces']=report.pop('closed_small_seam_loops');wall['extraction_report']=json.dumps(report)
empty=bpy.data.collections.get('07 | Continuous approved-style cave wall')
if empty and not empty.objects:bpy.data.collections.remove(empty)
wall.users_collection[0].name='13 | Joined interior cave surface'
while wall.data.materials[-1].get('surface_role')=='remove':wall.data.materials.pop(index=len(wall.data.materials)-1)
wall['surface_only']=True;wall['thickness']=0.;wall['no_exterior_or_caps']=True
S['single_surface_revision']='Right cave wall and enclosure are one welded interior surface. Original exposed rock shapes and materials retained. Center, bays, bridge, supports, upper-bay finish, and lights preserved.'
for name in ['integrate_right_surface.py','verify_integrated_surface.py']:
    t=bpy.data.texts.get(name) or bpy.data.texts.new(name);t.clear();t.write((P/name).read_text());t.use_fake_user=True
S.camera=S.objects['Interior | overview'];S.render.resolution_x=2000;S.render.resolution_y=1200;S.render.resolution_percentage=100;S.cycles.samples=64
S.render.filepath=str(P/'single-surface-overview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'connected-cavern-single-surface.blend'),compress=True)
bpy.ops.render.render(write_still=True)
S.camera=S.objects['Interior | reverse'];S.render.filepath=str(P/'single-surface-reverse.png');bpy.ops.render.render(write_still=True)
# Square overhead inspection keeps the complete front and rear contours in
# frame, and studio shading makes the thin surface topology easy to see.
S.camera=S.objects['Interior | single surface inspection'];S.render.resolution_x=1600;S.render.resolution_y=1600;S.render.engine='BLENDER_WORKBENCH'
sh=S.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';S.world.color=(.055,.065,.08)
for ob in S.objects:
    if ob.type=='MESH':ob.color=(.31,.37,.43,1) if ob==wall else (.64,.68,.73,1)
# Volume boxes are visible solid boxes only in Workbench; exclude them for this
# inspection render. No geometry, visibility, or material change is saved.
for ob in S.objects:
    if ob.type=='MESH' and any(m and m.use_nodes and any(n.type=='PRINCIPLED_VOLUME' for n in m.node_tree.nodes) for m in ob.data.materials):ob.hide_render=True
S.render.filepath=str(P/'single-surface-plan.png');bpy.ops.render.render(write_still=True)
