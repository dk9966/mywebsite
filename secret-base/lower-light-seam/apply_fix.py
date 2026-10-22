"""Move the right cave fill's emitting plane clear of the lower platform."""
import bpy, json
from mathutils import Vector
from pathlib import Path
p=Path('/Users/danielku/mywebsite/secret-base/lower-light-seam')
o=bpy.data.objects['RL | Cave | soft side bounce +1']
if o.get('Lower floor cutoff repaired'):
    raise RuntimeError('Repair already applied')
bpy.ops.wm.save_as_mainfile(filepath=str(p/'before-applying.blend'),copy=True,compress=True)
before=list(o.matrix_world.translation)
mw=o.matrix_world.copy()
mw.translation-=(mw.to_quaternion()@Vector((0,0,-1)))*4.0
o.matrix_world=mw
o['Lower floor cutoff repaired']='Emitter moved backward 4 m along emission axis so its plane no longer crosses the lower deck.'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result={'saved':bpy.data.filepath,'light':o.name,'before_world_position':before,'after_world_position':list(o.matrix_world.translation),'backup':str(p/'before-applying.blend')}
(p/'verification.json').write_text(json.dumps(result,indent=2))
