import bpy, json
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'base.blend'))
bpy.context.view_layer.update()
collection = bpy.data.collections['about_holo_table']
objects = list(collection.all_objects)
points = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
floor = bpy.data.objects['deck_floor_about']
floor_points = [floor.matrix_world @ Vector(p) for p in floor.bound_box]
report = {
    'scene': bpy.context.scene.name,
    'collection': collection.name,
    'objects': len(objects),
    'bounds': [[min(p[k] for p in points), max(p[k] for p in points)] for k in range(3)],
    'floor_top': max(p.z for p in floor_points),
    'materials': {m.name: {n.name: {s.name: list(s.default_value) if hasattr(s.default_value, '__len__') else s.default_value for s in n.inputs if hasattr(s, 'default_value') and isinstance(s.default_value, (float, int, bool)) or hasattr(s, 'default_value') and s.name in ['Base Color', 'Emission Color']} for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'} for o in objects for m in o.data.materials if m and m.use_nodes},
    'components': [{'name': o.name, 'parent': o.parent.name if o.parent else None, 'hidden': o.hide_render, 'vertices': len(o.data.vertices) if o.type == 'MESH' else 0} for o in objects],
}
(HERE/'holo-source-inventory.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != 'components'}), flush=True)
