import bpy,bmesh,json,time
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];s=bpy.data.objects['Lower right | sculpted bearing shoulder']
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
modifier_states=[(m,m.show_viewport,m.show_render) for m in r.modifiers]
# Keep the existing 75% bearing rim, broadening the rock body below it for upright feet.
old_sizes=[1,.998,.973,.925,.855,.76,.65,.54,.44,.34,.245,.18]
old_mix=[0,.025,.08,.16,.27,.4,.54,.67,.79,.88,.96,1]
new_sizes=[1,.998,.998,.995,.989,.975,.90,.74,.56,.38,.245,.18]
new_mix=[0,.004,.005,.01,.016,.03,.12,.3,.55,.8,.96,1]
center=Vector((8.148756742,-3.197468805,0));bury=Vector((10.1,-.8,0))
for v in s.data.vertices:
 k=v.index//56;z=v.co.z
 old_center=center.lerp(bury,old_mix[k]);new_center=center.lerp(bury,new_mix[k])
 v.co=new_center+(v.co-old_center)*(new_sizes[k]/old_sizes[k]);v.co.z=z
s.data.update()
for m in r.modifiers:m.show_viewport=False;m.show_render=False
bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());base=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get());r.data=base
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
cap_material=bpy.data.materials.new('Temporary boolean closure');base.materials.append(cap_material);cap_index=len(base.materials)-1
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
 if borders:
  filled=bmesh.ops.holes_fill(bm,edges=borders,sides=0)
  if ob==r:
   for f in filled['faces']:
    if f.calc_area()>10:f.material_index=cap_index
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 # Triangulate only non-triangular polygons for reliable exact union.
 bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
 for iteration in range(5):
  wire=[e for e in bm.edges if not e.link_faces]
  if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
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
for solver in ['MANIFOLD']:
 mod=r.modifiers.new('Test clean union '+solver,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver=solver;mod.object=s
 if solver=='EXACT':mod.use_self=False;mod.use_hole_tolerant=True
 bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
 raw=stat(me)
 bm=bmesh.new();bm.from_mesh(me)
 temporary=[f for f in bm.faces if f.material_index==cap_index]
 if temporary:bmesh.ops.delete(bm,geom=temporary,context='FACES_ONLY')
 # Remove boolean and triangulation edges only where the surface is coplanar.
 bmesh.ops.dissolve_limit(bm,angle_limit=.00005,use_dissolve_boundaries=False,verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL'})
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
 wire=[e for e in bm.edges if not e.link_faces]
 if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
 loose=[v for v in bm.verts if not v.link_edges]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 me.materials.pop(index=cap_index)
 st=stat(me);bvh=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices) for p in me.polygons])
 far=[bvh.find_nearest(p)[3] for i,p in enumerate(original) if i%11==0 and not(3.8<p.x<12.5 and -7<p.y<1 and 0<p.z<7.1)]
 upper=[Vector((x,y,6.633491)) for x,y in [(5.4,-4.5),(6,-5.5),(7,-5.5),(8,-5.5),(6,-3.5),(7,-3.5),(8,-3.5)]]
 top=[bvh.find_nearest(p)[3] for p in upper]
 entry={'solver':solver,'raw_stats':raw,'stats':st,'far_max':max(far),'top_max':max(top)};results.append(entry);print(json.dumps(entry),flush=True)
 r.modifiers.remove(mod)
 if st['nonmanifold']==st['boundary']==128 and max(top)<.001 and max(far)<.001 and len(st['components'])==1:
  r.data=me;me.name='Cave | continuous welded platform terrain'
  attr=me.attributes.get('roof_clearance_follow');assert attr and len(attr.data)==len(me.vertices)
  entry['roof_attribute_range']=[min(v.value for v in attr.data),max(v.value for v in attr.data)]
  for m,vp,rend in modifier_states:m.show_viewport=vp;m.show_render=rend
  bpy.data.objects.remove(s,do_unlink=True)
  r['right_foundation']='Welded continuous 75% bearing shoulder; internal surfaces removed; current sculpt shape baked.'
  bpy.ops.wm.save_as_mainfile(filepath=str(P/'welded-terrain-candidate.blend'),compress=True);break
report={'before':before,'cleaned':clean,'trials':results};(P/'welded-terrain-check.json').write_text(json.dumps(report,indent=2))
