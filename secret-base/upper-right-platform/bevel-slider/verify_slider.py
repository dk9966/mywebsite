import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;D=json.loads((P/'slider.json').read_text());S=bpy.context.scene
ctrl=bpy.data.objects['SCENE SLIDERS'];m=ctrl.modifiers['Scene Sliders'];sid=D['identifier'];old=m[sid]
up=bpy.data.objects['Upper | beveled square gallery'];F=up.matrix_world.copy();IV=F.inverted();A=float(up['side_m'])/2;H=float(up['deck_height_m']);wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
rows=[]
def update(value):m[sid]=value;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
try:
 for value in (.10,.30,.80,1.50):
  update(value);dg=bpy.context.evaluated_depsgraph_get();e=up.evaluated_get(dg);pts=[IV@e.matrix_world@v.co for v in e.data.vertices]
  cut=2*A-max(abs(p.x)+abs(p.y) for p in pts)
  floor_max=-100;rail_max=-100
  for o in bpy.data.collections['171 | Upper right square gallery'].objects:
   if not ('satin floor plate' in o.name or 'guardrail' in o.name or 'railing upright' in o.name):continue
   ob=o.evaluated_get(dg);excess=max(abs(p.x)+abs(p.y)-(2*A-value) for p in [IV@ob.matrix_world@v.co for v in ob.data.vertices])
   if 'satin floor' in o.name:floor_max=max(floor_max,excess)
   else:rail_max=max(rail_max,excess)
  rock=wall.evaluated_get(dg);M=rock.matrix_world.inverted()@F;gaps=[];head=[]
  for i in range(21):
   for j in range(21):
    x=-2.7+5.4*i/20;y=-2.7+5.4*j/20
    if abs(x)+abs(y)>2*A-value-.35:continue
    hit,p,n,idx=rock.ray_cast(M@Vector((x,y,H-.15)),M.to_3x3()@Vector((0,0,-1)),distance=10)
    gap=H-.2-(IV@rock.matrix_world@p).z if hit else 100;gaps.append(gap)
    hit,p,n,idx=rock.ray_cast(M@Vector((x,y,H+.006)),M.to_3x3()@Vector((0,0,1)),distance=1.5)
    if hit:head.append((x,y))
  invalid=[]
  for name in D['objects']:
   keys=bpy.data.objects[name].data.shape_keys
   if keys.animation_data:
    invalid.extend(name for fc in keys.animation_data.drivers if not fc.driver.is_valid)
  rows.append({'slider_m':value,'measured_corner_cut_m':cut,'cut_error_mm':abs(cut-value)*1000,'floor_outside_diagonal_m':floor_max,'rails_outside_diagonal_m':rail_max,'support_samples':len(gaps),'maximum_bearing_gap_mm':max(gaps)*1000,'minimum_bearing_gap_mm':min(gaps)*1000,'headroom_intrusions':len(head),'invalid_drivers':invalid})
finally:update(old)
result={'restored_m':old,'checks':rows};(P/'verification.json').write_text(json.dumps(result,indent=2))
