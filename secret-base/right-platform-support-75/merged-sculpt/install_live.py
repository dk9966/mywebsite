"""Install only the verified cave mesh and its replacement right-platform supports."""
import bpy,json,hashlib,bmesh
from pathlib import Path
P=Path(__file__).resolve().parent
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
shoulder=bpy.data.objects['Lower right | sculpted bearing shoulder']
def sig(ob):
 h=hashlib.sha256()
 for v in ob.data.vertices:h.update(str(tuple(v.co)).encode())
 if ob.data.shape_keys:
  for k in ob.data.shape_keys.key_blocks:
   h.update(str(k.value).encode())
   for v in k.data:h.update(str(tuple(v.co)).encode())
 return h.hexdigest()
start=json.loads((P/'live-start.json').read_text())
assert sig(rock)==start['cave'],'Cave changed since preparation; rebuild from fresh live geometry.'
assert sig(shoulder)==start['shoulder'],'Shoulder changed since preparation.'
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.ed.undo_push(message='Before welding right platform terrain and extending braces')
materials=list(rock.data.materials)
old_mesh=rock.data;old_mesh.use_fake_user=True
with bpy.data.libraries.load(str(P/'welded-terrain-candidate.blend'),link=False) as (source,target):
 target.meshes=['Cave | continuous welded platform terrain']
mesh=target.meshes[0]
assert mesh and mesh.attributes.get('roof_clearance_follow')
mesh.materials.clear()
for mat in materials:mesh.materials.append(mat)
rock.data=mesh
rock['right_foundation']='Continuous welded rock: current sculpt baked, internal overlap removed, 75 percent platform bearing.'
rock['sculpt_note']='The cave wall and right platform shoulder are one connected mesh. Original mesh retained in backup.'
bpy.data.objects.remove(shoulder,do_unlink=True)
bpy.context.view_layer.update()
# Recreate the verified support layout in the current scene without loading or saving other scene state.
support_code=(P/'build_upright_supports.py').read_text()
support_code=support_code.replace("bpy.ops.wm.save_as_mainfile(filepath=str(P/'welded-platform-upright-supports.blend'),compress=True)","")
exec(compile(support_code,str(P/'build_upright_supports.py'),'exec'))
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
bm=bmesh.new();bm.from_mesh(rock.data);remaining=set(bm.verts);parts=[]
while remaining:
 stack=[remaining.pop()];count=0
 while stack:
  v=stack.pop();count+=1
  for e in v.link_edges:
   other=e.other_vert(v)
   if other in remaining:remaining.remove(other);stack.append(other)
 parts.append(count)
topology={'vertices':len(bm.verts),'faces':len(bm.faces),'connected_components':len(parts),'open_bottom_boundary_edges':sum(e.is_boundary for e in bm.edges),'bad_interior_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),'loose_vertices':sum(not v.link_faces for v in bm.verts)}
bm.free()
assert topology['connected_components']==1 and topology['bad_interior_edges']==0 and topology['loose_vertices']==0
for ob in bpy.context.selected_objects:ob.select_set(False)
rock.select_set(True);bpy.context.view_layer.objects.active=rock
bpy.ops.object.mode_set(mode='SCULPT')
bpy.context.view_layer.update()
result={'topology':topology,'mode':bpy.context.mode,'bearing_fraction':ratio,'brace_count':len(report),'length_range':[min(p['length'] for p in report),max(p['length'] for p in report)],'angle_range':[min(p['angle_from_vertical'] for p in report),max(p['angle_from_vertical'] for p in report)],'visible_braces':sum(p['visible_fraction_from_main_camera']>.4 for p in report),'roof_control_preserved':any(m.type=='NODES' and m.show_viewport for m in rock.modifiers),'preview_path':str(P/'sculpt-ready-platform-preview.blend')}
(P/'live-install-check.json').write_text(json.dumps(result,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'sculpt-ready-platform-preview.blend'),copy=True,compress=True)
