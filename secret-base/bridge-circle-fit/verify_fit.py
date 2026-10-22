"""Verify evaluated joint clearance and radius-slider behavior in a saved copy."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
report=json.loads((P/'fit-report.json').read_text())
S=bpy.context.scene
rim=bpy.data.objects['Metal | upper rolled rim']
ctrl=bpy.data.objects['SCENE SLIDERS'];slider=ctrl.modifiers['Scene Sliders']
initial=slider['Socket_7']
C=bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy();C.z=0
phase=math.atan2(rim.matrix_world[1][0],rim.matrix_world[0][0])
base=max(math.hypot(v.co.x,v.co.y) for v in rim.data.vertices)
angles=sorted(set(round(math.atan2(v.co.y,v.co.x),6) for v in rim.data.vertices if abs(math.hypot(v.co.x,v.co.y)-base)<1e-5))
step=math.tau/len(angles)
records=[]
try:
 for value in (initial,initial-.01,initial+.01):
  slider['Socket_7']=value;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
  dg=bpy.context.evaluated_depsgraph_get()
  cut=bpy.data.objects['Bridge circle | hidden rim-following cut'].evaluated_get(dg)
  cp=[cut.matrix_world@v.co-C for v in cut.data.vertices]
  radius=max(math.hypot(p.x,p.y) for p in cp)
  minimum=1e9;empty=[];counts={};violations=[]
  for name in report['trimmed_objects']+report['end_frames']:
   o=bpy.data.objects[name].evaluated_get(dg)
   ps=[o.matrix_world@v.co-C for v in o.data.vertices]
   counts[name]=len(ps)
   if not ps:empty.append(name);continue
   for p in ps:
    a=math.atan2(p.y,p.x)-phase
    mid=angles[0]+(math.floor((a-angles[0])/step)+.5)*step
    boundary=radius*math.cos(step/2)/math.cos(a-mid)
    delta=math.hypot(p.x,p.y)-boundary
    minimum=min(minimum,delta)
    if delta<-.00008:violations.append((name,delta))
  assert not violations,violations[:10]
  # These old transverse bars lie entirely inside the platform. Their curved
  # replacements now finish the outside of the joint.
  if value==initial:
   assert set(empty)=={'Bridge | transverse panel frame 00','Bridge | deck cross bearer 00','Left stairs | bridge cross bearer','Rear left | bridge cross bearer'},empty
  print('Verified width setting',value,flush=True)
  records.append({'width_slider':value,'minimum_cut_clearance_m':minimum,'rim_fitting_gap_m':report['clearance_m'],'vertex_counts':counts,'fully_trimmed_original_crossbars':empty,'intrusions':len(violations)})
finally:
 slider['Socket_7']=initial;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
invalid=[]
for o in S.objects:
 if o.animation_data:
  for f in o.animation_data.drivers:
   if not f.driver.is_valid:invalid.append((o.name,f.data_path))
assert not invalid,invalid
(P/'verification.json').write_text(json.dumps({'checks':records,'invalid_drivers':invalid,'original_meshes_and_transforms_preserved':report['original_objects_preserved']},indent=2))
print(json.dumps({'verified_width_settings':len(records),'no_bridge_intrusions':True,'invalid_drivers':len(invalid)}))
