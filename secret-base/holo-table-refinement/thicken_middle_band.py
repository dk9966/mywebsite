"""Double the holotable fascia height without enlarging its radius again."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P=Path('/Users/danielku/mywebsite/secret-base/holo-table-refinement')
coll=bpy.data.collections['175 | Lower bay holo table']
assert not coll.get('middle_band_doubled'), 'Middle band has already been doubled.'
assert bpy.context.mode=='OBJECT'
filepath=bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-middle-band-thickness.blend'),copy=True,compress=True)
center=bpy.data.objects['Holo table | floor plinth'].matrix_world.translation.copy()
lower=.203
upper=.268
increase=upper-lower
outside={o.name:(o.data.as_pointer() if o.data else None,tuple(v for r in o.matrix_world for v in r))
         for o in bpy.context.scene.objects if o not in set(coll.objects)}
radius_before=max(v.co.xy.length for v in bpy.data.objects['Holo table | armored band panel 00'].data.vertices)

for o in coll.objects:
    if o.type=='LIGHT':
        world=o.matrix_world.copy();world.translation.z+=increase;o.matrix_world=world
        continue
    if o.type!='MESH':continue
    # The optical assembly follows the raised rim as a unit.
    optical=any(s in o.name for s in ['dark basin','misty holo glass','inner lip','inward projector'])
    o.data=o.data.copy()
    world=o.matrix_world.copy();inv=world.inverted()
    for v in o.data.vertices:
        p=world@v.co
        z=p.z-center.z
        if optical:p.z+=increase
        elif z>upper:p.z+=increase
        elif z>lower:p.z+=z-lower
        v.co=inv@p
    o.data.update()

bpy.context.view_layer.update()
assert outside=={name:(bpy.data.objects[name].data.as_pointer() if bpy.data.objects[name].data else None,
                       tuple(v for r in bpy.data.objects[name].matrix_world for v in r)) for name in outside}
radius_after=max(v.co.xy.length for v in bpy.data.objects['Holo table | armored band panel 00'].data.vertices)
assert abs(radius_before-radius_after)<1e-5
coll['middle_band_doubled']=True
coll['middle_band_height_m']=2*increase
text=bpy.data.texts.get('thicken_middle_band.py') or bpy.data.texts.new('thicken_middle_band.py')
text.clear();text.write(Path(__file__).read_text())
bpy.data.libraries.write(str(P/'table-preview.blend'),{coll},fake_user=True,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=filepath,compress=True)
result={'middle_band_before_m':increase,'middle_band_after_m':2*increase,
        'thickness_factor':2,'radius_m':radius_after,'unrelated_objects_preserved':len(outside),
        'saved':filepath,'backup':str(P/'before-middle-band-thickness.blend')}
(P/'middle-band-audit.json').write_text(json.dumps(result,indent=2))
