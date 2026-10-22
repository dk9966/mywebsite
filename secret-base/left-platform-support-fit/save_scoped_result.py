"""Save only this task's rock sculpt and supports onto the initial scene backup."""
import bpy,json,hashlib
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'before-left-fit.blend'))
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
floor=bpy.data.objects['Front left | beveled rectangle landing']
def sig(o):
 h=hashlib.sha256();h.update(repr([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
protected={o.name:sig(o) for o in bpy.context.scene.objects if o!=rock}
materials={m.name:m for m in bpy.data.materials};terrain_materials=list(rock.data.materials)
with bpy.data.libraries.load(str(P/'left-fit-preview.blend'),link=False) as (src,dst):
 dst.meshes=['Cave | fitted left bearing shoulder final']
 dst.collections=['167 | Left platform cliff supports']
rock.data.use_fake_user=True;rock['before_left_platform_fit_mesh']=rock.data.name
rock.data=dst.meshes[0];rock.data.materials.clear()
for m in terrain_materials:rock.data.materials.append(m)
col=dst.collections[0];bpy.context.scene.collection.children.link(col)
bpy.context.view_layer.update()
for ob in col.objects:
 world=ob.matrix_world.copy();ob.parent=floor;ob.matrix_world=world
 for slot in ob.material_slots:
  n=slot.material.name
  if n in materials:slot.material=materials[n]
  elif n.rsplit('.',1)[0] in materials:slot.material=materials[n.rsplit('.',1)[0]]
bpy.context.view_layer.update()
assert all(sig(bpy.data.objects[n])==s for n,s in protected.items())
output=P/'left-platform-fitted.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
report={'saved':str(output),'original_other_objects_unchanged':True,'new_support_parts':len(col.objects),'live_file_overwritten':False}
(P/'scoped-save-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
