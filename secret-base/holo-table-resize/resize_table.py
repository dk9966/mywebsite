"""Widen the existing tabletop while retaining ring cross-sections and controls."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
source = Path(bpy.data.filepath)
assert source.name == 'cave-platform-sliders.blend'
assert bpy.context.mode == 'OBJECT'
col = bpy.data.collections['175 | Lower bay holo table']
assert not col.get('widened_25_percent'), 'Already resized'
center = bpy.data.objects['Holo table | floor plinth'].matrix_world.translation.copy()
objects = [o for o in col.all_objects if not o.hide_render]
prefix = 'Holo table | '
fixed = {'floor plinth', 'pedestal column', 'pedestal collar'}

def coords(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]

def radius_range(o):
    rs = [(p-center).xy.length for p in coords(o)]
    return min(rs), max(rs)

radius = radius_range(bpy.data.objects[prefix+'armored band panel 00'])[1]
delta = radius * .25
before = {o.name: radius_range(o) for o in objects if o.type == 'MESH'}
original_z = {o.name: [p.z for p in coords(o)] for o in objects if o.type == 'MESH'}
# Keep a full recoverable copy before changing any geometry.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'before-table-widening.blend'), copy=True, compress=True)

# Each control assembly moves rigidly along its bezel's radial direction.
directions = {}
for o in objects:
    name = o.name.removeprefix(prefix)
    if name.startswith(('console ', 'fascia lamp ')):
        group = name.split(' | ')[0]
        if group not in directions:
            bezel_name = prefix+group+(' | metal bezel' if group.startswith('console') else ' | bezel')
            points = coords(bpy.data.objects[bezel_name])
            p = sum(points, Vector()) / len(points) - center
            p.z = 0
            directions[group] = p.normalized()*delta

rings = []
for o in objects:
    name = o.name.removeprefix(prefix)
    if name in fixed:
        continue
    if o.type == 'LIGHT':
        if name == 'soft glass glow' and hasattr(o.data, 'size'):
            o.data = o.data.copy()
            o.data.size *= (before[prefix+'misty holo glass'][1]+delta)/before[prefix+'misty holo glass'][1]
        continue
    assert o.type == 'MESH', (name, o.type)
    o.data = o.data.copy()
    matrix = o.matrix_world.copy()
    inverse = matrix.inverted()
    rigid = name.startswith(('console ', 'fascia lamp '))
    if not rigid:
        rings.append(o.name)
    for v in o.data.vertices:
        p = matrix @ v.co
        if rigid:
            p += directions[name.split(' | ')[0]]
        else:
            d = p-center
            r = d.xy.length
            # Keep disk-center vertices centered; shift every circular profile
            # outward by the same amount to preserve its radial thickness.
            if r > 1e-5:
                p.x += delta*d.x/r
                p.y += delta*d.y/r
        v.co = inverse @ p
    o.data.update()

bpy.context.view_layer.update()
after = {o.name: radius_range(o) for o in objects if o.type == 'MESH'}
for name in rings:
    lo, hi = before[name]
    if lo > 1e-5:
        assert abs((after[name][1]-after[name][0])-(hi-lo)) < 1e-5, name
for o in objects:
    if o.type == 'MESH':
        assert max(abs(p.z-z) for p,z in zip(coords(o),original_z[o.name])) < 1e-5
assert abs(after[prefix+'armored band panel 00'][1]/radius-1.25)<1e-5
col['widened_25_percent'] = True
col['radius_m'] = radius+delta
audit = {'old_tabletop_diameter':radius*2,'new_tabletop_diameter':(radius+delta)*2,
         'radial_offset':delta,'ring_thickness_preserved':True,'height_preserved':True,
         'before':before,'after':after,'backup':str(OUT/'before-table-widening.blend')}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
print('TABLE_RESIZE_OK',json.dumps({k:v for k,v in audit.items() if k not in ('before','after')}))
