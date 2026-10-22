"""Exercise saved-file controls without moving the user's live scene."""
import bpy,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
S=bpy.context.scene
ctrl=bpy.data.objects['SCENE SLIDERS'];mod=ctrl.modifiers['Scene Sliders']
width=next(s.identifier for s in mod.node_group.interface.items_tree if s.name=='Middle platform width')
original=float(mod[width]);checks=[]
objects=[o for o in S.objects if o.get('texture_grating')]
for value in (original,original*.95,original*1.05,original):
    mod[width]=value;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();triangles=0
    for ob in objects:
        ev=ob.evaluated_get(dg);mesh=ev.to_mesh();mesh.calc_loop_triangles()
        assert len(mesh.loop_triangles)>0,ob.name
        assert mesh.uv_layers.get('GratingUV'),ob.name
        assert all(math.isfinite(c) for v in mesh.vertices for c in v.co),ob.name
        triangles+=len(mesh.loop_triangles);ev.to_mesh_clear()
    middle=bpy.data.objects['Metal | recessed open grate 00']
    ev=middle.evaluated_get(dg)
    radial=max(math.hypot(v.co.x,v.co.y) for v in ev.data.vertices)
    checks.append({'width':value,'triangles':triangles,'sector_max_radius':radial})
assert checks[1]['sector_max_radius']<checks[0]['sector_max_radius']<checks[2]['sector_max_radius']
assert checks[0]==checks[3]
images=[i for i in bpy.data.images if i.name.startswith('Grating |')]
assert len(images)==20 and all(i.packed_file for i in images)
report={'file':bpy.data.filepath,'texture_objects':len(objects),'packed_images':len(images),
        'width_control_checks':checks,'saved_file_left_unchanged':True}
(P/'saved-file-checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
