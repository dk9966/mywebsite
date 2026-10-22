import bpy,bmesh,json,time
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];s=bpy.data.objects['Lower right | sculpted bearing shoulder']
for m in r.modifiers:m.show_viewport=False;m.show_render=False
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());base=bpy.data.meshes.new_from_object(ev);r.data=base
original=[v.co.copy() for v in base.vertices]

def stat(me):
 bm=bmesh.new();bm.from_mesh(me);rem=set(bm.verts);comp=[]
 while rem:
  st=[rem.pop()];n=0
  while st:
   v=st.pop();n+=1
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in rem:rem.remove(w);st.append(w)
  comp.append(n)
 d={'verts':len(bm.verts),'faces':len(bm.faces),'components':sorted(comp,reverse=True),'boundary':sum(e.is_boundary for e in bm.edges),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'volume':bm.calc_volume(signed=True)};bm.free();return d
before=stat(base)
for ob in [r,s]:
 bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
 bm.verts.index_update();seen=set();dups=[]
 for face in bm.faces:
  k=tuple(sorted(v.index for v in face.verts))
  if k in seen or face.calc_area()<1e-10:dups.append(face)
  else:seen.add(k)
 if dups:bmesh.ops.delete(bm,geom=dups,context='FACES_ONLY')
 # Remove tiny redundant slivers along existing non-manifold room seams.
 for _ in range(5):
  excess=[e for e in bm.edges if len(e.link_faces)>2]
  if not excess:break
  drop=set(min(e.link_faces,key=lambda f:f.calc_area()) for e in excess)
  bmesh.ops.delete(bm,geom=list(drop),context='FACES_ONLY')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 borders=[e for e in bm.edges if e.is_boundary]
 if borders:bmesh.ops.holes_fill(bm,edges=borders,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 # Triangulate only non-triangular polygons for reliable exact union.
 bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
 for iteration in range(5):
  bad=[e for e in bm.edges if not e.is_manifold]
  if not bad:break
  print('REPAIR',ob.name,iteration,[(len(e.link_faces),e.calc_length()) for e in bad],flush=True)
  remove=set(f for e in bad for f in e.link_faces)
  if remove:bmesh.ops.delete(bm,geom=list(remove),context='FACES_ONLY')
  loose=[v for v in bm.verts if not v.link_faces]
  if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
  borders=[e for e in bm.edges if e.is_boundary]
  if borders:bmesh.ops.holes_fill(bm,edges=borders,sides=0)
  bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bm.to_mesh(ob.data);bm.free();ob.data.update()
clean=stat(base)
results=[]
for solver in ['MANIFOLD','EXACT','FLOAT']:
 mod=r.modifiers.new('Test clean union '+solver,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver=solver;mod.object=s
 if solver=='EXACT':mod.use_self=False;mod.use_hole_tolerant=True
 bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev)
 st=stat(me);bvh=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices) for p in me.polygons])
 far=[bvh.find_nearest(p)[3] for i,p in enumerate(original) if i%11==0 and not(3.8<p.x<12.5 and -7<p.y<1 and 0<p.z<7.1)]
 upper=[Vector((x,y,6.633491)) for x,y in [(5.4,-4.5),(6,-5.5),(7,-5.5),(8,-5.5),(6,-3.5),(7,-3.5),(8,-3.5)]]
 top=[bvh.find_nearest(p)[3] for p in upper]
 entry={'solver':solver,'stats':st,'far_max':max(far),'top_max':max(top)};results.append(entry);print(json.dumps(entry),flush=True)
 r.modifiers.remove(mod)
 if st['nonmanifold']==0 and max(top)<.001 and max(far)<.001 and len(st['components'])==1:
  r.data=me;s.hide_render=True;s.hide_set(True);me.name='Cave | welded right shoulder clean candidate';bpy.ops.wm.save_as_mainfile(filepath=str(P/'clean-difference-candidate.blend'),compress=True);break
report={'before':before,'cleaned':clean,'trials':results};(P/'clean-difference-test.json').write_text(json.dumps(report,indent=2))
