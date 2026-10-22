import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
out={}
for label,file in [('current',P/'connected-cavern-right-wall-rebuilt.blend'),('center',P.parent/'central-metal-platform/central-metal-platform.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(file))
    out[label]={'collections':{c.name:{'count':len(c.objects),'types':sorted(set(o.type for o in c.objects)),'examples':[o.name for o in list(c.objects)[:5]]} for c in bpy.data.collections},'meshes':{o.name:[c.name for c in o.users_collection] for o in bpy.context.scene.objects if o.type=='MESH'},'lights':[{'name':o.name,'pos':list(I@o.location),'energy':o.data.energy} for o in bpy.context.scene.objects if o.type=='LIGHT']}
(P/'simplification-source-inventory.json').write_text(json.dumps(out,indent=2))
print('INVENTORY_SAVED',flush=True)
