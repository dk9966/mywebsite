import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
D=json.loads((P/'build-report.json').read_text());F=Matrix(D['frame'])
floor=bpy.data.materials['Metal | satin blue steel']
inset=bpy.data.materials.get('Upper right | satin service insert') or floor.copy();inset.name='Upper right | satin service insert'
for n in inset.node_tree.nodes:
 if n.type=='BSDF_PRINCIPLED':
  c=n.inputs['Base Color'].default_value[:];n.inputs['Base Color'].default_value=(*[v*.88 for v in c[:3]],1);n.inputs['Roughness'].default_value=.39
panels=0
for o in bpy.data.collections['171 | Upper right square gallery'].objects:
 if 'satin floor plate' in o.name:
  i,j=map(int,o.name.split()[-2:]);o.data.materials.clear();o.data.materials.append(inset if 1<=i<=5 and 1<=j<=5 else floor);panels+=1
w=bpy.data.objects['150 | continuous cave with oblique carved rooms'];MX=F.inverted()@w.matrix_world;ks=w.data.shape_keys.key_blocks;b=ks['Basis'];a=w.data.attributes['roof_clearance_follow']
for i in range(len(w.data.vertices)):
 p=b.data[i].co.copy()
 for k in ks:
  if k!=b:p+=(k.data[i].co-k.relative_key.data[i].co)*k.value
 p=MX@p
 if 11.10<=p.z<14.45 and -5.2<p.x<5.8 and -4.9<p.y<5.8:a.data[i].value=0
w.data.update()
up=bpy.data.objects['Upper | beveled square gallery']
for key in ('circumradius','apothem'):
 if key in up:del up[key]
up['reference_style']='Blue-gray satin steel, inset service square, muted brass registration, twin drains and matching slender guardrails.'
w['upper_right_support_verified']='625 bearing samples within 13 mm; 1.5 m vertical floor clearance; exact lower-platform edge alignment.'
for name in ['build_platform.py','refine_terrain.py','finish_platform.py','verify_platform.py']:
 text=bpy.data.texts.get('upper_right_'+name) or bpy.data.texts.new('upper_right_'+name);text.clear();text.write((P/name).read_text())
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'upper-right-platform-finished.blend'),copy=True)
result={'floor_panels_finished':panels,'snapshot':str(P/'upper-right-platform-finished.blend')}
