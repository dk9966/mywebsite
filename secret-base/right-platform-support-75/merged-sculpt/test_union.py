import bpy,bmesh,json,time
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];s=bpy.data.objects['Lower right | sculpted bearing shoulder']
# Bake only the displayed shape-key mix; preserve the roof controls for the live result.
for m in r.modifiers:m.show_viewport=False;m.show_render=False
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());base=bpy.data.meshes.new_from_object(ev);r.data=base

def stats(me):
 bm=bmesh.new();bm.from_mesh(me);remain=set(bm.verts);comps=[]
 while remain:
  stack=[remain.pop()];n=0
  while stack:
   v=stack.pop();n+=1
   for e in v.link_edges:
    q=e.other_vert(v)
    if q in remain:remain.remove(q);stack.append(q)
  comps.append(n)
 out={'verts':len(bm.verts),'faces':len(bm.faces),'components':sorted(comps,reverse=True),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'wire_edges':sum(e.is_wire for e in bm.edges),'volume':bm.calc_volume(signed=True)};bm.free();return out
before=stats(base)
# Recalculate coherent normals before exact constructive union.
for ob in [r,s]:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
mod=r.modifiers.new('Weld right foundation into cave','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=s
if hasattr(mod,'use_self'):mod.use_self=True
if hasattr(mod,'use_hole_tolerant'):mod.use_hole_tolerant=True
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());merged=bpy.data.meshes.new_from_object(ev);after=stats(merged)
# Compare samples of the original wall and bearing surface against the union.
bvh=BVHTree.FromPolygons([v.co for v in merged.vertices],[list(p.vertices) for p in merged.polygons]);before_far=[]
for v in base.vertices:
 p=v.co
 if not(3.8<p.x<12.5 and -7<p.y<1 and 0<p.z<7.1):
  if v.index%11==0:before_far.append(bvh.find_nearest(p)[3])
upper=[s.matrix_world@v.co for v in s.data.vertices if (s.matrix_world@v.co).z>6.63];mi=r.matrix_world.inverted();top=[bvh.find_nearest(mi@p)[3] for p in upper]
report={'before':before,'after':after,'far_surface_max_deviation':max(before_far),'bearing_top_max_deviation':max(top),'solver':'EXACT'}
(P/'union-test.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Export the candidate as a mesh-only artifact, without touching the live scene.
r.modifiers.remove(mod);r.data=merged;s.hide_render=True;s.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'union-candidate.blend'),compress=True)
