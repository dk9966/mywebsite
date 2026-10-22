"""Give the two right bays dark neutral steel and more focused overhead light.

Run once on the live scene after saving before-steel.blend. Material overrides
are object-linked so shared meshes and other platforms keep their original look.
"""
import array
import hashlib
import json
import math
from pathlib import Path

import bpy

P = Path(__file__).resolve().parent
S = bpy.context.scene
assert not S.get('right_platform_steel_revision'), 'Steel pass already applied'


def geometry_snapshot():
    meshes = {}
    for mesh in bpy.data.meshes:
        digest = hashlib.sha256()
        for items, field, count, kind in [
            (mesh.vertices, 'co', 3, 'f'),
            (mesh.loops, 'vertex_index', 1, 'i'),
            (mesh.polygons, 'material_index', 1, 'i'),
        ]:
            values = array.array(kind, [0]) * (len(items) * count)
            items.foreach_get(field, values)
            digest.update(values.tobytes())
        meshes[mesh.name] = digest.hexdigest()
    return {
        'meshes': meshes,
        'objects': {o.name: [list(r) for r in o.matrix_world] for o in S.objects},
        'camera': [S.camera.name, S.camera.data.lens],
    }


before = geometry_snapshot()
prefixes = ('151 |', '152 |', '157 |', '160 |', '161 |', '162 |',
            '163 |', '164 |', '165 |', '168 |', '171 |', '173 |',
            '174 | Upper')
targets = {o for c in bpy.data.collections if c.name.startswith(prefixes)
           for o in c.objects if o.type == 'MESH'}
outside_materials = {
    o.name: [(slot.link, slot.material.name if slot.material else None)
             for slot in o.material_slots]
    for o in S.objects if o not in targets
}

# Linear RGB: small cool bias, with subdued body color and satin highlights.
palette = {
    'Metal | satin blue steel': ((.033, .036, .040), .80, .41),
    'Upper right | satin service insert': ((.030, .033, .036), .80, .44),
    'Lower | radial satin turntable': ((.048, .052, .058), .78, .40),
    'Lower | aligned blue graphite panels': ((.042, .047, .053), .68, .47),
    'Bridge | blue gunmetal panel frames': ((.046, .050, .055), .78, .41),
    'Metal | outer walkway alloy': ((.025, .028, .032), .78, .43),
    'Metal | dark structural steel': ((.015, .017, .020), .76, .44),
    'Metal | machined edge highlights': ((.082, .090, .101), .86, .32),
    'Lower | aligned architectural trim': ((.029, .033, .038), .74, .43),
    'Lower | neutral gray channel supports': ((.052, .058, .065), .70, .44),
    'Lower | gray lamp ledges': ((.063, .069, .077), .70, .42),
    'Lower | crown sloped graphite roof': ((.026, .029, .033), .65, .49),
    'Lower | matte roof cassette': ((.024, .027, .031), .65, .50),
    'Lower | flat dark gray wall projections': ((.020, .022, .025), .55, .50),
    'Lower | dark recessed support channels': ((.020, .022, .025), .55, .50),
    'Lower | circular light blackened housing': ((.014, .016, .019), .74, .42),
    'Lower | circular light machined rim': ((.044, .049, .056), .82, .36),
    'Left bay | deep channel inset': ((.012, .014, .017), .65, .47),
    'Metal | unlit grate recess': ((.006, .007, .009), .25, .73),
    'Lower | circular light recessed slots': ((.005, .006, .008), .25, .55),
}
copies = {}
assignments = []
for o in sorted(targets, key=lambda o: o.name):
    for slot in o.material_slots:
        source = slot.material
        if source is None or source.name not in palette:
            continue
        if source.name not in copies:
            mat = source.copy()
            mat.name = 'Right steel | ' + source.name.split(' | ', 1)[-1]
            mat['Original material'] = source.name
            color, metallic, roughness = palette[source.name]
            mat.diffuse_color = (*color, 1.)
            for bsdf in [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']:
                bsdf.inputs['Base Color'].default_value = (*color, 1.)
                bsdf.inputs['Metallic'].default_value = metallic
                bsdf.inputs['Roughness'].default_value = roughness
                # Preserve procedural grain, editing the actual linked colors.
                for link in bsdf.inputs['Base Color'].links:
                    node = link.from_node
                    assert node.type == 'VALTORGB', (source.name, node.type)
                    els = node.color_ramp.elements
                    for i, e in enumerate(els):
                        factor = .95 + .10 * i / max(1, len(els)-1)
                        e.color = (*(v * factor for v in color), 1.)
                for link in bsdf.inputs['Roughness'].links:
                    node = link.from_node
                    if node.type == 'MAP_RANGE':
                        node.inputs['To Min'].default_value = roughness - .055
                        node.inputs['To Max'].default_value = roughness + .055
                    elif node.type == 'VALTORGB':
                        els = node.color_ramp.elements
                        for i, e in enumerate(els):
                            v = roughness - .055 + .11 * i / max(1, len(els)-1)
                            e.color = (v, v, v, 1.)
            copies[source.name] = mat
        assignments.append({'object': o.name, 'slot': slot.slot_index,
                            'old_link': slot.link, 'old': source.name,
                            'new': copies[source.name].name})
        slot.link = 'OBJECT'
        slot.material = copies[source.name]

ctrl = bpy.data.objects['LIGHTING CONTROLS']
ids = json.loads(ctrl['socket_ids'])
mod = ctrl.modifiers['Reference Lighting']
old_zone_values = {zone: mod[ids[zone]] for zone in
                   ('Upper right platform', 'Lower right platform')}
for zone in old_zone_values:
    mod[ids[zone]] = .82

lights = []
for o in bpy.data.collections['180 | Reference soft spotlight lighting'].objects:
    if o.type != 'LIGHT' or not o.name.startswith(('RL | Upper right |', 'RL | Lower right |')):
        continue
    d = o.data
    old = {'name': o.name, 'base_power': o['Base power (W)'],
           'drivers': [(f.data_path, f.array_index, f.driver.expression)
                       for f in d.animation_data.drivers],
           'volume_factor': d.volume_factor}
    if d.type == 'SPOT':
        o['Base power (W)'] *= 1.125
        d.volume_factor = 1.25
        # Focus the extremely broad original cones without a harsh edge.
        angle = 112. if 'Upper right' in o.name else 120.
        for f in d.animation_data.drivers:
            if f.data_path == 'spot_blend':
                f.driver.expression = '.84*b'
            elif f.data_path == 'spot_size':
                f.driver.expression = f'min(3.10,{math.radians(angle):.10f}*w)'
    else:
        o['Base power (W)'] *= .52
    for f in d.animation_data.drivers:
        if f.data_path == 'color':
            f.driver.expression = '.45*c+.55'
    o.update_tag()
    d.update_tag()
    lights.append(old)

mist_before = {}
for name in ('RL mist | Upper right', 'RL mist | Lower right'):
    mat = bpy.data.materials[name]
    mist_before[name] = []
    for f in mat.node_tree.animation_data.drivers:
        mist_before[name].append((f.data_path, f.driver.expression))
        f.driver.expression = f'({f.driver.expression})*1.5'
    mat.node_tree.update_tag()

ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
after = geometry_snapshot()
assert before == after, 'Unexpected geometry, transform or camera change'
assert outside_materials == {
    o.name: [(slot.link, slot.material.name if slot.material else None)
             for slot in o.material_slots]
    for o in S.objects if o not in targets
}, 'Material assignment changed outside right bays'

S['right_platform_steel_revision'] = 'Dark neutral satin steel; restrained room fill and stronger soft overhead beams.'
report = {
    'active_file': bpy.data.filepath,
    'material_assignments': assignments,
    'materials_created': {src: m.name for src, m in copies.items()},
    'zone_brightness_before': old_zone_values,
    'light_settings_before': lights,
    'mist_drivers_before': mist_before,
    'geometry_transforms_camera_unchanged': before == after,
    'outside_material_assignments_unchanged': True,
    'meshes_verified': len(before['meshes']),
    'objects_verified': len(before['objects']),
}
(P/'verification.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'steel-candidate.blend'), copy=True, compress=True)
result = {'candidate': str(P/'steel-candidate.blend'),
          'objects_recolored': len({a['object'] for a in assignments}),
          'materials_created': len(copies),
          'geometry_transforms_camera_unchanged': True}
