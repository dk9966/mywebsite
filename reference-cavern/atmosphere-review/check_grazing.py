import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/Users/danielku/mywebsite/reference-cavern/atmosphere-review/pass-12.blend')
s=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get();r=[]
for o in s.objects:
 if o.type!='LIGHT' or not o.name.startswith(('Grazing |','Depth |')):continue
 p=o.location.copy();d=o.rotation_euler.to_quaternion()@Vector((0,0,-1));hits=[]
 for j in range(5):
  hit,loc,norm,index,obj,m=s.ray_cast(dg,p,d,distance=35)
  if not hit:break
  hits.append([obj.name,list(loc)])
  if not obj.name.startswith('ATMOSPHERE'):break
  p=loc+d*.03
 r.append({'name':o.name,'hits':hits})
print('RAYS',json.dumps(r))
