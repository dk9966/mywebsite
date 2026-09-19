"""Pack the editable scene, validate it, and export a batched glTF handoff.
The editable .blend is saved before the runtime-only mesh batching.
"""
import bpy, os, json, math, collections
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'cavern-portfolio.blend'))
S=bpy.context.scene
ref=bpy.data.images.load(os.path.join(ROOT,'reference.png'),check_existing=True);ref.use_fake_user=True;ref.pack()
if not S.camera.data.background_images:
 bg=S.camera.data.background_images.new();bg.image=ref;bg.alpha=.35
S.camera.data.show_background_images=False
for f in ['build_scene.py','enrich_scene.py','detail_pass.py','finalize.py','instance_glb.py','verify_scene.py','refine_atmosphere.py','apply_scanned_materials.py','add_scanned_rock_faces.py','connect_geological_forms.py','weather_deck_surfaces.py','bake_runtime_water.py','SCENE_NOTES.md']:
 if f in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts[f])
 bpy.data.texts.load(os.path.join(ROOT,f))
bpy.ops.file.pack_all()
deps=bpy.context.evaluated_depsgraph_get();tris=0
for ob in S.objects:
 if ob.type in {'MESH','CURVE','FONT'}:
  me=ob.evaluated_get(deps).to_mesh();me.calc_loop_triangles();tris+=len(me.loop_triangles);ob.evaluated_get(deps).to_mesh_clear()
assert all(math.isfinite(float(c)) for o in S.objects for row in o.matrix_world for c in row)
assert S.camera.data.type=='ORTHO' and abs(S.camera.data.ortho_scale-44.5)<.0001
stats={'source_objects':len(S.objects),'evaluated_triangles':tris,'camera':{'position':list(S.camera.location),'quaternion':list(S.camera.rotation_euler.to_quaternion()),'horizontal_span':44.5,'vertical_span':44.5*927/1696},'water_elevation':.9,'runtime_notes':['GLB has batched unique geometry and EXT_mesh_gpu_instancing for repeated modules.','CC0 rock and metal maps, baked deck seam wear, a compact hologram emission map and baked water surface maps are packed in the GLB with explicit UVs. Render-only volumes and lights are excluded.','Recreate localized light pools, graded fog and restrained bloom in Three.js using atmosphere-runtime.json.','Editable labels and curves remain in the .blend; the GLB contains converted mesh lettering.']}
S['handoff']='See runtime-manifest.json and SCENE_NOTES.md';S['evaluated_triangles']=tris
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'cavern-portfolio.blend'))
if 'atmosphere_revision' in S:
 lighting=[]
 for o in S.objects:
  if o.type=='LIGHT' and o.data.energy>0:
   d=o.data;r={'name':o.name,'type':d.type,'position_blender_z_up':list(o.location),'quaternion_wxyz':list(o.rotation_euler.to_quaternion()),'watts':d.energy,'linear_color':list(d.color)}
   r['receiver_collection']=o.light_linking.receiver_collection.name if o.light_linking.receiver_collection else None
   if d.type=='SPOT':r.update(angle_radians=d.spot_size,blend=d.spot_blend,radius=d.shadow_soft_size)
   if d.type=='AREA':r.update(size=d.size)
   lighting.append(r)
 atmosphere={'revision':S['atmosphere_revision'],'active_lights':lighting,'render_engine':'Cycles','receiver_groups':{c.name:[ob.name for ob in c.objects] for c in bpy.data.collections if c.name.startswith('LIGHT LINK |')},'runtime_guidance':'Use baked lighting or a reduced local-light set. Cycles watts are reference values, not calibrated Three.js intensities. Approximate spatial mist with depth fog and local particles, retaining dark foreground silhouettes.'}
 json.dump(atmosphere,open(os.path.join(ROOT,'atmosphere-runtime.json'),'w'),indent=2)
# Bake procedural water into portable maps in the export copy only.
exec(compile(open(os.path.join(ROOT,'bake_runtime_water.py')).read(),'bake_runtime_water.py','exec'))
# Convert only curves/text in the in-memory export copy.
bpy.ops.object.select_all(action='DESELECT')
convert=[o for o in S.objects if o.type in {'CURVE','FONT'}]
for ob in convert:ob.select_set(True)
if convert:
 bpy.context.view_layer.objects.active=convert[0];bpy.ops.object.convert(target='MESH')
# The volume cube is a Cycles presentation object, not opaque runtime geometry.
for co in list(bpy.data.collections):
 if co.name.startswith('04 |'):
  for ob in list(co.objects):bpy.data.objects.remove(ob,do_unlink=True)
for ob in list(S.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
bpy.context.view_layer.update()
# Keep frequently reused meshes intact for GPU instancing; batch unique pieces by area.
counts=collections.Counter(o.data for o in S.objects if o.type=='MESH')
batch_count=0
for co in list(bpy.data.collections):
 candidates=[o for o in list(co.objects) if o.type=='MESH' and counts[o.data]<8]
 if not candidates:continue
 verts=[];faces=[];material_ids=[];smooth_flags=[];mats=[];matmap={};uv_faces=[];sharp_edges=set()
 for ob in candidates:
  base=len(verts);M=ob.matrix_world;verts.extend([tuple(M@v.co) for v in ob.data.vertices])
  local=[]
  for mat in ob.data.materials:
   key=mat.name if mat else 'None'
   if key not in matmap:matmap[key]=len(mats);mats.append(mat)
   local.append(matmap[key])
  uv=ob.data.uv_layers.active
  for e in ob.data.edges:
   if e.use_edge_sharp:sharp_edges.add(tuple(sorted(base+i for i in e.vertices)))
  for p in ob.data.polygons:
   uv_faces.append([tuple(uv.data[li].uv) if uv else (0,0) for li in p.loop_indices])
   faces.append(tuple(base+i for i in p.vertices));material_ids.append(local[p.material_index] if local else 0);smooth_flags.append(p.use_smooth)
 me=bpy.data.meshes.new(co.name+' | batched geometry');me.from_pydata(verts,[],faces);me.update()
 for mat in mats:me.materials.append(mat)
 for poly,idx,smooth in zip(me.polygons,material_ids,smooth_flags):poly.material_index=idx;poly.use_smooth=smooth
 uv=me.uv_layers.new(name='Surface UV • metric')
 for poly,coords in zip(me.polygons,uv_faces):
  for li,uvcoord in zip(poly.loop_indices,coords):uv.data[li].uv=uvcoord
 for e in me.edges:e.use_edge_sharp=tuple(sorted(e.vertices)) in sharp_edges

 ob=bpy.data.objects.new(co.name+' | runtime batch',me);co.objects.link(ob)
 # Preserve smooth water normals; faceted rock and manufactured parts stay explicit.
 if co.name.startswith('03 |'):
  for p in me.polygons:p.use_smooth=True
 for old in candidates:bpy.data.objects.remove(old,do_unlink=True)
 batch_count+=1
bpy.ops.object.select_all(action='DESELECT')
for ob in S.objects:
 if ob.type in {'MESH','CAMERA','EMPTY'}:ob.select_set(True)
stats['runtime_objects_before_instancing']=sum(1 for o in S.objects if o.type=='MESH');stats['area_batches']=batch_count
stats['area_anchors_blender_z_up']=json.loads(S.get('area_anchors_json','{}'))
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'cavern-portfolio.glb'),export_format='GLB',use_selection=True,export_apply=False,export_cameras=True,export_lights=False,export_gpu_instances=True,export_materials='EXPORT',export_extras=True,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,export_draco_position_quantization=16,export_draco_normal_quantization=12)
stats['glb_bytes']=os.path.getsize(os.path.join(ROOT,'cavern-portfolio.glb'))
with open(os.path.join(ROOT,'runtime-manifest.json'),'w') as f:json.dump(stats,f,indent=2)
exec(compile(open(os.path.join(ROOT,'instance_glb.py')).read(),'instance_glb.py','exec'))
print('HANDOFF',open(os.path.join(ROOT,'runtime-manifest.json')).read())
