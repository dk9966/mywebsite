"""Reversible local simplification after the platform fitting modifiers."""
import bpy, json, hashlib, array, statistics
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
w = bpy.data.objects['150 | continuous cave with oblique carved rooms']
d = bpy.data.objects['Upper | beveled square gallery']
NAME = 'Platform surrounds | broad stone triangles'
assert bpy.context.mode == 'OBJECT'

def fingerprint(o):
    h = hashlib.sha256(repr(([list(r) for r in o.matrix_world], o.hide_render,
                              o.hide_get(), o.data.name if o.data else None)).encode())
    if o.type == 'MESH':
        coords = array.array('f', [0.0]) * (len(o.data.vertices)*3)
        o.data.vertices.foreach_get('co', coords)
        h.update(coords.tobytes())
    return h.hexdigest()

if not (P/'protected-before.json').exists():
    (P/'protected-before.json').write_text(json.dumps({o.name:fingerprint(o) for o in bpy.context.scene.objects if o != w}))

# The former reduction happened before the two newest fitting fields and was
# disabled only in the viewport. Replace it with one consistent final pass.
old = w.modifiers['Between platforms | broad low-poly rock']
old.show_viewport = old.show_render = False
mod = w.modifiers.get(NAME)
if mod:
    mod.show_viewport = mod.show_render = False
bpy.context.view_layer.update()
e = w.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert len(e.data.vertices) == len(w.data.vertices)
M = d.matrix_world.inverted() @ w.matrix_world
coords = [M @ v.co for v in e.data.vertices]

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)

def weight(p):
    return (smooth((p.x+5)/1.2)*smooth((9-p.x)/1.2)
            *smooth((p.y+8)/1.5)*smooth((6-p.y)/1.5)
            *smooth((p.z-4.5)/1.0)*smooth((17-p.z)/1.5))

weights = [weight(p) for p in coords]
vg = w.vertex_groups.get(NAME) or w.vertex_groups.new(name=NAME)
vg.remove(list(range(len(coords))))
# Quantized falloff makes assignment inexpensive and deterministic.
bins = {}
for i,a in enumerate(weights):
    q = round(a*100)
    if q: bins.setdefault(q,[]).append(i)
for q,ids in bins.items():
    vg.add(ids,q/100,'REPLACE')

if not mod: mod = w.modifiers.new(NAME,'DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.vertex_group = vg.name
mod.vertex_group_factor = 0.02
mod.ratio = 0.38
mod.use_collapse_triangulate = True
mod.show_viewport = mod.show_render = True
w['platform_surround_optimization'] = 'Final local decimation, after all native fits. Stone detail remains in the material; coarse hidden backing avoids holes when adjusting platforms.'
bpy.context.view_layer.update()
ev = w.evaluated_get(bpy.context.evaluated_depsgraph_get())
result = {'source_triangles':sum(len(p.vertices)-2 for p in w.data.polygons),
          'evaluated_triangles':sum(len(p.vertices)-2 for p in ev.data.polygons),
          'region_vertices':sum(a>0 for a in weights),'modifier':mod.name,
          'source_shape_keys_retained':len(w.data.shape_keys.key_blocks),
          'material':w.data.materials[0].name}
(P/'build-report.json').write_text(json.dumps(result,indent=2))
