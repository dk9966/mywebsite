import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
for m in r.modifiers:m.show_viewport=False
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev)
tree=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);bm=bmesh.new();bm.from_mesh(me)
edges=set(e for e in bm.edges if e.is_boundary);loops=[]
while edges:
 e=edges.pop();todo=[e];group=[]
 while todo:
  e=todo.pop();group.append(e)
  for v in e.verts:
   for e2 in v.link_edges:
    if e2 in edges:edges.remove(e2);todo.append(e2)
 vs=set(v for e in group for v in e.verts)
 loops.append({'edges':len(group),'length':sum(e.calc_length() for e in group),'min':[min(v.co[i] for v in vs) for i in range(3)],'max':[max(v.co[i] for v in vs) for i in range(3)]})
bm.free()
bpy.ops.wm.open_mainfile(filepath=str(P/'welded-terrain-candidate.blend'));r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
added=[]
for f in r.data.polygons:
 c=f.center
 if 3.8<c.x<12.5 and -7<c.y<1 and 0<c.z<7.1:continue
 d=tree.find_nearest(c)[3]
 if d>.01:added.append({'index':f.index,'center':list(c),'area':f.area,'distance':d})
report={'boundary_groups':loops,'new_outside_faces':sorted(added,key=lambda x:-x['area'])[:30],'new_outside_total_area':sum(x['area'] for x in added),'new_outside_count':len(added)}
(P/'caps-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
