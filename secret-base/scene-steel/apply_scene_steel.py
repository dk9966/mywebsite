"""Extend the approved right-bay steel palette across the scene's metalwork."""
import array
import ast
import hashlib
import json
from pathlib import Path

import bpy

P = Path(__file__).resolve().parent
S = bpy.context.scene
assert S.get('right_platform_steel_revision'), 'Apply the approved right steel pass first'
assert not S.get('scene_steel_revision'), 'Scene steel pass already applied'

# Reuse only the read-only geometry fingerprint helper from the first pass.
source = ast.parse((P.parent/'right-platform-steel/apply_steel.py').read_text())
helper = next(n for n in source.body if isinstance(n, ast.FunctionDef)
              and n.name == 'geometry_snapshot')
exec(compile(ast.Module(body=[helper], type_ignores=[]), '<geometry helper>', 'exec'))
geometry_before = geometry_snapshot()
lights_before = {o.name: [o.data.energy, list(o.data.color)]
                 for o in S.objects if o.type == 'LIGHT'}

# Existing variants remain shared with the approved right-bay appearance.
mapping = {m['Original material']: m for m in bpy.data.materials
           if m.name.startswith('Right steel |') and 'Original material' in m}
aliases = {
    'Bridge | restrained silver fasteners': 'Metal | machined edge highlights',
    'Left bay | beveled gunmetal armor': 'Bridge | blue gunmetal panel frames',
    'Left bay | deck panel 0': 'Metal | satin blue steel',
    'Left bay | deck panel 1': 'Upper right | satin service insert',
    'Left bay | deck panel 2': 'Metal | satin blue steel',
    'Left bay | machined edge and bolt heads': 'Metal | machined edge highlights',
    'Left bay | satin graphite wall panels': 'Lower | aligned blue graphite panels',
    'Rear left | subtly varied floor panels': 'Upper right | satin service insert',
    'graphite': 'Lower | aligned blue graphite panels',
    'metalDark': 'Metal | outer walkway alloy',
    'holoTable_CW_alternate armor': 'Metal | outer walkway alloy',
    'holoTable_CW_satin armored alloy': 'Metal | satin blue steel',
    'holoTable_CW_machined edge': 'Metal | machined edge highlights',
    'holoTable_CW_key surrounds': 'Metal | dark structural steel',
    'holoTable_CW_recessed graphite': 'Metal | unlit grate recess',
    'holoTable_basin': 'Left bay | deep channel inset',
}
for source_name, approved_name in aliases.items():
    mapping[source_name] = mapping[approved_name]

# Image-based grating retains its alpha cutouts, normal maps, and UVs.
grating_variants = {}
assignments = []
untouched = []
for o in sorted(S.objects, key=lambda o: o.name):
    if o.type != 'MESH' or o.hide_render or all(c.hide_render for c in o.users_collection):
        continue
    for slot in o.material_slots:
        old = slot.material
        if not old:
            continue
        new = mapping.get(old.name)
        if old.name.startswith('Grating texture |'):
            if old.name not in grating_variants:
                new = old.copy()
                new.name = old.name.replace('Grating texture |', 'Scene steel grating |')
                new['Original material'] = old.name
                new.diffuse_color = (.033, .036, .040, 1.)
                nodes = new.node_tree.nodes
                links = new.node_tree.links
                for bsdf in [n for n in nodes if n.type == 'BSDF_PRINCIPLED']:
                    color_socket = bsdf.inputs['Base Color']
                    assert len(color_socket.links) == 1, old.name
                    upstream = color_socket.links[0].from_socket
                    links.remove(color_socket.links[0])
                    hsv = nodes.new('ShaderNodeHueSaturation')
                    hsv.name = 'Steel | neutral grating color'
                    hsv.label = 'Muted steel gray'
                    hsv.inputs['Saturation'].default_value = .12
                    hsv.inputs['Value'].default_value = .60
                    hsv.location = (bsdf.location.x - 210, bsdf.location.y + 160)
                    links.new(upstream, hsv.inputs['Color'])
                    links.new(hsv.outputs['Color'], color_socket)
                    bsdf.inputs['Roughness'].default_value = .46
                grating_variants[old.name] = new
            new = grating_variants[old.name]
        if new is None:
            untouched.append((o.name, slot.slot_index, old.name))
            continue
        assignments.append({'object': o.name, 'slot': slot.slot_index,
                            'before': old.name, 'before_link': slot.link,
                            'after': new.name})
        slot.link = 'OBJECT'
        slot.material = new

bpy.context.view_layer.update()
assert geometry_before == geometry_snapshot(), 'Geometry or camera changed'
assert lights_before == {o.name: [o.data.energy, list(o.data.color)]
                        for o in S.objects if o.type == 'LIGHT'}, 'Lighting changed'
assert all(bpy.data.objects[name].material_slots[index].material.name == mat
           for name, index, mat in untouched), 'A protected material changed'
S['scene_steel_revision'] = 'Approved right-bay neutral satin steel extended to all architectural metalwork and console housings.'
report = {
    'main_file': bpy.data.filepath,
    'objects_recolored': len({a['object'] for a in assignments}),
    'material_assignments': assignments,
    'grating_materials_created': [m.name for m in grating_variants.values()],
    'geometry_and_camera_unchanged': True,
    'lighting_unchanged': True,
    'other_material_assignments_unchanged': True,
}
(P/'verification.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'scene-steel-candidate.blend'), copy=True, compress=True)
result = {k: v for k, v in report.items() if k != 'material_assignments'}
