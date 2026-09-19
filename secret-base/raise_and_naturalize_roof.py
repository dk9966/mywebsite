"""Raise the roof relative to Projects and soften the cave's angular treatment."""
import bpy,os,math
from mathutils import Vector,noise
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-higher-natural-roof.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
floor=bpy.data.objects['deck_floor_b'];datum=max((floor.matrix_world@v.co).z for v in floor.data.vertices)
roof=bpy.data.objects['Cave | continuous overhead roof with rooted stalactites']
if not roof.get('raised_40_percent'):
 for v in roof.data.vertices:
  p=v.co
  # Small coherent lateral bends replace straight cone axes.
  t=max(0,min(1,(13.1-p.z)/2.5))
  n=noise.noise_vector(Vector((p.x*.38,p.y*.38,3)))
  p.x+=n.x*.30*t;p.y+=n.y*.30*t
  p.z=datum+(p.z-datum)*1.4
 roof['raised_40_percent']=True
 roof['height_datum']=datum
roof.data.update()
for p in roof.data.polygons:p.use_smooth=True
mod=roof.modifiers.get('Natural flowing stalactite profiles') or roof.modifiers.new('Natural flowing stalactite profiles','SUBSURF')
mod.subdivision_type='CATMULL_CLARK';mod.levels=2;mod.render_levels=2
# Smooth the old enclosing vault while preserving its broad irregular outline.
vault=bpy.data.objects['Cave | continuous sculpted walls and hanging roof']
for p in vault.data.polygons:p.use_smooth=True
mod=vault.modifiers.get('Weathered cave transitions') or vault.modifiers.new('Weathered cave transitions','SMOOTH')
mod.factor=.6;mod.iterations=3
mod=vault.modifiers.get('Natural cave surface') or vault.modifiers.new('Natural cave surface','SUBSURF')
mod.levels=1;mod.render_levels=1
# Quiet the most graphic added wall plates; retain restrained relief.
strata=bpy.data.objects.get('Cave | broad vertical stepped strata')
if strata:
 for p in strata.data.polygons:p.use_smooth=True
 bevel=strata.modifiers.get('Weathered fracture edges') or strata.modifiers.new('Weathered fracture edges','BEVEL')
 bevel.width=.035;bevel.segments=3
for o in bpy.data.collections['Cave_Backdrop'].objects:
 if o.type=='MESH' and 'bedrock' in o.name:
  for p in o.data.polygons:p.use_smooth=True
mats=set()
for o in [roof,vault]+([strata] if strata else []):
 for m in o.data.materials:
  if m and m.use_nodes:mats.add(m)
for m in mats:
 for node in m.node_tree.nodes:
  if node.type=='BSDF_PRINCIPLED':
   node.inputs['Roughness'].default_value=.78;node.inputs['Specular IOR Level'].default_value=.26
  elif node.type=='TEX_NOISE':
   node.inputs['Scale'].default_value=3.2;node.inputs['Detail'].default_value=3;node.inputs['Roughness'].default_value=.6
  elif node.type=='BUMP':
   node.inputs['Strength'].default_value=.12;node.inputs['Distance'].default_value=.025
# Move roof-only lights with the increased clearance, retaining their reach.
for o in bpy.data.collections['Cave_Continuous_Roof'].objects:
 if o.type=='LIGHT' and not o.get('raised_40_percent'):
  o.location.z=datum+(o.location.z-datum)*1.4;o.data.energy*=1.35;o['raised_40_percent']=True
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'projects_datum':datum,'roof_clearance_multiplier':1.4,'roof_min_z':min(v.co.z for v in roof.data.vertices),'roof_max_z':max(v.co.z for v in roof.data.vertices)}
