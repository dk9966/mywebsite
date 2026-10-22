import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms']
for m in r.modifiers:m.show_viewport=False
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());original=bpy.data.meshes.new_from_object(ev)
coords=[v.co.copy() for v in original.vertices];faces=[(list(f.vertices),f.material_index,f.use_smooth) for f in original.polygons]
tree=BVHTree.FromPolygons(coords,[p[0] for p in faces])
bpy.ops.wm.open_mainfile(filepath=str(P/'sculpt-ready-platform-preview.blend'))
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];me=r.data
bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();bm.verts.index_update();kd=KDTree(len(bm.verts))
for v in bm.verts:kd.insert(v.co,v.index)
kd.balance();mapping={}
for i,p in enumerate(coords):
 _,j,d=kd.find(p)
 if d<.00002:mapping[i]=bm.verts[j]
restored=removed=0
for ids,material,smooth in faces:
 if len(ids)<=3 or any(i not in mapping for i in ids):continue
 if any(3.7<coords[i].x<12.6 and -7.1<coords[i].y<1.1 and -.1<coords[i].z<7.2 for i in ids):continue
 vs=[mapping[i] for i in ids];vset=set(vs)
 linked=set(f for v in vs for f in v.link_faces)
 cover=[f for f in linked if all(v in vset for v in f.verts)]
 if len(cover)<2:continue
 counts={}
 for f in cover:
  for e in f.edges:counts[e]=counts.get(e,0)+1
 boundary={frozenset(e.verts) for e,count in counts.items() if count==1}
 expected={frozenset((vs[i],vs[(i+1)%len(vs)])) for i in range(len(vs))}
 if boundary!=expected:continue
 removed+=len(cover)-1;restored+=1
 bmesh.ops.delete(bm,geom=cover,context='FACES_ONLY')
 wire=[e for v in vs for e in v.link_edges if not e.link_faces and frozenset(e.verts) not in expected]
 if wire:bmesh.ops.delete(bm,geom=list(set(wire)),context='EDGES')
 f=bm.faces.new(vs);f.material_index=material;f.smooth=smooth
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
assert sum(e.is_boundary for e in bm.edges)==128
assert all(e.is_manifold or e.is_boundary for e in bm.edges)
bm.to_mesh(me);bm.free();me.update();me.calc_loop_triangles()
deviations=[]
for t in me.loop_triangles:
 p=sum((me.vertices[i].co for i in t.vertices),Vector())/3
 if 3.7<p.x<12.6 and -7.1<p.y<1.1 and -.1<p.z<7.2:continue
 deviations.append(tree.find_nearest(p)[3])
report={'restored_original_polygons':restored,'redundant_triangulation_faces_removed':removed,'vertices':len(me.vertices),'faces':len(me.polygons),'far_surface_max_deviation':max(deviations),'far_triangles_over_1mm':sum(d>.001 for d in deviations)}
(P/'restored-topology-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
for ob in bpy.context.selected_objects:ob.select_set(False)
r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='SCULPT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'final-clean-topology.blend'),compress=True)
