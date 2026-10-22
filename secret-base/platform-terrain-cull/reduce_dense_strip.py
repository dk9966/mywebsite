"""Spend the remaining geometry budget on silhouettes, not the roof's dense band."""
import bpy,json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
d=bpy.data.objects['Upper | beveled square gallery']
primary=w.modifiers['Platform surrounds | broad stone triangles']
NAME='Roof surround | remove remaining dense strip'
assert not w.modifiers.get(NAME)
primary.show_viewport=False;bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get());M=d.matrix_world.inverted()@w.matrix_world
def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)
vg=w.vertex_groups.new(name=NAME);bins=collections.defaultdict(list)
for v in e.data.vertices:
    p=M@v.co
    a=(smooth((p.x+3.8)/.6)*smooth((4.5-p.x)/.7)*smooth((p.y+7.2)/.8)
       *smooth((2.-p.y)/.7)*smooth((p.z-8.5)/.35)*smooth((10.6-p.z)/.7))
    if round(a*100):bins[round(a*100)].append(v.index)
for q,ids in bins.items():vg.add(ids,q/100,'REPLACE')
primary.show_viewport=True
mod=w.modifiers.new(NAME,'DECIMATE');mod.vertex_group=vg.name;mod.vertex_group_factor=.02
mod.ratio=.97;mod.use_collapse_triangulate=True
bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
result={'dense_strip_source_vertices':sum(map(len,bins.values())),'triangles':sum(len(f.vertices)-2 for f in e.data.polygons)}
(P/'dense-strip-report.json').write_text(json.dumps(result,indent=2))
